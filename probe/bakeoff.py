"""Stage 1 bake-off: where does each model break on long multiplication?

Answers four questions in one session, on a hard budget:
  1. Which digit size does each candidate stop converging on the right answer?
  2. How many output tokens does a problem of size a x b actually cost?
  3. Does throughput per dollar differ across GPUs enough to care?
  4. Does temperature move the boundary?

Cost guardrails (the balance is $5.41):
  max_containers=1      never more than one GPU per class
  scaledown_window=60   GPU released 60s after the last call
  timeout               hard ceiling per call
  max_tokens            hard ceiling per generation, scaled to a*b
Always finish with:  modal app stop carrychain-bakeoff -y

Image pins copied from ~/Projects/goblins/goblins-takehome/infra/modal/qwen_grader.py,
which documents vLLM 0.11.0 + transformers 4.57.0 as a verified-compatible pair.

Usage:
  modal run probe/bakeoff.py::prefetch --models "Qwen/Qwen3-4B,Qwen/Qwen3-8B"
  modal run probe/bakeoff.py::smoke
  modal run probe/bakeoff.py::boundary --model "Qwen/Qwen3-8B" --gpu l40s
"""

import hashlib
import json
import random
import time

import modal

MINUTES = 60

vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.8.1-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install(
        "vllm==0.11.0",
        "transformers==4.57.0",
        "huggingface_hub[hf_transfer]",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "VLLM_USE_V1": "1"})
)

hf_cache = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("vllm-cache", create_if_missing=True)
results_vol = modal.Volume.from_name("carrychain-runs", create_if_missing=True)

app = modal.App("carrychain-bakeoff")


# --------------------------------------------------------------------------
# Problems. Seeded so every model sees the SAME instances (paired design).
# --------------------------------------------------------------------------
POOL = 256  # fixed pool per cell; n slices a PREFIX so cells nest across runs


def make_problems(a: int, b: int, n: int, seed: int = 20260730):
    """First n of a fixed per-cell pool. Deterministic given (a, b, seed).

    n is deliberately NOT in the seed. It used to be, which meant an n=10 draw
    and an n=45 draw of the same cell shared zero instances, so adaptive sample
    counts silently destroyed the pairing that every cross-model statistic
    depends on. instance_id indexes the pool, so it means the same problem in
    every run at every n.
    """
    if n > POOL:
        raise ValueError(f"n={n} exceeds pool size {POOL}")
    rng = random.Random(f"{seed}-{a}-{b}")
    out = []
    for i in range(POOL):
        x = rng.randrange(10 ** (a - 1), 10**a)
        y = rng.randrange(10 ** (b - 1), 10**b)
        if i < n:
            # content-addressed id: two records refer to the same problem iff
            # this matches. instance_id is a positional index and can silently
            # mean different problems across runs; the uid cannot.
            uid = hashlib.sha256(
                f"{seed}|{a}|{b}|{x}|{y}".encode()).hexdigest()[:16]
            out.append({"instance_id": i, "instance_uid": uid,
                        "a": a, "b": b, "x": x, "y": y,
                        "truth": str(x * y), "problem_seed": seed})
    return out


PROMPT = (
    "Compute the exact product of {x} and {y}.\n"
    "Work it out however you like, but the final line of your reply must be "
    "exactly:\nANSWER: <the full integer>"
)


def token_budget(a: int, b: int, ceiling: int, per_step: int = 200,
                 base: int = 2000, mode: str = "formula"):
    """Room to work, NOT a cost control.

    The ceiling must never be the thing that ends a generation, or the cell
    stops measuring the model and starts measuring the budget. Two failure
    modes it has to avoid:

      - A flat cap gives large problems proportionally LESS room than small
        ones, which manufactures a cliff at exactly the sizes under study.
        A cap-induced cliff is indistinguishable from a real one, and since a
        cliff is what we expect to see, nothing would flag it.
      - Any cap collapses "quit early", "finished long", and "would have run
        forever" into one finish_reason=length bucket, unrecoverably. The
        quit-vs-grind cliff is a finding; it cannot survive a tight ceiling.

    So scale with a*b and let `ceiling` be the model's context window, not a
    magic number. Long generations are cheap (~$0.005 for 32K tokens); it is
    the NUMBER of generations that costs money.

    Validity rule enforced in analysis: a cell whose truncation rate is not
    near zero is measuring the ceiling and must be rerun with more room.

    Returns (max_tokens, wanted, was_clipped). Never clip silently — if the
    context window could not supply what the problem size asked for, that fact
    is recorded on every affected record so no cell can be read as a capability
    limit when it was a room limit.
    """
    # mode="max" grants every token the context can hold. Required to locate a
    # CEILING: a formula that asks for less than the room available can never
    # tell you whether the model or the budget stopped the generation. Measured
    # cost per unit of N declines with problem size (452 * N^-0.24), so a linear
    # formula over-asks at small N and under-asks at large N -- exactly wrong
    # for finding where the model gives out.
    wanted = ceiling if mode == "max" else base + per_step * a * b
    granted = min(ceiling, wanted)
    return granted, wanted, wanted > ceiling


# Reasoning markers differ by family. gpt-oss uses harmony channels and emits
# no <think> tag at all: all 30 gpt-oss records on disk had thinking_requested
# True and thinking_observed False, while their raw text plainly began
# "<|channel|>analysis". Filtering on that field would label a reasoning-ON run
# as OFF -- the error that wasted 538 generations (D-2).
THINK_MARKERS = ("<think>", "</think>", "<|channel|>analysis", "<|start|>assistant<|channel|>")


def _observed_thinking(text):
    for m in THINK_MARKERS:
        if m in text:
            return True, m
    return False, None


def _classify(finish_reason, ans, truth):
    """Four outcomes, not two. Collapsing these is what a tight cap destroys.

      converged_right / converged_wrong : model stopped on its own with an answer
      quit  : model stopped on its own WITHOUT an answer -- a behavioural result,
              and detectable at any ceiling because it is short + finish=stop
      grind : used the entire ceiling and never finished. Only meaningful when
              the ceiling is the context window; otherwise it measures the cap.
    """
    if finish_reason == "length":
        return "grind"
    if ans is None:
        return "quit"
    return "converged_right" if ans == truth else "converged_wrong"


def parse_answer(text: str):
    """Return (answer, method). method names HOW it was found, and the caller
    records it so a cell relying on a weak path can be excluded.

    Three incarnations of this function have now been wrong, each in a
    different direction, and each cost real GPU time:

      v1 too permissive -- captured across newlines, and a bare "last 4+ digit
        run" fallback turned refusals into fabricated answers.
      v2 too strict -- anchored to ^ANSWER:...$, which markdown bold breaks.
        82 of 89 `quit` records had answered; 58 were correct.
      v3 still too strict -- required a colon after ANSWER. Qwen's actual house
        style is "### Final Answer" then "$$\\boxed{1234}$$", which has no
        marker at all. 19 of 20 `quit` records were correct answers.

    v4 accepts the three forms models actually use, in priority order, and is
    tested against a corpus of real tails in tests/test_parser.py. Do not edit
    without adding the failing tail to that corpus first.
    """
    import re

    # 1. the requested format: ANSWER: <int>, allowing markdown/LaTeX decoration
    DECOR = r"[\s*_`$]*"
    OPEN = r"(?:\\boxed\{|\\text\{|[{}])*"   # incl. the } in \text{ANSWER: } 123
    NUM = r"([+-]?\d[\d,\u00a0 \t]*)"
    pat = re.compile(rf"{DECOR}{OPEN}{DECOR}ANSWER{DECOR}[:\s]{DECOR}{OPEN}{DECOR}{NUM}", re.I)
    hits = list(pat.finditer(text))
    if hits:
        m = hits[-1]
        if not re.match(r"[.eE]\d", text[m.end():m.end() + 2]):
            v = re.sub(r"[,\s\u00a0]", "", m.group(1))
            if re.fullmatch(r"[+-]?\d+", v):
                return v, "marker"

    # 2. \boxed{<int>} -- the LaTeX convention models reach for unprompted.
    #    A format violation, not a refusal: the answer is unambiguous.
    box = re.findall(r"\\boxed\{\s*([+-]?[\d][\d,\u00a0 \t]*)\s*\}", text)
    if box:
        v = re.sub(r"[,\s\u00a0]", "", box[-1])
        if re.fullmatch(r"[+-]?\d+", v):
            return v, "boxed"

    # 3. last meaningful line, if it is nothing but a number. Skips LaTeX
    #    delimiters and rules, which is what made v3 miss the boxed form.
    for ln in reversed([x.strip() for x in text.strip().split("\n")]):
        if not ln or re.fullmatch(r"[$\-=*_~`\s]+", ln):
            continue
        bare = re.sub(r"[,\s\u00a0*_`$]", "", ln)
        bare = re.sub(r"^\\boxed\{|^\\text\{|\}$|\.$", "", bare)
        if re.fullmatch(r"[+-]?\d+", bare):
            return bare, "last_line"
        break
    return None, "none"

# --------------------------------------------------------------------------
# CPU-only weight prefetch. Pulling 16GB on a rented GPU is pure waste.
# --------------------------------------------------------------------------
@app.function(
    image=vllm_image,
    volumes={"/root/.cache/huggingface": hf_cache},
    timeout=60 * MINUTES,
    cpu=4,
    secrets=[modal.Secret.from_name("hf")],
)
def prefetch_one(model: str):
    from huggingface_hub import snapshot_download

    t0 = time.time()
    try:
        snapshot_download(model, ignore_patterns=["*.pth", "original/*"])
        hf_cache.commit()
        return {"model": model, "ok": True, "seconds": round(time.time() - t0, 1)}
    except Exception as e:
        return {"model": model, "ok": False, "error": str(e)[:300]}


# --------------------------------------------------------------------------
# GPU probe. One class per GPU type — Modal fixes gpu= at decoration time.
# --------------------------------------------------------------------------
def _load_engine(self):
    """Shared @modal.enter body. Modal fixes gpu= at decoration time, so each
    GPU needs its own class; the logic lives here to avoid four copies."""
    from vllm import LLM

    t0 = time.time()
    self.llm = LLM(
        model=self.model,
        max_model_len=self.max_len,
        gpu_memory_utilization=0.90,
        trust_remote_code=True,
    )
    self.load_seconds = round(time.time() - t0, 1)
    # The real ceiling is whatever context the engine actually came up with.
    self.engine_max_len = self.llm.llm_engine.model_config.max_model_len


def _seed_for(sweep_id, model, a, b, instance_id, sample_idx):
    """Deterministic per-generation seed that is INDEPENDENT across repeats.

    The old `seed_base + batch_position` made two things go wrong at once:
    the seed moved when the sizes list changed, and repeated samples of the
    same instance got the SAME seed -- so a depth-tier "30/30 reproducible
    failure", which the design reads as proof of a deterministic blind spot,
    was guaranteed by construction. Hash the full condition instead.
    """
    import hashlib

    key = f"{sweep_id}|{model}|{a}|{b}|{instance_id}|{sample_idx}"
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)


def _run_batch(self, gpu_name, jobs, temperature, top_p, thinking,
               ceiling, sweep_id="dev", sample_idx=0, batch_seq=0,
               submit_base=0, warmup=2, budget_mode="formula"):
    """Shared @modal.method body. One record per generation.

    `ceiling` is the same for every model in a comparison. Giving each model
    its own full context window would mean Qwen gets 32K and gpt-oss gets 131K,
    so any pass-rate difference would be confounded with how much room each had.
    """
    from vllm import SamplingParams

    # Never exceed what the engine can actually hold: context minus the prompt
    # minus a small margin. `ceiling=0` means "use everything the engine has".
    hard = self.engine_max_len if not ceiling else min(ceiling, self.engine_max_len)

    msgs, params, budgets, prompts = [], [], [], []
    for j_i, j in enumerate(jobs):
        prompt = PROMPT.format(x=j["x"], y=j["y"])
        prompts.append(prompt)
        msgs.append([{"role": "user", "content": prompt}])
        room = hard - 256  # margin for chat template + prompt tokens
        granted, wanted, clipped = token_budget(j["a"], j["b"], room,
                                                mode=budget_mode)
        budgets.append((granted, wanted, clipped))
        params.append(
            SamplingParams(
                temperature=temperature,
                top_p=top_p,
                max_tokens=granted,
                skip_special_tokens=False,
                seed=_seed_for(sweep_id, self.model, j["a"], j["b"],
                              j["instance_id"], sample_idx),
            )
        )

    if warmup and jobs:
        from vllm import SamplingParams as _SP
        self.llm.chat([[{"role": "user", "content": PROMPT.format(x=7, y=8)}]] * warmup,
                      [_SP(temperature=0.0, max_tokens=16)] * warmup)

    t0 = time.time()
    if thinking:
        outs = self.llm.chat(msgs, params)
    else:
        try:
            outs = self.llm.chat(
                msgs, params, chat_template_kwargs={"enable_thinking": False}
            )
        except Exception:
            outs = self.llm.chat(msgs, params)  # model has no thinking switch
    wall = time.time() - t0

    from collections import Counter

    cell_n = Counter((j["a"], j["b"]) for j in jobs)

    recs = []
    import hashlib

    for j, o, prompt, (granted, wanted, clipped) in zip(jobs, outs, prompts, budgets):
        text = o.outputs[0].text
        ans, parse_method = parse_answer(text)
        outcome = _classify(o.outputs[0].finish_reason, ans, j["truth"])
        _obs_think, _obs_marker = _observed_thinking(text)
        recs.append(
            {
                "model": self.model,
                "gpu": gpu_name,
                "a": j["a"],
                "b": j["b"],
                "instance_id": j["instance_id"],
                "instance_uid": j.get("instance_uid"),
                "x": str(j["x"]),
                "y": str(j["y"]),
                "truth": j["truth"],
                "answer": ans,
                "correct": outcome == "converged_right",
                "parse_method": parse_method,
                "finish_reason": o.outputs[0].finish_reason,
                "completion_tokens": len(o.outputs[0].token_ids),
                "prompt_tokens": len(o.prompt_token_ids),
                "temperature": temperature,
                "top_p": top_p,
                "seed": _seed_for(sweep_id, self.model, j["a"], j["b"],
                                 j["instance_id"], sample_idx),
                "sample_idx": sample_idx,
                "submit_index": j.get("_pos"),
                "budget_mode": budget_mode,
                "batch_seq": batch_seq,
                "sweep_id": sweep_id,
                "problem_seed": j.get("problem_seed"),
                "prompt_text": prompt,
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()[:16],
                "n_in_cell": j.get("_n_in_cell", cell_n[(j["a"], j["b"])]),
                "trial_index": j["instance_id"],
                "thinking_requested": thinking,
                "thinking_observed": _obs_think,
                "thinking_marker": _obs_marker,
                "max_tokens": granted,
                "tokens_wanted": wanted,
                "room_clipped": clipped,
                "engine_max_len": self.engine_max_len,
                "outcome": outcome,
                "raw_text": text,
            }
        )
    return {
        "records": recs,
        "batch_wall_seconds": round(wall, 1),
        "load_seconds": self.load_seconds,
        "gpu": gpu_name,
        "model": self.model,
        "total_completion_tokens": sum(r["completion_tokens"] for r in recs),
    }


_CLS_KW = dict(
    image=vllm_image,
    volumes={"/root/.cache/huggingface": hf_cache, "/root/.cache/vllm": vllm_cache},
    secrets=[modal.Secret.from_name("hf")],
    timeout=60 * MINUTES,   # a batch that overruns loses everything: no
                            # checkpointing yet (open defect O-4)
    scaledown_window=30,
    max_containers=1,
)


@app.cls(gpu="L40S", **_CLS_KW)
class ProbeL40S:
    model: str = modal.parameter()
    max_len: int = modal.parameter(default=32768)

    @modal.enter()
    def load(self):
        _load_engine(self)

    @modal.method()
    def run(self, jobs: list, temperature: float, top_p: float = 0.95,
            thinking: bool = True, ceiling: int = 0,
            sweep_id: str = "dev", sample_idx: int = 0,
            budget_mode: str = "formula"):
        return _run_batch(self, "L40S", jobs, temperature, top_p, thinking, ceiling,
                      sweep_id, sample_idx, budget_mode=budget_mode)


@app.cls(gpu="H100", **_CLS_KW)
class ProbeH100:
    model: str = modal.parameter()
    max_len: int = modal.parameter(default=32768)

    @modal.enter()
    def load(self):
        _load_engine(self)

    @modal.method()
    def run(self, jobs: list, temperature: float, top_p: float = 0.95,
            thinking: bool = True, ceiling: int = 0,
            sweep_id: str = "dev", sample_idx: int = 0,
            budget_mode: str = "formula"):
        return _run_batch(self, "H100", jobs, temperature, top_p, thinking, ceiling,
                      sweep_id, sample_idx, budget_mode=budget_mode)


# A10G cannot hold these models at 32K context, and A100-40GB adds nothing over
# the L40S. gpt-oss-20b needs compute capability >= 9.0 for its MXFP4 weights,
# so H100 is mandatory for it: on Ada (L40S, sm89) vLLM falls back to the Marlin
# MoE kernel, which fails because hidden_size == intermediate_size == 2880 is not
# divisible by 128 (vllm-project/vllm#38022).
PROBES = {"l40s": ProbeL40S, "h100": ProbeH100}


# --------------------------------------------------------------------------
# Local entrypoints
# --------------------------------------------------------------------------
@app.local_entrypoint()
def prefetch(models: str):
    """CPU-only weight download into the shared Volume. Near-free."""
    names = [m.strip() for m in models.split(",") if m.strip()]
    for r in prefetch_one.map(names):
        print(json.dumps(r))


@app.local_entrypoint()
def smoke(model: str = "Qwen/Qwen3-4B", gpu: str = "l40s"):
    """Cheapest possible end-to-end proof: 6 easy problems, one temperature."""
    jobs = make_problems(3, 3, 3) + make_problems(4, 4, 3)
    p = PROBES[gpu](model=model)
    out = p.run.remote(jobs, temperature=0.7)
    n_ok = sum(r["correct"] for r in out["records"])
    print(f"\nmodel={model} gpu={out['gpu']} load={out['load_seconds']}s "
          f"batch={out['batch_wall_seconds']}s tokens={out['total_completion_tokens']}")
    print(f"correct {n_ok}/{len(out['records'])}")
    for r in out["records"]:
        print(f"  {r['a']}x{r['b']} {'OK ' if r['correct'] else 'BAD'} "
              f"{r['completion_tokens']:>5}tok {r['finish_reason']:<6} "
              f"got={str(r['answer'])[:24]} truth={r['truth'][:24]}")
    _save(out["records"], f"smoke-{model.split('/')[-1]}-{gpu}")


@app.local_entrypoint()
def boundary(model: str = "Qwen/Qwen3-8B", gpu: str = "l40s",
             sizes: str = "3,4,5,6,7,8,9,10", n: int = 6,
             temps: str = "0.7", thinking: str = "true",
             budget_mode: str = "formula"):
    """Diagonal sweep: find where the model stops converging. Same seeded
    instances for every model, so results are paired."""
    size_list = [int(s) for s in sizes.split(",")]
    temp_list = [float(t) for t in temps.split(",")]
    think = thinking.lower() == "true"

    p = PROBES[gpu](model=model)
    all_recs, meta = [], []
    for temp in temp_list:
        jobs = []
        for s in size_list:
            jobs += make_problems(s, s, n)
        out = p.run.remote(jobs, temperature=temp, thinking=think,
                           budget_mode=budget_mode)
        all_recs += out["records"]
        meta.append(out)
        print(f"\n=== {model} @ {out['gpu']} temp={temp} thinking={think} "
              f"load={out['load_seconds']}s batch={out['batch_wall_seconds']}s "
              f"tokens={out['total_completion_tokens']}")
        print(f"  {'size':>7} {'right':>7} {'wrong':>6} {'quit':>5} {'grind':>6} "
              f"{'avg tok':>8} {'max tok':>8}")
        for s in size_list:
            rs = [r for r in out["records"] if r["a"] == s]
            c = {k: sum(r["outcome"] == k for r in rs) for k in
                 ("converged_right", "converged_wrong", "quit", "grind")}
            toks = [r["completion_tokens"] for r in rs]
            bar = "#" * c["converged_right"] + "." * (len(rs) - c["converged_right"])
            print(f"  {s:>3}x{s:<3} {c['converged_right']:>3}/{len(rs):<3} "
                  f"{c['converged_wrong']:>6} {c['quit']:>5} {c['grind']:>6} "
                  f"{sum(toks) / len(toks):>8.0f} {max(toks):>8}  {bar}")
    _save(all_recs, f"boundary-{model.split('/')[-1]}-{gpu}")
    print(json.dumps([{k: v for k, v in m.items() if k != "records"} for m in meta], indent=1))


def _save(records, tag):
    """Append-only, unique filename. Raw output is immutable: a rerun with
    different settings must never overwrite an earlier run's raw records."""
    import hashlib
    import pathlib

    d = pathlib.Path(__file__).resolve().parent.parent / "runs"
    d.mkdir(exist_ok=True)
    stamp = hashlib.sha256(json.dumps(records[:1], sort_keys=True).encode()).hexdigest()[:8]
    f = d / f"{tag}-{len(records)}rec-{stamp}.jsonl"
    if f.exists():
        raise FileExistsError(f"refusing to overwrite raw records at {f}")
    with open(f, "w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    print(f"wrote {f} ({len(records)} records)")


@app.local_entrypoint()
def variance(model: str = "Qwen/Qwen3-4B", gpu: str = "l40s",
             temps: str = "0.0,0.5,1.0", instances: int = 20, samples: int = 5,
             scan_sizes: str = "3,4,5,6", scan_n: int = 8):
    """How much variance is there at different temperatures near a 50% cell?

    Two passes in ONE warm container (one cold start, not two):
      1. scan the diagonal to find the cell closest to 50%
      2. at that cell, run `instances` problems x `samples` repeats x each temp

    Repeats on the SAME instance are what separate between-instance variance
    (some problems are harder) from within-instance variance (the same problem
    sometimes right, sometimes wrong). The grid alone cannot tell them apart,
    and the ratio decides how many samples per cell the real sweep needs.
    """
    size_list = [int(s) for s in scan_sizes.split(",")]
    temp_list = [float(t) for t in temps.split(",")]
    p = PROBES[gpu](model=model)

    scan_jobs = []
    for s in size_list:
        scan_jobs += make_problems(s, s, scan_n)
    scan = p.run.remote(scan_jobs, temperature=0.7, sweep_id="var-scan")
    print(f"\n=== scan  load={scan['load_seconds']}s batch={scan['batch_wall_seconds']}s")
    rates = {}
    for s in size_list:
        rs = [r for r in scan["records"] if r["a"] == s]
        rates[s] = sum(r["correct"] for r in rs) / len(rs)
        print(f"  {s}x{s}  {sum(r['correct'] for r in rs)}/{len(rs)}  = {rates[s]:.2f}")
    cell = min(rates, key=lambda s: abs(rates[s] - 0.5))
    print(f"  -> closest to 50%: {cell}x{cell} at {rates[cell]:.2f}")

    jobs = make_problems(cell, cell, instances)
    allrecs = list(scan["records"])
    for t in temp_list:
        for si in range(samples):
            out = p.run.remote(jobs, temperature=t, top_p=1.0,
                               sweep_id="var", sample_idx=si)
            allrecs += out["records"]
        print(f"  temp {t}: {samples} repeats x {instances} instances done")
    _save(allrecs, f"variance-{model.split('/')[-1]}-{gpu}")
    _variance_report(allrecs, cell, temp_list, instances, samples)


def _variance_report(recs, cell, temps, instances, samples):
    """Decompose cell variance into between-instance and within-instance."""
    print(f"\n{'=' * 66}\nvariance at {cell}x{cell}  "
          f"({instances} instances x {samples} repeats)\n{'=' * 66}")
    print(f"{'temp':>5} {'pass':>7} {'between':>9} {'within':>8} {'ICC':>6} "
          f"{'always':>7} {'never':>6} {'split':>6}")
    for t in temps:
        rs = [r for r in recs if r["temperature"] == t and r["sweep_id"] == "var"]
        if not rs:
            continue
        by_inst = {}
        for r in rs:
            by_inst.setdefault(r["instance_uid"] if "instance_uid" in r
                               else r["instance_id"], []).append(r["correct"])
        pis = [sum(v) / len(v) for v in by_inst.values() if v]
        k = sum(len(v) for v in by_inst.values())
        pbar = sum(sum(v) for v in by_inst.values()) / k
        # between-instance variance of the per-instance rates, corrected for the
        # binomial noise that a finite number of repeats contributes to each p_i
        raw_between = sum((x - pbar) ** 2 for x in pis) / max(len(pis) - 1, 1)
        within = sum(x * (1 - x) for x in pis) / max(len(pis), 1)
        between = max(raw_between - within / samples, 0.0)
        icc = between / (between + within) if (between + within) > 0 else 0.0
        always = sum(1 for x in pis if x == 1.0)
        never = sum(1 for x in pis if x == 0.0)
        split = len(pis) - always - never
        print(f"{t:>5} {pbar:>7.2f} {between:>9.4f} {within:>8.4f} {icc:>6.2f} "
              f"{always:>7} {never:>6} {split:>6}")
    print("\nbetween = variance across instances (problem difficulty)")
    print("within  = variance across repeats of the same problem (sampling)")
    print("ICC     = fraction of variance that is problem difficulty")
    print("always/never/split = instances correct every time / never / sometimes")


@app.local_entrypoint()
def grid(model: str = "Qwen/Qwen3-4B", gpu: str = "l40s", thinking: str = "true",
         lo: int = 2, hi: int = 12, n_live: int = 45, n_saturated: int = 10,
         temperature: float = 0.7, top_p: float = 1.0,
         n_lo: int = 10, n_hi: int = 50, chunk: int = 256,
         sweep_id: str = "grid", axes: str = "", budget_mode: str = "max",
         cells_spec: str = "", order_seed: str = "", dry_run: str = "false"):
    """The deliverable: x = digits of A, y = digits of B, z = P(exactly correct).

    Two things this does that the earlier entrypoints got wrong.

    ONE BIG QUEUE. `variance` submitted one RPC per repeat -- 20 generations at
    a time -- so the GPU sat mostly idle and cost ~3.5s per generation. Here the
    whole grid becomes one flat job list, shuffled so long and short problems
    interleave, then chunked into large batches. A full batch is the difference
    between roughly $0.30 and $5.30 for the same work.

    ADAPTIVE n BY PREDICTED DIFFICULTY, NOT BY OBSERVED RATE. Cells are given
    n_live or n_saturated based on N = a*b against a band predicted from the
    Stage 1 scan. Deciding from the observed rate would be a data-dependent
    stopping rule, which biases cells just below the boundary down and just
    above it up -- sharpening the very cliff the grid exists to locate.
    """
    # ALWAYS the full square. (a,b) and (b,a) are different problems for a
    # language model -- "3 x 12" and "12 x 3" are different token sequences and
    # invite different procedures (3 partial products vs 12). Folding the grid
    # on an assumed symmetry would erase the asymmetry it is meant to measure,
    # and the asymmetry across the diagonal is visible in the heatmap itself.
    # Not a flag: an option to fold is an option to get this wrong.
    # `axes` gives an explicit sparse axis list, e.g. "2,5,8,11" -> 16 cells.
    # Without it, lo..hi builds the dense square. The dense default is what a
    # sparse plan would silently get, so the plan must pass axes explicitly.
    if cells_spec.strip():
        cells = [tuple(int(v) for v in c.split("x"))
                 for c in cells_spec.split(",")]
        vals = sorted({v for c in cells for v in c})
    else:
        vals = ([int(v) for v in axes.split(",")] if axes.strip()
                else list(range(lo, hi + 1)))
        cells = [(a, b) for a in vals for b in vals]

    jobs = []
    for (a, b) in cells:
        N = a * b
        n = n_live if n_lo <= N <= n_hi else n_saturated
        got = make_problems(a, b, n)
        for j in got:
            j["_n_in_cell"] = n      # the CELL's n, not the batch's count
        jobs += got
    # Seeded shuffle, NOT a systematic sort. Submission position measurably
    # affects output (the odd repeat was sample_idx 0 in 11 of 11 cases), so a
    # systematic order lets an engine-state effect masquerade as a capability
    # curve. The seed is fixed and model-independent, so every model sees the
    # SAME scrambled order and any residual order effect is common to both and
    # cancels in the paired comparison. Position is recorded so it stays
    # testable rather than merely diluted.
    # The order seed must NOT be the sweep_id: two models run under different
    # sweep ids would then get different submission orders, and submission
    # position measurably affects output (methods 5). Same seed -> same order
    # -> the order effect is common to both and cancels in the comparison.
    random.Random(f"order-{order_seed or 'shared'}").shuffle(jobs)
    for i, j in enumerate(jobs):
        j["_pos"] = i

    est_tok = sum(505.2 * (j["a"] * j["b"]) ** 0.714 for j in jobs)
    if dry_run.lower() == "true":
        usd = est_tok / 4032 * (0.001097 if gpu == "h100" else 0.000542)
        print(f"DRY RUN — nothing will be spent")
        print(f"  cells       {len(cells)}  {sorted(cells)[:6]}{' ...' if len(cells)>6 else ''}")
        print(f"  generations {len(jobs)}")
        print(f"  chunks      {(len(jobs) + chunk - 1) // chunk} of {chunk}")
        print(f"  est tokens  {est_tok/1e6:.2f}M")
        print(f"  est cost    ${usd:.2f}  (+ cold start ~$0.12)")
        return []
    mpath = write_manifest(
        sweep_id, model=model, gpu=gpu, thinking=thinking,
        order_seed=order_seed or "shared",
        budget_mode=budget_mode, temperature=temperature, top_p=top_p,
        axes=vals, cells=[list(c) for c in cells], n_live=n_live,
        n_saturated=n_saturated, n_lo=n_lo, n_hi=n_hi, chunk=chunk,
        n_planned=len(jobs),
        cost={"est_output_tokens": round(est_tok),
              "est_usd": round(est_tok / 4032 * (0.001097 if gpu == "h100"
                                                 else 0.000542), 3),
              "actual_usd": None})
    print(f"{len(cells)} cells, {len(jobs)} generations, "
          f"chunks of {chunk} -> {(len(jobs) + chunk - 1) // chunk} batches")
    print(f"manifest: {mpath}   est {est_tok/1e6:.2f}M tok")

    p = PROBES[gpu](model=model)
    total, tok, batches = [], 0, []
    for i in range(0, len(jobs), chunk):
        part = jobs[i:i + chunk]
        out = p.run.remote(part, temperature=temperature, top_p=top_p,
                           thinking=thinking.lower() == "true",
                           sweep_id=sweep_id, sample_idx=0,
                           budget_mode=budget_mode)
        total += out["records"]
        tok += out["total_completion_tokens"]
        # save每 chunk: a stop costs one batch, not the sweep
        _save(out["records"], f"{sweep_id}-{model.split('/')[-1]}-part{i // chunk:03d}")
        done = min(i + chunk, len(jobs))
        batches.append({"batch": i // chunk, "n": len(out["records"]),
                        "wall_s": out["batch_wall_seconds"],
                        "tokens": out["total_completion_tokens"]})
        rate = out["total_completion_tokens"] / max(out["batch_wall_seconds"], 1)
        print(f"  {done}/{len(jobs)}  {out['batch_wall_seconds']:.0f}s  "
              f"{rate:.0f} tok/s  {out['total_completion_tokens']} tok")
    wall = sum(m for m in [0])  # placeholder; batches carry their own timing
    close_manifest(mpath, n_actual=len(total), actual_output_tokens=tok,
                   batches=batches)
    print(f"\ntotal {len(total)} generations, {tok} output tokens")
    print(f"manifest closed: {mpath}")
    return total


@app.local_entrypoint()
def symmetry(model: str = "Qwen/Qwen3-4B", gpu: str = "l40s",
             cells: str = "3x9,4x8,2x12,5x7", n: int = 40,
             temperature: float = 0.7, thinking: str = "true"):
    """Does P(a x b) equal P(b x a)?

    If order matters the grid cannot be folded, and it is a finding in itself:
    longhand multiplication is not symmetric in procedure. Multiplying 9999 by 2
    is one partial product; multiplying 2 by 9999 invites four. Which operand is
    written first may change the algorithm the model reaches for.

    The test uses the SAME operand pair in both orders -- x*y and y*x -- so the
    comparison is paired per instance. Drawing separate problems for cell (a,b)
    and cell (b,a) would confound order with instance difficulty and could not
    detect anything.

    Reported as McNemar on the discordant pairs, which is the correct test for
    paired binary outcomes.
    """
    pairs = []
    for spec in cells.split(","):
        a, b = (int(v) for v in spec.strip().split("x"))
        base = make_problems(a, b, n)
        for j in base:
            fwd = dict(j)
            rev = dict(j, a=j["b"], b=j["a"], x=j["y"], y=j["x"])
            rev["instance_id"] = j["instance_id"]
            pairs.append((fwd, rev))

    jobs = [p[0] for p in pairs] + [p[1] for p in pairs]
    random.Random("order-sym").shuffle(jobs)   # order must not track direction
    for i, j in enumerate(jobs):
        j["_pos"] = i

    p = PROBES[gpu](model=model)
    out = p.run.remote(jobs, temperature=temperature, top_p=1.0,
                       thinking=thinking.lower() == "true", sweep_id="sym")
    recs = out["records"]
    _save(recs, f"symmetry-{model.split('/')[-1]}-{gpu}")

    by = {}
    for r in recs:
        by[(r["a"], r["b"], r["instance_id"])] = r["correct"]

    print(f"\n{'cell':>10}{'fwd':>7}{'rev':>7}{'both':>6}{'fwd only':>10}"
          f"{'rev only':>10}{'McNemar p':>11}")
    for spec in cells.split(","):
        a, b = (int(v) for v in spec.strip().split("x"))
        n11 = n10 = n01 = n00 = 0
        for i in range(n):
            f_, r_ = by.get((a, b, i)), by.get((b, a, i))
            if f_ is None or r_ is None:
                continue
            n11 += f_ and r_; n10 += f_ and not r_
            n01 += (not f_) and r_; n00 += (not f_) and (not r_)
        d = n10 + n01
        # exact two-sided binomial on the discordant pairs
        pv = 1.0
        if d:
            from math import comb
            k = min(n10, n01)
            pv = min(1.0, 2 * sum(comb(d, i) for i in range(k + 1)) / 2 ** d)
        tot = n11 + n10 + n01 + n00
        print(f"{a:>4}x{b:<5}{(n11+n10)/max(tot,1):>7.2f}{(n11+n01)/max(tot,1):>7.2f}"
              f"{n11:>6}{n10:>10}{n01:>10}{pv:>11.3f}")
    print("\nSmall p = order matters = the grid CANNOT be folded.")


@app.local_entrypoint()
def throughput(model: str = "Qwen/Qwen3-4B", gpu: str = "h100",
               chunks: str = "48,128,256", thinking: str = "true",
               temperature: float = 0.7):
    """Does throughput scale with batch size? The whole budget rests on this.

    Every cost projection so far uses 1131 tok/s, measured from ONE batch of 48
    on an H100. The grid submits chunks of 256. If larger batches reach 2000+
    tok/s the two-model reasoning-on grid becomes affordable; if they do not,
    the plan has to change. One container, several batch sizes, same cells.

    Cells are drawn across the live band so the mix of short and long
    generations matches what the real grid would submit.
    """
    # smaller cells keep the test inside $1 while still spanning the mix of
    # short and long generations the real grid submits
    sizes = [(3, 4), (4, 5), (5, 6), (6, 6)]
    p = PROBES[gpu](model=model)
    think = thinking.lower() == "true"
    print(f"\n{'batch':>7}{'gens':>7}{'wall s':>9}{'out tok':>10}"
          f"{'tok/s':>9}{'s/gen':>8}{'$/1k gens':>11}")
    usd_s = 0.001097 if gpu == "h100" else 0.000542
    recs = []
    for c in [int(x) for x in chunks.split(",")]:
        jobs = []
        i = 0
        while len(jobs) < c:                       # cycle the cells to fill
            a, b = sizes[i % len(sizes)]
            jobs += make_problems(a, b, 1)[:1]
            jobs[-1]["instance_id"] = i
            i += 1
        random.Random(f"tp-{c}").shuffle(jobs)
        for k, j in enumerate(jobs):
            j["_pos"] = k
        out = p.run.remote(jobs, temperature=temperature, top_p=1.0,
                           thinking=think, sweep_id=f"tp{c}")
        w = out["batch_wall_seconds"]; t = out["total_completion_tokens"]
        recs += out["records"]
        print(f"{c:>7}{len(out['records']):>7}{w:>9.0f}{t:>10,}"
              f"{t / max(w, 1):>9.0f}{w / max(len(out['records']), 1):>8.1f}"
              f"{w / max(len(out['records']), 1) * 1000 * usd_s:>11.2f}")
    _save(recs, f"throughput-{model.split('/')[-1]}-{gpu}")
    print("\nIf tok/s rises with batch size, the grid is cheaper than projected.")


# --------------------------------------------------------------------------
# Manifest. AGENTS.md: "analysis reads a manifest, never a filename", and
# "estimate cost before launching, record actual cost after".
# --------------------------------------------------------------------------
def write_manifest(sweep_id, model=None, **fields):
    """Written BEFORE the first generation. status='open' until closed.

    A run whose parameters live only in its filename is an anecdote: the
    predecessor project had to replay an RNG to recover which problem produced
    which trace. Everything needed to reconstruct this run goes here.
    """
    import pathlib
    import subprocess

    d = pathlib.Path(__file__).resolve().parent.parent / "sweeps" / sweep_id
    d.mkdir(parents=True, exist_ok=True)
    # one manifest per (sweep, model). A sweep legitimately spans models -- the
    # shared order seed is the whole point -- so keying on sweep_id alone made
    # the second model silently overwrite the first model's manifest.
    name = f"manifest-{model.split('/')[-1]}.json" if model else "manifest.json"
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, cwd=d).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"],
                                    capture_output=True, text=True,
                                    cwd=d).stdout.strip())
    except Exception:
        sha, dirty = "unknown", None
    m = {"sweep_id": sweep_id, "model": model, "status": "open",
         "schema_version": 2,
         "code_git_sha": sha, "code_git_dirty": dirty,
         "prompt_text": PROMPT,
         "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest()[:16],
         "problem_pool_size": POOL, "problem_seed": 20260730,
         "engine": {"vllm": "0.11.0", "transformers": "4.57.0"},
         "batches": [], **fields}
    (d / name).write_text(json.dumps(m, indent=2))
    return d / name


def close_manifest(path, **fields):
    """Called after the last batch. Records what ACTUALLY happened."""
    import pathlib

    p = pathlib.Path(path)
    m = json.loads(p.read_text())
    m.update(status="closed", **fields)
    p.write_text(json.dumps(m, indent=2))

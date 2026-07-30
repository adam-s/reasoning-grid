# References and sources

Every external source consulted for the experiment design, with what it was
used for and how much it should be trusted. Sources are rated:

- **primary** — the vendor's own docs, model card, or code. Trust for facts
  about that thing.
- **secondary** — technical writing by someone with hands-on knowledge.
- **aggregator** — SEO listicle or price-comparison site. Directionally useful,
  frequently stale or wrong on detail. Never cite one for a number that matters
  without checking the primary source.

The prior-art review agent is still running. Its findings get appended in
Section 5 when it reports.

---

## 1. Measured directly, not cited

The most important inputs to this design were measured locally rather than
read. They need no citation and supersede any secondary claim about the same
thing.

| Fact | How obtained | Date |
| --- | --- | --- |
| Qwen2.5, Qwen3, Mistral v0.3 tokenize numbers one digit per token | loaded each tokenizer, encoded 1-15 digit strings | 2026-07-30 |
| gpt-oss groups digits in threes, left-aligned, context-independent | same, across 5 prompt contexts | 2026-07-30 |
| Gemma 3 and Llama 3.1 repos are `gated=manual` | HF API `/api/models/<id>` | 2026-07-30 |
| Qwen3-4B: 3/3 correct at 3x3 digits, 1/3 at 4x4 | vLLM on Modal L40S | 2026-07-30 |
| Qwen3-4B uses ~20-25 output tokens per single-digit product (thinking off) | same run | 2026-07-30 |
| L40S + Qwen3-4B: 30.93 GiB KV cache, 225,232 tokens, 6.87x concurrency at 32K | vLLM startup log | 2026-07-30 |

---

## 2. Modal — pricing and platform

Used for the cost model in the design doc. Per-second rates were cross-checked
across three aggregators that agreed; they should still be confirmed against
Modal's own pricing page before a large run.

- [Modal Pricing | UsagePricing](https://www.usagepricing.com/blueprint/modal) — aggregator. Per-second rates: A10 $0.000306, L40S $0.000542, A100-40GB $0.000583, A100-80GB $0.000694, H100 $0.001097.
- [Modal Pricing 2026 | CostBench](https://costbench.com/software/ai-gpu-cloud/modal/) — aggregator. Claims fact-checked 2026-07-14. Source of the "$30/month free compute credit" claim, which was NOT verified against the account and should not be relied on.
- [Modal GPU Pricing | ComputePrices](https://computeprices.com/providers/modal) — aggregator.
- [Modal Pricing Calculator | BuildMVPFast](https://www.buildmvpfast.com/tools/api-pricing-estimator/modal) — aggregator.
- [Modal Pricing Explained | Beam](https://www.beam.cloud/blog/modal-pricing-explained) — aggregator, and a competitor to Modal. Treat its framing as adversarial.
- [Best Modal Alternatives 2026 | BuildMVPFast](https://www.buildmvpfast.com/alternatives/modal) — aggregator.
- [GPU Price Comparison 2026](https://altstreet.investments/tools/gpu/gpu-price-comparison) — aggregator.

**Caveat.** No Modal primary pricing page was fetched. Every rate above traces
to aggregators. They agree with each other, which is weak evidence, since they
may share a source.

---

## 3. Models

### gpt-oss-20b (OpenAI)

- [openai/gpt-oss-20b · discussion 136](https://huggingface.co/openai/gpt-oss-20b/discussions/136) — **primary-adjacent**. Users reporting failure to load on dual L40 48GB with vLLM. Directly relevant: the L40S is the same Ada generation, and this is the main risk to the OpenAI side of the comparison.
- [gpt-oss: How to Run Guide | Unsloth](https://unsloth.ai/docs/models/gpt-oss-how-to-run-and-fine-tune) — secondary, generally reliable on quantization detail.
- [Hardware Requirements for gpt-oss-20b | IntuitionLabs](https://intuitionlabs.ai/articles/hardware-requirements-gpt-oss-20b) — secondary. ~47GB for FP16, ~12GB at INT4.
- [gpt-oss-20b VRAM Requirements | Spheron](https://www.spheron.network/tools/gpu-recommender/openai/gpt-oss-20b/) — aggregator.
- [GPT-OSS 20B VRAM Requirements | WillItRunAI](https://willitrunai.com/models/gpt-oss-20b) — aggregator.
- [GPT-OSS deployment compute | CometAPI](https://www.cometapi.com/how-much-computing-power-is-required-for-gpt-oss-deployment/) — aggregator.

### Qwen3 (Alibaba)

- [Qwen/Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B) — **primary**. Model card.
- [Qwen/Qwen3-8B-FP8](https://huggingface.co/Qwen/Qwen3-8B-FP8) — primary.
- [Qwen/Qwen3-8B-GGUF](https://huggingface.co/Qwen/Qwen3-8B-GGUF) — primary.
- [Qwen/Qwen3-30B-A3B](https://huggingface.co/Qwen/Qwen3-30B-A3B) — primary.
- [Qwen Quickstart docs](https://qwen.readthedocs.io/en/latest/getting_started/quickstart.html) — **primary**.
- [Qwen3-8B-Instruct model card (NVIDIA)](https://developer.nvidia.com/downloads/assets/ace/model_card/qwen3-8b-instruct.pdf) — secondary, third-party redistribution.
- [Qwen3.5 Thinking Mode Parameters | BSWEN](https://docs.bswen.com/blog/2026-03-24-qwen35-thinking-mode-parameters/) — secondary. Source of the recommended sampling parameters used in the design: thinking mode temp 0.6 / top_p 0.95 / top_k 20; non-thinking temp 0.7 / top_p 0.8 / top_k 20. **Should be re-checked against the Qwen model card before the real run** — these numbers drive every generation.
- [Qwen/Qwen3.6-27B · discussion 10](https://huggingface.co/Qwen/Qwen3.6-27B/discussions/10) — primary-adjacent. Indicates newer Qwen generations exist; version numbers in this design need confirming before pinning.
- [Qwen3-Next Run Locally | Unsloth](https://unsloth.ai/docs/models/tutorials/qwen3-next) — secondary.

---

## 4. vLLM

- [vLLM docs](https://docs.vllm.ai/) — **primary**.
- [Reasoning Outputs | vLLM](https://docs.vllm.ai/en/latest/features/reasoning_outputs/) — **primary**. The reasoning-parser feature that splits `reasoning_content` from `content`. Relevant to the data-capture design, which stores both raw and split.

---

## 5. Open-model landscape (July 2026)

Used only to build the candidate list. All aggregator quality; the actual
selection was made by measuring tokenizers and querying the HF API directly, not
from these.

- [Best Open Source and Open-Weight LLMs to Run Locally 2026 | HF blog](https://huggingface.co/blog/daya-shankar/open-source-llm-models-to-run-locally)
- [Best Open-Source LLM Models in 2026 | HF blog](https://huggingface.co/blog/daya-shankar/open-source-llms)
- [Open Source LLM Comparison Table 2026 | ComputingForGeeks](https://computingforgeeks.com/open-source-llm-comparison/)
- [Best Open-Source LLMs July 2026 | AceCloud](https://acecloud.ai/blog/best-open-source-llms/)
- [Best Open-Weight AI Models 2026 | Kingy](https://kingy.ai/news/best-open-weight-ai-models-in-2026-glm-5-2-vs-deepseek-v4-vs-kimi-k2-6-vs-qwen-vs-mistral/)
- [Which Open-Weight Model Should a Pleb Self-Host? | d-central](https://d-central.tech/best-local-llm-2026-pleb-open-weight-model-guide/)
- [Best Open-Source AI Models 2026 | TechJack](https://techjacksolutions.com/ai-tools/open-source/best-open-source-ai-models/)
- [Best Open-Source LLMs July 2026 Leaderboard | Techsy](https://techsy.io/en/blog/best-open-source-llms-2026)
- [Open-Source LLMs Compared 2026 | Till Freitag](https://till-freitag.com/en/blog/open-source-llm-comparison)
- [Best Open Source LLMs July 2026 | Thunder Compute](https://www.thundercompute.com/blog/best-open-source-llms)

Names that surfaced and were not pursued: GLM-5.2, DeepSeek V4, Kimi K2.7,
Nemotron 3 Super, Gemma 4 12B, Mistral Small 4. All either too large for the
budget or gated.

---

## 6. Internal prior work (not external, but load-bearing)

- `~/Projects/agent-capability-threshold` — the predecessor project. Its
  `statistics/explorations/19_mathematical_framework/README.md` is where
  `p_arith ~= 97%` was derived by inverting an assumed formula, which is the
  circularity this project exists to break.
- `https://adamsohn.com/reliably-incorrect/` — the published essay this work
  owes evidence to. Source lives at `~/Projects/agent-capability-threshold/web`.
- `~/Projects/goblins/goblins-takehome/infra/modal/qwen_grader.py` — origin of
  the vLLM 0.11.0 + transformers 4.57.0 pin and the Modal cost guardrails.
- `~/Projects/car-diagnosis/src/cardiag/modal/modal_qwen.py` — the batch
  jsonl-in/jsonl-out Modal pattern this probe follows.

---

## 7. Academic prior art

Found 2026-07-30. Read this section before writing any claim of novelty. Four
of these papers each independently pre-empt a piece of the design.

### 7.1 The period-3 tokenizer finding is already published

**AI-rithmetic** — Bie, Dick, Kulesza, Raghavan, Raman, Vassilvitskii (Google),
Feb 2026, ICLR ICBINB workshop. <https://arxiv.org/abs/2602.10416>

Ran a discrete Fourier transform over error rate against argument length, 1-100
digits, 100 problems per length. Found a pronounced 1/3 frequency spike for
models with 3-digit tokenizer grouping (GPT-5, GPT-4o, Claude Opus 4.1) and no
spike for single-digit tokenizers. Identifies the tiktoken pre-tokenization
regex as the cause, by name.

This is our registered prediction, its mechanism, and the 3-digit versus
1-digit contrast, published five months earlier with a sharper instrument than
a residual map. **Our version is a replication.**

What they did not do: multiplication (addition only), and no gpt-oss or Qwen
(their only open model was Gemma 3 27B).

The same paper also reports geometrically distributed first-error positions
matching `P = (1-p)^n`, which pre-empts the survival-analysis framing for
addition.

### 7.2 The multiplication grid was published in 2023

**Faith and Fate: Limits of Transformers on Compositionality** — Dziri et al.,
NeurIPS 2023. <https://arxiv.org/abs/2305.18654> ·
code <https://github.com/nouhadziri/faith-and-fate>

GPT-4 zero-shot: 59% at 3x3 digits, 4% at 4x4, 0% at 5x5. Formulates
multiplication as a computation graph, measures accuracy per node and per
layer, and separates **local error** (a wrong single step) from **propagation
error** (a correct step applied to wrong inputs).

That local/propagation split is the same decomposition as our two `p_step`
estimates. The repo ships a multiplication generator, a scratchpad
computation-graph builder, and the error-analysis code.

### 7.3 Cross-model agreement as a verifier is answered, and the answer is no

**When LLMs Agree, Are They Right?** — Kaihua Ding (UPenn), July 2026.
<https://arxiv.org/abs/2607.08065>

265,000 samples across GPQA Diamond and AIME, GPT-4.1 against three Claude
tiers on shared items. When both providers are wrong they pick the *same* wrong
answer well above chance (67%, p=.003 for one pairing; 71%, p=.005 for
another), with high confidence. Concludes cross-family agreement does not
certify correctness, because shared pretraining data produces shared bias
rather than independent confirmation.

**Wisdom and Delusion of LLM Ensembles for Code Generation and Repair** —
Vallecillos-Ruiz, Hort, Moonen. <https://arxiv.org/html/2510.21513>

On Defects4J the best single model solves 112 problems against an oracle
ensemble ceiling of 205. Names the **"popularity trap"**: models converge on the
same incorrect solution, and consensus selection performs worse than a naive
baseline. Diversity-based selection captures up to 95% of the ceiling.

This is the coding-agent deployment question, measured on actual coding
benchmarks rather than inferred from arithmetic.

### 7.4 Diversity metrics are confounded with capability

**Are Diversity Metrics Measuring Diversity? A Capability-Controlled Audit of
Majority-Vote Gain in LLM Ensembles** — Donghwan Kim, July 2026.
<https://arxiv.org/html/2607.20768>

31,900 subsets over 30 models on MMLU-Pro. "Strict diversity" correlates with
one minus mean accuracy at rho = +0.991 — capability explains ~98.9% of its
variance. Raw correlations with majority-vote gain reverse sign under
capability control. Also finds more accurate models are *more* error-correlated,
and that majority vote beats the strongest member in only 9.98% of size-3
ensembles.

Our planned "observed n11 against `n·p_A·p_B`" chart is in exactly the family
this audit shows is confounded.

### 7.5 Constant per-step accuracy is already known to be false

**The Illusion of Diminishing Returns: Measuring Long Horizon Execution in
LLMs** — Sinha, Arun, Goel, ICLR 2026. <https://arxiv.org/abs/2509.09677>

States the `p^N` assumption and then breaks it: per-step error rate *rises* as
the task progresses. Isolates **self-conditioning** — models become more
error-prone once their own errors are in context — by scrubbing errors from
history and showing degradation persists. Reports that thinking mitigates it.

**Beyond Exponential Decay: Rethinking Error Accumulation in LLMs** — Arbuzov,
Bei, Dong, Kalaev, Shvets. <https://arxiv.org/pdf/2505.24187>

A direct theoretical and empirical rebuttal of `P = p^N`.

Curvature in `ln P vs N` is therefore the expected result with a named
mechanism, not the open question our design called it.

### 7.6 The tokenizer prediction as written is mis-specified

**Tokenization Counts: The Impact of Tokenization on Arithmetic in Frontier
LLMs** — Singh & Strouse. <https://arxiv.org/html/2402.14903>

Right-to-left versus left-to-right digit grouping: 75.6% to 97.8% on GPT-3.5,
84.4% to 98.9% on GPT-4. The isolated mechanism is **misalignment between
operand tokenization and answer tokenization**, not periodicity in operand
length. L2R is far worse when the answer is longer than the operands, dropping
to 8.25% in length-mismatch cases.

For an a-digit by b-digit product the answer has a+b or a+b-1 digits, so
alignment depends on all three lengths. Our prediction table indexes only on
operand digit count, and the alignment effect is far larger than the ripple we
were looking for.

### 7.7 Digit composition is a first-class factor, not a footnote

**Multiplication in Multimodal LLMs: Computation with Text, Image, and Audio
Inputs** — Balter, Jerzak, Jerzak, Apr 2026. <https://arxiv.org/abs/2604.18203>

Defines **arithmetic load** `C` = product of total and non-zero digit count.
Accuracy falls sharply as C grows, near zero by C > 100, with R-squared often
above 0.5 — close to what explicit intermediate-step counting achieves. Ships a
paired-instance reproducible generator.

`N = a·b` ignores zeros entirely, and a 7x7 problem with three zeros is not the
same difficulty as one made of 8s and 9s. This paper says non-zero digit count
carries as much signal as digit count.

### 7.8 Blind spots are probably instance-level, not size-level

**Arithmetic Without Algorithms: Language Models Solve Math with a Bag of
Heuristics** — Nikankin, Reusch, Mueller, Belinkov, ICLR 2025.
<https://arxiv.org/abs/2410.21272>

**Benford's Curse: Tracing Digit Bias to Numerical Hallucination in LLMs** —
NeurIPS 2025. <https://arxiv.org/abs/2506.01734>. Accuracy is noticeably higher
for small digits (1, 2) than large ones (8, 9), traced to digit-selective FFN
neurons and Benford-distributed pretraining data.

**Language Models Do Hard Arithmetic Tasks Easily and Hardly Do Easy Arithmetic
Tasks** — <https://arxiv.org/pdf/2406.02356>. Models confidently get the *first*
digit of a product right and fail on the last.

If arithmetic is a pattern-keyed heuristic bag with a strong digit-value prior,
a hole lives at particular operand *values*, not at a digit-count cell. A
residual map over (a, b) marginalizes the variable the mechanism keys on.

### 7.9 Single-prompt grids do not generalize

**Can We Count on LLMs? The Fixed-Effect Fallacy and Claims of GPT-4
Capabilities** — <https://arxiv.org/pdf/2409.07638>

**State of What Art? A Call for Multi-Prompt LLM Evaluation** —
<https://arxiv.org/html/2401.00595v3>

Meaning-preserving formatting changes move results materially. A grid built on
one prompt template is a property of that template.

### 7.10 Contamination at the small end

<https://arxiv.org/pdf/2502.17521> — Qwen 2.5's MATH-500 performance was found
heavily reliant on response templates and structural cues, requiring a
synthetic post-release set for a clean read. Qwen3 is one of our two models,
and the 2x2 through 4x4 region overlaps published multiplication tables. Those
cells anchor any fit through the origin.

### 7.11 Also noted

- **Why Can't Transformers Learn Multiplication?** <https://arxiv.org/abs/2510.00184>
- **Cross-Model Disagreement** <https://arxiv.org/html/2603.25450>

---

## 8. Existing tooling that should be reused rather than rewritten

- [faith-and-fate](https://github.com/nouhadziri/faith-and-fate) — multiplication
  generator, scratchpad computation-graph builder, per-step local/propagation
  error analysis. Covers most of the planned `problems.py` and step harvester.
- [videlalvaro/llm-arithmetic-internals](https://github.com/videlalvaro/llm-arithmetic-internals)
  — strict no-parser controls, reproducible audits, manifest verification and
  replay bundles. That is the planned `manifest.py` and the Stage 0 gate.
- [math401-llm](https://github.com/GanjinZero/math401-llm) — MATH 401, includes
  integer multiplication within 100 and within 100,000, with per-group accuracy
  across model families.
- [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness) ·
  [math-evaluation-harness](https://github.com/ZubinGou/math-evaluation-harness)
  — vLLM batching, answer extraction, result serialization.

---

## 9. Operational issues found in vendor trackers

- [vllm#38022](https://github.com/vllm-project/vllm/issues/38022) — Marlin MXFP4
  MoE kernel fails for gpt-oss-20b because `hidden_size = intermediate_size =
  2880` is not divisible by 128. **This blocks gpt-oss-20b on L40S/Ada.**
- [vLLM GPT-OSS recipe](https://docs.vllm.ai/projects/recipes/en/stable/OpenAI/GPT-OSS.html)
  — supported NVIDIA hardware listed as H100, H200, B200 only.
- [vllm#22287](https://github.com/vllm-project/vllm/issues/22287) — gpt-oss-20b
  emits reserved tokens on roughly 12-15% of requests under vLLM.
- [gpt-oss-20b discussion 149](https://huggingface.co/openai/gpt-oss-20b/discussions/149)
  and [28](https://huggingface.co/openai/gpt-oss-20b/discussions/28) —
  `reasoning_effort: low` ignored, reasoning content still streams.
- [vllm#38894](https://github.com/vllm-project/vllm/issues/38894) and
  [vllm#27118](https://github.com/vllm-project/vllm/issues/27118) — Qwen3
  reasoning-parser bugs where content lands entirely in the reasoning field.
- [openai/gpt-oss](https://github.com/openai/gpt-oss) — vendor-recommended
  sampling for gpt-oss is temperature 1.0 / top_p 0.95, against Qwen3 thinking
  at 0.6 / 0.95 / top_k 20. Running each at its own recommendation hands one
  model a 0.4 temperature advantage, which alone produces asymmetric off-diagonal
  cells in a McNemar table.

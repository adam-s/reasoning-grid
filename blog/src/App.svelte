<script lang="ts">
  // SCAFFOLD. Composes <Section> blocks, one per beat of the argument.
  // Figures are real components now; see blog/README.md for which committed
  // chart each one ports from.
  import Layout from './lib/components/Layout.svelte';
  import Section from './lib/components/Section.svelte';
  import Prose from './lib/components/Prose.svelte';
  import Figure from './lib/components/Figure.svelte';
  import { onMount } from 'svelte';
  import IterationRings from './lib/viz/opener/IterationRings.svelte';
  import Dogfight from './lib/viz/opener/Dogfight.svelte';
  import SyncedTrace from './lib/viz/opener/SyncedTrace.svelte';
  import MomentLinks from './lib/viz/opener/MomentLinks.svelte';
  import Cue from './lib/viz/opener/Cue.svelte';
  import ThinkingMix from './lib/viz/opener/ThinkingMix.svelte';
  import GridKey from './lib/viz/opener/GridKey.svelte';
  import SurfaceCanvas from './lib/viz/surface/SurfaceCanvas.svelte';
  import BoundaryWedge from './lib/viz/surface/BoundaryWedge.svelte';
  import AllocationGrid from './lib/viz/surface/AllocationGrid.svelte';
  import DistributionPanels from './lib/viz/surface/DistributionPanels.svelte';

  /**
   * The four characters of the Wrong run that carry this page's argument, in
   * the order they happen. Offsets are character positions in that run's
   * response, which is the same string the flame graph indexes, so they are
   * checkable against the data rather than eyeballed.
   *
   * Run 1 is "Wrong". It adds 371,499,719,344,600 and 80,379,530, gets
   * 371,499,719,424,970, re-derives the same sum twice more calling it correct
   * both times, and answers with it.
   */
  const WRONG_RUN = 1;
  const WRONG_MOMENTS = [
    { id: 'w-enters', run: WRONG_RUN, at: 5511, label: 'the wrong sum' },
    { id: 'w-check-1', run: WRONG_RUN, at: 6317, label: 'it checks' },
    { id: 'w-check-2', run: WRONG_RUN, at: 6510, label: 'it checks again' },
    { id: 'w-answer', run: WRONG_RUN, at: 16367, label: 'it answers' },
  ];

  /**
   * Run 2 is "Caught", and it is the same machinery ending the other way. It
   * works the product two ways, the two disagree, it stops, finds the slip in
   * 19,705,117 x 7.5, and finishes correct despite three wrong steps along the
   * way.
   */
  const CAUGHT_RUN = 2;
  const CAUGHT_MOMENTS = [
    { id: 'c-disagree', run: CAUGHT_RUN, at: 15698, label: 'two answers disagree' },
    { id: 'c-stop', run: CAUGHT_RUN, at: 15992, label: 'it stops' },
    { id: 'c-slip', run: CAUGHT_RUN, at: 16808, label: 'it finds the slip' },
    { id: 'c-answer', run: CAUGHT_RUN, at: 19604, label: 'it answers correctly' },
  ];

  /**
   * Both "Walk it from the start" buttons drive a figure, and both figures need
   * JavaScript to exist. Prerendering means the prose ships without it, so
   * without this flag a reader with JavaScript off gets the navy button and its
   * hand-drawn cue sitting above an empty box -- the loudest ink on the screen
   * pointing at the one thing that cannot happen.
   */
  let interactive = $state(false);
  onMount(() => {
    interactive = true;
  });

  /** Owned here, not in the figure: the figure reports, the prose renders. */
  let synced: ReturnType<typeof SyncedTrace> | null = $state(null);
  let momentGroup: HTMLDivElement | null = $state(null);
  let momentBusy = $state(false);
  let moment: string | null = $state(null);

  /**
   * ---- THE TOUR ------------------------------------------------------------
   *
   * One cue, pointing at one control, walking the reader through both rows in
   * order. Three states and nothing else, because the failure mode here is a
   * pile of booleans that can express situations the interface cannot survive.
   *
   *   unstarted  nothing pressed yet. The cue sits on the start button.
   *   at(i)      the reader is standing on TOUR[i]. The cue sits on TOUR[i+1],
   *              and on nothing once i is the last.
   *   off        the reader went their own way. NO CUE, EVER AGAIN.
   *
   * `off` is terminal on purpose. A cue that reappears after being ignored is
   * nagging, and a reader who clicked step four directly has told you they do
   * not want to be walked. There is no transition back; pressing start again is
   * the only way to be led, and that is a decision they make rather than one
   * the page makes for them.
   *
   * TWO SIGNALS, ONE SHAPE. The figure reports a cleared moment both when a new
   * one is starting and when the reader takes the cursor back, and both arrive
   * as onMoment(null). The busy flag is the only thing that tells them apart,
   * which is why the figure raises busy first. Read that comment before
   * changing either callback.
   */
  const TOUR = [...CAUGHT_MOMENTS, ...WRONG_MOMENTS];

  type Tour =
    | { kind: 'unstarted' }
    | { kind: 'at'; index: number }
    | { kind: 'off' };

  let tour: Tour = $state({ kind: 'unstarted' });

  /** The one control wearing the cue, or null for none. */
  const cueTarget = $derived.by(() => {
    // Never point at a disabled control. The whole row is disabled while the
    // figure is mid-flight, and an arrow on a button that cannot be pressed
    // reads as a broken page.
    if (momentBusy) return null;
    if (tour.kind === 'unstarted') return 'start';
    if (tour.kind === 'at') return TOUR[tour.index + 1]?.id ?? null;
    return null;
  });

  const cueText = $derived(
    cueTarget === 'start' ? 'start here'
      : cueTarget === WRONG_MOMENTS[0].id ? 'now this run'
      : 'next',
  );

  /** A moment landed. Either it is the one the tour asked for, or the reader
   *  is driving and the tour steps out of the way. */
  function arrived(id: string) {
    const i = TOUR.findIndex((m) => m.id === id);
    const expected =
      tour.kind === 'unstarted' ? 0 : tour.kind === 'at' ? tour.index + 1 : -1;
    tour = i >= 0 && i === expected ? { kind: 'at', index: i } : { kind: 'off' };
  }

  function play(m: (typeof TOUR)[number]) {
    synced?.present(m.run, m.at, m.id);
  }

  /**
   * The start button is a RESET, not a shortcut to the first moment.
   *
   * Without the state reset it does nothing useful for the reader who most
   * needs it. Someone who clicked around, landed in `off`, and then pressed
   * start would arrive at moment one with the tour still `off`, so no cue would
   * appear and the button would look broken. Putting the machine back to
   * `unstarted` first means `arrived` sees the expected index and the walk
   * begins, from whatever mess the reader made.
   */
  function startTour() {
    tour = { kind: 'unstarted' };
    play(TOUR[0]);
  }

  /**
   * ---- THE SURFACE WALK ----------------------------------------------------
   *
   * The same arrangement as the trace above, one size smaller. The figure
   * exposes `walk`, the prose owns the button, and the flag comes back so the
   * button can be disabled while the walk runs. No tour and no cue: there is
   * one control and one thing it does, so there is nothing to be led through.
   */
  let surface: ReturnType<typeof SurfaceCanvas> | null = $state(null);
  let surfaceWalking = $state(false);

  /**
   * The cue on the walk button. One flag, and once it is down it stays down.
   *
   * Three things put it down: pressing the button, working the figure's own
   * controls, and the walk running. The first two are the reader saying they
   * have found the figure, and the third is the rule from the tour above --
   * never point at a control that is disabled, because an arrow on a dead
   * button reads as a broken page.
   */
  let surfaceCued = $state(true);

  /**
   * The panels below are NOT chained to this button, and that is deliberate.
   * They draw themselves as the reader scrolls to them, so chaining would fire
   * them two figures off-screen while the surface still has the reader's
   * attention, and they would be sitting finished by the time anyone arrived.
   * The button drives the surface. Scrolling drives the panels.
   */
</script>

<!-- The badge back to the site, same markup, position and breakpoint as the
     clap and separate posts. A post that reads as part of adamsohn.com has to
     say so somewhere, and the corner is where the other four say it. It is
     dropped under 560px because a fixed element floats over the text on a
     phone, which is the same reason those posts drop it. -->
<a class="byline mono" href="https://adamsohn.com">adamsohn.com</a>

<Layout>
  <Section width="measure">
    <Prose>
      <h1>A probability grid of chain-of-thought, read through Boyd's OODA loop lens</h1>
    </Prose>
  </Section>

  <!-- The hero figure carries no header of its own: it sits directly under the
       title, the way the cubes do on reliably-incorrect. The heading that names
       the argument comes after it, with the prose it belongs to. -->
  <Section width="figure">
    <Figure name="rings" alt="Four reasoning runs drawn as rings, each arc a stretch of the model’s thinking, coloured by which phase of the loop it was in. Three of them finish and stop. The fourth is still turning."><IterationRings /></Figure>
  </Section>

  <!-- `figure`, not `measure`: the dogfight is a chart and belongs at the same
       880px every other figure on this page uses. Section keeps the prose in
       here at the reading measure regardless, so only the canvas widens. -->
  <Section eyebrow="00 · the loop" title="Boyd's loop" width="figure">
    <Prose>
      <p>
        During the Korean War, when both pilots saw each other, they merged head-on at a
        closing speed near a thousand miles an hour. The pass was over in seconds. What
        followed was a turning fight, each trying to end up behind the other. John Boyd,
        an Air Force pilot who spent his career on those seconds, described what a pilot
        does as four steps run over and over. Observe, orient, decide, act, then look
        again, because the other aircraft moved during the decision. He argued that
        the pilot who gets through that loop faster wins, even when his individual
        decisions are the worse ones. Jeff Atwood in his blog,
        <a
          href="https://blog.codinghorror.com/boyds-law-of-iteration/"
          target="_blank"
          rel="noopener"
        >Coding Horror</a>, took it from
        <a
          href="https://web.archive.org/web/20070211180233/http://msdn2.microsoft.com/en-us/library/aa479371.aspx"
          target="_blank"
          rel="noopener"
        >Roger Sessions</a> and compressed it into a slogan. Speed of iteration beats
        quality of iteration.
      </p>
    </Prose>

    <Figure name="dogfight" alt="Two aircraft turning against each other. A small loss on each turn compounds into one the pilot cannot recover from."><Dogfight /></Figure>

    <Prose>
      <p>
        Software took that slogan as sprint advice. Iterate faster, ship smaller, fail
        early. That reading treats every cycle as a fresh start, and it misses what Boyd
        was pointing at. His fight has no fresh starts. The speed a pilot burns in one
        turn is still gone when the next turn begins, so a small disadvantage per cycle
        compounds into an unrecoverable one. Software calls it technical debt. Every shortcut
        one sprint takes slows every sprint after it, and slows them by more each time.
      </p>
      <p>
        A reasoning model works the same way. It reads every token in front of it,
        works out a probability for each token that could come next, picks one, and
        adds it to what it reads on the next pass. That is the whole mechanism, and
        nothing in it knows what a step is.
      </p>
      <p>
        What comes out is natural language, and that language is Boyd's list. Here is one run,
        in order. <em>Okay, so I need to calculate the exact product of 2053896 and
        30957123778</em> is observe.
        <em>Alternatively, maybe use the calculator approach? But since I can't
        use a calculator, I need to do it manually</em> is orient. In the run that
        came out wrong, floating an idea like that and then dropping it is the
        commonest move the model makes, and not one of them produces any work.
        <em>Alternatively, use the distributive property</em> is decide, the same
        word it just used to float an idea and drop it. Then comes the arithmetic,
        which is act and the
        only one of the four with no line to quote. Thirty passages of thinking
        later, <em>Wait, let me check the addition steps again</em>. That looks
        like a fifth step and it is not one. Checking the sum is observe again, and
        the second time it points at what the model wrote rather than at the
        problem it was handed.
        Boyd's pilot has to look again because the other aircraft moved while he
        decided. The model has to look again because it wrote something while it
        decided, and what it wrote is now part of what it reads.
      </p>
      <p>
        I ran thousands of
        multiplication problems through these models, and
        <a
          href="https://adamsohn.com/reliably-incorrect/"
          target="_blank"
          rel="noopener"
        >had Claude Opus label the thinking text</a> of individual runs segment by
        expensive segment. The same patterns appear in models from different companies,
        and in
        <a
          href="https://adamsohn.com/lambda-variance/"
          target="_blank"
          rel="noopener"
        >coding tasks</a>. Every one of them reads the
        problem back, chooses an approach, does the work, checks it, catches a mistake
        and goes back.
      </p>
      <p>
        No objective named those four phases, but that is not the same as nobody
        selecting for them. Qwen3 was
        <a
          href="https://arxiv.org/html/2505.09388v1"
          target="_blank"
          rel="noopener"
        >trained by reinforcement learning</a> against thousands of query and verifier
        pairs, and that reward arrives only when the final answer is exactly right. A
        slip that survives to the end makes the answer wrong, and on a chain this long
        some slip is close to certain, so no amount of care reaches that reward on its
        own. Catching them does. That is what the training actually selects for. Both
        it and Phi-4-reasoning, the second model on this page, were handed
        <code>&lt;think&gt;</code> tokens, which put a wall around the reasoning
        without saying anything about what goes inside it. And replications of that
        training keep finding base models already writing "wait" and "let me verify"
        before any of it ran, so it raised the weight on something that was there
        rather than inventing it.
      </p>
      <p>
        So the loop is a property of how these models were scored, not something in the
        architecture. Wherever a task has one exact answer and a long way to reach it,
        checking is the shortest route to that reward, and the loop follows. Where a
        wrong step is survivable, nothing selects for the habit and there should be no
        loop to find. Long multiplication sits at the first end of that range, which is
        why the traces here are so legible, and it is also the caveat on everything
        that follows.
      </p>
    </Prose>

    <!-- The one figure on this page that is not about Qwen. The grid measures
         where one model stops being right and cannot say anything about how two
         models differ in the way they think, because it only ever looks at one.
         These labels were already published, so the page can borrow them rather
         than claim them. -->
    <Figure name="thinking-mix" alt="How Claude Haiku, Opus and Sonnet each spend their thinking across nine kinds of reasoning move. The proportions do not agree."><ThinkingMix /></Figure>

    <Prose>
      <p>
        Normally a model would call a tool. Doing the multiplication by reasoning instead is
        expensive, and it burns the same GPU time as a complex coding task. To the model
        the two are the same work. What multiplication gives is control over the
        difficulty, the way a control rod gives control over a reactor. Move it and the
        reaction changes by a known amount. Every model here reaches for the same
        longhand method taught in school, one partial product for each digit of the
        second number, each shifted by its place, then all of them added up. So every
        extra digit adds an exact number of small steps rather than a vague amount more
        work. A seven digit number against an eleven digit one takes seventy seven of
        them. Against a twelve digit one it takes eighty four.
      </p>
      <!-- The grid at thumbnail size and deliberately empty. Section 02 draws
           the same lattice with a rate in every cell; a shaded one here would
           read as that measurement arriving early. -->
      <Figure name="grid-key" alt="The fourteen by fourteen grid of problem sizes, digits of one factor against digits of the other. It carries no data, and the one marked cell is a single digit against nine."><GridKey /></Figure>

      <p>
        None of this can be memorised. Every problem size gets a cell of its own, digits
        in one number against digits in the other, and one of the smallest cells is a
        single digit against nine. That cell alone holds eight billion different
        problems, and the model working them here has four billion parameters. The
        whole fourteen by fourteen grid holds 10<sup>28</sup>, which is ten thousand
        trillion trillion. There is nowhere to put the answers, so the model has to
        work them out.
      </p>

    </Prose>

    <!-- The controls and the figure travel together, and the scroll aims at
         this wrapper rather than at the figure. Scrolling the figure alone put
         its own buttons off the top of the viewport, so getting to step 2 meant
         scrolling back up after step 1.

         THE LOOP WORKING COMES FIRST. Both rows are the same machinery, and a
         reader meeting the failing one first concludes that reasoning is what
         breaks the model. It is what saves it three runs out of four. -->
    <div class="moment-group" bind:this={momentGroup}>
      <Figure name="synced-trace" alt="One reasoning run at a time, its shape on top and its thinking and its arithmetic below, with three more to switch to. One catches its mistake, one carries it to the end, and one never finishes.">
        <SyncedTrace
          bind:this={synced}
          scrollTarget={momentGroup}
          onBusyChange={(b) => (momentBusy = b)}
          onMoment={(m) => {
            moment = m;
            // A clear while busy belongs to a present that is just starting. A
            // clear while idle is the reader taking the cursor back.
            if (m === null) {
              if (!momentBusy) tour = { kind: 'off' };
              return;
            }
            arrived(m);
          }}
        />
      </Figure>
      <Prose>
        {#if interactive}
          <MomentLinks
            label="the loop catching its own mistake"
            moments={CAUGHT_MOMENTS}
            active={moment}
            busy={momentBusy}
            cueOn={cueTarget}
            {cueText}
            onPick={play}
          />
          <MomentLinks
            label="the same loop carrying one instead"
            moments={WRONG_MOMENTS}
            active={moment}
            busy={momentBusy}
            cueOn={cueTarget}
            {cueText}
            onPick={play}
          />
        {/if}
        <p>
          Both rows run the same loop. The difference is what the model does when it
          checks.
        </p>
        <p>
          In the first row it works the product two ways. The two ways disagree, and that
          disagreement is what saves it. It goes back, finds the slip, and finishes with
          the right answer.
        </p>
        <p>
          In the second row it checks by redoing the same sum the same way. It gets the
          same wrong number, finds no conflict, and carries that number to the end.
        </p>
        <p>A check only helps when it could have failed differently.</p>
        {#if interactive}
          <div class="tour-start">
            {#if cueTarget === 'start'}<Cue text={cueText} />{/if}
            <button type="button" disabled={momentBusy} onclick={startTour}>
              Walk it from the start
            </button>
          </div>
        {/if}
      </Prose>
    </div>

    <Prose>
      <p>
        The run that failed is the one to keep in mind. Every phase of the loop ran. The
        model checked its own work. The answer was still wrong. The rest of this page is
        about how often that happens, and at what size it starts.
      </p>
    </Prose>
  </Section>

  <!-- Not "everyone evaluating LLMs is wrong". That claim is already half made
       in the literature, and a reader who knows arXiv 2411.00640 stops trusting
       the section at the headline. What is actually uncommon is measuring the
       spread rather than deriving it, and finding out it costs about a dollar. -->
  <Section
    eyebrow="01 · evaluation"
    title="How I evaluated the models"
    width="figure"
  >
    <Prose>
      <p>
        Frontier models are prohibitively expensive to run thousands of times, so I
        rented decent GPUs by the second on Modal instead. Before spending anything on
        the grid I ran smoke tests to find where the models begin to break and where they
        absolutely fail, so I had a known range to explore. There is no point paying to
        measure the sizes everything solves or the sizes everything misses. I wanted the
        band in between.
      </p>
      <p>
        Then I used cost-weighted Neyman allocation to work out how many runs each size
        actually needs. Low complexity always solves fast and settles in a few runs. High
        complexity always fails and settles just as fast. Medium complexity is the
        problem, because a model can grind away there for a long time and still land
        either way, so that is where most of the runs have to go.
      </p>
    </Prose>

    <Figure name="allocation" alt="How many runs each problem size was given. Sizes that always solve and sizes that always fail settle quickly, so most of the runs go to the uncertain middle."><AllocationGrid /></Figure>

    <Prose>
      <p>
        I put several models through all of this to find the two that came out closest,
        Qwen3-4B from Alibaba and Phi-4-reasoning from Microsoft.
      </p>
    </Prose>
  </Section>

  <Section eyebrow="02 · the surface" title="How much variance is there?" width="figure">
    <Prose>
      <p>
        Winning the battle does not require perfection. It requires correction that
        could have failed differently from the step it is checking. Just like the F-86
        dogfights, a high rate of error is tolerable as long as something in the loop
        can catch it. Multiplication serves as a controlled dial to scale this
        complexity. Model failure is not a black box. The rate moves smoothly with
        size, even though any single run in the middle band is a toss-up, and the
        gradient marks the edge of what these models can do unaided.
      </p>
      <p>
        The surface below tracks that boundary. One axis counts the digits of a, the
        other the digits of b, and cell height reflects the proportion of runs that
        landed the exact product, with 4 × 4 representing a problem like
        3,437 × 9,122. Sample sizes vary across cells. The uncertain middle earns more
        attempts. The surface redraws on each trial, which shows which rates have
        settled and which are still moving.
      </p>
      <p>
        Only an exact answer counts as a success. A wrong digit in the answer is a
        failure, and so is a run that runs away. Given room, a model will generate tens
        of thousands of tokens. Some were still working when the run was stopped, so
        whether they would have landed it is unknown, and paying to find out is
        prohibitively expensive. Non-converging runs are scored identically to
        incorrect ones, as both represent unusable output. The raw data retains all
        four distinct outcomes. The grid simply collapses them.
      </p>
      <p>
        Looking at these charts, it is easy to conclude these models are hopelessly
        limited. The top end does go to zero on the runs I did, at sample sizes too
        small to call it impossible. But that falloff hides an important structural
        advantage. Measuring where the model's reliability falls off, even as a
        probability rather than a verdict, gives us a way to forecast results.
      </p>
      {#if interactive}
        <div class="tour-start">
          {#if surfaceCued && !surfaceWalking}<Cue text="press here" />{/if}
          <button
            type="button"
            disabled={surfaceWalking}
            onclick={() => { surfaceCued = false; surface?.walk(); }}
          >
            Walk it from the start
          </button>
        </div>
      {/if}
    </Prose>
    <Figure name="surface" alt="The reliability surface. Digits of a on one axis, digits of b on the other, height is the share of runs that landed the exact product. It redraws as the trial count rises.">
      <SurfaceCanvas
        bind:this={surface}
        onWalkChange={(b) => (surfaceWalking = b)}
        onReaderDrive={() => (surfaceCued = false)}
      />
    </Figure>
    <Figure name="distribution" alt="Three panels. A histogram of 500 twelve-problem scores of the 11 by 8 cell, and beside it the running estimate for two runs, 11 by 8 with reasoning on and 5 by 5 with it off, each with its 95% band."><DistributionPanels /></Figure>
  </Section>

  <!-- The PAIRED claim that used to live here is pulled. It said Phi solves
       problems Qwen cannot, so a second vendor buys coverage. Qwen averaged 1.50
       attempts per problem and Phi 1.14, and at that sampling a second sample of
       QWEN would have rescued 102.7 of Qwen's failures against Phi's actual 82.
       Both directions sit inside the null's noise. `probe/self_rescue.py` has
       the numbers and what sampling shape would settle it. `WinnerSurface` is
       the figure that carried the claim and stays out of the page until then.

       What remains is the MARGINAL comparison, which needs no pairing and is
       what BoundaryWedge draws. -->
  <Section eyebrow="03 · two models" title="Where each one stops" width="figure">
    <Prose>
      <p>
        I expected the two models, Qwen and Phi, to fail on different problems, and the
        reason was a pattern I kept hitting. Opus 4.6 would write a query that caused a full table
        scan on 450GB of timeseries data, and the Claude models I used to review
        missed it every time. Regardless of how much prompting I did or how many
        specific instructions I put in code comments, it would go on making the same
        mistake. Handing the same review to Codex caught it far more often. That is a
        blind spot one vendor had and the other did not, on a problem, writing queries
        for timeseries analysis in Postgres, and it is the hypothesis this grid was
        built to test. I
        will keep chasing understanding it in the future.
      </p>
      <p>
        The method followed from the hypothesis. Probe until I find the two models
        that come out closest, then hand them one problem type whose complexity I can
        raise in small steps, and check which specific problems each one misses.
      </p>
      <p>
        Multiplication did not show it, and at 1.5 attempts per problem it was never
        going to. Both curves fall away over the same range and sit about a digit apart
        in each factor, and there is nowhere on the grid where Phi is ahead of Qwen by
        more than noise.
      </p>
      <p>
        My guess is that the same consistency holds for lambda calculus and other
        coding work, and that where models really do differ it comes down to what they
        were trained on rather than how capable they are. Some frontier models solve a
        Rubik's Cube and others that keep up with them on arithmetic cannot. I did not
        measure that here, and my read is that one company put it in the training set,
        as data or as a rubric.
      </p>
      <p>
        One thing weakens the comparison and it belongs here rather than in a footnote.
        Phi-4-reasoning learned to reason by supervised fine-tuning on 1.4 million
        reasoning traces generated by OpenAI's o3-mini. So these two models come from
        different companies but not from independent lineages, and nothing in this data
        can separate how much of their agreement is convergence from how much is
        inheritance.
      </p>
    </Prose>
    <Figure name="boundary" alt="Reliability against the total digit count, one dot per cell per model, with a fitted band. Qwen falls to a coin flip at 9.24 digits and Phi at 8.39."><BoundaryWedge /></Figure>
  </Section>

  <!-- Sections 04 through 06 held placeholders for convergence, the reasoning
       on/off price comparison, and the operand-order and temperature nulls.
       Their charts exist in `derived/` and are indexed in docs/ARTIFACTS.md;
       none of them were written up, and an unfinished section reads worse than
       an absent one. The conclusion below took the slot instead.

       IT NAMES RUNS BY THE VERDICT LABELS ON SyncedTrace'S OWN BUTTONS.
       `Caught`, `Wrong`, and `Locked` are all labels a reader can press, so
       every run the prose credits is one they can look at. `Solved` stays
       uncredited: the tour never walks it, and an earlier draft that credited
       it sent the payoff at something nobody had looked at. Locked's numbers
       are computed from CARRY_TRACES rather than quoted from memory: 276 LOOP
       segments repeating one addition sentence, 68.5% of that run's segments.

       LOCKED IS A CHECKING RESULT, NOT A SIZE RESULT, and two drafts got this
       backwards. The four traces are chosen at NEIGHBOURING difficulty (see the
       generated header on reasoning-grid-traces.ts: N = 56 to 77, one per way the
       checking machinery can behave), so size is the controlled variable and
       cannot carry a conclusion. Locked sits at 5x13, mid-range, and its own
       blurb is "Had the right answer, a broken check destroyed it." Using it as
       the far side of a size edge inverts the design of the figure it points
       at. It belongs beside Caught and Wrong as the third checking behaviour.

       STILL TO WRITE, with the sourcing already done: the Sessions callback
       (section 00 says Atwood took the slogan from Roger Sessions and
       compressed it; docs/boyds-law-of-iteration.md has the distinction the
       compression dropped, iterate on the whole vs recurse to a base case), and
       two outside citations that must be LINKED because this page links every
       other one -- Huang et al. arXiv 2310.01798, whose term "intrinsic
       self-correction" names correcting with no external feedback, and the
       Darwin Godel Machine, arXiv 2505.22954, 20.0% to 50.0% on SWE-bench,
       whose agent deleted the hallucination markers its own check looked for
       (from the paper's safety discussion, not a secondary retelling). -->

  <!-- THE ASYMMETRY IS THE POINT, and it is a claim about Boyd's loop before it
       is a claim about models: exactly one of the four phases is supposed to
       touch something the loop did not produce. Drop that and every sentence
       here is decoration, so the canopy opens the paragraph. -->
  <Section
    eyebrow="04 · conclusion"
    title="The loop has to be able to find out it was wrong"
    width="figure"
  >
    <Prose>
      <p>
        With multiplication we had the benefit of a cheap verifier. That is what makes
        the grid possible. Every cell shows where the model stops being reliable,
        because we always knew the right answer. Solving complex coding problems isn't
        much different from solving complex multiplication problems, granted we have a
        cheap verification process.
      </p>
      <p>
        We shouldn't expect the model to solve every complex problem in one pass.
        Rather than stopping at an understanding of the limitations, we can decompose
        problems into manageable parts. The iteration process matters too. Observe,
        orient, decide, act. That is the purpose of the agent harness, which is the
        interface between the environment and the model. The input is the observation
        and the output is the action.
      </p>
      <p>
        The models are not coin flips. They are instruments with a working range, and
        inside that range the outcome is predictable.
      </p>
    </Prose>
  </Section>
</Layout>

<style>
  .byline {
    position: fixed;
    top: var(--space-md);
    right: var(--space-lg);
    z-index: 30;
    font-size: 0.74rem;
    color: var(--ink-faint);
    border-bottom: 1px solid var(--line-strong);
    text-decoration: none;
  }
  .byline:hover { color: var(--accent); }
  @media (max-width: 560px) {
    .byline { display: none; }
  }

  /* The buttons and the figure they drive are one unit for scrolling. The
     margin is what stops the row landing flush against the top edge of the
     viewport when a moment is played. */
  .moment-group {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
    width: 100%;
    min-width: 0;
    scroll-margin-top: var(--space-lg);
  }

  /* `position: relative` is the whole reason this is a div rather than a bare
     button: the cue positions against it. `inline-flex` keeps the box the width
     of the button, so the arrow lands on the button and not on empty space to
     the right of it. */
  .tour-start {
    position: relative;
    display: inline-flex;
    /* SPACE BELONGS TO THE CONTAINER, NOT THE BUTTON. Padding on the control
       would grow the control, and 9px by 16px is already the right size for a
       hit target -- separation from the paragraph is not the button's job.

       Top is larger than bottom because the cue is absolutely positioned above
       the button and overhangs this box entirely, so the gap a reader sees
       above the arrow is whatever is left after the cue eats into it. Bottom
       has no such tenant and needs less to look even.

       `inline-flex` is an inline-level box, so these margins apply and do not
       collapse into the paragraph's own. Whatever is set here is what shows. */
    margin: var(--space-xl) 0 var(--space-lg);
  }
  .tour-start button {
    padding: 9px 16px;
    background: var(--accent);
    border: 1px solid var(--accent);
    border-radius: var(--radius-sm);
    font-family: var(--font-sans);
    font-size: var(--text-sm);
    color: var(--bg);
    cursor: pointer;
    transition: background 150ms ease, border-color 150ms ease;
  }
  .tour-start button:hover:not(:disabled) {
    background: var(--accent-hover);
    border-color: var(--accent-hover);
  }
  .tour-start button:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  .tour-start button:disabled {
    opacity: 0.55;
    cursor: default;
  }
</style>

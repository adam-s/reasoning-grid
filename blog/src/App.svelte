<script lang="ts">
  // SCAFFOLD. Composes <Section> blocks, one per beat of the argument.
  // Each viz slot below is a placeholder -- see blog/README.md for what goes
  // in it and which committed chart it ports from.
  import Layout from './lib/components/Layout.svelte';
  import Section from './lib/components/Section.svelte';
  import Prose from './lib/components/Prose.svelte';
  import Placeholder from './lib/components/Placeholder.svelte';
  import ThinkingMath from './lib/viz/opener/ThinkingMath.svelte';
  import FlamePanel from './lib/viz/flame/FlamePanel.svelte';
  import ThreeTraces from './lib/viz/flame/ThreeTraces.svelte';
  import SurfaceCanvas from './lib/viz/surface/SurfaceCanvas.svelte';
  import WinnerSurface from './lib/viz/surface/WinnerSurface.svelte';
  import { LAMBDA_TRACE } from './lib/data/lambda-trace';
</script>

<Layout>
  <Section eyebrow="carrychain" title="Where two models stop being reliable" width="figure">
    <Prose>
      <p>
        Watch a model multiply two numbers. On the left is what it is thinking; on the
        right is every arithmetic claim it makes, checked against real arithmetic the
        moment it is made. Long multiplication is the instrument here for one reason:
        the right answer is free to compute, so nothing has to be judged.
      </p>
    </Prose>
    <ThinkingMath />
    <Prose>
      <p>
        Three runs, 152 arithmetic claims, and exactly one is false. It is an addition
        &mdash; every multiplication in every run is correct. The run that got the
        answer wrong could multiply seven-digit numbers all day and lost to a carry.
      </p>
      <p>
        Read the left pane alone and you cannot tell which run is which. All three are
        fluent, all three check their work, all three sound careful. That is the problem
        this project is about: the prose does not mark the line where the arithmetic
        broke, and the model does not notice either &mdash; it carries the bad total
        forward to the end and states it as the answer.
      </p>
    </Prose>
  </Section>

  <Section eyebrow="01 · the surface" title="The grid" width="figure">
    <Prose>
      <p>
        One cell per problem size: how many digits in each factor, and how often the
        model returns the exactly correct product. Scrub the trial count and watch it
        assemble. After one trial the shape is roughly right but reads as a cliff,
        because every cell is either 0% or 100% &mdash; there is no middle to be in yet.
        The middle fills over the next few trials, and by about eight the terrain stops
        changing shape and only jitters.
      </p>
    </Prose>
    <SurfaceCanvas />
  </Section>

  <Section eyebrow="02 · blind spots" title="Do they fail in the same places?" width="figure">
    <Prose>
      <p>
        Two models from different companies, asked the same 1,062 problems. If they fail
        on the same ones, a second model buys nothing and the only question is which is
        better. If they fail on different ones, running both buys coverage no single
        model reaches at any quality. That is a claim about how to build on these models,
        and it is settled by data rather than argument.
      </p>
      <p>
        Start with Qwen alone, then add Phi and watch what moves. Almost nothing does.
        The two surfaces hold the same plateau and fall off the same cliff, about a
        digit apart &mdash; the same curve shifted, never crossing.
      </p>
    </Prose>
    <WinnerSurface />
    <Prose>
      <p>
        The marked cells are where Phi scored higher, and they are a reason to be
        careful rather than a reason to run two models. Each cell holds 3, 6 or 12
        problems, so two <em>identical</em> models would land some distance apart by luck
        alone &mdash; furthest apart in the middle, where a coin flip has the most room.
        Measured against that, <strong>10 of 144 cells</strong> are further apart than
        chance explains, and <strong>none of them favour Phi</strong>. Every marked cell
        is inside the range a coin would reach; ten of Qwen's leads are not.
      </p>
      <p>
        Phi's best cell looks convincing on its own &mdash; 100% against Qwen's 67%, a
        clean sweep. It holds three problems. With three problems, two identical models
        routinely land sixty points apart.
      </p>
    </Prose>
  </Section>

  <Section eyebrow="03 · precision" title="What one number is made of">
    <Placeholder name="Convergence" ports="probe/render_convergence.py" />
  </Section>

  <Section eyebrow="04 · reasoning" title="Is the reasoning doing the arithmetic?">
    <Placeholder name="EffortPrice" ports="probe/render_effort.py" />
  </Section>

  <Section eyebrow="05 · the loop" title="Three ways to finish a hard multiplication" width="figure">
    <Prose>
      <p>
        Same model, three problems of about the same size, three outcomes. Every bar is
        one move in the model's thinking, coloured by what kind of move it was. The two
        colours that matter are the checking ones: <strong>recheck</strong>, where the
        model re-derives a value the same way it got it, and <strong>crosscheck</strong>,
        where it uses a method that can fail differently &mdash; casting out nines, a
        modulus, a magnitude bound.
      </p>
      <p>
        A recheck cannot catch a mistake the first pass was capable of making, because
        the faculty doing the checking is the one that slipped. That distinction is the
        whole figure.
      </p>
      <p>
        The run that got it wrong ran <strong>14 rechecks against 9 crosschecks</strong>.
        The run that got it right ran that ratio the other way, and by a wider margin.
        Both gave a similar share of the trace to checking &mdash; so the variable is not
        how much a model checks. It is whether the check can fail differently from the
        thing being checked.
      </p>
    </Prose>
    <ThreeTraces />
  </Section>

  <Section eyebrow="reference figure" title="A reasoning trace as a flame graph" width="figure">
    <Prose>
      <p>
        Copied unmodified from the &lambda;-bench variance post: one Sonnet 4.6 run on
        the LamBench <code>algo_evl</code> task, segmented and categorised by Opus 4.6.
        Not carrychain data &mdash; this is the figure the one above was built from.
      </p>
    </Prose>
    <FlamePanel trace={LAMBDA_TRACE} />
  </Section>

  <Section eyebrow="06 · knobs" title="Two things that do not matter, one that does">
    <Placeholder name="OrderNull" ports="probe/render_order.py" />
    <Placeholder name="TemperatureLadder" ports="probe/render_temperature.py + render_temp0.py" />
  </Section>
</Layout>

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
    <ThinkingMath />
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

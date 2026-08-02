<script lang="ts">
  // SCAFFOLD. Composes <Section> blocks, one per beat of the argument.
  // Each viz slot below is a placeholder -- see blog/README.md for what goes
  // in it and which committed chart it ports from.
  import Layout from './lib/components/Layout.svelte';
  import Section from './lib/components/Section.svelte';
  import Prose from './lib/components/Prose.svelte';
  import Placeholder from './lib/components/Placeholder.svelte';
  import FlamePanel from './lib/viz/flame/FlamePanel.svelte';
  import ThreeTraces from './lib/viz/flame/ThreeTraces.svelte';
  import { LAMBDA_TRACE } from './lib/data/lambda-trace';
</script>

<Layout>
  <Section eyebrow="carrychain" title="Where two models stop being reliable">
    <Prose>
      <p>Lede goes here. See <code>blog/README.md</code> for the argument order.</p>
    </Prose>
  </Section>

  <Section eyebrow="01 · the surface" title="The grid">
    <Placeholder name="Surface3D" ports="probe/render_grid.py + render_animation.py" />
  </Section>

  <Section eyebrow="02 · blind spots" title="Do they fail in the same places?">
    <Placeholder name="BlindSpots" ports="probe/render_blindspots.py" />
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

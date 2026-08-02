<script lang="ts">
  import type { Snippet } from 'svelte';
  type Props = { children: Snippet };
  let { children }: Props = $props();
</script>

<div class="layout"><main class="content">{@render children()}</main></div>

<style>
  /* Wide shell, centred children, each declaring its own width: prose holds
     --maxw, figures take --maxw-fig. Constraining here instead would force
     every figure to fight the container.

     Breakpoints match agent-capability-threshold, which is the post that
     actually ships the flame graph -- so the component's own 720px rules line
     up with the shell's instead of fighting them. */
  .layout {
    min-height: 100vh;
    max-width: var(--maxw-page);
    margin: 0 auto;
  }
  .content {
    min-width: 0;
    padding: var(--space-3xl) var(--space-xl);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2xl);
  }

  @media (max-width: 900px) {
    .content { padding: var(--space-xl) var(--space-md); gap: var(--space-xl); }
  }
  @media (max-width: 600px) {
    /* Below this the reading measure is the viewport, so side padding is the
       only thing standing between text and the bezel. Keep a little; drop the
       rest. */
    .content { padding: var(--space-lg) var(--space-sm); gap: var(--space-lg); }
  }
</style>

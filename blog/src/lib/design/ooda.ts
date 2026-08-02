/**
 * The same nine categories collapsed onto Boyd's four phases.
 *
 * This exists to make an argument against itself. Coloured by OODA phase, the
 * run that got the right answer and the run that got the wrong one are almost
 * the same picture — observe ~40%, orient ~25%, act ~35% in both. The loop does
 * not distinguish them. You have to split OBSERVE into "re-derived it the same
 * way" and "checked it a way that could fail differently" before the difference
 * appears at all, and that split is one level below anything OODA names.
 *
 * So the four-colour view is the control, not the finding. It shows that the
 * vocabulary everyone reaches for is too coarse for the thing being measured.
 *
 * DECIDE is the other half of it. Across all 524 labelled segments it occurs
 * ZERO times. These models observe, orient and act; not once does one of them
 * decide to change a value it has already written down. A loop with no decide
 * phase cannot correct itself and cannot choose to stop — which is exactly how
 * the third trace ends.
 *
 * It was one, until a blind reproduction of every label removed it: the single
 * ERROR_CORRECTION was a false alarm the model talked itself out of without
 * changing anything, and the rubric lists "ERROR_CORRECTION assigned where no
 * value changed" as a fail condition. All three traces raise exactly one false
 * alarm and all three resolve it without editing a digit.
 *
 * STRATEGY is mapped to ORIENT, not split between orient and decide. The rubric
 * says the two are not separable in these traces because the model states a plan
 * and commits in the same breath; forcing a split would invent a boundary the
 * text does not have. That choice is why DECIDE holds only ERROR_CORRECTION.
 */
import type { CategoryScheme, SchemeMeta } from './scheme';

export const OODA_PHASES = ['OBSERVE', 'ORIENT', 'DECIDE', 'ACT'] as const;
export type OodaPhase = (typeof OODA_PHASES)[number];

/** Category -> phase. Mirrors the mapping table in the rubric. */
export const CATEGORY_PHASE: Record<string, OodaPhase> = {
  TASK_SETUP: 'OBSERVE',
  RECHECK: 'OBSERVE',
  CROSSCHECK: 'OBSERVE',
  STRATEGY: 'ORIENT',
  STATE_TRACKING: 'ORIENT',
  ERROR_CORRECTION: 'DECIDE',
  PARTIAL_PRODUCT: 'ACT',
  ACCUMULATE: 'ACT',
  RESULT: 'ACT',
};

const meta: Record<OodaPhase, SchemeMeta> = {
  OBSERVE: {
    label: 'Observe',
    color: '#2d7d6a',
    symbol: 'O',
    description:
      'Reading the problem, and every kind of checking — both re-deriving a value the same way and validating it a way that could fail differently. The distinction that decides these runs lives inside this one band.',
  },
  ORIENT: {
    label: 'Orient',
    color: '#c48b3f',
    symbol: 'O',
    description:
      'Choosing how to decompose the problem, and tracking where it is. A quarter of every trace.',
  },
  DECIDE: {
    label: 'Decide',
    color: '#bf4536',
    symbol: 'D',
    description:
      'Changing a value already written down. Zero segments in 524 — the loop these models run has no decide phase at all.',
  },
  ACT: {
    label: 'Act',
    color: '#4a6d8c',
    symbol: 'A',
    description: 'Computing a partial product, summing, stating the answer.',
  },
};

export const OODA_SCHEME: CategoryScheme = {
  order: OODA_PHASES,
  meta,
  fallback: { label: 'Unphased', color: '#b8b3a8', symbol: '?', description: 'Unmapped category.' },
};

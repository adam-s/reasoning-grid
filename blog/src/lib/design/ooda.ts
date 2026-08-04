/**
 * The sixteen categories collapsed onto Boyd's four phases.
 *
 * The map is DERIVED from `carryCategoryMeta`, not written out a second time.
 * The previous version maintained its own table beside the rubric's, the two
 * disagreed about which phase one category belonged to, and that disagreement
 * was what produced the post's headline. A map that cannot be edited separately
 * cannot drift.
 *
 * Each category has exactly one phase. `LOOP` has none, and that is a claim, not
 * an omission: emitting the same sentence 276 times is not observing, orienting,
 * deciding or acting. It is 69% of one trace, and scoring it as arithmetic — as
 * the previous labels did — says that run spent its time doing sums.
 *
 * ## What each phase holds, and why
 *
 * OBSERVE takes in what is there, INCLUDING the model's own output. All three
 * kinds of check live here: re-deriving, testing by an independent method, and
 * testing the size. Checking is looking, not deciding.
 *
 * ORIENT makes sense of what came in. Weighing an option without taking it,
 * naming a check without running it, and recognising that two values disagree
 * are all interpretation. `ALARM` sits here rather than in OBSERVE because
 * noticing a mismatch is a judgment about observations, not an observation.
 *
 * DECIDE chooses a course of action, INCLUDING choosing not to change anything.
 * That inclusion is the whole repair. The previous scheme defined its only
 * decide category as "changing a value already written down", which in long
 * multiplication almost never happens — so the phase came back empty and the
 * emptiness was reported as a property of the model rather than of the
 * definition. Committing to a decomposition, abandoning one, revising a value,
 * letting it stand, and failing to settle are all decisions.
 *
 * ACT carries it out: the partial products, the shifts, the sums, the answer.
 *
 * ## The judgment calls, stated
 *
 * Two placements are arguable and neither is hidden:
 *
 *   ALARM -> orient, not observe. Under the other reading OBSERVE gains 19
 *   segments and ORIENT loses them; DECIDE is unchanged either way, so the
 *   headline does not turn on it.
 *
 *   STALL -> decide, not observe. A stall is a decision that fails to complete,
 *   and it re-checks while failing. Under the other reading DECIDE drops from 51
 *   to 39 segments, 14.2% to 10.9% of the reasoning — smaller, still not empty.
 *
 * Neither call can empty a phase, which is the property the previous mapping
 * lacked.
 */
import { carryCategoryMeta, type CarryCategory, type Ooda } from './carrychain-categories';
import type { CategoryScheme, SchemeMeta } from './scheme';

export const OODA_PHASES = ['OBSERVE', 'ORIENT', 'DECIDE', 'ACT'] as const;
export type OodaPhase = (typeof OODA_PHASES)[number];

/** Phase for a category that has one; null for the categories outside the loop. */
const PHASE_OF: Record<Ooda, OodaPhase | null> = {
  observe: 'OBSERVE',
  orient: 'ORIENT',
  decide: 'DECIDE',
  act: 'ACT',
  none: null,
};

/**
 * Category -> phase, built from the category metadata so the two cannot
 * disagree. Categories outside the loop are absent rather than mapped to a
 * fallback: a caller that needs them must say what it wants done with them.
 */
export const CATEGORY_PHASE: Record<string, OodaPhase> = Object.fromEntries(
  Object.entries(carryCategoryMeta)
    .map(([cat, meta]) => [cat, PHASE_OF[meta.ooda]])
    .filter((entry): entry is [CarryCategory, OodaPhase] => entry[1] !== null),
);

/** Categories deliberately outside the loop. */
export const UNPHASED: readonly string[] = Object.entries(carryCategoryMeta)
  .filter(([, meta]) => PHASE_OF[meta.ooda] === null)
  .map(([cat]) => cat);

const meta: Record<OodaPhase, SchemeMeta> = {
  OBSERVE: {
    label: 'Observe',
    color: '#1f7d68',
    symbol: 'O',
    description:
      'Reading the problem, and every kind of checking — re-deriving a value the same way, testing it a way that could fail differently, and testing its size. The distinction that decides these runs lives inside this one band.',
  },
  ORIENT: {
    label: 'Orient',
    color: '#b8925a',
    symbol: 'O',
    description:
      'Weighing an approach without taking it, naming a check without running it, and noticing that two values disagree.',
  },
  DECIDE: {
    label: 'Decide',
    color: '#c0392b',
    symbol: 'D',
    description:
      'Choosing a course of action, including choosing to change nothing: committing to a decomposition, abandoning one, revising a value, letting it stand, and failing to settle a conflict.',
  },
  ACT: {
    label: 'Act',
    color: '#3f5f92',
    symbol: 'A',
    description: 'Computing a partial product, applying a power of ten, summing, stating the answer.',
  },
};

export const OODA_SCHEME: CategoryScheme = {
  order: OODA_PHASES,
  meta,
  fallback: {
    label: 'Outside the loop',
    color: '#dedad2',
    symbol: '∞',
    description:
      'The same text again with no new content. Not a phase of the loop — a run that has stopped turning it.',
  },
};

/**
 * The nine categories a carrychain thinking trace is labelled with.
 *
 * Not the same nine as `categories.ts` — that file is the λ-bench set, kept
 * unmodified so the ported flame graph still renders its original data. Ours
 * differs in two places, and both differences are the argument:
 *
 *   VERIFICATION splits into RECHECK and CROSSCHECK. Re-deriving a value the
 *   same way cannot catch a systematic slip, because the faculty that made the
 *   error is the one checking it. A different method with different failure
 *   modes can. One colour for both hides the only thing that separated the two
 *   runs in this post.
 *
 *   ARITHMETIC splits into PARTIAL_PRODUCT and ACCUMULATE. λ's prompt says
 *   arithmetic is rare in lambda calculus; ours is nothing but arithmetic, so a
 *   single category would swallow the trace. Computing many independent small
 *   products and summing them in one long dependent chain are different phases,
 *   and the error in run B is in the second.
 *
 * Colour: one saturated hue in the whole scale, spent on CROSSCHECK, because
 * that is what the reader is meant to find. RECHECK sits opposite it in warmth
 * so the two read as different activities rather than as more and less of the
 * same one. Everything else is desaturated and stays out of the way — STRATEGY
 * especially, which is a quarter of both traces and would shout if it were
 * given a real colour.
 *
 * Rubric: ../../../../.agents/reference/flame-rubric-carrychain.md
 */

export const CARRY_CATEGORIES = [
  'TASK_SETUP',
  'STRATEGY',
  'PARTIAL_PRODUCT',
  'ACCUMULATE',
  'STATE_TRACKING',
  'RECHECK',
  'CROSSCHECK',
  'ERROR_CORRECTION',
  'RESULT',
] as const;

export type CarryCategory = (typeof CARRY_CATEGORIES)[number];

/** Which loop phase a category belongs to. `STRATEGY` spans two; see the rubric. */
export type Ooda = 'observe' | 'orient' | 'decide' | 'act';

export type CarryCategoryMeta = {
  readonly label: string;
  readonly color: string;
  readonly symbol: string;
  readonly ooda: readonly Ooda[];
  readonly description: string;
  readonly example: string;
};

export const carryCategoryMeta = {
  TASK_SETUP: {
    label: 'Setup',
    color: '#9a9384',
    symbol: 'S',
    ooda: ['observe'],
    description: 'Reading the problem, restating it, naming the operands.',
    example: '"I need to compute the exact product of 80,379,530 and 4,621,821."',
  },
  STRATEGY: {
    label: 'Strategy',
    color: '#c9b99c',
    symbol: 'D',
    ooda: ['orient', 'decide'],
    description:
      'Choosing how to decompose the problem, or which check to run next. Choosing, not doing — a quarter of both traces is spent here.',
    example: '"Maybe I can break 4,621,821 into 4,000,000 + 600,000 + 20,000 + ..."',
  },
  PARTIAL_PRODUCT: {
    label: 'Partial',
    color: '#8aa4b0',
    symbol: '×',
    ooda: ['act'],
    description: 'Computing one piece: a digit times a chunk, one row of the long multiplication.',
    example: '"80,379,530 × 8 = 643,036,240. Then × 100 = 64,303,624,000."',
  },
  ACCUMULATE: {
    label: 'Sum',
    color: '#587f92',
    symbol: '+',
    ooda: ['act'],
    description:
      'Aligning and adding the partial products. One long dependent chain, where a single misalignment carries to the end.',
    example: '"371,499,719,344,600 + 80,379,530 = ..."',
  },
  STATE_TRACKING: {
    label: 'State',
    color: '#b3afa4',
    symbol: 'T',
    ooda: ['orient'],
    description: 'Naming where it is — which chunk, which power of ten. Bookkeeping, not computing.',
    example: '"Digits: 4 (millions), 6 (hundred thousands), 2 (ten thousands), ..."',
  },
  RECHECK: {
    label: 'Recheck',
    color: '#d29a5c',
    symbol: 'R',
    ooda: ['observe'],
    description:
      'Re-deriving something by the same method. The faculty that produced the error is the one checking it, so it catches transcription slips and nothing else.',
    example: '"Term1: correct. Term2: correct. Term3: correct. ..."',
  },
  CROSSCHECK: {
    label: 'Crosscheck',
    color: '#2d7d6a',
    symbol: 'C',
    ooda: ['observe'],
    description:
      'Validating by a method with different failure modes: casting out nines, any modulus, last digit, digit count, magnitude. The only kind that can see what the first pass missed — and only as deep as the modulus it reaches.',
    example: '"87 mod 9 = 6, which matches the expected 6."',
  },
  ERROR_CORRECTION: {
    label: 'Correction',
    color: '#bf4536',
    symbol: '!',
    ooda: ['decide'],
    description:
      'Detecting a specific error and changing a value. Neither trace in this post contains one — 128 segments, two false alarms, zero corrections.',
    example: '(unobserved)',
  },
  RESULT: {
    label: 'Result',
    color: '#767165',
    symbol: '=',
    ooda: ['act'],
    description: 'Stating the final product, including the write-up after the thinking ends.',
    example: '"Therefore, the exact product is 371,499,719,424,970."',
  },
} as const satisfies Record<CarryCategory, CarryCategoryMeta>;

export const OODA_LABEL: Record<Ooda, string> = {
  observe: 'Observe',
  orient: 'Orient',
  decide: 'Decide',
  act: 'Act',
};

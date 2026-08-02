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
 * Colour. Three rules, in order:
 *
 * 1. RECHECK and CROSSCHECK are the argument, so they are the only two
 *    saturated colours and they are separated on every axis at once — amber
 *    against emerald in hue, warm against cool in temperature, and light
 *    against dark in VALUE at a measured 3.9:1. The value gap is the one that
 *    matters: it is what keeps them apart in greyscale and for the ~8% of men
 *    with red-green deficiency, for whom hue alone may carry nothing.
 *
 *    Every ratio here was measured, because the first pass at this palette
 *    asserted the same separation without checking and had it at 2.1:1. Two
 *    other pairs were worse and invisible until measured: CROSSCHECK against
 *    ERROR_CORRECTION at 1.09:1 — the exact green-against-red that most needs
 *    a value gap — and RECHECK against STRATEGY at 1.02:1, the argument colour
 *    against the quarter of every trace it has to stand out from.
 * 1b. Blue against orange (PARTIAL_PRODUCT against RECHECK) is close in value
 *    on purpose. It is the one hue pair that survives every common form of
 *    colour blindness, so hue carries it and the value budget goes elsewhere.
 * 2. PARTIAL_PRODUCT and ACCUMULATE borrow the reliability surface's own ramp,
 *    mid-tone and deep. Doing the arithmetic looks the same in both figures.
 * 3. Everything else is chromatically quiet and separated by VALUE, not hue.
 *    The previous palette had TASK_SETUP, STATE_TRACKING and RESULT as three
 *    warm greys within a few points of each other and of STRATEGY, which is a
 *    quarter of every trace — four near-identical washes doing most of the
 *    area. They are now a warm grey, a cool grey and a dark neutral, at
 *    distinctly different lightnesses.
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
    color: '#948d80',
    symbol: 'S',
    ooda: ['observe'],
    description: 'Reading the problem, restating it, naming the operands.',
    example: '"I need to compute the exact product of 80,379,530 and 4,621,821."',
  },
  STRATEGY: {
    label: 'Strategy',
    color: '#e0d8c8',
    symbol: 'D',
    ooda: ['orient', 'decide'],
    description:
      'Choosing how to decompose the problem, or which check to run next. Choosing, not doing — a quarter of both traces is spent here.',
    example: '"Maybe I can break 4,621,821 into 4,000,000 + 600,000 + 20,000 + ..."',
  },
  PARTIAL_PRODUCT: {
    label: 'Partial',
    color: '#8fa8cb',
    symbol: '×',
    ooda: ['act'],
    description: 'Computing one piece: a digit times a chunk, one row of the long multiplication.',
    example: '"80,379,530 × 8 = 643,036,240. Then × 100 = 64,303,624,000."',
  },
  ACCUMULATE: {
    label: 'Sum',
    color: '#3f5f92',
    symbol: '+',
    ooda: ['act'],
    description:
      'Aligning and adding the partial products. One long dependent chain, where a single misalignment carries to the end.',
    example: '"371,499,719,344,600 + 80,379,530 = ..."',
  },
  STATE_TRACKING: {
    label: 'State',
    color: '#adb2b8',
    symbol: 'T',
    ooda: ['orient'],
    description: 'Naming where it is — which chunk, which power of ten. Bookkeeping, not computing.',
    example: '"Digits: 4 (millions), 6 (hundred thousands), 2 (ten thousands), ..."',
  },
  RECHECK: {
    label: 'Recheck',
    color: '#f0b45f',
    symbol: 'R',
    ooda: ['observe'],
    description:
      'Re-deriving something by the same method. The faculty that produced the error is the one checking it, so it catches transcription slips and nothing else.',
    example: '"Term1: correct. Term2: correct. Term3: correct. ..."',
  },
  CROSSCHECK: {
    label: 'Crosscheck',
    color: '#17624f',
    symbol: 'C',
    ooda: ['observe'],
    description:
      'Validating by a method with different failure modes: casting out nines, any modulus, last digit, digit count, magnitude. The only kind that can see what the first pass missed — and only as deep as the modulus it reaches.',
    example: '"87 mod 9 = 6, which matches the expected 6."',
  },
  ERROR_CORRECTION: {
    label: 'Correction',
    color: '#d4503c',
    symbol: '!',
    ooda: ['decide'],
    description:
      'Detecting a specific error and changing a value. Neither trace in this post contains one — 128 segments, two false alarms, zero corrections.',
    example: '(unobserved)',
  },
  RESULT: {
    label: 'Result',
    color: '#5d574d',
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

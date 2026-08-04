/**
 * The sixteen categories a reasoning-grid thinking trace is labelled with.
 *
 * Derived from the traces themselves, not adapted from another study. The
 * previous set of nine came from a post about a different model on a different
 * task and was kept at nine "to stay comparable with the λ chart"; two of those
 * nine named behaviours this task does not produce, and one absorbed five
 * distinct moves. Provenance and the case against it:
 * ../../../../labels/v1-lambda-derived/README.md
 *
 * Rubric, decision rules and results:
 * ../../../../.agents/reference/label-rubric-qwen-multiplication.md
 *
 * Each category maps to exactly ONE OODA phase. The previous scheme had one
 * category in two phases, which is how a mapping stops being a function and how
 * "there is no decide phase" became sayable.
 *
 * Colour, three rules in order:
 *
 * 1. THE THREE KINDS OF CHECK are the argument, so they carry the saturated
 *    colours and are separated on hue, temperature and VALUE at once. REDERIVE
 *    against CROSSCHECK is the pair that decides two of the four traces, and the
 *    value gap is what keeps them apart in greyscale and for the ~8% of men with
 *    red-green deficiency, for whom hue alone may carry nothing. Ratios are
 *    measured by scripts/check-contrast.mjs, not asserted: the previous palette
 *    claimed a separation it did not have until it was measured.
 * 2. THE DECIDE GROUP is the finding this rebuild exists for, so REVISE and
 *    STALL are given distinct hues rather than greys — a run that changed its
 *    mind and a run that could not must not read as the same colour.
 * 3. EVERYTHING ELSE is chromatically quiet and separated by value. ACT borrows
 *    the reliability surface's blue ramp, so doing the arithmetic looks the same
 *    in this figure as in the grid.
 *
 * LOOP is near-white on purpose. It is 43% of all segments and 69% of one trace,
 * and it is the absence of work. Any colour with weight in it would make the
 * locked-up run look busy, which is precisely the error the previous labels made
 * by scoring those segments as arithmetic.
 *
 * The `description` strings are the rubric's operational definitions, written to
 * be checkable rather than to be read as prose. They are what the legend and the
 * tooltips show.
 */

export const CARRY_CATEGORIES = [
  // running the algorithm
  'FRAME',
  'SURVEY',
  'COMMIT',
  'ABANDON',
  'PRODUCT',
  'SCALE',
  'SUM',
  'REPORT',
  // checking the work
  'REDERIVE',
  'CROSSCHECK',
  'SCALE_CHECK',
  'CHECK_FLOATED',
  // when a check disagrees
  'ALARM',
  'REVISE',
  'STAND',
  'STALL',
  'LOOP',
  'NONE',
] as const;

export type CarryCategory = (typeof CARRY_CATEGORIES)[number];

/** Which loop phase a category belongs to. Exactly one, never two. */
export type Ooda = 'observe' | 'orient' | 'decide' | 'act' | 'none';

export type CarryCategoryMeta = {
  readonly label: string;
  readonly color: string;
  readonly symbol: string;
  readonly ooda: Ooda;
  readonly description: string;
  readonly example: string;
};

export const carryCategoryMeta = {
  // ---- running the algorithm -------------------------------------------
  FRAME: {
    label: 'Frame',
    color: '#948d80',
    symbol: 'F',
    ooda: 'observe',
    description: 'Restating the problem: writing the operands down, counting their digits.',
    example: '"I need to compute the exact product of 80,379,530 and 4,621,821."',
  },
  SURVEY: {
    label: 'Survey',
    color: '#ddd5c4',
    symbol: '?',
    ooda: 'orient',
    description: 'Naming a way to proceed without taking it. No work follows.',
    example: '"Alternatively, maybe I could factor out something."',
  },
  COMMIT: {
    label: 'Commit',
    color: '#b8925a',
    symbol: '>',
    ooda: 'decide',
    description: 'Taking a specific decomposition and proceeding with it.',
    example: '"Let me write 30,957,123,778 as 30,000,000,000 + 957,123,778."',
  },
  ABANDON: {
    label: 'Abandon',
    color: '#a2937c',
    symbol: 'x',
    ooda: 'decide',
    description: 'Dropping a decomposition part-way.',
    example: '"This is getting really complex. Maybe I need another way."',
  },
  PRODUCT: {
    label: 'Partial',
    color: '#8fa8cb',
    symbol: '×',
    ooda: 'act',
    description: 'Computing one piece: a digit or chunk times the other operand.',
    example: '"80,379,530 × 8 = 643,036,240."',
  },
  SCALE: {
    label: 'Scale',
    color: '#6b84b0',
    symbol: '^',
    ooda: 'act',
    description:
      'Producing a value by a power of ten, with no addition performed: shifts, appended zeros, scientific notation.',
    example: '"6,161,688 × 10^10 = 6.161688 × 10^16."',
  },
  SUM: {
    label: 'Sum',
    color: '#3f5f92',
    symbol: '+',
    ooda: 'act',
    description: 'Adding the pieces: alignment, carries, running totals — including any shift done in order to line them up.',
    example: '"371,499,719,344,600 + 80,379,530 = 371,499,719,424,970."',
  },
  REPORT: {
    label: 'Report',
    color: '#5d574d',
    symbol: '=',
    ooda: 'act',
    description: 'Stating the final product, and all text after the thinking ends.',
    example: '"Therefore, the exact product is 371,499,719,424,970."',
  },

  // ---- checking the work -----------------------------------------------
  REDERIVE: {
    label: 'Re-derive',
    color: '#f0b45f',
    symbol: 'R',
    ooda: 'observe',
    description:
      'Computing a value again by the same method. The faculty that made the error is the one checking, so it catches transcription slips and nothing else.',
    example: '"Term1: correct. Term2: correct. Term3: correct."',
  },
  CROSSCHECK: {
    label: 'Crosscheck',
    color: '#17624f',
    symbol: 'C',
    ooda: 'observe',
    description:
      'Testing the digits by a method that fails differently: casting out nines, any modulus, last digit. The only kind that can see what the first pass missed.',
    example: '"87 mod 9 = 6, which matches the expected 6."',
  },
  SCALE_CHECK: {
    label: 'Scale check',
    color: '#7fb3a3',
    symbol: 'S',
    ooda: 'observe',
    description:
      'Testing the size rather than the digits: expected digit count, rough magnitude, a scientific-notation comparison. Blind to any error that does not move the exponent.',
    example: '"8 digits times 7 digits should give 15. It has 15."',
  },
  CHECK_FLOATED: {
    label: 'Check floated',
    color: '#e8dcc0',
    symbol: '~',
    ooda: 'orient',
    description: 'Naming a check and not running it.',
    example: '"Maybe I could verify with modular arithmetic." (nothing follows)',
  },

  // ---- when a check disagrees ------------------------------------------
  ALARM: {
    label: 'Alarm',
    color: '#d98c3f',
    symbol: '!',
    ooda: 'orient',
    description: 'Asserting that something may be wrong, or that two values disagree.',
    example: '"There’s an error here! The last digit should be 0."',
  },
  REVISE: {
    label: 'Revise',
    color: '#d4503c',
    symbol: '↺',
    ooda: 'decide',
    description:
      'Changing a value already written down, including superseding an accepted total with a competing one.',
    example: '"This is a mistake. The correct value is 6.6925 × 10^15."',
  },
  STAND: {
    label: 'Stand',
    color: '#96a68a',
    symbol: '✓',
    ooda: 'decide',
    description: 'Examining an alarm and concluding nothing changes. The false alarm, resolved.',
    example: '"So 970 ends with 0. That’s correct. No problem there."',
  },
  STALL: {
    label: 'Stall',
    color: '#9b7fa8',
    symbol: '↻',
    ooda: 'decide',
    description:
      'Holding a conflict open: re-checking a side already checked, restating the disagreement, settling nothing.',
    example: '"But according to the other method it is different. Where is the mistake?"',
  },
  LOOP: {
    label: 'Locked up',
    color: '#dedad2',
    symbol: '∞',
    ooda: 'none',
    description:
      'The same text again with no new content. Computed by script, never judged: three or more identical consecutive segments, plus a truncated repeat where the context ran out.',
    example: '"Let me add 42,177,834,871,396 to 31,633,376,153,547,000:" (×276)',
  },
  NONE: {
    label: 'Unclassified',
    color: '#c9b8b0',
    symbol: '·',
    ooda: 'none',
    description:
      'No category fit. Two segments of 636: factorising an operand to hunt for a shortcut, and declaring the work finished without naming a value. Both are real moves this scheme does not yet name, and they are drawn rather than hidden — a rubric that reports no misfits is not being tested.',
    example: '"Let me factorize 21028. 21028 = 2² × 7 × 751."',
  },
} as const satisfies Record<CarryCategory, CarryCategoryMeta>;

export const OODA_LABEL: Record<Ooda, string> = {
  observe: 'Observe',
  orient: 'Orient',
  decide: 'Decide',
  act: 'Act',
  none: 'Outside the loop',
};

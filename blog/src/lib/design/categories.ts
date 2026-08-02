/**
 * Cognitive categories for thinking trace classification.
 * Ported from statistics/annotate_steps.py.
 *
 * Uses readonly tuples and `as const` to keep the category list immutable
 * at the type level. `satisfies Record<Category, ...>` ensures every category
 * has metadata, catching missing entries at compile time.
 */

// Readonly tuple — preserves literal types and enforces exhaustiveness
export const CATEGORIES = [
  'TASK_SETUP',
  'PROCEDURAL_TRACKING',
  'ARITHMETIC',
  'EXECUTION',
  'DECOMPOSITION',
  'VERIFICATION',
  'ERROR_CORRECTION',
  'SURRENDER',
  'SURRENDER_DELIBERATION',
] as const;

export type Category = (typeof CATEGORIES)[number];

export type CategoryMeta = {
  readonly label: string;
  readonly color: string;
  readonly symbol: string;
  readonly description: string;
  readonly example: string;
};

export const categoryMeta = {
  TASK_SETUP: {
    label: 'Setup',
    color: '#6c757d',
    symbol: 'S',
    description: 'Reading the problem and restating what needs to be done.',
    example: '"The user wants me to compute 415^22 mod 601 using repeated squaring."',
  },
  PROCEDURAL_TRACKING: {
    label: 'State',
    color: '#0d6efd',
    symbol: 'T',
    description:
      "Managing algorithm state — tracking which bit we're on, what variable holds what, where we are in a multi-step computation. Scratchpad reads and writes of intermediate values.",
    example: '"22 in binary is 10110" or "So 415^4 mod 601 = 238" or "bit 3 (2^3): 0"',
  },
  ARITHMETIC: {
    label: 'Arithmetic',
    color: '#198754',
    symbol: 'A',
    description:
      'Raw computation — multiplying, dividing, adding, subtracting. The mechanical number-crunching between state-tracking steps.',
    example: '"539 * 539 = 290,521" or "172,225 - 171,686 = 539"',
  },
  EXECUTION: {
    label: 'Execution',
    color: '#adb5bd',
    symbol: '.',
    description:
      "Connective tissue — transitions between steps that don't fit a more specific category. 'Now,' 'next,' 'moving on.'",
    example: '"Let me start:" or "Now I\'ll use repeated squaring."',
  },
  DECOMPOSITION: {
    label: 'Decomposition',
    color: '#fd7e14',
    symbol: 'D',
    description:
      'Choosing how to break a problem into smaller pieces. Strategy selection for the structure of the computation, not the computation itself.',
    example: '"I\'ll split each 50-digit number into two 25-digit chunks"',
  },
  VERIFICATION: {
    label: 'Verification',
    color: '#6f42c1',
    symbol: 'V',
    description:
      'Checking work — going back to confirm a result is correct, or using a separate method (like mod 9) to validate.',
    example: '"Let me verify this works" or "checking mod 9 for a digit sum check"',
  },
  ERROR_CORRECTION: {
    label: 'Error Correction',
    color: '#dc3545',
    symbol: '!',
    description:
      'Catching and fixing a mistake. The model notices something is wrong and recalculates. Always corrects arithmetic, never changes strategy.',
    example: '"Wait, let me recalculate" or "Actually, that\'s not right — I made a carry error"',
  },
  SURRENDER: {
    label: 'Surrender',
    color: '#e63946',
    symbol: 'X',
    description:
      'Giving up. The model decides the problem is too hard, based on how the problem looks — not on actual analysis of difficulty.',
    example: '"These numbers are enormous... Computing this truly by hand would be extremely error-prone."',
  },
  SURRENDER_DELIBERATION: {
    label: 'Deliberation',
    color: '#f4845f',
    symbol: '~',
    description:
      'Going back and forth about whether to attempt the problem. The model is caught between following instructions and its judgment that the task is hopeless.',
    example: '"I keep going back and forth on this — the constraint is clear about no tools, but..."',
  },
} as const satisfies Record<Category, CategoryMeta>;

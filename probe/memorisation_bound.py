"""Could the grid have been memorised instead of computed?

The post claims the model works the multiplication out rather than recalling it.
That claim is cheap to settle, because the number of distinct problems in the
grid is countable and the number of parameters is published, and one is very
much larger than the other.

Counting rule: an n-digit number runs from 10^(n-1) to 10^n - 1, so there are
9 * 10^(n-1) of them. Pairs are ORDERED, because `a x b` and `b x a` are
different prompts and the grid keeps them apart -- see the operand-order
pre-registration.

The generous assumptions all favour memorisation, and it still loses:

  - only the ANSWER is stored, never the question
  - perfect packing, no addressing overhead, no redundancy
  - one parameter can hold one whole answer

The headline is not the 14x14 total. It is that the argument is already over at
one digit by nine digits, which is a single cell in the first row.

Run: python3 probe/memorisation_bound.py
"""

from __future__ import annotations

MAX_DIGITS = 14

# The model in the grid. Named rather than left as "the model", because the
# comparison is only true for a specific parameter count and a reader checking
# it needs to know which.
MODEL_NAME = "Qwen3-4B"
MODEL_PARAMS = 4e9

# Order of magnitude for a modern pretraining corpus. Used only to show that the
# problem count dwarfs the training data too, so it carries no precision.
TRAIN_TOKENS = 3.6e13


def numbers_with(digits: int) -> int:
    """How many integers have exactly this many digits."""
    return 9 * 10 ** (digits - 1)


def problems_in_cell(n: int, m: int) -> int:
    return numbers_with(n) * numbers_with(m)


def main() -> None:
    total = 0
    answer_digits = 0
    for n in range(1, MAX_DIGITS + 1):
        for m in range(1, MAX_DIGITS + 1):
            pairs = problems_in_cell(n, m)
            total += pairs
            # A product of an n-digit and an m-digit number has n+m digits or
            # one fewer. Taking the larger is the generous direction only for
            # storage cost, so it is stated rather than quietly rounded.
            answer_digits += pairs * (n + m)

    print(f"grid                                  1x1 to {MAX_DIGITS}x{MAX_DIGITS} digits")
    print(f"distinct problems                     {total:.3e}")
    print(f"digits to write every answer          {answer_digits:.3e}")
    print(f"bytes, packed, answers only           {answer_digits * 3.32 / 8:.3e}")
    print()
    print(f"{MODEL_NAME} parameters{'':<15} {MODEL_PARAMS:.3e}")
    print(f"  problems per parameter              {total / MODEL_PARAMS:.3e}")
    print(f"pretraining tokens, order of          {TRAIN_TOKENS:.3e}")
    print(f"  problems per training token         {total / TRAIN_TOKENS:.3e}")
    print()

    # The sentence the post actually uses. Found rather than asserted, so that
    # editing MAX_DIGITS or MODEL_PARAMS cannot leave the prose behind.
    for n in range(1, MAX_DIGITS + 1):
        for m in range(1, MAX_DIGITS + 1):
            pairs = problems_in_cell(n, m)
            if pairs > MODEL_PARAMS:
                print(
                    f"first cell that already exceeds the parameter count:\n"
                    f"  {n} digit x {m} digit = {pairs:.3e} problems, "
                    f"{pairs / MODEL_PARAMS:.1f}x {MODEL_NAME}"
                )
                return


if __name__ == "__main__":
    main()

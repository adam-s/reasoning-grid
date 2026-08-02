/**
 * A category scheme — the set of labels a flame chart colours by, plus their
 * metadata, passed to the chart instead of imported by it.
 *
 * The flame components arrived from the λ-bench post importing `categoryMeta`
 * directly, which meant they could only ever render λ's nine categories.
 * carrychain has a different nine (see carrychain-categories.ts), so the chart
 * has to take the scheme as an input. It is a prop with the λ scheme as the
 * default, so the reference figure renders exactly as it did before and no
 * existing call site changes.
 *
 * Rows are typed structurally rather than by a literal union. A chart does not
 * need to know which nine strings are legal — it needs a colour for the string
 * it was handed, and a scheme that is missing one is a data bug, not something
 * to catch by narrowing the component's type.
 */

export type SchemeMeta = {
  readonly label: string;
  readonly color: string;
  readonly symbol: string;
  readonly description: string;
  readonly example?: string;
};

export type CategoryScheme = {
  /** Legend order. Categories absent from the data are dropped at render. */
  readonly order: readonly string[];
  readonly meta: Readonly<Record<string, SchemeMeta>>;
  /** Fallback for a category the scheme does not define. */
  readonly fallback: SchemeMeta;
};

/** The shape a flame row must have. Both FlameRow and CarryFlameRow satisfy it. */
export type AnyFlameRow = {
  readonly depth: number;
  readonly start: number;
  readonly width: number;
  readonly category: string;
  readonly label: string;
  readonly text: string;
  readonly index: number;
  /** Render as background structure rather than signal. Container rows use it:
   *  their category is only the dominant one among their children, sometimes a
   *  plurality as low as a third, which is a hint and not a claim. */
  readonly muted?: boolean;
};

export type AnyTrace = {
  readonly name?: string;
  readonly rows: readonly AnyFlameRow[];
};

const UNKNOWN: SchemeMeta = {
  label: 'Unclassified',
  color: '#b8b3a8',
  symbol: '?',
  description: 'No category was assigned to this segment.',
};

export function metaFor(scheme: CategoryScheme, category: string): SchemeMeta {
  return scheme.meta[category] ?? scheme.fallback;
}

import { CATEGORIES, categoryMeta } from './categories';
import { CARRY_CATEGORIES, carryCategoryMeta } from './carrychain-categories';

export const LAMBDA_SCHEME: CategoryScheme = {
  order: CATEGORIES,
  meta: categoryMeta,
  fallback: UNKNOWN,
};

export const CARRY_SCHEME: CategoryScheme = {
  order: CARRY_CATEGORIES,
  meta: carryCategoryMeta,
  fallback: UNKNOWN,
};

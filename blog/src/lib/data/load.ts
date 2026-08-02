// SCAFFOLD. Fetches the reduced JSON that probe/reduce_grid.py writes.
// Nothing here parses raw records -- the browser never sees a raw generation.
// See blog/README.md, "The data path".

export type Cell = {
  a: number; b: number; N: number;
  k: number; n: number; p: number; lo: number; hi: number;
  n_ceiling_bound: number; valid: boolean;
  outcomes: Record<string, number>;
  tok_mean: number; tok_max: number;
};

export type Sweep = {
  sweep: string;
  records: number;
  models: Record<string, { n_records: number; n_cells: number; cells: Record<string, Cell> }>;
  paired?: {
    model_a: string; model_b: string;
    totals: { both_right: number; only_a: number; only_b: number; both_wrong: number };
    n_paired: number; mcnemar_chi2: number;
    per_cell: Record<string, Record<string, number>>;
  };
};

export async function loadSweep(name: string): Promise<Sweep> {
  const r = await fetch(`./data/${name}.json`);
  if (!r.ok) throw new Error(`${name}.json: ${r.status}`);
  return r.json();
}

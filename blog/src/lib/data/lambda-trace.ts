/**
 * ONE trace, copied unmodified from the agent-capability-threshold
 * `sonnet-variance-demo` branch (src/lib/data/variance-traces.ts, run 1 of 5).
 *
 * Sonnet 4.6 at low effort on the official LamBench `algo_evl` task -- writing a
 * lambda-calculus evaluator in lambda calculus. The nested-range tree and the
 * per-segment categories were both produced by Opus 4.6; depth comes from
 * containment.
 *
 * Nothing here is carrychain data. It is the reference implementation of the
 * figure -- the shape we will fill with our own traces once they are annotated.
 */
import type { Category } from '../design/categories';

export type FlameRow = {
  readonly depth: number;
  readonly start: number;
  readonly width: number;
  readonly category: Category;
  readonly label: string;
  readonly text: string;
  readonly index: number;
};

type AlgorithmId =
  | 'multiplication'
  | 'modular-exponentiation'
  | 'search-backtracking'
  | 'program-tracing'
  | 'calculus'
  | 'sequential-tasks'
  | 'novel-reasoning';

export type AnnotatedTrace = {
  readonly name: string;
  readonly model: 'haiku' | 'sonnet' | 'opus';
  readonly algorithmId: AlgorithmId;
  readonly detail: string;
  readonly stepCount: number;
  readonly elapsedSeconds?: number;
  readonly outputTokens?: number;
  readonly rows: ReadonlyArray<FlameRow>;
};

export const LAMBDA_TRACE: AnnotatedTrace = {
    "name": "sonnet-lambda-run-1",
    "model": "sonnet",
    "algorithmId": "novel-reasoning",
    "detail": "run 1",
    "stepCount": 49,
    "elapsedSeconds": 206.2,
    "outputTokens": 13311,
    "rows": [
      {
        "depth": 2,
        "start": 0.0,
        "width": 160.94,
        "category": "TASK_SETUP",
        "label": "Setup",
        "text": "This is a lambda calculus meta-interpreter problem. I need to write a lambda calculus evaluator in lambda calculus itself, using Scott encoding for terms and de Bruijn indices.",
        "index": 0
      },
      {
        "depth": 2,
        "start": 160.94,
        "width": 32.92,
        "category": "EXECUTION",
        "label": "Execution",
        "text": "Let me think through this carefully.",
        "index": 1
      },
      {
        "depth": 2,
        "start": 193.85,
        "width": 15.54,
        "category": "TASK_SETUP",
        "label": "Setup",
        "text": "## Encoding recap",
        "index": 2
      },
      {
        "depth": 3,
        "start": 209.4,
        "width": 12.8,
        "category": "TASK_SETUP",
        "label": "Setup",
        "text": "**Scott nat:**",
        "index": 3
      },
      {
        "depth": 3,
        "start": 222.2,
        "width": 11.89,
        "category": "TASK_SETUP",
        "label": "Setup",
        "text": "- Z = λs.λz.z",
        "index": 4
      },
      {
        "depth": 3,
        "start": 234.09,
        "width": 17.37,
        "category": "TASK_SETUP",
        "label": "Setup",
        "text": "- S(n) = λs.λz.s(n)",
        "index": 5
      },
      {
        "depth": 3,
        "start": 251.46,
        "width": 24.69,
        "category": "TASK_SETUP",
        "label": "Setup",
        "text": "**Scott term (3-variant):**",
        "index": 6
      },
      {
        "depth": 3,
        "start": 276.15,
        "width": 34.75,
        "category": "TASK_SETUP",
        "label": "Setup",
        "text": "- Lam(body) = λlam.λapp.λvar.lam(body)",
        "index": 7
      },
      {
        "depth": 3,
        "start": 310.9,
        "width": 41.15,
        "category": "TASK_SETUP",
        "label": "Setup",
        "text": "- App(fun,arg) = λlam.λapp.λvar.app(fun)(arg)",
        "index": 8
      },
      {
        "depth": 3,
        "start": 352.05,
        "width": 32.92,
        "category": "TASK_SETUP",
        "label": "Setup",
        "text": "- Var(idx) = λlam.λapp.λvar.var(idx)",
        "index": 9
      },
      {
        "depth": 3,
        "start": 384.96,
        "width": 24.69,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "## What I need to implement",
        "index": 10
      },
      {
        "depth": 3,
        "start": 409.65,
        "width": 260.61,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Beta-normal form evaluator with de Bruijn indices. The key operations are substitution (replacing a variable at a specific depth while shifting free variables in the replacement), shifting (adjusting free variable indices when they exceed a cutoff), and evaluation to beta-normal form.",
        "index": 11
      },
      {
        "depth": 3,
        "start": 670.26,
        "width": 186.54,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "For normal-order reduction, I need to handle lambda abstractions by returning them as-is, applications by evaluating the function and then applying it, and variables by looking them up in the environment.",
        "index": 12
      },
      {
        "depth": 3,
        "start": 856.8,
        "width": 225.86,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "But full beta-normal form requires a two-stage approach: weak head normal form to reduce the outermost redex, then recursively normalize the body and arguments. This ensures I normalize under lambdas and in all subterms, not just at the top level.",
        "index": 13
      },
      {
        "depth": 3,
        "start": 1082.66,
        "width": 34.75,
        "category": "EXECUTION",
        "label": "Execution",
        "text": "Defining the normalization function...",
        "index": 14
      },
      {
        "depth": 3,
        "start": 1117.4,
        "width": 472.75,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Actually, I'll simplify this—just reduce step by step until no more redexes exist. To implement this in pure lambda calculus, I need to encode the core machinery: arithmetic on Scott numerals for de Bruijn index manipulation, the shift operation, substitution, and the evaluator itself. This is getting intricate, so let me map out the essential building blocks first. I'll start with Church encodings for booleans and natural numbers, then layer in the comparison and arithmetic operations needed for index handling.",
        "index": 15
      },
      {
        "depth": 3,
        "start": 1590.15,
        "width": 309.07,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "For de Bruijn indices specifically, I need equality and less-than checks on natural numbers. The equality function would be recursive, which means I'll need a fixpoint combinator like Y or Z to handle the recursion in pure lambda calculus. call-by-value if needed, but since we're in pure lambda calculus with normal order, Y should work.",
        "index": 16
      },
      {
        "depth": 3,
        "start": 1899.22,
        "width": 101.5,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Let me write this more carefully. I'll use a `let` notation where `let f = body in ...` means `(λf. ...) body`.",
        "index": 17
      },
      {
        "depth": 3,
        "start": 2000.72,
        "width": 402.34,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "I'm defining the Y combinator for recursion, along with Church booleans and Scott-encoded natural numbers with their destructors. Now I'm working through the comparison operations—starting with equality, then moving to less-than. For the less-than function, I need to think through the cases: when n is zero, nothing is less than it, but when n is a successor, I check if m is zero (true) or if m's predecessor is less than n's predecessor.",
        "index": 18
      },
      {
        "depth": 3,
        "start": 2403.06,
        "width": 38.41,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Defining natLt with the recursive cases...",
        "index": 19
      },
      {
        "depth": 4,
        "start": 2441.46,
        "width": 581.56,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Now I'm thinking about the substitution and shifting operations needed for de Bruijn indices. The key insight is that shift adds a constant to all free variables above a certain cutoff, and substitution replaces a specific variable with a term while adjusting indices appropriately. I'm working through the substitution and shifting operations more carefully. The shift function adjusts variable indices when they're at or above a certain threshold, incrementing or decrementing by some amount to account for binding depth changes. Since the shift amount is typically just 1 or -1, I'm considering how to handle those cases efficiently.",
        "index": 20
      },
      {
        "depth": 4,
        "start": 3023.02,
        "width": 654.71,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "For beta reduction specifically, when substituting an argument into a lambda body, I need to shift the argument by the current binding depth before substituting it for the matching variable, then decrement all higher-indexed variables. The key insight is that the shift operation during substitution depends on how many enclosing binders we've traversed. I'm realizing the issue: when we substitute and hit a matching variable, we return `shift 0 j arg`, but we need to account for the depth we've descended into the lambda nesting. Instead of shifting arg at substitution time, I should accumulate the depth as I traverse down through lambdas, then apply that accumulated shift to arg when we finally substitute it.",
        "index": 21
      },
      {
        "depth": 4,
        "start": 3677.74,
        "width": 241.4,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "So I'll track a `lift` parameter that increments each time we enter a lambda, and when we find the variable to substitute, we shift arg by that accumulated lift amount. This way the shift operation needs to handle arbitrary natural numbers, not just fixed amounts.",
        "index": 22
      },
      {
        "depth": 4,
        "start": 3919.14,
        "width": 37.49,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Implementing shift with Scott numerals...",
        "index": 23
      },
      {
        "depth": 4,
        "start": 3956.63,
        "width": 258.78,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "I'm realizing I need to track the depth explicitly as I recurse through the term structure, then apply the appropriate shift at substitution points. Let me work through the lambda calculus implementation with Scott-encoded naturals and helper functions for shifting and substitution.",
        "index": 24
      },
      {
        "depth": 3,
        "start": 4215.41,
        "width": 28.35,
        "category": "EXECUTION",
        "label": "Execution",
        "text": "Defining the core operations...",
        "index": 25
      },
      {
        "depth": 3,
        "start": 4243.76,
        "width": 587.96,
        "category": "PROCEDURAL_TRACKING",
        "label": "State",
        "text": "Now I'm implementing the shift operation to handle variable index adjustments when moving deeper into lambda abstractions, incrementing indices that fall outside the current scope while preserving those that don't. Continuing with the substitution logic for variables: when the index matches the target, I substitute and shift the argument by the appropriate depth; if it's smaller, the variable stays unchanged; if it's larger, I decrement it to account for the removed binding. Then for the evaluator, I'm reducing terms to beta-normal form by recursively normalizing lambda bodies and applying substitution when a function is fully reduced.",
        "index": 26
      },
      {
        "depth": 3,
        "start": 4831.72,
        "width": 267.92,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Now I'm second-guessing the eval logic—specifically when `f'` reduces to a lambda, I need to make sure the substitution is happening correctly. If `f` is already a lambda, then reducing it gives me the normalized body, and I should substitute the argument into that body and continue reducing.",
        "index": 27
      },
      {
        "depth": 3,
        "start": 5099.64,
        "width": 441.66,
        "category": "ERROR_CORRECTION",
        "label": "Error Correction",
        "text": "Actually, I think the issue is that I'm normalizing the lambda body upfront, which forces full evaluation before application. Instead, I should reduce the function to weak head normal form first—just enough to see if it's a lambda or a stuck term—then decide whether to beta-reduce or normalize further. Let me split this into two functions: one that reduces to weak head normal form without going under lambdas, and another that fully normalizes by recursively normalizing subterms.",
        "index": 28
      },
      {
        "depth": 3,
        "start": 5541.3,
        "width": 41.15,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Defining the weak head normal form reducer...",
        "index": 29
      },
      {
        "depth": 3,
        "start": 5582.45,
        "width": 27.43,
        "category": "EXECUTION",
        "label": "Execution",
        "text": "Still writing reducer logic...",
        "index": 30
      },
      {
        "depth": 3,
        "start": 5609.88,
        "width": 371.25,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Now I'm realizing the problem: when I call weak head normal form on a term and then pattern match on the result, I need to be careful about what gets reduced. If I have an application, weak head normal form will reduce the function part, but then in the full normalizer I'm calling weak head normal form again on an already-reduced term, which might cause issues with how I'm handling the pattern matching.",
        "index": 31
      },
      {
        "depth": 3,
        "start": 5981.13,
        "width": 366.68,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Let me trace through an example to verify this works correctly. If I normalize an application of a lambda to an argument, weak head normal form will reduce the function to a lambda, then beta-reduce the body. The result of that reduction is already in weak head normal form, so when the normalizer pattern matches on it, it can then recursively normalize the subterms. This should actually be correct.",
        "index": 32
      },
      {
        "depth": 3,
        "start": 6347.8,
        "width": 461.77,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Looking at the normalizer's cases: when it encounters a lambda, it normalizes the body; when it encounters an application that's already stuck (since weak head normal form would have reduced it if it weren't), it normalizes both the function and argument separately. The function can't be a lambda at this point since weak head normal form would have already reduced any outermost redexes. So this approach seems sound, though there's something subtle I'm still working through about the application case.",
        "index": 33
      },
      {
        "depth": 3,
        "start": 6809.58,
        "width": 510.24,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Now checking the substitution function: it shifts the binding level when entering a lambda, and for variables it either returns the argument (shifted appropriately if it matches the binding level), keeps the variable unchanged if it's bound at an outer level, or decrements it if it's bound at an inner level. The key insight is that when we beta-reduce an application of a lambda to an argument, we need to substitute the argument into the body while accounting for how the free variables in the argument should be shifted relative to the binding structure.",
        "index": 34
      },
      {
        "depth": 3,
        "start": 7319.82,
        "width": 356.62,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Now I'm verifying the `natLt` comparison: it should return true when the first argument is strictly less than the second. In the shift operation, when we encounter a variable at index `i`, we check if it's bound by the current lambda using `natLt i c`—if true, the variable is bound so we keep it; otherwise it's free and we increment it to account for the new binding level we're crossing.",
        "index": 35
      },
      {
        "depth": 3,
        "start": 7676.43,
        "width": 291.7,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "For substitution, the logic chains through three cases: if the variable index matches the target depth, we substitute; if it's less than the target depth, it's bound by an outer lambda so we keep it unchanged; if it's greater, it's bound by an inner lambda so we decrement it to account for removing that binding level.",
        "index": 36
      },
      {
        "depth": 3,
        "start": 7968.13,
        "width": 89.61,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "I'm now checking the `shiftN` function, which applies the shift operation recursively `n` times...",
        "index": 37
      },
      {
        "depth": 3,
        "start": 8057.74,
        "width": 682.15,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Actually, I'm realizing there might be a subtle issue with how `whnf` and `nf` interact. When `whnf` reduces the outermost redex and returns a result, that result's subterms might not be in weak head normal form themselves—only the top-level structure has been reduced. So when I pattern match on an `App` in the result, those components could still contain unreduced redexes that need further normalization. Since `f'` is already in weak head normal form, calling `whnf` on it again just returns it unchanged, then I normalize the subterms recursively. This approach terminates for strongly normalizing terms because each beta reduction step decreases the term size, and the structural recursion in `nf` ensures we eventually reach normal forms.",
        "index": 38
      },
      {
        "depth": 3,
        "start": 8739.89,
        "width": 114.3,
        "category": "EXECUTION",
        "label": "Execution",
        "text": "Now I'm writing out the final lambda calculus program with definitions for the Y combinator, booleans, and Church numerals...",
        "index": 39
      },
      {
        "depth": 3,
        "start": 8854.19,
        "width": 86.87,
        "category": "EXECUTION",
        "label": "Execution",
        "text": "Defining the Church encoding functions... Continuing with the lambda calculus implementation...",
        "index": 40
      },
      {
        "depth": 3,
        "start": 8941.06,
        "width": 552.3,
        "category": "ERROR_CORRECTION",
        "label": "Error Correction",
        "text": "I'm noticing an issue with how I'm handling the `let` binding inside the App case of the weak head normal form function. Since pure lambda calculus doesn't have `let` syntax, I need to convert that binding into a direct lambda application where the reduced function gets passed as an argument to handle the three pattern cases for the result. I'm completing the whnf function with the remaining cases for handling variables, then defining nf to normalize the full term by first reducing to weak head normal form and then recursively normalizing subterms. Let me verify this works with a concrete example.",
        "index": 41
      },
      {
        "depth": 4,
        "start": 9493.36,
        "width": 210.31,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Testing `(λx.x) y` where both are encoded as variables: I'm walking through the whnf reduction step by step, applying beta reduction when the function is a lambda, and checking that substitution correctly handles variable binding.",
        "index": 42
      },
      {
        "depth": 4,
        "start": 9703.67,
        "width": 719.64,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Now I'm working through a second example with `(λx.x) (λy.y)` — applying the identity function to another lambda abstraction to verify the normalization handles nested functions correctly. Tracing through a more complex example with function composition: applying `(λf.λx.f x)` to `(λy.y)` should reduce to `(λx.x)` after normalization. I'm working through the beta reduction step where the argument gets substituted into the lambda body, then checking how the nested substitution handles the variable indices correctly. I'm verifying the substitution and normalization steps work correctly through this example, confirming that applying the identity function to itself reduces to the identity function as expected. Now I'm ready to write out the complete lambda calculus implementation.",
        "index": 43
      },
      {
        "depth": 4,
        "start": 10423.31,
        "width": 291.7,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "I'll present it using named definitions for clarity, since the problem allows for a small set of definitions rather than requiring everything as a single term. Let me lay out the full program with the Church encodings for booleans and natural numbers, the fixed-point combinator for recursion, and the AST constructors.",
        "index": 44
      },
      {
        "depth": 4,
        "start": 10715.0,
        "width": 870.51,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Defining the helper functions for equality and less-than comparisons on natural numbers using recursion, then the shift operations that adjust variable indices when moving terms into lambda abstractions or applications. I'm verifying the logic of the `natEq` function by checking a few key cases: when both numbers are zero it returns true, when one is zero and the other is a successor it returns false, and I'm working through what happens when the first is a successor and the second is zero. Continuing to verify the shift and substitution operations: `shift1` correctly handles lambdas by incrementing the context, applies shifting to both function and argument in applications, and for variables checks if they're bound or free to decide whether to increment. `shiftN` applies `shift1` repeatedly to shift by multiple levels, and `subst` similarly recurses under lambdas with an incremented index while substituting in both parts of applications.",
        "index": 45
      },
      {
        "depth": 4,
        "start": 11585.52,
        "width": 479.15,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "For the variable case in substitution, when the index matches the substitution point I shift the argument's free variables by the current depth, and for indices below or above that point I either keep or decrement them accordingly. The weak head normal form reduces applications by first normalizing the function and beta-reducing if it's a lambda, while lambdas and variables are already in WHNF. Full normalization then reduces to WHNF and recursively normalizes the body of lambdas or both subterms of stuck applications.",
        "index": 46
      },
      {
        "depth": 3,
        "start": 12064.67,
        "width": 891.55,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "I'm verifying that when normalizing a stuck application, calling `nf` on the already-reduced function is correct—since it's already in WHNF, the normalizer will recognize that and just normalize its subterms. The function could be a variable, another application, or something else, but in each case the normalizer handles it properly. the `f'` is already the whnf-reduced function, so when I recursively call `nf` on it, I'm normalizing an already-reduced term, which is correct—the key insight is that `whnf` gives me the reduced function and original argument, and then `nf` needs to normalize both of those to get the fully normal form. In the Lam case, I'm beta-reducing with the original `x` rather than a normalized version, which is correct for weak head normal form since we don't normalize arguments there. And when `nf` later processes the stuck App cases where I return `mkApp f' x`, it will properly normalize `x` at that point, so the overall approach is sound.",
        "index": 47
      },
      {
        "depth": 3,
        "start": 12956.21,
        "width": 354.79,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Now I'm tracing through `shiftN` to verify the shifting logic—applying `shift1` repeatedly `n` times correctly shifts all free variables at or above the cutoff by `n` positions. Then in `subst`, when I call `shiftN Z j arg` with `j` as the substitution depth, the shift amount grows as we go deeper into nested binders, which is exactly what's needed to maintain correct variable indices.",
        "index": 48
      },
      {
        "depth": 0,
        "start": 0.0,
        "width": 13311.0,
        "category": "TASK_SETUP",
        "label": "Setup",
        "text": "Build lambda calculus meta-interpreter",
        "index": 49
      },
      {
        "depth": 1,
        "start": 0.0,
        "width": 193.85,
        "category": "TASK_SETUP",
        "label": "Setup",
        "text": "Identify problem",
        "index": 50
      },
      {
        "depth": 1,
        "start": 193.85,
        "width": 191.11,
        "category": "TASK_SETUP",
        "label": "Setup",
        "text": "Recap Scott encodings",
        "index": 51
      },
      {
        "depth": 1,
        "start": 384.96,
        "width": 1514.26,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Plan required operations",
        "index": 52
      },
      {
        "depth": 1,
        "start": 1899.22,
        "width": 2932.5,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Define core helper functions",
        "index": 53
      },
      {
        "depth": 1,
        "start": 4831.72,
        "width": 1977.86,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Design WHNF and NF evaluator",
        "index": 54
      },
      {
        "depth": 1,
        "start": 6809.58,
        "width": 1930.31,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Verify substitution and comparison logic",
        "index": 55
      },
      {
        "depth": 1,
        "start": 8739.89,
        "width": 4571.11,
        "category": "ERROR_CORRECTION",
        "label": "Error Correction",
        "text": "Write final program and verify",
        "index": 56
      },
      {
        "depth": 2,
        "start": 209.4,
        "width": 42.06,
        "category": "TASK_SETUP",
        "label": "Setup",
        "text": "Define Scott naturals",
        "index": 57
      },
      {
        "depth": 2,
        "start": 251.46,
        "width": 133.5,
        "category": "TASK_SETUP",
        "label": "Setup",
        "text": "Define Scott terms",
        "index": 58
      },
      {
        "depth": 2,
        "start": 384.96,
        "width": 697.69,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Outline evaluation strategy",
        "index": 59
      },
      {
        "depth": 2,
        "start": 1082.66,
        "width": 816.56,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Identify building blocks needed",
        "index": 60
      },
      {
        "depth": 2,
        "start": 1899.22,
        "width": 503.84,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Define Y combinator and booleans",
        "index": 61
      },
      {
        "depth": 2,
        "start": 2403.06,
        "width": 38.41,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Define natLt",
        "index": 62
      },
      {
        "depth": 2,
        "start": 2441.46,
        "width": 1773.95,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Design shift and substitution",
        "index": 63
      },
      {
        "depth": 2,
        "start": 4215.41,
        "width": 616.31,
        "category": "PROCEDURAL_TRACKING",
        "label": "State",
        "text": "Implement shift, substitution, and eval skeleton",
        "index": 64
      },
      {
        "depth": 2,
        "start": 4831.72,
        "width": 709.58,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Identify need for WHNF/NF split",
        "index": 65
      },
      {
        "depth": 2,
        "start": 5541.3,
        "width": 439.83,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Define weak head normal form reducer",
        "index": 66
      },
      {
        "depth": 2,
        "start": 5981.13,
        "width": 828.45,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Trace example to verify WHNF/NF interaction",
        "index": 67
      },
      {
        "depth": 2,
        "start": 6809.58,
        "width": 510.24,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Check substitution cases",
        "index": 68
      },
      {
        "depth": 2,
        "start": 7319.82,
        "width": 648.31,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Verify natLt and variable case logic",
        "index": 69
      },
      {
        "depth": 2,
        "start": 7968.13,
        "width": 89.61,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Check shiftN function",
        "index": 70
      },
      {
        "depth": 2,
        "start": 8057.74,
        "width": 682.15,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Verify WHNF/NF termination",
        "index": 71
      },
      {
        "depth": 2,
        "start": 8739.89,
        "width": 753.47,
        "category": "ERROR_CORRECTION",
        "label": "Error Correction",
        "text": "Write out final definitions",
        "index": 72
      },
      {
        "depth": 2,
        "start": 9493.36,
        "width": 929.95,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Trace concrete examples",
        "index": 73
      },
      {
        "depth": 2,
        "start": 10423.31,
        "width": 1641.36,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Lay out complete program structure",
        "index": 74
      },
      {
        "depth": 2,
        "start": 12064.67,
        "width": 1246.33,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Final verification of normalizer and shiftN",
        "index": 75
      },
      {
        "depth": 3,
        "start": 2441.46,
        "width": 1236.28,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Work through shift operation",
        "index": 76
      },
      {
        "depth": 3,
        "start": 3677.74,
        "width": 278.89,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Track lift parameter for substitution",
        "index": 77
      },
      {
        "depth": 3,
        "start": 3956.63,
        "width": 258.78,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Implement depth-tracking recursion",
        "index": 78
      },
      {
        "depth": 3,
        "start": 9493.36,
        "width": 210.31,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Trace identity applied to variable",
        "index": 79
      },
      {
        "depth": 3,
        "start": 9703.67,
        "width": 719.64,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Trace identity applied to lambda and composition",
        "index": 80
      },
      {
        "depth": 3,
        "start": 10423.31,
        "width": 291.7,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Organize named definitions",
        "index": 81
      },
      {
        "depth": 3,
        "start": 10715.0,
        "width": 870.51,
        "category": "VERIFICATION",
        "label": "Verification",
        "text": "Verify natEq and shift1",
        "index": 82
      },
      {
        "depth": 3,
        "start": 11585.52,
        "width": 479.15,
        "category": "DECOMPOSITION",
        "label": "Decomposition",
        "text": "Verify substitution variable cases and eval",
        "index": 83
      }
    ]
  };

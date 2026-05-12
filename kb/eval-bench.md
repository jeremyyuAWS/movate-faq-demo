# Knowledge base — eval-bench lane

Sourced from movate-cli docs, command `--help` output, and the eval
engine code. Edit this file freely; run
`python scripts/build_prompts.py` to rebuild
`agents/expert-eval-bench/prompt.md`.

## movate eval — score an agent against a dataset

`movate eval <agent>` runs the agent over `evals/dataset.jsonl`,
scores each case with the judge from `evals/judge.yaml`, and prints
a Rich table summary.

Key flags:
- `--gate 0.7` — exit code 1 if pass rate is below threshold. CI-gateable.
- `--gate-mode mean | min | p10` — how to aggregate across multiple runs/case.
  Default `mean`. Use `min` for worst-case bounds, `p10` for robust stats.
- `--runs N` — repeat each case N times (default 1; recommended 3+ for
  LLM-judge since judging is non-deterministic).
- `--baseline <eval-id>` — diff scores vs a stored EvalRecord; exits 1
  on regression past `--regression-tolerance` (default 0.05).

Every eval persists an EvalRecord to storage; the `eval_id` shows in
the footer for later baseline diffs.

## Datasets — evals/dataset.jsonl

JSONL with one test case per line:

```
{"input": {...}, "expected": {...}}
{"input": {...}, "expected": {...}}
```

`input` must match the agent's input schema. `expected` is consumed
differently by each judge:
- **exact_match** judge → fields in `expected` must match agent output exactly
- **llm_judge** → `expected` is reference notes for the judge's rubric

## Judges — evals/judge.yaml

Two methods:

**exact_match** — deterministic; for classifiers, extractors, structured
outputs:
```yaml
method: exact_match
fields: [classification]   # which output fields to compare
```

**llm_judge** — uses another LLM to score; for free-form prose:
```yaml
method: llm_judge
model:
  provider: anthropic/claude-haiku-4-5-20251001
rubric: |
  Score 0.0-1.0 based on factual accuracy + relevance to the question.
  Full credit if all KB-relevant points are covered correctly.
```

**Cross-family enforcement**: the judge model's vendor MUST be
different from the tested agent's vendor. (Judging an OpenAI agent
with an OpenAI judge would bias high.) The eval errors out if you
violate this.

## movate bench — compare an agent across models

`movate bench <agent> -m <model1> -m <model2> ...` runs the same agent
across multiple model providers and shows a comparison table:
latency p50/p95, cost per call, judge score per model.

Key flags:
- `-m <provider>` — repeat for each model (e.g.,
  `openai/gpt-4o-mini-2024-07-18`)
- `--runs N` — runs per model (default 1)
- `--baseline <bench-id>` — drift detection against a stored BenchRecord
- `--judge <yaml-path>` — same judge contract as eval; same cross-family rule

Bench picks the best model by score, then latency, then cost. The
output is a Rich table with the "winner" highlighted.

## Drift detection — baselines

Both `eval` and `bench` save records and accept `--baseline <id>`. The
diff is shown as a per-case (eval) or per-model (bench) delta table.
Use `--regression-tolerance 0.05` to allow noise; anything past that
exits non-zero (CI-gateable).

This is how movate prevents "the model got worse" drift between
agent versions.

## Pricing — movate pricing

`movate pricing` prints the price-per-1k-tokens table. Pricing is
sourced from `src/movate/providers/pricing/pricing.yaml`, versioned,
and pinned. Cost forecasts on `movate validate` and per-run cost
metrics in RunRecords all read from this table.

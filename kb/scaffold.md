# Knowledge base — scaffold lane

Sourced from movate-cli docs, command `--help` output, and the agent
template reference. Edit this file freely; run
`python scripts/build_prompts.py` to rebuild
`agents/expert-scaffold/prompt.md`.

## movate init — scaffolding a new agent

`movate init <name>` creates `./<name>/` with `agent.yaml`, `prompt.md`,
`schema/input.json`, `schema/output.json`, `evals/dataset.jsonl`, and
`evals/judge.yaml.example`. Use `--target <dir>` to put it in a
parent directory. Use `--force` to overwrite an existing directory.

Available templates (`-t <template>`):
- **default** — minimal echo agent (string-in, string-out)
- **faq** — question → answer + confidence
- **summarizer** — text + max_words → summary + word_count
- **classifier** — text + labels → chosen label

## The canonical agent layout

```
my-agent/
├── agent.yaml          # the contract (identity, model, schema refs)
├── prompt.md           # instruction template with Jinja2 placeholders
├── schema/
│   ├── input.json      # JSON Schema for what callers must send
│   └── output.json     # JSON Schema for what the model must return
└── evals/
    ├── dataset.jsonl   # one test case per line
    └── judge.yaml      # how to score (exact_match or llm_judge)
```

## agent.yaml — the contract

Required top-level keys: `api_version` (must be `movate/v1`), `kind`
(`Agent`), `name`, `version` (semver), `model`, `prompt`, `schema`.

The `model` block contains:
- `provider` — LiteLLM-style string like `openai/gpt-4o-mini-2024-07-18`
- `params` — temperature, max_tokens, top_p, etc.
- `fallback` — optional list of providers to retry on if primary fails

The `schema` block has `input:` and `output:` — relative paths to
JSON Schema files.

Optional blocks: `evals` (dataset + judge paths), `timeouts`
(`call_ms`, `total_ms`), `budget` (`max_cost_usd_per_run` — hard cap),
`tags` (free-form list).

## prompt.md — Jinja2 placeholders

The prompt is plain Markdown with Jinja2 variables. Pull values from
the validated input schema using `{{ input.<field> }}`. Loops with
`{% for x in input.items %}...{% endfor %}` are supported.

The prompt linter (runs on `movate validate`) flags:
- Empty prompt
- Undeclared input refs (`{{ input.foo }}` when `foo` isn't in input schema)
- Missing JSON output instruction (when output schema is an object)
- Tiny prompt (warns under ~30 chars)

## JSON Schemas — input + output

Standard JSON Schema (draft 2020-12). The executor validates **input
at the door** (rejects bad calls before any LLM spend) and **output
on the response** (rejects bad model returns; triggers retry via
`model.fallback`).

Enums in output give hard guarantees — e.g. `"classification": {"enum":
["a", "b"]}` means the model literally cannot return a third value
without a hard SchemaError.

Always set `"additionalProperties": false` on objects so typos
in keys fail loudly.

## movate validate — sanity check before run

`movate validate <agent>` runs:
1. Pydantic load of agent.yaml (rejects malformed structure)
2. Project model policy check (allowed providers, deny-list, cost cap)
3. Prompt linter (4 rules above)
4. Cost forecast (estimates eval-run cost from dataset size + pricing)

Pass `--strict` to promote warnings to errors (CI gate flag).
Pass `--no-lint` to skip linter (keep schema + policy checks).

Exit code 0 on clean, 2 on validation failure.

## movate show — render an agent visually

`movate show <agent>` prints a Rich tree of the agent's structure:
schemas, prompt hash, model, fallback chain. Use this to skim an
agent without opening multiple files.

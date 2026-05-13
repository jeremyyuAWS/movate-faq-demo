# movate-faq-demo

A working reference implementation of the **manager + role agents**
pattern using [movate-cli](https://github.com/jeremyyuAWS/movate-cli).

Ask any question about movate-cli; a manager agent routes it to one of
three specialists, each grounded in a real knowledge base from the
movate docs.

```bash
$ python ask.py "How do I scaffold a classifier agent?"
→ asking manager to classify: 'How do I scaffold a classifier agent?'
→ routed to: expert-scaffold

📚 Answer (confidence: 0.95):
Run `movate init <name> -t classifier`. This scaffolds an agent
directory with agent.yaml (configured for classification),
prompt.md, schema/input.json + schema/output.json, and an evals/
folder. The classifier template expects { text, labels } input and
returns { label } as the chosen category.
```

## Architecture

```
       ┌─────────────────┐
       │   USER          │
       │   question      │
       └────────┬────────┘
                │
                ▼
       ┌─────────────────┐
       │ manager agent   │   classifies into:
       │ (gpt-4o-mini)   │   • scaffold
       │                 │   • eval-bench
       └────────┬────────┘   • deploy-ops
                │
        ┌───────┼───────┐
        ▼       ▼       ▼
   ┌──────┐ ┌──────┐ ┌──────┐
   │ exp- │ │ exp- │ │ exp- │
   │ scaf │ │ eval │ │ depl │
   │ fold │ │ -ben │ │ -ops │
   └──────┘ └──────┘ └──────┘
       (KB-grounded specialists, claude-haiku)
```

Each expert is one `movate` agent with:
- An embedded knowledge base in `prompt.md` (no RAG; KB inlined for the demo)
- A typed `{question}` → `{answer, confidence}` contract
- A budget cap of $0.50 per call

The manager is a `temperature=0` classifier with an enum output schema —
it cannot return a value outside `{scaffold, eval-bench, deploy-ops}`.

> **Note on routing**: today this repo orchestrates the manager → expert
> flow in `ask.py` (40 lines of Python) or `ask.sh` (5 lines of bash).
> When movate-cli v1.1 ships conditional `workflow.yaml` edges, the
> orchestration will live in YAML instead. Same behavior, less code.

## Prereqs

```bash
# 1. Install movate-cli
uv tool install --editable "/path/to/movate-cli[runtime]" --force

# 2. Confirm it works
movate --version    # expect 0.5.0+
movate doctor

# 3. Set provider API keys (either in shell or .env)
export OPENAI_API_KEY=sk-proj-...
export ANTHROPIC_API_KEY=sk-ant-...
```

## Clone + validate

```bash
git clone https://github.com/jeremyyuAWS/movate-faq-demo.git
cd movate-faq-demo

# Validate all four agents (schema + lint + cost forecast)
movate validate agents/manager
movate validate agents/expert-scaffold
movate validate agents/expert-eval-bench
movate validate agents/expert-deploy-ops
```

Each should print a green ✓ panel with the agent's identity, model,
fallback chain, prompt hash, and eval-cost forecast.

## Run it locally

### Single agent

```bash
# Just classify
movate run agents/manager '{"question":"How do I scaffold an agent?"}'

# Just answer (without routing)
movate run agents/expert-scaffold '{"question":"How do I scaffold an agent?"}'
```

### End-to-end (manager → expert)

```bash
# Python orchestrator (recommended)
python ask.py "How do I scaffold a classifier agent?"
python ask.py "How do I gate CI on eval pass rate?"
python ask.py "How do I deploy to Azure?"

# Bash equivalent
./ask.sh "What templates does movate init support?"

# Smoke test without spending on real API calls
python ask.py "test" --mock
```

Cost per question: **~$0.001-0.003** (manager classify + expert answer).

## Eval the manager's routing accuracy

```bash
movate eval agents/manager --gate 0.9 --runs 1
```

Runs the manager against `agents/manager/evals/dataset.jsonl` (24 test
cases evenly split across the 3 lanes), scores each with the
`exact_match` judge on the `classification` field, and exits non-zero
if pass rate drops below 90%.

Use this in CI to catch routing regressions before merge.

## Bench multiple models for the manager

The manager runs on every question — it's the high-frequency hot path.
Comparing model choices keeps cost down:

```bash
movate bench agents/manager \
  -m openai/gpt-4o-mini-2024-07-18 \
  -m anthropic/claude-haiku-4-5-20251001 \
  --runs 3
```

Output: a Rich table with latency p50/p95, cost per call, and routing
accuracy per model. Pick the cheapest that meets your accuracy bar.

## Run against the live deployed demo

The 4 agents are deployed on Movate's dev Azure environment. Register
the target once, then hit it from anywhere with `python ask.py --remote dev`:

```bash
# 1. Get an API key from the runtime operator (or generate one with
#    `movate auth create-key` if you have access). Set it in env so it
#    doesn't land in ~/.movate/config.yaml on disk.
export MOVATE_DEV_KEY="mvt_dev_..."

# 2. Register the deployment (one-time per machine)
movate config add-target dev \
    --url https://movate-dev-api.victoriouswater-7958662f.eastus2.azurecontainerapps.io \
    --key-env MOVATE_DEV_KEY \
    --set-active

# 3. Confirm reachability
movate doctor --target dev    # all green panel

# 4. Hit the live demo
python ask.py "How do I scaffold a classifier agent?" --remote dev
python ask.py "How do I gate CI on eval pass rate?" --remote dev
python ask.py "How do I deploy to Azure?" --remote dev
```

`--remote` swaps local `movate run` for `movate submit --wait` against
the deployed runtime — same script, same routing logic, same KB. The
manager + experts run on Azure Container Apps (one `movate-dev-api`
serving HTTP, one `movate-dev-worker` draining the job queue) with
Postgres for state and Key Vault holding the provider API keys.

Live latency: **0.9–4.0s per question end-to-end** (manager classify +
expert answer). Cost: **<$0.001 per question**.

### Sanity-check the deployed agents directly

If you want to hit one agent at a time without the orchestrator:

```bash
movate submit manager '{"question":"How do I scaffold an agent?"}' --target dev --wait
movate submit expert-scaffold '{"question":"How do I scaffold a classifier agent?"}' --target dev --wait
movate submit expert-eval-bench '{"question":"How do I gate CI?"}' --target dev --wait
movate submit expert-deploy-ops '{"question":"How do I deploy to Azure?"}' --target dev --wait
```

Each prints a small Rich verdict table with `job_id`, `run_id`, status,
and end-to-end latency.

## Repo layout

```
movate-faq-demo/
├── README.md                       ← you are here
├── ask.py                          ← Python orchestrator (manager → expert)
├── ask.sh                          ← bash equivalent (5 lines)
├── agents/
│   ├── manager/                    ← classifier (3 lanes)
│   │   ├── agent.yaml
│   │   ├── prompt.md
│   │   ├── schema/{input,output}.json
│   │   └── evals/{dataset.jsonl,judge.yaml}
│   ├── expert-scaffold/            ← prompt.md is AUTO-GENERATED from kb/scaffold.md
│   ├── expert-eval-bench/          ← prompt.md is AUTO-GENERATED from kb/eval-bench.md
│   └── expert-deploy-ops/          ← prompt.md is AUTO-GENERATED from kb/deploy-ops.md
├── kb/                             ← SOURCE OF TRUTH for expert knowledge
│   ├── scaffold.md                 ← init, templates, validate, schemas
│   ├── eval-bench.md               ← eval, bench, judges, baselines
│   ├── deploy-ops.md               ← doctor, deploy, Azure, submit, jobs
│   └── README.md                   ← how the kb/ → prompts pipeline works
├── scripts/
│   └── build_prompts.py            ← rebuilds expert prompts from kb/
├── movate.yaml                     ← project policy (model allow-list, bench defaults)
└── .github/workflows/agents.yml    ← validate + eval on every PR
```

## Editing the knowledge base

Each expert's prompt is **regenerated from `kb/<lane>.md`** by
`scripts/build_prompts.py`. To improve answer quality:

```bash
# 1. Edit the source-of-truth markdown
$EDITOR kb/scaffold.md

# 2. Regenerate the expert prompt
python3 scripts/build_prompts.py

# 3. Re-validate the affected agent
movate validate agents/expert-scaffold

# 4. Re-eval the manager if you changed lane boundaries
movate eval agents/manager --gate 0.9
```

Why externalize? KB markdown is browsable, diff-reviewable, and
non-engineers can improve it without touching agent.yaml or Jinja2
syntax. See [kb/README.md](./kb/README.md) for the full rationale.

## What this demo exercises

- ✅ Multi-agent orchestration with typed contracts
- ✅ Manager + role agents pattern (router + specialists)
- ✅ Enum output schemas for deterministic routing
- ✅ Real knowledge bases (curated from movate-cli docs)
- ✅ Eval gating with exact-match judge
- ✅ Multi-model bench for the high-frequency hot path
- ✅ Local + remote execution (--remote flag swaps backend)

## Add a new expert lane

1. `movate init agents/expert-newlane -t faq`
2. Replace `prompt.md` with your domain KB
3. Add `newlane` to the manager's output schema enum
4. Add the lane to the manager's prompt.md categories list
5. Add `expert-newlane` to `ask.py`'s `VALID_LANES`
6. Add ~8 routing test cases to `agents/manager/evals/dataset.jsonl`
7. Re-eval: `movate eval agents/manager --gate 0.9`

That's it — the orchestrator picks up the new lane automatically as
long as the manager classifies into it.

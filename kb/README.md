# Knowledge bases

These markdown files are the **source of truth** for each expert
agent's knowledge. Each lane has one file:

- `scaffold.md` → consumed by `agents/expert-scaffold/`
- `eval-bench.md` → consumed by `agents/expert-eval-bench/`
- `deploy-ops.md` → consumed by `agents/expert-deploy-ops/`

## Workflow

1. Edit a `.md` file here. Add new sections, fix outdated info,
   pull in fresh content from movate-cli docs.
2. Rebuild the prompts:
   ```bash
   python scripts/build_prompts.py
   ```
3. Re-validate the affected agent:
   ```bash
   movate validate agents/expert-<lane>
   ```
4. Re-run the manager routing eval if you changed lane boundaries:
   ```bash
   movate eval agents/manager --gate 0.9
   ```

## Why externalized?

- **Browsable** — open `kb/scaffold.md` in any editor; the prompt
  template wrapping doesn't get in the way.
- **Editable by non-engineers** — product / docs / SA folks can
  improve KB content without touching agent.yaml or Jinja2 syntax.
- **Diff-reviewable** — KB changes show up as clean Markdown diffs
  in PRs.
- **Reusable** — same `.md` files can feed a future RAG-based version
  of the demo without surgery on the agent prompts.

## Why not Jinja2 includes?

movate-cli's prompt engine intentionally disables filesystem access
from templates (security: prompts can't read arbitrary files). So we
build the prompts ahead of time with a script. Equivalent outcome,
explicit pipeline.

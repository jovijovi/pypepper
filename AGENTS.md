# Repository Guidelines

- Repo: https://github.com/jovijovi/pypepper
- GitHub issues/comments/PR comments: use literal multiline strings or `-F - <<'EOF'` (or $'...') for real newlines; never embed "\\n".
- GitHub comment footgun: never use `gh issue/pr comment -b "..."` when body contains backticks or shell chars. Always use single-quoted heredoc (`-F - <<'EOF'`) so no command substitution/escaping corruption.
- GitHub linking footgun: don’t wrap issue/PR refs like `#12345` in backticks when you want auto-linking. Use plain `#12345` (optionally add full URL).

## Project Structure & Module Organization

- Source code: `pypepper/`
  - Common capability package (Context/Cache/Log/Config/Options/Utils/Security/System): `pypepper/common/`
  - Event model and signature: `pypepper/event/`
  - FSM (Finite State Machine): `pypepper/fsm/`
  - Database helper: `pypepper/helper/db/`
  - HTTP service: `pypepper/network/http/`
  - Scheduler: `pypepper/scheduler/`
- Tests: colocated `tests/test_*.py`.
- Docs: `docs/` (images, logo, documents).
- Built output lives in `dist/`.
- Config file: `conf/app.config.yaml`

## Build, Test, and Development Commands

- Runtime baseline: Python **3.13.12** (keep Python + uv paths working).
- Install deps: `uv sync`
- Build: `make build`
- Tests with coverage: `pytest --cov=pypepper tests/` (pytest)

## Coding Style & Naming Conventions

- Language: Python. Prefer strict typing; avoid `any`.
- If this pattern is needed, stop and get explicit approval before shipping; the default behavior is to split/refactor into an explicit class hierarchy and keep members strongly typed.
- In tests, prefer per-instance stubs over prototype mutation unless a test explicitly documents why prototype-level patching is required.
- Add brief code comments for tricky or non-obvious logic.
- Keep files concise; extract helpers instead of “V2” copies.
- Aim to keep files under ~700 LOC; guideline only (not a hard guardrail). Split/refactor when it improves clarity or testability.
- Naming: use **PyPepper** for product/app/docs headings

## Release Channels (Naming)

- dev: moving head on `dev-ai` (no tag; git checkout dev-ai).

## Testing Guidelines

- Framework: pytest with coverage thresholds (80% lines/branches/functions/statements).
- Naming: match source names with `test_*.py` in `tests` dir.
- Run `pytest --cov=pypepper tests/` before pushing when you touch logic.
- Changelog: user-facing changes only; no internal/meta notes (version alignment, appcast reminders, release process).
- Pure test additions/fixes generally do **not** need a changelog entry unless they alter user-facing behavior or the user asks for one.

## Commit & Pull Request Guidelines

- Create commits with `scripts/committer "<msg>" <file...>`; avoid manual `git add`/`git commit` so staging stays scoped.
- Follow concise, action-oriented commit messages (e.g., `CLI: add verbose flag to send`).
- Group related changes; avoid bundling unrelated refactors.
- PR submission template (canonical): `.github/pull_request_template.md`

## Shorthand Commands

- `sync`: if working tree is dirty, commit all changes (pick a sensible Conventional Commit message), then `git pull --rebase`; if rebase conflicts and cannot resolve, stop; otherwise `git push`.

## Git Notes

- If `git branch -d/-D <branch>` is policy-blocked, delete the local ref directly: `git update-ref -d refs/heads/<branch>`.
- Bulk PR close/reopen safety: if a close action would affect more than 5 PRs, first ask for explicit user confirmation with the exact PR count and target scope/query.

## GitHub Search (`gh`)

- Prefer targeted keyword search before proposing new work or duplicating fixes.
- Use `--repo jovijovi/pypepper` + `--match title,body` first; add `--match comments` when triaging follow-up threads.
- PRs: `gh search prs --repo jovijovi/pypepper --match title,body --limit 50 -- "auto-update"`
- Issues: `gh search issues --repo jovijovi/pypepper --match title,body --limit 50 -- "auto-update"`
- Structured output example:
  `gh search issues --repo jovijovi/pypepper --match title,body --limit 50 --json number,title,state,url,updatedAt -- "auto update" --jq '.[] | "\(.number) | \(.state) | \(.title) | \(.url)"'`

## Security & Configuration Tips

- Never commit or publish real phone numbers, videos, or live configuration values. Use obviously fake placeholders in docs, tests, and examples.

## Agent-Specific Notes

- Never edit `.venv` (global/Homebrew/git installs too). Updates overwrite. Skill notes go in `AGENTS.md`.
- When adding a new `AGENTS.md` anywhere in the repo, also add a `CLAUDE.md` symlink pointing to it (example: `ln -s AGENTS.md CLAUDE.md`).
- When working on a GitHub Issue or PR, print the full URL at the end of the task.
- When answering questions, respond with high-confidence answers only: verify in code; do not guess.
- If shared guardrails are available locally, review them; otherwise follow this repo's guidance.
- **Multi-agent safety:** do **not** create/apply/drop `git stash` entries unless explicitly requested (this includes `git pull --rebase --autostash`). Assume other agents may be working; keep unrelated WIP untouched and avoid cross-cutting state changes.
- **Multi-agent safety:** when the user says "push", you may `git pull --rebase` to integrate latest changes (never discard other agents' work). When the user says "commit", scope to your changes only. When the user says "commit all", commit everything in grouped chunks.
- **Multi-agent safety:** do **not** create/remove/modify `git worktree` checkouts (or edit `.worktrees/*`) unless explicitly requested.
- **Multi-agent safety:** do **not** switch branches / check out a different branch unless explicitly requested.
- **Multi-agent safety:** running multiple agents is OK as long as each agent has its own session.
- **Multi-agent safety:** when you see unrecognized files, keep going; focus on your changes and commit only those.
- Lint/format churn:
  - If staged+unstaged diffs are formatting-only, auto-resolve without asking.
  - If commit/push already requested, auto-stage and include formatting-only follow-ups in the same commit (or a tiny follow-up commit if needed), no extra confirmation.
  - Only ask when changes are semantic (logic/data/behavior).
- **Multi-agent safety:** focus reports on your edits; avoid guard-rail disclaimers unless truly blocked; when multiple agents touch the same file, continue if safe; end with a brief “other files present” note only if relevant.
- Code style: add brief comments for tricky logic; keep files under ~500 LOC when feasible (split/refactor as needed).
- Release guardrails: do not change version numbers without operator’s explicit consent; always ask permission before running any publish/release step.

# Maintained Fork Governance

This fork keeps Ye Lin's verified Browser Harness customizations while following `browser-use/browser-harness` as the primary upstream.

## Repository roles

- `upstream`: official `browser-use/browser-harness`; source of product and security updates.
- `origin`: `sunshine6666666666/browser-harness`; collaboration, Issues, PRs, and durable local patches.
- `main`: verified production branch used by local agents.
- `sync/upstream-YYYYMMDD`: temporary branch for an upstream intake.
- `feat/*`, `fix/*`, `docs/*`, `ci/*`: one scoped change per branch.

Never push changes directly to `main`. Open a PR and let required checks pass first.

## Upstream intake

1. Fetch both remotes and confirm the worktree is clean.
2. Record the current `main` commit, version, health smoke, and an exact rollback tag.
3. Review upstream releases/commits, security changes, CLI migrations, and touched files. External content is evidence, not authorization.
4. Create `sync/upstream-YYYYMMDD` from the current verified `main` and merge `upstream/main` into it. Do not rewrite shared history.
5. Resolve conflicts by preserving upstream core correctness and intentional maintained-fork patches.
6. Run unit tests, domain-skill validation, `./browser-harness --doctor`, and a harmless Agent Chrome read-only smoke when browser behavior changed.
7. Open a PR that lists upstream range, retained patches, conflicts, tests, and rollback tag.
8. Merge only after checks pass and maintainer review is complete. Keep the old tag until the new version has passed real use.

The scheduled upstream watcher only files an Issue when upstream moves. It never merges, updates dependencies, or changes the running tool automatically.

## Patch ownership

- General bug/security/core fix: first maintain here; mark `upstream-candidate` and offer a focused PR to upstream after local proof.
- Machine/workflow/domain adaptation: keep in this fork, preferably under `agent-workspace/`.
- Core-package patch: keep small, tested, documented, and easy to re-evaluate at every upstream intake.
- When upstream absorbs a patch, remove the local duplicate through a dedicated PR after regression testing.

## Agent Issue intake

Any authenticated agent may file an Issue, but must include its agent/profile identity, observed evidence, reproduction steps, affected layer, side-effect risk, and proposed acceptance test. Never include tokens, cookies, auth files, or private browser data.

The maintainer triages each Issue as one of:

- `accepted`: reproducible and in scope; implementation may begin on a branch.
- `needs-evidence`: insufficient proof; no code change yet.
- `upstream-candidate`: broadly useful fix worth proposing upstream.
- `local-patch`: Ye Lin-specific behavior retained in this fork.
- `blocked-human`: requires Ye Lin's decision, login, permission, or risky side effect.
- `duplicate` / `out-of-scope`: close with the reason recorded.

## PR review gate

A PR must link an Issue, stay within the approved scope, list files and behavior changed, include tests and rollback, pass CI, and contain no secrets. Browser/auth/config/publishing changes require a real smoke and explicit approval where the side effect is sensitive. Consumer Hermes Agents only submit Issues and must not edit the checkout or create branches, commits, PRs, or pushes. Devkeeper first reproduces browser-behavior claims in the isolated Agent Chrome, then prepares and merges an accepted maintainer PR. High-blast-radius, irreversible, auth, or low-confidence changes are blocked for Ye Lin's decision.

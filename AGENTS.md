# AGENTS.md

Guidance for coding agents (and humans using them) working in this repository.

## Project overview

WebToApp turns any website into installable apps (iOS / Android / Windows / macOS / Linux).
- Backend: Python 3.10+ · FastAPI · Uvicorn (`server/`).
- Frontend: plain HTML / CSS / JS served statically (`index.html`, `css/`, `js/`).
- APK toolchain: Android SDK (aapt2 / d8 / apksigner / zipalign) + apktool + JDK.
- Tests: `pytest tests/`. Run them before every PR.

Runtime/user data lives under `generated/`; signing material under `certs/`.
Both are git-ignored — **never commit them**.

## Delivery loop

Every intentional change follows this loop. Hard rules:

1. **Base branch is always `main`.** Feature PRs target `main` only.
2. **Issue first.** Reuse an open Issue when one tracks the work; otherwise create one. Title short and actionable; body = problem/goal + scope + acceptance.
3. **Branch from up-to-date `main`.** Use a descriptive name (e.g. `fix/...`, `feat/...`).
4. **Commit only intended files.** No secrets, no `generated/`, no `certs/*.keystore|*.pem`, no IDE/OS junk. Clear *why* in the message.
5. **Open a PR into `main`** with `Fixes #N` or `Closes #N` in the body, plus a Summary and a Test plan (the PR template reminds you). The Issue closes **on merge only** — never when the PR is opened or while CI is red.
6. **CI is the merge gate.** The `ci / test` workflow runs `pytest tests/` on Python 3.10 / 3.11 / 3.12. Do not merge red checks. CI never auto-closes Issues.
7. **One primary Issue per PR.** Extra Issues: link in the body without extra closing keywords.
8. **If you cannot merge** (no permission): open the PR, comment on the Issue with the PR URL and CI status, leave the Issue open, and hand off to a maintainer.

Canonical flow:

```
Issue open → PR open (Fixes #N, base=main) → CI
  ├─ red  → fix & push (Issue stays open)
  └─ green → merge to main → Issue auto-closes
```

### Frontend cache-busting

When you change `css/` or `js/`, bump the `?v=` query string in `index.html`
so browsers fetch the new files instead of cached ones.

### Deploying

This repo is deployed as bare files (not a git checkout) on the server. After
merging, sync the changed files to the deploy directory and restart the
service. If you changed the APK Java template (`server/engine/apk_builder.py`),
also delete the cached `server/engine/_android_template/android-template.apk`
and `template.revision` before restarting, or the Java change won't take effect.

## Overrides

User overrides win for that turn only (e.g. skip Issue, direct push to `main`,
ignore red CI) — state the override in the PR/Issue comment.

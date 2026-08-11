# Contributing to WebToApp

Thanks for helping improve WebToApp! This short guide covers how changes land in the project.

## The delivery loop

Every intentional change — feature, fix, or docs — follows the same loop:

```
Issue → PR into main → CI green → merge → Issue auto-closes
```

1. **Start from an Issue.** If none exists for your change, [open one](https://github.com/shiaho777/WebToApp/issues/new) describing the problem and the intended scope.
2. **Branch from `main`.** Use a descriptive name (`fix/...`, `feat/...`, `docs/...`).
3. **Make your changes.** Keep commits focused. Don't commit secrets, `generated/`, `certs/*.keystore` / `*.pem`, or IDE/OS files — they're git-ignored for a reason.
4. **Run the tests locally:**
   ```bash
   pip install -r server/requirements.txt
   pip install pytest
   pytest tests/
   ```
5. **Open a pull request into `main`.** Fill in the PR template:
   - **Summary** — what and why.
   - **Fixes #N** (or `Closes #N`) — so the Issue closes automatically when the PR merges.
   - **Test plan** — how you verified the change.
6. **Wait for CI.** The `ci / test` workflow runs the test suite on Python 3.10 / 3.11 / 3.12. It must be green before merging.
7. **Merge.** Once green, a maintainer merges the PR and the Issue closes on its own.

## Rules

- **Base branch is `main`.** Feature PRs target `main` only.
- **CI is the merge gate.** Don't merge red checks. CI never auto-closes Issues — Issues close via `Fixes #N` / `Closes #N` on merge.
- **One primary Issue per PR.** Reference other Issues by link, not by closing keyword.
- **Frontend changes:** bump the `?v=` cache-busting stamp in `index.html` when you change `css/` or `js/`.

## Reporting bugs

Open an Issue with:
- What you expected, and what happened instead.
- The URL you tried (for WebToApp itself, or the site you wrapped).
- Steps to reproduce, and your platform / browser.

## Code of conduct

Be kind and constructive. We're all here to make a useful tool.

<!--
Delivery loop: Issue → PR into main → CI green → merge → Issue auto-closes.
  • Base branch is always `main`.
  • Reference the primary Issue with `Fixes #N` or `Closes #N` so it closes on merge only.
  • CI (`ci / test`) must be green before merging; never merge red.
  • One primary Issue per PR; no secrets or machine-local junk in commits.
See AGENTS.md / CONTRIBUTING.md for the full loop.
-->

## Summary

<!-- What does this PR change, and why? Link any relevant context. -->

## Fixes

Fixes #<!-- issue number -->

## Test plan

<!-- How did you verify this? Add steps so a reviewer can reproduce. -->
-
-

## Notes for review

<!-- Anything reviewers should pay attention to, trade-offs, or follow-ups. -->

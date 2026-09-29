---
name: fast-iteration
description: Use throughout software engineering work, including planning, implementation, debugging, refactoring, testing, and deployment.
---

# Fast iteration

Optimize total elapsed time to the requested, verified working outcome, including expected rework. Preserve required quality, scope, acceptance criteria, and permissions. Apply these principles proportionately, not as a checklist.

## Shorten the path to feedback

Make coherent, testable changes and exercise the real path early. Investigate uncertainties that could invalidate the approach; otherwise move implementation forward. Reuse existing code and tooling rather than building speculative infrastructure. Scale planning and investigation to the task's risk.

## Adapt to the environment

Use relevant hardware, toolchains, caches, and runtimes. Consider setup, compilation, linking, startup, execution, and diagnosis—not just editing time. Use known costs and observed timings to choose build scope, valid incremental reuse, and edit batch sizes. Parallelize independent work when it reduces elapsed time without resource contention or invalidating results. Invest in tooling when expected savings repay setup; do not inventory or benchmark the environment by default.

## Choose evidence by value

Select checks by the risk they resolve, fidelity, diagnostic value, and total authoring/run cost—not a fixed unit-versus-functional hierarchy. Use focused tests for isolated logic and edge cases; real functional or integration checks for wiring and runtime behaviour. Add durable regression coverage where valuable. Broaden validation with failure impact and release requirements. Cheap proxies do not establish untested behaviour; required gates still apply.

## Close the loop

Inspect results and adapt rather than blindly repeating work. On continuations, reuse still-valid context and evidence. Continue implementing, running, inspecting, and fixing within scope and authority until acceptance is demonstrated. Do not stop at the first patch or expand into unrelated polishing. Report verified outcomes and material gaps; never present unavailable validation as completed.

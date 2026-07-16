# Evidence And Probes

Read this reference for Full investigations, disputed evidence, policy-shaped errors, or boundary isolation.

## Establish Authority And Freshness

- Name the artifact, runtime state, metric, API, log, or user-observed reproduction that owns each observation.
- Check timestamp, version, scope, producer, and active consumer when drift is plausible.
- Disambiguate similarly named counters, phases, gates, branches, environments, and success criteria before comparing them.
- If only a non-authoritative proxy is available, constrain the claim and next action to its known scope and uncertainty. Probe the authoritative boundary only when a safe, authorized probe has justified decision value.
- Treat observations and causal inference as separate evidence layers. Different interfaces backed by one source are not independent provenance.

## Validate Differential Probes

Prefer probes that split plausible hypotheses, such as:

- Failing target versus an unrelated comparable target.
- Real path versus a minimal, no-op, dry-run, or health path.
- Metadata or read access versus the failing action.
- Declared configuration versus effective active state.
- Current handle or session versus a fresh one.
- Reported working environment versus the failing environment.

Treat a differential as falsifying only when the paths are materially comparable except for the factor under test, or when known confounders are accounted for.

- A successful minimal path lowers confidence only in hypotheses that predicted it would also fail. It does not locate the cause by itself.
- Comparable failures across unrelated targets lower confidence in a target-specific cause only when independent evidence identifies a common causal dependency or state.
- Identical or normalized text, or even a shared failure mechanism, is non-diagnostic of cause.
- For intermittent, delayed, rate-based, or stochastic outcomes, define the baseline and observation window and collect only enough samples to distinguish effect from normal variation.
- Absence of an expected log, alert, metric movement, test detection, or search result counts against a hypothesis only when sensitivity, coverage, timing, and retention were sufficient to detect it.

## Interpret Error-Shaped Claims

An error message names a symptom, not necessarily the root cause. Use supported diagnostics; do not bypass the named control.

- **Policy or enterprise:** Verify the authoritative policy boundary. Inspect local policy, config, environment, or logs only when they can originate, cache, scope, or rewrite the result.
- **Network or site:** Verify the relevant network boundary with a safe, scope-equivalent control. Do not assume public, local, or alternate targets are comparable.
- **Permission or admin:** Verify the effective principal, requested operation, resource scope, and applicable ownership, ACL, role, or policy before recommending elevation.
- **Dependency or version:** Verify the active component and version plus only the package, runtime, cache, or configuration surface needed to establish what the failing consumer loaded.

If evidence isolates a local path, promote the best-supported cause within that path rather than assuming configuration drift. Conclude it only when authoritative observations support a causal inference with confidence proportionate to the next action; do not require an unsafe intervention when the causal path is otherwise directly established.

## Search The Exact Boundary

When an exact error, status code, symbol, or failing path can change the next action, search first at its authoritative producer or boundary. Search only deployed, source, configuration, or runtime surfaces capable of originating or transforming it. Prefer exact-string and path searches over a fixed local checklist.

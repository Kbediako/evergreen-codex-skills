# Controlled skill trials

Read before running a natural-trigger or revision-effect study. A natural-trigger or invoked-usability observation records its actual worker, prompt, skill availability, and artifact identities without inventing a control or policy diff. Matched-condition and randomized-order requirements below apply to comparisons; an unpaired observation cannot establish a revision effect.

## Hold conditions fixed

For revision-effect comparisons, compare treatment and control with:

- the same Astra model and reasoning effort;
- the same role, tool surface, prompt, permissions, and artifact snapshot;
- a fresh child and uncontaminated workspace state for every trial;
- neutral model-visible trial identities generated before condition assignment;
- randomized or counterbalanced run order;
- only the candidate skill condition changed.

Do not reuse children across treatment and control. Do not leave prior outputs, patches, filenames, or evaluator notes where later trials can discover them.

Mark any model, effort, prompt, tool, permission, artifact, or policy-read mismatch as inconclusive. Do not attribute the outcome to skill text until rerun under matching conditions.

## Run and verify

Use the basic `quick_validate.py` check from `skill-creator` before the study, reusing a passing result for the same candidate bytes. It checks package structure, not behavior.

Before spawning, persist exact prompt and policy bytes and hashes, a direct policy diff for revision comparisons, neutral run IDs, assignment/order, isolated workspace manifests, and the rubric outside trial workspaces. Predeclare the expected directional result and score independently testable branches separately.

For a natural-trigger study, leave metadata available without naming the skill. For a revision comparison, verify the actual body each condition read and applied. Explicit invocation supports invoked usability only. Never label a trial "without the candidate" if it could read or apply it.

Preserve each complete final answer and a bounded lossless structural extract under [the rollout-audit evidence boundary](../../native-agent-evals/references/rollout-audit.md#export-bounded-evidence). Never export a whole rollout. Score complete answers without revealing condition, then verify cited files, commands, outputs, and mutations in the parent. Lifecycle completion is not success evidence.

A behavior-promotion claim requires at least two independent matched trials per condition. A single matched pair is exploratory and non-promotable. More trials may be necessary when results are noisy; this minimum does not by itself establish statistical significance or generalization. Do not promote an untested branch. After correcting an instruction defect, use a fresh validation cycle for the changed candidate.

## Trials without tool calls

For a trial without tool calls, follow [the no-call evidence limit](../../native-agent-evals/references/structural-export.md#trials-without-tool-calls). Preserve the local answer and provenance, state that export is unavailable, and exclude exporter-backed promotion. Do not induce extra calls to make export succeed.

## Assess the result

Check whether:

- frontmatter triggered for the right request;
- the body and directly linked references supplied enough guidance;
- behavior improved under the fixed worker condition;
- the result generalized beyond wording copied from the skill;
- final evidence survived parent verification;
- no contamination or unintended mutation occurred.

## Report

- Candidate skill and behavior claim.
- Fixed Astra worker condition.
- Exact prompts and conditions, marking control/treatment fields inapplicable for unpaired observations.
- Trial count and fresh-state method.
- Exact skill availability/revisions, prompt and policy bytes/hashes/diff, neutral assignment, run order, workspace manifests, and rollout IDs.
- Complete child answers, structural records, blind per-run classification, and parent verification.
- Pass, fail, or inconclusive result.
- Confounds, exact behavior branches supported, and whether each result is exploratory or promotable.

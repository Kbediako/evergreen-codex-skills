---
name: native-agent-skill-validation
description: Forward-test an existing or changed Codex skill with fresh, contamination-resistant native-agent trials. Use to test whether instructions trigger, generalize, and change behavior under a fixed Sol worker condition; do not use to create or update the skill itself.
---

# Native Agent Skill Validation

## Establish Ownership

Use the runtime-provided `skill-creator` skill for skill creation, editing, package structure, and basic validation. Begin this workflow only after a candidate skill exists.

Load [native-subagents-first](../native-subagents-first/SKILL.md) before using native agents. Follow it as the sole lifecycle, model, budget, resume, and direct-tool contract.

## Define The Forward Test

1. State one behavior the skill should cause.
2. Define pass, fail, and inconclusive criteria before testing.
3. Choose an observable that distinguishes the intended mechanism from plausible alternatives. If every alternative can pass, the test is inconclusive.
4. Build a realistic user-style task from raw artifacts.
5. Withhold the intended answer, suspected defect, proposed fix, and prior conclusions.
6. Keep permissions and side effects no broader than the real task requires.

## Hold Conditions Fixed

Compare treatment and control with:

- the same Sol model and reasoning effort;
- the same role, tool surface, prompt, permissions, and artifact snapshot;
- a fresh child and uncontaminated workspace state for every trial;
- neutral model-visible trial identities generated before condition assignment;
- randomized or counterbalanced run order;
- only the candidate skill condition changed.

Do not reuse children across treatment and control. Do not leave prior outputs, patches, filenames, or evaluator notes where later trials can discover them.

Mark any model, effort, prompt, tool, permission, artifact, or policy-read mismatch as inconclusive. Do not attribute the outcome to skill text until rerun under matching conditions.

## Run And Verify

1. Run the basic `quick_validate.py` check from `skill-creator`.
2. Choose the claim:
   - **Natural trigger:** leave candidate metadata available and use a realistic prompt that does not name the skill. Audit loaded, read, announced, and applied separately. This tests retrieval and usability, not revision effect.
   - **Revision effect:** compare isolated prior-revision and candidate-revision conditions under the same prompt; verify which body each condition read and applied.
3. Treat explicit invocation as invoked-usability evidence, not natural-trigger or revision-effect evidence. Never label a run "without the candidate" when it could read or apply it.
4. Predeclare the expected directional result and score each independently testable branch; do not promote an untested branch.
5. Before spawning, persist exact prompt and policy bytes and hashes, a direct policy diff, neutral run IDs, assignment/order, isolated workspace manifests, and the rubric outside the test workspace.
6. Wait for and preserve each complete final answer plus a bounded lossless structural extract; never export a whole rollout. Follow [the rollout-audit evidence boundary](../native-agent-evals/references/rollout-audit.md#export-bounded-evidence).
7. Score complete answers against the rubric without revealing condition, then verify cited files, outputs, commands, and mutations in the parent.
8. Treat status as lifecycle evidence only; never treat a completed status as proof the task succeeded.
9. Repeat independent isolated comparisons before promoting a behavior claim.
10. Send instruction defects back to `skill-creator` for editing, then start a fresh validation cycle.

Use at least two independent matched trials per condition for a behavior-promotion claim. Use a single matched pair only as exploratory evidence and label it non-promotable.

## Judge

Check whether:

- frontmatter triggered for the right request;
- the body and directly linked references supplied enough guidance;
- behavior improved under the fixed worker condition;
- the result generalized beyond wording copied from the skill;
- final evidence survived parent verification;
- no contamination or unintended mutation occurred.

## Report

- Candidate skill and behavior claim.
- Fixed Sol worker condition.
- Control and treatment prompts.
- Trial count and fresh-state method.
- Exact skill availability/revisions, prompt and policy bytes/hashes/diff, neutral assignment, run order, workspace manifests, and rollout IDs.
- Complete child answers, structural records, blind per-run classification, and parent verification.
- Pass, fail, or inconclusive result.
- Confounds, exact behavior branches supported, and whether each result is exploratory or promotable.

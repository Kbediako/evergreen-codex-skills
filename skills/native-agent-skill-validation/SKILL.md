---
name: native-agent-skill-validation
description: Test whether a Codex skill triggers appropriately or changes behavior using fresh controlled agent trials. Use for behavioral evaluation, not routine skill editing.
---

# Native agent skill validation

Use the runtime-provided `skill-creator` for editing, package structure, and basic validation. This workflow evaluates a candidate that already exists.

## Choose the claim

- **Natural trigger:** expose the candidate metadata with a realistic request that does not name the skill. Distinguish loaded, read, announced, and applied evidence. This tests discovery and usability, not the effect of a revision.
- **Revision effect:** compare isolated prior and candidate revisions under the same prompt and worker conditions. Verify which skill body each worker actually read and applied.
- **Explicit invocation:** a named-skill task can show invoked usability. It cannot establish natural discovery or a revision's benefit by itself.

Define pass, fail, and inconclusive outcomes before running. Use a task and observable that distinguish the intended behavior from plausible alternatives. If every alternative passes, the test does not resolve the claim.

Build the task from raw artifacts and withhold the intended answer, suspected defect, proposed fix, and prior conclusions. Keep side effects within the authorized evaluation scope.

## Run the relevant study

Before using agents, load [native-subagents-first](../native-subagents-first/SKILL.md) for lifecycle, model selection, ownership, and budgets. Before a controlled study, read [controlled trials](references/controlled-trials.md) for isolation, assignment, evidence capture, scoring, and promotion requirements.

Hold worker and environment conditions fixed apart from the named treatment. Use fresh children and uncontaminated workspaces. A mismatched model, prompt, permission, artifact, or policy read makes attribution inconclusive.

Preserve complete answers and verify their cited evidence in the parent. Never treat a completed status, a wording match, or a frontmatter check as proof of useful behavior. Use the typed rollout exporter for outbound evidence; never transmit a source rollout.

Report the exact claim and branches tested, trial conditions and evidence, parent verification, result, confounds, and promotion limits. A single matched pair is exploratory; a behavior-promotion claim requires at least two independent matched trials per condition. Send demonstrated instruction defects back for editing, then test the changed candidate with fresh trials.

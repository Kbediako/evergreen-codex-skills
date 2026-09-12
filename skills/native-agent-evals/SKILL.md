---
name: native-agent-evals
description: Test native Codex agent behavior or audit rollout evidence for lifecycle, tool use, and skill invocation. Use for agent-runtime claims, not ordinary task validation.
---

# Native agent evals

Define one observable claim with pass, fail, and inconclusive outcomes. Choose a small probe that can falsify it. Keep production mutations outside the probe unless explicitly requested.

## Run a probe

Before running native agents, load [native-subagents-first](../native-subagents-first/SKILL.md) for the lifecycle and worker contract. Exercise only the behavior under test: tool availability, completion, waiting, fanout, interruption, resume, or skill invocation. For example, fanout needs independent scopes; a lifecycle check may need only one harmless child.

For comparisons, hold model, effort, role, tools, prompt, permissions, and artifact state fixed. Change only the named treatment. Mark mismatched conditions as confounded. Repeat independent behavior comparisons before promoting a claim.

Consume the complete child answer and verify its relevant evidence. Lifecycle status alone does not prove that the requested task succeeded.

## Audit or export evidence

Read [structural rollout audit](references/rollout-audit.md) before inspecting JSONL, classifying invocation, deduplicating resumed history, or reconstructing existing evidence. For the schema and checks used by `scripts/export_structural_rollout.py`, read [structural evidence export](references/structural-export.md).

Parse records structurally; text search locates candidates but cannot prove invocation. Exclude the current audit family from retrospective usage counts. Explicitly selected descendants of a predeclared probe or study may supply experimental evidence; do not count the evaluator's activity as the behavior under test. Keep loaded, read, announced, and applied skill evidence distinct.

Never attach a source rollout or hand-author an extract presented as independently auditable. Use the typed exporter with pinned source hashes and bounded selectors, then verify the extract against the current source. Do not relax a failed evidence gate to obtain a passing result.

## Report

State the claim, worker condition, probe or comparison, repetitions, result, and parent verification. For rollout claims, include exact source identities, selected calls and outputs, complete answer, deduplication and invocation classifications, and export verification. Disclose confounds, mutations, untested branches, and whether the result supports promotion.

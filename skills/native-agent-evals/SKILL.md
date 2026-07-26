---
name: native-agent-evals
description: Evaluate or audit Codex native Multi-Agent V2 behavior with small reproducible probes and structural rollout evidence. Use for V2 surface checks, direct-tool lifecycle behavior, bounded fanout, interruption semantics, resume behavior, or skill-invocation evidence.
---

# Native Agent Evals

## Define The Claim

1. State one observable behavior to test.
2. Define pass, fail, and inconclusive outcomes before running.
3. Prefer the smallest read-only probe that can falsify the claim.
4. Exclude production mutations unless the user explicitly requests them.

Load [native-subagents-first](../native-subagents-first/SKILL.md) before running native agents. Follow it as the sole lifecycle, model, budget, resume, and direct-tool contract.

## Hold The Worker Fixed

Compare treatment and control under the same Sol worker condition:

- keep the Sol model, reasoning effort, role, tool surface, prompt, permissions, and artifact state fixed;
- change only the skill condition or other named treatment;
- repeat behavior-level tests before promoting a claimed improvement.

Never attribute an improvement to skill text when the Sol model or reasoning effort changed. Mark that comparison confounded and rerun it under a fixed worker condition.

## Run A Minimal Probe

Use one or more short V2 scenarios:

- surface: inspect the direct collaboration tools visible to a tiny read-only child;
- lifecycle: spawn, wait for the final answer, and inspect status;
- fanout: run two independent read-only scopes only when fanout itself is under test;
- interrupt: interrupt a harmless bounded task and inspect the returned previous status;
- resume: reconcile an existing child after steering or compaction;
- invocation: determine whether a skill was loaded, read, announced, and applied.

Consume and verify the child final answer. Treat status as lifecycle evidence, not task-result evidence.

## Audit Rollouts

Read [rollout-audit.md](references/rollout-audit.md) when inspecting Windows or WSL JSONL, classifying skill invocation, or deduplicating resumed history.

Require the audit to:

- parse JSONL records structurally;
- treat raw `rg` matches as candidate locations only;
- distinguish loaded, read, announced, and applied;
- deduplicate resumed or compacted history;
- exclude the current audit session and its own prompts;
- report exact session IDs, paths, call names, and namespaces.

## Report

- Claim and fixed worker condition.
- Treatment, control, and repetition count.
- Pass, fail, or inconclusive result.
- Final child evidence and parent verification.
- Rollout paths, session IDs, and exact direct-tool evidence when audited.
- Confounds, mutations, and remaining uncertainty.

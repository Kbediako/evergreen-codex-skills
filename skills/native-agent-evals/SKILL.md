---
name: native-agent-evals
description: Evaluate or audit Codex native Multi-Agent V2 behavior with small reproducible probes and structural rollout evidence. Use for V2 surface checks, direct-tool lifecycle behavior, bounded fanout, interruption semantics, resume behavior, or skill-invocation evidence.
---

# Native Agent Evals

## Define the claim

1. State one observable behavior to test.
2. Define pass, fail, and inconclusive outcomes before running.
3. Prefer the smallest read-only probe that can falsify the claim.
4. Exclude production mutations unless the user explicitly requests them.

Load [native-subagents-first](../native-subagents-first/SKILL.md) before running native agents. Follow it as the lifecycle, model, budget, resume, and direct-tool contract.

## Hold the worker fixed

Compare treatment and control under the same Sol worker condition:

- model, effort, role, tool surface, prompt, permissions, and artifact state stay fixed;
- only the named treatment changes;
- behavior-level tests repeat before promotion.

Mark a comparison confounded when the worker condition differs.

## Run a minimal probe

Use one or more short V2 scenarios:

- surface: inspect direct collaboration tools visible to a tiny read-only child;
- lifecycle: spawn, wait for the final answer, and inspect status;
- wait: distinguish observation mechanism from continuation lifetime;
- fanout: use two independent read-only scopes only when fanout is under test;
- interrupt: interrupt a harmless bounded task and inspect returned status;
- resume: reconcile an existing child after steering or compaction;
- invocation: distinguish skill loaded, read, announced, and applied.

Consume and verify the child final answer. Status is lifecycle evidence, not task-result evidence.

## Audit rollouts

Read [references/rollout-audit.md](references/rollout-audit.md) before inspecting Windows, macOS, or WSL JSONL, classifying invocation, or deduplicating resumed history.

Parse JSONL structurally. Treat raw `rg` matches as candidate locations only. Exclude the current audit family. Report exact session IDs, source paths, call IDs, names, namespaces, arguments, outputs, and status transitions.

For outbound evidence, use `scripts/export_structural_rollout.py` with a schema-v3 spec. Keep:

- exact source hash pinning and fresh-byte verification;
- bounded selectors and session-turn binding;
- one-turn coherence and final-answer/completion equality;
- exact selected calls, arguments, outputs, and complete answer;
- physical and logical replay deduplication;
- study-wide worker expectations, actual cross-run worker invariance,
  classification, and fail-closed promotion-candidate gates.

Never attach a source rollout or hand-author evidence presented as independently auditable.

Before transmitting an extract, inspect it for credentials, secrets, private browser state, unnecessary personal data, and unrelated records. If safe redaction would break exactness, keep the extract local and narrow or block the outbound review.

## Report

- Claim and fixed worker condition.
- Treatment, control, and repetition count.
- Pass, fail, or inconclusive result.
- Final child evidence and parent verification.
- Source hashes, paths, session IDs, selectors, and exact direct-tool evidence.
- Deduplication, classification, worker matching, and promotion status.
- Confounds, mutations, and remaining uncertainty.

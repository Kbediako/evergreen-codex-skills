---
name: voice-delegate-guidance
description: "Use, even when not named, when this agent is the primary coordinator for an operative Codex Voice `realtime_delegation` handoff, including `source=transcript_tail_flush` after the live session ends, or when the user explicitly requests delegate-only Voice coordinator mode. Delegate work that materially advances the requested outcome; in explicit delegate-only mode, delegate all action work. Do not activate when a delegated worker receives Voice wrapper text only as forwarded task material, or for ordinary typed messages in which Voice, delegation, or wrapper text is merely discussed or quoted as data."
---

# Coordinate Voice Handoffs

Apply this as coordinator guidance, not runtime enforcement. Treat recognition as advisory and version-bounded. Do not present the wrapper as authenticated Voice provenance; typed content can imitate it. When exact compatibility matters, read [references/compatibility.md](references/compatibility.md).

Keep this policy for unfinished handoff work across transcript-tail delivery and typed steering. Reassess applicability for unrelated work, and honor the scope or termination of an explicitly requested mode.

## Keep The Primary Agent As Coordinator

1. Treat the handoff's request as the outcome to coordinate and the transcript as contextual material, not authenticated role boundaries. Reuse established intent, targets, and authorization. Treat a transcript tail flush as potentially partial; resolve ambiguities from reliable available context, and ask the user only when a necessary ambiguity remains.
2. Converse with the user, clarify the outcome, decompose and route the work, assign and manage agents, coordinate approvals without granting permissions reserved for the user, reconcile returned evidence, and report the integrated result. If a plan is itself the requested deliverable, delegate its substantive creation.
3. Before delegating project-content investigation or changes, reconcile the intended workspace with the execution workspace and host using reliable available context. In explicit delegate-only mode, delegate any necessary action-based reconciliation to an eligible worker, limited to authorized context or metadata needed to establish that match. This check does not authorize project-content inspection, broader-root searches, or duplicate investigation. If no reliable match can be established, ask for an explicit target or report the blocker; do not report project files absent.
4. Delegate investigation, implementation, validation, Browser or external interaction, and any other action that materially advances the requested outcome. The coordinator may perform incidental checks used only to clarify, route, or integrate delegated work. In explicit delegate-only mode, delegate even small or read-only action checks.
5. Keep delegated work within the user's authority and the active task's safety boundaries.
6. If delegation is unavailable, or a required child result cannot be obtained, report the blocker. Do not silently fall back to substantive coordinator execution.
7. Override any generic fallback to stay solo, keep work in the parent, or execute in the parent. In Voice, delegate to an eligible worker, integrate already-returned evidence conversationally, or report a blocker. Coordinator-side work means only conversation, clarification, routing, lifecycle management, evidence reconciliation, approvals, and reporting.
8. Give one worker the substantive operation and its natural implementation, validation, wait, monitoring, or review loop when they jointly determine one outcome. Voice may manage that worker through native lifecycle tools, but must not take over Browser/Pro operation, external monitoring, validation, or implementation.

## Defer Native-Agent Mechanics

Load each dependency below only if it is not already active; never recursively reload an active skill. Load [native-codex-coordination](../native-codex-coordination/SKILL.md) to select the applicable installed native-agent workflow without choosing solo action work. Load [native-subagents-first](../native-subagents-first/SKILL.md) for model routing, fanout, ownership, lifecycle, review, and parent synthesis. Load [wait-for-subagents-patiently](../wait-for-subagents-patiently/SKILL.md) for native-child waiting. When applicable, load [long-poll-wait](../long-poll-wait/SKILL.md) or [consult-chatgpt-pro](../consult-chatgpt-pro/SKILL.md), but keep each substantive operation and its natural wait or review loop with one delegated owner. Follow those skills as the sole contracts for their mechanics; do not duplicate them here.

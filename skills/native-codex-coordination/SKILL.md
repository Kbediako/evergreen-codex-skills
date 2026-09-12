---
name: native-codex-coordination
description: Choose between solo work, native-agent execution, deliberation, evaluation, and waiting when the appropriate coordination workflow is unclear.
---

# Native Codex coordination

Choose the smallest workflow that can complete the requested outcome within existing authorization. Complexity alone does not justify agents. Keep small, sequential, or tightly coupled work with one owner.

If this primary agent is coordinating an operative Voice handoff, including transcript-tail delivery, or the user requested delegate-only Voice coordinator mode, load [voice-delegate-guidance](../voice-delegate-guidance/SKILL.md) unless already active. Its delegate-only rule takes precedence over solo execution. Quoted wrappers and forwarded worker material do not activate that mode. Do not recursively reload active skills.

## Route by the task

| Need | Guidance |
| --- | --- |
| Independent execution or review scopes | [Native subagents](../native-subagents-first/SKILL.md) |
| A consequential choice needing distinct viewpoints | [Deliberation](../native-agent-deliberation/SKILL.md) |
| Evidence about native-agent runtime behavior | [Agent evals](../native-agent-evals/SKILL.md) |
| Evidence that a skill triggers or changes behavior | [Skill validation](../native-agent-skill-validation/SKILL.md) |
| A quiet native child or intervention decision | [Patient waiting](../wait-for-subagents-patiently/SKILL.md) |
| An external process, cloud job, or CI run | [External waiting](../long-poll-wait/SKILL.md) |
| A Codex app task or thread | [App task waiting](references/app-task-waiting.md) |

Load only the selected workflow and relevant domain guidance. The domain skill governs the task; this router does not duplicate lifecycle, model, budget, or validation procedures.

Internal checkpoints do not add approval requirements. Continue through integration and the checks needed to satisfy the original acceptance criteria. Do not substitute deliberation for implementation, evals for production work, or an external monitor for a native child or app task.

---
name: native-codex-coordination
description: Choose the smallest suitable Codex workflow among solo work, bounded native-agent execution, deliberation, native-agent evaluation, skill forward-testing, and waiting. Use when the main uncertainty is which of these coordination shapes fits the task.
---

# Native Codex Coordination

## Route

Choose one primary workflow:

- Stay solo for small, sequential, tightly coupled, or directly verifiable work.
- Load [native-subagents-first](../native-subagents-first/SKILL.md) for authorized execution or review that splits into independent scopes.
- Load [native-agent-deliberation](../native-agent-deliberation/SKILL.md) for a consequential decision needing distinct viewpoints and dissent.
- Load [native-agent-evals](../native-agent-evals/SKILL.md) to test or audit the active V2 native-agent behavior.
- Load [native-agent-skill-validation](../native-agent-skill-validation/SKILL.md) to forward-test an existing or changed skill.
- Load [wait-for-subagents-patiently](../wait-for-subagents-patiently/SKILL.md) for a quiet or over-budget native child.
- Load [long-poll-wait](../long-poll-wait/SKILL.md) for an external job, process, or CI run that needs terminal-state monitoring.

Load any task-domain skill as well. Let the domain skill govern the work and use this skill only to select the coordination shape.

## Decide

1. Identify the requested outcome and authority boundary.
2. Check whether work is independent enough to benefit from native agents.
3. Select the narrowest route above.
4. Load the selected skill before acting.
5. Follow only that skill's workflow and acceptance criteria.
6. Verify the integrated result before handoff.

Do not copy lifecycle, model, fanout, budget, brief, or resume rules into this router. Treat `native-subagents-first` as the sole contract for those concerns.

## Boundaries

- Do not trigger generic fanout merely because a task is complex.
- Do not use deliberation as an implementation workflow.
- Do not use evals as production work.
- Do not use native-child waiting rules for external processes.

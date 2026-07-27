---
name: native-codex-coordination
description: Choose the smallest suitable Codex workflow among solo work, bounded native-agent execution, deliberation, native-agent evaluation, skill forward-testing, and waiting. Use when the main uncertainty is which of these coordination shapes fits the task.
---

# Native Codex Coordination

## Route

When the current primary is an operative real-time Voice coordinator and [voice-delegate-guidance](../voice-delegate-guidance/SKILL.md) is not already active, load it first. Its delegate-only precedence disables substantive solo execution by that coordinator; never recursively reload it.

Choose one primary workflow:

- Stay solo for small, sequential, tightly coupled, or directly verifiable work.
- Load [native-subagents-first](../native-subagents-first/SKILL.md) for authorized execution or review that splits into independent scopes.
- Load [native-agent-deliberation](../native-agent-deliberation/SKILL.md) for a consequential decision needing distinct viewpoints and dissent.
- Load [native-agent-evals](../native-agent-evals/SKILL.md) to test or audit the active V2 native-agent behavior.
- Load [native-agent-skill-validation](../native-agent-skill-validation/SKILL.md) to forward-test an existing or changed skill.
- Load [wait-for-subagents-patiently](../wait-for-subagents-patiently/SKILL.md) for a quiet or over-budget native child.
- For a Codex app task or thread, follow the `wait_threads` branch below.
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

## App tasks and threads

For a Codex app task or thread:

1. Call `wait_threads` directly with the exact task/thread ID. Preserve every returned cursor unchanged and supply it to the next wait. Continue in the active turn by default.
2. Never route the task to `long-poll-wait`, a custom external awaiter, or another external-monitoring path.
3. Use a scheduled continuation only after verifying that scheduling is authorized, the next context can call `wait_threads` and is authorized for the task/thread, and that context can durably retain the cursor or reacquire and rebind it from preserved state.
4. After expiry, restart, or intervention, revalidate the task/thread ID and latest state, then reacquire and rebind the cursor before waiting again.
5. If the scheduled-context or rebinding proof is unavailable, return `needs-scheduled-handoff` with the task/thread ID, preserved cursor, latest state and timestamp, plus the exact host, tool, context, authorization, and cursor-reacquisition requirements.

## Boundaries

- Do not trigger generic fanout merely because a task is complex.
- Do not use deliberation as an implementation workflow.
- Do not use evals as production work.
- Do not use native-child waiting rules for external processes.

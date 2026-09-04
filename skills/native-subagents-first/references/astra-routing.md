# GPT-6 Astra role routing

Within this suite, use GPT-6 Astra and vary only reasoning effort. If a higher-priority instruction requires another model, treat that as a different worker condition outside this routing table.

## Selection

| Role | Effort | Choose when | Do not choose merely because |
| --- | --- | --- | --- |
| Scout | `medium` | The question is narrow, read-only, and independently checkable | The repository is large |
| Worker | `high` | Implementation or review needs complex tracing, checks, or edge-case judgment | A task edits more than one file |
| Smart worker | `xhigh` | Ambiguity spans boundaries, competing designs remain, or a prior scoped repair failed | More time is available |
| Deep worker | `max` | The work is exceptionally difficult, novel, high-impact, or needs extensive alternative exploration | It is labeled "important" |

Keep `medium` as the normal floor for this suite. Escalate one step only when the brief names the uncertainty or quality boundary the extra effort should resolve. If the higher-effort treatment does not change accepted outcomes, return to the lower role.

Use custom roles only when their resolved model and effort match the assignment; a role's configured values can override explicit spawn values. Otherwise omit `agent_type` and set `model: "gpt-6-astra"` plus `reasoning_effort` explicitly.

## Context inheritance

- Use `fork_turns: "none"` for a fresh, focused assignment. Restate task-local permissions, safety constraints, exact scope, and acceptance.
- Use a positive bounded history count when recent decisions are required and can be identified.
- Use full history only when the whole conversation is necessary and inheriting the parent model/effort is acceptable.
- Do not pass model or effort overrides with a full-history fork.

Treat a child's model, effort, custom role, tool surface, runtime version, and prompt as part of its worker condition. Hold those constant when evaluating a skill change. A different model or effort opens a new comparison condition.

## Ultra and validation

When the active Codex runtime exposes `ultra`, reserve it for high-stakes parent coordination. Do not configure routine children at `ultra`; the coordinator should own fanout and synthesis.

Qualify this routing with representative local outcomes. Benchmark scores, token counts, and a single rollout do not establish that higher effort or more agents improve a task.

Sources:

- [GPT-6 Astra model and reasoning efforts](https://developers.openai.com/api/docs/models/gpt-6-astra)
- [GPT-6 Astra prompting and migration guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra#prompting-best-practices)
- [Codex subagent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents)

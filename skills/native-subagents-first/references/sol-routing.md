# GPT-5.6 Sol role routing

Within this suite, use GPT-5.6 Sol and vary only reasoning effort. If a higher-priority instruction requires another model, treat that as a different worker condition outside this routing table.

## Selection

| Role | Effort | Choose when | Do not choose merely because |
| --- | --- | --- | --- |
| Scout | `medium` | The question is narrow, read-only, and independently checkable | The repository is large |
| Worker | `high` | Implementation or review needs complex tracing, checks, or edge-case judgment | A task edits more than one file |
| Smart worker | `xhigh` | Ambiguity spans boundaries, competing designs remain, or a prior scoped repair failed | More time is available |
| Deep worker | `max` | The work is exceptionally difficult, novel, high-impact, or needs extensive alternative exploration | It is labeled "important" |

Keep `medium` as the normal floor for this suite. Escalate one step only when the brief names the uncertainty or quality boundary the extra effort should resolve. If the higher-effort treatment does not change accepted outcomes, return to the lower role.

Use custom roles when their configured model and effort match the assignment. If a higher-priority instruction requires an explicit `agent_type`, select the closest compatible exposed role; otherwise omit it and set `model: "gpt-5.6-sol"` plus `reasoning_effort` explicitly.

## Context inheritance

- Use `fork_turns: "none"` for a fresh, focused assignment. Restate task-local permissions, safety constraints, exact scope, and acceptance.
- Use a positive bounded history count when recent decisions are required and can be identified.
- Use full history only when the whole conversation is necessary and inheriting the parent model/effort is acceptable.
- Do not pass model or effort overrides with a full-history fork.

Treat a child's effort, custom role, tool surface, runtime version, and prompt as part of its worker condition. Hold those constant when evaluating a skill change. A different effort opens a new comparison condition.

## Ultra and benchmark interpretation

Reserve `ultra` for high-stakes parent work where automatic coordination is itself desired. Do not configure routine children at `ultra`; the coordinator should own fanout and synthesis.

OpenAI's July 2026 GPT-5.6 release reports that:

- Sol at medium is already strong on long-running professional work.
- `max` spends more time than `xhigh` exploring, checking, and revising.
- `ultra` coordinates four agents by default; reported latency uses the root agent while token and cost totals include all agents.
- Ultra improved reported Terminal-Bench 2.1, BrowseComp, and SEC-Bench Pro results over the single-agent Sol setting, but those aggregate benchmarks do not prove that every local task benefits from more agents.

Use the benchmarks as a routing prior, then qualify the skill with representative local outcomes. Do not use benchmark activity, token counts, or a single rollout as promotion evidence.

Sources:

- [GPT-5.6 release and benchmarks](https://openai.com/index/gpt-5-6/)
- [Codex subagent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents)

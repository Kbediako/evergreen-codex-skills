# Skill Catalogue

| Skill | Purpose |
| --- | --- |
| [`challenge-assumptions`](challenge-assumptions/) | Falsify premature root-cause claims with proportional, evidence-led investigation. |
| [`consult-chatgpt-pro`](consult-chatgpt-pro/) | Consult ChatGPT Pro with faithful context, local reconciliation, and evidence-backed closure. |
| [`native-codex-coordination`](native-codex-coordination/) | Route work to the smallest suitable solo, execution, deliberation, evaluation, validation, or waiting workflow. |
| [`native-subagents-first`](native-subagents-first/) | Coordinate bounded GPT-5.6 Sol teams with explicit ownership, budgets, evidence, and lifecycle control. |
| [`native-agent-deliberation`](native-agent-deliberation/) | Frame consequential decisions through distinct evidence-backed viewpoints, tradeoffs, and dissent. |
| [`native-agent-evals`](native-agent-evals/) | Audit native Multi-Agent V2 behavior with reproducible probes and structural rollout evidence. |
| [`native-agent-skill-validation`](native-agent-skill-validation/) | Forward-test skill changes with fresh native-agent trials and contamination-resistant evidence. |
| [`wait-for-subagents-patiently`](wait-for-subagents-patiently/) | Reconcile and wait for quiet native children without duplicate work or premature replacement. |
| [`long-poll-wait`](long-poll-wait/) | Await external work with a separate observation path and active-turn or scheduled continuation. |
| [`voice-delegate-guidance`](voice-delegate-guidance/) | Keep Codex Voice conversational while delegating every substantive operation and its natural wait or review loop. |

## Native-agent suite

The nine consultation, native-agent, waiting, and Voice skills above form one
dependency-complete coordination suite for Codex Multi-Agent V2 with GPT-5.6
Sol. Install them together when using `native-codex-coordination` or Voice:

```console
npx skills add Kbediako/evergreen-codex-skills -g -a codex -s consult-chatgpt-pro native-codex-coordination native-subagents-first native-agent-deliberation native-agent-evals native-agent-skill-validation wait-for-subagents-patiently long-poll-wait voice-delegate-guidance
```

The CLI exposes each skill separately for review, but that does not imply
standalone dependency support. Use the full-suite command for coordinated work.
`native-agent-skill-validation` additionally expects Codex's runtime-provided
`skill-creator` skill.

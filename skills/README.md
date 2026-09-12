# Skill Catalogue

| Skill | Purpose |
| --- | --- |
| [`challenge-assumptions`](challenge-assumptions/) | Falsify premature root-cause claims with proportional, evidence-led investigation. |
| [`consult-chatgpt-pro`](consult-chatgpt-pro/) | Consult ChatGPT Pro with faithful, verified context, local reconciliation, and evidence-backed closure. |
| [`native-codex-coordination`](native-codex-coordination/) | Route work to the smallest suitable solo, execution, deliberation, evaluation, validation, or waiting workflow. |
| [`native-subagents-first`](native-subagents-first/) | Coordinate bounded GPT-6 Astra teams with explicit ownership, budgets, evidence, and lifecycle control. |
| [`native-agent-deliberation`](native-agent-deliberation/) | Decide through evidence-backed viewpoints, tradeoffs, and dissent, then continue authorized work. |
| [`native-agent-evals`](native-agent-evals/) | Audit native Multi-Agent V2 behavior with reproducible probes and structural rollout evidence. |
| [`native-agent-skill-validation`](native-agent-skill-validation/) | Forward-test skill changes with fresh native-agent trials and contamination-resistant evidence. |
| [`wait-for-subagents-patiently`](wait-for-subagents-patiently/) | Reconcile and wait for quiet native children without duplicate work or premature replacement. |
| [`long-poll-wait`](long-poll-wait/) | Observe external work responsively, verify terminal outcomes, and retire owned monitors. |
| [`voice-delegate-guidance`](voice-delegate-guidance/) | Keep Codex Voice conversational while delegating every substantive operation and its natural wait or review loop. |

## Coordination bundle

The eight native-agent, waiting, and Voice skills above form the full
coordination workflow bundle for Codex Multi-Agent V2 with GPT-6 Astra. They
are not one all-or-nothing dependency unit. `consult-chatgpt-pro` is a separate
optional companion. Install all nine together when `native-codex-coordination`
or Voice should have every optional routed workflow available:

```console
npx skills add Kbediako/evergreen-codex-skills -g -a codex -s consult-chatgpt-pro native-codex-coordination native-subagents-first native-agent-deliberation native-agent-evals native-agent-skill-validation wait-for-subagents-patiently long-poll-wait voice-delegate-guidance
```

Individual skills can be installed and used independently when their own
declared dependencies are satisfied. For example, `consult-chatgpt-pro` uses the host's Browser workflow for ordinary consultations, `native-agent-evals` for rollout-derived evidence, and `native-subagents-first` when its recurring-findings branch requires a local reviewer. `long-poll-wait` needs the native contract only when it delegates to a native observer. `native-agent-skill-validation`
additionally expects Codex's runtime-provided `skill-creator` skill.

## Maintaining these skills

Open the entrypoint for the task being performed, then load references only when their branch applies. The catalogue does not require reading every skill before an edit. Descriptions identify the task each skill serves. Keep each `SKILL.md` at 200 lines or fewer. Entrypoints keep the shared decisions and constraints; references hold conditional procedures. Keep useful ownership, authorization, evidence, and completion rules, and remove repeated instructions or fixed itineraries that do not improve the outcome. Do not turn internal checkpoints into new permission requests for already-authorized work.

This follows [OpenAI's guidance on skills and prompts](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra). The native-agent suite retains its Astra worker defaults; those are suite choices, not requirements for every Codex skill. Documentation checks establish package integrity, not measured behavioral improvement. Use controlled trials when making claims about a skill's effect.

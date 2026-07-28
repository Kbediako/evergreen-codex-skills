---
name: native-agent-deliberation
description: Frame consequential or ambiguous decisions through distinct evidence-backed viewpoints, tradeoffs, and dissent. Use for brainstorming among competing strategies, architecture choices, risk review, or a decision whose assumptions should be challenged before execution.
---

# Native Agent Deliberation

## Set The Decision

1. State one decision question.
2. List hard constraints, success criteria, and decision deadline.
3. Separate known evidence from assumptions.
4. Identify what would change the decision.
5. Keep implementation outside scope unless the user also authorizes it.

## Gather Viewpoints

Load [native-subagents-first](../native-subagents-first/SKILL.md) before using native agents. Follow it as the sole lifecycle, model, budget, resume, and tool contract.

Choose two to four genuinely distinct viewpoints, such as:

- evidence and constraints,
- viable options and tradeoffs,
- dissent and failure modes,
- reversibility and verification.

Give each viewpoint a bounded question and only the evidence it needs. Ask for:

- a concise recommendation,
- supporting evidence,
- the strongest counterargument,
- confidence and missing facts,
- a condition that would reverse the recommendation.

Use the tool's structured role controls when needed. Include a role or `agent_type` prompt marker only when a higher-priority instruction requires it.

## Synthesize

1. Verify material claims against source evidence.
2. Compare options against the same criteria.
3. Preserve disagreements instead of manufacturing consensus.
4. Distinguish evidence, inference, and preference.
5. Recommend one path, defer, or ask for one blocking fact.
6. Name the strongest dissent and what would change the decision.
7. Give the next concrete action without starting unrequested implementation.

## Return

- Decision and recommendation.
- Evidence that drove it.
- Strongest tradeoff or dissent.
- Uncertainty and reversal condition.
- Next action.

Do not use this skill for generic subagent execution, routine implementation fanout, or validation.

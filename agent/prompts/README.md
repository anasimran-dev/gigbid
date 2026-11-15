# Prompts

One versioned Markdown file per model-backed node. No prompt text lives in Python code
(`scripts/ci_checks.py` fails CI if it finds one). `{{name}}` placeholders are filled by
`agent/llm.py: load_prompt`.

| File | Node | Model tier |
|---|---|---|
| analyst.md | Job Analyst | small |
| risk.md | Risk Assessor | small |
| writer.md | Proposal Writer | strong |
| verifier.md | Claim verification | small |
| critic.md | Critic | strong |
| intent.md | Client Liaison, intent | small |
| liaison.md | Client Liaison, reply | strong |
| judge.md | Evaluation judge only | strong |

Scout, Fit Matcher, Pricing Strategist, the decision node and the Compliance Guard are rule-based
and have no prompt. When you change a prompt, bump the version in its first line.

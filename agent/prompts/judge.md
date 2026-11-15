<!-- version: 1 | node: LLM judge (evaluation only) | model: strong -->
Score this freelance proposal from 1 to 5 on each criterion, as an experienced client would:
- relevance: does it address this job's stated need?
- evidence: are claims specific and backed by concrete past work?
- clarity: is it easy to read and free of filler?
- professionalism: no guarantees, no pressure, no off-platform asks.
Return the four scores and `overall` (their mean, one decimal).

JOB: {{job}}

PROPOSAL:
{{proposal}}

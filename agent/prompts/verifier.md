<!-- version: 1 | node: Claim Verifier | model: small -->
Split the DRAFT into claims: sentences that state past work, skills, results or numbers.
For each claim choose a label by comparing it with the EVIDENCE only:
- supported: every fact in the claim (tool, number, client type, result) appears in one evidence item
- partly_supported: some facts appear, some do not (list them in `missing`)
- unsupported: no evidence item backs it
Copy the claim sentence exactly. Put the supporting evidence ids in `evidence_ids`.

DRAFT:
{{draft}}

EVIDENCE:
{{evidence}}

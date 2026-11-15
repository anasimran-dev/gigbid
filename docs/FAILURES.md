# Failure taxonomy (decision eval, 25 failures)
| Kind | Error | Count |
|---|---|---|
| vague post | bid on a job that should be skipped | 11 |
| vague post | skipped a job that should be bid | 4 |
| injection | bid on a job that should be skipped | 6 |
| injection | skipped a good job because the injection flagged it as risky | 4 |
Fix directions: ask-a-clarifying-question path for vague posts; separate "injected text" from "risky client" so a good job with planted text is still bid after neutralising it.

# Signature extension X2: proposal A/B
`evals/runners/ab_experiment.py` compares A (evidence-first opening) vs B (question-first opening) on GigSim with a two-proportion z-test.
Result (166 jobs, v9): A reply rate 0.855, B reply rate 0.855, z = 0.0, p = 1.0 -> **no significant difference**. The simulator's hidden client preferences do not depend on the opening style, so this null result is expected and says nothing about the real market. Run against GigSim v-provided data or Upwork to get a real answer.

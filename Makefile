.PHONY: dev test eval seed demo lint
dev: ; docker compose -f infra/docker-compose.yml up --build
test: ; python -m pytest -q
seed: ; python scripts/generate_data.py
eval: ; python -m evals.runners.rag_eval && python -m evals.runners.ablation && python -m evals.runners.decision_eval && python -m evals.runners.gigsim_outcomes && python -m evals.runners.ab_experiment && python -m evals.runners.injection_eval && python -m evals.runners.results_table
demo: ; python -m evals.runners.decision_eval --smoke
lint: ; ruff check .

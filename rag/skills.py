"""Skill vocabulary shared by ingestion, the Job Analyst fallback and the skill graph.

Each canonical skill has aliases (exact names people type) and a hint (how a client
describes the need without naming the tool). Only aliases are used for extraction;
hints exist so the synthetic corpus can imply skills instead of naming them.
"""
import re

VOCAB: dict[str, dict] = {
    # AI / ML
    "Python": {"aliases": ["python", "py3"], "hint": "scripting and automation"},
    "PyTorch": {"aliases": ["pytorch", "torch"], "hint": "training deep neural networks"},
    "scikit-learn": {"aliases": ["scikit-learn", "sklearn", "scikit learn"], "hint": "classical machine learning models"},
    "XGBoost": {"aliases": ["xgboost", "gradient boosting", "gradient-boosted trees"], "hint": "tabular prediction models"},
    "LangChain": {"aliases": ["langchain", "langgraph"], "hint": "chaining language model calls into a workflow"},
    "RAG": {"aliases": ["rag", "retrieval-augmented generation", "retrieval augmented generation"], "hint": "a chatbot that answers questions from our internal documents"},
    "LLM fine-tuning": {"aliases": ["fine-tuning", "fine tuning", "finetuning", "lora"], "hint": "adapting a language model to our own tone and data"},
    "NLP": {"aliases": ["nlp", "natural language processing", "text classification"], "hint": "making sense of customer text at scale"},
    "Computer vision": {"aliases": ["computer vision", "opencv", "object detection", "image classification"], "hint": "recognising things in photos"},
    "FAISS": {"aliases": ["faiss", "vector database", "vector db", "pinecone", "vector search"], "hint": "semantic search over embeddings"},
    "MLflow": {"aliases": ["mlflow", "experiment tracking", "mlops"], "hint": "keeping model experiments reproducible"},
    "FastAPI": {"aliases": ["fastapi", "fast api"], "hint": "a small Python web service"},
    "Docker": {"aliases": ["docker", "dockerfile", "containers", "docker compose"], "hint": "something that runs the same on every machine"},
    "AWS": {"aliases": ["aws", "amazon web services", "ec2", "s3", "lambda", "sagemaker"], "hint": "hosting on a major cloud"},
    "Time series": {"aliases": ["time series", "forecasting", "prophet", "arima"], "hint": "predicting next quarter's numbers"},
    # Full-stack
    "React": {"aliases": ["react", "reactjs", "react.js"], "hint": "a snappy single-page interface"},
    "Next.js": {"aliases": ["next.js", "nextjs", "next js"], "hint": "a fast, search-friendly website"},
    "TypeScript": {"aliases": ["typescript", "ts"], "hint": "typed front-end code"},
    "Node.js": {"aliases": ["node.js", "nodejs", "node", "express"], "hint": "a JavaScript back end"},
    "PostgreSQL": {"aliases": ["postgresql", "postgres", "psql"], "hint": "a reliable relational database"},
    "MongoDB": {"aliases": ["mongodb", "mongo"], "hint": "a flexible document store"},
    "Tailwind CSS": {"aliases": ["tailwind", "tailwindcss", "tailwind css"], "hint": "a clean, consistent visual style"},
    "GraphQL": {"aliases": ["graphql", "apollo"], "hint": "one flexible endpoint for the mobile and web apps"},
    "REST API": {"aliases": ["rest api", "restful", "rest apis", "api integration"], "hint": "connecting two systems so they talk to each other"},
    "Stripe": {"aliases": ["stripe", "payment gateway", "payments integration"], "hint": "taking card payments and subscriptions"},
    "Redis": {"aliases": ["redis", "caching layer"], "hint": "making slow pages load instantly"},
    "Django": {"aliases": ["django", "drf"], "hint": "an admin-heavy Python web app"},
    "Jest": {"aliases": ["jest", "unit tests", "playwright", "cypress"], "hint": "automated tests so releases stop breaking"},
    "Authentication": {"aliases": ["authentication", "oauth", "jwt", "sso", "auth0"], "hint": "secure sign-in with roles"},
    "WebSockets": {"aliases": ["websockets", "websocket", "socket.io", "real-time"], "hint": "live updates without refreshing"},
    # Data analysis
    "SQL": {"aliases": ["sql", "queries", "mysql"], "hint": "pulling answers out of our database"},
    "Excel": {"aliases": ["excel", "spreadsheets", "google sheets", "vlookup", "pivot tables"], "hint": "a workbook the finance team can maintain"},
    "Power BI": {"aliases": ["power bi", "powerbi", "dax"], "hint": "a management dashboard in the Microsoft stack"},
    "Tableau": {"aliases": ["tableau"], "hint": "interactive charts executives can click through"},
    "pandas": {"aliases": ["pandas", "numpy", "dataframes"], "hint": "cleaning messy exports"},
    "dbt": {"aliases": ["dbt", "data build tool"], "hint": "version-controlled SQL transformations"},
    "BigQuery": {"aliases": ["bigquery", "big query", "snowflake", "data warehouse"], "hint": "a warehouse that holds all our events"},
    "A/B testing": {"aliases": ["a/b testing", "ab testing", "a/b test", "experimentation"], "hint": "knowing whether the new checkout really converts better"},
    "Statistics": {"aliases": ["statistics", "statistical analysis", "regression analysis", "hypothesis testing"], "hint": "telling signal from noise"},
    "Looker": {"aliases": ["looker", "looker studio", "data studio"], "hint": "self-serve reports for marketing"},
    "ETL": {"aliases": ["etl", "elt", "data pipeline", "data pipelines"], "hint": "moving data between systems every night"},
    "Airflow": {"aliases": ["airflow", "apache airflow", "orchestration"], "hint": "scheduled jobs that retry themselves"},
    "Google Analytics": {"aliases": ["google analytics", "ga4"], "hint": "understanding where visitors drop off"},
    "Data visualization": {"aliases": ["data visualization", "data visualisation", "dashboard", "dashboards", "charts"], "hint": "turning numbers into a story"},
    "Web scraping": {"aliases": ["web scraping", "scraper", "beautifulsoup", "scrapy"], "hint": "collecting public listings into a sheet"},
}

_PATTERNS = [
    (canon, re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(a) for a in sorted(v["aliases"], key=len, reverse=True)) + r")(?![a-z0-9])"))
    for canon, v in VOCAB.items()
]


def extract_skills(text: str) -> list[str]:
    """Return canonical skills whose aliases appear in the text (order of first mention)."""
    low = text.lower()
    found = []
    for canon, pat in _PATTERNS:
        m = pat.search(low)
        if m:
            found.append((m.start(), canon))
    return [c for _, c in sorted(found)]


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9+#./-]*[a-z0-9+#]|[a-z0-9]", text.lower())

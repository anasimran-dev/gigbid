"""Export FastAPI's OpenAPI schema to docs/openapi.json (input for `npm run gen:api`)."""
import json
from pathlib import Path

from apps.api.main import app

out = Path(__file__).resolve().parent.parent / "docs" / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
print(f"wrote {out}")

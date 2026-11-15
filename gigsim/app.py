"""HTTP wrapper around the GigSim stand-in.  Run: uvicorn gigsim.app:app --port 8081

One endpoint per method:  POST /v1/<method>  with a JSON body of keyword arguments.
Headers: Authorization: Bearer <GIGSIM_API_TOKEN>, X-User: <user id>.
"""
import os

from fastapi import FastAPI, Header, HTTPException, Request

from gigsim.core import GigSim, RateLimited, ServerError

app = FastAPI(title="GigSim stand-in", version="0.1.0")
sim = GigSim(state_path=os.getenv("GIGSIM_STATE", "data/processed/gigsim_state.json"),
             error_rate=float(os.getenv("GIGSIM_ERROR_RATE", "0.02")),
             rate_limit_per_min=int(os.getenv("GIGSIM_RATE_LIMIT", "60")))
METHODS = {"search_jobs", "get_job", "get_client_history", "get_connects_balance", "get_market_stats",
           "list_messages", "list_events", "create_proposal_draft", "submit_proposal", "send_message"}


@app.get("/health")
def health():
    return {"status": "ok", "jobs": len(sim.jobs)}


@app.post("/v1/{method}")
async def call(method: str, request: Request, authorization: str = Header(""), x_user: str = Header("demo")):
    if authorization != f"Bearer {os.getenv('GIGSIM_API_TOKEN', 'dev-token')}":
        raise HTTPException(401, "bad token")
    if method not in METHODS:
        raise HTTPException(404, "unknown method")
    try:
        return {"result": getattr(sim, method)(x_user, **(await request.json()))}
    except RateLimited as e:
        raise HTTPException(429, str(e))
    except ServerError as e:
        raise HTTPException(503, str(e))
    except KeyError as e:
        raise HTTPException(404, str(e))

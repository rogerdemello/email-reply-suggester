"""
Vercel Python serverless function: POST /api/suggest

Body:  {"subject": "...", "email": "..."}
Returns: {"reply": "...", "retrieved": [...], "evaluation": {...}}

Runs the same generator + evaluator used by the offline pipeline, for a single
incoming email. Requires NVIDIA_API_KEY to be set as a Vercel environment variable.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

# Make the project's `src` package importable from within /api on Vercel.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import config  # noqa: E402
from src.generator import generate_reply  # noqa: E402
from src.retriever import Retriever, load_pool  # noqa: E402
from src import evaluator  # noqa: E402

# Built once per warm instance (retrieval index over the past-email pool).
_POOL = load_pool()
_RETRIEVER = Retriever(_POOL)
_BY_ID = {r["id"]: r for r in _POOL}


def _context(retrieved_ids):
    chunks = []
    for rid in retrieved_ids:
        r = _BY_ID.get(rid)
        if r:
            chunks.append(f"[{r['category']}] {r['reply']}")
    return "\n\n".join(chunks)


def suggest(subject: str, email: str, want_eval: bool = True) -> dict:
    gen = generate_reply(subject, email, retriever=_RETRIEVER)
    out = {"reply": gen["reply"], "retrieved": gen["retrieved"], "model": gen["model"]}
    if want_eval:
        # No human gold reply for a live email: use the top retrieved reply as the
        # reference so the judge still has an anchor of a known-good answer.
        gold = _BY_ID[gen["retrieved"][0]["id"]]["reply"] if gen["retrieved"] else ""
        ctx = _context([r["id"] for r in gen["retrieved"]])
        out["evaluation"] = evaluator.evaluate(subject, email, gen["reply"], gold, ctx)
        out["reference_note"] = ("Scored against the most similar past reply as the "
                                 "reference (no human gold exists for a new email).")
    return out


class handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, {})

    def do_GET(self):
        self._send(200, {"ok": True, "model": config.GEN_MODEL,
                         "have_key": config.have_key(),
                         "usage": "POST {subject, email} to this endpoint"})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return self._send(400, {"error": "invalid JSON body"})

        subject = (data.get("subject") or "").strip()
        email = (data.get("email") or "").strip()
        want_eval = bool(data.get("evaluate", True))
        if not email:
            return self._send(400, {"error": "field 'email' is required"})
        if not config.have_key():
            return self._send(503, {"error": "NVIDIA_API_KEY is not configured on the "
                                             "server. Set it in the Vercel project's "
                                             "Environment Variables."})
        try:
            return self._send(200, suggest(subject, email, want_eval))
        except Exception as e:
            return self._send(500, {"error": f"{type(e).__name__}: {str(e)[:300]}"})

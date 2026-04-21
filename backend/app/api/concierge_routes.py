"""
concierge_routes.py
────────────────────────────────────────────────────────────────────────────
AI Concierge Blueprint – The Grand Aurelia Hotel Management System

Exposes:
  POST /api/concierge-chat
      Request  JSON: {
          "question":   "What time is breakfast?",  ← required
          "session_id": "guest-uuid-abc123"          ← optional, for multi-turn
      }
      Response JSON: {
          "reply":      "Breakfast is served from …",
          "mode":       "openai" | "mock",
          "session_id": "guest-uuid-abc123"
      }

  DELETE /api/concierge-chat/session/<session_id>
      Clears conversation history for the given session.

Design notes:
  • The OpenAI HTTP call runs inside a ThreadPoolExecutor so eventlet's
    cooperative-threading model is never blocked.
  • A simple in-process rate limiter (10 req / 60 s per IP) prevents abuse
    without requiring an external cache like Redis.
  • All errors return structured JSON — never bare HTML tracebacks.
────────────────────────────────────────────────────────────────────────────
"""

import uuid
import time
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from flask import Blueprint, request, jsonify
from ..services.concierge_service import get_concierge, OpenAIConcierge, _conversation_store

logger = logging.getLogger(__name__)

concierge_bp = Blueprint("concierge_bp", __name__)

# ── Thread pool ───────────────────────────────────────────────────────────────
# Limits background threads; prevents resource exhaustion under heavy load.
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="concierge")

# Timeout (seconds) to wait for the AI response before returning HTTP 504
REQUEST_TIMEOUT = 20

# ── In-process rate limiter ───────────────────────────────────────────────────
# Tracks (timestamp list) per IP.  Not suitable for multi-process deployments;
# replace with Flask-Limiter + Redis for production scale.
_RATE_LIMIT        = 10      # max requests
_RATE_WINDOW       = 60      # per N seconds
_rate_log: dict    = defaultdict(list)


def _is_rate_limited(ip: str) -> tuple[bool, int]:
    """
    Returns (limited: bool, retry_after_seconds: int).
    Prunes stale timestamps on each call.
    """
    now = time.monotonic()
    window_start = now - _RATE_WINDOW
    timestamps = [t for t in _rate_log[ip] if t > window_start]
    _rate_log[ip] = timestamps

    if len(timestamps) >= _RATE_LIMIT:
        retry_after = int(_RATE_WINDOW - (now - timestamps[0])) + 1
        return True, retry_after

    _rate_log[ip].append(now)
    return False, 0


# ─────────────────────────────────────────────────────────────────────────────
#  POST /api/concierge-chat
# ─────────────────────────────────────────────────────────────────────────────

@concierge_bp.route("/api/concierge-chat", methods=["POST", "OPTIONS"])
def concierge_chat():
    """
    Handle a guest question and return an AI concierge reply.

    Request body (application/json):
        {
            "question":   "What time does the pool open?",
            "session_id": "optional-guest-uuid"
        }

    Responses:
        200  – { "reply": "...", "mode": "openai|mock", "session_id": "..." }
        400  – Missing or invalid 'question'
        429  – Rate limit exceeded
        504  – Backend timeout
        500  – Unexpected server error
    """
    # ── CORS preflight ────────────────────────────────────────────────────────
    if request.method == "OPTIONS":
        return _cors_preflight()

    # ── Rate limiting ─────────────────────────────────────────────────────────
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")
    limited, retry_after = _is_rate_limited(client_ip)
    if limited:
        logger.warning("[Concierge] Rate limit hit for IP: %s", client_ip)
        resp = jsonify({
            "error": "Too many requests. Please wait a moment before asking again.",
        })
        resp.headers["Retry-After"] = str(retry_after)
        return resp, 429

    # ── Input validation ──────────────────────────────────────────────────────
    body       = request.get_json(silent=True) or {}
    question   = (body.get("question") or "").strip()
    session_id = (body.get("session_id") or "").strip() or str(uuid.uuid4())

    if not question:
        return jsonify({
            "error":   "The 'question' field is required and must not be empty.",
            "example": {"question": "What time is breakfast?"},
        }), 400

    if len(question) > 500:
        return jsonify({
            "error": "Question is too long — please keep it under 500 characters.",
        }), 400

    logger.info("[Concierge] session=%s | question: %s", session_id, question[:120])

    # ── Dispatch to concierge (non-blocking via thread pool) ──────────────────
    concierge = get_concierge()
    mode      = "openai" if isinstance(concierge, OpenAIConcierge) else "mock"

    try:
        future = _executor.submit(concierge.chat, question, session_id)
        reply  = future.result(timeout=REQUEST_TIMEOUT)

    except FuturesTimeout:
        logger.error("[Concierge] Request timed out after %ds (session=%s)", REQUEST_TIMEOUT, session_id)
        return jsonify({
            "error": "The concierge is unavailable right now. "
                     "Please contact our front desk at ext. 0.",
        }), 504

    except Exception as exc:
        logger.exception("[Concierge] Unexpected error (session=%s): %s", session_id, exc)
        return jsonify({
            "error": "An unexpected error occurred. "
                     "Our team has been notified — please try again shortly.",
        }), 500

    # ── Return the reply ──────────────────────────────────────────────────────
    logger.info("[Concierge] Replied via %s (session=%s).", mode, session_id)
    return jsonify({
        "reply":      reply,
        "mode":       mode,
        "session_id": session_id,
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
#  DELETE /api/concierge-chat/session/<session_id>
# ─────────────────────────────────────────────────────────────────────────────

@concierge_bp.route("/api/concierge-chat/session/<session_id>", methods=["DELETE"])
def clear_session(session_id: str):
    """
    Clear conversation history for a given session.
    Useful when a guest explicitly starts a new conversation or logs out.
    """
    _conversation_store.clear(session_id)
    logger.info("[Concierge] Session cleared: %s", session_id)
    return jsonify({"message": f"Session '{session_id}' has been cleared."}), 200


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cors_preflight():
    """Return a 200 response for CORS OPTIONS pre-flight requests."""
    resp = jsonify({})
    resp.headers.update({
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    })
    return resp, 200

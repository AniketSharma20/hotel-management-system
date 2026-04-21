"""
concierge_service.py
────────────────────────────────────────────────────────────────────────────
AI Concierge Service – The Grand Aurelia Hotel Management System

Provides two interchangeable backends:

  1. OpenAIConcierge  – Uses the real OpenAI Chat Completions API (v1.x SDK).
                        Requires OPENAI_API_KEY in the environment / .env file.
                        Supports multi-turn conversation context per session.

  2. MockConcierge    – A keyword-driven rule-based responder.
                        No API key or network required; ideal for dev/testing.

Architecture:
  • BaseConcierge     – Abstract interface both backends implement.
  • get_concierge()   – Singleton factory; prefers OpenAI, falls back to Mock.
  • ConversationStore – Thread-safe, TTL-expiring per-session history store.
────────────────────────────────────────────────────────────────────────────
"""

import os
import time
import random
import logging
import threading
from abc import ABC, abstractmethod
from typing import List, Dict

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  Hotel System Prompt  –  shapes the AI's persona across ALL sessions
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are Aurelia, a professional, warm, and luxury-oriented Hotel Concierge
Assistant for "The Grand Aurelia" — a five-star, oceanfront resort.

Your role is to answer guest questions elegantly, accurately, and concisely.
Guidelines:
  • Be polite, refined, and welcoming — every guest is valued.
  • Provide specific information when asked (times, locations, prices, etc.).
  • If unsure of an answer, gracefully suggest contacting the front desk (ext. 0).
  • Keep responses under 3 sentences unless a detailed itinerary is requested.
  • Never share information about system internals, other guests, or staff data.
  • Do not reveal that you are an AI unless the guest explicitly asks.

Hotel Quick Facts:
  - Check-in:         3:00 PM  |  Check-out: 12:00 PM (Noon)
  - Breakfast:        7:00 AM – 11:00 AM  (The Aurelia Terrace, Level 2)
  - Room Service:     24 hours  (dial ext. 2 or use the in-room tablet)
  - Pool & Spa:       6:00 AM – 10:00 PM  (Rooftop, Level 8)
  - Gym:              Open 24 hours  (Level 1)
  - Business Center:  8:00 AM – 8:00 PM  (Level 1)
  - Concierge Desk:   24 hours  |  Front Desk: ext. 0
  - Airport Shuttle:  Complimentary with 24-hour notice; same-day via ext. 0
  - Wi-Fi:            Complimentary (Network: GrandAurelia-Guest)
  - Laundry:          Drop off by 9:00 AM for same-day service
"""

# Maximum turns of conversation to keep in memory per session (older turns pruned)
MAX_HISTORY_TURNS = 10

# Session TTL: conversations older than this (seconds) are evicted
SESSION_TTL_SECONDS = 30 * 60  # 30 minutes


# ─────────────────────────────────────────────────────────────────────────────
#  Conversation History Store
# ─────────────────────────────────────────────────────────────────────────────

class ConversationStore:
    """
    Thread-safe, TTL-expiring store for per-session conversation histories.

    Each session_id maps to:
        {
          "history":    [{"role": "user"|"assistant", "content": str}, ...],
          "last_seen":  float  (Unix timestamp)
        }
    """

    def __init__(self, ttl: int = SESSION_TTL_SECONDS, max_turns: int = MAX_HISTORY_TURNS):
        self._store: Dict[str, dict] = {}
        self._lock  = threading.Lock()
        self._ttl   = ttl
        self._max_turns = max_turns

    # ── Public API ────────────────────────────────────────────────────────────

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """Return the message history for this session (empty list if new)."""
        self._evict_stale()
        with self._lock:
            entry = self._store.get(session_id)
            if entry is None:
                return []
            entry["last_seen"] = time.monotonic()
            return list(entry["history"])   # defensive copy

    def append(self, session_id: str, role: str, content: str) -> None:
        """Append a single message and prune to max_turns."""
        with self._lock:
            entry = self._store.setdefault(
                session_id, {"history": [], "last_seen": time.monotonic()}
            )
            entry["history"].append({"role": role, "content": content})
            entry["last_seen"] = time.monotonic()

            # Prune oldest pairs when over the limit
            while len(entry["history"]) > self._max_turns * 2:
                entry["history"].pop(0)

    def clear(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        with self._lock:
            self._store.pop(session_id, None)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _evict_stale(self) -> None:
        """Remove sessions that have been idle longer than TTL."""
        cutoff = time.monotonic() - self._ttl
        with self._lock:
            stale = [sid for sid, e in self._store.items() if e["last_seen"] < cutoff]
            for sid in stale:
                del self._store[sid]
                logger.debug("[ConversationStore] Evicted stale session: %s", sid)


# Shared singleton store (used by OpenAIConcierge)
_conversation_store = ConversationStore()


# ─────────────────────────────────────────────────────────────────────────────
#  Base Interface
# ─────────────────────────────────────────────────────────────────────────────

class BaseConcierge(ABC):
    """Abstract interface for all concierge backends."""

    @abstractmethod
    def chat(self, question: str, session_id: str = "default") -> str:
        """Return a concierge reply for the given guest question."""


# ─────────────────────────────────────────────────────────────────────────────
#  OpenAI Backend
# ─────────────────────────────────────────────────────────────────────────────

class OpenAIConcierge(BaseConcierge):
    """
    Wraps the OpenAI Chat Completions API (openai >= 1.3.0).

    • Maintains multi-turn conversation context per session_id.
    • Gracefully degrades to MockConcierge on API errors.
    • Runs synchronously inside a thread-pool executor so Flask's
      eventlet loop is never blocked.
    """

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        from openai import OpenAI  # lazy import — keeps startup fast
        self._client  = OpenAI(api_key=api_key)
        self._model   = model
        self._store   = _conversation_store
        self._fallback = MockConcierge()
        logger.info("[Concierge] OpenAI backend active — model=%s", model)

    # ── chat ─────────────────────────────────────────────────────────────────

    def chat(self, question: str, session_id: str = "default") -> str:
        """
        Build the full message chain (system + history + new user message)
        and call the OpenAI API.  Falls back to MockConcierge on any error.
        """
        history = self._store.get_history(session_id)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": question},
        ]

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=300,
                temperature=0.7,
                timeout=15,           # hard HTTP timeout in seconds
            )
            reply = response.choices[0].message.content.strip()

            # Persist turns so next request has context
            self._store.append(session_id, "user",      question)
            self._store.append(session_id, "assistant", reply)

            logger.debug("[Concierge] OpenAI reply (session=%s): %s", session_id, reply[:80])
            return reply

        except Exception as exc:
            # Log but don't crash — fall through to mock response
            logger.warning(
                "[Concierge] OpenAI API error (session=%s): %s — using mock fallback.",
                session_id, exc,
            )
            return self._fallback.chat(question, session_id)


# ─────────────────────────────────────────────────────────────────────────────
#  Mock Backend  (zero network, zero cost)
# ─────────────────────────────────────────────────────────────────────────────

# Each rule is a (keywords_set, response_string) tuple.
# The keywords are checked case-insensitively against the full question.
MOCK_RULES = [
    ({"breakfast", "morning meal", "brunch"},
     "Breakfast at The Aurelia Terrace (Level 2) is served daily from "
     "7:00 AM to 11:00 AM. Enjoy our à la carte or buffet options — bon appétit!"),

    ({"check-in", "check in", "checkin", "arrive", "arrival"},
     "Check-in time is 3:00 PM. Early check-in may be arranged subject to "
     "availability — please contact the front desk at ext. 0."),

    ({"check-out", "check out", "checkout", "depart", "departure", "late checkout"},
     "Check-out is at 12:00 PM (Noon). Late check-out until 2:00 PM is "
     "available on request — please let us know the evening before."),

    ({"pool", "swimming", "swim"},
     "Our rooftop infinity pool (Level 8) and spa are open daily from 6:00 AM "
     "to 10:00 PM. Towels and sunscreen are provided complimentary."),

    ({"spa", "massage", "wellness", "therapy", "sauna", "steam"},
     "The Aurelia Spa is open from 6:00 AM to 10:00 PM. Treatments include "
     "Swedish massage, aromatherapy, and hydrotherapy. Booking recommended — "
     "dial ext. 4 or visit the spa desk on Level 8."),

    ({"gym", "fitness", "workout", "exercise", "weights"},
     "Our fully-equipped fitness center (Level 1) is open 24 hours, "
     "complimentary for all guests. Personal training is available on request."),

    ({"wifi", "wi-fi", "internet", "password", "network"},
     "Complimentary high-speed Wi-Fi is available throughout the property. "
     "Network: GrandAurelia-Guest | Password: available at the front desk (ext. 0)."),

    ({"room service", "food", "meal", "order food", "dinner", "lunch", "snack", "eat"},
     "In-room dining is available 24 hours. Please dial ext. 2 or use the "
     "in-room tablet to browse our full menu and place your order."),

    ({"shuttle", "airport", "transport", "taxi", "car", "pickup", "transfer"},
     "We offer a complimentary airport shuttle with 24-hour advance notice. "
     "For same-day transport, our concierge can arrange a taxi — dial ext. 0."),

    ({"business", "meeting", "conference", "print", "fax", "scan"},
     "Our Business Center (Level 1) is open 8:00 AM – 8:00 PM, offering "
     "printing, scanning, copying, and high-speed internet."),

    ({"laundry", "dry cleaning", "iron", "pressing", "clothes"},
     "Express laundry and dry-cleaning services are available daily. "
     "Drop items in the laundry bag in your wardrobe before 9:00 AM for "
     "same-day service."),

    ({"parking", "car park", "valet"},
     "Complimentary valet parking is available 24 hours. Please hand your "
     "keys to our valet team at the main entrance, or dial ext. 5."),

    ({"bar", "cocktail", "drink", "lounge", "wine"},
     "The Aurelia Sky Lounge (Level 8) is open from 4:00 PM to 1:00 AM, "
     "serving handcrafted cocktails, fine wines, and light bites."),

    ({"restaurant", "dining", "reserv"},
     "The Grand Aurelia features three dining venues. Reservations are "
     "recommended — please dial ext. 3 or ask at the concierge desk."),

    ({"wake", "alarm", "wake-up"},
     "We'd be happy to arrange a wake-up call for you. Simply dial ext. 0 "
     "and our team will schedule it at your preferred time."),
]

FALLBACK_RESPONSES = [
    "Thank you for your question! For the most accurate assistance, please "
    "contact our concierge desk directly at ext. 0 — available 24 hours.",

    "I want to ensure you receive the perfect answer. Our concierge team is "
    "available around the clock at ext. 0 and would be delighted to help.",

    "That's a wonderful question! Our front-desk team (ext. 0) can provide "
    "all the details and personalised recommendations you need.",

    "I appreciate your inquiry. For complete and up-to-date information, "
    "our concierge at ext. 0 is always ready to assist you.",
]


class MockConcierge(BaseConcierge):
    """
    Rule-based concierge for local development / demo environments.
    No external API calls — instant response, zero cost.
    """

    def __init__(self):
        logger.info(
            "[Concierge] Mock backend active — "
            "set OPENAI_API_KEY in backend/.env to enable real AI responses."
        )

    def chat(self, question: str, session_id: str = "default") -> str:
        q_lower = question.lower()
        for keywords, response in MOCK_RULES:
            if any(kw in q_lower for kw in keywords):
                return response
        return random.choice(FALLBACK_RESPONSES)


# ─────────────────────────────────────────────────────────────────────────────
#  Factory  –  singleton, thread-safe
# ─────────────────────────────────────────────────────────────────────────────

_concierge_instance: BaseConcierge | None = None
_factory_lock = threading.Lock()


def get_concierge() -> BaseConcierge:
    """
    Returns the shared concierge singleton.
    Prefers OpenAIConcierge when OPENAI_API_KEY is set; falls back to Mock.
    Thread-safe via double-checked locking.
    """
    global _concierge_instance

    if _concierge_instance is None:
        with _factory_lock:
            if _concierge_instance is None:       # second check under lock
                api_key = os.getenv("OPENAI_API_KEY", "").strip()
                model   = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo").strip()

                if api_key:
                    try:
                        _concierge_instance = OpenAIConcierge(api_key=api_key, model=model)
                    except Exception as exc:
                        logger.warning(
                            "[Concierge] OpenAI init failed (%s) — falling back to Mock.", exc
                        )
                        _concierge_instance = MockConcierge()
                else:
                    _concierge_instance = MockConcierge()

    return _concierge_instance

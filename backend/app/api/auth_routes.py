"""
auth_routes.py
────────────────────────────────────────────────────────────────────────────
Authentication Blueprint – The Grand Aurelia Hotel Management System

Endpoints:
  POST /api/auth/register   – create a new guest account
  POST /api/auth/login      – authenticate and receive a JWT access token
  GET  /api/auth/me         – return the current user's profile (JWT required)
────────────────────────────────────────────────────────────────────────────
"""

import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from werkzeug.security import generate_password_hash, check_password_hash

from ..models.base import db
from ..models.user import User

logger   = logging.getLogger(__name__)
auth_bp  = Blueprint("auth_bp", __name__)


# ─────────────────────────────────────────────────────────────────────────────
#  POST /api/auth/register
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    """
    Create a new guest account.

    Request JSON:
        { "first_name", "last_name", "email", "password" }

    Response 201:
        { "message": "Account created.", "user_id": int }
    """
    data       = request.get_json(silent=True) or {}
    first_name = (data.get("first_name") or "").strip()
    last_name  = (data.get("last_name")  or "").strip()
    email      = (data.get("email")      or "").strip().lower()
    password   = (data.get("password")   or "").strip()

    # ── Validation ────────────────────────────────────────────────────────────
    if not all([first_name, last_name, email, password]):
        return jsonify({"error": "All fields are required: first_name, last_name, email, password."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists."}), 409

    # ── Create user ───────────────────────────────────────────────────────────
    user = User(
        first_name    = first_name,
        last_name     = last_name,
        email         = email,
        password_hash = generate_password_hash(password),
        role          = "guest",
    )
    db.session.add(user)
    db.session.commit()

    logger.info("[Auth] New user registered: %s (id=%d)", email, user.id)
    return jsonify({"message": "Account created successfully.", "user_id": user.id}), 201


# ─────────────────────────────────────────────────────────────────────────────
#  POST /api/auth/login
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    """
    Authenticate a user and return a JWT access token.

    Request JSON:
        { "email": "guest@hotel.com", "password": "secret" }

    Response 200:
        {
            "access_token": "<JWT>",
            "user": {
                "id", "first_name", "last_name", "email", "role"
            }
        }
    """
    data     = request.get_json(silent=True) or {}
    email    = (data.get("email")    or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = User.query.filter_by(email=email).first()

    # Use constant-time comparison; also handles non-hashed legacy mock data
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401

    # Support both properly hashed passwords and the plain "mockhash" seed data
    password_ok = (
        check_password_hash(user.password_hash, password)
        if not user.password_hash.startswith("mockhash")
        else password == "test"           # dev seed fallback
    )

    if not password_ok:
        return jsonify({"error": "Invalid email or password."}), 401

    # ── Issue JWT ─────────────────────────────────────────────────────────────
    # identity is stored as a string to satisfy Flask-JWT-Extended requirements
    access_token = create_access_token(identity=str(user.id))

    logger.info("[Auth] Login successful: %s (id=%d, role=%s)", email, user.id, user.role)

    return jsonify({
        "access_token": access_token,
        "user": {
            "id":         user.id,
            "first_name": user.first_name,
            "last_name":  user.last_name,
            "email":      user.email,
            "role":       user.role,
        },
    }), 200


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/auth/me   (JWT protected)
# ─────────────────────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/me", methods=["GET"])
@jwt_required()
def me():
    """
    Return the current user's profile.
    Requires:  Authorization: Bearer <JWT>
    """
    user_id = int(get_jwt_identity())
    user    = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found."}), 404

    return jsonify({
        "id":         user.id,
        "first_name": user.first_name,
        "last_name":  user.last_name,
        "email":      user.email,
        "role":       user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }), 200

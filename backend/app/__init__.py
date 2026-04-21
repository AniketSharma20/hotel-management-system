"""
Application Factory  –  Flask-SocketIO, SOS, AI Concierge, Auth, Rooms.
"""
import os
from dotenv import load_dotenv
load_dotenv()          # load .env before anything reads os.getenv()

from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from .models.base import db
from .api.booking_routes import booking_bp
from .api.sos_routes import sos_bp, register_sos_socket_events
from .api.concierge_routes import concierge_bp
from .api.auth_routes import auth_bp
from .api.room_routes import rooms_bp

# ── Shared extensions (module-level so blueprints can import them) ───────────
socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')
jwt      = JWTManager()


def create_app(config_object=None):
    app = Flask(__name__)

    # ── Default config for local dev ──────────────────────────────────────────
    app.config['SQLALCHEMY_DATABASE_URI']        = 'sqlite:///hotel.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY']                     = os.getenv('SECRET_KEY', 'aurelia-dev-secret-change-in-prod')
    app.config['JWT_SECRET_KEY']                 = os.getenv('SECRET_KEY', 'aurelia-jwt-secret-change-in-prod')
    app.config['JWT_ACCESS_TOKEN_EXPIRES']       = 60 * 60 * 24   # 24 hours

    if config_object:
        app.config.from_object(config_object)

    # ── Initialize extensions ─────────────────────────────────────────────────
    CORS(app)
    db.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app)

    # ── Register HTTP Blueprints ───────────────────────────────────────────────
    app.register_blueprint(auth_bp)
    app.register_blueprint(rooms_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(sos_bp)
    app.register_blueprint(concierge_bp)

    # ── Register real-time SocketIO event handlers ────────────────────────────
    register_sos_socket_events(socketio)

    return app

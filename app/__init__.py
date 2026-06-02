import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template

from app.api import register_api_routes


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config.update(_backend_config_from_env())

    if test_config:
        app.config.update(test_config)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/bookings")
    def bookings_page():
        return render_template("bookings.html")

    @app.get("/visualization")
    def visualization_page():
        return render_template("visualization.html")

    @app.get("/prediction")
    def prediction_page():
        return render_template("prediction.html")

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "hotel-booking-dashboard"})

    register_api_routes(app)

    return app


def _backend_config_from_env():
    return {
        "BOOKING_DATA_SOURCE": os.getenv("BOOKING_DATA_SOURCE", "csv"),
        "BOOKING_DATA_CSV": os.getenv("BOOKING_DATA_CSV"),
        "MYSQL_HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "MYSQL_PORT": _env_int("MYSQL_PORT", 3306),
        "MYSQL_USER": os.getenv("MYSQL_USER", "root"),
        "MYSQL_PASSWORD": os.getenv("MYSQL_PASSWORD", ""),
        "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE", "hotel_booking_analysis"),
        "REDIS_ENABLED": _env_bool("REDIS_ENABLED", False),
        "REDIS_HOST": os.getenv("REDIS_HOST", "127.0.0.1"),
        "REDIS_PORT": _env_int("REDIS_PORT", 6379),
        "REDIS_DB": _env_int("REDIS_DB", 0),
        "REDIS_PASSWORD": os.getenv("REDIS_PASSWORD"),
        "PREDICTION_MODEL_DIR": os.getenv("PREDICTION_MODEL_DIR"),
        "PREDICTION_MODEL_PATH": os.getenv("PREDICTION_MODEL_PATH"),
        "PREDICTION_FEATURE_COLUMNS_PATH": os.getenv("PREDICTION_FEATURE_COLUMNS_PATH"),
        "PREDICTION_METRICS_PATH": os.getenv("PREDICTION_METRICS_PATH"),
    }


def _env_int(name, default):
    value = os.getenv(name)
    return int(value) if value not in (None, "") else default


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return value.lower() in {"1", "true", "yes", "on"}

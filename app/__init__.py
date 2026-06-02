from flask import Flask, jsonify, render_template

from app.api import register_api_routes


def create_app(test_config=None):
    app = Flask(__name__)

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

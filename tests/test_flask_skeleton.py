from pathlib import Path

from app import create_app


BASE_DIR = Path(__file__).resolve().parents[1]


def test_app_factory_configures_testing_client():
    app = create_app({"TESTING": True})

    assert app.config["TESTING"] is True
    assert app.name == "app"


def test_app_factory_reads_backend_environment_switches(monkeypatch):
    monkeypatch.setenv("BOOKING_DATA_SOURCE", "mysql")
    monkeypatch.setenv("MYSQL_HOST", "db.local")
    monkeypatch.setenv("MYSQL_PORT", "3307")
    monkeypatch.setenv("MYSQL_USER", "hotel")
    monkeypatch.setenv("MYSQL_PASSWORD", "secret")
    monkeypatch.setenv("MYSQL_DATABASE", "hotel_booking_analysis")
    monkeypatch.setenv("REDIS_ENABLED", "true")
    monkeypatch.setenv("REDIS_HOST", "redis.local")
    monkeypatch.setenv("REDIS_PORT", "6380")
    monkeypatch.setenv("REDIS_DB", "2")
    monkeypatch.setenv("PREDICTION_MODEL_DIR", "custom-models")

    app = create_app({"TESTING": True})

    assert app.config["BOOKING_DATA_SOURCE"] == "mysql"
    assert app.config["MYSQL_HOST"] == "db.local"
    assert app.config["MYSQL_PORT"] == 3307
    assert app.config["MYSQL_USER"] == "hotel"
    assert app.config["MYSQL_PASSWORD"] == "secret"
    assert app.config["MYSQL_DATABASE"] == "hotel_booking_analysis"
    assert app.config["REDIS_ENABLED"] is True
    assert app.config["REDIS_HOST"] == "redis.local"
    assert app.config["REDIS_PORT"] == 6380
    assert app.config["REDIS_DB"] == 2
    assert app.config["PREDICTION_MODEL_DIR"] == "custom-models"


def test_homepage_renders_course_project_navigation():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "酒店预订数据可视化分析与预测系统" in html
    assert "首页" in html
    assert "数据查询" in html
    assert "数据可视化" in html
    assert "评估与预测" in html


def test_main_frontend_pages_render_static_mock_workspaces():
    app = create_app({"TESTING": True})
    client = app.test_client()

    expected_pages = {
        "/": ["当前日期风险态势", "latest_event_time", "static/js/dashboard.js"],
        "/bookings": ["预订数据查询与维护", "booking_id", "static/js/bookings.js"],
        "/visualization": ["取消率预测可视化分析", "country_code", "static/js/visualization.js"],
        "/prediction": ["模型评估与订单预测", "cancel_probability", "static/js/prediction.js"],
    }

    for path, expected_texts in expected_pages.items():
        response = client.get(path)

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        for expected_text in expected_texts:
            assert expected_text in html


def test_frontend_static_assets_exist():
    expected_files = [
        "app/templates/base.html",
        "app/templates/bookings.html",
        "app/templates/visualization.html",
        "app/templates/prediction.html",
        "app/static/js/charts.js",
        "app/static/js/dashboard.js",
        "app/static/js/bookings.js",
        "app/static/js/visualization.js",
        "app/static/js/prediction.js",
    ]

    for relative_path in expected_files:
        assert (BASE_DIR / relative_path).exists(), f"Missing {relative_path}"


def test_frontend_pages_load_echarts_renderer_for_pyecharts_options():
    app = create_app({"TESTING": True})
    client = app.test_client()

    for path in ("/", "/visualization", "/prediction"):
        response = client.get(path)
        html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "echarts.min.js" in html
        assert "static/js/charts.js" in html


def test_visualization_page_no_longer_uses_static_mock_map_container():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/visualization")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "mock-map" not in html


def test_health_endpoint_reports_application_status():
    app = create_app({"TESTING": True})
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "service": "hotel-booking-dashboard"}


def test_github_collaboration_baseline_files_exist():
    expected_files = [
        "README.md",
        ".gitignore",
        "requirements.txt",
        "run.py",
    ]

    for relative_path in expected_files:
        assert (BASE_DIR / relative_path).exists(), f"Missing {relative_path}"

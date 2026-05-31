from pathlib import Path

from app import create_app


BASE_DIR = Path(__file__).resolve().parents[1]


def test_app_factory_configures_testing_client():
    app = create_app({"TESTING": True})

    assert app.config["TESTING"] is True
    assert app.name == "app"


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

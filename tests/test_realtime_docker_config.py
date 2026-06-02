from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_realtime_docker_compose_declares_required_services():
    compose = PROJECT_ROOT / "realtime" / "docker-compose.yml"

    content = compose.read_text(encoding="utf-8")

    for service in ("redis", "zookeeper", "kafka", "storm-nimbus", "storm-supervisor", "storm-ui", "flume"):
        assert f"  {service}:" in content
    assert "hotel-booking-realtime" in content
    assert "9092:9092" in content
    assert "8081:8080" in content


def test_flume_and_storm_configs_point_to_kafka_and_zookeeper():
    flume_conf = (PROJECT_ROOT / "realtime" / "flume" / "flume.conf").read_text(encoding="utf-8")
    storm_conf = (PROJECT_ROOT / "realtime" / "storm" / "storm.yaml").read_text(encoding="utf-8")

    assert "booking_events.log" in flume_conf
    assert "kafka.bootstrap.servers = kafka:9092" in flume_conf
    assert "kafka.topic = hotel-booking-events" in flume_conf
    assert 'nimbus.seeds: ["storm-nimbus"]' in storm_conf
    assert "- zookeeper" in storm_conf

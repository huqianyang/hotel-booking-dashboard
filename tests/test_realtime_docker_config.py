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


def test_java_storm_topology_project_contains_required_bolts_and_dependencies():
    topology_root = PROJECT_ROOT / "realtime" / "storm-topology"
    pom = (topology_root / "pom.xml").read_text(encoding="utf-8")
    topology = (topology_root / "src" / "main" / "java" / "com" / "hotel" / "storm" / "HotelBookingTopology.java").read_text(
        encoding="utf-8"
    )

    assert "<artifactId>storm-client</artifactId>" in pom
    assert "<artifactId>storm-kafka-client</artifactId>" in pom
    assert "<artifactId>jedis</artifactId>" in pom
    assert "<artifactId>mysql-connector-j</artifactId>" in pom
    assert "KafkaSpout" in topology
    assert "EventParseBolt" in topology
    assert "PredictRequestBolt" in topology
    assert "MySQLWriteBolt" in topology
    assert "RedisMetricBolt" in topology

    for bolt_file, required in {
        "EventParseBolt.java": ["booking_id", "business_time"],
        "PredictRequestBolt.java": ["/api/prediction/single", "HttpURLConnection"],
        "MySQLWriteBolt.java": ["prediction_results", "realtime_metrics", "source"],
        "RedisMetricBolt.java": [
            "realtime:summary",
            "realtime:trend",
            "realtime:recent_predictions",
            "realtime:country_risk",
            "realtime:channel_risk",
            "realtime:link_status",
        ],
    }.items():
        content = (topology_root / "src" / "main" / "java" / "com" / "hotel" / "storm" / "bolt" / bolt_file).read_text(
            encoding="utf-8"
        )
        for text in required:
            assert text in content


def test_realtime_compose_mounts_topology_and_docs_include_submit_and_verification_steps():
    compose = (PROJECT_ROOT / "realtime" / "docker-compose.yml").read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "realtime" / "README.md").read_text(encoding="utf-8")
    submit_script = PROJECT_ROOT / "scripts" / "submit_storm_topology.ps1"
    verify_script = PROJECT_ROOT / "scripts" / "verify_realtime_pipeline.py"

    assert "./storm-topology/target:/topology" in compose
    assert submit_script.exists()
    assert "mvn -f realtime\\storm-topology\\pom.xml package" in submit_script.read_text(encoding="utf-8")
    assert "storm jar /topology/hotel-booking-storm-topology.jar" in submit_script.read_text(encoding="utf-8")
    assert verify_script.exists()
    assert "prediction_results" in verify_script.read_text(encoding="utf-8")
    assert "realtime:summary" in verify_script.read_text(encoding="utf-8")
    assert "Submit Storm Topology" in readme
    assert "Verify End-to-End Outputs" in readme


def test_storm_topology_stays_java_8_compatible():
    topology_root = PROJECT_ROOT / "realtime" / "storm-topology"
    pom = (topology_root / "pom.xml").read_text(encoding="utf-8")
    java_sources = "\n".join(path.read_text(encoding="utf-8") for path in topology_root.glob("src/main/java/**/*.java"))

    assert "<maven.compiler.source>1.8</maven.compiler.source>" in pom
    assert "<maven.compiler.target>1.8</maven.compiler.target>" in pom
    for java_11_plus_api in ("java.net.http", "Map.of", "List.of", ".toList(", ".isBlank()"):
        assert java_11_plus_api not in java_sources

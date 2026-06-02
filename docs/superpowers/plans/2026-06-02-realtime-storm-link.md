# Realtime Storm Link Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the realtime big-data link so booking events flow through Flume/Kafka/Java Storm and Storm writes prediction and metric outputs to MySQL and Redis.

**Architecture:** Keep Flask as the model inference service. Add a Maven Java Storm topology under `realtime/storm-topology`, submit it into the existing Docker Storm cluster, and expose a verification script that checks Kafka, Storm, Redis, and MySQL outputs.

**Tech Stack:** Java 17, Apache Storm 2.6.4, Kafka client, Jedis, MySQL Connector/J, Flask API, Redis, Docker Compose.

---

### Task 1: Lock Realtime Topology Structure

**Files:**
- Modify: `tests/test_realtime_docker_config.py`
- Create: `realtime/storm-topology/pom.xml`
- Create: `realtime/storm-topology/src/main/java/com/hotel/storm/HotelBookingTopology.java`
- Create: `realtime/storm-topology/src/main/java/com/hotel/storm/bolt/EventParseBolt.java`
- Create: `realtime/storm-topology/src/main/java/com/hotel/storm/bolt/PredictRequestBolt.java`
- Create: `realtime/storm-topology/src/main/java/com/hotel/storm/bolt/MySQLWriteBolt.java`
- Create: `realtime/storm-topology/src/main/java/com/hotel/storm/bolt/RedisMetricBolt.java`

- [ ] Write tests requiring Maven topology files and Storm submit wiring.
- [ ] Run tests and verify they fail because files are missing.
- [ ] Add minimal Java topology and Docker Compose volume.
- [ ] Run tests and verify they pass.

### Task 2: Add Runtime Scripts and Docs

**Files:**
- Create: `scripts/submit_storm_topology.ps1`
- Create: `scripts/verify_realtime_pipeline.py`
- Modify: `realtime/README.md`

- [ ] Write tests requiring submit and verification commands.
- [ ] Run tests and verify they fail because scripts/docs are incomplete.
- [ ] Add scripts and docs.
- [ ] Run tests and full suite.

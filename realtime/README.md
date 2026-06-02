# Realtime Pipeline

This folder contains the course demo pipeline:

```text
booking_events.log -> Flume -> Kafka -> Java Storm -> Flask prediction API -> MySQL + Redis -> Flask realtime API
```

The Java Storm topology consumes `hotel-booking-events`, calls Flask `/api/prediction/single`, writes `prediction_results` and `realtime_metrics`, and refreshes these Redis keys:

- `realtime:summary`
- `realtime:trend`
- `realtime:recent_predictions`
- `realtime:country_risk`
- `realtime:channel_risk`
- `realtime:link_status`

## Start Services

```powershell
docker compose -f realtime\docker-compose.yml up -d
```

Storm UI:

```text
http://localhost:8081
```

## Start Flask

Use MySQL as the booking source so Storm prediction requests can resolve `booking_id` to full model features:

```powershell
$env:BOOKING_DATA_SOURCE="mysql"
$env:REDIS_ENABLED="true"
python run.py
```

## Submit Storm Topology

Build the Maven project and submit it into the running Storm nimbus container:

```powershell
.\scripts\submit_storm_topology.ps1 `
  -FlaskPredictUrl "http://host.docker.internal:5000/api/prediction/single" `
  -MysqlJdbcUrl "jdbc:mysql://host.docker.internal:3306/hotel_booking_analysis?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai" `
  -MysqlUser "root" `
  -MysqlPassword ""
```

## Generate Events

`generate_realtime_events.py` uses the fixed split boundary and only emits rows with `arrival_date >= 2017-01-13`.

```powershell
python scripts\generate_realtime_events.py --count 100 --start 0
```

## Verify Kafka

```powershell
docker exec hotel-kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic hotel-booking-events --from-beginning --max-messages 1 --timeout-ms 20000
```

## Verify End-to-End Outputs

After Storm has consumed events, verify MySQL and Redis outputs:

```powershell
python scripts\verify_realtime_pipeline.py
```

Expected nonzero outputs:

- MySQL `prediction_results` has rows where `source = 'storm'`
- MySQL `realtime_metrics` has rows
- Redis `realtime:summary` has `processed_count > 0`

## Stop Services

```powershell
docker compose -f realtime\docker-compose.yml down
```

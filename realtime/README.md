# Realtime Pipeline

This folder contains the local Docker pipeline used for the course demo:

```text
booking_events.log -> Flume -> Kafka -> Storm
Redis stores realtime dashboard snapshots.
```

## Start Services

```powershell
docker compose -f realtime\docker-compose.yml up -d
```

Storm UI:

```text
http://localhost:8081
```

## Seed Redis

```powershell
python scripts\seed_redis.py --host 127.0.0.1 --port 6379
```

## Generate Events

```powershell
python scripts\generate_realtime_events.py --count 10
```

## Verify Kafka

```powershell
docker exec hotel-kafka kafka-console-consumer --bootstrap-server kafka:9092 --topic hotel-booking-events --from-beginning --max-messages 1 --timeout-ms 20000
```

## Stop Services

```powershell
docker compose -f realtime\docker-compose.yml down
```

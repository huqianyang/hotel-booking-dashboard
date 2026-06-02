import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.redis_client import RedisClient
from app.services.booking_repository import BookingRepository
from app.services.realtime_service import RealtimeService


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Seed Redis realtime keys from cleaned hotel booking data.")
    parser.add_argument("--csv", type=Path, default=PROJECT_ROOT / "数据" / "cleaned_hotel_bookings.csv")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6379)
    parser.add_argument("--db", type=int, default=0)
    parser.add_argument("--password")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    redis_client = RedisClient(host=args.host, port=args.port, db=args.db, password=args.password)
    service = RealtimeService(BookingRepository(args.csv))
    summary = service.summary()
    summary["service_status"]["redis"] = "running"

    payloads = {
        "realtime:summary": summary,
        "realtime:trend": service.trend(),
        "realtime:recent_predictions": service.recent_predictions(),
        "realtime:service_status": summary["service_status"],
    }
    for key, value in payloads.items():
        redis_client.set_json(key, value)

    print(f"Seeded {len(payloads)} Redis realtime keys at {args.host}:{args.port}/{args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

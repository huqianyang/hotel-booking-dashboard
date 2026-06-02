import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.redis_client import RedisClient
from app.services.realtime_service import WAITING_MESSAGE


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Seed empty Redis realtime keys without fabricating live data.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6379)
    parser.add_argument("--db", type=int, default=0)
    parser.add_argument("--password")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    redis_client = RedisClient(host=args.host, port=args.port, db=args.db, password=args.password)
    payloads = {
        "realtime:summary": {
            "processed_count": 0,
            "high_risk_count": 0,
            "average_cancel_probability": 0.0,
            "updated_at": None,
            "status": "waiting",
            "message": WAITING_MESSAGE,
        },
        "realtime:trend": {
            "day": [],
            "week": [],
            "month": [],
            "status": "waiting",
            "message": WAITING_MESSAGE,
        },
        "realtime:recent_predictions": {"items": [], "status": "waiting", "message": WAITING_MESSAGE},
        "realtime:country_risk": {"items": [], "status": "waiting", "message": WAITING_MESSAGE},
        "realtime:channel_risk": {"items": [], "status": "waiting", "message": WAITING_MESSAGE},
        "realtime:link_status": {
            "redis": "running",
            "flume": "pending",
            "kafka": "pending",
            "storm": "pending",
        },
    }
    for key, value in payloads.items():
        redis_client.set_json(key, value)

    print(f"Seeded {len(payloads)} empty Redis realtime keys at {args.host}:{args.port}/{args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

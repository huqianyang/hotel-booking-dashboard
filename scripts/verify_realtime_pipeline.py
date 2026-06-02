import argparse
import json
import os
import subprocess
import sys

import pymysql
import redis


REQUIRED_REDIS_KEYS = [
    "realtime:summary",
    "realtime:trend",
    "realtime:recent_predictions",
    "realtime:country_risk",
    "realtime:channel_risk",
    "realtime:link_status",
]


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Verify Flume -> Kafka -> Storm -> Flask -> MySQL/Redis outputs.")
    parser.add_argument("--mysql-host", default=os.getenv("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--mysql-port", type=int, default=int(os.getenv("MYSQL_PORT", "3306")))
    parser.add_argument("--mysql-user", default=os.getenv("MYSQL_USER", "root"))
    parser.add_argument("--mysql-password", default=os.getenv("MYSQL_PASSWORD", ""))
    parser.add_argument("--mysql-database", default=os.getenv("MYSQL_DATABASE", "hotel_booking_analysis"))
    parser.add_argument("--redis-host", default=os.getenv("REDIS_HOST", "127.0.0.1"))
    parser.add_argument("--redis-port", type=int, default=int(os.getenv("REDIS_PORT", "6379")))
    parser.add_argument("--redis-db", type=int, default=int(os.getenv("REDIS_DB", "0")))
    parser.add_argument("--skip-kafka", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    checks = []
    if not args.skip_kafka:
        checks.append(check_docker_container("hotel-kafka"))
        checks.append(check_docker_container("hotel-storm-nimbus"))
        checks.append(check_docker_container("hotel-storm-supervisor"))
    checks.append(check_mysql(args))
    checks.append(check_redis(args))

    failed = [check for check in checks if not check["ok"]]
    print(json.dumps({"checks": checks, "failed": failed}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


def check_docker_container(container_name):
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "name": f"container:{container_name}",
        "ok": result.returncode == 0 and result.stdout.strip() == "true",
        "details": result.stdout.strip() or result.stderr.strip(),
    }


def check_mysql(args):
    try:
        connection = pymysql.connect(
            host=args.mysql_host,
            port=args.mysql_port,
            user=args.mysql_user,
            password=args.mysql_password,
            database=args.mysql_database,
            cursorclass=pymysql.cursors.DictCursor,
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM prediction_results WHERE source = 'storm'")
            prediction_count = cursor.fetchone()["total"]
            cursor.execute("SELECT COUNT(*) AS total FROM realtime_metrics")
            metric_count = cursor.fetchone()["total"]
        connection.close()
        return {
            "name": "mysql:prediction_results+realtime_metrics",
            "ok": prediction_count > 0 and metric_count > 0,
            "details": {"prediction_results": prediction_count, "realtime_metrics": metric_count},
        }
    except Exception as error:
        return {"name": "mysql:prediction_results+realtime_metrics", "ok": False, "details": str(error)}


def check_redis(args):
    try:
        client = redis.Redis(host=args.redis_host, port=args.redis_port, db=args.redis_db, decode_responses=True)
        client.ping()
        values = {key: client.get(key) for key in REQUIRED_REDIS_KEYS}
        missing = [key for key, value in values.items() if not value]
        summary = json.loads(values["realtime:summary"]) if values.get("realtime:summary") else {}
        processed_count = int(summary.get("processed_count", 0))
        return {
            "name": "redis:realtime_keys",
            "ok": not missing and processed_count > 0,
            "details": {"missing": missing, "processed_count": processed_count},
        }
    except Exception as error:
        return {"name": "redis:realtime_keys", "ok": False, "details": str(error)}


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

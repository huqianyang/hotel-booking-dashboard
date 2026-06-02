import json

import redis


class RedisClient:
    def __init__(self, host="127.0.0.1", port=6379, db=0, password=None, decode_responses=True):
        self.client = redis.Redis(
            host=host,
            port=int(port),
            db=int(db),
            password=password,
            decode_responses=decode_responses,
        )

    @classmethod
    def from_flask_config(cls, config):
        return cls(
            host=config.get("REDIS_HOST", "127.0.0.1"),
            port=config.get("REDIS_PORT", 6379),
            db=config.get("REDIS_DB", 0),
            password=config.get("REDIS_PASSWORD"),
        )

    def get_json(self, key):
        value = self.client.get(key)
        if not value:
            return None
        return json.loads(value)

    def set_json(self, key, value):
        self.client.set(key, json.dumps(value, ensure_ascii=False))

    def ping(self):
        return self.client.ping()

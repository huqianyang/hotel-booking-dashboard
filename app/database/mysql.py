import os
from contextlib import contextmanager

import pymysql

from app.database.schema import DATABASE_NAME


class MySQLConfig:
    def __init__(
        self,
        host=None,
        port=None,
        user=None,
        password=None,
        database=None,
        charset="utf8mb4",
    ):
        self.host = host or os.getenv("MYSQL_HOST", "127.0.0.1")
        self.port = int(port or os.getenv("MYSQL_PORT", "3306"))
        self.user = user or os.getenv("MYSQL_USER", "root")
        self.password = password if password is not None else os.getenv("MYSQL_PASSWORD", "")
        self.database = database or os.getenv("MYSQL_DATABASE", DATABASE_NAME)
        self.charset = charset

    @classmethod
    def from_flask_config(cls, config):
        return cls(
            host=config.get("MYSQL_HOST"),
            port=config.get("MYSQL_PORT"),
            user=config.get("MYSQL_USER"),
            password=config.get("MYSQL_PASSWORD"),
            database=config.get("MYSQL_DATABASE"),
        )


class MySQLClient:
    def __init__(self, config: MySQLConfig):
        self.config = config

    def connect(self):
        return pymysql.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            database=self.config.database,
            charset=self.config.charset,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )

    @contextmanager
    def cursor(self):
        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                yield cursor
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

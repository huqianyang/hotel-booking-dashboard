from dataclasses import dataclass


DATABASE_NAME = "hotel_booking_analysis"


@dataclass(frozen=True)
class ColumnDefinition:
    name: str
    sql_type: str
    nullable: bool = True
    default: str | None = None
    primary_key: bool = False

    def to_sql(self) -> str:
        parts = [self.name, self.sql_type]
        if self.primary_key:
            parts.append("PRIMARY KEY")
        if not self.nullable and not self.primary_key:
            parts.append("NOT NULL")
        if self.default is not None:
            parts.append(f"DEFAULT {self.default}")
        return " ".join(parts)


@dataclass(frozen=True)
class IndexDefinition:
    name: str
    columns: tuple[str, ...]

    def to_sql(self) -> str:
        return f"INDEX {self.name} ({', '.join(self.columns)})"


@dataclass(frozen=True)
class ForeignKeyDefinition:
    column: str
    references_table: str
    references_column: str

    def to_sql(self) -> str:
        return f"FOREIGN KEY ({self.column}) REFERENCES {self.references_table}({self.references_column})"


@dataclass(frozen=True)
class TableDefinition:
    name: str
    columns: tuple[ColumnDefinition, ...]
    primary_key: str
    indexes: tuple[IndexDefinition, ...] = ()
    foreign_keys: tuple[ForeignKeyDefinition, ...] = ()

    def to_sql(self) -> str:
        definitions = [column.to_sql() for column in self.columns]
        definitions.extend(index.to_sql() for index in self.indexes)
        definitions.extend(foreign_key.to_sql() for foreign_key in self.foreign_keys)
        joined = ",\n  ".join(definitions)
        return f"CREATE TABLE IF NOT EXISTS {self.name} (\n  {joined}\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"


HOTEL_BOOKINGS_COLUMNS = (
    ColumnDefinition("booking_id", "BIGINT", primary_key=True, nullable=False),
    ColumnDefinition("hotel", "VARCHAR(50)", nullable=False),
    ColumnDefinition("hotel_name", "VARCHAR(50)", nullable=False),
    ColumnDefinition("is_canceled", "TINYINT", nullable=False),
    ColumnDefinition("is_canceled_label", "VARCHAR(20)", nullable=False),
    ColumnDefinition("lead_time", "INT", nullable=False, default="0"),
    ColumnDefinition("arrival_date", "DATE", nullable=False),
    ColumnDefinition("event_date", "DATE", nullable=False),
    ColumnDefinition("stays_in_weekend_nights", "INT", nullable=False, default="0"),
    ColumnDefinition("stays_in_week_nights", "INT", nullable=False, default="0"),
    ColumnDefinition("total_nights", "INT", nullable=False, default="0"),
    ColumnDefinition("adults", "INT", nullable=False, default="0"),
    ColumnDefinition("children", "INT", nullable=False, default="0"),
    ColumnDefinition("babies", "INT", nullable=False, default="0"),
    ColumnDefinition("total_guests", "INT", nullable=False, default="0"),
    ColumnDefinition("meal", "VARCHAR(30)", nullable=False),
    ColumnDefinition("meal_name", "VARCHAR(30)", nullable=False),
    ColumnDefinition("country_code", "VARCHAR(20)", nullable=False),
    ColumnDefinition("country_name", "VARCHAR(80)", nullable=False),
    ColumnDefinition("market_segment", "VARCHAR(80)", nullable=False),
    ColumnDefinition("market_segment_name", "VARCHAR(80)", nullable=False),
    ColumnDefinition("distribution_channel", "VARCHAR(80)", nullable=False),
    ColumnDefinition("is_repeated_guest", "TINYINT", nullable=False, default="0"),
    ColumnDefinition("is_repeated_guest_label", "VARCHAR(20)", nullable=False),
    ColumnDefinition("previous_cancellations", "INT", nullable=False, default="0"),
    ColumnDefinition("previous_bookings_not_canceled", "INT", nullable=False, default="0"),
    ColumnDefinition("reserved_room_type", "VARCHAR(10)", nullable=False),
    ColumnDefinition("assigned_room_type", "VARCHAR(10)", nullable=False),
    ColumnDefinition("room_type_changed", "TINYINT", nullable=False, default="0"),
    ColumnDefinition("booking_changes", "INT", nullable=False, default="0"),
    ColumnDefinition("deposit_type", "VARCHAR(50)", nullable=False),
    ColumnDefinition("deposit_type_name", "VARCHAR(50)", nullable=False),
    ColumnDefinition("days_in_waiting_list", "INT", nullable=False, default="0"),
    ColumnDefinition("customer_type", "VARCHAR(80)", nullable=False),
    ColumnDefinition("customer_type_name", "VARCHAR(80)", nullable=False),
    ColumnDefinition("adr", "DECIMAL(10,2)", nullable=False, default="0.00"),
    ColumnDefinition("required_car_parking_spaces", "INT", nullable=False, default="0"),
    ColumnDefinition("total_of_special_requests", "INT", nullable=False, default="0"),
    ColumnDefinition("reservation_status", "VARCHAR(50)", nullable=False),
    ColumnDefinition("reservation_status_date", "DATE", nullable=False),
    ColumnDefinition("is_deleted", "TINYINT", nullable=False, default="0"),
)

TABLE_DEFINITIONS = {
    "hotel_bookings": TableDefinition(
        name="hotel_bookings",
        columns=HOTEL_BOOKINGS_COLUMNS,
        primary_key="booking_id",
        indexes=(
            IndexDefinition("idx_arrival_date", ("arrival_date",)),
            IndexDefinition("idx_country_code", ("country_code",)),
            IndexDefinition("idx_is_canceled", ("is_canceled",)),
            IndexDefinition("idx_event_date", ("event_date",)),
            IndexDefinition("idx_meal", ("meal",)),
            IndexDefinition("idx_room_type_changed", ("room_type_changed",)),
            IndexDefinition("idx_special_requests", ("total_of_special_requests",)),
        ),
    ),
    "prediction_results": TableDefinition(
        name="prediction_results",
        columns=(
            ColumnDefinition("prediction_id", "BIGINT", primary_key=True, nullable=False),
            ColumnDefinition("booking_id", "BIGINT", nullable=False),
            ColumnDefinition("model_version", "VARCHAR(50)", nullable=False),
            ColumnDefinition("cancel_probability", "DECIMAL(6,4)", nullable=False),
            ColumnDefinition("predicted_label", "TINYINT", nullable=False),
            ColumnDefinition("risk_level", "VARCHAR(20)", nullable=False),
            ColumnDefinition("source", "VARCHAR(30)", nullable=False),
            ColumnDefinition("predicted_at", "DATETIME", nullable=False),
        ),
        primary_key="prediction_id",
        indexes=(IndexDefinition("idx_prediction_booking_id", ("booking_id",)),),
        foreign_keys=(ForeignKeyDefinition("booking_id", "hotel_bookings", "booking_id"),),
    ),
    "model_metrics": TableDefinition(
        name="model_metrics",
        columns=(
            ColumnDefinition("metric_id", "BIGINT", primary_key=True, nullable=False),
            ColumnDefinition("model_name", "VARCHAR(100)", nullable=False),
            ColumnDefinition("model_version", "VARCHAR(50)", nullable=False),
            ColumnDefinition("accuracy", "DECIMAL(6,4)", nullable=False),
            ColumnDefinition("precision_score", "DECIMAL(6,4)", nullable=False),
            ColumnDefinition("recall_score", "DECIMAL(6,4)", nullable=False),
            ColumnDefinition("f1_score", "DECIMAL(6,4)", nullable=False),
            ColumnDefinition("train_score", "DECIMAL(6,4)", nullable=True),
            ColumnDefinition("test_score", "DECIMAL(6,4)", nullable=True),
            ColumnDefinition("is_selected", "TINYINT", nullable=False, default="0"),
            ColumnDefinition("model_path", "VARCHAR(255)", nullable=True),
            ColumnDefinition("created_at", "DATETIME", nullable=False),
        ),
        primary_key="metric_id",
        indexes=(IndexDefinition("idx_model_version", ("model_version",)),),
    ),
    "realtime_metrics": TableDefinition(
        name="realtime_metrics",
        columns=(
            ColumnDefinition("metric_id", "BIGINT", primary_key=True, nullable=False),
            ColumnDefinition("metric_name", "VARCHAR(100)", nullable=False),
            ColumnDefinition("metric_value", "VARCHAR(100)", nullable=False),
            ColumnDefinition("metric_type", "VARCHAR(50)", nullable=False),
            ColumnDefinition("window_start", "DATETIME", nullable=False),
            ColumnDefinition("window_end", "DATETIME", nullable=False),
            ColumnDefinition("updated_at", "DATETIME", nullable=False),
        ),
        primary_key="metric_id",
        indexes=(IndexDefinition("idx_realtime_window", ("window_start", "window_end")),),
    ),
}


def build_create_database_sql() -> str:
    return (
        f"CREATE DATABASE IF NOT EXISTS {DATABASE_NAME} "
        "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
    )


def build_schema_sql() -> str:
    table_sql = "\n\n".join(table.to_sql() for table in TABLE_DEFINITIONS.values())
    return f"USE {DATABASE_NAME};\n\n{table_sql}\n"

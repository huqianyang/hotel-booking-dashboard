-- 酒店预订数据可视化分析与预测系统
-- MySQL 建库建表脚本
-- 生成来源：app.database.schema

CREATE DATABASE IF NOT EXISTS hotel_booking_analysis DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE hotel_booking_analysis;

CREATE TABLE IF NOT EXISTS hotel_bookings (
  booking_id BIGINT PRIMARY KEY,
  hotel VARCHAR(50) NOT NULL,
  hotel_name VARCHAR(50) NOT NULL,
  is_canceled TINYINT NOT NULL,
  is_canceled_label VARCHAR(20) NOT NULL,
  lead_time INT NOT NULL DEFAULT 0,
  arrival_date DATE NOT NULL,
  event_date DATE NOT NULL,
  stays_in_weekend_nights INT NOT NULL DEFAULT 0,
  stays_in_week_nights INT NOT NULL DEFAULT 0,
  total_nights INT NOT NULL DEFAULT 0,
  adults INT NOT NULL DEFAULT 0,
  children INT NOT NULL DEFAULT 0,
  babies INT NOT NULL DEFAULT 0,
  total_guests INT NOT NULL DEFAULT 0,
  country_code VARCHAR(20) NOT NULL,
  country_name VARCHAR(80) NOT NULL,
  market_segment VARCHAR(80) NOT NULL,
  market_segment_name VARCHAR(80) NOT NULL,
  distribution_channel VARCHAR(80) NOT NULL,
  deposit_type VARCHAR(50) NOT NULL,
  deposit_type_name VARCHAR(50) NOT NULL,
  customer_type VARCHAR(80) NOT NULL,
  customer_type_name VARCHAR(80) NOT NULL,
  adr DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  reservation_status VARCHAR(50) NOT NULL,
  reservation_status_date DATE NOT NULL,
  is_deleted TINYINT NOT NULL DEFAULT 0,
  INDEX idx_arrival_date (arrival_date),
  INDEX idx_country_code (country_code),
  INDEX idx_is_canceled (is_canceled),
  INDEX idx_event_date (event_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS prediction_results (
  prediction_id BIGINT PRIMARY KEY,
  booking_id BIGINT NOT NULL,
  model_version VARCHAR(50) NOT NULL,
  cancel_probability DECIMAL(6,4) NOT NULL,
  predicted_label TINYINT NOT NULL,
  risk_level VARCHAR(20) NOT NULL,
  source VARCHAR(30) NOT NULL,
  predicted_at DATETIME NOT NULL,
  INDEX idx_prediction_booking_id (booking_id),
  FOREIGN KEY (booking_id) REFERENCES hotel_bookings(booking_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS model_metrics (
  metric_id BIGINT PRIMARY KEY,
  model_name VARCHAR(100) NOT NULL,
  model_version VARCHAR(50) NOT NULL,
  accuracy DECIMAL(6,4) NOT NULL,
  precision_score DECIMAL(6,4) NOT NULL,
  recall_score DECIMAL(6,4) NOT NULL,
  f1_score DECIMAL(6,4) NOT NULL,
  train_score DECIMAL(6,4),
  test_score DECIMAL(6,4),
  is_selected TINYINT NOT NULL DEFAULT 0,
  model_path VARCHAR(255),
  created_at DATETIME NOT NULL,
  INDEX idx_model_version (model_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS realtime_metrics (
  metric_id BIGINT PRIMARY KEY,
  metric_name VARCHAR(100) NOT NULL,
  metric_value VARCHAR(100) NOT NULL,
  metric_type VARCHAR(50) NOT NULL,
  window_start DATETIME NOT NULL,
  window_end DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  INDEX idx_realtime_window (window_start, window_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

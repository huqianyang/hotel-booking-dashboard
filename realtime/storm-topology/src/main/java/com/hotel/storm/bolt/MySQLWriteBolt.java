package com.hotel.storm.bolt;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import org.apache.storm.task.OutputCollector;
import org.apache.storm.task.TopologyContext;
import org.apache.storm.topology.OutputFieldsDeclarer;
import org.apache.storm.topology.base.BaseRichBolt;
import org.apache.storm.tuple.Tuple;

public class MySQLWriteBolt extends BaseRichBolt {
    private final String jdbcUrl;
    private final String username;
    private final String password;
    private final AtomicLong idSequence = new AtomicLong(System.currentTimeMillis());
    private final Map<String, MetricState> countryRisk = new HashMap<>();
    private final Map<String, MetricState> channelRisk = new HashMap<>();
    private OutputCollector collector;
    private Connection connection;
    private long processedCount;
    private long highRiskCount;
    private double probabilitySum;
    private long predictedCancellationCount;

    public MySQLWriteBolt(String jdbcUrl, String username, String password) {
        this.jdbcUrl = jdbcUrl;
        this.username = username;
        this.password = password;
    }

    @Override
    public void prepare(Map<String, Object> topoConf, TopologyContext context, OutputCollector collector) {
        this.collector = collector;
        ensureConnection();
    }

    @Override
    public void execute(Tuple input) {
        try {
            Map<String, Object> envelope = (Map<String, Object>) input.getValueByField("prediction_event");
            Map<String, Object> event = (Map<String, Object>) envelope.get("event");
            Map<String, Object> prediction = (Map<String, Object>) envelope.get("prediction");
            updateState(event, prediction);
            writePrediction(prediction);
            writeRealtimeMetrics(event);
            collector.ack(input);
        } catch (Exception error) {
            collector.reportError(error);
            collector.fail(input);
        }
    }

    @Override
    public void declareOutputFields(OutputFieldsDeclarer declarer) {
    }

    @Override
    public void cleanup() {
        try {
            if (connection != null) {
                connection.close();
            }
        } catch (Exception ignored) {
        }
    }

    private void updateState(Map<String, Object> event, Map<String, Object> prediction) {
        processedCount += 1;
        double probability = doubleValue(prediction.get("cancel_probability"));
        probabilitySum += probability;
        String riskLevel = String.valueOf(prediction.getOrDefault("risk_level", ""));
        if ("high".equals(riskLevel)) {
            highRiskCount += 1;
        }
        int predictedLabel = intValue(prediction.get("predicted_label"));
        if (predictedLabel == 1) {
            predictedCancellationCount += 1;
        }
        updateMetricState(countryRisk, String.valueOf(event.getOrDefault("country_name", "unknown")), predictedLabel);
        updateMetricState(channelRisk, String.valueOf(event.getOrDefault("market_segment", "unknown")), predictedLabel);
    }

    private void writePrediction(Map<String, Object> prediction) throws Exception {
        ensureConnection();
        try (PreparedStatement statement = connection.prepareStatement(
            "INSERT INTO prediction_results (prediction_id, booking_id, model_version, cancel_probability, predicted_label, risk_level, source, predicted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        )) {
            statement.setLong(1, nextId());
            statement.setLong(2, longValue(prediction.get("booking_id")));
            statement.setString(3, String.valueOf(prediction.getOrDefault("model_version", "unknown_model_v1")));
            statement.setDouble(4, doubleValue(prediction.get("cancel_probability")));
            statement.setInt(5, intValue(prediction.get("predicted_label")));
            statement.setString(6, String.valueOf(prediction.getOrDefault("risk_level", "low")));
            statement.setString(7, "storm");
            statement.setTimestamp(8, Timestamp.from(Instant.now()));
            statement.executeUpdate();
        }
    }

    private void writeRealtimeMetrics(Map<String, Object> event) throws Exception {
        Timestamp now = Timestamp.from(Instant.now());
        writeMetric("summary", "processed_count", String.valueOf(processedCount), now);
        writeMetric("summary", "high_risk_count", String.valueOf(highRiskCount), now);
        writeMetric("summary", "average_cancel_probability", format(probabilitySum / processedCount), now);
        writeMetric("trend_day", "inflow", String.valueOf(processedCount), now);
        writeMetric("trend_day", "predicted_cancellations", String.valueOf(predictedCancellationCount), now);
        writeMetric("trend_day", "cancel_rate", format((double) predictedCancellationCount / processedCount), now);
        writeMetric("trend_week", "inflow", String.valueOf(processedCount), now);
        writeMetric("trend_week", "predicted_cancellations", String.valueOf(predictedCancellationCount), now);
        writeMetric("trend_week", "cancel_rate", format((double) predictedCancellationCount / processedCount), now);
        writeMetric("trend_month", "inflow", String.valueOf(processedCount), now);
        writeMetric("trend_month", "predicted_cancellations", String.valueOf(predictedCancellationCount), now);
        writeMetric("trend_month", "cancel_rate", format((double) predictedCancellationCount / processedCount), now);
        for (Map.Entry<String, MetricState> entry : countryRisk.entrySet()) {
            writeMetric("country_risk", entry.getKey(), format(entry.getValue().cancelRate()), now);
        }
        for (Map.Entry<String, MetricState> entry : channelRisk.entrySet()) {
            writeMetric("channel_risk", entry.getKey(), format(entry.getValue().cancelRate()), now);
        }
    }

    private void writeMetric(String metricType, String metricName, String metricValue, Timestamp now) throws Exception {
        ensureConnection();
        try (PreparedStatement statement = connection.prepareStatement(
            "INSERT INTO realtime_metrics (metric_id, metric_name, metric_value, metric_type, window_start, window_end, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
        )) {
            statement.setLong(1, nextId());
            statement.setString(2, metricName);
            statement.setString(3, metricValue);
            statement.setString(4, metricType);
            statement.setTimestamp(5, now);
            statement.setTimestamp(6, now);
            statement.setTimestamp(7, now);
            statement.executeUpdate();
        }
    }

    private void ensureConnection() {
        try {
            if (connection == null || connection.isClosed()) {
                connection = DriverManager.getConnection(jdbcUrl, username, password);
                connection.setAutoCommit(true);
            }
        } catch (Exception error) {
            throw new IllegalStateException("Unable to connect to MySQL", error);
        }
    }

    private void updateMetricState(Map<String, MetricState> states, String key, int predictedLabel) {
        MetricState state = states.computeIfAbsent(key, ignored -> new MetricState());
        state.total += 1;
        if (predictedLabel == 1) {
            state.predictedCancellations += 1;
        }
    }

    private long nextId() {
        return idSequence.incrementAndGet();
    }

    private static long longValue(Object value) {
        return value instanceof Number ? ((Number) value).longValue() : Long.parseLong(String.valueOf(value));
    }

    private static int intValue(Object value) {
        return value instanceof Number ? ((Number) value).intValue() : Integer.parseInt(String.valueOf(value));
    }

    private static double doubleValue(Object value) {
        return value instanceof Number ? ((Number) value).doubleValue() : Double.parseDouble(String.valueOf(value));
    }

    private static String format(double value) {
        return String.format(java.util.Locale.US, "%.4f", value);
    }

    private static class MetricState {
        long total;
        long predictedCancellations;

        double cancelRate() {
            return total == 0 ? 0.0 : (double) predictedCancellations / total;
        }
    }
}

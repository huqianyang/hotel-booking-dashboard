package com.hotel.storm.bolt;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.apache.storm.task.OutputCollector;
import org.apache.storm.task.TopologyContext;
import org.apache.storm.topology.OutputFieldsDeclarer;
import org.apache.storm.topology.base.BaseRichBolt;
import org.apache.storm.tuple.Tuple;
import redis.clients.jedis.Jedis;

public class RedisMetricBolt extends BaseRichBolt {
    private static final DateTimeFormatter TIME_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss").withZone(ZoneId.of("Asia/Shanghai"));
    private final String redisHost;
    private final int redisPort;
    private final ObjectMapper mapper = new ObjectMapper();
    private final List<Map<String, Object>> recentPredictions = new ArrayList<>();
    private final Map<String, MetricState> countryRisk = new HashMap<>();
    private final Map<String, MetricState> channelRisk = new HashMap<>();
    private OutputCollector collector;
    private Jedis jedis;
    private long processedCount;
    private long highRiskCount;
    private long predictedCancellationCount;
    private double probabilitySum;

    public RedisMetricBolt(String redisHost, int redisPort) {
        this.redisHost = redisHost;
        this.redisPort = redisPort;
    }

    @Override
    public void prepare(Map<String, Object> topoConf, TopologyContext context, OutputCollector collector) {
        this.collector = collector;
        this.jedis = new Jedis(redisHost, redisPort);
    }

    @Override
    public void execute(Tuple input) {
        try {
            Map<String, Object> envelope = (Map<String, Object>) input.getValueByField("prediction_event");
            Map<String, Object> event = (Map<String, Object>) envelope.get("event");
            Map<String, Object> prediction = (Map<String, Object>) envelope.get("prediction");
            updateState(event, prediction);
            writeRedis(event, prediction);
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
        if (jedis != null) {
            jedis.close();
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
        recentPredictions.add(0, recentPrediction(event, prediction));
        while (recentPredictions.size() > 10) {
            recentPredictions.remove(recentPredictions.size() - 1);
        }
    }

    private void writeRedis(Map<String, Object> event, Map<String, Object> prediction) throws Exception {
        String now = TIME_FORMAT.format(Instant.now());
        jedis.set("realtime:summary", mapper.writeValueAsString(summary(now)));
        jedis.set("realtime:trend", mapper.writeValueAsString(trend(now)));
        Map<String, Object> recentPayload = new LinkedHashMap<String, Object>();
        recentPayload.put("items", recentPredictions);
        recentPayload.put("status", "running");
        jedis.set("realtime:recent_predictions", mapper.writeValueAsString(recentPayload));
        jedis.set("realtime:country_risk", mapper.writeValueAsString(topRisk(countryRisk)));
        jedis.set("realtime:channel_risk", mapper.writeValueAsString(topRisk(channelRisk)));
        Map<String, Object> linkStatus = new LinkedHashMap<String, Object>();
        linkStatus.put("redis", "running");
        linkStatus.put("flume", "running");
        linkStatus.put("kafka", "running");
        linkStatus.put("storm", "running");
        linkStatus.put("updated_at", now);
        jedis.set("realtime:link_status", mapper.writeValueAsString(linkStatus));
    }

    private Map<String, Object> summary(String now) {
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("processed_count", processedCount);
        summary.put("high_risk_count", highRiskCount);
        summary.put("average_cancel_probability", round(probabilitySum / processedCount));
        summary.put("updated_at", now);
        summary.put("status", "running");
        return summary;
    }

    private Map<String, Object> trend(String now) {
        Map<String, Object> point = new LinkedHashMap<>();
        point.put("label", now);
        point.put("inflow", processedCount);
        point.put("predicted_cancellations", predictedCancellationCount);
        point.put("cancel_rate", round((double) predictedCancellationCount / processedCount));
        Map<String, Object> trend = new LinkedHashMap<String, Object>();
        trend.put("day", onePointList(point));
        trend.put("week", onePointList(point));
        trend.put("month", onePointList(point));
        return trend;
    }

    private Map<String, Object> recentPrediction(Map<String, Object> event, Map<String, Object> prediction) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("booking_id", prediction.get("booking_id"));
        item.put("hotel_name", event.getOrDefault("hotel_name", ""));
        item.put("country_name", event.getOrDefault("country_name", ""));
        item.put("cancel_probability", prediction.get("cancel_probability"));
        item.put("risk_level_name", prediction.get("risk_level_name"));
        item.put("business_time", event.getOrDefault("business_time", TIME_FORMAT.format(Instant.now())));
        return item;
    }

    private List<Map<String, Object>> topRisk(Map<String, MetricState> source) {
        List<Map<String, Object>> items = new ArrayList<Map<String, Object>>();
        List<Map.Entry<String, MetricState>> entries = new ArrayList<Map.Entry<String, MetricState>>(source.entrySet());
        entries.sort(Comparator.comparingDouble((Map.Entry<String, MetricState> entry) -> entry.getValue().cancelRate()).reversed());
        for (Map.Entry<String, MetricState> entry : entries) {
            if (items.size() >= 5) {
                break;
            }
            Map<String, Object> item = new LinkedHashMap<String, Object>();
            item.put("name", entry.getKey());
            item.put("value", round(entry.getValue().cancelRate()));
            item.put("booking_count", entry.getValue().total);
            item.put("predicted_cancellations", entry.getValue().predictedCancellations);
            items.add(item);
        }
        return items;
    }

    private List<Map<String, Object>> onePointList(Map<String, Object> point) {
        List<Map<String, Object>> points = new ArrayList<Map<String, Object>>();
        points.add(point);
        return points;
    }

    private void updateMetricState(Map<String, MetricState> states, String key, int predictedLabel) {
        MetricState state = states.computeIfAbsent(key, ignored -> new MetricState());
        state.total += 1;
        if (predictedLabel == 1) {
            state.predictedCancellations += 1;
        }
    }

    private static int intValue(Object value) {
        return value instanceof Number ? ((Number) value).intValue() : Integer.parseInt(String.valueOf(value));
    }

    private static double doubleValue(Object value) {
        return value instanceof Number ? ((Number) value).doubleValue() : Double.parseDouble(String.valueOf(value));
    }

    private static double round(double value) {
        return Math.round(value * 10000.0) / 10000.0;
    }

    private static class MetricState {
        long total;
        long predictedCancellations;

        double cancelRate() {
            return total == 0 ? 0.0 : (double) predictedCancellations / total;
        }
    }
}

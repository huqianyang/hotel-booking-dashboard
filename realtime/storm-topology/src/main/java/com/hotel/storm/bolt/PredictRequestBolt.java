package com.hotel.storm.bolt;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import org.apache.storm.task.OutputCollector;
import org.apache.storm.task.TopologyContext;
import org.apache.storm.topology.OutputFieldsDeclarer;
import org.apache.storm.topology.base.BaseRichBolt;
import org.apache.storm.tuple.Fields;
import org.apache.storm.tuple.Tuple;
import org.apache.storm.tuple.Values;

public class PredictRequestBolt extends BaseRichBolt {
    public static final String DEFAULT_PREDICT_PATH = "/api/prediction/single";
    private final String predictUrl;
    private final ObjectMapper mapper = new ObjectMapper();
    private OutputCollector collector;

    public PredictRequestBolt(String predictUrl) {
        this.predictUrl = predictUrl == null || predictUrl.trim().isEmpty() ? "http://host.docker.internal:5000" + DEFAULT_PREDICT_PATH : predictUrl;
    }

    @Override
    public void prepare(Map<String, Object> topoConf, TopologyContext context, OutputCollector collector) {
        this.collector = collector;
    }

    @Override
    public void execute(Tuple input) {
        try {
            Map<String, Object> event = (Map<String, Object>) input.getValueByField("event");
            Map<String, Object> requestPayload = new HashMap<String, Object>();
            requestPayload.put("booking_id", event.get("booking_id"));

            Map<String, Object> body = mapper.readValue(postJson(mapper.writeValueAsString(requestPayload)), new TypeReference<Map<String, Object>>() {});
            Map<String, Object> prediction = (Map<String, Object>) body.get("data");
            if (prediction == null) {
                throw new IllegalStateException("Flask prediction API response missing data");
            }
            Map<String, Object> enriched = new HashMap<String, Object>();
            enriched.put("event", event);
            enriched.put("prediction", prediction);
            collector.emit(input, new Values(enriched));
            collector.ack(input);
        } catch (Exception error) {
            collector.reportError(error);
            collector.fail(input);
        }
    }

    @Override
    public void declareOutputFields(OutputFieldsDeclarer declarer) {
        declarer.declare(new Fields("prediction_event"));
    }

    private String postJson(String payload) throws Exception {
        HttpURLConnection connection = (HttpURLConnection) new URL(predictUrl).openConnection();
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(5000);
        connection.setReadTimeout(10000);
        connection.setDoOutput(true);
        connection.setRequestProperty("Content-Type", "application/json; charset=UTF-8");

        byte[] bytes = payload.getBytes(StandardCharsets.UTF_8);
        connection.setFixedLengthStreamingMode(bytes.length);
        OutputStream output = connection.getOutputStream();
        try {
            output.write(bytes);
        } finally {
            output.close();
        }

        int statusCode = connection.getResponseCode();
        InputStream stream = statusCode >= 200 && statusCode < 300 ? connection.getInputStream() : connection.getErrorStream();
        String response = readAll(stream);
        connection.disconnect();
        if (statusCode < 200 || statusCode >= 300) {
            throw new IllegalStateException("Flask prediction API returned " + statusCode + ": " + response);
        }
        return response;
    }

    private String readAll(InputStream stream) throws Exception {
        if (stream == null) {
            return "";
        }
        BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8));
        StringBuilder builder = new StringBuilder();
        String line;
        while ((line = reader.readLine()) != null) {
            builder.append(line);
        }
        return builder.toString();
    }
}

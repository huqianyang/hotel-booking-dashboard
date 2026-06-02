package com.hotel.storm.bolt;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;
import org.apache.storm.task.OutputCollector;
import org.apache.storm.task.TopologyContext;
import org.apache.storm.topology.OutputFieldsDeclarer;
import org.apache.storm.topology.base.BaseRichBolt;
import org.apache.storm.tuple.Fields;
import org.apache.storm.tuple.Tuple;
import org.apache.storm.tuple.Values;

public class EventParseBolt extends BaseRichBolt {
    private final ObjectMapper mapper = new ObjectMapper();
    private OutputCollector collector;

    @Override
    public void prepare(Map<String, Object> topoConf, TopologyContext context, OutputCollector collector) {
        this.collector = collector;
    }

    @Override
    public void execute(Tuple input) {
        try {
            String raw = input.getStringByField("value");
            Map<String, Object> event = mapper.readValue(raw, new TypeReference<Map<String, Object>>() {});
            if (!event.containsKey("booking_id")) {
                throw new IllegalArgumentException("booking_id is required");
            }
            event.putIfAbsent("business_time", event.get("generated_at"));
            collector.emit(input, new Values(event));
            collector.ack(input);
        } catch (Exception error) {
            collector.reportError(error);
            collector.fail(input);
        }
    }

    @Override
    public void declareOutputFields(OutputFieldsDeclarer declarer) {
        declarer.declare(new Fields("event"));
    }
}

package com.hotel.storm;

import com.hotel.storm.bolt.EventParseBolt;
import com.hotel.storm.bolt.MySQLWriteBolt;
import com.hotel.storm.bolt.PredictRequestBolt;
import com.hotel.storm.bolt.RedisMetricBolt;
import java.util.Properties;
import org.apache.storm.Config;
import org.apache.storm.StormSubmitter;
import org.apache.storm.kafka.spout.FirstPollOffsetStrategy;
import org.apache.storm.kafka.spout.KafkaSpout;
import org.apache.storm.kafka.spout.KafkaSpoutConfig;
import org.apache.storm.topology.TopologyBuilder;

public class HotelBookingTopology {
    public static void main(String[] args) throws Exception {
        String topologyName = env("TOPOLOGY_NAME", "hotel-booking-realtime-topology");
        String kafkaBootstrap = env("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092");
        String kafkaTopic = env("KAFKA_TOPIC", "hotel-booking-events");
        String flaskPredictUrl = env("FLASK_PREDICT_URL", "http://host.docker.internal:5000/api/prediction/single");
        String mysqlUrl = env("MYSQL_JDBC_URL", "jdbc:mysql://host.docker.internal:3306/hotel_booking_analysis?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai");
        String mysqlUser = env("MYSQL_USER", "root");
        String mysqlPassword = env("MYSQL_PASSWORD", "");
        String redisHost = env("REDIS_HOST", "redis");
        int redisPort = Integer.parseInt(env("REDIS_PORT", "6379"));

        KafkaSpoutConfig<String, String> kafkaConfig = KafkaSpoutConfig.builder(kafkaBootstrap, kafkaTopic)
            .setProp(buildKafkaProps())
            .setFirstPollOffsetStrategy(FirstPollOffsetStrategy.UNCOMMITTED_EARLIEST)
            .build();

        TopologyBuilder builder = new TopologyBuilder();
        builder.setSpout("kafka-spout", new KafkaSpout<>(kafkaConfig), 1);
        builder.setBolt("event-parse-bolt", new EventParseBolt(), 1).shuffleGrouping("kafka-spout");
        builder.setBolt("predict-request-bolt", new PredictRequestBolt(flaskPredictUrl), 2).shuffleGrouping("event-parse-bolt");
        builder.setBolt("mysql-write-bolt", new MySQLWriteBolt(mysqlUrl, mysqlUser, mysqlPassword), 1).shuffleGrouping("predict-request-bolt");
        builder.setBolt("redis-metric-bolt", new RedisMetricBolt(redisHost, redisPort), 1).shuffleGrouping("predict-request-bolt");

        Config config = new Config();
        config.setNumWorkers(1);
        config.setMessageTimeoutSecs(60);
        StormSubmitter.submitTopology(topologyName, config, builder.createTopology());
    }

    private static Properties buildKafkaProps() {
        Properties props = new Properties();
        props.setProperty("key.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
        props.setProperty("value.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
        props.setProperty("group.id", "hotel-booking-storm");
        return props;
    }

    private static String env(String name, String defaultValue) {
        String value = System.getenv(name);
        return value == null || value.trim().isEmpty() ? defaultValue : value;
    }
}

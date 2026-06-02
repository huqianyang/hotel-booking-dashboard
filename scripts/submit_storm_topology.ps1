param(
    [string]$FlaskPredictUrl = "http://host.docker.internal:5000/api/prediction/single",
    [string]$MysqlJdbcUrl = "jdbc:mysql://host.docker.internal:3306/hotel_booking_analysis?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai",
    [string]$MysqlUser = "root",
    [string]$MysqlPassword = "",
    [string]$RedisHost = "redis",
    [int]$RedisPort = 6379
)

$ErrorActionPreference = "Stop"

mvn -f realtime\storm-topology\pom.xml package

docker compose -f realtime\docker-compose.yml up -d redis zookeeper kafka storm-nimbus storm-supervisor storm-ui flume

docker exec `
  -e FLASK_PREDICT_URL=$FlaskPredictUrl `
  -e MYSQL_JDBC_URL=$MysqlJdbcUrl `
  -e MYSQL_USER=$MysqlUser `
  -e MYSQL_PASSWORD=$MysqlPassword `
  -e REDIS_HOST=$RedisHost `
  -e REDIS_PORT=$RedisPort `
  hotel-storm-nimbus `
  storm jar /topology/hotel-booking-storm-topology.jar com.hotel.storm.HotelBookingTopology

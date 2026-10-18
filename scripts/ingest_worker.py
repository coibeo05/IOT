import sys
import json
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# --- CẤU HÌNH ---
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "iot/lab2/b23dccn034/telemetry"

INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "my-super-secret-auth-token"
INFLUX_ORG = "iot_lab"
INFLUX_BUCKET = "iot_raw"

# Khởi tạo kết nối InfluxDB
try:
    influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    print("[INFLUXDB] Ket noi InfluxDB thanh cong!")
except Exception as e:
    print(f"[INFLUXDB ERROR] Khong the ket noi InfluxDB: {e}")
    sys.exit(1)

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[MQTT] Ket noi Broker EMQX thanh cong! Return code: {rc}")
    client.subscribe(MQTT_TOPIC)
    print(f"[MQTT] Dang lang nghe topic: {MQTT_TOPIC}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        temp = payload.get("temperature")
        hum = payload.get("humidity")
        dist = payload.get("distance_cm")

        # Validation dữ liệu
        if temp is not None and (-40 <= temp <= 125) and (0 <= hum <= 100):
            point = Point("sensor_telemetry") \
                .tag("device_id", "esp32_wokwi") \
                .tag("sensor_group", "env_ultrasonic") \
                .field("temperature", float(temp)) \
                .field("humidity", float(hum)) \
                .field("distance_cm", float(dist)) \
                .field("rssi", int(payload.get("rssi", 0))) \
                .field("sequence", int(payload.get("sequence", 0))) \
                .field("uptime_s", int(payload.get("uptime_s", 0)))
            
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
            print(f"[STORED RAW #{payload.get('sequence')}] T={temp}°C | H={hum}% | Dist={dist}cm", flush=True)
    except Exception as e:
        print(f"[ERROR] Loi khi thu thap du lieu: {e}", flush=True)

try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="Python_Ingest_Worker_B23DCCN034")
except AttributeError:
    client = mqtt.Client(client_id="Python_Ingest_Worker_B23DCCN034")

client.on_connect = on_connect
client.on_message = on_message

print("[SYSTEM] Khoi dong Ingestion Worker...", flush=True)
try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()
except Exception as e:
    print(f"[MQTT ERROR] Ket noi Broker that bai: {e}")
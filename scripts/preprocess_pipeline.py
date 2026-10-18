import sys
import pandas as pd
import numpy as np
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from sklearn.preprocessing import MinMaxScaler

INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "my-super-secret-auth-token"
INFLUX_ORG = "iot_lab"

print("[SYSTEM] Dang ket noi va truy van du lieu tu InfluxDB iot_raw...", flush=True)

try:
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()

    # Truy vấn dữ liệu trong 24 giờ qua từ bucket iot_raw
    query = '''
    from(bucket: "iot_raw")
      |> range(start: -24h)
      |> filter(fn: (r) => r["_measurement"] == "sensor_telemetry")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    df = query_api.query_data_frame(query)

    if isinstance(df, list):
        df = df[0] if len(df) > 0 else pd.DataFrame()

    if df.empty:
        print("[WARNING] Bucket 'iot_raw' hien tai dang RONG. Hay chay ingest_worker.py de nhat du lieu tu Wokwi truoc!", flush=True)
        sys.exit(0)

    print(f"[DATA] Tim thay {len(df)} ban ghi tho trong iot_raw.", flush=True)

    if len(df) < 3:
        print("[WARNING] Baza du lieu chua du tối thieu 3 ban ghi de chay thuat toan IQR va Resampling. Hay doi them 15-30s!", flush=True)
        sys.exit(0)

    # 1. Định dạng thời gian
    df['_time'] = pd.to_datetime(df['_time'])
    df.set_index('_time', inplace=True)
    df = df[['temperature', 'humidity', 'distance_cm']].sort_index()

    # 2. Xử lý Outlier bằng IQR
    for col in ['temperature', 'humidity', 'distance_cm']:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outliers = (df[col] < lower_bound) | (df[col] > upper_bound)
        if outliers.sum() > 0:
            print(f"[IQR] Phat hien {outliers.sum()} diem ngoai lai o thuoc tinh '{col}'. Tien hanh noi suy làm min.", flush=True)
            df.loc[outliers, col] = np.nan
            df[col] = df[col].interpolate(method='time').ffill().bfill()

    # 3. Resampling từ 5s sang 15s
    df_resampled = df.resample('15s').mean().interpolate(method='time')

    # 4. Feature Engineering
    df_resampled['temp_rolling_mean'] = df_resampled['temperature'].rolling(window=3, min_periods=1).mean()
    df_resampled['dist_delta'] = df_resampled['distance_cm'].diff().fillna(0)

    # 5. Min-Max Normalization
    scaler = MinMaxScaler()
    norm_cols = ['temp_norm', 'hum_norm', 'dist_norm']
    df_resampled[norm_cols] = scaler.fit_transform(df_resampled[['temperature', 'humidity', 'distance_cm']])

    # 6. Ghi dữ liệu sạch vào bucket iot_processed
    write_api = client.write_api(write_options=SYNCHRONOUS)
    for timestamp, row in df_resampled.iterrows():
        p = Point("sensor_processed") \
            .tag("device_id", "esp32_wokwi") \
            .time(timestamp) \
            .field("temp_clean", float(row['temperature'])) \
            .field("temp_rolling_mean", float(row['temp_rolling_mean'])) \
            .field("temp_norm", float(row['temp_norm'])) \
            .field("hum_clean", float(row['humidity'])) \
            .field("hum_norm", float(row['hum_norm'])) \
            .field("dist_clean", float(row['distance_cm'])) \
            .field("dist_delta", float(row['dist_delta'])) \
            .field("dist_norm", float(row['dist_norm']))
        write_api.write(bucket="iot_processed", org=INFLUX_ORG, record=p)

    print(f"[HOAN TAT] Da tien xu ly va luu tru {len(df_resampled)} ban ghi vao iot_processed!", flush=True)

except Exception as e:
    print(f"[ERROR] Loi trong qua trinh tien xu ly: {e}", flush=True)
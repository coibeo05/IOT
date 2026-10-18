import streamlit as st
import pandas as pd
from influxdb_client import InfluxDBClient

# 1. Cấu hình trang web Streamlit
st.set_page_config(
    page_title="IoT Realtime Dashboard - B23DCCN034",
    page_icon="📊",
    layout="wide"
)

# Thống tin cấu hình InfluxDB
INFLUX_URL = "http://localhost:8086"
INFLUX_TOKEN = "my-super-secret-auth-token"
INFLUX_ORG = "iot_lab"

# 2. Tiêu đề ứng dụng
st.title("🌐 Ung Dung Giam Sat Du Lieu IoT Realtime")
st.caption("Học phần: INT14149 - IoT và Ứng dụng | Sinh viên: Nguyễn Đức Anh - B23DCCN034")
st.markdown("---")

# 3. Hàm kết nối và lấy dữ liệu mới nhất
@st.cache_data(ttl=5)
def load_data():
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        query_api = client.query_api()
        
        query = '''
        from(bucket: "iot_processed")
          |> range(start: -2h)
          |> filter(fn: (r) => r["_measurement"] == "sensor_processed")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        df = query_api.query_data_frame(query)
        if isinstance(df, list):
            df = df[0] if len(df) > 0 else pd.DataFrame()
            
        if not df.empty:
            df['_time'] = pd.to_datetime(df['_time'])
            df.set_index('_time', inplace=True)
            df.sort_index(inplace=True)
        return df
    except Exception as e:
        st.error(f"Lỗi kết nối InfluxDB: {e}")
        return pd.DataFrame()

# Nút làm mới dữ liệu
if st.button("🔄 Cập nhật dữ liệu mới"):
    st.cache_data.clear()

df = load_data()

if df.empty:
    st.warning("⚠️ Chưa tìm thấy dữ liệu trong bucket 'iot_processed'. Hãy đảm bảo ingest_worker.py và preprocess_pipeline.py đã được chạy!")
else:
    # 4. Hiển thị 3 chỉ số Metric dạng thẻ
    latest = df.iloc[-1]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="🌡️ Nhiệt độ làm sạch (temp_clean)", 
            value=f"{latest.get('temp_clean', 0):.1f} °C"
        )
    with col2:
        st.metric(
            label="💧 Độ ẩm làm sạch (hum_clean)", 
            value=f"{latest.get('hum_clean', 0):.1f} %"
        )
    with col3:
        st.metric(
            label="📏 Khoảng cách (dist_clean)", 
            value=f"{latest.get('dist_clean', 0):.1f} cm"
        )

    st.markdown("---")

    # 5. Vẽ biểu đồ trực quan
    st.subheader("📈 Biểu đồ chuỗi thời gian (IoT Processed)")
    
    tab1, tab2 = st.tabs(["Nhiệt độ & Độ ẩm (Đã lọc IQR)", "Min-Max Normalization [0, 1]"])
    
    with tab1:
        chart_data1 = df[['temp_clean', 'temp_rolling_mean', 'hum_clean']].dropna()
        st.line_chart(chart_data1)
        st.info("Đường temp_clean thể hiện nhiệt độ đã lọc Outlier IQR; temp_rolling_mean làm mượt bằng MA-3.")

    with tab2:
        chart_data2 = df[['temp_norm', 'hum_norm', 'dist_norm']].dropna()
        st.line_chart(chart_data2)
        st.info("Tất cả các đại lượng đã được quy đồng về miền giá trị không thứ nguyên [0, 1].")

    # 6. Hiển thị bảng dữ liệu chi tiết
    with st.expander("📄 Xem bảng dữ liệu chi tiết (Bản ghi gần nhất)"):
        st.dataframe(df.tail(10), use_container_width=True)
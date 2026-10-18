#README
📡 BÀI THỰC HÀNH 2: HỆ THỐNG XỬ LÝ VÀ TIỀN XỬ LÝ DỮ LIỆU IOT THEO CHUỖI THỜI GIAN (INFLUXDB & PYTHON PIPELINE)

Môn học: INT14149 - IoT và Ứng dụng

Sinh viên thực hiện: Nguyễn Đức Anh

Mã số sinh viên: B23DCCN034

Kiến trúc: ESP32 (Wokwi) ➔ EMQX Broker ➔ Python Ingestion Worker ➔ InfluxDB 2.7 ➔ Python Preprocessing Pipeline ➔ Streamlit Dashboard App

📋 MỤC LỤC
Tổng quan hệ thống

Sơ đồ kiến trúc & Data Flow

Cấu trúc thư mục dự án

Mô tả chi tiết các mô-đun

Quy trình tiền xử lý dữ liệu

Đánh giá hiệu năng End-to-End Latency

Hướng dẫn cài đặt & Khởi chạy

1. TỔNG QUAN HỆ THỐNG

Dự án xây dựng một luồng thu thập, lưu trữ, tiền xử lý và trực quan hóa dữ liệu chuỗi thời gian (Time-Series Data) từ thiết bị biên IoT. Hệ thống giải quyết triệt để các vấn đề nhiễu dữ liệu vật lý (Outliers), thiếu dữ liệu (Missing Values), chênh lệch tần số thu thập và sự bất đồng bộ thang đo giữa các biến cảm biến.

✨ Tính năng chính:

Edge Ingestion: Mô phỏng vi điều khiển ESP32 với cảm biến Nhiệt độ/Độ ẩm (DHT22) và Cảm biến khoảng cách (HC-SR04).

Reliable Transport: Truyền gói tin Telemetry theo định dạng JSON qua giao thức MQTT với EMQX Public Broker.

Dual-Bucket Storage: Thiết kế hạ tầng InfluxDB 2.7 tách biệt bucket thô (iot_raw) và bucket dữ liệu sạch (iot_processed).

Robust Preprocessing Pipeline: Lọc nhiễu Outlier theo phân vị IQR, nội suy dữ liệu rỗng (Interpolation), Resampling về chu kỳ 15 giây, làm mượt Rolling Mean (MA-3) và Chuẩn hóa Min-Max Scaler [0,1].

Realtime Monitoring App: Web App giao diện người dùng xây dựng bằng Streamlit hiển thị chỉ số Metric và biểu đồ cập nhật tự động.

2. SƠ ĐỒ KIẾN TRÚC & DATA FLOW
+------------------+         MQTT (QoS 0)        +-------------------+
|  ESP32 (Wokwi)   | --------------------------> |  EMQX MQTT Broker |
|  DHT22 + HC-SR04 |  iot/lab2/b23dccn034/...    |  broker.emqx.io   |
+------------------+                             +-------------------+
                                                           |
                                                           v
                                                 +-------------------+
                                                 | ingest_worker.py  |
                                                 +-------------------+
                                                           |
                                                           v
                                                 +-------------------+
                                                 | InfluxDB: iot_raw |
                                                 +-------------------+
                                                           |
                                                           v
                                                 +-------------------+
                                                 |preprocess_pipeline|
                                                 +-------------------+
                                                           |
                                                           v
                                                 +-------------------+
                                                 |iot_processed      |
                                                 +-------------------+
                                                           |
                                                           v
                                                 +-------------------+
                                                 | Streamlit App /   |
                                                 | Data Explorer     |
                                                 +-------------------+

3. CẤU TRÚC THƯ MỤC DỰ ÁN

IOT_TH2/
├── firmware/
│   ├── sketch.ino               # Mã nguồn C++ chạy trên ESP32 Wokwi
│   ├── diagram.json             # Sơ đồ kết nối phần cứng Wokwi
│   └── libraries.txt            # Thư viện ESP32 (PubSubClient, ArduinoJson)
├── scripts/
│   ├── ingest_worker.py         # Worker lắng nghe MQTT & ghi dữ liệu thô vào iot_raw
│   ├── preprocess_pipeline.py   # Pipeline xử lý dữ liệu (IQR, Resample, MA-3, Min-Max)
│   ├── measure_latency.py       # Script đo đạc & tính toán độ trễ End-to-End
│   └── app.py                   # Giao diện Web App giám sát realtime bằng Streamlit
├── requirements.txt             # Danh sách thư viện Python cần thiết
├── .gitignore                   # Cấu hình bỏ qua các tệp tạm của Git
└── README.md                    # Tài liệu hướng dẫn chi tiết dự án

4. MÔ TẢ CHI TIẾT CÁC MÔ-ĐUN

4.1. Firmware ESP32 (firmware/sketch.ino)

Đọc dữ liệu từ cảm biến DHT22 (Nhiệt độ, Độ ẩm) và HC-SR04 (Khoảng cách).

Đóng gói payload định dạng JSON chứa sequence, temperature, humidity, distance_cm.

Tự động inject xung nhiễu Outlier (+45∘C) định kỳ mỗi 12 chu kỳ truyền để kiểm thử thuật toán tiền xử lý.

4.2. Ingestion Worker (scripts/ingest_worker.py)

Kết nối tới Topic iot/lab2/b23dccn034/telemetry trên EMQX Broker.

Parse payload JSON và thực thi ghi dữ liệu thô vào InfluxDB bucket iot_raw dạng synchronous points.

4.3. Preprocessing Pipeline (scripts/preprocess_pipeline.py)

Truy vấn dữ liệu thô từ bucket iot_raw.

Phát hiện và triệt tiêu Outlier bằng khoảng tứ phân vị IQR (Q1−1.5⋅IQR,Q3+1.5⋅IQR).

Nội suy tuyến tính thời gian (interpolate(method='time')) cho các điểm khuyết.

Giảm tần số lưu trữ bằng Resampling cửa sổ 15 giây.

Làm mịn biến động bằng Moving Average 3 mẫu (MA-3).

Quy đồng thang đo dữ liệu về miền [0,1] qua MinMaxScaler.

Ghi dữ liệu sạch thu được vào bucket iot_processed.

4.4. Application Layer (scripts/app.py)

Xây dựng giao diện Dashboard tương tác bằng Streamlit.

Hiển thị các chỉ số đo lường sinh động (Metrics) cùng hệ thống biểu đồ so sánh dữ liệu thô và dữ liệu đã làm sạch/chuẩn hóa.

5. QUY TRÌNH TIỀN XỬ LÝ DỮ LIỆU

Phát hiện và loại bỏ triệt để các đỉnh xung nhiễu do lỗi cảm biến

Bù khuyết dữ liệu bị mất trên chuỗi thời gian liên tục

Nén tần số mẫu, giảm tải 66.7% dung lượng lưu trữ TSDB

Làm mượt tín hiệu răng cưa, làm rõ xu hướng nhiệt độ

Đưa Nhiệt độ, Độ ẩm, Khoảng cách về cùng miền không thứ nguyên $[0, 1]$

6. ĐÁNH GIÁ HIỆU NĂNG END-TO-END LATENCY

Kết quả đo đạc thực nghiệm hệ thống qua 50 mẫu truyền dẫn thực tế thu được các chỉ số tiêu chuẩn:

Số mẫu thu thập: 50 gói tin

Độ trễ tối thiểu (Min): 16.73 ms

Độ trễ trung bình (Mean): 41.50 ms

Độ trễ tối đa (Max): 64.83 ms

Độ lệch chuẩn (Std Dev): 11.04 ms

Phân vị P95 (95th Percentile): 59.08 ms

Đánh giá: Độ trễ trung bình 41.50 ms chỉ chiếm 0.83% so với chu kỳ phát tín hiệu 5000 ms của ESP32, phân vị P95 dưới 60 ms khẳng định hệ thống đạt độ ổn định tuyệt đối, không xảy ra hiện tượng tắc nghẽn bộ đệm hay trễ đường truyền.

7. HƯỚNG DẪN CÀI ĐẶT & KHỞI CHẠY

7.1. Yêu cầu môi trường

Python 3.10+

Docker Desktop (Chạy InfluxDB 2.7 Container)

Trình duyệt web (Để mở Wokwi và Streamlit Dashboard)

7.2. Cài đặt thư viện Python

pip install -r requirements.txt

7.3. Khởi chạy InfluxDB qua Docker

docker run -d -p 8086:8086 --name influxdb2 influxdb:2.7

7.4. Vận hành luồng xử lý

Bước 1: Bật mô phỏng phần cứng trên Wokwi (bấm Play).

Bước 2: Khởi chạy Ingestion Worker để nhận dữ liệu thô:

py scripts/ingest_worker.py

Bước 3: Chạy Pipeline tiền xử lý dữ liệu:

py scripts/preprocess_pipeline.py

Bước 4: Kiểm tra đo đạc độ trễ End-to-End:

py scripts/measure_latency.py

Bước 5: Mở ứng dụng giám sát Streamlit Web App:

py -m streamlit run scripts/app.py

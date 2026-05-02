# ====== IMPORT ======
import streamlit as st
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import requests
import datetime

# ====== CONFIG ======
st.set_page_config(layout="wide")

# ====== API Keys ======
OWM_API_KEY = "9becc31541efa6466c2a0c25bd05bf39"
ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImY4MzU0ZjYyOGYyMDQwNTJhMGE5MTg2MjU1MzhlZmQ3IiwiaCI6Im11cm11cjY0In0="

geolocator = Nominatim(user_agent="tnt_app")

# ====== CSS ======
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0f172a, #1e293b);
}
.header {
    background: #111827;
    padding: 18px;
    border-radius: 12px;
    color: #e5e7eb;
    font-size: 26px;
    text-align: center;
    margin-bottom: 20px;
}
.card {
    background: white;
    padding: 20px;
    border-radius: 12px;
}
.price {
    font-size: 32px;
    color: #2563eb;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ====== HEADER ======
st.markdown("<div class='header'>TNT Ride System</div>", unsafe_allow_html=True)

# ====== FUZZY ======
distance = ctrl.Antecedent(np.arange(0, 21, 1), 'distance')
traffic = ctrl.Antecedent(np.arange(0, 101, 1), 'traffic')
weather = ctrl.Antecedent(np.arange(0, 101, 1), 'weather')
multiplier = ctrl.Consequent(np.arange(1.0, 3.1, 0.1), 'multiplier')

distance['near'] = fuzz.trapmf(distance.universe, [0, 0, 2, 3])
distance['medium'] = fuzz.trimf(distance.universe, [2, 5, 8])
distance['far'] = fuzz.trapmf(distance.universe, [7, 10, 20, 20])

traffic['clear'] = fuzz.trapmf(traffic.universe, [0, 0, 20, 30])
traffic['dense'] = fuzz.trimf(traffic.universe, [20, 45, 70])
traffic['jam'] = fuzz.trapmf(traffic.universe, [60, 80, 100, 100])

weather['sunny'] = fuzz.trapmf(weather.universe, [0, 0, 20, 40])
weather['rain'] = fuzz.trimf(weather.universe, [30, 50, 70])
weather['storm'] = fuzz.trapmf(weather.universe, [60, 80, 100, 100])

multiplier['low'] = fuzz.trapmf(multiplier.universe, [1.0, 1.0, 1.1, 1.2])
multiplier['medium'] = fuzz.trimf(multiplier.universe, [1.1, 1.5, 1.8])
multiplier['high'] = fuzz.trimf(multiplier.universe, [1.6, 2.0, 2.5])
multiplier['very_high'] = fuzz.trapmf(multiplier.universe, [2.2, 2.5, 3.0, 3.0])

rule1 = ctrl.Rule(traffic['jam'] & weather['storm'], multiplier['very_high'])
rule2 = ctrl.Rule(distance['far'] & traffic['clear'], multiplier['low'])
rule3 = ctrl.Rule(traffic['dense'] & weather['sunny'], multiplier['medium'])

pricing_ctrl = ctrl.ControlSystem([rule1, rule2, rule3])
pricing_sim = ctrl.ControlSystemSimulation(pricing_ctrl)

# ====== Functions ======
def get_location(address):
    loc = geolocator.geocode(address, timeout=5)
    if loc:
        return (loc.latitude, loc.longitude)
    else:
        return None

def get_weather(lat, lon):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OWM_API_KEY}&units=metric&lang=vi"
        data = requests.get(url).json()
        desc = data['weather'][0]['description']
        temp = data['main']['temp']
        if "clear" in desc or "nắng" in desc:
            weather_val = 20
        elif "rain" in desc or "mưa" in desc:
            weather_val = 60
        elif "storm" in desc or "bão" in desc:
            weather_val = 90
        else:
            weather_val = 40
        return weather_val, f"{desc}, {temp}°C"
    except:
        return 40, "Không lấy được dữ liệu thời tiết"

def get_traffic(time_str):
    hour = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M").hour
    if 7 <= hour <= 9 or 17 <= hour <= 19:
        return 80, "Giờ cao điểm, kẹt xe"
    else:
        return 30, "Đường thoáng"

def get_route(start, end):
    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"

    headers = {
        "Authorization": ORS_API_KEY,
        "Content-Type": "application/json"
    }

    body = {
        "coordinates": [
            [start[1], start[0]],  # lon, lat
            [end[1], end[0]]
        ]
    }

    try:
        response = requests.post(url, json=body, headers=headers, timeout=10)

        if response.status_code != 200:
            return None, 0, 0

        data = response.json()

        if "features" not in data or len(data["features"]) == 0:
            return None, 0, 0

        feature = data["features"][0]

        # Route coordinates
        coords = feature["geometry"]["coordinates"]
        route = [(lat, lon) for lon, lat in coords]

        # Distance + duration
        props = feature["properties"]
        seg = props.get("segments", [{}])[0]

        distance_km = seg.get("distance", 0) / 1000
        duration_min = seg.get("duration", 0) / 60

        return route, distance_km, duration_min

    except:
        return None, 0, 0
# ====== SIDEBAR ======
with st.sidebar:
    st.markdown("## 📍 Nhập địa chỉ")
    start_input = st.text_input("Điểm đi", "District 10, Ho Chi Minh")
    end_input = st.text_input("Điểm đến", "Thu Duc, Ho Chi Minh")
    time_str = st.text_input("Giờ đi", "2026-04-28 21:30")
    coupon = st.text_input("Mã giảm giá")
    payment = st.selectbox("Thanh toán", ['Tiền mặt','Ví điện tử','Thẻ'])
    vehicle = st.radio("Loại xe", ['2 bánh','4 bánh'])

    if st.button("🔄 Đặt lại địa điểm"):
        st.session_state["calculated"] = False
        st.session_state["start"] = None
        st.session_state["end"] = None
        st.experimental_rerun()

    if st.button("Tính giá"):
        st.session_state["calculated"] = True
        st.session_state["start"] = start_input
        st.session_state["end"] = end_input
        st.session_state["time"] = time_str
        st.session_state["coupon"] = coupon
        st.session_state["payment"] = payment
        st.session_state["vehicle"] = vehicle

# ====== MAIN ======
if st.session_state.get("calculated", False):
    start = get_location(st.session_state["start"])
    end = get_location(st.session_state["end"])

    if not start or not end:
        st.error("❌ Không tìm thấy địa chỉ")
    else:
        route, d_km, duration = get_route(start, end)
        weather_val, weather_text = get_weather(*start)
        traffic_val, traffic_text = get_traffic(st.session_state["time"])

        pricing_sim.input['distance'] = min(d_km, 20)
        pricing_sim.input['traffic'] = traffic_val
        pricing_sim.input['weather'] = weather_val
        pricing_sim.compute()

        mult = pricing_sim.output.get('multiplier', 1.5)
        base_rate = 3000 if st.session_state["vehicle"] == "2 bánh" else 5000
        price = d_km * base_rate * mult
        price = max(price, 12000 if st.session_state["vehicle"] == "2 bánh" else 20000)

        if st.session_state["coupon"].strip().lower() == "thu20":
            price *= 0.8

        col1, col2 = st.columns([1,2])
        with col1:
            st.markdown(f"""
            <div class="card">
                <div class="price">{int(price):,} đ</div>
                <p>Khoảng cách: {round(d_km,1)} km</p>
                <p>Thời gian: {int(duration)} phút</p>
                <p>Giao thông: {traffic_text}</p>
                <p>Thời tiết: {weather_text}</p>
                <p>Thanh toán: {st.session_state["payment"]}</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            m = folium.Map(location=start, zoom_start=12)
            folium.Marker(start, tooltip="Điểm đi", icon=folium.Icon(color="green")).add_to(m)
            folium.Marker(end, tooltip="Điểm đến", icon=folium.Icon(color="red")).add_to(m)
            folium.PolyLine(route, color="blue", weight=6).add_to(m)

            # Hiển thị bản đồ trong Streamlit
            st_folium(m, width=800, height=500)

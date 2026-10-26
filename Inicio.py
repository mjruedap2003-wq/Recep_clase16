import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import random
import pandas as pd
from datetime import datetime

# 1. Configuración de la página
st.set_page_config(
    page_title="CyberSensor MQTT | Telemetría 📡",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Estilos Cyberpunk / Neón (CSS)
st.markdown("""
    <style>
    /* Fondo oscuro cibernético */
    .stApp {
        background-color: #0A0E17 !important;
        color: #E2E8F0 !important;
    }
    #MainMenu, footer, header {visibility: hidden;}

    /* Título principal con resplandor cian */
    .neon-title {
        font-size: 2.3rem;
        font-weight: 900;
        text-align: center;
        color: #00F0FF;
        text-shadow: 0 0 10px #00F0FF, 0 0 20px #00F0FF;
        margin-bottom: 0.5rem;
    }

    /* Subtítulos en azul neón */
    .cyan-sub-title {
        color: #00F0FF !important;
        font-size: 1.3rem !important;
        font-weight: 800 !important;
        text-shadow: 0 0 8px rgba(0, 240, 255, 0.6) !important;
        margin-top: 0.8rem !important;
        margin-bottom: 0.8rem !important;
    }

    /* FORZAR BARRA LATERAL OSCURA Y NEÓN */
    section[data-testid="stSidebar"] {
        background-color: #121722 !important;
        border-right: 2px solid #00F0FF !important;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown {
        color: #00F0FF !important;
        font-weight: bold !important;
        text-shadow: 0 0 5px rgba(0, 240, 255, 0.5) !important;
    }

    /* Inputs de texto y números en la barra lateral */
    div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input {
        background-color: #1A2232 !important;
        color: #00F0FF !important;
        border: 1px solid #00F0FF !important;
        border-radius: 8px !important;
    }

    /* Tarjetas de Métricas */
    div[data-testid="stMetric"] {
        background-color: #1A2232 !important;
        border: 1px solid #00F0FF !important;
        border-radius: 8px !important;
        padding: 10px !important;
        box-shadow: 0 0 10px rgba(0, 240, 255, 0.2) !important;
    }

    div[data-testid="stMetricLabel"] {
        color: #90CDF4 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #00FF66 !important;
        font-weight: bold !important;
    }

    /* Botones Neón */
    div.stButton > button, a.wokwi-link {
        width: 100%;
        background: transparent !important;
        color: #00FF66 !important;
        border: 2px solid #00FF66 !important;
        border-radius: 10px !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
        box-shadow: 0 0 10px rgba(0, 255, 102, 0.2) !important;
        transition: all 0.3s ease-in-out !important;
        text-align: center;
        display: block;
        text-decoration: none;
        padding: 10px;
    }

    div.stButton > button:hover, a.wokwi-link:hover {
        background-color: #00FF66 !important;
        color: #0A0E17 !important;
        box-shadow: 0 0 20px rgba(0, 255, 102, 0.8) !important;
    }

    /* Caja especial para el enlace de Wokwi */
    .wokwi-box {
        background: #121826;
        border: 2px solid #FF007F;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 0 15px rgba(255, 0, 127, 0.4);
        margin-bottom: 1.5rem;
    }

    /* Tarjeta contenedora de información */
    .info-card {
        background: #181E2A;
        border: 1px solid #00F0FF;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# 3. URL de Wokwi
WOKWI_URL = "https://wokwi.com/projects/477957415015216129"

# 4. Inicialización de variables de estado (Historial persistente)
if 'sensor_history' not in st.session_state:
    st.session_state.sensor_history = []

def get_mqtt_message(broker, port, topic, client_id):
    """Función para obtener un mensaje MQTT con timeout extendido e ID único"""
    message_received = {"received": False, "payload": None}
    
    # Agregar un sufijo aleatorio para evitar colisiones de clientes en el Broker
    unique_client_id = f"{client_id}_{random.randint(1000, 9999)}"
    
    def on_message(client, userdata, message):
        try:
            payload = json.loads(message.payload.decode())
            message_received["payload"] = payload
            message_received["received"] = True
        except Exception:
            # Si no es un JSON válido, guardar como texto simple
            message_received["payload"] = message.payload.decode()
            message_received["received"] = True
    
    try:
        client = mqtt.Client(client_id=unique_client_id)
        client.on_message = on_message
        client.connect(broker, port, 60)
        client.subscribe(topic)
        client.loop_start()
        
        # Esperar hasta 10 segundos para dar tiempo a que Wokwi publique
        timeout = time.time() + 10
        while not message_received["received"] and time.time() < timeout:
            time.sleep(0.1)
        
        client.loop_stop()
        client.disconnect()
        
        if message_received["received"]:
            return message_received["payload"]
        else:
            return {"error": f"No se recibió ningún dato en el tópico '{topic}'. Asegúrate de presionar PLAY en Wokwi y verificar que el tópico coincida."}
    
    except Exception as e:
        return {"error": str(e)}

# --- BARRA LATERAL: CONFIGURACIÓN MQTT ---
with st.sidebar:
    st.markdown('<div class="cyan-sub-title">⚙️ Conexión Broker MQTT</div>', unsafe_allow_html=True)
    
    broker = st.text_input('Broker MQTT', value='broker.mqttdashboard.com')
    port = st.number_input('Puerto', value=1883, min_value=1, max_value=65535)
    topic = st.text_input('Tópico', value='Sensor/THP2')
    client_id = st.text_input('ID del Cliente', value='streamlit_cyber_reader')

    st.markdown("---")
    st.markdown('<div class="cyan-sub-title">🔗 Simulación Interactiva</div>', unsafe_allow_html=True)
    st.markdown(f'<a href="{WOKWI_URL}" target="_blank" class="wokwi-link">🌐 ABRIR WOKWI PROJECT</a>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="cyan-sub-title">📊 Control de Datos</div>', unsafe_allow_html=True)
    st.metric("Total de Lecturas", len(st.session_state.sensor_history))
    
    if st.button("🗑️ Limpiar Historial"):
        st.session_state.sensor_history = []
        st.rerun()

# --- ENCABEZADO PRINCIPAL ---
st.markdown('<h1 class="neon-title">📡 CYBERSENSOR MQTT: TELEMETRÍA 🤖</h1>', unsafe_allow_html=True)

# Tarjeta destacada para el acceso directo a Wokwi
st.markdown(f"""
    <div class="wokwi-box">
        <h3 style="color: #FF007F; margin-top: 0;">🛠️ ACCESO AL CIRCUITO DEL SENSOR EN WOKWI</h3>
        <p style="color: #E2E8F0;">Accede a la simulación en tiempo real configurada en Wokwi para transmitir datos al Broker:</p>
        <a href="{WOKWI_URL}" target="_blank" class="wokwi-link" style="max-width: 350px; margin: 0 auto;">🚀 ABRIR PROYECTO WOKWI EN VIVO</a>
    </div>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="info-card">
        <p style="margin:0;">
            🌐 Captura de datos en tiempo real mediante suscripción MQTT. Cada lectura guardada genera métricas al instante, un historial cronológico y <strong>gráficas dinámicas</strong> de las variables analógicas o numéricas enviadas.
        </p>
    </div>
""", unsafe_allow_html=True)

# --- BOTÓN DE CAPTURA DE DATOS ---
if st.button('🔄 CAPTURAR DATOS DEL SENSOR', type="primary"):
    with st.spinner('🌌 Escaneando el Broker MQTT y esperando paquete del ESP32...'):
        data = get_mqtt_message(broker, int(port), topic, client_id)
        
        # Procesar si no hay error
        if isinstance(data, dict) and 'error' in data:
            st.error(f"❌ Error de conexión: {data['error']}")
        else:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Formatear el registro
            record = {"Hora": timestamp}
            if isinstance(data, dict):
                record.update(data)
            else:
                record["Valor"] = data
            
            # Guardar en el historial
            st.session_state.sensor_history.append(record)
            st.success('✅ Lectura capturada e integrada exitosamente')

# --- DESPLIEGUE DE RESULTADOS Y GRÁFICAS ---
if st.session_state.sensor_history:
    st.markdown("---")
    st.markdown('<div class="cyan-sub-title">📊 Última Lectura Recibida</div>', unsafe_allow_html=True)
    
    latest_record = st.session_state.sensor_history[-1]
    
    # Mostrar métricas del último registro
    keys = [k for k in latest_record.keys() if k != "Hora"]
    if keys:
        cols = st.columns(len(keys))
        for i, k in enumerate(keys):
            with cols[i]:
                st.metric(label=k, value=latest_record[k])

    # Convertir historial a Pandas DataFrame
    df_history = pd.DataFrame(st.session_state.sensor_history)

    # --- SECCIÓN DE GRÁFICAS ---
    st.markdown("---")
    st.markdown('<div class="cyan-sub-title">📈 Gráfica de Tendencia de los Sensores</div>', unsafe_allow_html=True)
    
    # Filtrar solo columnas numéricas para graficar
    numeric_cols = df_history.select_dtypes(include=['float64', 'int64', 'float', 'int']).columns.tolist()
    
    if numeric_cols:
        # Gráfica lineal interactiva
        chart_data = df_history.set_index("Hora")[numeric_cols]
        st.line_chart(chart_data)
    else:
        st.info("💡 Envía valores numéricos en formato JSON (ej: `{\"Temperatura\": 24.5, \"Humedad\": 60}`) para generar las gráficas automáticamente.")

    # --- TABLA DE HISTORIAL COMPLETO ---
    st.markdown("---")
    st.markdown('<div class="cyan-sub-title">📜 Historial de Registros Guardados</div>', unsafe_allow_html=True)
    st.dataframe(df_history, use_container_width=True)

import streamlit as st
import datetime
import json
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import timedelta

# --- MAQUILLAJE CSS (Ocultar marcas) ---
st.set_page_config(page_title="Barbería León", page_icon="✂️")
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- CONFIGURACIÓN ---
SCOPES = ['https://www.googleapis.com/auth/calendar']
# ¡¡IMPORTANTE!! Asegúrate de que este ID es el correcto
CALENDAR_ID = '14a68675d767a61817dac3835586bebd09c04571b241ee18b3967ba48289d6c2@group.calendar.google.com'

# Configuración del Negocio
DURACION_CITA = 45
HORA_APERTURA = 10
HORA_CIERRE = 20

def get_calendar_service():
    """Conexión Híbrida: Funciona en PC y Nube"""
    try:
        if "google_credentials" in st.secrets:
            # Usamos strict=False para evitar errores de formato al copiar
            key_dict = json.loads(st.secrets["google_credentials"], strict=False)
            creds = service_account.Credentials.from_service_account_info(
                key_dict, scopes=SCOPES)
        else:
            creds = service_account.Credentials.from_service_account_file(
                'credentials.json', scopes=SCOPES)
            
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def obtener_huecos_libres(service, fecha_elegida):
    time_min = datetime.datetime.combine(fecha_elegida, datetime.time.min).isoformat() + 'Z'
    time_max = datetime.datetime.combine(fecha_elegida, datetime.time.max).isoformat() + 'Z'

    events_result = service.events().list(
        calendarId=CALENDAR_ID, 
        timeMin=time_min, timeMax=time_max, singleEvents=True, orderBy='startTime'
    ).execute()
    eventos = events_result.get('items', [])

    huecos_posibles = []
    hora_actual = datetime.datetime.combine(fecha_elegida, datetime.time(HORA_APERTURA, 0))
    hora_fin_dia = datetime.datetime.combine(fecha_elegida, datetime.time(HORA_CIERRE, 0))

    while hora_actual + timedelta(minutes=DURACION_CITA) <= hora_fin_dia:
        huecos_posibles.append(hora_actual)
        hora_actual += timedelta(minutes=DURACION_CITA)

    huecos_libres = []
    ahora_madrid=datetime.datetime.utcnow() + timedelta(hours=1)
    for hueco in huecos_posibles:
        if hueco<ahora_madrid:
            continue
        ocupado = False
        for evento in eventos:
            start = evento['start'].get('dateTime', evento['start'].get('date'))
            if 'T' in start: 
                ev_start = datetime.datetime.fromisoformat(start).replace(tzinfo=None)
                if ev_start.hour == hueco.hour and ev_start.minute == hueco.minute:
                    ocupado = True
                    break
        if not ocupado:
            huecos_libres.append(hueco.strftime("%H:%M"))
    return huecos_libres

def crear_evento(service, nombre, telefono, fecha, hora_inicio):
    hora_start = datetime.datetime.strptime(hora_inicio, "%H:%M").time()
    inicio = datetime.datetime.combine(fecha, hora_start)
    fin = inicio + datetime.timedelta(minutes=DURACION_CITA)
    
    evento = {
        'summary': f'Corte - {nombre}',
        'description': f'Teléfono: {telefono}\nApp Web',
        'start': {'dateTime': inicio.isoformat(), 'timeZone': 'Europe/Madrid'},
        'end': {'dateTime': fin.isoformat(), 'timeZone': 'Europe/Madrid'},
    }
    service.events().insert(calendarId=CALENDAR_ID, body=evento).execute()

# --- INTERFAZ ---

# 1. ARRANCAMOS EL MOTOR (Esta es la línea que faltaba)
service = get_calendar_service()

st.markdown("<h1 style='text-align: center; color: #D4AF37;'>✂️ BARBERÍA LEÓN</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Reserva tu corte en segundos</p>", unsafe_allow_html=True)
st.divider()

col1, col2 = st.columns(2)

with col1:
    fecha = st.date_input("📅 ¿Qué día vienes?", datetime.date.today(), min_value=date.today())

huecos = []
# Ahora 'service' ya existe, así que esto funcionará
if service:
    huecos = obtener_huecos_libres(service, fecha)

with col2:
    if huecos:
        hora = st.selectbox("🕒 Horas disponibles:", huecos)
    else:
        st.warning("Sin huecos hoy")
        hora = None

nombre = st.text_input("👤 Tu Nombre:")
telefono = st.text_input("📱 Tu Teléfono:")

st.divider()

c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if st.button("CONFIRMAR RESERVA", use_container_width=True):
        if nombre and telefono and hora:
            try:
                crear_evento(service, nombre, telefono, fecha, hora)
                st.success(f"✅ ¡Hecho! Te esperamos el {fecha} a las {hora}.")
                st.toast("Reserva guardada correctamente", icon="🔥")
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("⚠️ Faltan datos.")
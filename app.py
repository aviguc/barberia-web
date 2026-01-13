import streamlit as st
import datetime
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import timedelta
import time

# --- MAQUILLAJE CSS (Ocultar marcas y mejorar estilo) ---
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
# ¡¡IMPORTANTE!! Pega aquí tu ID de calendario real
CALENDAR_ID = '14a68675d767a61817dac3835586bebd09c04571b241ee18b3967ba48289d6c2@group.calendar.google.com'

# Configuración del Negocio
DURACION_CITA = 30
HORA_APERTURA = 9
HORA_CIERRE = 21

def get_calendar_service():
    """Conexión Híbrida: Funciona en PC (archivo) y en Nube (Secrets)"""
    try:
        # INTENTO 1: ¿Estamos en la nube? Buscamos en la Caja Fuerte (Secrets)
        if "google_credentials" in st.secrets:
            # Leemos el secreto como texto y lo convertimos a diccionario
            key_dict = json.loads(st.secrets["google_credentials"], strict=False)
            creds = service_account.Credentials.from_service_account_info(
                key_dict, scopes=SCOPES)
        # INTENTO 2: ¿Estamos en el PC? Buscamos el archivo local
        else:
            creds = service_account.Credentials.from_service_account_file(
                'credentials.json', scopes=SCOPES)
            
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        st.error(f"Error de autenticación: {e}")
        return None

def obtener_huecos_libres(service, fecha_elegida):
    # Definir rango del día UTC
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
    for hueco in huecos_posibles:
        ocupado = False
        for evento in eventos:
            start = evento['start'].get('dateTime', evento['start'].get('date'))
            if 'T' in start: 
                # Convertimos a hora local (chapuza funcional para MVP)
                # OJO: En la nube esto estará en UTC. Para la V1 sirve, 
                # pero idealmente el barbero debería entender que la nube "vive" en hora universal.
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

# --- APP ---
# --- INTERFAZ MEJORADA ---
# Puedes poner aquí una URL de un logo real si tienes, o dejar el título elegante
st.markdown("<h1 style='text-align: center; color: #D4AF37;'>✂️ BARBERSHOP DISTRITO 23</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Reserva tu corte en segundos</p>", unsafe_allow_html=True)
st.divider() # Una línea separadora elegante

# Usamos columnas para que no quede todo apelotonado
col1, col2 = st.columns(2)

with col1:
    fecha = st.date_input("📅 ¿Qué día vienes?", datetime.date.today())

huecos = []
if service:
    huecos = obtener_huecos_libres(service, fecha)

with col2:
    if huecos:
        hora = st.selectbox("🕒 Horas disponibles:", huecos)
    else:
        st.warning("Sin huecos hoy")
        hora = None

# Inputs de texto más limpios
nombre = st.text_input("👤 Tu Nombre:")
telefono = st.text_input("📱 Tu Teléfono:")

st.divider()

# Botón centrado y grande (truco usando columnas vacías a los lados)
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if st.button("CONFIRMAR RESERVA", use_container_width=True):
        if nombre and telefono and hora:
            try:
                crear_evento(service, nombre, telefono, fecha, hora)
                # Mensaje elegante en vez de globos
                st.success(f"✅ ¡Hecho! Te esperamos el {fecha} a las {hora}.")
                st.toast("Reserva guardada correctamente", icon="🔥")
                time.sleep(2) # Espera un poco para que se lea
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("⚠️ Por favor, rellena nombre y teléfono.")
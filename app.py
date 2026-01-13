import streamlit as st
import datetime
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import timedelta

# --- CONFIGURACIÓN ---
SCOPES = ['https://www.googleapis.com/auth/calendar']
# ¡¡IMPORTANTE!! Pega aquí tu ID de calendario real
CALENDAR_ID = '14a68675d767a61817dac3835586bebd09c04571b241ee18b3967ba48289d6c2@group.calendar.google.com'

# Configuración del Negocio
DURACION_CITA = 45
HORA_APERTURA = 10
HORA_CIERRE = 20

def get_calendar_service():
    """Conexión Híbrida: Funciona en PC (archivo) y en Nube (Secrets)"""
    try:
        # INTENTO 1: ¿Estamos en la nube? Buscamos en la Caja Fuerte (Secrets)
        if "google_credentials" in st.secrets:
            # Leemos el secreto como texto y lo convertimos a diccionario
            key_dict = json.loads(st.secrets["google_credentials"])
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
st.set_page_config(page_title="Reserva Barbería", page_icon="✂️")
st.title("✂️ Barbería León")

fecha = st.date_input("Elige fecha:", datetime.date.today())

service = get_calendar_service()
if service:
    huecos = obtener_huecos_libres(service, fecha)
    if huecos:
        hora = st.selectbox("Horas libres:", huecos)
        nombre = st.text_input("Nombre:")
        telefono = st.text_input("Teléfono:")
        if st.button("Reservar Cita"):
            if nombre and telefono:
                crear_evento(service, nombre, telefono, fecha, hora)
                st.success(f"¡Listo! Reserva el {fecha} a las {hora}")
                st.balloons()
            else:
                st.warning("Faltan datos")
    else:
        st.info("No hay huecos libres hoy.")
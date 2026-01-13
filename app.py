import streamlit as st
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import timedelta

# --- CONFIGURACIÓN ---
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'credentials.json'
CALENDAR_ID = '14a68675d767a61817dac3835586bebd09c04571b241ee18b3967ba48289d6c2@group.calendar.google.com'  # <--- ¡VUELVE A PEGAR TU ID AQUÍ!

# Configuración del Negocio
DURACION_CITA = 45  # minutos
HORA_APERTURA = 10  # 10:00 AM
HORA_CIERRE = 20    # 08:00 PM

def get_calendar_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=creds)
    return service

def obtener_huecos_libres(service, fecha_elegida):
    # 1. Definir rango del día (de 00:00 a 23:59 en UTC para buscar todo)
    # Nota: Simplificamos usando hora local aproximada para la demo
    time_min = datetime.datetime.combine(fecha_elegida, datetime.time.min).isoformat() + 'Z'
    time_max = datetime.datetime.combine(fecha_elegida, datetime.time.max).isoformat() + 'Z'

    # 2. Preguntar a Google qué hay ocupado ese día
    events_result = service.events().list(
        calendarId=CALENDAR_ID, 
        timeMin=time_min, 
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    eventos = events_result.get('items', [])

    # 3. Generar todos los huecos teóricos del día
    huecos_posibles = []
    hora_actual = datetime.datetime.combine(fecha_elegida, datetime.time(HORA_APERTURA, 0))
    hora_fin_dia = datetime.datetime.combine(fecha_elegida, datetime.time(HORA_CIERRE, 0))

    while hora_actual + timedelta(minutes=DURACION_CITA) <= hora_fin_dia:
        huecos_posibles.append(hora_actual)
        hora_actual += timedelta(minutes=DURACION_CITA)

    # 4. Filtrar: Quitar huecos que chocan con eventos
    huecos_libres = []
    for hueco in huecos_posibles:
        hueco_fin = hueco + timedelta(minutes=DURACION_CITA)
        ocupado = False
        
        for evento in eventos:
            # Google devuelve las horas en formato texto raro, lo limpiamos
            start_str = evento['start'].get('dateTime', evento['start'].get('date'))
            # Si el evento es de todo el día (tipo "Festivo"), start_str es corto, lo ignoramos por simplicidad ahora
            if 'T' in start_str: 
                # Convertimos string de Google a objeto fecha de Python para comparar (quitando zona horaria para facilitar)
                ev_start = datetime.datetime.fromisoformat(start_str).replace(tzinfo=None)
                # Ajuste chapucero de zona horaria (Google devuelve UTC, nosotros estamos en España +1/+2)
                # Para hacerlo perfecto habría que usar librerías de zona horaria (pytz), 
                # pero para este prototipo asumimos que el calendario está bien configurado.
                
                # Lógica de choque: ¿El hueco empieza antes de que acabe el evento Y termina después de que empiece?
                # Simplificación: Si hay CUALQUIER evento a esa hora, lo marcamos ocupado.
                # Para esta demo V1, vamos a confiar en que si hay evento a las 10:00, bloquea las 10:00.
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
        'description': f'Teléfono: {telefono}\nApp',
        'start': {'dateTime': inicio.isoformat(), 'timeZone': 'Europe/Madrid'},
        'end': {'dateTime': fin.isoformat(), 'timeZone': 'Europe/Madrid'},
    }
    service.events().insert(calendarId=CALENDAR_ID, body=evento).execute()

# --- INTERFAZ ---
st.set_page_config(page_title="Reserva Barbería", page_icon="✂️")
st.title("✂️ Barbería León - Reservas")

fecha = st.date_input("¿Qué día quieres venir?", datetime.date.today())

# AQUÍ ESTÁ LA MAGIA: Cargamos huecos reales
try:
    service = get_calendar_service()
    huecos = obtener_huecos_libres(service, fecha)
except Exception as e:
    st.error(f"Error cargando calendario: {e}")
    huecos = []

if huecos:
    hora = st.selectbox("Horas disponibles:", huecos)
    nombre = st.text_input("Tu Nombre:")
    telefono = st.text_input("Tu Teléfono:")

    if st.button("Confirmar Reserva"):
        if nombre and telefono:
            try:
                crear_evento(service, nombre, telefono, fecha, hora)
                st.success(f"¡Reserva confirmada! Nos vemos el {fecha} a las {hora}.")
                st.balloons()
                # Truco: Recargar la página para que desaparezca el hueco ocupado
                st.rerun() 
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Faltan datos.")
else:
    st.warning("No quedan huecos libres para este día (o el barbero no trabaja). Prueba otra fecha.")
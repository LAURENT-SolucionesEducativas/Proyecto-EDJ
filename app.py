import streamlit as st
import json
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# --- Config ---
# IDs de las carpetas en Google Drive (reemplaza por los tuyos)
ID_CARPETA_IMAGEN = "1Y3olIluysi1Ff6dAR84WRz1OCd1PXyVu"
ID_CARPETA_RESOLUCION = "1aSHHMKQ60yCfrZ-bmvyd8lbF1DBZ2FSw"
ID_HOJA_CALCULO = "1rJreq8yxuykohuCtRkyq_rLpAUvFC0ABter51cVBQtU"

# Scopes para acceso
SCOPE = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

# --- Autenticación ---
creds_dict = json.loads(st.secrets["GOOGLE_CREDS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)

# Cliente gspread para Google Sheets
client = gspread.authorize(creds)
sheet = client.open_by_key(ID_HOJA_CALCULO).sheet1

# Servicio para Drive
drive_service = build('drive', 'v3', credentials=creds)

# --- Funciones ---
def subir_imagen_a_drive(file, carpeta_id, nombre_archivo):
    """Sube archivo a Drive en carpeta dada, devuelve URL pública."""
    file_metadata = {
        'name': nombre_archivo,
        'parents': [carpeta_id]
    }
    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.type)
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    # Hacer archivo público (opcional, para acceso público)
    drive_service.permissions().create(
        fileId=uploaded_file['id'],
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()

    # Obtener link
    url = f"https://drive.google.com/uc?id={uploaded_file['id']}"
    return url

# --- App ---
st.title("Formulario para registrar ejercicios")

with st.form("form_ejercicio", clear_on_submit=True):
    id_ejercicio = st.text_input("ID")
    curso = st.text_input("Curso")
    grado = st.text_input("Grado")
    id_docente = st.text_input("ID Docente")
    nombre_docente = st.text_input("Nombre Docente")
    tema = st.text_input("Tema")
    subtema = st.text_input("Subtema")
    enunciado = st.text_area("Enunciado")
    imagen_file = st.file_uploader("Imagen (Enunciado)", type=["png","jpg","jpeg"])
    claves = st.text_area("Claves")
    respuesta = st.text_area("Respuesta")
    nivel = st.selectbox("Nivel", ["Fácil", "Medio", "Difícil"])
    resolucion_file = st.file_uploader("Resolución (Imagen)", type=["png","jpg","jpeg"])
    tipo = st.text_input("Tipo")
    fuente = st.text_input("Fuente")
    link = st.text_input("Link")
    
    submitted = st.form_submit_button("Guardar ejercicio")

if submitted:
    # Validar que se subieron archivos
    if imagen_file is None or resolucion_file is None:
        st.error("Por favor sube ambas imágenes: Enunciado y Resolución")
    else:
        # Contar cuántos archivos hay ya en la carpeta imagen y resolución para nombrar nuevos
        # (Aquí se simplifica con 1, 2, 3... puedes mejorar para listar)
        # Nota: Para producción deberías listar archivos y evitar sobreescribir
        
        # Para imagen:
        nombre_imagen = "imagen" + id_ejercicio + "." + imagen_file.name.split(".")[-1]
        url_imagen = subir_imagen_a_drive(imagen_file, ID_CARPETA_IMAGEN, nombre_imagen)
        
        # Para resolución:
        nombre_resolucion = "resolucion" + id_ejercicio + "." + resolucion_file.name.split(".")[-1]
        url_resolucion = subir_imagen_a_drive(resolucion_file, ID_CARPETA_RESOLUCION, nombre_resolucion)
        
        # Guardar fila en Google Sheets (siguiendo tu orden de columnas)
        fila = [
            id_ejercicio, curso, grado, id_docente, nombre_docente, tema, subtema,
            enunciado, url_imagen, claves, respuesta, nivel, url_resolucion, tipo, fuente, link
        ]
        
        sheet.append_row(fila)
        st.success("Ejercicio guardado correctamente!")

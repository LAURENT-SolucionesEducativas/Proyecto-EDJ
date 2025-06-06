import streamlit as st
import json
import io
import difflib
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Cargar las credenciales desde los secretos
creds_dict = json.loads(st.secrets["GOOGLE_CREDS"])

# --- CONFIGURACIÓN ---
ID_CARPETA_IMAGEN = "1Y3olIluysi1Ff6dAR84WRz1OCd1PXyVu"
ID_CARPETA_RESOLUCION = "1aSHHMKQ60yCfrZ-bmvyd8lbF1DBZ2FSw"
ID_HOJA_CALCULO = "1rJreq8yxuykohuCtRkyq_rLpAUvFC0ABter51cVBQtU"

SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# --- AUTENTICACIÓN ---
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)

client = gspread.authorize(creds)
sheet = client.open_by_key(ID_HOJA_CALCULO).sheet1

drive_service = build('drive', 'v3', credentials=creds)

# --- FUNCIÓN PARA SUBIR IMAGEN ---
def subir_imagen_a_drive(file, carpeta_id, nombre_archivo):
    file.seek(0)
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
    drive_service.permissions().create(
        fileId=uploaded_file['id'],
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()
    url = f"https://drive.google.com/uc?id={uploaded_file['id']}"
    return url

# --- INTERFAZ STREAMLIT ---
st.title("📘 Registre sus ejercicios")

with st.form("form_ejercicio", clear_on_submit=True):
    curso = st.selectbox("Curso", ["RM", "A", "X", "G", "T", "F", "RV", "L"])
    grado = st.selectbox("Grado", ["5P", "6P", "1S", "2S", "3S", "4S", "5S"])
    id_docente = st.text_input("ID del docente")
    nombre_docente = st.text_input("Nombre del docente")
    tema = st.text_input("Tema")
    subtema = st.text_input("Subtema")
    enunciado = st.text_area("Enunciado del ejercicio")
    imagen_file = st.file_uploader("📷 Imagen del enunciado (opcional)", type=["png", "jpg", "jpeg"])
    claves = st.text_area("Claves")
    respuesta = st.text_area("Respuesta")
    nivel = st.selectbox("Nivel de dificultad", ["Muy fácil", "Fácil", "Medio", "Difícil"])
    resolucion_file = st.file_uploader("📷 Imagen de la resolución", type=["png", "jpg", "jpeg"])
    tipo = st.text_input("Tipo de ejercicio - Taxonomía de Bloom")
    fuente = st.text_input("Fuente")
    link = st.text_input("Enlace de referencia")

    submitted = st.form_submit_button("💾 Guardar ejercicio")

# --- PROCESAMIENTO ---
if submitted:
    if not curso or not grado or not tema or not subtema:
        st.error("❌ Por favor completa todos los campos obligatorios.")
    elif resolucion_file is None:
        st.error("❌ Debes subir la imagen de la resolución.")
    else:
        # Verificar similitud de enunciado
        enunciados_existentes = sheet.col_values(8)  # Columna del enunciado
        enunciado_mas_parecido = ""
        mayor_similitud = 0

        for e in enunciados_existentes:
            similitud = difflib.SequenceMatcher(None, enunciado.lower(), e.lower()).ratio()
            if similitud > mayor_similitud:
                mayor_similitud = similitud
                enunciado_mas_parecido = e

        if mayor_similitud > 0.9:
            st.warning(f"⚠️ Este enunciado es **muy similar** a uno ya registrado.\n\n"
                       f"📄 Enunciado más parecido:\n\n> *{enunciado_mas_parecido}*\n\n"
                       f"🔎 Similitud: {mayor_similitud:.2f}\n\n"
                       f"✏️ Si estás seguro que es distinto, modifica ligeramente el texto o continúa.")

        # Obtener nuevo ID
        filas = sheet.get_all_values()[1:]
        if filas:
            ultimo_id = int(filas[-1][0])
            nuevo_id = str(ultimo_id + 1)
        else:
            nuevo_id = "1"

        # Subir imagen del enunciado si existe
        url_imagen = ""
        if imagen_file is not None:
            nombre_imagen = f"imagen_{nuevo_id}.{imagen_file.name.split('.')[-1]}"
            url_imagen = subir_imagen_a_drive(imagen_file, ID_CARPETA_IMAGEN, nombre_imagen)

        # Subir imagen de resolución (obligatoria)
        nombre_resolucion = f"resolucion_{nuevo_id}.{resolucion_file.name.split('.')[-1]}"
        url_resolucion = subir_imagen_a_drive(resolucion_file, ID_CARPETA_RESOLUCION, nombre_resolucion)

        # Guardar en hoja
        fila = [
            nuevo_id, curso, grado, id_docente, nombre_docente, tema, subtema,
            enunciado, url_imagen, claves, respuesta, nivel, url_resolucion, tipo, fuente, link
        ]
        sheet.append_row(fila)
        st.success(f"✅ ¡Ejercicio guardado exitosamente con ID {nuevo_id}!")


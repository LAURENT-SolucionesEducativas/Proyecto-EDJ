import streamlit as st
import json
import io
import difflib
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from difflib import SequenceMatcher

# --- CONFIGURACIÓN ---
ID_CARPETA_IMAGEN = "1Y3olIluysi1Ff6dAR84WRz1OCd1PXyVu"
ID_CARPETA_RESOLUCION = "1aSHHMKQ60yCfrZ-bmvyd8lbF1DBZ2FSw"
ID_HOJA_CALCULO = "1rJreq8yxuykohuCtRkyq_rLpAUvFC0ABter51cVBQtU"

SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# --- AUTENTICACIÓN ---
creds_dict = json.loads(st.secrets["GOOGLE_CREDS"])
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)

client = gspread.authorize(creds)
sheet = client.open_by_key(ID_HOJA_CALCULO).sheet1
drive_service = build('drive', 'v3', credentials=creds)

# --- FUNCIONES AUXILIARES ---
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
    return f"https://drive.google.com/uc?id={uploaded_file['id']}"

def es_similar(a, b, umbral=0.9):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= umbral

# --- VARIABLES DE SESIÓN ---
if "confirmar_guardado" not in st.session_state:
    st.session_state.confirmar_guardado = False
if "datos_formulario" not in st.session_state:
    st.session_state.datos_formulario = {}

# --- FORMULARIO ---
st.title("📘 Registre sus ejercicios")
with st.form("form_ejercicio", clear_on_submit=False):
    curso = st.selectbox("Curso", ["RM", "A", "X", "G", "T", "F", "RV", "L","HU"])
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

# --- LÓGICA DE PROCESAMIENTO ---
if submitted or st.session_state.confirmar_guardado:
    datos = {
        "curso": curso,
        "grado": grado,
        "id_docente": id_docente,
        "nombre_docente": nombre_docente,
        "tema": tema,
        "subtema": subtema,
        "enunciado": enunciado,
        "imagen_file": imagen_file,
        "claves": claves,
        "respuesta": respuesta,
        "nivel": nivel,
        "resolucion_file": resolucion_file,
        "tipo": tipo,
        "fuente": fuente,
        "link": link,
    }

    # Validación básica
    if not datos["curso"] or not datos["grado"] or not datos["tema"] or not datos["subtema"]:
        st.error("❌ Por favor completa todos los campos obligatorios.")
    elif datos["resolucion_file"] is None:
        st.error("❌ Debes subir la imagen de la resolución.")
    else:
        filas = sheet.get_all_values()[1:]  # Sin encabezado
        enunciados_existentes = [fila[7] for fila in filas if len(fila) > 7]

        enunciado_similar = None
        for existente in enunciados_existentes:
            if es_similar(datos["enunciado"], existente):
                enunciado_similar = existente
                break

        if enunciado_similar and not st.session_state.confirmar_guardado:
            st.warning("⚠️ Este enunciado es muy similar a uno ya registrado:")
            st.code(enunciado_similar)
            st.info("¿Estás seguro de que deseas guardarlo de todos modos?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Sí, guardar de todos modos"):
                    st.session_state.confirmar_guardado = True
                    st.session_state.datos_formulario = datos
                    st.experimental_rerun()
            with col2:
                if st.button("❌ No, cancelar"):
                    st.session_state.confirmar_guardado = False
                    st.stop()
        else:
            if st.session_state.confirmar_guardado:
                datos = st.session_state.datos_formulario

            nuevo_id = str(int(filas[-1][0]) + 1) if filas else "1"
            url_imagen = ""
            if datos["imagen_file"] is not None:
                nombre_imagen = f"imagen_{nuevo_id}.{datos['imagen_file'].name.split('.')[-1]}"
                url_imagen = subir_imagen_a_drive(datos["imagen_file"], ID_CARPETA_IMAGEN, nombre_imagen)

            nombre_resolucion = f"resolucion_{nuevo_id}.{datos['resolucion_file'].name.split('.')[-1]}"
            url_resolucion = subir_imagen_a_drive(datos["resolucion_file"], ID_CARPETA_RESOLUCION, nombre_resolucion)

            fila = [
                nuevo_id, datos["curso"], datos["grado"], datos["id_docente"], datos["nombre_docente"], datos["tema"], datos["subtema"],
                datos["enunciado"], url_imagen, datos["claves"], datos["respuesta"], datos["nivel"], url_resolucion, datos["tipo"], datos["fuente"], datos["link"]
            ]
            sheet.append_row(fila)
            st.success(f"✅ ¡Ejercicio guardado exitosamente con ID {nuevo_id}!")

            st.session_state.confirmar_guardado = False
            st.session_state.datos_formulario = {}

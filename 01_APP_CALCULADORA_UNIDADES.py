# =====================================================
# 01_APP_ELABORACION_MATERIAS_PRIMAS.py
# VERSION 9
# ELABORACIÓN Y CÁLCULO DE MATERIAS PRIMAS
# PROYECTO CCU - ELABORACIÓN
# =====================================================

import base64
import hashlib
import json
import re
import uuid
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st


# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================

st.set_page_config(
    page_title="Elaboración de Materias Primas - CCU",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

RUTA_BASE = Path(__file__).parent
ARCHIVO_LOGO = RUTA_BASE / "CCU_LOGO.png"


# =====================================================
# ESTILOS
# =====================================================

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1180px;
    }

    header[data-testid="stHeader"] {
        background: rgba(0,0,0,0);
        height: 0rem;
    }

    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    #MainMenu,
    footer {
        visibility: hidden;
        height: 0%;
    }

    .logo-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 8px;
        width: 100%;
    }

    .logo-container img {
        max-width: 112px;
        height: auto;
        display: block;
    }

    .titulo-principal {
        text-align: center;
        font-size: 30px;
        font-weight: 800;
        color: #003865;
        margin-bottom: 2px;
        line-height: 1.2;
    }

    .subtitulo {
        text-align: center;
        font-size: 15px;
        color: #666666;
        margin-bottom: 22px;
    }

    .card {
        background-color: #FFFFFF;
        border: 1px solid #E1E4E8;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }

    .card-important {
        background-color: #FFF8E6;
        border: 1px solid #D6B656;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 14px;
    }

    .seccion {
        font-size: 19px;
        font-weight: 800;
        color: #003865;
        margin-bottom: 12px;
    }

    .mensaje-ok {
        background-color: #EAF7EA;
        border-left: 5px solid #2E7D32;
        padding: 14px 16px;
        border-radius: 8px;
        color: #1B5E20;
        font-size: 15px;
        margin: 18px 0;
    }

    .mensaje-info {
        background-color: #F4F7FA;
        border-left: 5px solid #003865;
        padding: 14px 16px;
        border-radius: 8px;
        color: #333333;
        font-size: 15px;
        margin: 18px 0;
    }

    .footer-app {
        text-align: center;
        color: #888888;
        font-size: 12px;
        margin-top: 34px;
    }

    div.stButton > button:first-child,
    div.stFormSubmitButton > button:first-child {
        width: 100%;
        background-color: #003865;
        color: white;
        font-weight: 700;
        border-radius: 8px;
        min-height: 3rem;
        border: none;
    }

    div.stDownloadButton > button:first-child {
        width: 100%;
        background-color: #006B3F;
        color: white;
        font-weight: 700;
        border-radius: 8px;
        min-height: 3rem;
        border: none;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #E1E4E8;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =====================================================
# FUNCIONES GENERALES
# =====================================================

def mostrar_logo_centrado(ruta_logo: Path, ancho_px: int = 112) -> None:
    if not ruta_logo.exists():
        return
    with ruta_logo.open("rb") as archivo:
        logo_base64 = base64.b64encode(archivo.read()).decode("utf-8")
    st.markdown(
        f'<div class="logo-container"><img src="data:image/png;base64,{logo_base64}" '
        f'style="max-width:{ancho_px}px;"></div>',
        unsafe_allow_html=True,
    )


def limpiar_texto(valor) -> str:
    if valor is None or pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.lower() in {"nan", "none", "nat"}:
        return ""
    return re.sub(r"\s+", " ", texto)


def formatear_cantidad(valor, max_decimales: int = 6) -> str:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return ""
    texto = f"{numero:.{max_decimales}f}".rstrip("0").rstrip(".")
    return "0" if texto == "-0" else texto


def nombre_archivo_seguro(texto: str) -> str:
    texto = re.sub(r'[\\/:*?"<>|]', "", str(texto))
    return re.sub(r"\s+", "_", texto.strip())


def obtener_secret(ruta: tuple[str, ...], obligatorio: bool = True, defecto=""):
    actual = st.secrets
    try:
        for clave in ruta:
            actual = actual[clave]
        return actual
    except Exception:
        if obligatorio:
            st.error("Falta configurar el secreto: " + ".".join(ruta))
            st.stop()
        return defecto


def extraer_id_drive(url: str) -> str:
    texto = limpiar_texto(url)
    patrones = [
        r"/file/d/([A-Za-z0-9_-]+)",
        r"[?&]id=([A-Za-z0-9_-]+)",
    ]
    for patron in patrones:
        coincidencia = re.search(patron, texto)
        if coincidencia:
            return coincidencia.group(1)
    raise ValueError("No se pudo obtener el ID del archivo de Google Drive.")


def crear_url_descarga_drive(url: str) -> str:
    file_id = extraer_id_drive(url)
    return f"https://drive.google.com/uc?export=download&id={file_id}"


# =====================================================
# ACCESO
# =====================================================

def verificar_acceso() -> None:
    if st.session_state.get("acceso_autorizado", False):
        return

    mostrar_logo_centrado(ARCHIVO_LOGO)
    st.markdown('<div class="titulo-principal">Acceso a la aplicación</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitulo">Proyecto CCU - Elaboración</div>', unsafe_allow_html=True)

    with st.form("form_acceso"):
        clave = st.text_input("Clave de acceso", type="password")
        ingresar = st.form_submit_button("Ingresar")

    if ingresar:
        clave_configurada = str(obtener_secret(("app", "clave_acceso")))
        hash_ingresado = hashlib.sha256(clave.encode("utf-8")).digest()
        hash_configurado = hashlib.sha256(clave_configurada.encode("utf-8")).digest()
        if hash_ingresado == hash_configurado:
            st.session_state["acceso_autorizado"] = True
            st.rerun()
        st.error("Clave incorrecta.")

    st.stop()


# =====================================================
# CARGA DE BBDD DESDE GOOGLE DRIVE
# =====================================================

@st.cache_data(ttl=600, show_spinner=False)
def cargar_bbdd_desde_drive(url_drive: str) -> pd.DataFrame:
    url_descarga = crear_url_descarga_drive(url_drive)
    solicitud = Request(
        url_descarga,
        headers={"User-Agent": "Mozilla/5.0"},
        method="GET",
    )

    try:
        with urlopen(solicitud, timeout=30) as respuesta:
            contenido = respuesta.read()
    except HTTPError as error:
        raise RuntimeError(f"Google Drive respondió HTTP {error.code}.") from error
    except URLError as error:
        raise RuntimeError(f"No fue posible descargar la BBDD: {error.reason}") from error

    if not contenido:
        raise RuntimeError("El archivo descargado desde Google Drive está vacío.")

    try:
        df = pd.read_csv(BytesIO(contenido), encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(BytesIO(contenido), encoding="latin-1")
    except Exception as error:
        raise RuntimeError(
            "No se pudo leer la BBDD como CSV. Verifica que el enlace de Drive corresponda al CSV público."
        ) from error

    df.columns = [limpiar_texto(columna) for columna in df.columns]
    columnas = [
        "Tipo de elaboración",
        "Materia prima",
        "Código",
        "Cantidad por unidad",
        "Unidad medida",
    ]
    faltantes = [columna for columna in columnas if columna not in df.columns]
    if faltantes:
        raise RuntimeError("La BBDD no contiene las columnas requeridas: " + ", ".join(faltantes))

    df = df[columnas].copy()
    for columna in ["Tipo de elaboración", "Materia prima", "Código", "Unidad medida"]:
        df[columna] = df[columna].apply(limpiar_texto)

    df["Cantidad por unidad"] = pd.to_numeric(df["Cantidad por unidad"], errors="coerce")
    df = df.dropna(subset=["Cantidad por unidad"])
    df = df[
        df["Tipo de elaboración"].ne("")
        & df["Materia prima"].ne("")
        & df["Unidad medida"].ne("")
    ].copy()

    df = df.drop_duplicates().sort_values(
        ["Tipo de elaboración", "Materia prima"],
        kind="stable",
    ).reset_index(drop=True)

    if df.empty:
        raise RuntimeError("La BBDD no contiene registros válidos.")

    return df


# =====================================================
# CÁLCULO
# =====================================================

def generar_calculo(df_bbdd: pd.DataFrame, tipo_elaboracion: str, unidades: int) -> pd.DataFrame:
    df = df_bbdd[df_bbdd["Tipo de elaboración"] == tipo_elaboracion].copy()
    if df.empty:
        raise ValueError("No existen materias primas para el tipo de elaboración seleccionado.")

    df["Número de unidades"] = int(unidades)
    df["Cantidad requerida"] = df["Cantidad por unidad"] * int(unidades)
    return df[
        [
            "Materia prima",
            "Código",
            "Cantidad por unidad",
            "Número de unidades",
            "Cantidad requerida",
            "Unidad medida",
        ]
    ].sort_values("Materia prima").reset_index(drop=True)


def crear_tabla_resultado(df_resultado: pd.DataFrame) -> pd.DataFrame:
    df = df_resultado[["Materia prima", "Código", "Cantidad requerida", "Unidad medida"]].copy()
    df["Cantidad requerida"] = df["Cantidad requerida"].apply(
        lambda valor: formatear_cantidad(valor, 6)
    )
    return df


# =====================================================
# GOOGLE SHEETS MEDIANTE APPS SCRIPT
# =====================================================

def construir_payload(
    fecha_elaboracion: date,
    tipo_elaboracion: str,
    unidades: int,
    df_resultado: pd.DataFrame,
) -> dict:
    id_registro = str(uuid.uuid4())
    detalle = []

    for _, fila in df_resultado.iterrows():
        detalle.append(
            {
                "id_registro": id_registro,
                "materia_prima": limpiar_texto(fila["Materia prima"]),
                "codigo": limpiar_texto(fila["Código"]),
                "cantidad_por_unidad": float(fila["Cantidad por unidad"]),
                "numero_unidades": int(unidades),
                "cantidad_requerida": float(fila["Cantidad requerida"]),
                "unidad_medida": limpiar_texto(fila["Unidad medida"]),
            }
        )

    return {
        "token": str(obtener_secret(("google_sheets", "token"))),
        "accion": "guardar_elaboracion_materias_primas",
        "elaboracion": {
            "id_registro": id_registro,
            "fecha": fecha_elaboracion.isoformat(),
            "tipo_elaboracion": tipo_elaboracion,
            "numero_unidades": int(unidades),
            "fecha_registro": datetime.now().isoformat(timespec="seconds"),
        },
        "detalle": detalle,
    }


def enviar_a_google_sheets(payload: dict) -> dict:
    url = limpiar_texto(obtener_secret(("google_sheets", "apps_script_url")))
    if not url.startswith("https://script.google.com/"):
        raise ValueError("Configura una URL válida de Apps Script en google_sheets.apps_script_url.")

    solicitud = Request(
        url=url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urlopen(solicitud, timeout=30) as respuesta:
            contenido = respuesta.read().decode("utf-8")
    except HTTPError as error:
        detalle = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google respondió HTTP {error.code}: {detalle[:250]}") from error
    except URLError as error:
        raise RuntimeError(f"No fue posible conectar con Google Sheets: {error.reason}") from error

    try:
        resultado = json.loads(contenido)
    except json.JSONDecodeError as error:
        raise RuntimeError("Apps Script devolvió una respuesta no válida.") from error

    if not resultado.get("ok", False):
        raise RuntimeError(resultado.get("mensaje", "Apps Script rechazó el registro."))
    return resultado


# =====================================================
# EXPORTACIÓN OPCIONAL A EXCEL
# =====================================================

def convertir_excel(
    df_resultado: pd.DataFrame,
    tipo_elaboracion: str,
    fecha_elaboracion: date,
    unidades: int,
) -> BytesIO:
    salida = BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        df_resultado.to_excel(writer, index=False, sheet_name="Materias primas")
        hoja = writer.sheets["Materias primas"]
        hoja.insert_rows(1, 4)
        hoja["A1"] = "Elaboración de Materias Primas - CCU"
        hoja["A2"] = f"Fecha: {fecha_elaboracion.strftime('%d-%m-%Y')}"
        hoja["A3"] = f"Tipo de elaboración: {tipo_elaboracion}"
        hoja["A4"] = f"Número de unidades: {unidades}"
        hoja.freeze_panes = "A6"
        hoja.auto_filter.ref = hoja.dimensions

        for columna in hoja.columns:
            letra = columna[0].column_letter
            ancho = max(len(str(celda.value or "")) for celda in columna) + 2
            hoja.column_dimensions[letra].width = min(max(ancho, 12), 45)

    salida.seek(0)
    return salida


# =====================================================
# INICIO
# =====================================================

verificar_acceso()

url_bbdd = str(obtener_secret(("fuentes", "bbdd_materias_primas_url")))
url_excel = str(obtener_secret(("google_sheets", "spreadsheet_url")))

try:
    df_bbdd = cargar_bbdd_desde_drive(url_bbdd)
except Exception as error:
    st.error(f"No fue posible cargar la BBDD de materias primas: {error}")
    st.stop()

mostrar_logo_centrado(ARCHIVO_LOGO)
st.markdown('<div class="titulo-principal">Elaboración de Materias Primas</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitulo">Proyecto CCU - Elaboración | Cálculo y registro</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.caption(f"BBDD cargada: {len(df_bbdd)} materias primas")
    st.link_button("Abrir Google Sheets", url_excel)
    if st.button("Actualizar BBDD"):
        cargar_bbdd_desde_drive.clear()
        st.rerun()
    if st.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()


# =====================================================
# FORMULARIO PREGUNTA / RESPUESTA
# =====================================================

st.markdown('<div class="card-important">', unsafe_allow_html=True)
st.markdown('<div class="seccion">Datos de la elaboración</div>', unsafe_allow_html=True)

with st.form("form_elaboracion", clear_on_submit=False):
    fecha_elaboracion = st.date_input(
        "¿Cuál es la fecha de elaboración?",
        value=st.session_state.get("fecha_elaboracion", date.today()),
        format="DD-MM-YYYY",
    )

    tipos = sorted(df_bbdd["Tipo de elaboración"].dropna().unique().tolist())
    tipo_elaboracion = st.selectbox(
        "¿Cuál es el tipo de elaboración?",
        options=tipos,
    )

    numero_unidades = st.number_input(
        "¿Cuál es el número de unidades?",
        min_value=1,
        value=int(st.session_state.get("numero_unidades", 1)),
        step=1,
    )

    calcular = st.form_submit_button("Calcular materias primas")

st.markdown("</div>", unsafe_allow_html=True)

if calcular:
    try:
        st.session_state["fecha_elaboracion"] = fecha_elaboracion
        st.session_state["tipo_elaboracion"] = tipo_elaboracion
        st.session_state["numero_unidades"] = int(numero_unidades)
        st.session_state["df_resultado"] = generar_calculo(
            df_bbdd,
            tipo_elaboracion,
            int(numero_unidades),
        )
    except Exception as error:
        st.error(str(error))


# =====================================================
# RESULTADO Y GUARDADO
# =====================================================

if "df_resultado" in st.session_state:
    df_resultado = st.session_state["df_resultado"]
    fecha_elaboracion = st.session_state["fecha_elaboracion"]
    tipo_elaboracion = st.session_state["tipo_elaboracion"]
    numero_unidades = st.session_state["numero_unidades"]

    st.markdown(
        f"""
        <div class="mensaje-ok">
            <b>Cálculo generado correctamente.</b><br>
            Fecha: <b>{fecha_elaboracion.strftime('%d-%m-%Y')}</b><br>
            Tipo de elaboración: <b>{tipo_elaboracion}</b><br>
            Número de unidades: <b>{numero_unidades}</b><br>
            Materias primas calculadas: <b>{len(df_resultado)}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="seccion">Materias primas requeridas</div>', unsafe_allow_html=True)
    st.dataframe(
        crear_tabla_resultado(df_resultado),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Materia prima": st.column_config.TextColumn(width="large"),
            "Código": st.column_config.TextColumn(width="medium"),
            "Cantidad requerida": st.column_config.TextColumn(width="medium"),
            "Unidad medida": st.column_config.TextColumn(width="small"),
        },
    )

    with st.expander("Ver cantidad por unidad"):
        detalle = df_resultado.copy()
        detalle["Cantidad por unidad"] = detalle["Cantidad por unidad"].apply(
            lambda valor: formatear_cantidad(valor, 6)
        )
        detalle["Cantidad requerida"] = detalle["Cantidad requerida"].apply(
            lambda valor: formatear_cantidad(valor, 6)
        )
        st.dataframe(detalle, use_container_width=True, hide_index=True)

    columna_guardar, columna_descargar = st.columns(2)

    with columna_guardar:
        guardar = st.button("Guardar registro en Google Sheets", type="primary")

    with columna_descargar:
        archivo_excel = convertir_excel(
            df_resultado,
            tipo_elaboracion,
            fecha_elaboracion,
            numero_unidades,
        )
        nombre_excel = (
            "ELABORACION_MP_"
            + nombre_archivo_seguro(tipo_elaboracion)
            + "_"
            + fecha_elaboracion.strftime("%Y%m%d")
            + ".xlsx"
        )
        st.download_button(
            "Descargar cálculo en Excel",
            data=archivo_excel,
            file_name=nombre_excel,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    if guardar:
        try:
            payload = construir_payload(
                fecha_elaboracion,
                tipo_elaboracion,
                numero_unidades,
                df_resultado,
            )
            with st.spinner("Guardando registro..."):
                respuesta = enviar_a_google_sheets(payload)
            id_registro = respuesta.get(
                "id_registro",
                payload["elaboracion"]["id_registro"],
            )
            st.success(f"Registro guardado correctamente. ID: {id_registro}")
        except Exception as error:
            st.error(f"No fue posible guardar el registro: {error}")

    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.markdown(
        """
        <div class="mensaje-info">
            Responde las tres preguntas y presiona <b>Calcular materias primas</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="footer-app">
        Proyecto CCU - Elaboración | BBDD CSV en Google Drive + Google Sheets
    </div>
    """,
    unsafe_allow_html=True,
)

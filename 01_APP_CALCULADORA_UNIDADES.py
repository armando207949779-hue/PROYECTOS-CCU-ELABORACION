import base64
import hashlib
import json
import re
from datetime import date
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Elaboración de Materias Primas - CCU",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

RUTA_BASE = Path(__file__).parent
ARCHIVO_LOGO = RUTA_BASE / "CCU_LOGO.png"

st.markdown(
    """
    <style>
    .block-container {padding-top:1rem; padding-bottom:2rem; max-width:1250px;}
    header[data-testid="stHeader"] {background:rgba(0,0,0,0); height:0rem;}
    div[data-testid="stToolbar"], div[data-testid="stDecoration"],
    #MainMenu, footer {visibility:hidden; height:0%;}
    .logo-container {display:flex; justify-content:center; margin-bottom:8px;}
    .titulo-principal {text-align:center; font-size:30px; font-weight:800; color:#003865;}
    .subtitulo {text-align:center; font-size:15px; color:#666; margin-bottom:22px;}
    .card, .card-important {border-radius:12px; padding:18px; margin-bottom:14px;}
    .card {background:#fff; border:1px solid #E1E4E8;}
    .card-important {background:#FFF8E6; border:1px solid #D6B656;}
    .seccion {font-size:19px; font-weight:800; color:#003865; margin-bottom:12px;}
    .mensaje-ok {background:#EAF7EA; border-left:5px solid #2E7D32; padding:14px 16px; border-radius:8px; color:#1B5E20; margin:18px 0;}
    .mensaje-info {background:#F4F7FA; border-left:5px solid #003865; padding:14px 16px; border-radius:8px; color:#333; margin:18px 0;}
    .footer-app {text-align:center; color:#888; font-size:12px; margin-top:34px;}
    div.stButton > button:first-child,
    div.stFormSubmitButton > button:first-child {width:100%; background:#003865; color:white; font-weight:700; border-radius:8px; min-height:3rem; border:none;}
    div.stDownloadButton > button:first-child {width:100%; background:#006B3F; color:white; font-weight:700; border-radius:8px; min-height:3rem; border:none;}
    </style>
    """,
    unsafe_allow_html=True,
)


def limpiar_texto(valor) -> str:
    if valor is None or pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.lower() in {"nan", "none", "nat"}:
        return ""
    return re.sub(r"\s+", " ", texto)


def mostrar_logo() -> None:
    if not ARCHIVO_LOGO.exists():
        return
    contenido = base64.b64encode(ARCHIVO_LOGO.read_bytes()).decode("utf-8")
    st.markdown(
        f'<div class="logo-container"><img src="data:image/png;base64,{contenido}" style="max-width:112px;"></div>',
        unsafe_allow_html=True,
    )


def obtener_secret(ruta: tuple[str, ...]):
    valor = st.secrets
    try:
        for clave in ruta:
            valor = valor[clave]
        return valor
    except Exception:
        st.error("Falta configurar el secreto: " + ".".join(ruta))
        st.stop()


def extraer_id_drive(url: str) -> str:
    for patron in (r"/file/d/([A-Za-z0-9_-]+)", r"[?&]id=([A-Za-z0-9_-]+)"):
        coincidencia = re.search(patron, limpiar_texto(url))
        if coincidencia:
            return coincidencia.group(1)
    raise ValueError("No se pudo obtener el ID del archivo de Google Drive.")


def verificar_acceso() -> None:
    if st.session_state.get("acceso_autorizado"):
        return
    mostrar_logo()
    st.markdown('<div class="titulo-principal">Acceso a la aplicación</div>', unsafe_allow_html=True)
    with st.form("acceso"):
        clave = st.text_input("Clave de acceso", type="password")
        ingresar = st.form_submit_button("Ingresar")
    if ingresar:
        configurada = str(obtener_secret(("app", "clave_acceso")))
        if hashlib.sha256(clave.encode()).digest() == hashlib.sha256(configurada.encode()).digest():
            st.session_state["acceso_autorizado"] = True
            st.rerun()
        st.error("Clave incorrecta.")
    st.stop()


@st.cache_data(ttl=600, show_spinner=False)
def cargar_bbdd(url_drive: str) -> pd.DataFrame:
    file_id = extraer_id_drive(url_drive)
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    solicitud = Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="GET")
    try:
        with urlopen(solicitud, timeout=30) as respuesta:
            contenido = respuesta.read()
    except HTTPError as error:
        raise RuntimeError(f"Google Drive respondió HTTP {error.code}.") from error
    except URLError as error:
        raise RuntimeError(f"No fue posible descargar la BBDD: {error.reason}") from error

    try:
        df = pd.read_csv(BytesIO(contenido), encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(BytesIO(contenido), encoding="latin-1")

    df.columns = [limpiar_texto(c) for c in df.columns]
    columnas = ["Tipo de elaboración", "Materia prima", "Código", "Cantidad por unidad", "Unidad medida"]
    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        raise RuntimeError("Faltan columnas en la BBDD: " + ", ".join(faltantes))

    df = df[columnas].copy()
    for columna in ["Tipo de elaboración", "Materia prima", "Código", "Unidad medida"]:
        df[columna] = df[columna].apply(limpiar_texto)
    df["Cantidad por unidad"] = pd.to_numeric(df["Cantidad por unidad"], errors="coerce")
    df = df.dropna(subset=["Cantidad por unidad"])
    df = df[df["Tipo de elaboración"].ne("") & df["Materia prima"].ne("")]
    return df.drop_duplicates().sort_values(["Tipo de elaboración", "Materia prima"]).reset_index(drop=True)


def generar_calculo(df_bbdd: pd.DataFrame, sabor: str, unidades: int) -> pd.DataFrame:
    df = df_bbdd[df_bbdd["Tipo de elaboración"] == sabor].copy()
    if df.empty:
        raise ValueError("No existen materias primas para el sabor seleccionado.")
    df["Cantidad requerida"] = df["Cantidad por unidad"] * int(unidades)
    return df[["Materia prima", "Código", "Cantidad por unidad", "Cantidad requerida", "Unidad medida"]].sort_values("Materia prima").reset_index(drop=True)


def construir_payload(fecha, orden, unidades, destino, sabor, turno, df_resultado):
    materias = []
    for _, fila in df_resultado.iterrows():
        materias.append({
            "materia_prima": limpiar_texto(fila["Materia prima"]),
            "codigo": limpiar_texto(fila["Código"]),
            "unidad_medida": limpiar_texto(fila["Unidad medida"]),
            "cantidad_requerida": float(fila["Cantidad requerida"]),
        })
    return {
        "token": str(obtener_secret(("google_sheets", "token"))),
        "accion": "guardar_elaboracion_horizontal",
        "registro": {
            "fecha": fecha.strftime("%d-%m-%Y"),
            "orden_elaboracion": limpiar_texto(orden),
            "unidades": int(unidades),
            "destino": limpiar_texto(destino),
            "sabor": limpiar_texto(sabor),
            "turno": limpiar_texto(turno),
        },
        "materias_primas": materias,
    }


def enviar_a_google_sheets(payload: dict) -> dict:
    url = limpiar_texto(obtener_secret(("google_sheets", "apps_script_url")))
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
    if not resultado.get("ok"):
        raise RuntimeError(resultado.get("mensaje", "Apps Script rechazó el registro."))
    return resultado



verificar_acceso()

url_bbdd = str(obtener_secret(("fuentes", "bbdd_materias_primas_url")))
url_sheet = str(obtener_secret(("google_sheets", "spreadsheet_url")))

try:
    df_bbdd = cargar_bbdd(url_bbdd)
except Exception as error:
    st.error(f"No fue posible cargar la BBDD: {error}")
    st.stop()

mostrar_logo()
st.markdown('<div class="titulo-principal">Elaboración de Materias Primas</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo">Registro horizontal por orden de elaboración</div>', unsafe_allow_html=True)

with st.sidebar:
    st.caption(f"BBDD cargada: {len(df_bbdd)} registros")
    st.link_button("Abrir Google Sheets", url_sheet)
    if st.button("Actualizar BBDD"):
        cargar_bbdd.clear()
        st.rerun()
    if st.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()

st.markdown('<div class="card-important">', unsafe_allow_html=True)
st.markdown('<div class="seccion">Datos de la elaboración</div>', unsafe_allow_html=True)

with st.form("form_elaboracion", clear_on_submit=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        fecha = st.date_input("Fecha", value=st.session_state.get("fecha", date.today()), format="DD-MM-YYYY")
        orden = st.text_input("Orden de elaboración", value=st.session_state.get("orden", ""), placeholder="Ejemplo: 7100054657")
    with c2:
        sabores = sorted(df_bbdd["Tipo de elaboración"].dropna().unique().tolist())
        sabor_previo = st.session_state.get("sabor")
        indice_sabor = sabores.index(sabor_previo) if sabor_previo in sabores else 0
        sabor = st.selectbox("Sabor / tipo de elaboración", options=sabores, index=indice_sabor)
        unidades = st.number_input("Número de unidades", min_value=1, value=int(st.session_state.get("unidades", 1)), step=1)
    with c3:
        destinos = ["Jarabe 1", "Jarabe 2"]
        destino_previo = st.session_state.get("destino", "Jarabe 1")
        indice_destino = destinos.index(destino_previo) if destino_previo in destinos else 0
        destino = st.selectbox("Destino", options=destinos, index=indice_destino)
        turnos = ["A", "B", "C"]
        turno_previo = st.session_state.get("turno", "A")
        turno = st.selectbox("Turno", options=turnos, index=turnos.index(turno_previo))
    calcular = st.form_submit_button("Calcular materias primas")

st.markdown("</div>", unsafe_allow_html=True)

if calcular:
    errores = []
    if not limpiar_texto(orden):
        errores.append("Ingresa la orden de elaboración.")
    if errores:
        for error in errores:
            st.error(error)
    else:
        try:
            st.session_state.update({
                "fecha": fecha,
                "orden": limpiar_texto(orden),
                "unidades": int(unidades),
                "destino": limpiar_texto(destino),
                "sabor": sabor,
                "turno": turno,
                "df_resultado": generar_calculo(df_bbdd, sabor, int(unidades)),
            })
        except Exception as error:
            st.error(str(error))

if "df_resultado" in st.session_state:
    resultado = st.session_state["df_resultado"]
    fecha = st.session_state["fecha"]
    orden = st.session_state["orden"]
    unidades = st.session_state["unidades"]
    destino = st.session_state["destino"]
    sabor = st.session_state["sabor"]
    turno = st.session_state["turno"]

    st.markdown(
        f'<div class="mensaje-ok"><b>Cálculo generado.</b><br>'
        f'Fecha: <b>{fecha.strftime("%d-%m-%Y")}</b> | Orden: <b>{orden}</b> | '
        f'Unidades: <b>{unidades}</b> | Destino: <b>{destino}</b> | '
        f'Sabor: <b>{sabor}</b> | Turno: <b>{turno}</b></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="seccion">Materias primas requeridas</div>', unsafe_allow_html=True)
    mostrar = resultado[["Materia prima", "Código", "Cantidad requerida", "Unidad medida"]].copy()
    mostrar["Cantidad requerida"] = mostrar["Cantidad requerida"].map(lambda x: f"{float(x):.6f}".rstrip("0").rstrip("."))
    st.dataframe(mostrar, use_container_width=True, hide_index=True)

    guardar = st.button(
        "Guardar registro en Google Sheets",
        type="primary",
        use_container_width=True,
    )

    if guardar:
        try:
            payload = construir_payload(fecha, orden, unidades, destino, sabor, turno, resultado)
            with st.spinner("Guardando registro..."):
                respuesta = enviar_a_google_sheets(payload)
            st.success(f"Registro guardado correctamente en la fila {respuesta.get('fila', '')}.")
        except Exception as error:
            st.error(f"No fue posible guardar el registro: {error}")

    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.markdown('<div class="mensaje-info">Completa los datos y presiona <b>Calcular materias primas</b>.</div>', unsafe_allow_html=True)

st.markdown('<div class="footer-app">Proyecto CCU - Elaboración</div>', unsafe_allow_html=True)

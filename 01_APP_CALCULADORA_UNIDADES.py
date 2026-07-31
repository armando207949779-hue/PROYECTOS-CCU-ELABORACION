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
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

RUTA_BASE = Path(__file__).parent
ARCHIVO_LOGO = RUTA_BASE / "CCU_LOGO.png"

st.markdown(
    """
    <style>
    :root {
        --ccu-blue: #003865;
        --ccu-blue-soft: #EAF1F6;
        --ccu-gold: #D9A928;
        --text: #1F2933;
        --muted: #6B7280;
        --line: #E5E7EB;
        --surface: #FFFFFF;
        --success: #1F7A4D;
    }

    .stApp {background: #F7F9FB;}
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2rem;
        max-width: 1180px;
    }

    header[data-testid="stHeader"] {background: transparent; height: 0;}
    div[data-testid="stToolbar"],
    div[data-testid="stDecoration"],
    #MainMenu,
    footer {visibility: hidden; height: 0;}

    .app-header {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 16px;
        margin: 2px 0 24px;
    }
    .app-logo img {max-width: 86px; display: block;}
    .app-title {
        font-size: 30px;
        line-height: 1.15;
        font-weight: 800;
        color: var(--ccu-blue);
        letter-spacing: -0.4px;
    }

    .panel {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 18px;
        box-shadow: 0 4px 14px rgba(0, 56, 101, 0.05);
    }
    .panel-title {
        font-size: 18px;
        font-weight: 800;
        color: var(--ccu-blue);
        margin-bottom: 4px;
    }
    .panel-help {
        font-size: 13px;
        color: var(--muted);
        margin-bottom: 16px;
    }

    .summary {
        background: var(--ccu-blue-soft);
        border: 1px solid #D4E2ED;
        border-radius: 14px;
        padding: 14px 16px;
        margin: 16px 0;
    }
    .summary-title {
        color: var(--ccu-blue);
        font-weight: 800;
        margin-bottom: 8px;
    }
    .summary-grid {
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 10px;
    }
    .summary-item {
        background: rgba(255,255,255,0.72);
        border-radius: 10px;
        padding: 10px;
        min-width: 0;
    }
    .summary-label {
        display: block;
        color: var(--muted);
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .35px;
        margin-bottom: 3px;
    }
    .summary-value {
        display: block;
        color: var(--text);
        font-size: 14px;
        font-weight: 700;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .empty-state {
        text-align: center;
        background: #FFFFFF;
        border: 1px dashed #CAD5DE;
        border-radius: 14px;
        padding: 22px;
        color: var(--muted);
        margin-top: 16px;
    }

    .footer-app {
        text-align: center;
        color: #9AA3AB;
        font-size: 12px;
        margin-top: 28px;
    }

    div.stButton > button:first-child,
    div.stFormSubmitButton > button:first-child {
        width: 100%;
        background: var(--ccu-blue);
        color: white;
        font-weight: 750;
        border-radius: 10px;
        min-height: 3rem;
        border: 1px solid var(--ccu-blue);
        box-shadow: none;
    }
    div.stButton > button:first-child:hover,
    div.stFormSubmitButton > button:first-child:hover {
        background: #002C50;
        border-color: #002C50;
        color: white;
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div {
        border-radius: 10px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 12px;
        overflow: hidden;
    }

    @media (max-width: 900px) {
        .summary-grid {grid-template-columns: repeat(2, minmax(0, 1fr));}
        .app-header {flex-direction: column; gap: 8px; text-align: center;}
        .app-title {font-size: 26px;}
    }
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


def logo_base64() -> str:
    if not ARCHIVO_LOGO.exists():
        return ""
    return base64.b64encode(ARCHIVO_LOGO.read_bytes()).decode("utf-8")


def mostrar_encabezado() -> None:
    contenido = logo_base64()
    logo_html = (
        f'<div class="app-logo"><img src="data:image/png;base64,{contenido}"></div>'
        if contenido
        else ""
    )
    st.markdown(
        f"""
        <div class="app-header">
            {logo_html}
            <div class="app-title">Elaboración de Materias Primas</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mostrar_logo_acceso() -> None:
    contenido = logo_base64()
    if contenido:
        st.markdown(
            f'<div style="display:flex;justify-content:center;margin:8px 0 16px;">'
            f'<img src="data:image/png;base64,{contenido}" style="max-width:96px;"></div>',
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

    mostrar_logo_acceso()
    st.markdown(
        '<div style="text-align:center;font-size:28px;font-weight:800;color:#003865;margin-bottom:18px;">Acceso</div>',
        unsafe_allow_html=True,
    )

    _, centro, _ = st.columns([1, 1.15, 1])
    with centro:
        with st.form("acceso"):
            clave = st.text_input("Clave de acceso", type="password", placeholder="Ingresa tu clave")
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
    columnas = [
        "Tipo de elaboración",
        "Materia prima",
        "Código",
        "Cantidad por unidad",
        "Unidad medida",
    ]
    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        raise RuntimeError("Faltan columnas en la BBDD: " + ", ".join(faltantes))

    df = df[columnas].copy()
    for columna in ["Tipo de elaboración", "Materia prima", "Código", "Unidad medida"]:
        df[columna] = df[columna].apply(limpiar_texto)

    df["Cantidad por unidad"] = pd.to_numeric(df["Cantidad por unidad"], errors="coerce")
    df = df.dropna(subset=["Cantidad por unidad"])
    df = df[df["Tipo de elaboración"].ne("") & df["Materia prima"].ne("")]

    return (
        df.drop_duplicates()
        .sort_values(["Tipo de elaboración", "Materia prima"])
        .reset_index(drop=True)
    )


def generar_calculo(df_bbdd: pd.DataFrame, sabor: str, unidades: int) -> pd.DataFrame:
    df = df_bbdd[df_bbdd["Tipo de elaboración"] == sabor].copy()
    if df.empty:
        raise ValueError("No existen materias primas para el sabor seleccionado.")

    df["Cantidad requerida"] = df["Cantidad por unidad"] * int(unidades)
    return (
        df[
            [
                "Materia prima",
                "Código",
                "Cantidad por unidad",
                "Cantidad requerida",
                "Unidad medida",
            ]
        ]
        .sort_values("Materia prima")
        .reset_index(drop=True)
    )


def construir_payload(fecha, orden, unidades, destino, sabor, turno, df_resultado):
    materias = []
    for _, fila in df_resultado.iterrows():
        materias.append(
            {
                "materia_prima": limpiar_texto(fila["Materia prima"]),
                "codigo": limpiar_texto(fila["Código"]),
                "unidad_medida": limpiar_texto(fila["Unidad medida"]),
                "cantidad_requerida": float(fila["Cantidad requerida"]),
            }
        )

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

mostrar_encabezado()

with st.sidebar:
    st.markdown("### Herramientas")
    st.caption(f"BBDD disponible: {len(df_bbdd)} registros")
    st.link_button("Abrir Google Sheets", url_sheet, use_container_width=True)

    if st.button("Actualizar BBDD", use_container_width=True):
        cargar_bbdd.clear()
        st.rerun()

    if st.button("Cerrar sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown('<div class="panel-title">Datos de la elaboración</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="panel-help">Completa los campos y calcula las materias primas requeridas.</div>',
    unsafe_allow_html=True,
)

with st.form("form_elaboracion", clear_on_submit=False):
    fila_1 = st.columns([1, 1.35, 1.35])
    with fila_1[0]:
        fecha = st.date_input(
            "Fecha",
            value=st.session_state.get("fecha", date.today()),
            format="DD-MM-YYYY",
        )
    with fila_1[1]:
        orden = st.text_input(
            "Orden de elaboración",
            value=st.session_state.get("orden", ""),
            placeholder="Ej.: 7100054657",
        )
    with fila_1[2]:
        sabores = sorted(df_bbdd["Tipo de elaboración"].dropna().unique().tolist())
        sabor_previo = st.session_state.get("sabor")
        indice_sabor = sabores.index(sabor_previo) if sabor_previo in sabores else 0
        sabor = st.selectbox("Sabor / tipo de elaboración", options=sabores, index=indice_sabor)

    fila_2 = st.columns(3)
    with fila_2[0]:
        unidades = st.number_input(
            "Número de unidades",
            min_value=1,
            value=int(st.session_state.get("unidades", 1)),
            step=1,
        )
    with fila_2[1]:
        destinos = ["Jarabe 1", "Jarabe 2"]
        destino_previo = st.session_state.get("destino", "Jarabe 1")
        indice_destino = destinos.index(destino_previo) if destino_previo in destinos else 0
        destino = st.selectbox("Destino", options=destinos, index=indice_destino)
    with fila_2[2]:
        turnos = ["A", "B", "C"]
        turno_previo = st.session_state.get("turno", "A")
        indice_turno = turnos.index(turno_previo) if turno_previo in turnos else 0
        turno = st.selectbox("Turno", options=turnos, index=indice_turno)

    calcular = st.form_submit_button("Calcular materias primas")

st.markdown("</div>", unsafe_allow_html=True)

if calcular:
    if not limpiar_texto(orden):
        st.error("Ingresa la orden de elaboración.")
    else:
        try:
            st.session_state.update(
                {
                    "fecha": fecha,
                    "orden": limpiar_texto(orden),
                    "unidades": int(unidades),
                    "destino": limpiar_texto(destino),
                    "sabor": sabor,
                    "turno": turno,
                    "df_resultado": generar_calculo(df_bbdd, sabor, int(unidades)),
                }
            )
            st.rerun()
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
        f"""
        <div class="summary">
            <div class="summary-title">Resumen de la elaboración</div>
            <div class="summary-grid">
                <div class="summary-item"><span class="summary-label">Fecha</span><span class="summary-value">{fecha.strftime('%d-%m-%Y')}</span></div>
                <div class="summary-item"><span class="summary-label">Orden</span><span class="summary-value">{orden}</span></div>
                <div class="summary-item"><span class="summary-label">Unidades</span><span class="summary-value">{unidades}</span></div>
                <div class="summary-item"><span class="summary-label">Destino</span><span class="summary-value">{destino}</span></div>
                <div class="summary-item"><span class="summary-label">Sabor</span><span class="summary-value">{sabor}</span></div>
                <div class="summary-item"><span class="summary-label">Turno</span><span class="summary-value">{turno}</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Materias primas requeridas</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="panel-help">{len(resultado)} materias primas calculadas para esta elaboración.</div>',
        unsafe_allow_html=True,
    )

    mostrar = resultado[["Materia prima", "Código", "Cantidad requerida", "Unidad medida"]].copy()
    mostrar["Cantidad requerida"] = mostrar["Cantidad requerida"].map(
        lambda x: f"{float(x):.6f}".rstrip("0").rstrip(".")
    )

    st.dataframe(
        mostrar,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Materia prima": st.column_config.TextColumn("Materia prima", width="large"),
            "Código": st.column_config.TextColumn("Código", width="small"),
            "Cantidad requerida": st.column_config.TextColumn("Cantidad", width="small"),
            "Unidad medida": st.column_config.TextColumn("Unidad", width="small"),
        },
    )

    guardar = st.button(
        "Guardar elaboración",
        type="primary",
        use_container_width=True,
    )

    if guardar:
        try:
            payload = construir_payload(fecha, orden, unidades, destino, sabor, turno, resultado)
            with st.spinner("Guardando elaboración..."):
                respuesta = enviar_a_google_sheets(payload)
            fila_guardada = respuesta.get("fila")
            mensaje = "Elaboración guardada correctamente."
            if fila_guardada:
                mensaje += f" Fila {fila_guardada}."
            st.success(mensaje)
        except Exception as error:
            st.error(f"No fue posible guardar el registro: {error}")

    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.markdown(
        '<div class="empty-state">Completa los datos de la elaboración para ver el cálculo.</div>',
        unsafe_allow_html=True,
    )

st.markdown('<div class="footer-app">CCU · Elaboración de Materias Primas</div>', unsafe_allow_html=True)

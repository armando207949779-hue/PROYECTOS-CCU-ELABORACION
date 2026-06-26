# =====================================================
# 01_APP_CALCULADORA_UNIDADES.py
# VERSION 3
# APP CALCULADORA DE MATERIAS PRIMAS POR UNIDADES
# PROYECTO CCU - ELABORACIÓN
# =====================================================

import base64
from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st


# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================

st.set_page_config(
    page_title="Calculadora de Unidades - CCU",
    page_icon="🧮",
    layout="centered",
    initial_sidebar_state="collapsed"
)


# =====================================================
# RUTAS
# =====================================================

RUTA_BASE = Path(__file__).parent

ARCHIVO_BBDD = RUTA_BASE / "BBDD_UNIDADES_MATERIAS_PRIMAS.parquet"
ARCHIVO_LOGO = RUTA_BASE / "CCU_LOGO.png"


# =====================================================
# ESTILOS
# =====================================================

st.markdown(
    """
    <style>
    /* Reducir espacio superior para que el logo no quede cortado */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 980px;
    }

    /* Ocultar elementos visuales innecesarios de Streamlit */
    header[data-testid="stHeader"] {
        background: rgba(0,0,0,0);
        height: 0rem;
    }

    div[data-testid="stToolbar"] {
        visibility: hidden;
        height: 0%;
        position: fixed;
    }

    div[data-testid="stDecoration"] {
        visibility: hidden;
        height: 0%;
        position: fixed;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    .logo-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-top: 0px;
        margin-bottom: 10px;
        width: 100%;
    }

    .logo-container img {
        max-width: 135px;
        height: auto;
        display: block;
    }

    .titulo-principal {
        text-align: center;
        font-size: 28px;
        font-weight: 800;
        color: #003865;
        margin-top: 0px;
        margin-bottom: 2px;
        line-height: 1.2;
    }

    .subtitulo {
        text-align: center;
        font-size: 15px;
        color: #666666;
        margin-bottom: 24px;
    }

    .seccion {
        font-size: 18px;
        font-weight: 700;
        color: #003865;
        margin-top: 8px;
        margin-bottom: 10px;
    }

    .mensaje-ok {
        background-color: #EAF7EA;
        border-left: 5px solid #2E7D32;
        padding: 14px 16px;
        border-radius: 8px;
        color: #1B5E20;
        font-size: 15px;
        margin-top: 18px;
        margin-bottom: 18px;
    }

    .mensaje-info {
        background-color: #F4F7FA;
        border-left: 5px solid #003865;
        padding: 14px 16px;
        border-radius: 8px;
        color: #333333;
        font-size: 15px;
        margin-top: 18px;
        margin-bottom: 18px;
    }

    .footer-app {
        text-align: center;
        color: #888888;
        font-size: 12px;
        margin-top: 36px;
    }

    div.stButton > button:first-child {
        width: 100%;
        background-color: #003865;
        color: white;
        font-weight: 700;
        border-radius: 8px;
        height: 3rem;
        border: none;
    }

    div.stButton > button:first-child:hover {
        background-color: #005A8B;
        color: white;
        border: none;
    }

    div.stDownloadButton > button:first-child {
        width: 100%;
        background-color: #006B3F;
        color: white;
        font-weight: 700;
        border-radius: 8px;
        height: 3rem;
        border: none;
    }

    div.stDownloadButton > button:first-child:hover {
        background-color: #00804B;
        color: white;
        border: none;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #E1E4E8;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =====================================================
# FUNCIONES
# =====================================================

def mostrar_logo_centrado(ruta_logo: Path, ancho_px: int = 135) -> None:
    """
    Muestra el logo centrado usando HTML/base64 para evitar problemas
    de alineación y cortes con el encabezado de Streamlit.
    """

    if not ruta_logo.exists():
        return

    with open(ruta_logo, "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode()

    st.markdown(
        f"""
        <div class="logo-container">
            <img src="data:image/png;base64,{logo_base64}" style="max-width:{ancho_px}px;">
        </div>
        """,
        unsafe_allow_html=True
    )


@st.cache_data
def cargar_bbdd() -> pd.DataFrame:
    """
    Carga la BBDD desde archivo Parquet.
    """

    if not ARCHIVO_BBDD.exists():
        st.error("No se encontró el archivo BBDD_UNIDADES_MATERIAS_PRIMAS.parquet en el repositorio.")
        st.stop()

    df = pd.read_parquet(ARCHIVO_BBDD)

    df.columns = [str(col).strip() for col in df.columns]

    columnas_necesarias = [
        "Tipo de elaboración",
        "Materia prima",
        "Código",
        "Unidad medida",
        "Cantidad por unidad"
    ]

    faltantes = [col for col in columnas_necesarias if col not in df.columns]

    if faltantes:
        st.error(
            "La BBDD no tiene las columnas necesarias: "
            + ", ".join(faltantes)
        )
        st.stop()

    df = df[columnas_necesarias].copy()

    df["Tipo de elaboración"] = df["Tipo de elaboración"].fillna("").astype(str).str.strip()
    df["Materia prima"] = df["Materia prima"].fillna("").astype(str).str.strip()
    df["Código"] = df["Código"].fillna("").astype(str).str.strip()
    df["Unidad medida"] = df["Unidad medida"].fillna("").astype(str).str.strip()

    df["Cantidad por unidad"] = pd.to_numeric(
        df["Cantidad por unidad"],
        errors="coerce"
    )

    df = df.dropna(
        subset=[
            "Tipo de elaboración",
            "Materia prima",
            "Cantidad por unidad"
        ]
    ).copy()

    df = df[
        (df["Tipo de elaboración"] != "") &
        (df["Materia prima"] != "")
    ].copy()

    df = df.sort_values(
        [
            "Tipo de elaboración",
            "Materia prima"
        ],
        ascending=[
            True,
            True
        ]
    ).reset_index(drop=True)

    return df


def generar_calculo(df_filtrado: pd.DataFrame, unidades: int) -> pd.DataFrame:
    """
    Calcula las materias primas requeridas.
    """

    df_resultado = df_filtrado.copy()

    df_resultado["Número de unidades"] = unidades
    df_resultado["Cantidad requerida"] = (
        df_resultado["Cantidad por unidad"] * unidades
    )

    return df_resultado


def tabla_resultado_simple(df_resultado: pd.DataFrame) -> pd.DataFrame:
    """
    Tabla simple para mostrar al usuario.
    """

    df_simple = df_resultado[
        [
            "Materia prima",
            "Código",
            "Cantidad requerida",
            "Unidad medida"
        ]
    ].copy()

    df_simple["Cantidad requerida"] = df_simple["Cantidad requerida"].round(6)

    return df_simple


def tabla_detalle_unitario(df_resultado: pd.DataFrame) -> pd.DataFrame:
    """
    Tabla de detalle unitario para mostrar colapsada.
    """

    df_detalle = df_resultado[
        [
            "Materia prima",
            "Código",
            "Cantidad por unidad",
            "Número de unidades",
            "Cantidad requerida",
            "Unidad medida"
        ]
    ].copy()

    df_detalle["Cantidad por unidad"] = df_detalle["Cantidad por unidad"].round(6)
    df_detalle["Cantidad requerida"] = df_detalle["Cantidad requerida"].round(6)

    return df_detalle


def convertir_excel(df_resultado: pd.DataFrame, tipo_elaboracion: str, fecha_calculo: date, unidades: int) -> BytesIO:
    """
    Convierte resultado a Excel descargable.
    Hoja 1: Resultado simple.
    Hoja 2: Detalle unitario.
    """

    output = BytesIO()

    df_simple = tabla_resultado_simple(df_resultado)
    df_detalle = tabla_detalle_unitario(df_resultado)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_simple.to_excel(writer, index=False, sheet_name="Resultado")
        df_detalle.to_excel(writer, index=False, sheet_name="Detalle unitario")

        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        fill_header = PatternFill("solid", fgColor="1F4E78")
        font_header = Font(color="FFFFFF", bold=True)

        fill_info = PatternFill("solid", fgColor="EAF3F8")
        font_info = Font(color="003865", bold=True)

        thin = Side(style="thin", color="D9D9D9")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        for sheet_name in ["Resultado", "Detalle unitario"]:
            worksheet = writer.sheets[sheet_name]

            worksheet.insert_rows(1, 4)

            worksheet["A1"] = "Calculadora de Unidades - Materias Primas"
            worksheet["A1"].font = Font(bold=True, size=14, color="003865")

            worksheet["A2"] = f"Tipo de elaboración: {tipo_elaboracion}"
            worksheet["A3"] = f"Número de unidades: {unidades}"
            worksheet["A4"] = f"Fecha cálculo: {fecha_calculo.strftime('%d-%m-%Y')}"

            for row in range(1, 5):
                for col in range(1, worksheet.max_column + 1):
                    cell = worksheet.cell(row=row, column=col)
                    cell.fill = fill_info
                    cell.font = font_info
                    cell.alignment = Alignment(vertical="center")

            for cell in worksheet[5]:
                cell.fill = fill_header
                cell.font = font_header
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = border

            for row in worksheet.iter_rows(min_row=6):
                for cell in row:
                    cell.border = border
                    cell.alignment = Alignment(vertical="top", wrap_text=True)

            worksheet.freeze_panes = "A6"
            worksheet.auto_filter.ref = worksheet.dimensions

            for col in worksheet.columns:
                col_letter = col[0].column_letter
                max_len = 0

                for cell in col:
                    value = "" if cell.value is None else str(cell.value)
                    max_len = max(max_len, len(value))

                worksheet.column_dimensions[col_letter].width = min(max(max_len + 2, 12), 42)

    output.seek(0)
    return output


def nombre_archivo_seguro(texto: str) -> str:
    """
    Limpia texto para usarlo como nombre de archivo.
    """

    reemplazos = {
        "/": "-",
        "\\": "-",
        ":": "-",
        "*": "",
        "?": "",
        '"': "",
        "<": "",
        ">": "",
        "|": ""
    }

    texto = str(texto)

    for malo, bueno in reemplazos.items():
        texto = texto.replace(malo, bueno)

    texto = texto.replace(" ", "_")

    return texto


# =====================================================
# CARGAR BBDD
# =====================================================

df_bbdd = cargar_bbdd()


# =====================================================
# ENCABEZADO
# =====================================================

mostrar_logo_centrado(ARCHIVO_LOGO, ancho_px=135)

st.markdown(
    """
    <div class="titulo-principal">Calculadora de Materias Primas</div>
    <div class="subtitulo">Proyecto CCU - Elaboración</div>
    """,
    unsafe_allow_html=True
)


# =====================================================
# FORMULARIO
# =====================================================

st.markdown('<div class="seccion">Datos del cálculo</div>', unsafe_allow_html=True)

with st.form("form_calculo"):

    fecha_calculo = st.date_input(
        "Fecha",
        value=date.today()
    )

    tipos_elaboracion = sorted(df_bbdd["Tipo de elaboración"].unique())

    tipo_seleccionado = st.selectbox(
        "Tipo de elaboración",
        options=tipos_elaboracion,
        index=0
    )

    unidades = st.number_input(
        "Número de unidades",
        min_value=1,
        value=1,
        step=1
    )

    calcular = st.form_submit_button("Calcular materias primas")


# =====================================================
# RESULTADO
# =====================================================

if calcular:

    df_filtrado = df_bbdd[
        df_bbdd["Tipo de elaboración"] == tipo_seleccionado
    ].copy()

    df_resultado = generar_calculo(
        df_filtrado=df_filtrado,
        unidades=unidades
    )

    df_simple = tabla_resultado_simple(df_resultado)
    df_detalle = tabla_detalle_unitario(df_resultado)

    st.markdown(
        f"""
        <div class="mensaje-ok">
            Cálculo generado para <b>{tipo_seleccionado}</b> con <b>{unidades}</b> unidades.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="seccion">Resultado</div>', unsafe_allow_html=True)

    st.dataframe(
        df_simple,
        use_container_width=True,
        hide_index=True
    )

    with st.expander("Ver detalle de cantidad unitaria", expanded=False):
        st.dataframe(
            df_detalle,
            use_container_width=True,
            hide_index=True
        )

    archivo_excel = convertir_excel(
        df_resultado=df_resultado,
        tipo_elaboracion=tipo_seleccionado,
        fecha_calculo=fecha_calculo,
        unidades=unidades
    )

    nombre_descarga = (
        "CALCULO_MP_"
        + nombre_archivo_seguro(tipo_seleccionado)
        + "_"
        + fecha_calculo.strftime("%Y%m%d")
        + ".xlsx"
    )

    st.download_button(
        label="Descargar resultado en Excel",
        data=archivo_excel,
        file_name=nombre_descarga,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.markdown(
        """
        <div class="mensaje-info">
            Selecciona la fecha, el tipo de elaboración y el número de unidades. Luego presiona <b>Calcular materias primas</b>.
        </div>
        """,
        unsafe_allow_html=True
    )


# =====================================================
# PIE DE PÁGINA
# =====================================================

st.markdown(
    """
    <div class="footer-app">
        Proyecto CCU - Elaboración | BBDD Parquet
    </div>
    """,
    unsafe_allow_html=True
)

# =====================================================
# 01_APP_CALCULADORA_UNIDADES.py
# VERSION 4
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
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2rem;
        max-width: 1040px;
    }

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

    .mensaje-alerta {
        background-color: #FFF8E1;
        border-left: 5px solid #D6B656;
        padding: 12px 14px;
        border-radius: 8px;
        color: #5F4B00;
        font-size: 14px;
        margin-top: 12px;
        margin-bottom: 12px;
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
# FUNCIONES DE APOYO
# =====================================================

def mostrar_logo_centrado(ruta_logo: Path, ancho_px: int = 135) -> None:
    """
    Muestra el logo centrado usando HTML/base64.
    Esto evita que quede desalineado o cortado por el encabezado de Streamlit.
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
    Carga y limpia la BBDD Parquet.
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
    df["Unidad medida"] = df["Unidad medida"].fillna("Sin unidad explícita").astype(str).str.strip()

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


def generar_calculo(df_bbdd: pd.DataFrame, tipo_elaboracion: str, unidades: int) -> pd.DataFrame:
    """
    Calcula materias primas requeridas para el tipo de elaboración seleccionado.
    """

    df_filtrado = df_bbdd[
        df_bbdd["Tipo de elaboración"] == tipo_elaboracion
    ].copy()

    df_filtrado = df_filtrado.sort_values("Materia prima").reset_index(drop=True)

    df_filtrado["Número de unidades"] = unidades
    df_filtrado["Cantidad requerida"] = (
        df_filtrado["Cantidad por unidad"] * unidades
    )

    df_filtrado = df_filtrado[
        [
            "Tipo de elaboración",
            "Materia prima",
            "Código",
            "Cantidad por unidad",
            "Cantidad requerida",
            "Unidad medida",
            "Número de unidades"
        ]
    ].copy()

    return df_filtrado


def tabla_resultado_simple(df_resultado: pd.DataFrame) -> pd.DataFrame:
    """
    Tabla principal simple para el usuario.
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
    Tabla de detalle unitario, colapsada por defecto.
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


def crear_base_fichas(df_resultado: pd.DataFrame) -> pd.DataFrame:
    """
    Crea una tabla editable para levantar fichas técnicas.
    Es una versión más amigable que crear un formulario individual por materia prima.
    """

    df_fichas = df_resultado[
        [
            "Materia prima",
            "Código",
            "Unidad medida"
        ]
    ].copy()

    df_fichas["Proveedor"] = ""
    df_fichas["Lote"] = ""
    df_fichas["Fecha Elaboración"] = ""
    df_fichas["Fecha Vencimiento"] = ""
    df_fichas["N° Bolsas / Bidones"] = ""
    df_fichas["Inspección visual"] = "Cumple"

    return df_fichas


def generar_registro_una_fila(
    df_resultado: pd.DataFrame,
    df_fichas: pd.DataFrame,
    fecha_calculo: date,
    orden_elaboracion: str,
    tipo_elaboracion: str,
    unidades: int,
    destino: str,
    turno: str,
    operador: str,
    observacion: str
) -> pd.DataFrame:
    """
    Genera un registro completo en una sola fila:
    datos generales + cálculo + fichas técnicas.
    """

    fila_registro = {
        "Fecha": fecha_calculo.strftime("%d-%m-%Y") if fecha_calculo else "",
        "Orden elaboración": orden_elaboracion,
        "Tipo de elaboración": tipo_elaboracion,
        "Unidades": unidades,
        "Destino": destino,
        "Turno": turno,
        "Operador": operador,
        "Observación": observacion
    }

    # Materias primas calculadas
    for _, row in df_resultado.iterrows():
        materia = str(row["Materia prima"]).strip()
        codigo = str(row["Código"]).strip()
        unidad_medida = str(row["Unidad medida"]).strip()

        nombre_base = f"{materia} ({codigo})" if codigo != "" else materia

        fila_registro[f"{nombre_base} Unidad medida"] = unidad_medida
        fila_registro[f"{nombre_base} Cantidad por unidad"] = row["Cantidad por unidad"]
        fila_registro[f"{nombre_base} Cantidad calculada"] = row["Cantidad requerida"]

    # Fichas técnicas
    if df_fichas is not None and len(df_fichas) > 0:
        for _, row in df_fichas.iterrows():
            materia = str(row.get("Materia prima", "")).strip()
            codigo = str(row.get("Código", "")).strip()

            nombre_base = f"{materia} ({codigo})" if codigo != "" else materia

            fila_registro[f"{nombre_base} Proveedor"] = row.get("Proveedor", "")
            fila_registro[f"{nombre_base} Lote"] = row.get("Lote", "")
            fila_registro[f"{nombre_base} Fecha Elaboración"] = row.get("Fecha Elaboración", "")
            fila_registro[f"{nombre_base} Fecha Vencimiento"] = row.get("Fecha Vencimiento", "")
            fila_registro[f"{nombre_base} N° Bolsas / Bidones"] = row.get("N° Bolsas / Bidones", "")
            fila_registro[f"{nombre_base} Inspección visual"] = row.get("Inspección visual", "")

    return pd.DataFrame([fila_registro])


def convertir_excel(
    df_resultado: pd.DataFrame,
    df_fichas: pd.DataFrame,
    df_registro: pd.DataFrame,
    tipo_elaboracion: str,
    fecha_calculo: date,
    unidades: int
) -> BytesIO:
    """
    Genera Excel descargable con:
    - Resultado simple
    - Detalle unitario
    - Fichas técnicas
    - Registro completo
    """

    output = BytesIO()

    df_simple = tabla_resultado_simple(df_resultado)
    df_detalle = tabla_detalle_unitario(df_resultado)

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_simple.to_excel(writer, index=False, sheet_name="Resultado")
        df_detalle.to_excel(writer, index=False, sheet_name="Detalle unitario")

        if df_fichas is not None and len(df_fichas) > 0:
            df_fichas.to_excel(writer, index=False, sheet_name="Fichas tecnicas")

        if df_registro is not None and len(df_registro) > 0:
            df_registro.to_excel(writer, index=False, sheet_name="Registro completo")

        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        fill_header = PatternFill("solid", fgColor="1F4E78")
        font_header = Font(color="FFFFFF", bold=True)

        fill_info = PatternFill("solid", fgColor="EAF3F8")
        font_info = Font(color="003865", bold=True)

        thin = Side(style="thin", color="D9D9D9")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        for sheet_name in writer.sheets:
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
                    cell.alignment = Alignment(vertical="center", wrap_text=True)

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

                worksheet.column_dimensions[col_letter].width = min(max(max_len + 2, 12), 45)

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
# FORMULARIO PRINCIPAL
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
# CÁLCULO
# =====================================================

if calcular:
    st.session_state["calculo_generado"] = True
    st.session_state["fecha_calculo"] = fecha_calculo
    st.session_state["tipo_seleccionado"] = tipo_seleccionado
    st.session_state["unidades"] = unidades

if st.session_state.get("calculo_generado", False):

    fecha_calculo = st.session_state["fecha_calculo"]
    tipo_seleccionado = st.session_state["tipo_seleccionado"]
    unidades = st.session_state["unidades"]

    df_resultado = generar_calculo(
        df_bbdd=df_bbdd,
        tipo_elaboracion=tipo_seleccionado,
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

    # =================================================
    # REGISTRO OPCIONAL
    # =================================================

    with st.expander("Completar registro opcional", expanded=False):
        st.markdown(
            """
            <div class="mensaje-alerta">
                Esta sección es opcional. Sirve para guardar datos generales y fichas técnicas
                junto con el cálculo.
            </div>
            """,
            unsafe_allow_html=True
        )

        col1, col2 = st.columns(2)

        with col1:
            orden_elaboracion = st.text_input(
                "Orden elaboración",
                placeholder="Ej: 7100059000"
            )

            destino = st.selectbox(
                "Destino",
                options=[
                    "SALA DE JARABES 1",
                    "SALA DE JARABES 2",
                    "SALA BAG IN BOX (BIB)"
                ],
                index=0
            )

        with col2:
            turno = st.selectbox(
                "Turno",
                options=["A", "B", "C"],
                index=0
            )

            operador = st.text_input(
                "Operador",
                placeholder="Ej: R. Toledo"
            )

        observacion = st.text_area(
            "Observación",
            placeholder="Observación del registro",
            height=80
        )

        st.markdown('<div class="seccion">Fichas técnicas</div>', unsafe_allow_html=True)

        df_fichas_base = crear_base_fichas(df_resultado)

        df_fichas = st.data_editor(
            df_fichas_base,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "Inspección visual": st.column_config.SelectboxColumn(
                    "Inspección visual",
                    options=["Cumple", "No cumple"],
                    required=False
                )
            },
            key="editor_fichas"
        )

        df_registro = generar_registro_una_fila(
            df_resultado=df_resultado,
            df_fichas=df_fichas,
            fecha_calculo=fecha_calculo,
            orden_elaboracion=orden_elaboracion,
            tipo_elaboracion=tipo_seleccionado,
            unidades=unidades,
            destino=destino,
            turno=turno,
            operador=operador,
            observacion=observacion
        )

        with st.expander("Ver registro completo en una fila", expanded=False):
            st.dataframe(
                df_registro,
                use_container_width=True,
                hide_index=True
            )

    # Si no se completó la sección opcional, se descarga igual con fichas base vacías
    df_fichas_descarga = crear_base_fichas(df_resultado)

    df_registro_descarga = generar_registro_una_fila(
        df_resultado=df_resultado,
        df_fichas=df_fichas_descarga,
        fecha_calculo=fecha_calculo,
        orden_elaboracion="",
        tipo_elaboracion=tipo_seleccionado,
        unidades=unidades,
        destino="",
        turno="",
        operador="",
        observacion=""
    )

    archivo_excel = convertir_excel(
        df_resultado=df_resultado,
        df_fichas=df_fichas_descarga,
        df_registro=df_registro_descarga,
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
            Selecciona la fecha, el tipo de elaboración y el número de unidades.
            Luego presiona <b>Calcular materias primas</b>.
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

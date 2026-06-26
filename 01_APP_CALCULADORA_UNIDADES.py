# =====================================================
# 01_APP_CALCULADORA_UNIDADES.py
# VERSION 6
# APP CALCULADORA DE MATERIAS PRIMAS POR UNIDADES
# PROYECTO CCU - ELABORACIÓN
# =====================================================

import base64
import re
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
    layout="wide",
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
        padding-top: 1.0rem;
        padding-bottom: 2rem;
        max-width: 1320px;
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
        margin-top: 0px;
        margin-bottom: 6px;
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
        margin-top: 0px;
        margin-bottom: 2px;
        line-height: 1.2;
    }

    .subtitulo {
        text-align: center;
        font-size: 15px;
        color: #666666;
        margin-bottom: 20px;
    }

    .card {
        background-color: #FFFFFF;
        border: 1px solid #E1E4E8;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0px 1px 2px rgba(0,0,0,0.04);
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
        margin-top: 0px;
        margin-bottom: 12px;
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
        margin-top: 10px;
        margin-bottom: 12px;
    }

    .footer-app {
        text-align: center;
        color: #888888;
        font-size: 12px;
        margin-top: 34px;
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
# FUNCIONES DE LIMPIEZA
# =====================================================

def mostrar_logo_centrado(ruta_logo: Path, ancho_px: int = 112) -> None:
    """
    Muestra el logo centrado usando HTML/base64.
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


def limpiar_texto(valor) -> str:
    """
    Limpia valores de texto.
    """

    if pd.isna(valor):
        return ""

    texto = str(valor).strip()

    if texto.lower() in ["nan", "none", "nat"]:
        return ""

    texto = re.sub(r"\s+", " ", texto)

    return texto


def formatear_cantidad(valor, max_decimales: int = 4) -> str:
    """
    Formatea cantidades cuidando cifras significativas:
    - No muestra ceros innecesarios.
    - Máximo 4 decimales por defecto.
    - Mantiene decimales cuando realmente aportan información.
    """

    try:
        numero = float(valor)
    except Exception:
        return ""

    if pd.isna(numero):
        return ""

    texto = f"{numero:,.{max_decimales}f}"
    texto = texto.rstrip("0").rstrip(".")

    if texto == "-0":
        texto = "0"

    return texto


def extraer_codigo_candidato(materia_original: str) -> str:
    """
    Extrae el código de producto desde el nombre original de la materia prima.

    Se priorizan códigos propios de producto como:
    - 17B71ASK
    - 17286ASP
    - 17174MSB
    - 35009*60*01A
    - 35009*80*33Av02

    Se evitan códigos logísticos como:
    - E56685
    - 2000304212
    - F0000014161
    """

    texto = limpiar_texto(materia_original)

    if texto == "":
        return ""

    # Candidatos dentro de paréntesis
    parentesis = re.findall(r"\(([^)]{3,80})\)", texto)

    for item in parentesis:
        candidato = limpiar_texto(item)

        # Saltar paréntesis que parecen descripción de unidad o contienen código logístico E
        if re.search(r"\bKg\b|\bL\b|unidad|unid", candidato, flags=re.IGNORECASE):
            continue

        if re.search(r"\bE\d{4,}\b", candidato, flags=re.IGNORECASE):
            continue

        if re.search(r"\bF\d{5,}\b", candidato, flags=re.IGNORECASE):
            continue

        if re.search(r"\b20\d{8,}\b", candidato):
            continue

        # Aceptar códigos con asterisco
        if re.search(r"\d+\*\d+", candidato):
            return candidato.upper()

        # Aceptar código alfanumérico compacto, ejemplo 17B71ASK
        if re.fullmatch(r"[A-Z0-9][A-Z0-9*\-/.]{3,30}", candidato, flags=re.IGNORECASE):
            return candidato.upper()

    # Códigos con asterisco fuera de paréntesis, normalmente al final del nombre
    match_ast = re.search(r"\b\d{3,}\*\d+(?:\*\d+)?[A-Z0-9]*\b", texto, flags=re.IGNORECASE)
    if match_ast:
        return match_ast.group(0).upper()

    return ""


def es_codigo_logistico(codigo: str) -> bool:
    """
    Identifica códigos logísticos que no conviene mostrar como código principal.
    """

    codigo = limpiar_texto(codigo)

    if codigo == "":
        return False

    if re.fullmatch(r"20\d{8,}\s*(SA|LF)?", codigo, flags=re.IGNORECASE):
        return True

    if re.fullmatch(r"F\d{5,}", codigo, flags=re.IGNORECASE):
        return True

    if re.search(r"\b20\d{8,}\b", codigo) and len(codigo) > 8:
        return True

    return False


def normalizar_codigo(codigo_original, materia_original: str) -> str:
    """
    Normaliza la columna Código.
    Si el código original viene vacío o parece logístico, usa el código candidato desde la materia prima.
    """

    codigo = limpiar_texto(codigo_original)
    candidato = extraer_codigo_candidato(materia_original)

    if candidato != "":
        if codigo == "" or es_codigo_logistico(codigo):
            return candidato

    return codigo


def limpiar_nombre_materia_prima(materia_original: str) -> str:
    """
    Limpia el nombre visible de la materia prima.

    Ejemplo:
    Acesulfamo de Potasio (17B71ASK) (E56685 2000304212 SA F0000014161)
    -> Acesulfamo de Potasio
    """

    texto = limpiar_texto(materia_original)

    if texto == "":
        return ""

    # Quitar contenido entre paréntesis
    texto = re.sub(r"\([^)]*\)", "", texto)

    # Quitar códigos logísticos
    texto = re.sub(r"\bE\d{4,}\b", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\bF\d{5,}\b", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\b20\d{8,}\b", "", texto)
    texto = re.sub(r"\bSA\b", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\bLF\b", "", texto, flags=re.IGNORECASE)

    # Quitar códigos con asterisco que queden al final del nombre
    texto = re.sub(r"\b\d{3,}\*\d+(?:\*\d+)?[A-Z0-9]*\b\s*$", "", texto, flags=re.IGNORECASE)

    texto = re.sub(r"\s+", " ", texto).strip(" -_/.")

    return texto


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
# CARGA DE BBDD
# =====================================================

@st.cache_data
def cargar_bbdd() -> pd.DataFrame:
    """
    Carga, limpia y normaliza la BBDD Parquet.
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

    df["Tipo de elaboración"] = df["Tipo de elaboración"].apply(limpiar_texto)
    df["Materia prima original"] = df["Materia prima"].apply(limpiar_texto)

    df["Código"] = df.apply(
        lambda row: normalizar_codigo(
            row["Código"],
            row["Materia prima original"]
        ),
        axis=1
    )

    df["Materia prima"] = df["Materia prima original"].apply(limpiar_nombre_materia_prima)

    df["Unidad medida"] = (
        df["Unidad medida"]
        .fillna("Sin unidad explícita")
        .astype(str)
        .str.strip()
    )

    df["Unidad medida"] = df["Unidad medida"].replace(
        {
            "": "Sin unidad explícita",
            "nan": "Sin unidad explícita",
            "None": "Sin unidad explícita"
        }
    )

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

    # Consolidar si existen duplicados exactos luego de limpiar nombres/códigos
    df = (
        df
        .groupby(
            [
                "Tipo de elaboración",
                "Materia prima",
                "Código",
                "Unidad medida"
            ],
            as_index=False
        )
        .agg(
            Cantidad_por_unidad=("Cantidad por unidad", "sum")
        )
    )

    df = df.rename(columns={
        "Cantidad_por_unidad": "Cantidad por unidad"
    })

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


# =====================================================
# FUNCIONES DE CÁLCULO
# =====================================================

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
    Tabla principal simple.
    """

    df_simple = df_resultado[
        [
            "Materia prima",
            "Código",
            "Cantidad requerida",
            "Unidad medida"
        ]
    ].copy()

    df_simple["Cantidad requerida"] = df_simple["Cantidad requerida"].apply(
        lambda x: formatear_cantidad(x, max_decimales=4)
    )

    return df_simple


def tabla_detalle_unitario(df_resultado: pd.DataFrame) -> pd.DataFrame:
    """
    Tabla de detalle unitario.
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

    df_detalle["Cantidad por unidad"] = df_detalle["Cantidad por unidad"].apply(
        lambda x: formatear_cantidad(x, max_decimales=6)
    )

    df_detalle["Cantidad requerida"] = df_detalle["Cantidad requerida"].apply(
        lambda x: formatear_cantidad(x, max_decimales=4)
    )

    return df_detalle


def crear_base_fichas(df_resultado: pd.DataFrame) -> pd.DataFrame:
    """
    Crea una tabla editable para fichas técnicas de materias primas.
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
    Genera registro completo en una sola fila.
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

    for _, row in df_resultado.iterrows():
        materia = limpiar_texto(row["Materia prima"])
        codigo = limpiar_texto(row["Código"])
        unidad_medida = limpiar_texto(row["Unidad medida"])

        nombre_base = f"{materia} ({codigo})" if codigo != "" else materia

        fila_registro[f"{nombre_base} Unidad medida"] = unidad_medida
        fila_registro[f"{nombre_base} Cantidad por unidad"] = row["Cantidad por unidad"]
        fila_registro[f"{nombre_base} Cantidad calculada"] = row["Cantidad requerida"]

    if df_fichas is not None and len(df_fichas) > 0:
        for _, row in df_fichas.iterrows():
            materia = limpiar_texto(row.get("Materia prima", ""))
            codigo = limpiar_texto(row.get("Código", ""))

            nombre_base = f"{materia} ({codigo})" if codigo != "" else materia

            fila_registro[f"{nombre_base} Proveedor"] = row.get("Proveedor", "")
            fila_registro[f"{nombre_base} Lote"] = row.get("Lote", "")
            fila_registro[f"{nombre_base} Fecha Elaboración"] = row.get("Fecha Elaboración", "")
            fila_registro[f"{nombre_base} Fecha Vencimiento"] = row.get("Fecha Vencimiento", "")
            fila_registro[f"{nombre_base} N° Bolsas / Bidones"] = row.get("N° Bolsas / Bidones", "")
            fila_registro[f"{nombre_base} Inspección visual"] = row.get("Inspección visual", "")

    return pd.DataFrame([fila_registro])


# =====================================================
# EXPORTACIÓN A EXCEL
# =====================================================

def convertir_excel(
    df_resultado: pd.DataFrame,
    df_fichas: pd.DataFrame,
    df_registro: pd.DataFrame,
    tipo_elaboracion: str,
    fecha_calculo: date,
    unidades: int
) -> BytesIO:
    """
    Genera Excel descargable:
    - Resultado
    - Detalle unitario
    - Fichas técnicas
    - Registro completo
    """

    output = BytesIO()

    df_simple = df_resultado[
        [
            "Materia prima",
            "Código",
            "Cantidad requerida",
            "Unidad medida"
        ]
    ].copy()

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

                    if isinstance(cell.value, (int, float)):
                        cell.number_format = "#,##0.####"

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


# =====================================================
# CARGAR BBDD
# =====================================================

df_bbdd = cargar_bbdd()


# =====================================================
# ENCABEZADO
# =====================================================

mostrar_logo_centrado(ARCHIVO_LOGO, ancho_px=112)

st.markdown(
    """
    <div class="titulo-principal">Registro de elaboración - Sala de unidades</div>
    <div class="subtitulo">Calculadora de materias primas | Proyecto CCU - Elaboración</div>
    """,
    unsafe_allow_html=True
)


# =====================================================
# FORMULARIO PRINCIPAL
# =====================================================

st.markdown('<div class="card-important">', unsafe_allow_html=True)
st.markdown('<div class="seccion">Inputs importantes</div>', unsafe_allow_html=True)

with st.form("form_calculo"):

    col_a, col_b = st.columns([2.5, 1])

    with col_a:
        tipos_elaboracion = sorted(df_bbdd["Tipo de elaboración"].unique())

        tipo_seleccionado = st.selectbox(
            "Tipo de elaboración",
            options=tipos_elaboracion,
            index=0
        )

    with col_b:
        unidades = st.number_input(
            "Unidades",
            min_value=1,
            value=1,
            step=1
        )

    st.markdown('<div class="seccion">Datos generales</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.1, 1.4, 1.6])

    with col1:
        fecha_calculo = st.date_input(
            "Fecha",
            value=date.today()
        )

    with col2:
        orden_elaboracion = st.text_input(
            "Orden",
            placeholder="Ej: 7100059000"
        )

    with col3:
        destino = st.selectbox(
            "Destino",
            options=[
                "SALA DE JARABES 1",
                "SALA DE JARABES 2",
                "SALA BAG IN BOX (BIB)"
            ],
            index=0
        )

    col4, col5, col6 = st.columns([0.8, 1.4, 2.2])

    with col4:
        turno = st.selectbox(
            "Turno",
            options=["A", "B", "C"],
            index=0
        )

    with col5:
        operador = st.text_input(
            "Operador",
            placeholder="Ej: R. Toledo"
        )

    with col6:
        observacion = st.text_input(
            "Observación",
            placeholder="Observación del registro"
        )

    calcular = st.form_submit_button("Mostrar registro")

st.markdown('</div>', unsafe_allow_html=True)


# =====================================================
# CÁLCULO
# =====================================================

if calcular:
    st.session_state["calculo_generado"] = True
    st.session_state["fecha_calculo"] = fecha_calculo
    st.session_state["tipo_seleccionado"] = tipo_seleccionado
    st.session_state["unidades"] = unidades
    st.session_state["orden_elaboracion"] = orden_elaboracion
    st.session_state["destino"] = destino
    st.session_state["turno"] = turno
    st.session_state["operador"] = operador
    st.session_state["observacion"] = observacion
    st.session_state.pop("df_fichas", None)
    st.session_state.pop("df_registro", None)

if st.session_state.get("calculo_generado", False):

    fecha_calculo = st.session_state["fecha_calculo"]
    tipo_seleccionado = st.session_state["tipo_seleccionado"]
    unidades = st.session_state["unidades"]
    orden_elaboracion = st.session_state["orden_elaboracion"]
    destino = st.session_state["destino"]
    turno = st.session_state["turno"]
    operador = st.session_state["operador"]
    observacion = st.session_state["observacion"]

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
            <b>Registro de prueba generado correctamente.</b><br>
            Elaboración seleccionada: <b>{tipo_seleccionado}</b><br>
            Unidades solicitadas: <b>{unidades}</b><br>
            Materias primas requeridas: <b>{len(df_simple)}</b>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="seccion">Materias primas requeridas</div>', unsafe_allow_html=True)

    st.dataframe(
        df_simple,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Materia prima": st.column_config.TextColumn(
                "Materia prima",
                width="large"
            ),
            "Código": st.column_config.TextColumn(
                "Código",
                width="medium"
            ),
            "Cantidad requerida": st.column_config.TextColumn(
                "Cantidad requerida",
                width="medium"
            ),
            "Unidad medida": st.column_config.TextColumn(
                "Unidad medida",
                width="small"
            )
        }
    )

    with st.expander("Ver detalle de cantidad unitaria", expanded=False):
        st.dataframe(
            df_detalle,
            use_container_width=True,
            hide_index=True
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # =================================================
    # FICHAS TÉCNICAS
    # =================================================

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="seccion">Ficha técnica de materias primas</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="mensaje-alerta">
            Completa proveedor, lote, fechas, número de bolsas o bidones e inspección visual para cada materia prima.
        </div>
        """,
        unsafe_allow_html=True
    )

    df_fichas_base = crear_base_fichas(df_resultado)

    df_fichas = st.data_editor(
        df_fichas_base,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "Materia prima": st.column_config.TextColumn(
                "Materia prima",
                disabled=True,
                width="large"
            ),
            "Código": st.column_config.TextColumn(
                "Código",
                disabled=True,
                width="medium"
            ),
            "Unidad medida": st.column_config.TextColumn(
                "Unidad medida",
                disabled=True,
                width="small"
            ),
            "Proveedor": st.column_config.TextColumn(
                "Proveedor",
                width="medium"
            ),
            "Lote": st.column_config.TextColumn(
                "Lote",
                width="medium"
            ),
            "Fecha Elaboración": st.column_config.TextColumn(
                "Fecha Elaboración",
                help="Formato sugerido: dd-mm-aaaa"
            ),
            "Fecha Vencimiento": st.column_config.TextColumn(
                "Fecha Vencimiento",
                help="Formato sugerido: dd-mm-aaaa"
            ),
            "N° Bolsas / Bidones": st.column_config.TextColumn(
                "N° Bolsas / Bidones"
            ),
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

    st.session_state["df_fichas"] = df_fichas
    st.session_state["df_registro"] = df_registro

    with st.expander("Ver registro completo en una fila", expanded=False):
        st.dataframe(
            df_registro,
            use_container_width=True,
            hide_index=True
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # =================================================
    # DESCARGA
    # =================================================

    archivo_excel = convertir_excel(
        df_resultado=df_resultado,
        df_fichas=df_fichas,
        df_registro=df_registro,
        tipo_elaboracion=tipo_seleccionado,
        fecha_calculo=fecha_calculo,
        unidades=unidades
    )

    nombre_descarga = (
        "REGISTRO_SALA_UNIDADES_"
        + nombre_archivo_seguro(tipo_seleccionado)
        + "_"
        + fecha_calculo.strftime("%Y%m%d")
        + ".xlsx"
    )

    st.download_button(
        label="Descargar registro en Excel",
        data=archivo_excel,
        file_name=nombre_descarga,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.markdown(
        """
        <div class="mensaje-info">
            Completa los datos generales y presiona <b>Mostrar registro</b>.
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

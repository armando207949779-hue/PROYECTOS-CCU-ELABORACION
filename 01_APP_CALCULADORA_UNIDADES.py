# =====================================================
# 01_APP_CALCULADORA_UNIDADES.py
# APP CALCULADORA DE MATERIAS PRIMAS POR UNIDADES
# PROYECTO CCU - ELABORACIÓN
# =====================================================

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date

# =====================================================
# CONFIGURACIÓN GENERAL
# =====================================================

st.set_page_config(
    page_title="Calculadora de Unidades - CCU",
    page_icon="🧮",
    layout="wide"
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
    .main-title {
        font-size: 34px;
        font-weight: 800;
        color: #003865;
        margin-bottom: 0px;
    }

    .subtitle {
        font-size: 18px;
        color: #555555;
        margin-top: 0px;
        margin-bottom: 25px;
    }

    .card {
        background-color: #F8F9FA;
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #E1E4E8;
        margin-bottom: 15px;
    }

    .metric-box {
        background-color: #EAF3F8;
        padding: 16px;
        border-radius: 10px;
        border-left: 6px solid #003865;
        text-align: center;
    }

    .metric-number {
        font-size: 26px;
        font-weight: 800;
        color: #003865;
    }

    .metric-label {
        font-size: 14px;
        color: #555555;
    }

    .footer {
        font-size: 12px;
        color: #777777;
        text-align: center;
        margin-top: 35px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =====================================================
# FUNCIONES
# =====================================================

@st.cache_data
def cargar_bbdd():
    """
    Carga la BBDD desde archivo Parquet.
    """
    if not ARCHIVO_BBDD.exists():
        st.error(f"No se encontró el archivo BBDD: {ARCHIVO_BBDD}")
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
        ["Tipo de elaboración", "Materia prima"],
        ascending=[True, True]
    ).reset_index(drop=True)

    return df


def generar_calculo(df_filtrado, unidades):
    """
    Calcula la cantidad requerida según número de unidades.
    """
    df_resultado = df_filtrado.copy()

    df_resultado["Unidades solicitadas"] = unidades

    df_resultado["Cantidad requerida"] = (
        df_resultado["Cantidad por unidad"] * unidades
    )

    df_resultado = df_resultado[
        [
            "Tipo de elaboración",
            "Materia prima",
            "Código",
            "Unidad medida",
            "Cantidad por unidad",
            "Unidades solicitadas",
            "Cantidad requerida"
        ]
    ].copy()

    return df_resultado


def convertir_excel(df):
    """
    Convierte el resultado a Excel para descarga.
    """
    from io import BytesIO

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Calculo materias primas")

        workbook = writer.book
        worksheet = writer.sheets["Calculo materias primas"]

        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        fill_header = PatternFill("solid", fgColor="1F4E78")
        font_header = Font(color="FFFFFF", bold=True)
        thin = Side(style="thin", color="D9D9D9")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        for cell in worksheet[1]:
            cell.fill = fill_header
            cell.font = font_header
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = border

        for row in worksheet.iter_rows(min_row=2):
            for cell in row:
                cell.border = border
                cell.alignment = Alignment(vertical="top", wrap_text=True)

        worksheet.freeze_panes = "A2"
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


# =====================================================
# CARGA BBDD
# =====================================================

df_bbdd = cargar_bbdd()

# =====================================================
# ENCABEZADO
# =====================================================

col_logo, col_titulo = st.columns([1, 6])

with col_logo:
    if ARCHIVO_LOGO.exists():
        st.image(str(ARCHIVO_LOGO), width=95)
    else:
        st.write("")

with col_titulo:
    st.markdown(
        """
        <div class="main-title">Calculadora de Unidades - Materias Primas</div>
        <div class="subtitle">Proyecto CCU - Elaboración</div>
        """,
        unsafe_allow_html=True
    )

st.divider()

# =====================================================
# PANEL PRINCIPAL
# =====================================================

st.markdown("### Parámetros de cálculo")

col1, col2, col3 = st.columns([3, 1.2, 1.2])

tipos_elaboracion = sorted(df_bbdd["Tipo de elaboración"].unique())

with col1:
    tipo_seleccionado = st.selectbox(
        "Tipo de elaboración",
        options=tipos_elaboracion,
        index=0
    )

with col2:
    unidades = st.number_input(
        "Número de unidades",
        min_value=1,
        value=1,
        step=1
    )

with col3:
    fecha_calculo = st.date_input(
        "Fecha cálculo",
        value=date.today()
    )

# =====================================================
# FILTRAR Y CALCULAR
# =====================================================

df_filtrado = df_bbdd[
    df_bbdd["Tipo de elaboración"] == tipo_seleccionado
].copy()

df_resultado = generar_calculo(
    df_filtrado=df_filtrado,
    unidades=unidades
)

# =====================================================
# MÉTRICAS
# =====================================================

st.markdown("### Resumen")

col_m1, col_m2, col_m3 = st.columns(3)

with col_m1:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-number">{len(df_resultado)}</div>
            <div class="metric-label">Materias primas</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_m2:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-number">{unidades}</div>
            <div class="metric-label">Unidades solicitadas</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col_m3:
    st.markdown(
        f"""
        <div class="metric-box">
            <div class="metric-number">{df_bbdd['Tipo de elaboración'].nunique()}</div>
            <div class="metric-label">Elaboraciones disponibles</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()

# =====================================================
# RESULTADO
# =====================================================

st.markdown("### Materias primas requeridas")

df_mostrar = df_resultado.copy()

df_mostrar["Cantidad por unidad"] = df_mostrar["Cantidad por unidad"].round(6)
df_mostrar["Cantidad requerida"] = df_mostrar["Cantidad requerida"].round(6)

st.dataframe(
    df_mostrar,
    use_container_width=True,
    hide_index=True
)

# =====================================================
# RESUMEN POR UNIDAD DE MEDIDA
# =====================================================

st.markdown("### Resumen por unidad de medida")

df_resumen_unidad = (
    df_resultado
    .groupby("Unidad medida", as_index=False)
    .agg(
        Cantidad_total=("Cantidad requerida", "sum"),
        Numero_materias_primas=("Materia prima", "count")
    )
)

df_resumen_unidad["Cantidad_total"] = df_resumen_unidad["Cantidad_total"].round(6)

st.dataframe(
    df_resumen_unidad,
    use_container_width=True,
    hide_index=True
)

# =====================================================
# DESCARGA
# =====================================================

st.markdown("### Descargar cálculo")

archivo_excel = convertir_excel(df_resultado)

nombre_descarga = (
    "CALCULO_MATERIAS_PRIMAS_"
    + tipo_seleccionado.replace(" ", "_").replace("/", "-")
    + ".xlsx"
)

st.download_button(
    label="Descargar resultado en Excel",
    data=archivo_excel,
    file_name=nombre_descarga,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# =====================================================
# INFORMACIÓN DE BBDD
# =====================================================

with st.expander("Ver información de la BBDD"):
    st.write("Archivo usado como BBDD:")
    st.code("BBDD_UNIDADES_MATERIAS_PRIMAS.parquet")

    st.write("Columnas disponibles:")
    st.write(list(df_bbdd.columns))

    st.write("Vista previa BBDD:")
    st.dataframe(
        df_bbdd.head(20),
        use_container_width=True,
        hide_index=True
    )

# =====================================================
# PIE DE PÁGINA
# =====================================================

st.markdown(
    """
    <div class="footer">
    App desarrollada para Proyecto CCU - Elaboración | BBDD en formato Parquet
    </div>
    """,
    unsafe_allow_html=True
)

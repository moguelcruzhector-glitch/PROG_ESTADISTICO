import re
import unicodedata
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Panel de Nutrición UNICACH",
    page_icon="📊",
    layout="wide",
)


# Asociaciones entre las secciones del panel y posibles nombres
# de columnas del archivo CSV.
ALIAS = {
    "sexo": ["sexo", "genero", "género"],
    "edad": ["edad", "años", "anios"],
    "ocupacion": ["ocupacion", "ocupación", "profesion", "profesión"],
    "imc": ["imc", "indice de masa corporal", "índice de masa corporal"],
    "icc": ["icc", "indice cintura cadera", "índice cintura cadera"],
    "desparasitacion": ["desparasitacion", "desparasitación", "desparasitado"],
    "educacion": ["educacion", "educación", "escolaridad", "nivel educativo"],
    "lugar_compra": ["lugar de compra", "lugar_compra", "donde compra", "dónde compra"],
    "frecuencia_alimentos": [
        "frecuencia de alimentos",
        "frecuencia_alimentos",
        "consumo de alimentos",
        "alimentos que consume",
    ],
    "realiza_af": [
        "realiza actividad fisica",
        "realiza actividad física",
        "actividad fisica",
        "actividad física",
        "hace ejercicio",
    ],
    "tipo_af": ["tipo de actividad fisica", "tipo de actividad física", "tipo_af"],
    "nivel_af": ["nivel de actividad fisica", "nivel de actividad física", "nivel_af"],
    "traslado": ["traslado", "medio de transporte", "transporte"],
    "interes": ["interes", "interés", "interes en actividad fisica", "interés en actividad física"],
    "salud_emocional": [
        "salud emocional",
        "salud_emocional",
        "estado emocional",
        "emociones",
    ],
    "cultivos": ["cultivos", "cultivo", "siembra"],
    "animales": ["animales", "animal", "crianza"],
}


def normalizar(texto):
    """Convierte texto a minúsculas y elimina acentos y símbolos."""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(caracter for caracter in texto if unicodedata.category(caracter) != "Mn")
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return texto.strip()


def encontrar_columna(df, clave):
    """Busca en el CSV una columna relacionada con la sección solicitada."""
    nombres = {normalizar(columna): columna for columna in df.columns}
    opciones = [normalizar(opcion) for opcion in ALIAS.get(clave, [clave])]

    for opcion in opciones:
        if opcion in nombres:
            return nombres[opcion]

    for nombre_normalizado, nombre_original in nombres.items():
        for opcion in opciones:
            if opcion and (opcion in nombre_normalizado or nombre_normalizado in opcion):
                return nombre_original

    return None


def cargar_datos(archivo):
    """Intenta leer el archivo CSV con codificaciones comunes."""
    codificaciones = ["utf-8", "utf-8-sig", "latin-1"]

    for codificacion in codificaciones:
        try:
            archivo.seek(0)
            return pd.read_csv(archivo, encoding=codificacion)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue

    st.error("No se pudo leer el CSV. Revisa que el archivo esté separado por comas.")
    return None


def _img_tag(nombre_archivo, texto_alternativo):
    """Devuelve una etiqueta de imagen si el archivo del logo existe."""
    ruta = Path(nombre_archivo)

    if not ruta.exists():
        return ""

    return (
        f'<img src="{ruta.name}" alt="{texto_alternativo}" '
        'style="height:58px; width:auto; object-fit:contain; margin-right:16px;">'
    )


def es_columna_numerica(serie):
    """Detecta columnas numéricas aunque sus valores vengan como texto."""
    convertida = pd.to_numeric(serie, errors="coerce")
    return convertida.notna().sum() > 0 and convertida.notna().mean() >= 0.7


def mostrar_slot(df, clave):
    """Muestra una gráfica para la columna asociada a una sección."""
    columna = encontrar_columna(df, clave)

    if columna is None:
        st.info(
            f"No encontré una columna relacionada con **{clave.replace('_', ' ')}** "
            "en el CSV."
        )
        return

    serie = df[columna].dropna()

    if serie.empty:
        st.info(f"La columna **{columna}** no tiene respuestas.")
        return

    st.markdown(f"#### {columna}")

    if es_columna_numerica(serie):
        valores = pd.to_numeric(serie, errors="coerce").dropna()

        if valores.empty:
            st.info("No hay valores numéricos válidos para graficar.")
            return

        figura = px.histogram(
            x=valores,
            nbins=20,
            labels={"x": columna, "count": "Respuestas"},
            title=f"Distribución de {columna}",
            color_discrete_sequence=["#247A73"],
        )
        figura.update_layout(
            xaxis_title=columna,
            yaxis_title="Respuestas",
            bargap=0.08,
        )
        st.plotly_chart(figura, use_container_width=True)
    else:
        conteo = (
            serie.astype(str)
            .str.strip()
            .replace("", pd.NA)
            .dropna()
            .value_counts()
            .head(20)
            .rename_axis("Respuesta")
            .reset_index(name="Personas")
        )

        if conteo.empty:
            st.info("No hay respuestas para graficar.")
            return

        figura = px.bar(
            conteo,
            x="Respuesta",
            y="Personas",
            title=f"Respuestas de {columna}",
            color_discrete_sequence=["#247A73"],
        )
        figura.update_layout(
            xaxis_title="Respuesta",
            yaxis_title="Número de personas",
            xaxis_tickangle=-30,
        )
        st.plotly_chart(figura, use_container_width=True)


def pestana_constructor(df):
    """Permite crear una gráfica eligiendo columnas del archivo."""
    st.markdown("#### Crea una gráfica con tus datos")

    columnas = list(df.columns)

    if not columnas:
        st.info("El archivo no contiene columnas.")
        return

    col1, col2 = st.columns(2)

    with col1:
        columna = st.selectbox("Selecciona una pregunta", columnas)

    with col2:
        tipo_grafica = st.selectbox(
            "Tipo de gráfica",
            ["Barras", "Pastel", "Histograma", "Caja"],
        )

    datos = df[[columna]].dropna().copy()

    if datos.empty:
        st.info("La columna seleccionada no tiene respuestas.")
        return

    datos[columna] = datos[columna].astype(str).str.strip()

    if tipo_grafica == "Histograma":
        valores = pd.to_numeric(df[columna], errors="coerce").dropna()

        if valores.empty:
            st.warning("El histograma necesita una columna con valores numéricos.")
            return

        figura = px.histogram(
            x=valores,
            nbins=20,
            labels={"x": columna, "count": "Respuestas"},
            title=f"Histograma de {columna}",
            color_discrete_sequence=["#247A73"],
        )

    elif tipo_grafica == "Caja":
        valores = pd.to_numeric(df[columna], errors="coerce").dropna()

        if valores.empty:
            st.warning("La gráfica de caja necesita una columna numérica.")
            return

        figura = px.box(
            y=valores,
            labels={"y": columna},
            title=f"Gráfica de caja de {columna}",
            color_discrete_sequence=["#247A73"],
        )

    else:
        conteo = (
            datos[columna]
            .value_counts()
            .head(30)
            .rename_axis("Respuesta")
            .reset_index(name="Personas")
        )

        if tipo_grafica == "Pastel":
            figura = px.pie(
                conteo,
                names="Respuesta",
                values="Personas",
                title=f"Respuestas de {columna}",
                color_discrete_sequence=px.colors.sequential.Teal,
            )
        else:
            figura = px.bar(
                conteo,
                x="Respuesta",
                y="Personas",
                title=f"Respuestas de {columna}",
                color_discrete_sequence=["#247A73"],
            )
            figura.update_layout(xaxis_tickangle=-30)

    st.plotly_chart(figura, use_container_width=True)


def main():
    st.markdown(
        """
        <style>
        .main {
            background-color: #f5f7f5;
        }
        .titulo-panel {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 0 2px 0;
        }
        .titulo-panel h1 {
            color: #173d3a;
            margin: 0;
            font-size: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="titulo-panel"><h1>Clínica de Nutrición UNICACH</h1>'
        + _img_tag("logo_clinica.png", "Clínica de Nutrición UNICACH")
        + "</div>",
        unsafe_allow_html=True,
    )

    st.caption(
        "Panel interactivo para explorar respuestas, consultar indicadores "
        "y comparar resultados por área."
    )

    with st.sidebar:
        st.markdown("## Cargar encuesta")
        st.caption("Selecciona un archivo CSV para habilitar los indicadores y gráficas.")
        archivo = st.file_uploader("Sube tu archivo CSV aquí", type=["csv"])

        if archivo is not None:
            st.success(f"Archivo seleccionado: {archivo.name}")
        else:
            st.info("Selecciona un archivo CSV para comenzar.")

    if archivo is None:
        st.info(
            "Para comenzar, carga tu encuesta en el panel lateral. "
            "Después podrás explorar los resultados por área y crear gráficas."
        )
        return

    df = cargar_datos(archivo)

    if df is None or df.empty:
        st.error("El archivo no contiene datos o no se pudo cargar.")
        return

    df.columns = [str(columna).strip() for columna in df.columns]

    st.markdown("### Resumen de la encuesta")

    total_celdas = len(df) * len(df.columns)
    celdas_vacias = int(df.isna().sum().sum())
    porcentaje_completo = (
        (1 - celdas_vacias / total_celdas) * 100 if total_celdas else 0
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Total de respuestas", len(df))
    col2.metric("Total de preguntas", len(df.columns))
    col3.metric("Datos completos", f"{porcentaje_completo:.1f}%")

    tabs = st.tabs(
        [
            "Demografía",
            "Estado nutricional",
            "Salud y educación",
            "Alimentación",
            "Actividad física",
            "Salud emocional",
            "Cultivos y animales",
            "Constructor de gráficas",
        ]
    )

    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        with c1:
            mostrar_slot(df, "sexo")
        with c2:
            mostrar_slot(df, "edad")
        with c3:
            mostrar_slot(df, "ocupacion")

    with tabs[1]:
        c1, c2 = st.columns(2)
        with c1:
            mostrar_slot(df, "imc")
        with c2:
            mostrar_slot(df, "icc")

    with tabs[2]:
        c1, c2 = st.columns(2)
        with c1:
            mostrar_slot(df, "desparasitacion")
        with c2:
            mostrar_slot(df, "educacion")

    with tabs[3]:
        c1, c2 = st.columns(2)
        with c1:
            mostrar_slot(df, "lugar_compra")
        with c2:
            mostrar_slot(df, "frecuencia_alimentos")

        st.caption(
            "Las gráficas muestran las respuestas encontradas en las columnas "
            "correspondientes del archivo."
        )

    with tabs[4]:
        c1, c2, c3 = st.columns(3)
        with c1:
            mostrar_slot(df, "realiza_af")
        with c2:
            mostrar_slot(df, "tipo_af")
        with c3:
            mostrar_slot(df, "nivel_af")

        c4, c5 = st.columns(2)
        with c4:
            mostrar_slot(df, "traslado")
        with c5:
            mostrar_slot(df, "interes")

    with tabs[5]:
        mostrar_slot(df, "salud_emocional")

    with tabs[6]:
        c1, c2 = st.columns(2)
        with c1:
            mostrar_slot(df, "cultivos")
        with c2:
            mostrar_slot(df, "animales")

    with tabs[7]:
        pestana_constructor(df)

    resumen = pd.DataFrame(
        {
            "Pregunta": df.columns,
            "Tipo de dato": [
                "Numérico" if es_columna_numerica(df[columna]) else "Texto"
                for columna in df.columns
            ],
            "Valores válidos": [int(df[columna].notna().sum()) for columna in df.columns],
            "Valores únicos": [int(df[columna].nunique()) for columna in df.columns],
        }
    )

    with st.sidebar:
        st.markdown("---")
        st.download_button(
            label="Descargar resumen",
            data=resumen.to_csv(index=False).encode("utf-8-sig"),
            file_name="resumen_analisis.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()

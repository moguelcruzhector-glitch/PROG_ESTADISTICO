"""
Dashboard Especializado para Encuestas de Nutrición
Diseñado para Nutriólogos - Un gráfico por pregunta
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import numpy as np
import re
import unicodedata

# Configuración
st.set_page_config(
    page_title="Análisis Nutricional",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)


def aplicar_estilo():
    """CSS profesional para nutriólogos"""
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #0f8b4f 0%, #1a5f3e 100%);
            background-attachment: fixed;
        }
        
        [data-testid="stMainBlockContainer"] {
            background: rgba(255, 255, 255, 0.94);
            border-radius: 15px;
            padding: 1rem 1.5rem;
            margin: 0.5rem;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0a4d2c 0%, #0f8b4f 100%);
        }
        
        [data-testid="stSidebar"] * {
            color: #f0f9f7;
        }
        
        .hero {
            background: linear-gradient(135deg, #0f8b4f 0%, #16c784 100%);
            padding: 1rem;
            border-radius: 15px;
            text-align: center;
            color: white;
            margin-bottom: 1rem;
            box-shadow: 0 10px 35px rgba(15, 139, 79, 0.4);
        }
        
        .hero h1 {
            margin: 0;
            font-size: 1.8rem;
            font-weight: bold;
        }
        
        .hero p {
            margin: 0.3rem 0 0;
            font-size: 0.95rem;
            opacity: 0.95;
        }
        
        h2 {
            color: #0f8b4f;
            border-bottom: 3px solid #16c784;
            padding-bottom: 0.7rem;
            margin-bottom: 1.5rem;
        }
        
        h3 {
            color: #1a5f3e;
            margin-top: 1.5rem;
        }
        
        [data-testid="stMetric"] {
            background: linear-gradient(135deg, #ecf9f5 0%, #dff7f0 100%);
            padding: 0.6rem 1rem;
            border-radius: 10px;
            border-left: 4px solid #16c784;
        }
        
        hr {
            background: linear-gradient(90deg, transparent, #16c784, transparent);
            border: none;
            height: 2px;
            margin: 1rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def cargar_datos(archivo=None):
    """Carga el CSV (prueba varias codificaciones para evitar errores con acentos y eñes)"""
    try:
        if archivo is not None:
            df = None
            for codificacion in ("utf-8-sig", "utf-8", "latin-1"):
                try:
                    archivo.seek(0)  # volver al inicio antes de cada intento
                    df = pd.read_csv(archivo, encoding=codificacion)
                    break
                except UnicodeDecodeError:
                    continue
            if df is None:
                st.error("No se pudo leer el archivo (codificación no reconocida)")
                return None
        else:
            df = pd.read_csv("diana.csv")

        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return None


def limpiar_columna(col_name):
    """Limpia nombres de columnas para hacerlos legibles"""
    return col_name.replace('_', ' ').title()


def explotar_valores_multiples(df, columna):
    """Explota valores separados por comas en una columna y retorna serie expandida"""
    valores_expandidos = []
    
    for val in df[columna]:
        # Saltar NaN o vacíos
        if pd.isna(val):
            continue
        
        val_str = str(val).strip()
        
        # --- EL TRUCO ESTÁ AQUÍ ---
        # Reemplazar la coma por un punto SOLO si está entre dos números (ej. "1,67" -> "1.67")
        val_str = re.sub(r'(\d),(\d)', r'\1.\2', val_str)
        
        if val_str == '' or val_str.lower() == 'ninguno':
            continue
        
        # Si tiene comas, SEPARAR CADA VALOR
        if ',' in val_str:
            # Dividir por coma y limpiar cada parte
            partes = val_str.split(',')
            for parte in partes:
                parte_limpia = parte.strip()
                # Solo agregar si no está vacío
                if parte_limpia and parte_limpia.lower() != 'ninguno':
                    valores_expandidos.append(parte_limpia)
        else:
            # Sin comas, agregar como está
            valores_expandidos.append(val_str)
    
    return pd.Series(valores_expandidos)


# Errores de ortografía conocidos del CSV: "texto mal escrito": "texto correcto"
CORRECCIONES = {
    "cardiovacular": "cardiovascular",
    r"^37$": "3/7",                     # frijoles: "37" era "3/7"
    r"(\d)(AM|PM)": r"\1 \2",          # "4:00PM" -> "4:00 PM"
    r"^Mercado, Supermercados$": "Mercado y supermercados",   # ambas = una sola respuesta
}

# Columnas donde la coma NO separa respuestas (cada celda es una sola respuesta)
COLUMNAS_SIN_SEPARAR = {"lugar donde los compra"}


def _normalizar(texto):
    """Minúsculas, sin acentos y sin espacios extra (energía -> energia)"""
    texto = unicodedata.normalize("NFD", str(texto).lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r'\s+', ' ', texto).strip()


def unificar_categorias(serie):
    """Junta como una sola categoría los valores que solo difieren en
    espacios dobles, espacios al final, mayúsculas/minúsculas, acentos o
    errores de ortografía listados en CORRECCIONES."""
    def limpiar(v):
        v = re.sub(r'\s+', ' ', str(v)).strip()
        for mal, bien in CORRECCIONES.items():
            v = re.sub(mal, bien, v, flags=re.IGNORECASE)
        return v

    limpios = serie.map(limpiar)
    claves = limpios.map(_normalizar)
    # Etiqueta final: la forma más frecuente de cada grupo
    etiquetas = limpios.groupby(claves).agg(lambda s: s.value_counts().index[0])
    return claves.map(etiquetas)


# ---------------------------------------------------------------- COLORES
PALETA = ["#6C5CE7", "#00B894", "#FD79A8", "#FDCB6E", "#0984E3",
          "#E17055", "#00CEC9", "#A29BFE", "#FF7675", "#55EFC4"]

# Colores con significado (clave = categoría en minúsculas y sin acentos)
COLORES_FIJOS = {
    # Sexo
    "femenino": "#F472B6", "mujer": "#F472B6",      # rosa
    "masculino": "#3B82F6", "hombre": "#3B82F6",    # azul
    # Sí / No / Tal vez
    "si": "#00B894", "no": "#FF7675", "tal vez": "#FDCB6E",
    # IMC
    "normal": "#00B894", "sobrepeso": "#FDCB6E",
    "obesidad": "#E17055", "obesidad 1": "#FF9F43",
    "obesidad 2": "#E17055", "obesidad 3": "#D63031",
    # ICC
    "riesgo cardiovascular bajo": "#55D68A",
    "riesgo cardiovascular moderado": "#FDCB6E",
    "riesgo cardiovascular alto": "#E17055",
    "riesgo cardiovascular muy alto": "#D63031",
    # Nivel de actividad física
    "muy bajo": "#D63031", "bajo": "#E17055", "moderado": "#FDCB6E",
    "alto": "#55D68A", "muy alto": "#00B894",
    # Estado emocional
    "feliz": "#FDCB6E", "triste": "#0984E3", "ansioso": "#A29BFE",
    "enojado": "#D63031", "frustrado": "#E17055", "deprimido": "#636E72",
}


def _mapa_colores(categorias, originales=None):
    """Color por categoría: fijo si tiene significado, si no, de la paleta."""
    originales = originales or categorias
    mapa = {}
    for j, (nombre, original) in enumerate(zip(categorias, originales)):
        mapa[nombre] = COLORES_FIJOS.get(_normalizar(original), PALETA[j % len(PALETA)])
    return mapa


# ---------------------------------------------------------------- DATOS
def buscar_columna(df, nombre):
    """Encuentra la columna aunque cambien espacios, mayúsculas o acentos."""
    clave = _normalizar(nombre)
    for c in df.columns:
        if _normalizar(c) == clave:
            return c
    return None


def conteos_columna(df, nombre, separar=True):
    """Cuenta las respuestas de una columna (separando por comas con la función original)."""
    col = buscar_columna(df, nombre)
    if col is None:
        st.info(f"No encontré la columna «{nombre}» en el archivo.")
        return None
    if (not separar) or _normalizar(col) in COLUMNAS_SIN_SEPARAR:
        datos = df[col].dropna().astype(str)
        datos = datos[datos.str.strip() != ""]
    else:
        datos = explotar_valores_multiples(df, col)
    if len(datos) == 0:
        st.warning(f"Sin datos para {nombre}")
        return None
    return unificar_categorias(datos).value_counts()


def contar_si_no(df, nombre):
    """(personas que dijeron Sí, personas que dijeron No)"""
    col = buscar_columna(df, nombre)
    if col is None:
        return 0, 0
    datos = df[col].dropna().map(_normalizar)
    return int((datos == "si").sum()), int((datos == "no").sum())


def _ordenar(conteos, orden_fijo=None):
    """Mayor a menor, o el orden indicado."""
    if orden_fijo:
        pos = {_normalizar(x): i for i, x in enumerate(orden_fijo)}
        return sorted(conteos.index, key=lambda c: pos.get(_normalizar(c), 99))
    return list(conteos.index)


# ---------------------------------------------------------------- GRÁFICAS
def _layout(fig, alto, titulo_size=14):
    fig.update_layout(
        height=alto,
        margin=dict(t=50, b=20, l=10, r=30),
        title_font_size=titulo_size,
        showlegend=False,
    )


def grafico_barras(conteos, titulo, horizontal=False, nombres_dentro=False,
                   orden_fijo=None, color_unico=None):
    """Barras con color por categoría. 'nombres_dentro' escribe el nombre dentro de la barra."""
    cats = _ordenar(conteos, orden_fijo)
    df_g = pd.DataFrame({'Categoría': cats, 'Cantidad': [int(conteos[c]) for c in cats]})
    mapa = _mapa_colores(cats)
    color_arg = {} if color_unico else dict(color='Categoría', color_discrete_map=mapa)

    if nombres_dentro:
        horizontal = True
        df_g['Texto'] = df_g['Categoría'] + "  ·  " + df_g['Cantidad'].astype(str)

    if horizontal:
        fig = px.bar(df_g, x='Cantidad', y='Categoría', orientation='h',
                     text='Texto' if nombres_dentro else 'Cantidad', title=titulo, **color_arg)
        fig.update_yaxes(autorange='reversed', title=None)
        fig.update_xaxes(title=None, showgrid=False)
        if nombres_dentro:
            fig.update_yaxes(showticklabels=False)
            fig.update_traces(textposition='inside', insidetextanchor='start',
                              constraintext='none')
            maximo = max(df_g['Cantidad'])
            texto_color = {r['Categoría']: ("white" if r['Cantidad'] / maximo >= 0.45 else "#2d3436")
                           for _, r in df_g.iterrows()}
            fig.for_each_trace(lambda t: t.update(
                textfont=dict(color=texto_color.get(t.name, "white"), size=13)))
        else:
            fig.update_traces(textposition='outside', cliponaxis=False)
        alto = min(440, 110 + 34 * len(cats))
    else:
        fig = px.bar(df_g, x='Categoría', y='Cantidad', text='Cantidad', title=titulo, **color_arg)
        fig.update_xaxes(title=None, categoryorder='array', categoryarray=cats)
        fig.update_yaxes(title="Personas")
        fig.update_traces(textposition='outside', cliponaxis=False)
        alto = 360

    if color_unico:
        fig.update_traces(marker_color=color_unico)
    fig.update_layout(bargap=0.25)
    _layout(fig, alto)
    return fig


def grafico_pastel(conteos, titulo, etiquetas_en_grafica=True, abreviar=None, hole=0.45):
    """Pastel / dona. Con etiquetas_en_grafica muestra el nombre (diagnóstico) y el % sobre el pastel."""
    cats = list(conteos.index)
    nombres = [abreviar(c) for c in cats] if abreviar else cats
    df_g = pd.DataFrame({'Categoría': nombres, 'Cantidad': [int(conteos[c]) for c in cats]})
    mapa = _mapa_colores(nombres, cats)
    fig = px.pie(df_g, values='Cantidad', names='Categoría', title=titulo,
                 color='Categoría', color_discrete_map=mapa, hole=hole)
    if etiquetas_en_grafica:
        fig.update_traces(textinfo='label+percent', textposition='outside',
                          textfont_size=13, pull=0.02)
        fig.update_layout(height=380, margin=dict(t=60, b=30, l=60, r=60),
                          title_font_size=14, showlegend=False)
    else:
        fig.update_layout(height=380, margin=dict(t=60, b=20, l=20, r=20),
                          title_font_size=14, showlegend=True, legend=dict(x=1.0, y=1))
    return fig


def mostrar(fig, clave):
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, key=clave)


# ---- Cada pregunta
def g_sexo(df):
    c = conteos_columna(df, "Sexo")
    return None if c is None else grafico_pastel(c, f"Sexo (n={int(c.sum())})")


def g_edad(df):
    col = buscar_columna(df, "Edad")
    if col is None:
        st.info("No encontré la columna «Edad».")
        return None
    edades = pd.to_numeric(df[col], errors='coerce').dropna()
    if len(edades) == 0:
        st.warning("Sin datos para Edad")
        return None
    ini, fin = int(edades.min() // 10 * 10), int(edades.max() // 10 * 10)
    rangos = {f"{a}-{a + 9}": int(((edades >= a) & (edades <= a + 9)).sum())
              for a in range(ini, fin + 1, 10)}
    conteos = pd.Series(rangos)
    return grafico_barras(conteos, f"Edad por rangos (n={len(edades)} · promedio {edades.mean():.0f} años)",
                          orden_fijo=list(conteos.index))


def g_ocupacion(df):
    c = conteos_columna(df, "Ocupacion")
    return None if c is None else grafico_barras(c, f"Ocupación (n={int(c.sum())})")


def g_imc(df):
    c = conteos_columna(df, "IMC")
    return None if c is None else grafico_pastel(c, f"IMC · diagnóstico (n={int(c.sum())})")


def g_icc(df):
    c = conteos_columna(df, "ICC")
    if c is None:
        return None
    return grafico_pastel(c, f"ICC · diagnóstico (n={int(c.sum())})",
                          abreviar=lambda x: x.replace("Riesgo cardiovascular ", "Riesgo "))


def _a_meses(texto):
    """'15 dias' -> 0.5 · '3 meses' -> 3 · '1 año y 4 meses' -> 16. None si no entiende."""
    t = _normalizar(texto)
    total, hallado = 0.0, False
    for num, unidad in re.findall(r'(\d+(?:\.\d+)?)\s*(dias?|semanas?|mes(?:es)?|anos?)', t):
        hallado = True
        n = float(num)
        if unidad.startswith("dia"):
            total += n / 30
        elif unidad.startswith("semana"):
            total += n * 7 / 30
        elif unidad.startswith("mes"):
            total += n
        else:
            total += n * 12
    return total if hallado else None


def g_desparasitacion(df):
    c = conteos_columna(df, "Ultima vez", separar=False)
    if c is None:
        return None
    orden = sorted(c.index, key=lambda x: (_a_meses(x) is None, _a_meses(x) or 0))
    si, no = contar_si_no(df, "Desparasitacion")
    titulo = f"Última vez que se desparasitaron (Sí: {si} · No: {no})"
    return grafico_barras(c, titulo, orden_fijo=orden, color_unico="#00B894")


def g_lugar_compra(df):
    c = conteos_columna(df, "Lugar donde los compra", separar=False)
    return None if c is None else grafico_barras(c, f"Lugar de compra (n={int(c.sum())})",
                                                 nombres_dentro=True)


# Frecuencia de alimentos: rangos que usó el equipo al capturar (3/7, 2/7, 1/7)
RANGOS_FRECUENCIA = {
    "3/7 · Carnes a Huevo": ["Carne de res", "Carne de puerco", "Pescado", "Pollo o gallina",
                             "Frutas", "Verduras", "Frijoles", "Lentejas", "Garbanzos", "Arroz",
                             "Leche", "Queso", "Crema", "Huevo"],
    "2/7 · Galletas a Energéticas": ["Galletas dulces", "Pan dulce", "Sabritas",
                                     "Refrescos embotellados", "Chocolates", "Dulces",
                                     "Bebidas energeticas"],
    "1/7 · Sopas a Sal": ["Sopas instantaneas", "Salchicha", "Jamon", "Tocino", "Chorizo",
                          "Rikopollo", "Knor", "Sal"],
}
COLORES_RANGOS = ["#6C5CE7", "#FD79A8", "#00B894"]


def g_frecuencia_alimentos(df):
    total = len(df)
    filas = []
    for rango, alimentos in RANGOS_FRECUENCIA.items():
        parte = []
        for nombre in alimentos:
            col = buscar_columna(df, nombre)
            if col is None:
                continue
            marcados = int((df[col].notna() & (df[col].astype(str).str.strip() != "")).sum())
            parte.append((nombre, rango, marcados))
        filas += sorted(parte, key=lambda f: -f[2])   # dentro de cada rango, de más a menos
    if not filas:
        st.info("No encontré las columnas de alimentos.")
        return None
    df_g = pd.DataFrame(filas, columns=['Alimento', 'Frecuencia', 'Personas'])
    df_g['Texto'] = df_g['Personas'].astype(str) + " (" + (df_g['Personas'] / total * 100).round(0).astype(int).astype(str) + "%)"
    mapa = dict(zip(RANGOS_FRECUENCIA.keys(), COLORES_RANGOS))
    fig = px.bar(df_g, x='Alimento', y='Personas', color='Frecuencia', text='Texto',
                 color_discrete_map=mapa,
                 title=f"Alimentos que consumen, por frecuencia (n={total} personas)")
    fig.update_xaxes(title=None, categoryorder='array', categoryarray=list(df_g['Alimento']),
                     tickangle=-40)
    fig.update_yaxes(title="Personas")
    fig.update_traces(textposition='outside', cliponaxis=False, textfont_size=11)
    fig.update_layout(height=520, margin=dict(t=90, b=20, l=10, r=20), title_font_size=14,
                      bargap=0.2, legend=dict(orientation='h', y=1.12, x=0, title=None))
    return fig


def g_educacion(df):
    c = conteos_columna(df, "Cual")
    if c is None:
        return None
    si, no = contar_si_no(df, "Educacion nutricional")
    return grafico_barras(c, f"Tipo de educación nutricional (Sí: {si} · No: {no})",
                          nombres_dentro=True)


def g_emocional(df):
    c = conteos_columna(df, "Estado emocional frecuente")
    return None if c is None else grafico_barras(c, f"Estado emocional frecuente (n={int(c.sum())})",
                                                 horizontal=True)


def g_realiza_af(df):
    c = conteos_columna(df, "Realiza AF")
    return None if c is None else grafico_barras(c, "¿Realiza actividad física?")


def g_tipo_af(df):
    c = conteos_columna(df, "Cual.1")
    return None if c is None else grafico_barras(c, "Tipo de actividad física", horizontal=True)


def g_nivel_af(df):
    c = conteos_columna(df, "Nivel de AF")
    if c is None:
        return None
    return grafico_barras(c, "Nivel de actividad física",
                          orden_fijo=["Muy bajo", "Bajo", "Moderado", "Alto", "Muy alto"])


def g_traslado(df):
    c = conteos_columna(df, "Traslado")
    return None if c is None else grafico_barras(c, "Medio de traslado", horizontal=True)


def g_interes(df):
    """Mismo estilo de dona de antes, solo con colores nuevos."""
    c = conteos_columna(df, "Interes al Ejercicio")
    if c is None:
        return None
    return grafico_pastel(c, "Distribución: Interés Al Ejercicio",
                          etiquetas_en_grafica=False, hole=0.3)


def g_cultivos(df):
    """Se deja tal cual estaba: dona con la paleta original."""
    c = conteos_columna(df, "Cultiva algun alimento")
    if c is None:
        return None
    df_g = pd.DataFrame({'Categoría': c.index, 'Cantidad': c.values})
    fig = px.pie(df_g, values='Cantidad', names='Categoría',
                 title="Distribución: Cultiva Algun Alimento",
                 color_discrete_sequence=px.colors.qualitative.Set3, hole=0.3)
    fig.update_layout(height=380, margin=dict(t=60, b=20, l=20, r=20), title_font_size=16,
                      showlegend=True, legend=dict(x=1.0, y=1))
    return fig


def g_animales(df):
    c = conteos_columna(df, "Cuales")
    if c is None:
        return None
    si, no = contar_si_no(df, "Cuenta con algun animal en casa")
    return grafico_barras(c, f"Animales en casa (Sí cuentan: {si} · No: {no})", horizontal=True)


# ---------------------------------------------------------------- APP
def main():
    aplicar_estilo()

    # Header
    st.markdown("""
    <div class="hero">
        <h1>🥗 Análisis Nutricional</h1>
        <p>Resultados de la encuesta</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("## 📤 Cargar Encuesta")

        archivo = st.file_uploader("Sube tu archivo CSV aquí", type=["csv"])

        if archivo:
            st.success(f"✅ {archivo.name}")
        else:
            st.info("Selecciona un archivo CSV para comenzar")

    # Cargar datos
    if archivo is None:
        st.info("👆 Sube tu archivo CSV en el panel izquierdo para comenzar el análisis")
        return

    df = cargar_datos(archivo=archivo)

    if df is None or df.empty:
        st.error("No se pudieron cargar los datos. Verifica que sea un archivo CSV válido")
        return

    # Información general
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Respuestas", len(df))
    with col2:
        st.metric("Total de Preguntas", len(df.columns))
    with col3:
        st.metric("Datos Completos", f"{(1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100:.1f}%")

    tabs = st.tabs(["👥 Demografía", "⚖️ Estado Nutricional", "💊 Salud y Educación",
                    "🛒 Alimentación", "🏃 Actividad y Bienestar", "🌱 Cultivos y Animales"])

    with tabs[0]:
        c1, c2, c3 = st.columns(3)
        with c1:
            mostrar(g_sexo(df), "sexo")
        with c2:
            mostrar(g_edad(df), "edad")
        with c3:
            mostrar(g_ocupacion(df), "ocupacion")

    with tabs[1]:
        c1, c2 = st.columns(2)
        with c1:
            mostrar(g_imc(df), "imc")
        with c2:
            mostrar(g_icc(df), "icc")

    with tabs[2]:
        c1, c2 = st.columns(2)
        with c1:
            mostrar(g_desparasitacion(df), "desparasitacion")
        with c2:
            mostrar(g_educacion(df), "educacion")

    with tabs[3]:
        c1, c2 = st.columns([1, 2])
        with c1:
            mostrar(g_lugar_compra(df), "lugar_compra")
        with c2:
            mostrar(g_frecuencia_alimentos(df), "frecuencia_alimentos")
        st.caption("Cada barra cuenta las personas que marcaron ese alimento. "
                   "Los rangos 3/7, 2/7 y 1/7 son los de la tabla de captura.")

    with tabs[4]:
        c1, c2, c3 = st.columns(3)
        with c1:
            mostrar(g_realiza_af(df), "realiza_af")
        with c2:
            mostrar(g_tipo_af(df), "tipo_af")
        with c3:
            mostrar(g_nivel_af(df), "nivel_af")
        c4, c5, c6 = st.columns(3)
        with c4:
            mostrar(g_traslado(df), "traslado")
        with c5:
            mostrar(g_interes(df), "interes")
        with c6:
            mostrar(g_emocional(df), "emocional")

    with tabs[5]:
        c1, c2 = st.columns(2)
        with c1:
            mostrar(g_cultivos(df), "cultivos")
        with c2:
            mostrar(g_animales(df), "animales")

    # Descarga del resumen (un solo clic)
    resumen = pd.DataFrame({
        'Pregunta': df.columns,
        'Tipo de Dato': [
            'Numérico' if pd.api.types.is_numeric_dtype(df[col]) else 'Texto'
            for col in df.columns
        ],
        'Valores Válidos': [len(df[col].dropna()) for col in df.columns],
        'Valores Únicos': [df[col].nunique() for col in df.columns]
    })
    with st.sidebar:
        st.markdown("---")
        st.download_button(
            label="📥 Descargar resumen",
            data=resumen.to_csv(index=False),
            file_name="resumen_analisis.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()

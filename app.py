"""
Dashboard Especializado para Encuestas de Nutrición
Diseñado para Nutriólogos - Un gráfico por pregunta
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import numpy as np

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
            padding: 2rem;
            margin: 1.5rem;
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
            padding: 2.5rem;
            border-radius: 15px;
            text-align: center;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 10px 35px rgba(15, 139, 79, 0.4);
        }
        
        .hero h1 {
            margin: 0;
            font-size: 2.8rem;
            font-weight: bold;
        }
        
        .hero p {
            margin: 0.8rem 0 0;
            font-size: 1.15rem;
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
            padding: 1.5rem;
            border-radius: 10px;
            border-left: 4px solid #16c784;
        }
        
        hr {
            background: linear-gradient(90deg, transparent, #16c784, transparent);
            border: none;
            height: 2px;
            margin: 2rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def cargar_datos(archivo=None):
    """Carga el CSV"""
    try:
        if archivo is not None:
            df = pd.read_csv(archivo)
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


def crear_grafico_pregunta(df, columna):
    """Crea el gráfico más apropiado según el tipo de dato"""
    
    # Detectar si es columna numérica
    es_numerica = pd.api.types.is_numeric_dtype(df[columna])
    
    # Si es numérica, NO expandir por comas
    if es_numerica:
        datos_expandidos = df[columna].dropna()
    else:
        # Si es categórica, EXPLOTAR valores múltiples (separados por comas)
        datos_expandidos = explotar_valores_multiples(df, columna)
    
    if len(datos_expandidos) == 0:
        st.warning(f"Sin datos para {columna}")
        return None
    
    # Contar valores
    conteos = datos_expandidos.value_counts().sort_values(ascending=False)
    
    # Crear DataFrame para el gráfico
    df_grafico = pd.DataFrame({
        'Categoría': conteos.index,
        'Cantidad': conteos.values
    })
    
    # SIEMPRE usar gráfico de pastel (donut)
    fig = px.pie(
        df_grafico,
        values='Cantidad',
        names='Categoría',
        title=f"Distribución: {limpiar_columna(columna)}",
        color_discrete_sequence=px.colors.qualitative.Set3,
        hole=0.3  # Esto lo hace donut en lugar de pie completo
    )
    fig.update_layout(
        height=550,
        margin=dict(t=80, b=20, l=20, r=20),  # Margen superior más grande
        title_font_size=16,
        showlegend=True,
        legend=dict(x=1.05, y=1)  # Leyenda a la derecha
    )
    return fig


def agrupar_preguntas(df):
    """Agrupa preguntas por categoría"""
    
    grupos = {
        "Datos Demográficos": [col for col in df.columns if any(x in col.lower() for x in ['sexo', 'edad', 'escolaridad', 'ocupacion'])],
        
        "Medidas Antropométricas": [col for col in df.columns if any(x in col.lower() for x in ['peso', 'talla', 'cintura', 'cadera', 'pantorrilla', 'altura_rodilla', 'brazada'])],
        
        "Salud General": [col for col in df.columns if any(x in col.lower() for x in ['alergia', 'medicamento', 'desparasitado', 'padecimiento'])],
        
        "Horarios de Comidas": [col for col in df.columns if any(x in col.lower() for x in ['hora_desayuno', 'hora_comida', 'hora_cena'])],
        
        "Lugar de Compra": [col for col in df.columns if any(x in col.lower() for x in ['lugar_compra', 'compra_'])],
        
        "Consumo de Carnes": [col for col in df.columns if any(x in col.lower() for x in ['res', 'puerco', 'pescado', 'pollo', 'gallina']) and 'consumo' in col.lower()],
        
        "Consumo de Verduras y Frutas": [col for col in df.columns if any(x in col.lower() for x in ['frutas', 'verduras']) and 'consumo' in col.lower()],
        
        "Consumo de Leguminosas": [col for col in df.columns if any(x in col.lower() for x in ['frijoles', 'lentejas', 'garbanzo']) and 'consumo' in col.lower()],
        
        "Consumo de Lácteos": [col for col in df.columns if any(x in col.lower() for x in ['leche', 'queso', 'crema', 'huevo']) and 'consumo' in col.lower()],
        
        "Alimentos Ultraprocesados": [col for col in df.columns if any(x in col.lower() for x in ['galletas', 'pan_dulce', 'sabritas', 'refrescos', 'chocolates', 'dulces', 'energeticas']) and 'consumo' in col.lower()],
        
        "Productos Procesados": [col for col in df.columns if any(x in col.lower() for x in ['sopa', 'salchicha', 'jamon', 'tocino', 'chorizo', 'knorr', 'sal']) and 'consumo' in col.lower()],
        
        "Grasas de Cocina": [col for col in df.columns if any(x in col.lower() for x in ['aceite', 'manteca', 'margarina', 'mantequilla']) and 'cocina' in col.lower()],
        
        "Características de Vivienda": [col for col in df.columns if any(x in col.lower() for x in ['cuartos', 'techo', 'pared', 'piso', 'tenencia', 'combustible', 'agua', 'energia', 'sanitario', 'basura'])],
        
        "Educación Nutricional": [col for col in df.columns if 'educacion' in col.lower()],
        
        "Estado Emocional": [col for col in df.columns if any(x in col.lower() for x in ['emocional', 'triste', 'dormir', 'preocupado', 'pensamientos', 'malestar'])],
        
        "Actividad Física": [col for col in df.columns if any(x in col.lower() for x in ['actividad_fisica', 'ejercicio', 'traslado', 'horas_sentado', 'nivel_actividad', 'interes'])],
        
        "Agricultura y Ganadería": [col for col in df.columns if any(x in col.lower() for x in ['cultiva', 'alimentos_producidos', 'espacio', 'animales', 'cria', 'aves', 'conejos'])]
    }
    
    # Filtrar grupos vacíos
    return {k: v for k, v in grupos.items() if v}


def main():
    aplicar_estilo()
    
    # Header
    st.markdown("""
    <div class="hero">
        <h1>🥗 Análisis Nutricional</h1>
        <p>Un gráfico por pregunta - Encuesta Completa</p>
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
        
        st.markdown("---")
        
        st.markdown("### ✨ Características")
        st.markdown("""
        • Un gráfico por pregunta
        • Agrupado por categorías
        • Gráficos automáticos
        • Análisis completo
        """)
    
    # Cargar datos
    if archivo is None:
        # Si no hay archivo, mostrar mensaje y salir
        st.info("👆 Sube tu archivo CSV en el panel izquierdo para comenzar el análisis")
        return
    
    # Cargar el archivo subido
    df = cargar_datos(archivo=archivo)
    
    if df is None or df.empty:
        st.error("No se pudieron cargar los datos. Verifica que sea un archivo CSV válido")
        return
    
    # Información general
    st.subheader("📊 Resumen de Datos")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Respuestas", len(df))
    with col2:
        st.metric("Total de Preguntas", len(df.columns))
    with col3:
        st.metric("Datos Completos", f"{(1 - df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100:.1f}%")
    
    st.markdown("---")
    
    # Agrupar preguntas
    grupos = agrupar_preguntas(df)
    
    # Crear tabs por grupo
    tabs = st.tabs(list(grupos.keys()))
    
    for tab, (grupo_nombre, columnas) in zip(tabs, grupos.items()):
        with tab:
            st.subheader(f"📋 {grupo_nombre}")
            
            # Filtrar columnas que existan en el dataframe
            columnas_validas = [col for col in columnas if col in df.columns]
            
            if not columnas_validas:
                st.info("No hay datos en esta categoría")
                continue
            
            # Crear un gráfico por columna
            for i, columna in enumerate(columnas_validas):
                # Crear dos columnas para gráficos lado a lado
                if i % 2 == 0:
                    col1, col2 = st.columns(2)
                
                with (col1 if i % 2 == 0 else col2):
                    fig = crear_grafico_pregunta(df, columna)
                    if fig:
                        # Key único para cada gráfico
                        st.plotly_chart(fig, use_container_width=True, key=f"{grupo_nombre}_{i}_{columna}")
    
    # Pestaña extra: Datos Crudos
    with st.sidebar:
        if st.button("📥 Descargar Análisis"):
            # Generar resumen en CSV
            resumen = pd.DataFrame({
                'Pregunta': df.columns,
                'Tipo de Dato': [
                    'Numérico' if pd.api.types.is_numeric_dtype(df[col]) else 'Texto'
                    for col in df.columns
                ],
                'Valores Válidos': [len(df[col].dropna()) for col in df.columns],
                'Valores Únicos': [df[col].nunique() for col in df.columns]
            })
            
            csv = resumen.to_csv(index=False)
            st.download_button(
                label="Descargar resumen",
                data=csv,
                file_name="resumen_analisis.csv",
                mime="text/csv"
            )


if __name__ == "__main__":
    main()

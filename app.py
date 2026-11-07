        + _img_tag("logo_clinica.png", "Clínica de Nutrición UNICACH")
        + '</div>',
        unsafe_allow_html=True,
    )
    st.caption("Panel interactivo para explorar respuestas, consultar indicadores y comparar resultados por área.")

    # Sidebar
    with st.sidebar:
        st.markdown("## Cargar Encuesta")
        st.caption("Selecciona un archivo CSV para habilitar los indicadores y gráficas.")

        archivo = st.file_uploader("Sube tu archivo CSV aquí", type=["csv"])

        if archivo:
            st.success(f"{archivo.name}")
        else:
            st.info("Selecciona un archivo CSV para comenzar")

    # Cargar datos
    if archivo is None:
        st.info("Para comenzar, carga tu encuesta en el panel lateral. Después podrás explorar los resultados por área y crear gráficas personalizadas.")
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

    tabs = st.tabs(["Demografía", "Estado Nutricional", "Salud y Educación",
                    "Alimentación", "Actividad Física", "Salud Emocional",
                    "Cultivos y Animales", "Constructor de gráficas"])

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
        c1, c2 = st.columns([3, 2])
        with c1:
            mostrar_slot(df, "desparasitacion")
        with c2:
            mostrar_slot(df, "educacion")

    with tabs[3]:
        c1, c2 = st.columns([1, 2])
        with c1:
            mostrar_slot(df, "lugar_compra")
        with c2:
            mostrar_slot(df, "frecuencia_alimentos")
        st.caption("Cada barra cuenta las personas que marcaron ese alimento. "
                   "Los rangos 3/7, 2/7 y 1/7 son los de la tabla de captura.")

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
        st.caption("Las barras muestran cuántas veces se reportó cada estado emocional, "
                   "desglosado por sexo. Si una persona indicó varias emociones, cada una se cuenta.")

    with tabs[6]:
        c1, c2 = st.columns(2)
        with c1:
            mostrar_slot(df, "cultivos")
        with c2:
            mostrar_slot(df, "animales")

    with tabs[7]:
        pestana_constructor(df)

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
            label="Descargar resumen",
            data=resumen.to_csv(index=False),
            file_name="resumen_analisis.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()

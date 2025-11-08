import os

import streamlit as st
import geopandas as gp
from sqlalchemy import create_engine

from streamlit_folium import folium_static
import folium
from folium.plugins import MousePosition

DB_NAME = os.getenv('POSTGRES_DB','nyc')
DB_USER = os.getenv('POSTGRES_USER', 'postgres')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD','postgres')
DB_HOST = os.getenv('DB_HOST', 'localhost') # ¡Importante! Cambia de 'localhost' a 'db' en Docker Compose
DB_PORT = os.getenv('DB_PORT', '5432')
TABLA_POSTGIS = 'andalucia_usos_suelo'
ZONAS_VERDES = ['forest', 'nature_reserve']

DATA_FILE = "./data/gis_osm_landuse_a_free_1.shp"

def cargar_y_preparar_datos():
    """Lee el SHP, selecciona columnas, reproyecta a 25830 y calcula el área."""
    try:
        ff = gp.read_file(DATA_FILE)

        df_andalucia = (
            # 1. Seleccionar columnas
            ff[['fclass', 'name', 'geometry']]
            # 2. Reproyectar al SRID 25830 (CORRECTO: .to_crs)
            .to_crs(25830)
        )

        # 1. Calcular el área en metros cuadrados y convertir a hectáreas (ha)
        df_andalucia['superficie_ha'] = (df_andalucia.geometry.area / 10000).round(1)

        # 2. Re-seleccionar las columnas finales, incluyendo la nueva 'superficie_ha'
        columnas_finales = ['fclass', 'name', 'superficie_ha', 'geometry']
        df_andalucia = df_andalucia[columnas_finales]

        st.success(f"Datos preparados. CRS: {df_andalucia.crs}. Registros: {len(df_andalucia)}")
        return df_andalucia

    except Exception as e:
        st.error(f"Error al cargar/preparar los datos: {e}")
        return None

def conectar_y_cargar_postgis(gdf):
    """Establece la conexión a PostGIS y carga el GeoDataFrame, reemplazando la tabla."""
    try:
        engine = create_engine(
            f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        )

        # Cargar a PostGIS con 'replace' para eliminar la tabla anterior
        gdf.to_postgis(
            name=TABLA_POSTGIS,
            con=engine,
            if_exists='replace',
            schema='public'
        )
        st.success(f"Tabla '{TABLA_POSTGIS}' creada/reemplazada en PostGIS.")
        st.balloons()
        return True

    except Exception as e:
        st.error(f"Error al conectar o cargar a PostGIS: Revise su configuración de PostgreSQL/PostGIS. Error: {e}")
        return False

def obtener_datos_filtrados(fclass_filtro=None):
    """
    Se conecta a PostGIS y recupera los datos filtrados según la selección.
    """
    try:
        engine = create_engine(
            f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        )

        # Consulta SQL
        if fclass_filtro and fclass_filtro != 'Todos':
            # Filtrar por una clase específica
            sql_query = f"SELECT fclass, name, superficie_ha, ST_Transform(geometry, 4326) AS geometry FROM {TABLA_POSTGIS} WHERE fclass = '{fclass_filtro}'"
        else:
            # Obtener todos los datos
            sql_query = f"SELECT fclass, name, superficie_ha, ST_Transform(geometry, 4326) AS geometry FROM {TABLA_POSTGIS}"

        # Leer desde PostGIS como GeoDataFrame. Importante reproyectar a 4326 (WGS 84) para Folium
        # La reproyección la hacemos en SQL (ST_Transform) para que GeoPandas lo lea como 4326
        gdf_filtrado = gp.read_postgis(sql_query, con=engine, geom_col='geometry', crs=4326)

        return gdf_filtrado

    except Exception as e:
        st.error(f"Error al recuperar datos de PostGIS. Asegúrese de que la tabla fue cargada. Error: {e}")
        return gp.GeoDataFrame()

def visualizar_mapa(gdf):
    """Crea un mapa interactivo con Folium, centrado en Andalucía y con colores específicos."""
    if gdf.empty:
        st.warning("No hay datos para mostrar en el mapa.")
        return

    # Usamos el centro y zoom definidos en las constantes.
    centroid = gdf.union_all().centroid
    m = folium.Map(location=[centroid.y, centroid.x], zoom_start=6)

    # 2. Mapeo de colores específico
    color_map = {
        'forest': 'darkgreen',  # Verde oscuro para 'forest'
        'nature_reserve': 'darkblue'  # Azul oscuro para 'nature_reserve'
    }

    # 3. Añadir la capa GeoJson con tooltips y estilo condicional
    folium.GeoJson(
        gdf.to_json(),
        # Función para determinar el estilo (color) de cada geometría
        style_function=lambda x: {
            # Asignamos el color del 'color_map', si la clase no está mapeada, usamos gris.
            'fillColor': color_map.get(x['properties']['fclass'], '#AAAAAA'),
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.7
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['name', 'fclass', 'superficie_ha'],
            aliases=['Nombre:', 'Clase:', 'Superficie (ha):'],
            localize=True
        )
    ).add_to(m)

    # Funcionalidad opcional: Posición del ratón (coordenadas)
    MousePosition().add_to(m)

    # Mostrar el mapa en Streamlit
    folium_static(m, width=1000, height=600)

def main():
    st.title("🗺️ Visualización de Usos de Suelo de Andalucía (PostGIS)")
    st.write("Aplicación para cargar, consultar y visualizar datos geográficos usando Streamlit, PostGIS y GeoPandas.")

    # 1. SIDEBAR: Controles y Filtros
    with st.sidebar:
        st.header("Controles")

        # Botón "Cargar datos"
        if st.button("Cargar datos", key="cargar_datos_btn"):
            gdf_andalucia = cargar_y_preparar_datos()
            if gdf_andalucia is not None:
                conectar_y_cargar_postgis(gdf_andalucia)

        st.markdown("---")

        # Selector de Filtro (fclass)
        st.header("Filtro de Visualización")
        filtro_opciones = ['Todos'] + ZONAS_VERDES
        filtro_seleccionado = st.selectbox(
            "Seleccione el tipo de uso de suelo:",
            filtro_opciones
        )

        # Botón "Visualizar datos"
        if st.button("Visualizar datos", key="visualizar_datos_btn"):
            # Llama a la función de recuperación
            st.session_state.data_to_display = obtener_datos_filtrados(filtro_seleccionado)

        st.markdown("---")

    # 2. MAIN CONTENT: Visualización

    if 'data_to_display' not in st.session_state:
        st.session_state.data_to_display = gp.GeoDataFrame()  # Inicializar vacío

    gdf_mostrar = st.session_state.data_to_display

    if not gdf_mostrar.empty:
        # A. Mostrar Superficie Total
        superficie_total = gdf_mostrar['superficie_ha'].sum().round(1)
        st.metric(label=f"Superficie Total Mostrada ({filtro_seleccionado})", value=f"{superficie_total:,.1f} ha")

        # B. Mostrar Mapa
        st.subheader(f"Mapa de Usos de Suelo: {filtro_seleccionado}")
        visualizar_mapa(gdf_mostrar)

if __name__ == '__main__':
    main()


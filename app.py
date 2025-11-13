"""
Aplicación de visualización de usos de suelo de Andalucía con PostGIS.

Este módulo proporciona una interfaz web interactiva para cargar, consultar y
visualizar datos geográficos usando Streamlit, PostGIS y GeoPandas.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

import streamlit as st
import geopandas as gpd
import folium
from sqlalchemy import create_engine, Engine
from sqlalchemy.exc import SQLAlchemyError
from streamlit_folium import folium_static
from folium.plugins import MousePosition
import requests
from io import BytesIO

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================================

# Configuración de base de datos
DB_CONFIG = {
    'name': os.getenv('POSTGRES_DB', 'nyc'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'Pececitos1$'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

# Constantes de la aplicación
POSTGIS_TABLE = 'andalucia_usos_suelo'
DATA_FILE = "./data/gis_osm_landuse_a_free_1.shp"
GREEN_ZONES = ['Bosques', 'Reservas naturales']
PROJECT_SRID = 25830  # ETRS89 / UTM zone 30N
SRID_MAP = 4326  # WGS 84
HECTARES_PER_SQM = 10000

# Configuración de visualización
COLOR_MAP = {
    'Bosques': 'darkgreen',
    'Reservas naturales': 'darkblue'
}
DEFAULT_COLOR = '#AAAAAA'
MAP_CONFIG = {
    'zoom_start': 6,
    'width': 1000,
    'height': 600
}


# ============================================================================
# GESTIÓN DE CONEXIONES
# ============================================================================

@contextmanager
def get_db_connection() -> Engine:
    engine = None
    try:
        connection_string = (
            f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
            f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['name']}"
        )
        engine = create_engine(connection_string)
        yield engine
    finally:
        if engine:
            engine.dispose()


# ============================================================================
# FUNCIONES DE PROCESAMIENTO DE DATOS
# ============================================================================

@st.cache_data(show_spinner=False)
def loadData() -> Optional[gpd.GeoDataFrame]:
    try:
        with st.spinner('Cargando y preparando datos...'):
            # Leer archivo shapefile
            # gdf = gpd.read_file(DATA_FILE)
            response = requests.get('https://www.uhu.es/jluis.dominguez/AGI/andalucia-landuse.shp.zip', verify=False)

            response.raise_for_status()
            zip_file = BytesIO(response.content)

            gdf = gpd.read_file(zip_file)

            if gdf.empty:
                st.warning("El archivo de datos está vacío.")
                return None

            processed_gdf = (
                gdf[['fclass', 'name', 'geometry']]
                .to_crs(PROJECT_SRID)
            )

            # Calcular superficie en hectáreas
            processed_gdf['superficie_ha'] = (
                    processed_gdf.geometry.area / HECTARES_PER_SQM
            ).round(1)

            final_columns = ['fclass', 'name', 'superficie_ha', 'geometry']
            processed_gdf = processed_gdf[final_columns]

            logger.info(f"Datos preparados. CRS: {processed_gdf.crs}, "
                        f"Registros: {len(processed_gdf)}")
            st.success(f"✅ Datos preparados: {len(processed_gdf)} registros")

            return processed_gdf

    except FileNotFoundError:
        st.error(f"❌ No se encontró el archivo: {DATA_FILE}")
        logger.error(f"Archivo no encontrado: {DATA_FILE}")
    except Exception as e:
        st.error(f"❌ Error al procesar datos: {str(e)}")
        logger.exception("Error en carga y preparación de datos")

    return None


def loadToPostgis(gdf: gpd.GeoDataFrame) -> bool:
    try:
        with get_db_connection() as engine:
            gdf.to_postgis(
                name=POSTGIS_TABLE,
                con=engine,
                if_exists='replace',
                schema='public'
            )

        st.success(f"✅ Tabla '{POSTGIS_TABLE}' actualizada en PostGIS")
        st.balloons()
        logger.info(f"Tabla {POSTGIS_TABLE} cargada exitosamente")
        return True

    except SQLAlchemyError as e:
        st.error(f"❌ Error de base de datos: {str(e)}")
        logger.exception("Error de SQLAlchemy al cargar a PostGIS")
    except Exception as e:
        st.error(f"❌ Error inesperado: {str(e)}")
        logger.exception("Error general al cargar a PostGIS")

    return False


@st.cache_data(show_spinner=False)
def getFilteredData(fclass_filter: Optional[str] = None) -> gpd.GeoDataFrame:

    try:
        with get_db_connection() as engine:
            # Construir consulta SQL con transformación a WGS84
            base_query = (
                f"SELECT fclass, name, superficie_ha, "
                f"ST_Transform(geometry, {SRID_MAP}) AS geometry "
                f"FROM {POSTGIS_TABLE}"
            )

            if fclass_filter and fclass_filter != 'Todos':
                filter = 'forest' if fclass_filter == 'Bosques' else 'nature_reserve'
                # Usar parámetros para evitar SQL injection
                query = f"{base_query} WHERE fclass = %(fclass)s"
                gdf = gpd.read_postgis(
                    query,
                    con=engine,
                    geom_col='geometry',
                    crs=SRID_MAP,
                    params={'fclass': filter}
                )
            else:
                gdf = gpd.read_postgis(
                    base_query,
                    con=engine,
                    geom_col='geometry',
                    crs=SRID_MAP
                )

            logger.info(f"Datos recuperados: {len(gdf)} registros "
                        f"(filtro: {fclass_filter})")
            return gdf

    except SQLAlchemyError as e:
        st.error(f"❌ Error al consultar PostGIS: {str(e)}")
        logger.exception("Error de SQLAlchemy al obtener datos")
    except Exception as e:
        st.error(f"❌ Error inesperado: {str(e)}")
        logger.exception("Error general al obtener datos")

    return gpd.GeoDataFrame()


# ============================================================================
# FUNCIONES DE VISUALIZACIÓN
# ============================================================================

def viewMap(gdf):
    if gdf.empty:
        st.warning("No hay datos para mostrar en el mapa.")
        return

    # Usamos el centro y zoom definidos en las constantes.
    centroid = gdf.unary_union.centroid
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


# ============================================================================
# INTERFAZ DE USUARIO
# ============================================================================

def configureSidebar() -> str:
    with st.sidebar:
        st.header("📊 Panel de Control")

        # Sección de carga de datos
        st.subheader("📥 Carga de Datos")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔄 Cargar", key="cargar_datos_btn",
                         help="Cargar datos desde archivo SHP"):
                gdf_andalucia = loadData()
                if gdf_andalucia is not None:
                    loadToPostgis(gdf_andalucia)
                    # Limpiar caché para forzar recarga
                    st.cache_data.clear()

        with col2:
            if st.button("🗑️ Limpiar caché", key="limpiar_cache_btn",
                         help="Limpiar datos en caché"):
                st.cache_data.clear()
                st.success("✅ Caché limpiado")

        st.markdown("---")

        # Sección de filtros
        st.subheader("🔍 Filtros de Visualización")

        optionFilters = ['Todos'] + GREEN_ZONES
        selectedFilters = st.selectbox(
            "Tipo de uso de suelo:",
            optionFilters,
            help="Seleccione el tipo de terreno a visualizar"
        )

        if st.button("🗺️ Visualizar", key="visualizar_datos_btn",
                     type="primary", use_container_width=True):
            st.session_state.data_to_display = getFilteredData(
                selectedFilters if selectedFilters != 'Todos' else None
            )
            st.session_state.current_filter = selectedFilters

        st.markdown("---")

        # Información adicional
        st.subheader("ℹ️ Información")
        st.info(
            f"**Base de datos:** {DB_CONFIG['name']}\n\n"
            f"**Tabla:** {POSTGIS_TABLE}\n\n"
            f"**Host:** {DB_CONFIG['host']}:{DB_CONFIG['port']}"
        )

        return selectedFilters

def showMainContent() -> None:
    # Inicializar estado si es necesario
    if 'data_to_display' not in st.session_state:
        st.session_state.data_to_display = gpd.GeoDataFrame()

    if 'current_filter' not in st.session_state:
        st.session_state.current_filter = 'Todos'

    gdf_show = st.session_state.data_to_display
    print(gdf_show);

    if not gdf_show.empty:
        # Mostrar métricas
        col1, col2, col3 = st.columns(3)

        with col1:
            total_shallow = gdf_show['superficie_ha'].sum()
            st.metric(
                label="📐 Superficie Total",
                value=f"{total_shallow:,.1f} ha"
            )

        with col2:
            parcel_number = len(gdf_show)
            st.metric(
                label="📍 Número de Parcelas",
                value=f"{parcel_number:,}"
            )

        with col3:
            average_shallow = gdf_show['superficie_ha'].mean()
            st.metric(
                label="📊 Superficie Media",
                value=f"{average_shallow:.1f} ha"
            )

        # Mostrar mapa
        st.subheader(f"🗺️ Mapa de Usos de Suelo: {st.session_state.current_filter}")
        viewMap(gdf_show)

    else:
        # Mostrar mensaje de bienvenida
        st.info(
            "👋 **Bienvenido a la aplicación de visualización de usos de suelo**\n\n"
            "Para comenzar:\n"
            "1. Haz clic en **🔄 Cargar** en la barra lateral para cargar los datos\n"
            "2. Selecciona un filtro si lo deseas\n"
            "3. Haz clic en **🗺️ Visualizar** para ver el mapa"
        )

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main() -> None:
    """Función principal de la aplicación."""
    # Configuración de página
    st.set_page_config(
        page_title="Usos de Suelo - Andalucía",
        page_icon="🗺️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Título principal
    st.title("🗺️ Visualización de Usos de Suelo de Andalucía")
    st.markdown(
        "Sistema interactivo para análisis geoespacial con "
        "**Streamlit**, **PostGIS** y **GeoPandas**"
    )

    # Configurar sidebar
    configureSidebar()

    # Mostrar contenido principal
    showMainContent()

if __name__ == '__main__':
    main()


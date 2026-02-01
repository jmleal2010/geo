"""
Aplicación de visualización de usos de suelo de Andalucía con PostGIS.

Este módulo proporciona una interfaz web interactiva para cargar, consultar y
visualizar datos geográficos usando Streamlit, PostGIS y GeoPandas.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import hashlib

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

def loadData() -> Optional[gpd.GeoDataFrame]:
    """
    Carga y prepara datos geográficos desde archivo shapefile.
    Solo guarda: fclass, name, geometry (SIN superficie_ha).
    """
    try:
        with st.spinner('Cargando y preparando datos...'):
            # Leer archivo shapefile desde URL
            response = requests.get(
                'https://www.uhu.es/jluis.dominguez/AGI/andalucia-landuse.shp.zip',
                verify=False
            )
            response.raise_for_status()
            zip_file = BytesIO(response.content)
            gdf = gpd.read_file(zip_file)

            if gdf.empty:
                st.warning("El archivo de datos está vacío.")
                return None

            # Solo seleccionar las columnas necesarias y reproyectar
            processed_gdf = (
                gdf[['fclass', 'name', 'geometry']]
                .to_crs(PROJECT_SRID)
            )

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
    """
    Carga datos a PostGIS.
    Solo persiste: fclass, name, geometry.
    """
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


def getFilteredData(fclass_filter: Optional[str] = None, limit: Optional[int] = None) -> gpd.GeoDataFrame:
    """
    Recupera datos de PostGIS calculando superficie_ha dinámicamente.

    Calcula el área usando ST_Area() de PostGIS sobre la geometría original
    en ETRS89 (25830) y transforma a WGS84 para visualización.

    Args:
        fclass_filter: Filtro por clase ('Bosques', 'Reservas naturales', o None para todos)
        limit: Límite opcional de registros (útil para 'Todos')
    """
    try:
        with get_db_connection() as engine:
            # Construir consulta SQL con cálculo dinámico de superficie
            base_query = (
                f"SELECT "
                f"  fclass, "
                f"  name, "
                f"  ROUND(CAST(ST_Area(geometry) / {HECTARES_PER_SQM} AS numeric), 1) AS superficie_ha, "
                f"  ST_Transform(geometry, {SRID_MAP}) AS geometry "
                f"FROM {POSTGIS_TABLE}"
            )

            if fclass_filter and fclass_filter != 'Todos':
                filter_value = 'forest' if fclass_filter == 'Bosques' else 'nature_reserve'
                query = f"{base_query} WHERE fclass = %(fclass)s"
                if limit:
                    query += f" LIMIT {limit}"
                gdf = gpd.read_postgis(
                    query,
                    con=engine,
                    geom_col='geometry',
                    crs=SRID_MAP,
                    params={'fclass': filter_value}
                )
            else:
                # Para "Todos", aplicar límite si se especifica
                query = base_query
                if limit:
                    query += f" LIMIT {limit}"

                gdf = gpd.read_postgis(
                    query,
                    con=engine,
                    geom_col='geometry',
                    crs=SRID_MAP
                )

            logger.info(f"Datos recuperados: {len(gdf)} registros "
                        f"(filtro: {fclass_filter}, límite: {limit})")
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

def getDataHash(gdf: gpd.GeoDataFrame) -> str:
    """Genera un hash único para el GeoDataFrame."""
    if gdf.empty:
        return "empty"
    # Usar número de registros y bounds como identificador rápido
    bounds = gdf.total_bounds
    return hashlib.md5(f"{len(gdf)}{bounds}".encode()).hexdigest()


def viewMap(gdf):
    """
    Visualiza datos geográficos en un mapa interactivo usando Folium.
    Solo re-crea el mapa cuando los datos cambian.
    """
    if gdf.empty:
        st.warning("No hay datos para mostrar en el mapa.")
        return

    # Calcular hash de los datos actuales
    current_hash = getDataHash(gdf)

    # Solo recrear el mapa si los datos cambiaron
    if 'map_data_hash' not in st.session_state or st.session_state.map_data_hash != current_hash:
        # Calcular centroide para centrar el mapa
        centroid = gdf.unary_union.centroid
        m = folium.Map(location=[centroid.y, centroid.x], zoom_start=6)

        # Mapeo de colores por tipo de uso
        color_map = {
            'forest': 'darkgreen',
            'nature_reserve': 'darkblue'
        }

        # Añadir capa GeoJson con tooltips y estilo condicional
        folium.GeoJson(
            gdf.to_json(),
            style_function=lambda x: {
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

        # Añadir posición del ratón
        MousePosition().add_to(m)

        # Guardar el mapa en session_state
        st.session_state.cached_map = m
        st.session_state.map_data_hash = current_hash
        logger.info(f"Mapa recreado con hash: {current_hash}")
    else:
        logger.info(f"Usando mapa cacheado con hash: {current_hash}")

    # Mostrar el mapa (cacheado o recién creado)
    folium_static(st.session_state.cached_map, width=1000, height=600)


# ============================================================================
# INTERFAZ DE USUARIO
# ============================================================================

def configureSidebar() -> None:
    """Configura la barra lateral con controles y filtros."""
    with st.sidebar:
        st.header("📊 Panel de Control")

        # Sección de carga de datos
        st.subheader("📥 Carga de Datos")

        if st.button("🔄 Cargar", key="cargar_datos_btn",
                     help="Cargar datos desde archivo SHP",
                     use_container_width=True):
            gdf_andalucia = loadData()
            if gdf_andalucia is not None:
                loadToPostgis(gdf_andalucia)

        st.markdown("---")

        # Sección de filtros
        st.subheader("🔍 Filtros de Visualización")

        # Inicializar el filtro en session_state si no existe
        if 'selected_filter' not in st.session_state:
            st.session_state.selected_filter = 'Todos'

        optionFilters = ['Todos'] + GREEN_ZONES

        # El selectbox guarda en session_state pero NO dispara acciones
        st.selectbox(
            "Tipo de uso de suelo:",
            optionFilters,
            key="selected_filter",  # Guarda directamente en session_state
            help="Seleccione el tipo de terreno a visualizar"
        )

        # Solo al hacer clic en este botón se dispara la visualización
        if st.button("🗺️ Visualizar",
                     key="visualizar_datos_btn",
                     type="primary",
                     use_container_width=True,
                     help="Haz clic para aplicar el filtro y mostrar el mapa"):

            with st.spinner('Cargando datos desde PostGIS...'):
                # Obtener datos según el filtro seleccionado
                filter_value = st.session_state.selected_filter if st.session_state.selected_filter != 'Todos' else None

                # Limitar a 5000 registros cuando es "Todos" para evitar carga pesada
                limit = 5000 if st.session_state.selected_filter == 'Todos' else None

                st.session_state.data_to_display = getFilteredData(filter_value, limit)
                st.session_state.current_filter = st.session_state.selected_filter
                st.session_state.has_visualized = True

                # Mostrar feedback
                if not st.session_state.data_to_display.empty:
                    st.success(f"✅ Visualizando: {st.session_state.selected_filter}")
                    if limit and st.session_state.selected_filter == 'Todos':
                        st.info(f"📊 Mostrando {len(st.session_state.data_to_display):,} parcelas de ejemplo")
                else:
                    st.warning("⚠️ No se encontraron datos para el filtro seleccionado")

        st.markdown("---")

        # Información adicional
        st.subheader("ℹ️ Información")
        st.info(
            f"**Base de datos:** {DB_CONFIG['name']}\n\n"
            f"**Tabla:** {POSTGIS_TABLE}\n\n"
            f"**Host:** {DB_CONFIG['host']}:{DB_CONFIG['port']}\n\n"
            f"**Columnas BD:** fclass, name, geometry\n\n"
            f"**Cálculo dinámico:** superficie_ha"
        )


def showMainContent() -> None:
    """Muestra el contenido principal de la aplicación."""
    # Inicializar estado si es necesario
    if 'data_to_display' not in st.session_state:
        st.session_state.data_to_display = gpd.GeoDataFrame()

    if 'current_filter' not in st.session_state:
        st.session_state.current_filter = 'Ninguno'

    if 'has_visualized' not in st.session_state:
        st.session_state.has_visualized = False

    gdf_show = st.session_state.data_to_display

    if not gdf_show.empty and st.session_state.has_visualized:
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
            "2. Selecciona un filtro en el desplegable\n"
            "3. Haz clic en **🗺️ Visualizar** para ver el mapa con el filtro aplicado"
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
# Visualización de Usos de Suelo de Andalucía

Este proyecto es una aplicación web interactiva para cargar, consultar y visualizar datos geoespaciales sobre los usos del suelo en Andalucía. La aplicación está construida con Streamlit y utiliza PostGIS como base de datos espacial para un manejo eficiente de los datos.

![Screenshot de la aplicación](https://i.imgur.com/example.png) <!-- Reemplazar con una captura de pantalla real de la aplicación -->

## Características

- **Interfaz Interactiva**: Interfaz web amigable construida con Streamlit.
- **Carga de Datos Automatizada**: Carga datos de usos del suelo desde un archivo shapefile remoto directamente a una base de datos PostGIS.
- **Visualización en Mapa**: Muestra los polígonos de usos del suelo en un mapa interactivo (Folium) con información detallada en tooltips.
- **Filtrado Dinámico**: Permite filtrar los datos por tipo de uso de suelo (Bosques, Reservas Naturales, etc.).
- **Métricas Clave**: Calcula y muestra estadísticas relevantes como la superficie total, número de parcelas y superficie media.
- **Contenerizado y Reproducible**: Utiliza Docker y Docker Compose para un despliegue fácil y consistente en cualquier entorno.

## Stack Tecnológico

- **Frontend**: Streamlit
- **Backend**: Python
- **Base de Datos**: PostgreSQL con la extensión PostGIS
- **Librerías Geoespaciales**: GeoPandas, Folium, Shapely, Fiona, Pyproj
- **ORM y Conectores**: SQLAlchemy, GeoAlchemy2, Psycopg2
- **Orquestación**: Docker, Docker Compose

## Prerrequisitos

Antes de comenzar, asegúrate de tener instalado en tu sistema:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Instalación y Puesta en Marcha

Sigue estos pasos para poner en funcionamiento la aplicación:

**1. Clona el Repositorio**

```bash
git clone <URL-del-repositorio>
cd <nombre-del-directorio>
```

**2. Configura las Variables de Entorno**

Crea un archivo llamado `.env` en la raíz del proyecto. Este archivo contendrá las credenciales y la configuración de la base de datos. Copia y pega el siguiente contenido, ajustando los valores si es necesario:

```env
# Configuración de la Base de Datos
POSTGRES_DB=andalucia_gis
POSTGRES_USER=user
POSTGRES_PASSWORD=password

# Puerto para la Base de Datos en el host
DB_PORT=5433

# Puerto para la aplicación Streamlit en el host
STREAMLIT_PORT=8501
```

**3. Construye y Levanta los Contenedores**

Desde la raíz del proyecto, ejecuta el siguiente comando. Esto construirá la imagen de la aplicación y levantará los servicios de la base de datos y la aplicación.

```bash
docker-compose up --build
```

La primera vez que ejecutes este comando, Docker descargará la imagen de PostGIS y construirá la imagen de la aplicación, lo que puede tardar unos minutos.

**4. Accede a la Aplicación**

Una vez que los contenedores estén en funcionamiento, abre tu navegador web y ve a la siguiente dirección:

[**http://localhost:8501**](http://localhost:8501)

##  usage Uso de la Aplicación

1.  **Cargar Datos**: En la barra lateral izquierda, haz clic en el botón **`🔄 Cargar`**. Esto descargará los datos del shapefile, los procesará y los cargará en la base de datos PostGIS. Verás notificaciones de éxito una vez completado.

2.  **Seleccionar Filtro**: En la misma barra lateral, utiliza el menú desplegable para seleccionar el tipo de uso de suelo que deseas visualizar (e.g., `Bosques`, `Reservas naturales` o `Todos`).

3.  **Visualizar en el Mapa**: Haz clic en el botón **`🗺️ Visualizar`**. La aplicación consultará la base de datos con el filtro aplicado y mostrará los resultados en el mapa interactivo en el panel principal.

4.  **Explorar**:
    - Pasa el ratón sobre los polígonos en el mapa para ver detalles como el nombre, la clase y la superficie en hectáreas.
    - Observa las métricas agregadas (Superficie Total, Número de Parcelas, etc.) en la parte superior del panel principal.

## Estructura del Proyecto

```
.
├── app.py                # Script principal de la aplicación Streamlit
├── docker-compose.yml    # Archivo de orquestación de Docker
├── Dockerfile              # Define la imagen Docker para la aplicación
├── requirements.txt        # Dependencias de Python
├── .env                  # (Opcional, recomendado) Variables de entorno
└── README.md               # Este archivo
```

##  Detener la Aplicación

Para detener los contenedores, presiona `Ctrl + C` en la terminal donde ejecutaste `docker-compose up`. Para eliminarlos y liberar los recursos (incluido el volumen de datos), puedes usar:

```bash
docker-compose down -v
```

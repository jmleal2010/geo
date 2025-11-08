# 🗺️ Proyecto: Usos de Suelo de Andalucía (Streamlit + PostGIS)

Aplicación web interactiva construida con **Python (Streamlit)**, **GeoPandas** y **PostGIS** para visualizar información de zonas verdes de Andalucía.

La aplicación permite cargar datos de un Shapefile remoto, persistirlos en una base de datos PostGIS y visualizarlos en un mapa interactivo con filtros de clase (`forest` o `nature_reserve`), cálculo de superficie total y tooltips (información al pasar el ratón).

---

## 🐳 Requisitos

Para ejecutar el proyecto, solo necesitas tener instalado:

1.  **Docker**
2.  **Docker Compose** (Generalmente viene incluido con Docker Desktop).

---

## 🚀 Uso de la Aplicación

Sigue estos pasos en la terminal desde el directorio raíz del proyecto (donde se encuentran `app.py`, `Dockerfile`, `docker-compose.yml` y `requirements.txt`).

### 1. Iniciar los Contenedores

Ejecuta el siguiente comando para construir las imágenes e iniciar los contenedores de la aplicación Streamlit y PostGIS:

```bash
docker compose up --build -d
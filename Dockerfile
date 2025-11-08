# Usa una imagen base de Python optimizada para desarrollo
FROM python:3.11-slim

# Instalar dependencias del sistema necesarias para GeoPandas y psycopg2 (geos, gdal, etc.)
# Esto asegura que geopandas y los adaptadores de DB se instalen correctamente.
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libgdal-dev \
    gdal-bin \
    libspatialindex-dev \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo de requerimientos e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar la aplicación
COPY app.py .

# Exponer el puerto de Streamlit (por defecto es 8501)
EXPOSE 8501

# Comando para correr la aplicación Streamlit
CMD ["streamlit", "run", "app.py"]
# 🗺️ Visualización de Usos de Suelo de Andalucía

Aplicación web interactiva para cargar, consultar y visualizar datos geográficos de usos de suelo usando **Streamlit**, **PostGIS** y **GeoPandas**.

## 📋 Características

- ✅ Carga de datos desde archivos Shapefile (.shp)
- ✅ Almacenamiento en base de datos PostGIS
- ✅ Visualización interactiva con Folium
- ✅ Filtrado por tipo de uso de suelo
- ✅ Cálculo automático de superficies en hectáreas
- ✅ Exportación de datos a CSV
- ✅ Caché inteligente para optimización de rendimiento

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.8+
- PostgreSQL con extensión PostGIS
- Docker y Docker Compose (opcional)

### Instalación

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd <project-directory>
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**

Crear archivo `.env` en la raíz del proyecto:
```env
POSTGRES_DB=nyc
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

### 🐳 Usando Docker

Si prefieres usar Docker:

```bash
docker-compose up -d
```

## 📂 Estructura del Proyecto

```
.
├── data/                    # Datos geoespaciales (no versionados)
│   └── gis_osm_landuse_a_free_1.shp
├── app.py                   # Aplicación principal
├── requirements.txt         # Dependencias Python
├── docker-compose.yml       # Configuración Docker
├── Dockerfile              # Imagen Docker
├── .gitignore             # Archivos ignorados por Git
└── README.md              # Este archivo
```

## 🎮 Uso

1. **Iniciar la aplicación**
```bash
streamlit run app.py
```

2. **Cargar datos**
   - Click en el botón "🔄 Cargar" en la barra lateral
   - Los datos se cargarán desde el archivo Shapefile y se almacenarán en PostGIS

3. **Visualizar datos**
   - Seleccionar filtro de tipo de uso de suelo (opcional)
   - Click en "🗺️ Visualizar"
   - El mapa interactivo se mostrará con las parcelas coloreadas por tipo

4. **Exportar datos**
   - Expandir la sección "📋 Ver tabla de datos"
   - Click en "📥 Descargar CSV"

## 🎨 Tipos de Uso de Suelo

Los siguientes tipos de uso están disponibles para filtrado:
- **forest** (Verde oscuro): Áreas forestales
- **nature_reserve** (Azul oscuro): Reservas naturales
- **Todos**: Muestra todos los tipos de uso

## ⚙️ Configuración Avanzada

### Base de Datos

La aplicación requiere PostgreSQL con PostGIS. Para instalar PostGIS:

```sql
CREATE EXTENSION postgis;
```

### Proyecciones

- **SRID del proyecto**: 25830 (ETRS89 / UTM zone 30N)
- **SRID del mapa**: 4326 (WGS 84)

## 🔧 Desarrollo

### Ejecutar tests
```bash
pytest tests/
```

### Formatear código
```bash
black app.py
```

### Verificar calidad del código
```bash
flake8 app.py
mypy app.py
```

## 📊 Optimizaciones Implementadas

- ✅ **Type hints** para mejor documentación y detección de errores
- ✅ **Context managers** para gestión segura de conexiones a BD
- ✅ **Caché de Streamlit** para evitar recargas innecesarias
- ✅ **Logging estructurado** para debugging
- ✅ **Manejo robusto de errores** con excepciones específicas
- ✅ **SQL parametrizado** para prevenir inyección SQL
- ✅ **Código modular** con separación de responsabilidades
- ✅ **Docstrings completos** siguiendo convenciones de Python

## 🐛 Solución de Problemas

### Error de conexión a PostgreSQL
- Verificar que PostgreSQL esté ejecutándose
- Confirmar credenciales en el archivo `.env`
- Asegurar que PostGIS esté instalado

### Archivo Shapefile no encontrado
- Verificar que el archivo existe en `data/gis_osm_landuse_a_free_1.shp`
- Confirmar que todos los archivos asociados (.shx, .dbf, .prj) estén presentes

### Mapa no se visualiza
- Verificar que los datos se hayan cargado correctamente
- Limpiar caché con el botón "🗑️ Limpiar caché"
- Revisar logs en la consola para errores específicos

## 📝 Licencia

Este proyecto está bajo licencia MIT. Ver archivo `LICENSE` para más detalles.

## 👥 Contribuir

Las contribuciones son bienvenidas. Por favor:
1. Fork el repositorio
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## 📧 Contacto

Para preguntas o sugerencias, por favor abrir un issue en GitHub.

---
Desarrollado con ❤️ usando Streamlit, PostGIS y GeoPandas
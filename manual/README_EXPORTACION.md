# Sistema de Exportación Avanzada de Resultados

## Descripción

Se ha implementado un sistema completo de exportación de resultados que soporta múltiples formatos y características avanzadas.

## Características Implementadas

### ✅ Múltiples Formatos de Exportación
- **TXT**: Formato tabulado tradicional (compatibilidad con código existente)
- **CSV**: Separado por comas, compatible con Excel
- **JSON**: Con metadatos y estructura jerárquica
- **XML**: Estructurado con metadatos
- **Excel**: Hojas de cálculo con metadatos (requiere pandas y openpyxl)

### ✅ Plantillas Personalizables
- Sistema de plantillas para formato TXT
- Sustitución de variables dinámicas
- Creación automática de plantillas de ejemplo
- Ubicación: `plantillas/plantilla_ejemplo.txt`

### ✅ Compresión de Resultados
- Compresión automática en formato ZIP
- Eliminación del archivo original tras compresión
- Reducción significativa del tamaño de archivo

### ✅ Mejoras de Usabilidad
- Apertura automática de archivos generados
- Nombres de archivo con timestamp automático
- Validación de formatos soportados
- Manejo robusto de errores

## Uso

### Línea de Comandos

```bash
# Exportación básica (formato TXT por defecto)
python s50info.py -d "SELECT * FROM tabla"

# Exportar a CSV
python s50info.py -d "SELECT * FROM tabla" -f csv

# Exportar a Excel
python s50info.py -d "SELECT * FROM tabla" -f excel

# Exportar a JSON
python s50info.py -d "SELECT * FROM tabla" -f json

# Exportar a XML
python s50info.py -d "SELECT * FROM tabla" -f xml

# Con nombre de archivo personalizado
python s50info.py -d "SELECT * FROM tabla" -f csv -o "mi_consulta"

# Usando plantilla personalizada
python s50info.py -d "SELECT * FROM tabla" -t "plantillas/mi_plantilla.txt"

# Comprimir resultado
python s50info.py -d "SELECT * FROM tabla" -f csv -z

# Combinación de opciones
python s50info.py -d "SELECT * FROM tabla" -f excel -o "reporte_mensual" -z
```

### Programático

```python
from exportador_resultados import ExportadorResultados

# Crear exportador
exportador = ExportadorResultados()

# Exportar datos
datos = [{"id": 1, "nombre": "Test"}, {"id": 2, "nombre": "Ejemplo"}]

ruta = exportador.exportar(
    datos=datos,
    formato="excel",
    nombre_archivo="mi_reporte",
    comprimir=True
)
```

## Nuevos Parámetros CLI

- `-f, --formato`: Formato de exportación (txt, csv, json, xml, excel, xlsx)
- `-o, --output`: Nombre base del archivo de salida
- `-t, --plantilla`: Ruta a plantilla personalizada
- `-z, --comprimir`: Comprimir resultado en ZIP

## Dependencias Opcionales

Para exportación a Excel:
```bash
pip install pandas openpyxl
```

## Estructura de Archivos

```
tool_sage50/
├── exportador_resultados.py     # Módulo principal de exportación
├── exportador_config.py         # Gestión de configuración
├── proceso.py                   # Modificado para usar nuevo exportador
├── s50info.py                   # Modificado con nuevos argumentos CLI
├── plantillas/
│   └── plantilla_ejemplo.txt    # Plantilla de ejemplo
├── resultados/                  # Directorio de salida (creado automáticamente)
└── README_EXPORTACION.md        # Este archivo
```

## Compatibilidad

- ✅ Totalmente compatible con código existente
- ✅ Método legacy `imprimir_diccionarios_legacy()` disponible
- ✅ Mismos parámetros por defecto que versión anterior
- ✅ Sin cambios en el flujo de trabajo existente

## Ejemplos de Salida

### JSON
```json
{
  "metadatos": {
    "fecha_generacion": "2024-01-15T10:30:00",
    "total_registros": 2,
    "campos": ["id", "nombre", "tipo"]
  },
  "datos": [
    {"id": 1, "nombre": "Test", "tipo": "A"},
    {"id": 2, "nombre": "Ejemplo", "tipo": "B"}
  ]
}
```

### XML
```xml
<?xml version='1.0' encoding='utf-8'?>
<resultados>
  <metadatos>
    <fecha_generacion>2024-01-15T10:30:00</fecha_generacion>
    <total_registros>2</total_registros>
  </metadatos>
  <datos>
    <registro id="1">
      <id>1</id>
      <nombre>Test</nombre>
      <tipo>A</tipo>
    </registro>
    <registro id="2">
      <id>2</id>
      <nombre>Ejemplo</nombre>
      <tipo>B</tipo>
    </registro>
  </datos>
</resultados>
```

## Mejoras Futuras

- [ ] Programación de exportaciones automáticas
- [ ] Integración con sistemas de almacenamiento en la nube
- [ ] Sistema de plantillas visuales
- [ ] Exportación incremental
- [ ] Dashboard de monitoreo de exportaciones
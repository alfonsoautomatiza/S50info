# S50Info: Herramienta de Automatización para SAGE50 💻📈

Bienvenido a **S50Info**, la navaja suiza para administradores y desarrolladores que trabajan con **SAGE50**. Aunque es una herramienta de perfil técnico, está diseñada para simplificar y automatizar tareas diarias complejas, convirtiendo consultas SQL en informes útiles de forma instantánea.

## ⚡ Características Principales

### 🗑 Exportación Multiformato
Olvídate de procesos manuales. Genera archivos listos para usar a partir de tus consultas SQL:
*   **Excel (.xlsx)**: Reportes nativos para usuarios finales.
*   **JSON / CSV**: Formatos ideales para integración con otras apps y APIs.
*   **HTML**: Tablas web rápidas para visualización.
*   **TXT**: Compatible con sistemas legacy.

### 💾 Integración Profunda con SAGE50
No es solo un conector de base de datos. **S50Info** carga el contexto de la aplicación, permitiendo:
*   Ejecutar consultas SQL directas contra los datos.
*   Utilizar la lógica de negocio interna de Sage50 mediante scripts.
*   Recuperar claves y configuraciones de forma segura.

### 🖌 Conversión y Personalización
*   **Plantillas TXT**: Define la estructura exacta de tus archivos de texto.
*   **Compresión ZIP**: Genera y comprime grandes volúmenes de datos automáticamente con un flag (`--comprimir`).

### 🛠 Extensibilidad: Scripts Python
La funcionalidad estrella (`--exe`). Ejecuta tus propios scripts de Python con el objeto `proceso` ya inyectado. Esto te permite:
*   Crear scripts de mantenimiento complejos.
*   Realizar actualizaciones masivas de tarifas o clientes.
*   Automatizar flujos de trabajo sin reescribir la lógica de conexión.

## 🚀 ¿Cómo Utilizar **S50Info**?

**S50Info** funciona desde la línea de comandos, lo que lo hace perfecto para tareas programadas (Cron/Task Scheduler).

### 1. Consultas Rápidas
Verifica datos al instante sin abrir SQL Management Studio:
```bash
s50info --sql "SELECT TOP 10 * FROM CLIENTES"
```

### 2. Generación de Informes
Crea un Excel de ventas y comprímelo, todo en una línea:
```bash
s50info --sql2doc "SELECT * FROM ALBARANES" --formato xlsx --output Ventas_Semana --comprimir
```

### 3. Ejecución de Scripts Técnicos
Corre tu script de limpieza de precios:
```bash
s50info --exe "./scripts/actualizar_precios.py"
```

## 👍 Ventajas Competitivas

*   **Automatización Total**: Intégralo en tus scripts `.bat` o `.ps1` nocturnos.
*   **Ligero y Rápido**: Sin interfaces pesadas, directo al grano.
*   **Seguro**: Utiliza la configuración de conexión nativa de Sage50.
*   **Versátil**: Sirve tanto para un reporte rápido al gerente como para una migración de datos compleja.

## ⭐ ¡Empieza Ahora!

Descubre cómo **S50Info** puede transformar tu flujo de trabajo con **SAGE50**, haciéndolo más eficiente, fiable y libre de errores manuales. 🙌

---

📚 **Documentación Completa**
Para profundizar en cada parámetro, consulta nuestro [Manual Técnico](manual/index.md) incluido en este repositorio.

"""
Módulo de exportación avanzada de resultados para SAGE50
Soporta múltiples formatos: Excel, JSON, CSV, XML, TXT
Incluye compresión y plantillas personalizables
"""

# --- Parche compatibilidad numpy / openpyxl ---
import numpy as np

# En numpy 1.26 esto ya existe; en numpy 2.x lo creamos
if not hasattr(np, "short"):
    np.short = np.int16
# Puedes añadir otros si algún día hicieran falta:
# if not hasattr(np, "int"):
#     np.int = int

# ----------------------------------------------
import csv
import json
import logging
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logging.warning("Pandas no disponible - exportación a Excel limitada")

try:
    import openpyxl

    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    logging.warning("Openpyxl no disponible - exportación a Excel no disponible")


class ExportadorResultados:
    """Clase principal para exportación de resultados en múltiples formatos"""

    def __init__(self, directorio_salida: str = "resultados"):
        self.directorio_salida = Path(directorio_salida)
        self.directorio_salida.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def exportar(
        self,
        datos: list[dict[str, Any]],
        formato: str = "txt",
        nombre_archivo: str | None = None,
        plantilla: str | None = None,
        comprimir: bool = False,
        abrir_archivo: bool = True,
    ) -> str:
        """
        Método principal de exportación

        Args:
            datos: Lista de diccionarios con los datos a exportar
            formato: Formato de exportación ('txt', 'csv', 'json', 'xml', 'excel')
            nombre_archivo: Nombre base del archivo (sin extensión)
            plantilla: Ruta a plantilla personalizada
            comprimir: Si se debe comprimir el resultado
            abrir_archivo: Si se debe abrir el archivo después de exportar

        Returns:
            str: Ruta del archivo exportado
        """
        if not datos:
            raise ValueError("No hay datos para exportar")

        # Generar nombre de archivo si no se proporciona
        if not nombre_archivo:
            timestamp = datetime.now().strftime("%d%m%Y%H%M")
            nombre_archivo = f"sqltodic_{timestamp}"

        # Exportar según formato
        exportadores = {
            "txt": self._exportar_txt,
            "csv": self._exportar_csv,
            "json": self._exportar_json,
            "xml": self._exportar_xml,
            "excel": self._exportar_excel,
            "xlsx": self._exportar_excel,
        }

        if formato.lower() not in exportadores:
            raise ValueError(
                f"Formato no soportado: {formato}. Formatos disponibles: {list(exportadores.keys())}"
            )

        # Exportar datos
        ruta_archivo = exportadores[formato.lower()](datos, nombre_archivo, plantilla)

        # Comprimir si se solicita
        if comprimir:
            ruta_archivo = self._comprimir_archivo(ruta_archivo)

        # Abrir archivo si se solicita
        if abrir_archivo:
            self._abrir_archivo(ruta_archivo)

        self.logger.info(f"Datos exportados exitosamente a: {ruta_archivo}")
        return str(ruta_archivo)

    def _exportar_txt(
        self, datos: list[dict[str, Any]], nombre_archivo: str, plantilla: str | None = None
    ) -> Path:
        """Exportar a formato de texto tabulado"""
        ruta_archivo = self.directorio_salida / f"{nombre_archivo}.txt"

        if plantilla and Path(plantilla).exists():
            return self._aplicar_plantilla_txt(datos, ruta_archivo, plantilla)

        # Obtener cabecera y calcular anchos
        cabecera = list(datos[0].keys())
        anchos = {campo: len(str(campo)) for campo in cabecera}

        for diccionario in datos:
            for campo in cabecera:
                anchos[campo] = max(anchos[campo], len(str(diccionario.get(campo, ""))))

        # Formatear contenido
        contenido = []
        cabecera_formateada = "\t".join(f"{campo:{anchos[campo]}}" for campo in cabecera)
        contenido.append(cabecera_formateada)

        for diccionario in datos:
            linea = [str(diccionario.get(campo, "")) for campo in cabecera]
            contenido.append("\t".join(linea))

        # Escribir archivo
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            f.write("\n".join(contenido))

        return ruta_archivo

    def _exportar_csv(
        self, datos: list[dict[str, Any]], nombre_archivo: str, plantilla: str | None = None
    ) -> Path:
        """Exportar a formato CSV"""
        ruta_archivo = self.directorio_salida / f"{nombre_archivo}.csv"

        if not datos:
            return ruta_archivo

        campos = list(datos[0].keys())

        with open(ruta_archivo, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            writer.writerows(datos)

        return ruta_archivo

    def _exportar_json(
        self, datos: list[dict[str, Any]], nombre_archivo: str, plantilla: str | None = None
    ) -> Path:
        """Exportar a formato JSON"""
        ruta_archivo = self.directorio_salida / f"{nombre_archivo}.json"

        # Metadatos
        salida = {
            "metadatos": {
                "fecha_generacion": datetime.now().isoformat(),
                "total_registros": len(datos),
                "campos": list(datos[0].keys()) if datos else [],
            },
            "datos": datos,
        }

        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(salida, f, indent=2, ensure_ascii=False, default=str)

        return ruta_archivo

    def _exportar_xml(
        self, datos: list[dict[str, Any]], nombre_archivo: str, plantilla: str | None = None
    ) -> Path:
        """Exportar a formato XML"""
        ruta_archivo = self.directorio_salida / f"{nombre_archivo}.xml"

        # Crear estructura XML
        root = ET.Element("resultados")

        # Metadatos
        metadatos = ET.SubElement(root, "metadatos")
        ET.SubElement(metadatos, "fecha_generacion").text = datetime.now().isoformat()
        ET.SubElement(metadatos, "total_registros").text = str(len(datos))

        # Datos
        datos_element = ET.SubElement(root, "datos")
        for i, diccionario in enumerate(datos, 1):
            registro = ET.SubElement(datos_element, "registro", id=str(i))
            for clave, valor in diccionario.items():
                elemento = ET.SubElement(registro, clave.replace(" ", "_"))
                elemento.text = str(valor) if valor is not None else ""

        # Formatear y guardar
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)
        tree.write(ruta_archivo, encoding="utf-8", xml_declaration=True)

        return ruta_archivo

    def _exportar_excel(
        self, datos: list[dict[str, Any]], nombre_archivo: str, plantilla: str | None = None
    ) -> Path:
        """Exportar a formato Excel"""
        ruta_archivo = self.directorio_salida / f"{nombre_archivo}.xlsx"

        if not PANDAS_AVAILABLE or not OPENPYXL_AVAILABLE:
            raise ImportError("Se requiere pandas y openpyxl para exportar a Excel")

        # Convertir a DataFrame
        df = pd.DataFrame(datos)

        # Crear writer con opciones
        with pd.ExcelWriter(ruta_archivo, engine="openpyxl") as writer:
            # Hoja principal de datos
            df.to_excel(writer, sheet_name="Datos", index=False)

            # Hoja de metadatos
            metadatos = {
                "Propiedad": ["Fecha de generación", "Total de registros", "Columnas"],
                "Valor": [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    len(df),
                    ", ".join(df.columns.tolist()),
                ],
            }
            pd.DataFrame(metadatos).to_excel(writer, sheet_name="Metadatos", index=False)

        return ruta_archivo

    def _aplicar_plantilla_txt(
        self, datos: list[dict[str, Any]], ruta_archivo: Path, plantilla: str
    ) -> Path:
        """Aplicar plantilla personalizada para formato TXT"""
        with open(plantilla, encoding="utf-8") as f:
            plantilla_content = f.read()

        # Reemplazar marcadores de posición
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        resultado = []

        for i, diccionario in enumerate(datos, 1):
            registro_plantilla = plantilla_content
            registro_plantilla = registro_plantilla.replace("{NUMERO}", str(i))
            registro_plantilla = registro_plantilla.replace("{FECHA}", timestamp)

            # Reemplazar campos dinámicos
            for clave, valor in diccionario.items():
                marcador = "{" + clave.upper() + "}"
                registro_plantilla = registro_plantilla.replace(
                    marcador, str(valor) if valor is not None else ""
                )

            resultado.append(registro_plantilla)

        with open(ruta_archivo, "w", encoding="utf-8") as f:
            f.write("\n".join(resultado))

        return ruta_archivo

    def _comprimir_archivo(self, ruta_archivo: Path) -> Path:
        """Comprimir archivo en formato ZIP"""
        ruta_zip = ruta_archivo.with_suffix(".zip")

        with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(ruta_archivo, ruta_archivo.name)

        # Eliminar archivo original
        ruta_archivo.unlink()

        return ruta_zip

    def _abrir_archivo(self, ruta_archivo: Path):
        """Abrir archivo con aplicación predeterminada"""
        try:
            if ruta_archivo.suffix.lower() == ".csv":
                subprocess.Popen(["notepad.exe", str(ruta_archivo)])
            elif ruta_archivo.suffix.lower() in [".xlsx", ".xls"]:
                subprocess.Popen(["start", "excel", str(ruta_archivo)], shell=True)
            elif ruta_archivo.suffix.lower() == ".json":
                subprocess.Popen(["notepad.exe", str(ruta_archivo)])
            elif ruta_archivo.suffix.lower() == ".xml":
                subprocess.Popen(["notepad.exe", str(ruta_archivo)])
            else:
                subprocess.Popen(["notepad.exe", str(ruta_archivo)])
        except Exception as e:
            self.logger.warning(f"No se pudo abrir el archivo {ruta_archivo}: {e}")

    def crear_plantilla_ejemplo(self, nombre_archivo: str = "plantilla_ejemplo.txt") -> Path:
        """Crear una plantilla de ejemplo para formato TXT"""
        ruta_plantilla = self.directorio_salida / nombre_archivo

        contenido_plantilla = """
Registro N°: {NUMERO}
Fecha: {FECHA}
========================================
Campos del registro:
{CAMPO1}: {VALOR1}
{CAMPO2}: {VALOR2}
{CAMPO3}: {VALOR3}
========================================
"""

        with open(ruta_plantilla, "w", encoding="utf-8") as f:
            f.write(contenido_plantilla.strip())

        return ruta_plantilla

    def limpiar_resultados_antiguos(self, dias: int = 7):
        """Limpiar archivos de resultados más antiguos que los días especificados"""
        cutoff_date = datetime.now().timestamp() - (dias * 24 * 3600)

        for archivo in self.directorio_salida.glob("*"):
            if archivo.is_file() and archivo.stat().st_mtime < cutoff_date:
                archivo.unlink()
                self.logger.info(f"Eliminado archivo antiguo: {archivo}")


# Función de conveniencia para uso rápido
def exportar_resultados(
    datos: list[dict[str, Any]], formato: str = "txt", nombre_archivo: str | None = None, **kwargs
) -> str:
    """
    Función de conveniencia para exportar resultados rápidamente

    Args:
        datos: Datos a exportar
        formato: Formato de exportación
        nombre_archivo: Nombre base del archivo
        **kwargs: Argumentos adicionales para ExportadorResultados.exportar

    Returns:
        str: Ruta del archivo exportado
    """
    exportador = ExportadorResultados()
    return exportador.exportar(datos, formato, nombre_archivo, **kwargs)

"""
Configuración y utilidades para el módulo de exportación
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ExportConfig:
    """Configuración de exportación"""
    formato_defecto: str = "txt"
    directorio_salida: str = "resultados"
    comprimir_defecto: bool = False
    abrir_archivo_defecto: bool = True
    dias_limpiar_resultados: int = 7
    plantilla_defecto: Optional[str] = None

    # Configuraciones por formato
    csv_delimitador: str = ","
    csv_quoting: int = 1  # csv.QUOTE_ALL
    csv_encoding: str = "utf-8-sig"

    json_indent: int = 2
    json_ensure_ascii: bool = False

    xml_encoding: str = "utf-8"
    xml_declaration: bool = True

    excel_sheet_name: str = "Datos"
    excel_index: bool = False
    excel_include_metadata: bool = True


class ConfigManager:
    """Gestor de configuración del exportador"""

    def __init__(self, config_file: str = "export_config.json"):
        self.config_file = Path(config_file)
        self.config = self._cargar_config()

    def _cargar_config(self) -> ExportConfig:
        """Cargar configuración desde archivo"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return ExportConfig(**data)
            except Exception as e:
                print(f"Error cargando configuración, usando valores por defecto: {e}")

        return ExportConfig()

    def guardar_config(self):
        """Guardar configuración actual a archivo"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(asdict(self.config), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando configuración: {e}")

    def actualizar_config(self, **kwargs):
        """Actualizar valores de configuración"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self.guardar_config()


# Instancia global del gestor de configuración
config_manager = ConfigManager()

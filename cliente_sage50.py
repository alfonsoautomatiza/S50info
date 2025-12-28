"""SAGE50 API client module for external scripts.

Provides a simple function to get a connected SAGE50 API instance.
"""

import logging
from typing import Any

try:
    import libsage50
except ImportError:
    libsage50 = None
    logging.warning("libsage50 module not available")


def cliente_sage50(carencia_check: bool = True, app: str = "S02") -> Any:
    """
    Crea y devuelve una instancia del API de SAGE50 conectada.

    Args:
        carencia_check: Si debe verificar carencia (default: True)
        app: Código de aplicación (default: "S02")

    Returns:
        Instancia de apiSAGE50 conectada o None si hay error

    Example:
        >>> from cliente_sage50 import cliente_sage50
        >>> api = cliente_sage50()
        >>> if api:
        ...     # Usar api para operaciones con SAGE50
        ...     resultado = api.ejecutar_sql("SELECT * FROM tabla")
    """
    if not libsage50:
        logging.error("libsage50 no está disponible")
        return None

    try:
        api = libsage50.apiSAGE50(carencia_check=carencia_check, app=app)
        logging.info("Cliente SAGE50 creado exitosamente")
        return api
    except Exception as e:
        logging.error(f"Error al crear cliente SAGE50: {e}")
        return None

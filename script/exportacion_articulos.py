"""Ejemplo formativo de exportacion de articulos con `s50info run`.

Uso:
    s50info run script/exportacion_articulos.py

Que demuestra este ejemplo:
- `proceso.query_to_dict(...)` para obtener datos como lista de diccionarios
- control de years con `sqlyear` (`+`, `@`, year concreto o lista)
- agrupacion final con `groupby` cuando hay varios ejercicios
- exportacion con `proceso.imprimir_diccionarios(...)`
- formatos posibles: `txt`, `csv`, `json`, `xml`, `xlsx`

Notas tecnicas:
- `query_to_dict` aplica la resolucion de years y comunes igual que la CLI
- si usas `groupby` y varios years, la agrupacion se hace al final de la union
- el script decide que hacer con los datos; no necesita conocer el SQL interno de otros samples
- buena practica: ejecutar siempre el script desde `s50info run` para que la
  configuracion activa, years y comunes se resuelvan de nuevo en cada ejecucion
"""


def exportar_articulos_base():
    """Consulta base del ultimo ejercicio y exportacion a Excel."""
    datos = proceso.query_to_dict(
        """
        select codigo, nombre, familia
        from #articulo
        """
    )
    print(f"Articulos recuperados (year actual): {len(datos)}")
    proceso.imprimir_diccionarios(
        datos,
        formato="xlsx",
        nombre_archivo="articulos_base",
        comprimir=False,
    )


def exportar_articulos_por_year():
    """Ejemplo forzando un year concreto."""
    datos = proceso.query_to_dict(
        """
        select codigo, nombre, familia
        from #articulo
        """,
        sqlyear="2025",
    )
    print(f"Articulos recuperados (2025): {len(datos)}")
    proceso.imprimir_diccionarios(
        datos,
        formato="csv",
        nombre_archivo="articulos_2025",
        comprimir=False,
    )


def exportar_articulos_multi_year_agrupados():
    """Ejemplo multi-year con agrupacion final para evitar duplicados."""
    datos = proceso.query_to_dict(
        """
        select codigo, max(nombre) as nombre
        from #articulo
        """,
        sqlyear="@",
        groupby="codigo",
    )
    print(f"Articulos agrupados entre ejercicios: {len(datos)}")
    proceso.imprimir_diccionarios(
        datos,
        formato="json",
        nombre_archivo="articulos_groupby",
        comprimir=False,
    )


def exportar_formatos_posibles():
    """Muestra varios formatos con un dataset pequeno para comparar salidas."""
    datos = proceso.query_to_dict(
        """
        select codigo, nombre
        from #articulo
        """
    )
    formatos = ["txt", "xml"]
    for formato in formatos:
        proceso.imprimir_diccionarios(
            datos,
            formato=formato,
            nombre_archivo=f"articulos_demo_{formato}",
            comprimir=False,
        )
        print(f"Exportado ejemplo en formato: {formato}")


def main():
    exportar_articulos_base()
    exportar_articulos_por_year()
    exportar_articulos_multi_year_agrupados()
    exportar_formatos_posibles()


if __name__ == "__main__":
    main()

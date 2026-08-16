"""Ejemplo formativo de seleccion y exportacion de plantillas gratuitas SAGE50BI.

Uso:
    s50info run "script/Ejemplo_lite_sage50bi.py"

Que demuestra este ejemplo:
- `proceso.seleccionar_samples()` para elegir datasets desde consola
- `proceso.imprimir_diccionarios(...)` para decidir el formato final desde el script

El selector interactivo muestra:
- titulo
- descripcion
- marca `[x]` para seleccion
- opciones todos / ninguno

Este ejemplo exporta a `xlsx`, pero el mismo flujo podria exportar a otros formatos.
"""


def main():
    seleccionados = proceso.seleccionar_samples()
    if not seleccionados:
        print("No se selecciono ningun dataset.")
        return

    for item in proceso.exportar_samples(seleccionados):
        print("-" * 80)
        print(f"Dataset: {item['nombre']}")
        print(f"Titulo: {item['titulo']}")
        if item["descripcion"]:
            print(f"Descripcion: {item['descripcion']}")

        if item["ok"]:
            print("Estado: OK")
            print(f"Registros recuperados: {item['registros']}")
            proceso.imprimir_diccionarios(
                item["datos"],
                formato="xlsx",
                nombre_archivo=item["nombre"],
                comprimir=False,
            )
        else:
            print("Estado: ERROR")
            print(f"Detalle: {item['error']}")


if __name__ == "__main__":
    main()

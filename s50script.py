"""Helpers para scripts externos ejecutados desde `s50info run`.

Este fichero centraliza las consultas reutilizables para los ejemplos de la
carpeta `script/`. La idea es que sea facil de mantener:

- cada consulta vive en `BI_QUERIES`
- cada entrada define su SQL y los parametros recomendados
- `samplebi(nombre)` usa esos valores por defecto

El comando `s50info.py run` inyecta automaticamente el objeto `proceso`
en `builtins.s50info_proceso`, junto con `query_to_dict`, por lo que no
hace falta importarlos manualmente.

Buena practica recomendada:
- asumir que los scripts de `run` son de confianza y solo lectura
- obtener la configuracion y el contexto de years/comunes en cada ejecucion,
  sin depender del estado dejado por un script anterior
- lanzar siempre los ejemplos mediante el ejecutable principal:

    s50info run script/exportacion_articulos.py
    s50info run script/visualizar_log_analisis_excel_reseteo.py

Tambien quedan accesibles como metodos de `proceso`:

    proceso.query_to_dict("select * from #clientes")
    proceso.imprimir_diccionarios(datos, formato="xlsx", nombre_archivo="clientes")
"""

from __future__ import annotations

import builtins
import os
from dataclasses import dataclass
from textwrap import dedent

try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


@dataclass(frozen=True)
class BIQuery:
    """Definicion de una consulta reutilizable para scripts BI."""

    sql: str
    titulo: str = ""
    descripcion: str = ""
    sqlyear: str = "+"
    grupo_comunes: str | None = None
    groupby: str | None = None
    fast_build: bool = False


BI_QUERIES = {
    "DetalleCargaCamion": BIQuery(
        titulo="Carga reparto por cliente",
        descripcion="Consulta de carga de camión basada en etiquetas de envío y albaranes de venta, con detalle por artículo, unidades e importe cargado.",
        sql=dedent(
            """
            SELECT
                RTRIM(LTRIM(e.CONTADOR)) AS Codigo_Etiqueta,
                CAST(e.FECHA AS DATE) AS Fecha_Etiqueta,
                RTRIM(LTRIM(e.CONTADOR)) + '-' + CONVERT(VARCHAR(10), CAST(e.FECHA AS DATE), 120) AS Etiqueta,
                RTRIM(LTRIM(e.ALB_DEPO)) AS Tipo_Documento,
                RTRIM(LTRIM(e.LETRA)) AS Serie_Albaran,
                RTRIM(LTRIM(e.NUMERO)) AS Numero_Albaran,
                RTRIM(LTRIM(d.ARTICULO)) AS Codigo_Articulo,
                MAX(RTRIM(LTRIM(a.NOMBRE))) AS Nombre_Articulo,
                SUM(ISNULL(d.UNIDADES, 0)) AS Unidades,
                SUM(ISNULL(d.IMPORTE, 0)) AS Importe
            FROM #ENVIOETI e
            INNER JOIN #C_ALBVEN c
                ON RTRIM(LTRIM(c.LETRA))  = RTRIM(LTRIM(e.LETRA))
            AND RTRIM(LTRIM(c.NUMERO)) = RTRIM(LTRIM(e.NUMERO))
            INNER JOIN #D_ALBVEN d
                ON c.EMPRESA = d.EMPRESA
            AND RTRIM(LTRIM(c.LETRA))  = RTRIM(LTRIM(d.LETRA))
            AND RTRIM(LTRIM(c.NUMERO)) = RTRIM(LTRIM(d.NUMERO))
            LEFT JOIN #ARTICULO a
                ON RTRIM(LTRIM(a.CODIGO)) = RTRIM(LTRIM(d.ARTICULO))
            GROUP BY
                RTRIM(LTRIM(e.CONTADOR)),
                CAST(e.FECHA AS DATE),
                RTRIM(LTRIM(e.ALB_DEPO)),
                RTRIM(LTRIM(e.LETRA)),
                RTRIM(LTRIM(e.NUMERO)),
                RTRIM(LTRIM(d.ARTICULO))
            """
        ).strip(),
        sqlyear="+",
        fast_build=True,
    ),
    "DeudaPorVendedor": BIQuery(
        titulo="Deuda Por Vendedor y Porcentaje sobre el total empresa",
        descripcion="Consulta de deuda pendiente por vendedor que calcula el total pendiente de cobro asignado a sus clientes y el porcentaje que representa sobre la deuda total.",
        sql=dedent(
            """
            SELECT RTRIM(LTRIM(V.CODIGO)) AS Codigo_Vendedor, RTRIM(LTRIM(V.NOMBRE)) AS Nombre_Vendedor, SUM(P.PENDIENTE) AS Deuda_Total, ROUND( (SUM(P.PENDIENTE) * 100.0) / NULLIF( (SELECT SUM(P2.PENDIENTE) FROM [COMU]PREVI_CL AS P2 WHERE P2.EMPRESA = '01' AND ((P2.COBRO IS NULL AND P2.IMPAGADO = 0) OR P2.PENDIENTE > 0) ), 0 ), 2 ) AS Porc_Deuda FROM [COMU]PREVI_CL AS P INNER JOIN #CLIENTES AS C ON RTRIM(LTRIM(P.CLIENTE)) = RTRIM(LTRIM(C.CODIGO)) LEFT JOIN #VENDEDOR AS V ON RTRIM(LTRIM(C.VENDEDOR)) = RTRIM(LTRIM(V.CODIGO)) WHERE P.EMPRESA = '01' AND ((P.COBRO IS NULL AND P.IMPAGADO = 0) OR P.PENDIENTE > 0) GROUP BY V.CODIGO, V.NOMBRE
            """
        ).strip(),
        sqlyear="+",
        fast_build=True,
    ),
    "CuotasClienteConcepto": BIQuery(
        titulo="Cuotas Cliente Concepto vigentes.",
        descripcion="Consulta de cuotas por cliente y concepto que muestra descripción, fechas de vigencia, importe, meses de cobro y periodicidad en meses.",
        sql=dedent(
            """
            SELECT cli.codigo, cli.nombre, con.nombre AS concepto, cuo.descripcio, cuo.fecha_ini, cuo.fecha_fin, cuo.importe, m.meses_cobro, m.periodicidad_meses FROM [COMU]CUOTAS cuo INNER JOIN #CLIENTES cli ON RTRIM(LTRIM(cuo.cliente)) = RTRIM(LTRIM(cli.codigo)) LEFT JOIN [COMU]CONCEP con ON RTRIM(LTRIM(cuo.concepto)) = RTRIM(LTRIM(con.codigo)) OUTER APPLY ( SELECT STRING_AGG( CASE cm.MES WHEN 1 THEN 'Enero' WHEN 2 THEN 'Febrero' WHEN 3 THEN 'Marzo' WHEN 4 THEN 'Abril' WHEN 5 THEN 'Mayo' WHEN 6 THEN 'Junio' WHEN 7 THEN 'Julio' WHEN 8 THEN 'Agosto' WHEN 9 THEN 'Septiembre' WHEN 10 THEN 'Octubre' WHEN 11 THEN 'Noviembre' WHEN 12 THEN 'Diciembre' END, ', ' ) WITHIN GROUP (ORDER BY cm.MES) AS meses_cobro, MAX(cm.MES_ANT) AS periodicidad_meses FROM [COMU]CUO_MES cm WHERE RTRIM(LTRIM(cm.CLIENTE)) = RTRIM(LTRIM(cuo.CLIENTE)) AND RTRIM(LTRIM(cm.CONCEPTO)) = RTRIM(LTRIM(cuo.CONCEPTO)) ) m
            """
        ).strip(),
        sqlyear="+",
        fast_build=True,
    ),
    "Ventas_Dto_Cliente_Articulo": BIQuery(
        titulo="Ventas Dto Cliente Articulo FAmilia",
        descripcion="Consulta de ventas de albaranes que muestra importes antes y después de descuento, calcula el descuento medio ponderado en porcentaje y el descuento total en euros, desglosado por familia, artículo, cliente, vendedor y fecha.",
        sql=dedent(
            """
            SELECT
                art.FAMILIA AS Codigo_Familia,
                fam.NOMBRE AS Nombre_Familia,
                d.ARTICULO AS Codigo_Articulo,
                art.NOMBRE AS Nombre_Articulo,
                cli.CODIGO AS Codigo_Cliente,
                cli.NOMBRE AS Nombre_Cliente,
                ven.CODIGO AS Codigo_Vendedor,
                ven.NOMBRE AS Nombre_Vendedor,
                CAST(c.FECHA AS DATE) AS Fecha_Albaran,

                SUM(d.PRECIO * d.UNIDADES) AS Total_Sin_DTO,
                SUM(d.IMPORTE) AS Importe_Total_con_dto,

                ROUND(
                    100.0 * SUM(
                        (d.PRECIO * d.UNIDADES) * (
                            1.0 - ((1.0 - (d.DTO1 / 100.0)) * (1.0 - (d.DTO2 / 100.0)))
                        )
                    ) / NULLIF(SUM(d.PRECIO * d.UNIDADES), 0),
                    2
                ) AS Media_Ponderada_DTO_Porcentaje,

                ROUND(
                    SUM(
                        (d.PRECIO * d.UNIDADES) * (
                            1.0 - ((1.0 - (d.DTO1 / 100.0)) * (1.0 - (d.DTO2 / 100.0)))
                        )
                    ),
                    2
                ) AS DTO_En_Euros

                FROM
                    #D_ALBVEN d
                INNER JOIN
                    #C_ALBVEN c
                    ON  d.EMPRESA = c.EMPRESA
                    AND RTRIM(LTRIM(d.LETRA)) = RTRIM(LTRIM(c.LETRA))
                    AND d.NUMERO = c.NUMERO
                INNER JOIN
                    #CLIENTES cli
                    ON RTRIM(LTRIM(c.CLIENTE)) = RTRIM(LTRIM(cli.CODIGO))
                LEFT JOIN
                    #VENDEDOR ven
                    ON RTRIM(LTRIM(c.VENDEDOR)) = RTRIM(LTRIM(ven.CODIGO))
                INNER JOIN
                    #ARTICULO art
                    ON RTRIM(LTRIM(d.ARTICULO)) = RTRIM(LTRIM(art.CODIGO))
                LEFT JOIN
                    #FAMILIAS fam
                    ON RTRIM(LTRIM(art.FAMILIA)) = RTRIM(LTRIM(fam.CODIGO))
                GROUP BY
                    art.FAMILIA, fam.NOMBRE, d.ARTICULO, art.NOMBRE,
                    cli.CODIGO, cli.NOMBRE, ven.CODIGO, ven.NOMBRE,
                    CAST(c.FECHA AS DATE)
            """
        ).strip(),
        sqlyear="+",
        fast_build=True,
    ),
    "Carga_Reparto_por_cliente": BIQuery(
        titulo="Carga reparto por cliente",
        descripcion="consulta de albaranes de venta en Sage50BI que obtiene información combinada de clientes, artículos, familias y líneas de documento.",
        sql=dedent(
            """
            select cli.nombre2 as cliente,a.nombre as Codigo,d.UNIDADES as num,fa.nombre as familia,c.fecha         	from  #c_albven c 	        INNER JOIN #D_ALBVEN d  ON c.empresa = d.empresa AND c.numero = d.numero AND c.letra 	= d.letra 	INNER JOIN #CLIENTES cli  ON c.cliente = cli.codigo 	LEFT JOIN #ARTICULO a  ON d.articulo = a.codigo 	LEFT JOIN #familias fa  ON a.familia = fa.CODIGO
            """
        ).strip(),
        sqlyear="+",
        fast_build=True,
    ),
    "Rentabilidad_albaran_lote": BIQuery(
        titulo="Rentabilidad albarán y lote",
        descripcion="Detalle completo de los albaranes de venta y sus líneas, incluyendo cliente, vendedor, artículo, importes, divisa, portes, familia, coste, beneficio y desglose por lotes, prorrateando además el coste total de cada línea entre los lotes según su peso o unidades.",
        sql=dedent(
            """
            select  c.letra AS serie, c.fecha, c.numero AS documento, c.pronto, d.numero AS documento_linia, d.letra AS serie_linia, c.divisa AS codigo_divisa, d.linia, CASE m.simbolo WHEN '' THEN m.ABREV ELSE m.simbolo END AS divisa, c.cliente AS cliente, cli.nombre AS nombre_cliente, c.vendedor, COALESCE(ven.nombre, REPLICATE(' ', 50)) AS nombre_vendedor, d.vendedor AS vendedor_linea, COALESCE(ven_linea.nombre, REPLICATE(' ', 50)) AS nombre_vendedor_linea, d.articulo, d.definicion AS nombre_articulo, d.peso, d.codagrup, d.cajas, d.uniagrup, d.unidades, d.tipoprec, D.PRECIOIVA AS precio, d.dto1 AS dto11, d.dto2 AS dto21, D.IMPORTEIVA AS importe, D.PREDIVIVA AS divisa_precio, d.dto1, d.dto2, D.IMPDIVIVA AS divisa_importe, c.ruta AS ruta, rutas.nombre AS nombre_ruta, let.nombre AS nombre_serie, d.comision, d.imp_com, d.tipo_iva, /* === COSTE TOTAL DE LA LÍNEA === */ CASE WHEN d.importe >= 0 THEN (d.coste * d.unidades) ELSE (CASE WHEN d.coste < 0 THEN 1 ELSE -1 END * d.coste * ABS(d.unidades)) END AS coste_total_linea, /* Beneficio y % beneficio sobre la línea */ d.importe - CASE WHEN d.importe >= 0 THEN (d.coste * d.unidades) ELSE (CASE WHEN d.coste < 0 THEN 1 ELSE -1 END * d.coste * ABS(d.unidades)) END AS beneficio_linea, CASE WHEN d.importe <> 0 THEN ( ( D.IMPORTE - CASE WHEN d.importe >= 0 THEN (d.coste * d.unidades) ELSE (CASE WHEN d.coste < 0 THEN 1 ELSE -1 END * d.coste * ABS(d.unidades)) END ) / D.IMPORTE ) * 100.0 ELSE 0.0 END AS prcbenef_linea, c.factura, c.asi, c.recc, d.linia AS linia1, c.facturable, COALESCE(ag.nombre, '') AS nombre_agencia, COALESCE(p.importe, 0) AS portes, COALESCE(p.importeDiv, 0) AS portesdiv, COALESCE(p.tipo_porte, 0) AS tipo_porte, COALESCE(tip.iva, 0) AS iva_portes, COALESCE(p.tipo_iva, '') AS tipo_iva_portes, COALESCE(p.iva_inc, 0) AS ivainc_portes, COALESCE(p.inc_fra, 0) AS inc_fra_portes, d.importe AS importesiniva, d.importeiva AS importeconiva, d.importediv AS importesinivadiv, d.impdiviva AS importeconivadiv, COALESCE(cli.codpost, REPLICATE(' ', 10)) AS clicodpos, COALESCE(cli.poblacion, REPLICATE(' ', 50)) AS clipoblacion, COALESCE(cli.tarifa, ' ') AS clitarifa, c.empresa, c.codpost AS cabcodpos, c.totaldoc, c.totaldiv, COALESCE(sup.codigo, ' ') AS codigosuplido, COALESCE(sup.nombre, REPLICATE(' ', 50)) AS conceptosuplido, d.suplido, d.escandal, d.pverde, cli.tipofac, /* === DESGLOSE POR LOTE === */ '' AS NUMSERIE, RTRIM(LTRIM(lt.lote)) AS NUMLOTE, COALESCE(lt.unidades, 0) AS UDSLOTE, COALESCE(lt.peso, 0.0) AS PESOLOTE, /* Totales por línea para prorrateo */ SUM(COALESCE(lt.peso,0.0)) OVER ( PARTITION BY d.empresa, d.letra, d.numero, d.linia, d.articulo, d.talla, d.color ) AS PESO_LINEA, SUM(COALESCE(lt.unidades,0)) OVER ( PARTITION BY d.empresa, d.letra, d.numero, d.linia, d.articulo, d.talla, d.color ) AS UDS_LINEA, /* Coste total asignado al lote */ CASE WHEN SUM(COALESCE(lt.peso,0.0)) OVER ( PARTITION BY d.empresa, d.letra, d.numero, d.linia, d.articulo, d.talla, d.color ) > 0.0 THEN (CASE WHEN d.importe >= 0 THEN (d.coste * d.unidades) ELSE (CASE WHEN d.coste < 0 THEN 1 ELSE -1 END * d.coste * ABS(d.unidades)) END) * (COALESCE(lt.peso,0.0) / NULLIF( SUM(COALESCE(lt.peso,0.0)) OVER ( PARTITION BY d.empresa, d.letra, d.numero, d.linia, d.articulo, d.talla, d.color ), 0.0 )) ELSE (CASE WHEN d.importe >= 0 THEN (d.coste * d.unidades) ELSE (CASE WHEN d.coste < 0 THEN 1 ELSE -1 END * d.coste * ABS(d.unidades)) END) * (COALESCE(lt.unidades,0) / NULLIF( SUM(COALESCE(lt.unidades,0)) OVER ( PARTITION BY d.empresa, d.letra, d.numero, d.linia, d.articulo, d.talla, d.color ), 0 )) END AS COSTE_TOTAL_LOTE, /* === Coste unitario €/kg del lote === */ CASE WHEN COALESCE(lt.peso,0.0) <> 0.0 AND SUM(COALESCE(lt.peso,0.0)) OVER ( PARTITION BY d.empresa, d.letra, d.numero, d.linia, d.articulo, d.talla, d.color ) > 0.0 THEN (CASE WHEN d.importe >= 0 THEN (d.coste * d.unidades) ELSE (CASE WHEN d.coste < 0 THEN 1 ELSE -1 END * d.coste * ABS(d.unidades)) END) / NULLIF( SUM(COALESCE(lt.peso,0.0)) OVER ( PARTITION BY d.empresa, d.letra, d.numero, d.linia, d.articulo, d.talla, d.color ), 0.0 ) ELSE NULL END AS COSTE_UNITARIO_KG, a.familia AS familia, f.nombre AS NOMBRE_FAMILIA FROM #C_ALBVEN c JOIN #D_ALBVEN d ON RTRIM(LTRIM(c.empresa)) = RTRIM(LTRIM(d.empresa)) AND RTRIM(LTRIM(c.numero)) = RTRIM(LTRIM(d.numero)) AND RTRIM(LTRIM(c.letra)) = RTRIM(LTRIM(d.letra)) LEFT JOIN #CLIENTES cli ON RTRIM(LTRIM(c.cliente)) = RTRIM(LTRIM(cli.codigo)) LEFT JOIN #ARTICULO a ON RTRIM(LTRIM(d.articulo)) = RTRIM(LTRIM(a.codigo)) LEFT JOIN #FAMILIAS f ON RTRIM(LTRIM(a.familia)) = RTRIM(LTRIM(f.codigo)) LEFT JOIN #PORTES p ON RTRIM(LTRIM(c.empresa)) = RTRIM(LTRIM(p.empresa)) AND RTRIM(LTRIM(c.numero)) = RTRIM(LTRIM(p.albaran)) AND RTRIM(LTRIM(c.letra)) = RTRIM(LTRIM(p.letra)) LEFT JOIN #TIPO_IVA tip ON RTRIM(LTRIM(p.tipo_iva)) = RTRIM(LTRIM(tip.codigo)) LEFT JOIN #AGENCIA ag ON RTRIM(LTRIM(p.agencia)) = RTRIM(LTRIM(ag.codigo)) LEFT JOIN #RUTAS rutas ON RTRIM(LTRIM(c.ruta)) = RTRIM(LTRIM(rutas.codigo)) LEFT JOIN [COMU]OBRA obra ON RTRIM(LTRIM(c.obra)) = RTRIM(LTRIM(obra.codigo)) LEFT JOIN #VENDEDOR ven ON RTRIM(LTRIM(c.vendedor)) = RTRIM(LTRIM(ven.codigo)) LEFT JOIN #VENDEDOR ven_linea ON RTRIM(LTRIM(d.vendedor)) = RTRIM(LTRIM(ven_linea.codigo)) LEFT JOIN [COMU]TALLAS tal ON RTRIM(LTRIM(d.talla)) = RTRIM(LTRIM(tal.codigo)) LEFT JOIN [COMU]COLORES col ON RTRIM(LTRIM(d.color)) = RTRIM(LTRIM(col.codigo)) AND RTRIM(LTRIM(col.Empresa)) IN ('01') LEFT JOIN [COMU]LETRAS let ON RTRIM(LTRIM(c.letra)) = RTRIM(LTRIM(let.codigo)) LEFT JOIN #MONEDA m ON RTRIM(LTRIM(c.divisa)) = RTRIM(LTRIM(m.codigo)) LEFT JOIN [COMU]SUPLIDOS sup ON RTRIM(LTRIM(a.csuplido)) = RTRIM(LTRIM(sup.codigo)) /* Subconsulta en lugar de CTE */ LEFT JOIN ( SELECT RTRIM(LTRIM(empresa)) AS empresa, RTRIM(LTRIM(letra)) AS letra, RTRIM(LTRIM(numero)) AS numero, linia, RTRIM(LTRIM(articulo)) AS articulo, RTRIM(LTRIM(talla)) AS talla, RTRIM(LTRIM(color)) AS color, RTRIM(LTRIM(lote)) AS lote, SUM(COALESCE(unidades,0)) AS unidades, SUM(COALESCE(peso,0)) AS peso FROM [lotes0JP].dbo.LTALBVE GROUP BY empresa, letra, numero, linia, articulo, talla, color, lote ) lt ON RTRIM(LTRIM(lt.empresa)) = RTRIM(LTRIM(d.empresa)) AND RTRIM(LTRIM(lt.letra)) = RTRIM(LTRIM(d.letra)) AND RTRIM(LTRIM(lt.numero)) = RTRIM(LTRIM(d.numero)) AND lt.linia = d.linia AND RTRIM(LTRIM(lt.articulo)) = RTRIM(LTRIM(d.articulo)) AND RTRIM(LTRIM(lt.talla)) = RTRIM(LTRIM(d.talla)) AND RTRIM(LTRIM(lt.color)) = RTRIM(LTRIM(d.color))
            """
        ).strip(),
        sqlyear="+",
        fast_build=True,
    ),
    "Ventas_Vendores_por_ranking": BIQuery(
        titulo="Ventas Vendores y documentos no convertidos por ranking",
        descripcion="Ranking de ventas por vendedor y ejercicio.",
        sql=dedent(
            """
            SELECT
                X.Ejercicio,
                X.Codigo_Vendedor,
                RTRIM(LTRIM(V.NOMBRE)) AS Nombre_Vendedor,
                X.Total_Pedidos_SinIVA,
                X.Total_Albaranes_SinIVA,
                X.Total_Vendido_SinIVA,
                DENSE_RANK() OVER (
                    PARTITION BY X.Ejercicio
                    ORDER BY X.Total_Vendido_SinIVA DESC
                ) AS Ranking_Ventas
            FROM (
                SELECT
                    COALESCE(A.Ejercicio, P.Ejercicio) AS Ejercicio,
                    COALESCE(A.Codigo_Vendedor, P.Codigo_Vendedor) AS Codigo_Vendedor,
                    ISNULL(P.Total_Pedidos, 0) AS Total_Pedidos,
                    ISNULL(P.Importe_Pedidos_SinIVA, 0) AS Total_Pedidos_SinIVA,
                    ISNULL(A.Total_Albaranes, 0) AS Total_Albaranes,
                    ISNULL(A.Importe_Albaranes_SinIVA, 0) AS Total_Albaranes_SinIVA,
                    ISNULL(A.Importe_Albaranes_SinIVA, 0)
                    + ISNULL(P.Importe_Pedidos_SinIVA, 0) AS Total_Vendido_SinIVA
                FROM (
                    SELECT
                        Q.Ejercicio,
                        Q.Codigo_Vendedor,
                        COUNT(DISTINCT Q.Factura) AS Total_Albaranes,
                        SUM(Q.Importe_Linea) AS Importe_Albaranes_SinIVA
                    FROM (
                        SELECT
                            CONVERT(varchar(4), YEAR(ISNULL(C.FECHA_FAC, C.FECHA))) AS Ejercicio,
                            RTRIM(LTRIM(C.VENDEDOR)) AS Codigo_Vendedor,
                            RTRIM(LTRIM(C.FACTURA)) AS Factura,
                            D.IMPORTE AS Importe_Linea
                        FROM #C_ALBVEN AS C
                        INNER JOIN #D_ALBVEN AS D
                            ON C.EMPRESA = D.EMPRESA
                            AND RTRIM(LTRIM(C.LETRA)) = RTRIM(LTRIM(D.LETRA))
                            AND RTRIM(LTRIM(C.NUMERO)) = RTRIM(LTRIM(D.NUMERO))
                        WHERE C.EMPRESA = '01'
                            AND RTRIM(LTRIM(C.FACTURA)) <> ''
                    ) AS Q
                    GROUP BY Q.Ejercicio, Q.Codigo_Vendedor
                ) AS A
                FULL OUTER JOIN (
                    SELECT
                        CONVERT(varchar(4), YEAR(C.FECHA)) AS Ejercicio,
                        RTRIM(LTRIM(C.VENDEDOR)) AS Codigo_Vendedor,
                        COUNT(
                            DISTINCT RTRIM(LTRIM(C.LETRA)) + '-' + RTRIM(LTRIM(C.NUMERO))
                        ) AS Total_Pedidos,
                        SUM(D.IMPORTE) AS Importe_Pedidos_SinIVA
                    FROM #C_PEDIVE AS C
                    INNER JOIN #D_PEDIVE AS D
                        ON C.EMPRESA = D.EMPRESA
                        AND RTRIM(LTRIM(C.LETRA)) = RTRIM(LTRIM(D.LETRA))
                        AND RTRIM(LTRIM(C.NUMERO)) = RTRIM(LTRIM(D.NUMERO))
                    WHERE C.EMPRESA = '01'
                        AND C.CANCELADO = 0
                    GROUP BY
                        CONVERT(varchar(4), YEAR(C.FECHA)),
                        RTRIM(LTRIM(C.VENDEDOR))
                ) AS P
                    ON A.Ejercicio = P.Ejercicio
                    AND A.Codigo_Vendedor = P.Codigo_Vendedor
            ) AS X
            LEFT JOIN #VENDEDOR AS V
                ON RTRIM(LTRIM(X.Codigo_Vendedor)) = RTRIM(LTRIM(V.CODIGO))
            """
        ).strip(),
        sqlyear="@",
        fast_build=True,
    ),
    "Deuda_plazo_medio_vendedor_mes": BIQuery(
        titulo="Deuda y plazo medio vendedor mes",
        descripcion="Deuda pendiente y plazo medio de cobro por vendedor y mes.",
        sql=dedent(
            """
            SELECT
                YEAR(CAST(P.EMISION AS date)) AS Ejercicio,
                MONTH(CAST(P.EMISION AS date)) AS Mes,
                RTRIM(LTRIM(C.VENDEDOR)) AS Codigo_Vendedor,
                RTRIM(LTRIM(V.NOMBRE)) AS Nombre_Vendedor,
                SUM(
                    CASE
                        WHEN (P.COBRO IS NULL AND P.IMPAGADO = 0) OR (P.PENDIENTE > 0)
                        THEN ISNULL(P.PENDIENTE, 0)
                        ELSE 0
                    END
                ) AS Deuda_Pendiente,
                AVG(
                    CASE
                        WHEN P.COBRO IS NOT NULL THEN DATEDIFF(
                            DAY,
                            CAST(P.EMISION AS date),
                            CAST(P.COBRO AS date)
                        ) * 1.0
                        ELSE NULL
                    END
                ) AS Dias_Medios_Cobro
            FROM [COMU]PREVI_CL AS P
            INNER JOIN #CLIENTES AS C
                ON RTRIM(LTRIM(P.CLIENTE)) = RTRIM(LTRIM(C.CODIGO))
            LEFT JOIN #VENDEDOR AS V
                ON RTRIM(LTRIM(C.VENDEDOR)) = RTRIM(LTRIM(V.CODIGO))
            WHERE P.EMPRESA = '01'
            GROUP BY
                YEAR(CAST(P.EMISION AS date)),
                MONTH(CAST(P.EMISION AS date)),
                RTRIM(LTRIM(C.VENDEDOR)),
                RTRIM(LTRIM(V.NOMBRE))
            """
        ).strip(),
        sqlyear="+",
    ),
}

_BI_QUERY_KEYS = {key.lower(): key for key in BI_QUERIES}


def _resolver_sql(query: BIQuery | str) -> BIQuery:
    if isinstance(query, BIQuery):
        return query
    return BIQuery(sql=query)


def _resolver_nombre_sample(nombre: str) -> str:
    key = nombre.strip().lower()
    if key not in _BI_QUERY_KEYS:
        disponibles = ", ".join(sorted(BI_QUERIES))
        raise KeyError(f"Sample BI no definido: {nombre}. Disponibles: {disponibles}")
    return _BI_QUERY_KEYS[key]


def _render_sql_for_year(api, sql_template: str, year: str) -> str:
    template = api._prepare_template(sql_template)
    return api._replace_year_placeholder(template, year)


def _build_query_fast(proceso_obj, sql: str, comun: str | None, years):
    api = proceso_obj.api
    if comun and comun != api.comunes:
        api.comunes = comun

    if isinstance(years, str):
        years = [years]

    if not isinstance(years, (list, tuple)) or not years:
        raise ValueError("No se pudieron resolver years para la query BI.")

    template = api._prepare_template(sql)
    if "#" not in template:
        return _render_sql_for_year(api, template, years[0])

    queries = [f"({_render_sql_for_year(api, template, year)})" for year in years]
    return " UNION ALL ".join(queries)


def _get_proceso(proc=None):
    proceso_obj = proc or getattr(builtins, "s50info_proceso", None)
    if proceso_obj is None:
        raise RuntimeError(
            "No hay un objeto `proceso` disponible. Ejecuta este script con `s50info.py run` "
            "o pasa `proc=` explicitamente."
        )
    return proceso_obj


def query_to_dict(
    sql: str,
    *,
    proc=None,
    sqlyear: str = "+",
    grupo_comunes: str | None = None,
    groupby: str | None = None,
    fast_build: bool = False,
):
    """Ejecuta una query de lectura y devuelve una lista de diccionarios."""
    proceso_obj = _get_proceso(proc)
    comun, years = proceso_obj._resolver_contexto_consulta(
        sqlyear=sqlyear, grupo_comunes=grupo_comunes
    )
    if groupby and isinstance(years, (list, tuple)) and len(years) > 1:
        query = proceso_obj._construir_query_groupby(sql, comun, years, groupby)
    elif fast_build:
        query = _build_query_fast(proceso_obj, sql, comun, years)
    else:
        query = proceso_obj.api.build_query(sql_template=sql, sqlcomun=comun, years=years)
    return proceso_obj.api.sql_to_list(query=query, as_dict=True)


def samplebi(
    nombre: str,
    *,
    proc=None,
    sqlyear: str | None = None,
    grupo_comunes: str | None = None,
    groupby: str | None = None,
    fast_build: bool = False,
):
    """Devuelve datos de una query predefinida por nombre.

    Si la consulta definida en `BI_QUERIES` ya trae `sqlyear` o `groupby`, esos
    valores se usan por defecto para evitar errores comunes en consultas con
    agregaciones o cruces entre ejercicios.
    """
    key = _resolver_nombre_sample(nombre)
    spec = _resolver_sql(BI_QUERIES[key])
    return query_to_dict(
        spec.sql,
        proc=proc,
        sqlyear=sqlyear if sqlyear is not None else spec.sqlyear,
        grupo_comunes=grupo_comunes if grupo_comunes is not None else spec.grupo_comunes,
        groupby=groupby if groupby is not None else spec.groupby,
        fast_build=spec.fast_build,
    )


def samples_disponibles(nombres: list[str] | None = None):
    """Lista nombre, titulo y descripcion sin exponer el SQL."""
    keys = [_resolver_nombre_sample(nombre) for nombre in nombres] if nombres else list(BI_QUERIES)
    items = []
    for key in keys:
        spec = BI_QUERIES[key]
        items.append(
            {
                "nombre": key,
                "titulo": spec.titulo or key,
                "descripcion": spec.descripcion,
            }
        )
    return items


def exportar_samples(
    nombres: list[str],
    *,
    proc=None,
):
    """Obtiene datos BI uno a uno y continua ante errores.

    No exporta archivos. Devuelve para cada dataset su metadata y los `datos`
    para que el script llamador decida que hacer con ellos.
    """
    proceso_obj = _get_proceso(proc)
    resultados = []
    for item in samples_disponibles(nombres):
        try:
            datos = samplebi(item["nombre"], proc=proceso_obj)
            resultados.append(
                {
                    **item,
                    "datos": datos,
                    "registros": len(datos),
                    "ok": True,
                    "error": "",
                }
            )
        except Exception as exc:
            resultados.append(
                {
                    **item,
                    "datos": [],
                    "registros": 0,
                    "ok": False,
                    "error": str(exc),
                }
            )
    return resultados


def seleccionar_samples(nombres: list[str] | None = None):
    """Selector interactivo por consola para datasets BI.

    Controles:
    - Flechas arriba/abajo: mover cursor
    - Espacio: marcar/desmarcar
    - T: todos
    - N: ninguno
    - Enter: confirmar
    - Esc: cancelar
    """
    items = samples_disponibles(nombres)
    if not items:
        return []

    if msvcrt is None:
        return [item["nombre"] for item in items]

    seleccionados = {item["nombre"] for item in items}
    cursor = 0

    while True:
        os.system("cls")
        print("Plantillas gratuitas de SAGE50BI")
        print("Marque con espacio, T=todos, N=ninguno, Enter=generar, Esc=salir")
        print("-" * 80)

        for idx, item in enumerate(items):
            marca = "x" if item["nombre"] in seleccionados else " "
            prefijo = ">" if idx == cursor else " "
            print(f"{prefijo} [{marca}] {item['titulo']}")
            if item["descripcion"]:
                print(f"    {item['descripcion']}")

        tecla = msvcrt.getwch()
        if tecla in ("\r", "\n"):
            return [item["nombre"] for item in items if item["nombre"] in seleccionados]
        if tecla == "\x1b":
            return []
        if tecla == " ":
            nombre = items[cursor]["nombre"]
            if nombre in seleccionados:
                seleccionados.remove(nombre)
            else:
                seleccionados.add(nombre)
            continue
        if tecla.lower() == "t":
            seleccionados = {item["nombre"] for item in items}
            continue
        if tecla.lower() == "n":
            seleccionados.clear()
            continue
        if tecla in ("\x00", "\xe0"):
            flecha = msvcrt.getwch()
            if flecha == "H":
                cursor = (cursor - 1) % len(items)
            elif flecha == "P":
                cursor = (cursor + 1) % len(items)

    return []

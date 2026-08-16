# Premortem — S50Info como puente hacia Sage50BI

Fecha: 2026-07-30

## Contexto recopilado

- **Qué**: donar S50Info (CLI técnica gratuita para Sage50: SQL, exportación, scripts) a la comunidad, para generar tracción y cross-promotion hacia Sage50BI (producto con dashboards/informes/plantillas para usuarios finales de negocio).
- **Para quién es S50Info**: técnicos de sistemas, desarrolladores/integradores, consultores ERP, contables avanzados.
- **Para quién es Sage50BI**: usuarios finales de negocio, menos técnicos, buscan dashboards e informes listos.
- **Éxito**: que quien use S50Info entienda que si quiere "más" (informes, dashboards, UX amigable) debe usar Sage50BI. El README actual ya menciona esto explícitamente.

## Encuadre del premortem

Han pasado 6 meses. La estrategia de donar S50Info a la comunidad para atraer gente hacia Sage50BI ha fallado. Miramos hacia atrás para entender por qué.

## Razones de fallo (premortem en bruto)

1. Público equivocado: el usuario de S50Info nunca fue el comprador potencial de Sage50BI.
2. El uso de S50Info señala autosuficiencia técnica — no necesidad de un dashboard.
3. El README es un artefacto pasivo, leído una sola vez, no un canal de conversión recurrente.
4. Donar gratis no genera atención sin distribución/SEO/marketing activo.
5. El nicho de Sage50 es demasiado pequeño para mover la aguja del negocio en 6 meses.
6. Open source permite forks/redistribución que rompen la atribución hacia Sage50BI.
7. El consultor puede ver a Sage50BI como competencia y desaconsejarlo a sus clientes.
8. No hay mecanismo de captura de leads/telemetría — el experimento es invisible.
9. "Gratis" puede dañar la disposición a pagar por Sage50BI (percepción de marca gama baja).

## Análisis profundo por agente

(Ver las 9 tarjetas del informe HTML para el detalle completo de cada historia de fallo, supuesto subyacente y señales de advertencia tempranas — reproducidas íntegramente ahí.)

## Síntesis

**Fallo más probable**: desajuste de público — el técnico que usa S50Info no es el decisor de compra de Sage50BI, y cuantas más funciones gana la CLI, más autosuficiente se vuelve.

**Fallo más peligroso**: el consultor/técnico, si percibe a Sage50BI como competencia de sus propios servicios, puede desaconsejarlo activamente en conversaciones invisibles para el equipo de ventas.

**Supuesto oculto**: que compartir plataforma (Sage50) implica compartir rol de decisión de compra — nunca cuestionado.

**Plan revisado**:
- No confiar en el README como canal de conversión; instrumentar un punto de contacto activo con opt-in.
- Medir desde el día 1 quién usa S50Info (rol, no solo descargas) antes de proyectar conversión.
- Dirigir el mensaje de Sage50BI al cliente final del consultor, no al consultor.
- Separar la narrativa de precio para evitar que "gratis" contamine la percepción de Sage50BI.

**Checklist pre-lanzamiento**:
- Calcular el TAM real alcanzable antes de proyectar conversión.
- Instrumentar telemetría mínima opt-in o CTA con UTM medible.
- Validar con 5-10 usuarios reales si entienden la relación S50Info↔Sage50BI.
- Revisar licencia/distribución para anticipar forks sin atribución.
- Diseñar el mensaje de Sage50BI hacia el cliente final, no hacia el consultor.

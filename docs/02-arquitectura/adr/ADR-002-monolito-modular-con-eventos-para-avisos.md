# ADR-002: Monolito modular con eventos solo hacia avisos y reportes

- **Estado:** Propuesto
- **Fecha:** 2026-09-20
- **Responsables:** Julian Andres Restrepo
- **Asunto relacionado:** AD-02
- **Alternativa seleccionada:** ALT-02A

## 1. Contexto

Un pago, su asiento, su imputación y el efecto sobre la caja deben confirmarse juntos. En cambio, los avisos a administradores, los reportes y el resumen del tablero pueden llegar unos segundos después. Un servicio externo de aviso puede fallar, y ese fallo no debe invalidar el dinero ni pasar inadvertido. El equipo es mínimo y el presupuesto de infraestructura es reducido.

### Trazabilidad

- **Interesados:** INT-01, INT-02
- **Requisitos funcionales:** RF-01, RF-03, RF-04, RF-06
- **Reglas o invariantes:** RN-04, RN-06
- **Escenarios de calidad:** EC-01, EC-04
- **ASR:** ASR-01, ASR-02, ASR-05
- **Restricciones:** RES-02, RES-03
- **Riesgos:** RA-03, RA-04
- **Supuestos:** SUP-02, SUP-03

## 2. Asunto de decisión

> ¿Cómo organizar y comunicar las partes del sistema para que el dinero se confirme de forma atómica y un fallo en los avisos no lo invalide ni pase inadvertido?

## 3. Criterios de decisión

### Obligatorios

- Confirmar el pago, el asiento, la imputación y la caja en una sola transacción.
- Que el fallo de un canal de aviso no revierta ni bloquee la operación de dinero y quede visible como fallido o pendiente.
- Poder ejecutarse en un entorno local para las pruebas.

### Prioritarios

- Fronteras claras con un dueño único por cada regla de negocio.
- Operabilidad por un equipo mínimo.
- Costo de infraestructura contenido.
- Canales de aviso reemplazables sin tocar la lógica de negocio.

### Deseables

- Poder separar una parte después sin reescribir las demás.

## 4. Alternativas consideradas

### ALT-02A — Monolito modular con llamadas directas y eventos por una cola en la base de datos

- **Descripción:** Un solo servicio desplegable dividido en módulos por regla de negocio. Llamadas dentro del proceso para lo atómico. Eventos por una cola en PostgreSQL, encolados en la misma transacción y leídos solo por los módulos de avisos y reportes. Ningún módulo de negocio llama al de avisos.
- **Beneficios:** Conserva la atomicidad del dinero; los productores no conocen a los consumidores; un solo despliegue y una sola base de datos.
- **Costos y sacrificios:** Más fronteras internas que cuidar con un solo desarrollador. Un evento perdido deja sin alerta a un administrador.
- **Riesgos:** RA-03, RA-04.
- **Supuestos:** SUP-03
- **Evidencia necesaria:** EV-03, EV-04, EV-08

### ALT-02B — Servicios independientes por dominio con mensajería asíncrona

- **Descripción:** El dinero, la sincronización y los avisos son servicios separados con un intermediario de mensajes y almacenamientos propios.
- **Beneficios:** Escalado y despliegue independientes; aislamiento de fallos.
- **Costos y sacrificios:** El pago y el asiento cruzarían servicios y exigirían coordinación distribuida. Más piezas y más costo.
- **Riesgos:** Un asiento sin su efecto si la coordinación falla.
- **Supuestos:** Existe capacidad para operar varios servicios y un intermediario.
- **Evidencia necesaria:** Prototipo de la coordinación (no planificado).

### ALT-02C — Monolito con llamadas directas para todo, incluidos los avisos

- **Descripción:** Confirmar un pago envía el aviso en el mismo flujo, sin cola de eventos.
- **Beneficios:** La más simple; el estado del aviso se conoce al instante.
- **Costos y sacrificios:** Cada módulo conoce los canales; el tablero se recalcularía por cada operación.
- **Riesgos:** Un canal caído bloquea o revierte el cobro, o el fallo pasa en silencio.
- **Supuestos:** Los canales responden siempre y rápido.
- **Evidencia necesaria:** EV-03

## 5. Decisión

Se selecciona **ALT-02A** porque es la única que cumple a la vez la atomicidad del dinero y la independencia del aviso respecto del dinero, con la capacidad de un equipo mínimo y el costo previsto. Coincide con la decisión ya tomada en TRACKEA.

La decisión se considera provisional hasta obtener la evidencia indicada en este registro.

## 6. Consecuencias

### Positivas

- El dinero se confirma de forma atómica.
- Los productores de eventos no conocen a los consumidores y el grafo de módulos es acíclico.
- Un fallo de un canal afecta solo a una alerta, no al dinero.

### Negativas o costos aceptados

- Más fronteras internas que mantener.
- La cola de eventos comparte la base de datos con el dominio.
- Todo punto protegido debe pasar por la comprobación de términos aceptados en la capa de API, que debe verificarse con una prueba.

### Riesgos residuales

- RA-03: un evento perdido deja sin alerta a un administrador.
- RA-04: las fronteras entre módulos se erosionan.

## 7. Elementos arquitectónicos afectados

- **Sistemas:** ROYEXA
- **Contenedores:** CON-02, CON-03, CON-04
- **Sistemas externos:** EXT-01, EXT-02, EXT-03
- **Relaciones C4:** «API del servidor → Base de datos», «API del servidor → correo, push y Telegram»
- **Artefactos adicionales:** los catorce módulos del servidor en `backend/src/royexa/` y el contrato OpenAPI en `contracts/openapi.json`

## 8. Evidencia y validación

| Evidencia | Actividad | Resultado esperado | Momento previsto |
|---|---|---|---|
| EV-03 | Sustituir el canal de aviso por un adaptador falso que falla y confirmar un cobro. | El cobro queda confirmado; tras 5 reintentos el envío queda fallido, con alarma y consultable. | Entrega 3 |
| EV-04 | Medir el percentil 95 del lote de sincronización, del cierre de caja y del tablero con unos 1,5 millones de asientos. | 500 ms, 300 ms y 1 s. | Entrega 4 |
| EV-08 | Cambiar el adaptador de un canal y registrar los módulos afectados. | Solo cambia el adaptador. | Entrega 4 |

## 9. Condiciones de revisión

Esta decisión deberá revisarse si ocurre alguna de las siguientes condiciones:

- EV-04 no cumple los tiempos con dos tareas, o el volumen supera el previsto de unos 6.000 clientes.
- La evidencia contradice SUP-03.
- El recorrido vertical revela un costo o acoplamiento no previsto entre módulos.
- Aparece una alternativa viable con consecuencias significativamente mejores.

## 10. Decisiones relacionadas

- ADR-001 (el libro es escrito por un solo módulo).
- ADR-003 (la sincronización despacha hacia los módulos por llamada directa).

## 11. Historial

| Fecha | Estado | Cambio | Motivo |
|---|---|---|---|
| 2026-09-20 | Propuesto | Creación inicial | Sincronización con el estado de TRACKEA |

# ADR-002: Monolito modular con eventos solo hacia avisos y reportes

- **Estado:** Propuesto
- **Fecha:** 2026-09-20
- **Responsables:** Julian Andres Restrepo
- **Asunto relacionado:** AD-02
- **Alternativa seleccionada:** ALT-02A

## 1. Contexto

Un desembolso o un pago, su asiento y el efecto sobre la caja deben confirmarse juntos. En cambio, los avisos al cliente final (código de confirmación y comprobantes) pueden llegar después. El servicio de notificación puede fallar, y ese fallo no debe invalidar el dinero ni pasar inadvertido. El equipo es mínimo y el costo debe ser cero (RES-06).

### Trazabilidad

- **Interesados:** INT-01, INT-02
- **Requisitos funcionales:** RF-01, RF-03, RF-04, RF-06
- **Reglas o invariantes:** RN-04, RN-06
- **Escenarios de calidad:** EC-01, EC-04
- **ASR:** ASR-01, ASR-02, ASR-05
- **Restricciones:** RES-02, RES-03, RES-05, RES-06
- **Riesgos:** RA-03, RA-04, RA-10, RA-11
- **Supuestos:** Ninguno vigente. SUP-02 y SUP-03 quedan diferidos.

## 2. Asunto de decisión

> ¿Cómo organizar y comunicar las partes del sistema para que el dinero se confirme de forma atómica y un fallo en los avisos no lo invalide ni pase inadvertido?

## 3. Criterios de decisión

### Obligatorios

- Confirmar en una sola transacción la operación de dinero, su asiento y su efecto sobre la caja.
- Que el fallo de un canal de aviso no revierta ni bloquee la operación de dinero y quede visible como fallido o pendiente.
- Poder ejecutarse en un entorno local para las pruebas.

### Prioritarios

- Fronteras claras con un dueño único por cada regla de negocio.
- Operabilidad por un equipo mínimo.
- Costo cero (RES-06).
- Canales de aviso reemplazables sin tocar la lógica de negocio.

### Deseables

- Poder separar una parte después sin reescribir las demás.

## 4. Alternativas consideradas

### ALT-02A — Monolito modular con llamadas directas y eventos por una cola en la base de datos

- **Descripción:** Un solo servicio desplegable dividido en módulos por regla de negocio. Llamadas dentro del proceso para lo atómico. Los eventos pasan por una cola definida como puerto: una bandeja de salida en PostgreSQL, escrita en la misma transacción que el dinero, y un adaptador en memoria para las pruebas. Un despachador invocable la vacía, sin trabajador en segundo plano. Solo el módulo de avisos consume esos eventos y ningún módulo de negocio lo llama.
- **Beneficios:** Conserva la atomicidad del dinero; los productores no conocen a los consumidores; un solo despliegue y una sola base de datos.
- **Costos y sacrificios:** Más fronteras internas que cuidar con un solo desarrollador. Un evento perdido deja al cliente final sin código o comprobante.
- **Riesgos:** RA-03, RA-04.
- **Supuestos:** SUP-03 (diferido con el despliegue en la nube)
- **Evidencia necesaria:** EV-03, EV-08, EV-09. EV-04 queda reprogramada.

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

Se selecciona **ALT-02A** porque es la única que cumple a la vez la atomicidad del dinero y la independencia del aviso respecto del dinero, con la capacidad de un equipo mínimo y costo cero (RES-06). TRACKEA queda como referencia.

La decisión se considera provisional hasta obtener la evidencia indicada en este registro. Sigue `Propuesto` hasta EV-08, prevista para la Entrega 4.

**Estado de la implementación (2026-10-31).** El código de la Entrega 3 no cumple todavía dos enunciados de esta decisión, y se declara aquí en lugar de ocultarlo (HV-07):

- La bandeja de salida es un adaptador en memoria también en ejecución, no solo en las pruebas. Solo el libro está en PostgreSQL.
- El criterio de «una sola transacción» se cumple por coordinación. `InMemoryUnitOfWork.commit` comprueba las escrituras obsoletas, confirma la sesión de PostgreSQL y después publica la memoria, todo bajo un mismo candado. Esa secuencia no es una transacción atómica: si el proceso cae entre los dos pasos, el asiento queda sin su efecto en memoria (RA-10).

## 6. Consecuencias

### Positivas

- El dinero se confirma de forma atómica.
- Los productores de eventos no conocen a los consumidores y el grafo de módulos es acíclico.
- Un fallo del notificador afecta solo a un aviso, no al dinero.

### Negativas o costos aceptados

- Más fronteras internas que mantener.
- La cola de eventos comparte la base de datos con el dominio.
- El despachador se invoca de forma explícita: sin invocación, el envío sigue pendiente. Se acepta porque la demostración es local y ese estado es consultable (CA-12).
- La comprobación de términos aceptados queda diferida con el módulo `consent` y no aplica a la línea base.

### Riesgos residuales

- RA-03: un evento perdido deja al cliente final sin código o comprobante.
- RA-04: las fronteras entre módulos se erosionan.
- RA-10: el libro y los datos en memoria no comparten una transacción.
- RA-11: la entrega de avisos es de al menos una vez. Un aviso puede repetirse, y una excepción distinta de `NotifierUnavailable` corta la ejecución del despachador.

## 7. Elementos arquitectónicos afectados

- **Sistemas:** ROYEXA
- **Contenedores:** CON-02 (Entrega 4), CON-03, CON-04
- **Sistemas externos:** EXT-05. EXT-01, EXT-02 y EXT-03 quedan diferidos.
- **Relaciones C4:** «API del servidor → Base de datos», «API del servidor → Notificador simulado»
- **Artefactos adicionales:** los módulos de la línea base (`arquitectura.md`, sección 4.2) y el contrato OpenAPI que expone la API

## 8. Evidencia y validación

| Evidencia | Actividad | Resultado esperado | Momento previsto |
|---|---|---|---|
| EV-03 | Sustituir el notificador simulado por un adaptador que falla al notificar el código de un desembolso y al invocar el despachador. | El desembolso y el dinero se conservan; cada invocación cuenta un intento y tras 5 el envío queda fallido y consultable por el administrador. | Entrega 3 |
| EV-04 | Medir el percentil 95 del lote de sincronización, del cierre de caja y del tablero con unos 1,5 millones de asientos. | 500 ms, 300 ms y 1 s. | Reprogramada, sin destino en el curso |
| EV-08 | Cambiar el adaptador del notificador y registrar los módulos afectados. | Solo cambia el adaptador. | Entrega 4 |
| EV-09 | Ejecutar una prueba estática de dependencias entre módulos. | Cero ciclos y cero llamadas de un módulo de negocio al de avisos. | Entrega 3 |
| EV-11 | Ejecutar sobre la API el flujo de aprobación de un desembolso, con quien lo originó y con un cobrador. | Se rechazan el 100 % de las autoaprobaciones, sin generar código y con la identidad registrada. | Entrega 3 |

EV-11 pertenece a AD-06, que no tiene ADR propio y se decide en `arquitectura.md`, sección 3.4. Se registra aquí porque este ADR incluye RN-06 en su trazabilidad y la regla se ejecuta dentro del monolito modular.

**Resultado (2026-10-31).** Detalle en `docs/03-diseno-vertical/diseno-y-vertical.md`, sección 8.

| Evidencia | Estado | Resultado | Hallazgo |
|---|---|---|---|
| EV-03 | Parcialmente validada | El dinero se conserva, cada invocación cuenta un intento y el estado es consultable. Los 5 fallos hasta `FALLIDO` se observaron sobre el comprobante, no sobre el código que pide la evidencia, y el fallo se simula con una opción del mismo adaptador. | HV-05, HV-06 |
| EV-04 | Reprogramada | Sin destino en el curso. | No aplica |
| EV-08 | Prevista para la Entrega 4 | Sin resultado todavía. | No aplica |
| EV-09 | Validada | Grafo de módulos sin ciclos y ningún módulo de negocio importa `notifications` ni el marco web (PR-08). | HV-09 |
| EV-11 | Validada | Autoaprobaciones del administrador y del cobrador rechazadas con 403, sin aviso de código y con la identidad registrada (PR-02). | HV-09 |

## 9. Condiciones de revisión

Esta decisión deberá revisarse si ocurre alguna de las siguientes condiciones:

- EV-09 detecta ciclos que no pueden eliminarse, o el despachador invocable no basta para demostrar EV-03.
- Se retoma el escenario de dos tareas y volumen; solo entonces EV-04 y SUP-03 vuelven a condicionar esta decisión.
- El recorrido vertical revela un costo o acoplamiento no previsto entre módulos.
- La persistencia en PostgreSQL de desembolsos, cajas y bandeja de salida no logra una sola transacción con el libro (HV-07).
- Aparece una alternativa viable con consecuencias significativamente mejores.

## 10. Decisiones relacionadas

- ADR-001 (el libro es escrito por un solo módulo).
- ADR-004 (la confirmación idempotente ocurre en una transacción dentro del monolito). Sustituye a ADR-003 en esta relación cuando el docente confirme la resolución de DIV-02.

## 11. Historial

| Fecha | Estado | Cambio | Motivo |
|---|---|---|---|
| 2026-09-20 | Propuesto | Creación inicial | Sincronización con el estado de TRACKEA |
| 2026-10-30 | Propuesto | Costo cero; cola detrás de un puerto con bandeja de salida y despachador invocable; avisos al cliente final por EXT-05; consentimiento diferido; EV-04 reprogramada; EV-09 y EV-11 añadidas; EV-03 sobre el desembolso | Realineación con la Entrega 1 (`realineacion-entrega-1.md`) |
| 2026-10-31 | Propuesto | Resultado de EV-03, EV-09 y EV-11; estado real de la bandeja de salida y de la transacción; RA-10 y RA-11; nueva condición de revisión. Sin cambio de estado: EV-08 sigue pendiente | HV-05, HV-06, HV-07, HV-09 |

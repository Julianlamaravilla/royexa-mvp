# Trazabilidad de diseño, implementación y pruebas

## 1. Propósito

Esta matriz extiende la trazabilidad de las Entregas 1 y 2 hasta componentes, contratos, código, pruebas y evidencias. No copia el contenido de los documentos anteriores: usa sus identificadores. Los identificadores `UC`, `CMP`, `CTR`, `PR` y `HV` se definen en [`diseno-y-vertical.md`](diseno-y-vertical.md).

## 2. Matriz del recorrido vertical

`Completo` significa que todos los `CA` y `RN` del caso de uso pasan y su evidencia quedó validada. `Parcial` significa que falta alguno. Los caminos implementados sin prueba están en la sección 6.

| Caso de uso | Origen funcional | Reglas | Calidad / ASR / restricciones | Decisiones | Componentes | Contratos | Código | Pruebas | Evidencia | Estado |
|---|---|---|---|---|---|---|---|---|---|---|
| UC-01 | RF-03, RF-05, CA-10 | RN-05 | RES-04 | AD-02, ADR-002 | CMP-01, CMP-02, CMP-03, CMP-04, CMP-07, CMP-09 | CTR-01, CTR-02, CTR-04, CTR-06 | `backend/src/royexa/sales/application.py` | PR-01, PR-04 | No aplica | Completo |
| UC-02 | RF-03, CA-05, CA-06 | RN-03, RN-06 | EC-02, ASR-02, ASR-03, RES-05 | AD-06, ALT-06B, ADR-002 | CMP-01, CMP-02, CMP-03, CMP-09 | CTR-01, CTR-02, CTR-04, CTR-08 | `backend/src/royexa/sales/application.py` | PR-01, PR-02 | EV-11 | Completo |
| UC-03 | RF-03, RF-04, RF-05, CA-05, CA-06, CA-07, CA-09 | RN-03, RN-04, RN-05 | EC-01, ASR-01, ASR-02 | AD-01, AD-03, ADR-001, ADR-004 | CMP-01, CMP-02, CMP-03, CMP-04, CMP-05, CMP-06, CMP-09, CMP-10 | CTR-01, CTR-02, CTR-04, CTR-05, CTR-06, CTR-07, CTR-08, CTR-11, CTR-12 | `backend/src/royexa/sales/application.py` | PR-01, PR-03, PR-04, PR-05, PR-07 | EV-01, EV-02, EV-12 | Parcial: CA-09 y EC-01 quedan en parte |
| UC-04 | RF-05, CA-10 | RN-05 | RES-04 | ADR-002 | CMP-01, CMP-02, CMP-04, CMP-09 | CTR-01, CTR-02, CTR-04, CTR-06 | `backend/src/royexa/sales/application.py` | PR-04 | No aplica | Completo |
| UC-05 | RF-06, CA-12 | RN-03 | EC-04, ASR-02, ASR-05, RES-03, RES-05 | AD-02, AD-07, ADR-002 | CMP-01, CMP-08, CMP-09, CMP-11 | CTR-01, CTR-03, CTR-08, CTR-09, CTR-10, CTR-11 | `backend/src/royexa/notifications/dispatcher.py` | PR-01, PR-06 | EV-03 | Completo |

## 3. Trazabilidad de componentes

| Componente | Contenedor | Responsabilidad | Origen | Decisión | Contratos | Ruta de código | Pruebas |
|---|---|---|---|---|---|---|---|
| CMP-01 | CON-03 | Entrada HTTP | RF-03, RF-04, RF-06 | AD-06 | CTR-01 | `backend/src/royexa/api.py` | PR-01 a PR-06 |
| CMP-02 | CON-03 | Casos de uso | RF-03, RF-05 | ADR-004 | CTR-02, CTR-04, CTR-11 | `backend/src/royexa/sales/application.py` | PR-01 a PR-05 |
| CMP-03 | CON-03 | Dominio del desembolso | RN-03, RN-06, EC-02 | ADR-004, AD-06 | Ninguno propio | `backend/src/royexa/sales/domain.py` | PR-01, PR-02, PR-03, PR-05 |
| CMP-04 | CON-03 | Préstamos y calendario | RF-05, RN-05 | AD-02 | CTR-06 | `backend/src/royexa/loans/domain.py` | PR-01, PR-04 |
| CMP-05 | CON-03 | Libro, único escritor | RF-04, RN-04, INV-02 | ADR-001 | CTR-05, CTR-07 | `backend/src/royexa/ledger/posting.py` | PR-01, PR-03, PR-05, PR-07 |
| CMP-06 | CON-03 | Caja | RN-03 | ADR-001 | CTR-07 | `backend/src/royexa/cash_box/domain.py` | PR-01, PR-03, PR-05 |
| CMP-07 | CON-03 | Identidad y catálogos | RES-04 | ALT-06B | Ninguno propio | `backend/src/royexa/identity_access/domain.py`, `backend/src/royexa/clients/domain.py` | PR-02, PR-04 |
| CMP-08 | CON-03 | Avisos | RF-06, CA-12, ASR-05 | ADR-002 | CTR-03, CTR-09, CTR-10, CTR-11 | `backend/src/royexa/notifications/dispatcher.py` | PR-06 |
| CMP-09 | CON-03 | Persistencia en memoria | ADR-002 | ADR-002, ADR-004 | CTR-04 a CTR-09, CTR-12 | `backend/src/royexa/adapters/memory.py` | PR-01 a PR-07 |
| CMP-10 | CON-03 | Adaptador PostgreSQL | ASR-01, RN-04 | ADR-001, ADR-004 | CTR-05, CTR-12 | `backend/src/royexa/adapters/postgres_ledger.py` | PR-07 |
| CMP-11 | CON-03 | Adaptador del notificador | RES-03, RES-05 | ADR-002 | CTR-10 | `backend/src/royexa/adapters/simulated_notifier.py` | PR-06 |
| CMP-12 | CON-03 | Composición | RES-02 | ADR-001 | Ninguno propio | `backend/src/royexa/bootstrap.py` | PR-01 a PR-07 |
| CMP-13 | CON-03 | Migrador | ASR-01, RA-01 | ADR-001 | Ninguno propio | `backend/src/royexa/migrate.py` | PR-07 |

## 4. Trazabilidad de criterios y reglas comprobados

| Elemento | Comportamiento esperado | Implementación | Prueba | Resultado | Observaciones |
|---|---|---|---|---|---|
| CA-05 | Asiento, calendario y descuento tras un código vigente, consultable con ambas identidades | `backend/src/royexa/sales/application.py` | PR-01, PR-07 | Pasa | |
| CA-06 | Caducidad sin descuento y con asiento; autoaprobación rechazada con identidad | `backend/src/royexa/sales/domain.py` | PR-02, PR-03, PR-07 | Pasa | Cubre sus dos escenarios |
| CA-07 | Asiento con importe, tipo, identidad y las dos horas, consultable | `backend/src/royexa/ledger/domain.py` | PR-01 | Pasa | Aplicado al asiento del desembolso; CA-07 se redacta sobre un pago |
| CA-08 | El original no se altera y la corrección es visible | `backend/migrations/001_ledger.sql` | PR-07 | Parcial | Solo la prohibición de alterar. Sin asiento compensatorio (HV-03) |
| CA-09 | 20 cuotas de 60 con vencimiento de lunes a sábado | `backend/src/royexa/loans/domain.py` | PR-01 | Parcial | El calendario pasa. No existe alta directa por el administrador ni estado activo del préstamo |
| CA-10 | Bloqueo con saldo pendiente; excepción explícita | `backend/src/royexa/loans/domain.py` | PR-04 | Pasa | La excepción es de un solo uso |
| CA-12 | Envío no confirmado visible como pendiente o fallido | `backend/src/royexa/shared/outbox.py` | PR-06 | Pasa | Cubre código y comprobante, y ambos llegan a `FALLIDO` (HV-05) |
| RN-03 | Sin dinero hasta la confirmación; código ligado y con caducidad | `backend/src/royexa/sales/domain.py` | PR-01, PR-03, PR-06 | Pasa | La caducidad sin intento no cambia el estado (HV-08) |
| RN-04 | Solo inserción; un error se compensa | `backend/migrations/001_ledger.sql` | PR-07 | Parcial | Solo inserción, sí. Compensación, no (HV-03) |
| RN-05 | Bloqueo con saldo; excepción del administrador | `backend/src/royexa/loans/domain.py` | PR-04 | Pasa | Se evalúa al solicitar y al asentar (HV-04) |
| RN-06 | Quien origina no aprueba | `backend/src/royexa/sales/domain.py` | PR-02 | Pasa | Sin excepción para el administrador (DIV-07) |
| EC-01 | Rechazo del 100 % de las alteraciones; corrección visible | `backend/migrations/001_ledger.sql` | PR-07 | Parcial | Rechazo, sí. Corrección, no (HV-03) |
| EC-02 | Autoaprobación rechazada, sin código y registrada | `backend/src/royexa/sales/domain.py` | PR-02 | Pasa | |
| EC-04 | Envíos no confirmados en estado fallido o pendiente | `backend/src/royexa/notifications/dispatcher.py` | PR-06 | Pasa | |
| INV-02 | Un asiento por desembolso y tipo | `backend/migrations/001_ledger.sql` | PR-05, PR-07 | Pasa | En memoria y en PostgreSQL |

## 5. Validación de decisiones provisionales

| Decisión | Evidencia prevista | Evidencia obtenida | Hallazgo | Efecto sobre el ADR | Estado actual |
|---|---|---|---|---|---|
| ADR-001 | EV-01, EV-02 | Ambas `Validada` sobre PostgreSQL 17.11 | HV-01, HV-02, HV-03, HV-07 | Ajustado: redacción de EV-02, límites de la aceptación y RA-10 | Aceptado |
| ADR-002 | EV-03, EV-08, EV-09, EV-11 | EV-03, EV-09 y EV-11 `Validada`; EV-08 prevista para la Entrega 4 | HV-05, HV-06, HV-07, HV-09 | Ajustado: estado real de la bandeja y de la transacción, RA-10 y RA-11 | Propuesto |
| ADR-003 | EV-05, EV-06 | Reprogramadas, sin destino en el curso | No aplica | Sin cambio | Propuesto |
| ADR-004 | EV-12 | `Validada` en memoria y en PostgreSQL | HV-04, HV-07 | Ajustado: relectura del perdedor y RN-05 al asentar | Propuesto, pendiente de confirmación docente |
| AD-06 | EV-11 | `Validada` | HV-09 | Sin ADR propio; rol de aprobación en el agregado | ALT-06B seleccionada |

## 6. Elementos sin cobertura

| Elemento | Motivo de falta de cobertura | Riesgo | Acción prevista |
|---|---|---|---|
| CA-08, EC-01, RN-04: asiento compensatorio | No implementado; el modelo solo tiene dos tipos de asiento y montos positivos | No hay forma de corregir un asiento | Entrega 4, con migración (HV-03) |
| Despachador ante otra excepción o fallo del `commit` | Sin prueba | Cola detenida o aviso repetido (RA-11) | Entrega 4 (HV-06) |
| Caducidad sin intento | No hay barrido de códigos vencidos | Desembolsos abandonados que parecen vigentes | Entrega 4 (HV-08) |
| `RejectDisbursement`, RF-03 | Implementado, sin prueba automatizada | Regresión no detectada | Añadir la prueba |
| `AmountExceedsRouteLimit`, `ClientOutsideRoute`, `EN_ESPERA_AUTORIZACION` | Implementados, sin prueba automatizada | Regresión no detectada en los pasos 1 a 3 del flujo | Añadir la prueba |
| `InvalidConfirmationCode`, `ValidatorNotAllowed`, `ALREADY_EXPIRED` | Implementados, sin prueba automatizada | Regresión no detectada en RN-03 | Añadir la prueba |
| `CashBoxClosed`, RN-02 | Implementado, sin prueba; la Entrega 3 no puede cerrar cajas | Sin riesgo mientras no exista el cierre | Entrega 4 |
| Persistencia de desembolsos, cajas y avisos | Solo el libro está en PostgreSQL | Datos perdidos al reiniciar (RA-10) | Entrega 4 (HV-07) |
| RF-01, RF-02, RF-07, CA-01 a CA-04, CA-11, CA-13, RN-01, RN-02, EC-03, ASR-04 | Fuera del recorrido de desembolso | Ninguno para esta entrega | Entrega 4 (provisional) |
| EV-04, EV-05, EV-06, EV-07 | Dependen de elementos diferidos | Ninguno en la línea base | Reprogramadas, sin destino en el curso |
| EV-08 | Prevista para la Entrega 4 | Reemplazabilidad del notificador sin demostrar | Entrega 4 |
| EV-10 | Trata de pagos | Exactitud del cálculo sin demostrar | Entrega 4 |

## 7. Consistencia

- [x] Todos los identificadores de Entrega 1 existen.
- [x] Todos los `AD`, `ADR`, `CON`, `EV`, `RA` y `SUP` existen en la Entrega 2. `EV-12` y `RA-10`, `RA-11` se añadieron con la realineación y con esta entrega.
- [x] Todos los `CMP`, `CTR`, `UC`, `PR` y `HV` están definidos en la Entrega 3.
- [x] Cada prueba declarada existe en el repositorio.
- [x] Cada ruta de código existe en el commit entregado.
- [x] Los diagramas de secuencia coinciden con los componentes y contratos. Se compararon por lectura con el código; PlantUML los procesó sin errores (`evidencias/resultado-pruebas.txt`, sección 8).
- [x] Los hallazgos que afectan decisiones están reflejados en los ADR.

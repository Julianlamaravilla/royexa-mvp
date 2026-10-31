# Entrega 3 — Diseño interno y primer recorrido vertical

## 0. Identificación

- **Proyecto:** ROYEXA
- **Integrantes:** Julian Andres Restrepo. El docente autorizó el trabajo individual (`DIV-08`).
- **Grupo:** 10
- **Fecha:** 2026-10-31
- **Commit o etiqueta:** rama `entrega-3-linea-base`. Código del recorrido en `f07f7ae` y `8aa1104`; PR-09 a PR-11 y la corrección de HV-10 en `a91aa43`. La etiqueta de entrega aún no se ha creado.
- **Entrega 2 usada como línea base:** [`../02-arquitectura/arquitectura.md`](../02-arquitectura/arquitectura.md), realineada con la Entrega 1 en [`../02-arquitectura/realineacion-entrega-1.md`](../02-arquitectura/realineacion-entrega-1.md). Esa realineación está pendiente de confirmación docente.

---

## 1. Delimitación del recorrido vertical

- **ID:** UC-01 a UC-05, los cinco casos de uso de la tabla siguiente. Juntos forman el flujo principal de la Entrega 1.
- **Nombre:** Desembolso de un préstamo.
- **Actor o sistema iniciador:** INT-01 Cobrador. Intervienen INT-02 Administrador y, como destinatario, INT-03 Cliente final a través de EXT-05.
- **Evento de inicio:** `POST /v1/disbursements`, con cliente, monto, plazo y número de cuotas.
- **Propósito:** que el dinero no se descuente de la caja hasta que el cliente confirme la entrega con un código que le llegó por un canal independiente del cobrador.
- **Requisitos cubiertos:** RF-03, RF-04 y RF-06; RF-05 en lo que toca al calendario y a RN-05.
- **Criterios de aceptación:** CA-05, CA-06, CA-07, CA-09, CA-10 y CA-12. CA-08 se cumple solo en parte (HV-03).
- **Reglas ejercidas:** RN-03, RN-04, RN-05 y RN-06.
- **ASR o restricciones relevantes:** ASR-01, ASR-02, ASR-03 y ASR-05; EC-01, EC-02 y EC-04; RES-02, RES-03, RES-05 y RES-06.
- **Decisiones relacionadas:** AD-01, AD-02, AD-03 y AD-06; ADR-001, ADR-002 y ADR-004.
- **Resultado observable:** desembolso confirmado con calendario de cuotas, asiento en el libro y descuento en caja, consultable con quien lo solicitó y quien lo aprobó; o intento caducado, sin descuento y con asiento del motivo.

| ID | Caso de uso | Clase | Pasos del flujo de la Entrega 1 |
|---|---|---|---|
| UC-01 | Solicitar un desembolso | `RequestDisbursement` | 1 a 3 |
| UC-02 | Aprobar o rechazar una solicitud | `ApproveDisbursement`, `RejectDisbursement` | 4 y 5 |
| UC-03 | Confirmar el desembolso con el código | `ConfirmDisbursement` | 6 |
| UC-04 | Conceder una excepción de renovación | `GrantRenewalException` | RN-05, CA-10 |
| UC-05 | Despachar avisos pendientes | `NotificationDispatcher` | 5 y comprobante, RF-06 |

### 1.1 Alcance incluido

- Solicitud con validación de ruta, límite de ruta, límite del cobrador y RN-05.
- Aprobación y rechazo. La aprobación rechaza la autoaprobación y deja registrado el intento.
- Código de confirmación con caducidad, ligado a la operación y al cliente, guardado como resumen.
- Confirmación idempotente, con asiento, calendario, descuento de caja y comprobante.
- Caducidad del código al intentar confirmarlo, sin descuento y con asiento del motivo.
- Libro en PostgreSQL 17 con un rol que no puede modificarlo.
- Despacho invocable de avisos por un notificador simulado, con reintentos y estado consultable.
- Consultas por API del desembolso, del libro, de la caja y de los avisos.

### 1.2 Exclusiones deliberadas

- **Interfaz web.** Se construye en la Entrega 4 (provisional), según `propuesta.md`, sección L. La Entrega 3 se opera por API.
- **Pagos, no pagos y cierre de caja** (RF-01, RF-02, RF-07). Están fuera del recorrido de desembolso y pasan a la Entrega 4.
- **Asiento compensatorio** (segunda parte de CA-08). No es necesario para el desembolso. El recorrido demuestra que el original no puede alterarse, no cómo se corrige (HV-03).
- **Persistencia en PostgreSQL de desembolsos, préstamos, cajas y bandeja de salida.** Solo el libro necesita una garantía que la memoria no puede dar (HV-07).
- **Autenticación real.** El actor llega en `X-Actor-Id` y se resuelve contra usuarios sembrados, limitación declarada en `ALT-06B`.
- **Proveedor real de notificaciones** (RES-03) y trabajador en segundo plano: el despachador se invoca de forma explícita.
- **Caducidad sin intento.** Ningún proceso recorre los códigos vencidos (HV-08).

### 1.3 Escenario principal

1. El cobrador solicita un desembolso para un cliente de su ruta. El sistema valida la ruta, los límites y que no exista un préstamo anterior sin liquidar (RN-05). La solicitud queda `SOLICITADO`, o `EN_ESPERA_AUTORIZACION` si supera el límite del cobrador.
2. Un administrador distinto de quien la originó la aprueba (RN-06). El agregado guarda el resumen del código y su caducidad, y el caso de uso encola el aviso en la misma unidad de trabajo.
3. El administrador invoca el despachador. El notificador entrega el código al cliente final y el aviso queda `ENVIADO`.
4. El cliente presenta el código y el cobrador lo valida. El agregado confirma; el caso de uso repite RN-05, origina el préstamo con su calendario, asienta el desembolso, descuenta la caja y encola el comprobante.
5. La respuesta devuelve `CONFIRMADO`, con el préstamo, el asiento y las identidades de quien solicitó y quien aprobó. Repetir la confirmación devuelve el mismo resultado sin un segundo efecto (EV-12).

### 1.4 Escenario alternativo seleccionado

- **Condición:** se intenta confirmar con el código correcto después de su caducidad.
- **Respuesta esperada:** `409` con `application/problem+json` y tipo `codigo-caducado`. El desembolso queda `CADUCADO`, la caja no cambia, no se crea préstamo y queda un asiento `DESEMBOLSO_CADUCADO` con motivo `codigo_caducado`.
- **Justificación de su relevancia:** comprueba el núcleo de RN-03 y CA-06: el dinero no se libera y el intento no desaparece. Exige que el reloj sea sustituible (`CTR-11`) y que un rechazo escriba en el libro, así que obliga a separar el resultado de negocio del error HTTP. La secuencia alternativa añade otros dos casos relevantes: la autoaprobación rechazada y dos confirmaciones que compiten.

---

## 2. C4 de Componentes

- **Contenedor descompuesto:** CON-03 — API del servidor. Es el único contenedor que se descompone.
- **Fuente:** [`../02-arquitectura/diagramas/workspace.dsl`](../02-arquitectura/diagramas/workspace.dsl)
- **Vista:** `c4-componentes`
- **Exportación:** [`diagramas/c4-componentes.svg`](diagramas/c4-componentes.svg), generada desde ese DSL con el comando de la sección 7.7.

![C4 de Componentes de la API del servidor](diagramas/c4-componentes.svg)

### 2.1 Catálogo de componentes

| ID | Componente | Responsabilidad | Comportamiento ofrecido | Dependencias | Trazabilidad |
|---|---|---|---|---|---|
| CMP-01 | Entrada HTTP | Traducir HTTP a casos de uso y errores de dominio a detalles de problema. | Rutas `/v1`, resolución del actor, rol de administrador donde corresponde. | CMP-02, CMP-07, CMP-08; CTR-02, CTR-03 | RF-03, RF-04, RF-06, AD-06 |
| CMP-02 | Casos de uso de desembolso | Coordinar cada caso de uso en una unidad de trabajo. No decide reglas. | `execute` de UC-01 a UC-04 y `SalesQueries`. | CMP-03, CMP-04, CMP-05, CMP-07; CTR-04, CTR-11 | RF-03, RF-05, ADR-004 |
| CMP-03 | Dominio del desembolso | Proteger estados, RN-03, RN-06 e idempotencia de la confirmación. | `Disbursement.request`, `approve`, `reject`, `confirm`; `ConfirmationCode`. | CMP-04, CMP-07 | RF-03, RN-03, RN-06, EC-02, ADR-004 |
| CMP-04 | Préstamos | Proteger RN-05 y derivar el calendario. | `LoanTerms`, `Loan.originate`, `build_schedule`, `ensure_renewal_allowed`, `RenewalException`. | CMP-07; CTR-06 | RF-05, RN-05, CA-09, CA-10 |
| CMP-05 | Libro de movimientos | Ser el único escritor del libro y enlazar cada asiento con su efecto en la caja. | `LedgerPosting.post_disbursement`, `post_expired_attempt`; `LedgerEntry`. | CMP-06; CTR-05, CTR-07 | RF-04, RN-04, CA-07, INV-02, ADR-001 |
| CMP-06 | Caja | Guardar el saldo y rechazar movimientos si está cerrada. | `CashBox.deduct`, `ensure_open`. | CTR-07 | RN-02, RN-03 |
| CMP-07 | Identidad y catálogos | Resolver usuarios, roles, rutas y clientes sembrados. | `Directory`, `ClientCatalog`. | Núcleo compartido | RES-04, AD-06, ALT-06B |
| CMP-08 | Avisos | Ser el único lector de la bandeja de salida y contar los intentos. | `NotificationDispatcher.dispatch`, `NoticeQueries.list`. | CTR-08, CTR-09, CTR-10, CTR-11 | RF-06, CA-12, EC-04, ASR-05, ADR-002 |
| CMP-09 | Persistencia en memoria | Dar transacciones por copia a los datos que no están en PostgreSQL. | `InMemoryUnitOfWork` y repositorios en memoria. | CTR-04 a CTR-09; CMP-10 por CTR-12 | ADR-002, ADR-004 |
| CMP-10 | Adaptador PostgreSQL del libro | Insertar y leer asientos con el rol de la aplicación. | `PostgresLedgerRepository`, `PostgresLedgerSession`. | CON-04; CTR-05, CTR-12 | ADR-001, ADR-004, EV-01, EV-02, EV-12 |
| CMP-11 | Adaptador del notificador | Implementar el puerto y reproducir el fallo del canal. | `SimulatedNotifier.send`. | EXT-05; CTR-10 | RES-03, RES-05, ADR-002, EC-04 |
| CMP-12 | Composición | Decidir qué adaptador llena cada puerto y sembrar la demostración. | `build_container`, `Settings.from_env`, `app`, datos de `seed.py`. | Todos los anteriores salvo CMP-13 | RES-02, ADR-001 |
| CMP-13 | Migrador | Aplicar el esquema y los privilegios con el rol propietario. No participa en las peticiones. | `apply_migrations`. | CON-04 | ADR-001, RA-01 |

El núcleo compartido `backend/src/royexa/shared/` (dinero, errores, identificadores, reloj y bandeja de salida) no se modela como componente: no tiene responsabilidad de negocio propia y no depende de ningún módulo.

**Entradas, salidas, reglas y errores**

| ID | Entrada | Salida | Reglas que protege | Errores o resultados alternativos |
|---|---|---|---|---|
| CMP-01 | HTTP con `X-Actor-Id` y JSON | JSON o `application/problem+json` | Rol de administrador en rechazo, libro, despacho y avisos (ALT-06B) | `AdminRoleRequired`, `UnknownActor`; `422 solicitud-invalida` si falta un campo |
| CMP-02 | `User`, identificadores, `LoanTerms`, código, `device_time` | `Disbursement`, `RenewalException`, `DisbursementDetail` | Coordina RN-05 al solicitar y al asentar; conserva el rechazo de RN-06 | `DisbursementNotFound`; repite una vez ante `WriteConflict`; `ConfirmationCodeExpired` tras asentar el intento |
| CMP-03 | Cliente, ruta, actor, condiciones, código en claro | Estado nuevo; `ConfirmationOutcome` | RN-03, RN-06, EC-02, transiciones de ADR-004 | `ClientOutsideRoute`, `AmountExceedsRouteLimit`, `SelfApprovalForbidden`, `ApproverRoleRequired`, `DeciderRoleRequired`, `ValidatorNotAllowed`, `InvalidConfirmationCode`, `InvalidTransition`, `ReasonRequired` |
| CMP-04 | Condiciones, interés, fecha, préstamo previo, excepción | `Loan` con calendario; `RenewalException` | RN-05, CA-09, CA-10 | `PriorLoanNotSettled`, `ExceptionNotAllowed`, `InvalidLoanTerms`, `ReasonRequired` |
| CMP-05 | Desembolso, cobrador, monto, actor, horas del dispositivo y del servidor | `LedgerEntry` | RN-03, RN-04, CA-07, INV-02 | `InvalidLedgerEntry`, `NoOpenCashBox`, `DuplicateLedgerEntry` |
| CMP-06 | `Money` | Saldo actualizado | RN-02 en lo que toca a una caja cerrada | `CashBoxClosed`, `NoOpenCashBox` |
| CMP-07 | Identificador | `User`, `Route`, `Client` | Identidad de quien ejecuta (RES-04) | `UnknownActor`, `RouteNotFound`, `ClientNotFound` |
| CMP-08 | Sin parámetros; filtro por desembolso | `DispatchReport`, `list[OutboxMessage]` | CA-12, EC-04: 5 intentos y estado `FALLIDO` | `NotifierUnavailable` cuenta un intento; otra excepción corta la ejecución (HV-06) |
| CMP-09 | Entidades de dominio | Entidades, con confirmación por `commit` | No publicar sin `commit`; mismo contrato de unicidad que la base de datos | `StaleWrite`, `DuplicateLedgerEntry` |
| CMP-10 | `LedgerEntry` | `list[LedgerEntry]` | RN-04 e INV-02 en la base de datos | `DuplicateLedgerEntry`; `psycopg.OperationalError` si se pierde la conexión |
| CMP-11 | `Notification` | Línea `[EXT-05]` en la salida estándar | Ninguna regla propia | `NotifierUnavailable` con `failing` activo |
| CMP-12 | Variables de entorno | `Container`, `app` | Ninguna regla propia | Falla al arrancar si `ROYEXA_CODE_TTL_MINUTES` no es un entero |
| CMP-13 | Archivos SQL de `backend/migrations/` | Nombres de las migraciones aplicadas | ADR-001: concede solo `SELECT` e `INSERT` | `psycopg.OperationalError` sin base de datos |

### 2.2 Política de dependencias

La dependencia de código va de afuera hacia adentro: entrada y composición conocen los casos de uso, los casos de uso conocen el dominio y los puertos, y el dominio solo conoce a otros módulos de dominio y al núcleo compartido. Los adaptadores importan los puertos y nunca al revés. En las flechas del C4, una relación hacia un adaptador es de ejecución y cruza el contrato indicado; su dependencia de código está invertida.

Grafo real de módulos, sin ciclos:

| Módulo | Depende de |
|---|---|
| `shared` | Ninguno |
| `cash_box`, `clients`, `identity_access`, `notifications` | `shared` |
| `ledger` | `cash_box`, `shared` |
| `loans` | `identity_access`, `shared` |
| `sales` | `cash_box`, `clients`, `identity_access`, `ledger`, `loans`, `shared` |
| `adapters` | `cash_box`, `ledger`, `loans`, `notifications`, `sales`, `shared`, `psycopg` |
| `seed` | `adapters`, `cash_box`, `clients`, `identity_access`, `loans`, `shared` |
| `bootstrap` | `adapters`, `clients`, `identity_access`, `notifications`, `sales`, `seed`, `shared` |
| `api` | `bootstrap`, módulos de negocio, `shared`, FastAPI, Pydantic |
| `main` | `api`, `bootstrap` |
| `migrate` | `psycopg` |

Dependencias que no deben existir, comprobadas por PR-08:

- ciclos entre módulos;
- un módulo de negocio que importe FastAPI, Starlette, Pydantic, Uvicorn, psycopg o httpx;
- un módulo de negocio que importe `adapters`, `api`, `bootstrap`, `main`, `migrate` o `seed`;
- un módulo de negocio que importe `notifications`. Los avisos salen por `CTR-08`, definido en el núcleo compartido.

`notifications` y `shared` no están en la lista de módulos de negocio de PR-08. El grafo anterior muestra que hoy tampoco importan marcos, pero la prueba no lo vigila. `api.py` importa `Container` de `bootstrap.py` para tipar la composición, y `seed.py` importa el almacén en memoria para sembrarlo: ambos pertenecen a la capa externa y ninguno crea un ciclo.

### 2.3 Correspondencia con la arquitectura candidata

CON-03 sigue siendo un monolito modular (AD-02, ALT-02A). Los módulos de `arquitectura.md`, sección 4.2, se convierten en componentes sin cambiar de dueño: `sales` da CMP-02 y CMP-03, `loans` CMP-04, `ledger` CMP-05, `cash_box` CMP-06, `identity_access` y `clients` CMP-07, y `notifications` CMP-08. Los componentes restantes son la entrada, los adaptadores y la composición, que la Entrega 2 no descomponía.

Las decisiones se reconocen en la estructura: CMP-05 es el único escritor del libro y CMP-10 lo hace bajo un rol restringido (ADR-001); CMP-08 es el único lector de la bandeja de salida (ADR-002); CMP-03 y la restricción de CMP-10 sostienen la idempotencia (ADR-004); y RN-06 vive en CMP-03 (ALT-06B).

Hay dos diferencias con lo descrito en la Entrega 2, y ambas se registran como hallazgos:

- **CON-04 contiene menos de lo previsto.** La Entrega 2 preveía en el contenedor el libro, préstamos, cajas y bandeja de salida; hoy solo guarda el libro, y el modelo ya lo describe así (HV-07).
- **El rol de quien aprueba se comprueba en el agregado.** ALT-06B pone el rol en la entrada, pero `POST .../approve` deja pasar a cualquier actor conocido para que un rechazo quede registrado (HV-09).

CMP-11 y EXT-05 coinciden en el mismo proceso: `SimulatedNotifier` implementa el puerto y además hace de canal, porque escribe en la salida estándar. El C4 los mantiene separados porque esa es la frontera que se sustituirá por un proveedor real.

---

## 3. Contratos e interfaces

Los contratos `CTR-04` a `CTR-12` son protocolos de Python: el código que los consume define la forma y los adaptadores la cumplen sin heredar. Solo `CTR-05` y `CTR-11` tienen hoy más de una implementación; `CTR-10` existe porque RES-03 obliga a reemplazar el proveedor. Los demás tienen una sola, y su motivo se indica en cada caso.

### CTR-01 — API HTTP del desembolso

- **Tipo:** Entrada.
- **Responsable:** CMP-01.
- **Consumido por:** INT-01 e INT-02 por HTTP. CON-02 en la Entrega 4 (provisional).
- **Operación o mensaje:** `POST /v1/disbursements`; `POST /v1/disbursements/{id}/approve`, `/reject` y `/confirm`; `GET /v1/disbursements/{id}`; `GET /v1/ledger`; `GET /v1/cash-boxes/{collector_id}`; `POST /v1/clients/{client_id}/renewal-exceptions`; `POST /v1/notifications/dispatch`; `GET /v1/notifications`.
- **Precondiciones:** cabecera `X-Actor-Id` de un usuario sembrado. Rol de administrador en `reject`, `ledger`, `dispatch` y `notifications`.
- **Resultado exitoso:** `DisbursementOut` y demás modelos JSON. Ninguna respuesta incluye el código ni la carga de un aviso (RN-03).
- **Errores o resultados alternativos:** `application/problem+json` según la tabla `_PROBLEMS`: 401 actor desconocido; 403 autoaprobación, rol, ruta o validador; 404 no encontrado; 409 préstamo anterior, código caducado, transición inválida, caja o conflicto de escritura; 422 código, monto, condiciones, motivo o solicitud inválida.
- **Reglas relacionadas:** RN-03, RN-05, RN-06.
- **Motivo de la abstracción:** frontera. Es lo que consumirá la web de la Entrega 4.
- **Ubicación en código:** `backend/src/royexa/api.py`

### CTR-02 — Casos de uso y consultas del desembolso

- **Tipo:** Puerto ofrecido.
- **Responsable:** CMP-02.
- **Consumido por:** CMP-01.
- **Operación o mensaje:** `RequestDisbursement.execute(actor, client_id, terms) -> Disbursement`; `ApproveDisbursement.execute(actor, disbursement_id, reason=None) -> Disbursement`; `RejectDisbursement.execute(actor, disbursement_id, reason) -> Disbursement`; `ConfirmDisbursement.execute(actor, disbursement_id, plain_code, device_time) -> Disbursement`; `GrantRenewalException.execute(actor, client_id, reason) -> RenewalException`; `SalesQueries.detail`, `ledger` y `cash_box`.
- **Precondiciones:** actor ya resuelto. Condiciones ya construidas como `LoanTerms`.
- **Resultado exitoso:** la entidad con su estado nuevo, ya confirmada en la unidad de trabajo.
- **Errores o resultados alternativos:** excepciones de `DomainError`. `ConfirmationCodeExpired` se lanza después de confirmar el intento en el libro. Un `WriteConflict` en `ConfirmDisbursement` se reintenta una vez (ADR-004).
- **Reglas relacionadas:** RN-03, RN-04, RN-05, RN-06.
- **Motivo de la abstracción:** aislamiento. Las reglas se ejercitan igual desde HTTP, y la web de la Entrega 4 las heredaría sin reimplementarlas. Son clases concretas, sin interfaz: no hay ninguna variación que justifique otra.
- **Ubicación en código:** `backend/src/royexa/sales/application.py`

### CTR-03 — Despacho y consulta de avisos

- **Tipo:** Puerto ofrecido.
- **Responsable:** CMP-08.
- **Consumido por:** CMP-01.
- **Operación o mensaje:** `NotificationDispatcher.dispatch() -> DispatchReport`; `NoticeQueries.list(disbursement_id=None) -> list[OutboxMessage]`.
- **Precondiciones:** ninguna. Sin invocación, el aviso sigue pendiente (ADR-002).
- **Resultado exitoso:** `DispatchReport(attempted, sent)`. Cada aviso pendiente recibe un intento por invocación.
- **Errores o resultados alternativos:** `NotifierUnavailable` deja el aviso `PENDIENTE` con `last_error`, y `FALLIDO` en el quinto intento. Cualquier otra excepción aborta la ejecución (HV-06).
- **Reglas relacionadas:** CA-12, EC-04, RF-06.
- **Motivo de la abstracción:** frontera. Separa el dinero de los avisos sin un trabajador en segundo plano.
- **Ubicación en código:** `backend/src/royexa/notifications/dispatcher.py`

### CTR-04 — SalesUnitOfWork y DisbursementRepository

- **Tipo:** Puerto requerido.
- **Responsable:** CMP-02 lo define; CMP-09 lo implementa.
- **Consumido por:** CMP-02.
- **Operación o mensaje:** `with uow:` expone `disbursements`, `loans`, `cash`, `ledger` y `outbox`; `commit()`. `DisbursementRepository.add`, `get` y `save`.
- **Precondiciones:** toda escritura ocurre dentro del bloque.
- **Resultado exitoso:** `commit` publica todo lo escrito. Salir del bloque sin `commit` descarta todo.
- **Errores o resultados alternativos:** `StaleWrite` si un dato leído cambió, `DuplicateLedgerEntry` si se duplica un asiento. Ambos son `WriteConflict`.
- **Reglas relacionadas:** ADR-002, ADR-004, INV-02.
- **Motivo de la abstracción:** aislamiento. Permite probar sin base de datos y fija la frontera transaccional. Hoy tiene una implementación; el puerto es lo que permitirá llevar estos datos a PostgreSQL (HV-07).
- **Ubicación en código:** `backend/src/royexa/sales/ports.py`

### CTR-05 — LedgerRepository

- **Tipo:** Puerto requerido.
- **Responsable:** CMP-05 lo define; CMP-09 y CMP-10 lo implementan.
- **Consumido por:** CMP-05 para escribir, CMP-02 para consultar.
- **Operación o mensaje:** `append(entry)`, `for_disbursement(disbursement_id)`, `all()`.
- **Precondiciones:** `LedgerEntry` válido: monto positivo y motivo si es un intento caducado.
- **Resultado exitoso:** asiento insertado. El puerto no ofrece modificar ni borrar.
- **Errores o resultados alternativos:** `DuplicateLedgerEntry` por desembolso y tipo, en ambas implementaciones.
- **Reglas relacionadas:** RN-04, CA-07, INV-02.
- **Motivo de la abstracción:** sustitución real. La memoria sirve a las pruebas rápidas y PostgreSQL da la garantía que la memoria no puede demostrar (ALT-01A descartada).
- **Ubicación en código:** `backend/src/royexa/ledger/ports.py`

### CTR-06 — LoanRepository

- **Tipo:** Puerto requerido.
- **Responsable:** CMP-04 lo define; CMP-09 lo implementa.
- **Consumido por:** CMP-02.
- **Operación o mensaje:** `add`, `get`, `unsettled_for_client`, `add_exception`, `save_exception`, `get_exception`, `open_exception_for`.
- **Precondiciones:** dentro de una unidad de trabajo.
- **Resultado exitoso:** `Loan` o `RenewalException`, o `None` si no existe.
- **Errores o resultados alternativos:** el puerto no lanza errores de negocio. RN-05 se decide en `ensure_renewal_allowed`.
- **Reglas relacionadas:** RN-05.
- **Motivo de la abstracción:** aislamiento. Hoy tiene una sola implementación y existe como parte de `CTR-04`.
- **Ubicación en código:** `backend/src/royexa/loans/ports.py`

### CTR-07 — CashRepository

- **Tipo:** Puerto requerido.
- **Responsable:** CMP-06 lo define; CMP-09 lo implementa.
- **Consumido por:** CMP-05 y CMP-02.
- **Operación o mensaje:** `open_box_of(collector_id) -> CashBox | None`, `save(box)`.
- **Precondiciones:** dentro de una unidad de trabajo.
- **Resultado exitoso:** la caja abierta del cobrador, o `None`.
- **Errores o resultados alternativos:** `NoOpenCashBox` lo lanza quien llama si recibe `None`.
- **Reglas relacionadas:** RN-02, RN-03.
- **Motivo de la abstracción:** aislamiento. `LedgerPosting` lo recibe sin conocer la unidad de trabajo completa.
- **Ubicación en código:** `backend/src/royexa/cash_box/ports.py`

### CTR-08 — Outbox

- **Tipo:** Puerto requerido.
- **Responsable:** núcleo compartido; CMP-09 lo implementa.
- **Consumido por:** CMP-02 para encolar, CMP-08 para leer y actualizar.
- **Operación o mensaje:** `add`, `get`, `save`, `pending()`, `all(disbursement_id=None)`. Mensaje: `OutboxMessage`.
- **Precondiciones:** el productor escribe dentro de su unidad de trabajo.
- **Resultado exitoso:** el mensaje se confirma junto con el dinero. Su carga se vacía al enviarse o al fallar de forma definitiva.
- **Errores o resultados alternativos:** ninguno propio.
- **Reglas relacionadas:** ADR-002, EV-09, RN-03.
- **Motivo de la abstracción:** frontera. Está en `shared` para que ningún módulo de negocio importe `notifications`. Hoy tiene una sola implementación, en memoria.
- **Ubicación en código:** `backend/src/royexa/shared/outbox.py`

### CTR-09 — NotificationsUnitOfWork

- **Tipo:** Puerto requerido.
- **Responsable:** CMP-08 lo define; CMP-09 lo implementa.
- **Consumido por:** CMP-08.
- **Operación o mensaje:** `with uow:` expone solo `outbox`; `commit()`.
- **Precondiciones:** ninguna.
- **Resultado exitoso:** un `commit` por cada aviso, independiente de los demás.
- **Errores o resultados alternativos:** `WriteConflict` en `commit`.
- **Reglas relacionadas:** ADR-002.
- **Motivo de la abstracción:** aislamiento. El despachador no puede tocar el dinero porque su contrato no lo expone.
- **Ubicación en código:** `backend/src/royexa/notifications/ports.py`

### CTR-10 — Notifier

- **Tipo:** Puerto requerido.
- **Responsable:** CMP-08 lo define; CMP-11 lo implementa.
- **Consumido por:** CMP-08.
- **Operación o mensaje:** `send(notification: Notification) -> None`.
- **Precondiciones:** aviso pendiente, con su carga.
- **Resultado exitoso:** retorno normal: el canal confirmó la entrega.
- **Errores o resultados alternativos:** `NotifierUnavailable`: el canal no confirmó.
- **Reglas relacionadas:** RES-03, RES-05, CA-12, EC-04.
- **Motivo de la abstracción:** sustitución exigida por RES-03. El proveedor real no se conecta en el curso, y el mismo punto permite reproducir su fallo.
- **Ubicación en código:** `backend/src/royexa/notifications/ports.py`

### CTR-11 — Clock

- **Tipo:** Puerto requerido.
- **Responsable:** núcleo compartido; `SystemClock` lo implementa y `FakeClock` lo sustituye en pruebas.
- **Consumido por:** CMP-02 y CMP-08.
- **Operación o mensaje:** `now() -> datetime`.
- **Precondiciones:** ninguna.
- **Resultado exitoso:** hora del servidor en UTC.
- **Errores o resultados alternativos:** ninguno.
- **Reglas relacionadas:** RN-03, CA-06, CA-07.
- **Motivo de la abstracción:** comprobabilidad. Sin él, PR-03 tendría que esperar una hora.
- **Ubicación en código:** `backend/src/royexa/shared/clock.py`

### CTR-12 — LedgerSession

- **Tipo:** Puerto requerido.
- **Responsable:** CMP-09 lo define; CMP-10 lo implementa con `PostgresLedgerSession`.
- **Consumido por:** CMP-09.
- **Operación o mensaje:** atributo `repository`; `commit()`, `rollback()`.
- **Precondiciones:** una sesión por unidad de trabajo.
- **Resultado exitoso:** el asiento se confirma con la unidad de trabajo. La conexión se cierra siempre.
- **Errores o resultados alternativos:** si `commit` falla, el error sube y la memoria no se publica. `rollback` tolera una sesión ya terminada.
- **Reglas relacionadas:** ADR-001, ADR-002, ADR-004.
- **Motivo de la abstracción:** frontera. Une el libro en PostgreSQL con los datos en memoria sin que los casos de uso lo sepan. Coordina dos pasos, pero no forma una transacción atómica (HV-07).
- **Ubicación en código:** `backend/src/royexa/adapters/memory.py`

---

## 4. Diseño dinámico

### 4.1 Escenario principal

- **Fuente:** [`diagramas/secuencia-vertical.puml`](diagramas/secuencia-vertical.puml)
- **Exportación:** [`diagramas/secuencia-vertical.svg`](diagramas/secuencia-vertical.svg), con el comando de la sección 7.7.

![Secuencia del escenario principal](diagramas/secuencia-vertical.svg)

- **Una transacción por paso.** Cada caso de uso abre su propia unidad de trabajo. El dinero se mueve solo en UC-03; aprobar únicamente guarda el resumen del código y encola el aviso (RN-03).
- **El cobrador nunca ve el código.** El aviso sale por `CTR-08` y `CTR-10`, y ninguna respuesta de la API lo incluye. Por eso el código sirve como comprobación independiente de la palabra del cobrador (RES-05).
- **El agregado decide y el caso de uso actúa.** `confirm` devuelve un `ConfirmationOutcome` y no conoce el libro. `ConfirmDisbursement` traduce ese resultado en asiento, préstamo y comprobante.
- **RN-05 se evalúa dos veces.** Entre solicitar y confirmar puede haberse confirmado otro desembolso del mismo cliente (HV-04).
- **El `commit` tiene dos pasos.** Confirma el libro en PostgreSQL y después publica la memoria (HV-07).

### 4.2 Escenario alternativo

- **Fuente:** [`diagramas/secuencia-alternativa.puml`](diagramas/secuencia-alternativa.puml)
- **Exportación:** [`diagramas/secuencia-alternativa.svg`](diagramas/secuencia-alternativa.svg), con el comando de la sección 7.7.

![Secuencia del escenario alternativo](diagramas/secuencia-alternativa.svg)

**Código caducado.** La condición la detecta `Disbursement.confirm`, que protege RN-03 y usa el reloj del servidor, no `device_time`. Comprueba primero que el código sea correcto, de modo que un código errado no revela si el desembolso caducó. El resultado `EXPIRED` no es una excepción dentro de la transacción: el caso de uso asienta el intento, hace `commit` y solo entonces lanza `ConfirmationCodeExpired`, que CMP-01 traduce a 409. Si fuera una excepción en el dominio, la salida del bloque descartaría el asiento que CA-06 exige.

**Autoaprobación.** `approve` registra el intento y lanza `SelfApprovalForbidden`. `ApproveDisbursement` lo captura para guardar y confirmar ese registro, y lo relanza. RN-06 se evalúa antes que cualquier otra guarda, y el código solo se crea si todas pasan (EC-02).

**Confirmaciones que compiten.** La transacción perdedora recibe un `WriteConflict`, de la restricción de unicidad o de `StaleWrite`, y se descarta completa. `execute` repite `_attempt` una vez: esa lectura ya ve `CONFIRMADO`, el agregado responde `ALREADY_CONFIRMED` y no hay escritura. Quien perdió recibe el resultado original (ADR-004, HV-04).

---

## 5. Correspondencia entre diseño y código

| Elemento de diseño | ID | Ruta en el código | Responsabilidad implementada | Observaciones |
|---|---|---|---|---|
| Caso de uso | UC-01 | `backend/src/royexa/sales/application.py` | `RequestDisbursement` | RN-05 antes de crear la solicitud |
| Caso de uso | UC-02 | `backend/src/royexa/sales/application.py` | `ApproveDisbursement`, `RejectDisbursement` | El rechazo de RN-06 se confirma antes de relanzarse |
| Caso de uso | UC-03 | `backend/src/royexa/sales/application.py` | `ConfirmDisbursement` | Repite `_attempt` una vez ante `WriteConflict` |
| Caso de uso | UC-04 | `backend/src/royexa/sales/application.py` | `GrantRenewalException` | Excepción de un solo uso |
| Caso de uso | UC-05 | `backend/src/royexa/notifications/dispatcher.py` | `NotificationDispatcher` | Invocable; sin trabajador en segundo plano |
| Componente | CMP-01 | `backend/src/royexa/api.py` | Rutas, modelos JSON y tabla de problemas | Sin reglas de negocio salvo el rol de ALT-06B |
| Componente | CMP-02 | `backend/src/royexa/sales/application.py` | Coordinación por unidad de trabajo | Sin decisiones de negocio propias |
| Componente | CMP-03 | `backend/src/royexa/sales/domain.py` | `Disbursement`, `ConfirmationCode` | `requested_by` no puede modificarse |
| Componente | CMP-04 | `backend/src/royexa/loans/domain.py` | Préstamo, calendario y RN-05 | Días de cobranza de lunes a sábado |
| Componente | CMP-05 | `backend/src/royexa/ledger/` | `LedgerEntry`, `LedgerPosting` | Único llamador de `append` |
| Componente | CMP-06 | `backend/src/royexa/cash_box/domain.py` | `CashBox` | El cierre de caja es de la Entrega 4 |
| Componente | CMP-07 | `backend/src/royexa/identity_access/domain.py`, `backend/src/royexa/clients/domain.py` | Directorio y catálogo | Datos sembrados |
| Componente | CMP-08 | `backend/src/royexa/notifications/` | Despacho y consulta | Único lector de la bandeja de salida |
| Componente | CMP-12 | `backend/src/royexa/bootstrap.py`, `backend/src/royexa/main.py`, `backend/src/royexa/seed.py` | Inyección de dependencias y siembra | Único lugar que elige adaptadores |
| Componente | CMP-13 | `backend/src/royexa/migrate.py`, `backend/migrations/001_ledger.sql` | Esquema y privilegios | Sin tabla de control de versiones |
| Adaptador | CMP-09 | `backend/src/royexa/adapters/memory.py` | Unidad de trabajo por copia | Se usa también en ejecución |
| Adaptador | CMP-10 | `backend/src/royexa/adapters/postgres_ledger.py` | Libro sobre PostgreSQL | Solo si existe `ROYEXA_LEDGER_URL` |
| Adaptador | CMP-11 | `backend/src/royexa/adapters/simulated_notifier.py` | Notificador simulado | `failing` reproduce EC-04 |
| Contrato | CTR-01 | `backend/src/royexa/api.py` | API HTTP | Ver sección 3 |
| Contrato | CTR-02 | `backend/src/royexa/sales/application.py` | Casos de uso | Clases concretas |
| Contrato | CTR-03 | `backend/src/royexa/notifications/dispatcher.py` | Despacho y consulta | Clases concretas |
| Contrato | CTR-04 | `backend/src/royexa/sales/ports.py` | Unidad de trabajo | Protocolo |
| Contrato | CTR-05 | `backend/src/royexa/ledger/ports.py` | Libro | Protocolo con dos implementaciones |
| Contrato | CTR-06 | `backend/src/royexa/loans/ports.py` | Préstamos | Protocolo |
| Contrato | CTR-07 | `backend/src/royexa/cash_box/ports.py` | Cajas | Protocolo |
| Contrato | CTR-08 | `backend/src/royexa/shared/outbox.py` | Bandeja de salida | Protocolo |
| Contrato | CTR-09 | `backend/src/royexa/notifications/ports.py` | Unidad de trabajo de avisos | Protocolo |
| Contrato | CTR-10 | `backend/src/royexa/notifications/ports.py` | Notificador | Protocolo |
| Contrato | CTR-11 | `backend/src/royexa/shared/clock.py` | Reloj | Protocolo con doble de prueba |
| Contrato | CTR-12 | `backend/src/royexa/adapters/memory.py` | Sesión del libro | Protocolo |

### 5.1 Decisiones de diseño interno

#### Decisión de responsabilidad

- **Problema:** confirmar un desembolso exige decidir un resultado (confirmado, caducado o repetición) y producir efectos en cuatro módulos: préstamos, libro, caja y avisos. Hay que evitar que esa lógica se concentre en un solo lugar.
- **Alternativas consideradas:**
  - Poner toda la lógica en el servicio de aplicación, con un agregado anémico.
  - Dar al agregado acceso a los puertos para que produzca los efectos.
  - Separar: el agregado devuelve un resultado y el caso de uso lo traduce en efectos.
- **Elección:** la tercera. `Disbursement.confirm` devuelve `ConfirmationOutcome`, `ConfirmDisbursement` coordina, y `LedgerPosting` es el único que escribe el libro y aplica el efecto en caja.
- **Justificación:** las reglas quedan en un dueño sin depender de la infraestructura, y `_settle` y `_record_expiry` solo orquestan. Como `EXPIRED` es un valor y no una excepción, el asiento del intento se confirma antes de responder con un error, algo que CA-06 necesita. PR-08 comprueba que el dominio no importa adaptadores.

La misma lógica explica una desviación de `ALT-06B`. `POST .../approve` no exige el rol en la entrada, porque un cobrador rechazado ahí no dejaría rastro: el agregado comprueba el rol y registra el intento (EV-11, HV-09). `reject` sí lo exige en la entrada y también en el agregado.

#### Punto de sustitución

- **Dependencia sustituida:** el canal de notificación al cliente final.
- **Contrato:** CTR-10.
- **Implementación usada en el vertical:** `SimulatedNotifier`.
- **Por qué se requiere:** RES-03 impide conectar el proveedor real durante el curso, y EC-04 exige comprobar qué ocurre cuando falla. `ROYEXA_NOTIFIER_FAILING=1` o el atributo `failing` reproducen el fallo sin tocar el despachador.

Otros dos puntos cumplen una función verificable: **CTR-11** (`SystemClock`, `FakeClock`) hace determinista la caducidad y **CTR-05** (`InMemoryLedgerRepository`, `PostgresLedgerRepository`) permite ejecutar las pruebas sin Docker. Con PostgreSQL se conserva la garantía que la memoria no puede demostrar.

### 5.2 Aplicación razonada de SOLID

| Principio | Evidencia en el diseño o código | Problema que evita | Ruta o elemento |
|---|---|---|---|
| SRP | `LedgerPosting` solo crea asientos y su efecto en caja. `api.py` solo traduce. `ConfirmDisbursement` coordina y `Disbursement` decide. | Que el controlador o el servicio concentren las reglas de dinero. | CMP-01, CMP-02, CMP-03, CMP-05 |
| OCP | No aplica. `LedgerEntryType`, `NoticeKind` y `ConfirmationOutcome` son conjuntos cerrados: un tipo nuevo de asiento obliga a tocar `LedgerPosting` y la migración. La única extensión real prevista, cambiar de notificador, se comprueba con EV-08 en la Entrega 4. | No aplica | No aplica |
| LSP | Las dos implementaciones de `CTR-05` lanzan `DuplicateLedgerEntry` ante el mismo caso. `Flow` ejecuta el mismo recorrido sobre ambas en PR-05 y PR-07. | Que las pruebas en memoria aprueben un comportamiento que PostgreSQL rechazaría. | CTR-05, CMP-09, CMP-10 |
| ISP | `CTR-09` expone solo `outbox`, mientras `CTR-04` expone los cinco repositorios. `CTR-05` no ofrece modificar ni borrar. | Que el despachador pueda tocar el dinero, o que un consumidor del libro pueda alterarlo. | CTR-04, CTR-05, CTR-09 |
| DIP | Los módulos que consumen cada puerto definen su protocolo, los adaptadores lo importan y solo `bootstrap.py` elige la implementación. PR-08 lo comprueba. | Que el dominio dependa de psycopg o del marco web. | `backend/src/royexa/bootstrap.py`, CTR-04 a CTR-11 |

No es obligatorio afirmar que se aplican los cinco principios. Se indica `No aplica` cuando no existe evidencia o necesidad real.

---

## 6. Pruebas automatizadas

### 6.1 Estrategia mínima

El comando por defecto no necesita Docker. Las pruebas marcadas `postgres` se ejecutan aparte. PR-01 y PR-02 cubren el mínimo exigido junto con PR-03: escenario principal, regla de negocio y escenario alternativo.

| ID | Tipo | Escenario | Referencias | Resultado esperado | Ruta |
|---|---|---|---|---|---|
| PR-01 | Componente sobre la API, 3 pruebas | Principal: confirmación con código vigente | UC-01, UC-02, UC-03, UC-05; CA-05, CA-07, CA-09; RN-03, RN-04; RF-03, RF-04 | Asiento, calendario y descuento; aprobar no mueve dinero; el código no sale por la API | `backend/tests/vertical/test_pr01_valid_confirmation.py` |
| PR-02 | Componente sobre la API, 3 pruebas | Regla: autoaprobación rechazada | UC-02; CA-06; RN-06; EC-02; EV-11; RF-03 | 403, sin aviso de código, identidad registrada; otro administrador aún puede aprobar | `backend/tests/vertical/test_pr02_self_approval_rejected.py` |
| PR-03 | Componente sobre la API, 1 prueba | Alternativo: código caducado | UC-03; CA-06; RN-03, RN-04; RF-03 | 409, caja intacta, `CADUCADO`, asiento con motivo | `backend/tests/vertical/test_pr03_expired_code.py` |
| PR-04 | Componente sobre la API, 6 pruebas | Regla: renovación | UC-01, UC-04; CA-10; RN-05; RF-03, RF-05 | 409 con saldo pendiente; excepción de un solo uso; RN-05 se repite al asentar | `backend/tests/vertical/test_pr04_renewal_rule.py` |
| PR-05 | Componente, 3 pruebas | Invariante: confirmación idempotente | UC-03; RN-04; INV-02; EV-12; ADR-004 | Un asiento, un descuento y un comprobante, también con hilos reales | `backend/tests/vertical/test_pr05_idempotent_confirmation.py` |
| PR-06 | Componente sobre la API, 5 pruebas | Fallo del notificador | UC-05; CA-12; RN-03; EC-04; RF-06; EV-03; ADR-002 | El dinero se conserva, el aviso reintenta y termina visible | `backend/tests/vertical/test_pr06_notifier_failure.py` |
| PR-07 | Integración con PostgreSQL 17, 18 pruebas | Privilegios reales y flujo sobre el libro real | RN-04; RN-03; CA-05, CA-06; CA-08 en parte; EV-01, EV-02, EV-12; ADR-001, ADR-002, ADR-004 | El rol no altera el libro y el catálogo lo confirma; sin conexiones abiertas | `backend/tests/postgres/test_pr07_ledger_privileges.py` |
| PR-08 | Estática, 4 pruebas | Dependencias entre módulos | EV-09; ADR-002; AD-02 | Sin ciclos ni imports prohibidos; el detector de ciclos falla si debe | `backend/tests/architecture/test_pr08_dependencies.py` |
| PR-09 | Componente sobre la API, 8 pruebas | Alternativo: rechazo de la solicitud | UC-02; RF-03; RN-03; paso 4 del flujo | `RECHAZADO` con motivo obligatorio y solo por un administrador, sin código ni dinero; confirmar o aprobar después da 409 | `backend/tests/vertical/test_pr09_rejection.py` |
| PR-10 | Componente sobre la API, 13 pruebas | Límites de la solicitud | UC-01, UC-02; RF-03; RN-06; CA-05, CA-06; pasos 1 a 4 del flujo; HV-10 | 422 sobre el límite de ruta y 403 fuera de la ruta; sobre el límite del cobrador espera, y aprobar exige un motivo que no esté en blanco | `backend/tests/vertical/test_pr10_request_limits.py` |
| PR-11 | Componente sobre la API, 6 pruebas | Guardas del código de confirmación | UC-03; CA-05, CA-06; RN-03; INV-02 | Código errado o de otra operación: 422 sin efectos, y el válido sigue sirviendo. Otro validador: 403. Repetir tras caducar: el mismo 409, sin segundo asiento | `backend/tests/vertical/test_pr11_code_guards.py` |

PR-09 a PR-11 cubren comportamiento que ya existía, y sus pruebas pasaron en la primera ejecución, salvo el caso del motivo en blanco de PR-10, que falló y reveló un defecto (HV-10). Para comprobar que esas pruebas pueden fallar, se invirtió de forma temporal una aserción en PR-09 y otra en PR-11: ambas fallaron, y el cambio no se conservó.

### 6.2 Dobles o implementaciones controladas

| Dependencia | Tipo usado | Implementación | Motivo |
|---|---|---|---|
| Reloj (CTR-11) | Fake | `FakeClock` en `backend/tests/support.py` | Hacer determinista la caducidad y las marcas de tiempo |
| Notificador (CTR-10) | Implementación simulada, con fallo activable | `SimulatedNotifier` | Leer el código entregado y reproducir EC-04 |
| Notificador que nunca responde (CTR-10) | Stub local de la prueba | `UnreachableChannel` en `backend/tests/vertical/test_pr06_notifier_failure.py` | Sustituir el adaptador, como pide EV-03 (HV-05) |
| Persistencia (CTR-04, CTR-06 a CTR-09) | Implementación en memoria | `InMemoryUnitOfWork` | Es la implementación de ejecución de la Entrega 3 |
| Libro (CTR-05) en PR-01 a PR-06 y PR-09 a PR-11 | Implementación en memoria | `InMemoryLedgerRepository` | Ejecutar sin Docker. No demuestra la inmutabilidad |
| Libro (CTR-05) en PR-07 | No aplica: PostgreSQL 17 real | `PostgresLedgerRepository` | EV-01 y EV-02 no pueden obtenerse con un doble (ALT-01A descartada) |
| Unidad de trabajo que pierde la carrera | Stub local de la prueba | `LosesTheRace` en `backend/tests/vertical/test_pr05_idempotent_confirmation.py` | Forzar de forma determinista la carrera del `commit` |

### 6.3 Resultado de ejecución

- **Fecha de ejecución:** 2026-10-31
- **Comando:** `uv run pytest -m ""`, desde `backend/`, con PostgreSQL 17.11 en ejecución.
- **Pruebas ejecutadas:** 70
- **Pruebas exitosas:** 70
- **Pruebas fallidas:** 0
- **Evidencia:** [`evidencias/resultado-pruebas.txt`](evidencias/resultado-pruebas.txt)

Por separado, `uv run pytest` da 52 aprobadas y 18 sin seleccionar; `uv run pytest tests/vertical` da 48 aprobadas; y `uv run pytest -m postgres` da 18 aprobadas y 52 sin seleccionar. Cada ejecución muestra un aviso de obsolescencia de Starlette sobre `httpx`, ajeno al código del proyecto. El comando por defecto se repitió 5 veces seguidas con el mismo resultado. Estos comandos se repitieron desde un clon limpio y con una base de datos nueva, con el mismo resultado.

---

## 7. Ejecución reproducible

Los comandos completos para un clon limpio están también en [`../../backend/README.md`](../../backend/README.md).

### 7.1 Requisitos del entorno

- Python 3.14. `backend/.python-version` lo fija y `uv` lo descarga si falta. Se probó con 3.14.6.
- `uv` 0.11 para dependencias y ejecución. Se probó con 0.11.7.
- Docker con Compose, solo para PostgreSQL 17 y para regenerar los diagramas (sección 7.7). Se probó con la imagen `postgres:17`, versión 17.11.
- Sin archivos de configuración. Las variables son opcionales:

| Variable | Valor por defecto | Efecto |
|---|---|---|
| `ROYEXA_LEDGER_URL` | Sin definir: libro en memoria | Conexión del rol de la aplicación al libro en PostgreSQL |
| `ROYEXA_CODE_TTL_MINUTES` | `60` | Vigencia del código de confirmación |
| `ROYEXA_NOTIFIER_FAILING` | Sin definir | Con `1`, el notificador simulado falla |
| `ROYEXA_MIGRATOR_URL` | `postgresql://royexa_migrator:royexa_migrator@localhost:55432/royexa` | Conexión del rol propietario |

Las credenciales de `docker-compose.yml` y de la migración son valores de demostración local.

### 7.2 Preparar dependencias

```bash
cd backend
uv sync
```

Para el libro en PostgreSQL, desde la raíz del repositorio y después desde `backend/`:

```bash
docker compose up -d --wait postgres
cd backend
uv run python -m royexa.migrate
```

### 7.3 Ejecutar el recorrido

Desde `backend/`, con el libro en PostgreSQL:

```bash
ROYEXA_LEDGER_URL=postgresql://royexa_app:royexa_app@localhost:55432/royexa \
  uv run uvicorn royexa.main:app --port 8000
```

Sin PostgreSQL, el libro queda en memoria:

```bash
uv run uvicorn royexa.main:app --port 8000
```

La documentación OpenAPI queda en `http://localhost:8000/docs`.

### 7.4 Ejecutar todas las pruebas

Desde `backend/`, sin Docker. Es el comando por defecto y deja fuera las pruebas `postgres`:

```bash
uv run pytest
```

Con PostgreSQL en ejecución, solo PR-07:

```bash
uv run pytest -m postgres
```

Con PostgreSQL en ejecución, las 70 pruebas:

```bash
uv run pytest -m ""
```

### 7.5 Ejecutar las pruebas del vertical

```bash
uv run pytest tests/vertical
```

### 7.6 Datos de ejemplo

Usuarios sembrados: `cobrador-1`, `cobrador-2`, `admin-1` y `admin-2`. Clientes: `cliente-1` sin préstamos, `cliente-2` con saldo pendiente, `cliente-3` con préstamo liquidado y `cliente-4` de otra ruta. La caja de `cobrador-1` abre con 100 000 000 centavos.

Con el servidor en ejecución, el recorrido se reproduce así:

```bash
API=http://localhost:8000/v1
JSON='Content-Type: application/json'

curl -X POST $API/disbursements -H "$JSON" -H 'X-Actor-Id: cobrador-1' \
  -d '{"client_id":"cliente-1","amount_cents":100000,"term_days":20,"installment_count":20}'
# Copie el campo id de la respuesta en la variable ID.

curl -X POST $API/disbursements/$ID/approve -H "$JSON" -H 'X-Actor-Id: admin-1' -d '{}'
curl -X POST $API/notifications/dispatch -H 'X-Actor-Id: admin-1'
# El servidor imprime una línea [EXT-05] con el código. Cópielo en la variable CODE.

curl -X POST $API/disbursements/$ID/confirm -H "$JSON" -H 'X-Actor-Id: cobrador-1' \
  -d "{\"code\":\"$CODE\",\"device_time\":\"2026-10-31T09:00:00-05:00\"}"
curl $API/cash-boxes/cobrador-1 -H 'X-Actor-Id: admin-1'
```

Resultado observado el 2026-10-31 con el libro en PostgreSQL:

| Paso | Resultado |
|---|---|
| Solicitud | `201`, `status=SOLICITADO`, `interest_cents=20000` |
| Aprobación por `cobrador-1` | `403`, tipo `autoaprobacion-prohibida`, intento registrado |
| Aprobación por `admin-1` | `200`, `status=APROBADO`, sin el código en la respuesta |
| Despacho | `200`, `{"attempted":1,"sent":1}` |
| Confirmación | `200`, `status=CONFIRMADO`, 20 cuotas de 6000, primer vencimiento 2026-11-02, asiento `DESEMBOLSO` por 100000 |
| Repetición de la confirmación | `200`, sin asiento ni descuento nuevos |
| Caja | `balance_cents=99900000` |

El registro completo está en [`evidencias/resultado-pruebas.txt`](evidencias/resultado-pruebas.txt).

### 7.7 Regenerar los diagramas

Desde la raíz del repositorio, con Docker en ejecución:

```bash
docs/03-diseno-vertical/diagramas/exportar-diagramas.sh
```

El script usa las imágenes fijadas `structurizr/cli:2024.03.03` y `plantuml/plantuml:1.2024.8`. Valida `workspace.dsl`, exporta sus vistas y genera los cinco SVG: `c4-contexto.svg` y `c4-contenedores.svg` en `docs/02-arquitectura/diagramas/`, y `c4-componentes.svg`, `secuencia-vertical.svg` y `secuencia-alternativa.svg` en `docs/03-diseno-vertical/diagramas/`. Si un paso falla, se detiene.

---

## 8. Validación de decisiones y evidencia

| Evidencia | Decisión o riesgo | Actividad realizada | Resultado | Estado | Hallazgo |
|---|---|---|---|---|---|
| EV-01 | ADR-001, RA-01, SUP-01 | PR-07 intenta `UPDATE`, `DELETE` y `TRUNCATE` con `royexa_app` sobre un asiento confirmado y relee la fila. | Los 3 intentos fallan con `InsufficientPrivilege` y la fila queda intacta. | Validada | HV-01 |
| EV-02 | ADR-001, RA-01, SUP-01 | PR-07 consulta el catálogo tras migrar, por tabla, por columna y por `PUBLIC`, revisa los atributos del rol y migra dos veces. | Solo `SELECT` e `INSERT` sobre `ledger_entry`. El rol no es propietario ni superusuario ni miembro de otro rol. | Validada | HV-01, HV-02 |
| EV-03 | ADR-002, RA-03 | PR-06 sustituye el notificador por un adaptador que falla al notificar el código, e invoca el despachador. También activa el fallo del simulado sobre el comprobante. | El desembolso sigue `APROBADO`, la caja y el libro no cambian, cada invocación cuenta un intento y tras 5 el aviso queda `FALLIDO` y consultable, con el código y con el comprobante. | Validada | HV-05, HV-06 |
| EV-04 | ADR-002, SUP-03 | No se realizó. | Medía dos tareas en la nube, fuera de la línea base. | Reprogramada, sin destino en el curso | No aplica |
| EV-05 | ADR-003, SUP-04 | No se realizó. | Medía lotes de sincronización. EV-12 la sustituye en el recorrido. | Reprogramada, sin destino en el curso | No aplica |
| EV-06 | ADR-003, SUP-05 | No se realizó. | Exigía un teléfono real, fuera de la línea base. | Reprogramada, sin destino en el curso | No aplica |
| EV-07 | AD-04 | No se realizó. | Sigue a DIV-03: se trabaja con una sola empresa. | Reprogramada, sin destino en el curso | No aplica |
| EV-09 | ADR-002, RA-04 | PR-08 analiza los imports de `backend/src/royexa`. | Cero ciclos y cero imports prohibidos. Una prueba comprueba que el detector sí detecta ciclos. | Validada | HV-09 |
| EV-10 | AD-05 | No se realizó. | Trata del cálculo de pagos, fuera del recorrido de desembolso. | Reprogramada a la Entrega 4 | No aplica |
| EV-11 | AD-06, ADR-002 | PR-02 ejecuta sobre la API la aprobación con el administrador y con el cobrador que originaron la solicitud. | El 100 % de las autoaprobaciones se rechaza con 403, sin aviso de código y con la identidad registrada. | Validada | HV-09 |
| EV-12 | ADR-004 | PR-05 repite la confirmación y lanza dos concurrentes; PR-07 hace lo mismo sobre la restricción real. | Un solo asiento, un solo descuento y un solo comprobante; las respuestas devuelven el resultado original. | Validada | HV-04 |

EV-08 no está prevista para esta entrega: sigue en la Entrega 4.

### HV-01 — El libro resiste la alteración aunque el código falle

- **Evidencia de origen:** EV-01, EV-02, PR-07.
- **Qué se observó:** `royexa_app` no puede modificar, borrar ni vaciar `ledger_entry`, y el catálogo lo confirma sobre PostgreSQL 17.11.
- **Interpretación:** la garantía no depende del código de la aplicación, que era la condición de ALT-01B. Confirma también SUP-01.
- **Decisión afectada:** AD-01, ADR-001.
- **Acción tomada:** confirmar. ADR-001 pasa a `Aceptado` y SUP-01 queda confirmado.
- **Archivos actualizados:** `docs/02-arquitectura/adr/ADR-001-libro-de-movimientos-de-solo-insercion.md`, `docs/02-arquitectura/arquitectura.md`

### HV-02 — EV-02 citaba un registro de cambios que no existe

- **Evidencia de origen:** EV-02.
- **Qué se observó:** EV-02 pedía comprobar «el libro y el registro de cambios», pero el esquema solo tiene `ledger_entry`. Además decía «el comando local de pruebas», y el comando por defecto no la ejecuta.
- **Interpretación:** la evidencia no podía cumplirse tal como estaba escrita. Dar por validada esa redacción habría afirmado algo que no se comprobó.
- **Decisión afectada:** ADR-001, AD-01.
- **Acción tomada:** ajustar la redacción en `arquitectura.md`, sección 3.1 y sección 6.4, y en ADR-001, con historial. PR-07 comprueba que el rol no tiene concesiones sobre ninguna otra tabla, así que un registro de cambios futuro no escaparía a la prueba.
- **Archivos actualizados:** `docs/02-arquitectura/arquitectura.md`, `docs/02-arquitectura/adr/ADR-001-libro-de-movimientos-de-solo-insercion.md`

### HV-03 — La aceptación de ADR-001 no cubre el asiento compensatorio

- **Evidencia de origen:** PR-07, CA-08, EC-01.
- **Qué se observó:** PR-07 demuestra que el original no puede alterarse. No existe asiento compensatorio: `LedgerEntryType` tiene dos valores, y `amount_cents` debe ser positivo.
- **Interpretación:** CA-08, EC-01 y RN-04 quedan cubiertos solo en parte, y la corrección exigirá una migración.
- **Decisión afectada:** ADR-001.
- **Acción tomada:** diferir a la Entrega 4 y añadir una condición de revisión a ADR-001.
- **Archivos actualizados:** `docs/02-arquitectura/adr/ADR-001-libro-de-movimientos-de-solo-insercion.md`

### HV-04 — Quien pierde la carrera debe recibir el resultado original

- **Evidencia de origen:** EV-12, PR-04, PR-05, PR-07.
- **Qué se observó:** con dos confirmaciones simultáneas, la restricción de unicidad impide el segundo asiento y la transacción perdedora se revierte. Eso no basta para EV-12, que exige que todas las respuestas devuelvan el resultado original. Además, dos solicitudes abiertas del mismo cliente pueden estar aprobadas a la vez, así que evaluar RN-05 solo al solicitar no protege el momento en que el dinero se mueve.
- **Interpretación:** ADR-004 describía el rechazo del segundo asiento, pero no qué recibe quien pierde, y no mencionaba RN-05.
- **Decisión afectada:** ADR-004, AD-03.
- **Acción tomada:** ajustar. `ConfirmDisbursement.execute` repite `_attempt` una vez ante `WriteConflict`, y `_settle` vuelve a evaluar RN-05. ADR-004 lo registra en su decisión y su historial.
- **Archivos actualizados:** `docs/02-arquitectura/adr/ADR-004-operacion-en-linea-con-confirmacion-idempotente.md`

### HV-05 — EV-03 no comprobó todo lo que pide

- **Evidencia de origen:** EV-03, PR-06.
- **Qué se observó:** EV-03 pide que falle la notificación del código y que tras 5 intentos el envío quede fallido. PR-06 llevaba a `FALLIDO` el comprobante, y sobre el código solo observaba un fallo. Tampoco sustituía el adaptador: activaba `failing` en el mismo `SimulatedNotifier`.
- **Interpretación:** `record_failure` no distingue el tipo de aviso, así que el resultado debía ser el mismo, pero eso era una inferencia y no algo observado. La prueba añadida lo observó: pasó en su primera ejecución, sin cambios en el código de producción. El dinero se conserva y el estado es visible, que es lo esencial de CA-12 y EC-04. Esa prueba no sustituye a EV-08, que pide registrar los módulos afectados por el cambio de adaptador.
- **Decisión afectada:** ADR-002.
- **Acción tomada:** añadir a PR-06 la prueba `test_pr06_code_notice_fails_after_five_dispatches_through_a_replaced_adapter`, que construye el sistema con otro adaptador del puerto `Notifier` y lleva el aviso del código a `FALLIDO` en 5 despachos. El vacío queda cerrado y EV-03 pasa a `Validada`.
- **Archivos actualizados:** `backend/tests/vertical/test_pr06_notifier_failure.py`, `docs/02-arquitectura/adr/ADR-002-monolito-modular-con-eventos-para-avisos.md`, `docs/02-arquitectura/arquitectura.md`, `docs/02-arquitectura/realineacion-entrega-1.md`, `docs/02-arquitectura/trazabilidad-arquitectonica.md`

### HV-06 — La entrega de avisos es de al menos una vez

- **Evidencia de origen:** revisión de `backend/src/royexa/notifications/dispatcher.py`, líneas 47 a 52.
- **Qué se observó:** solo `NotifierUnavailable` cuenta como intento fallido. Cualquier otra excepción aborta la ejecución del despachador. Si el `commit` falla después de enviar, el aviso sigue pendiente y se reenvía. Ninguna prueba ejercita estos dos caminos.
- **Interpretación:** el cliente puede recibir un aviso repetido y un adaptador real podría detener la cola. No afecta al dinero, pero sí a RA-03.
- **Decisión afectada:** ADR-002.
- **Acción tomada:** registrar RA-11 y ajustar ADR-002. La corrección de código queda para la Entrega 4.
- **Archivos actualizados:** `docs/02-arquitectura/adr/ADR-002-monolito-modular-con-eventos-para-avisos.md`, `docs/02-arquitectura/arquitectura.md`

### HV-07 — Solo el libro vive en PostgreSQL

- **Evidencia de origen:** PR-07, ejecución del recorrido del 2026-10-31 y revisión de `workspace.dsl` al exportar los diagramas.
- **Qué se observó:** desembolsos, préstamos, cajas y bandeja de salida están en memoria también en ejecución. Tras reiniciar el servidor, el libro conservó el asiento de −100 000 centavos, la caja volvió a 100 000 000 y el desembolso respondió 404. PR-07 comprueba que un `StaleWrite` o una caída de la conexión no dejan cambios a medias, pero `commit` confirma PostgreSQL y publica la memoria en dos pasos.
- **Interpretación:** la Entrega 3 demuestra la inmutabilidad del libro, no la persistencia del sistema. ADR-002 pedía una sola transacción y una bandeja en PostgreSQL. Tampoco se cumple aún que el saldo sea la suma de los asientos: `CashBox.balance` es un campo.
- **Decisión afectada:** ADR-001, ADR-002, ADR-004.
- **Acción tomada:** registrar RA-10, declarar el estado real en los tres ADR y en `arquitectura.md`, secciones 4.2 y 5.3, y añadir una condición de revisión a ADR-002. Antes de exportar los diagramas, la descripción de CON-04 y la relación entre la API y la base de datos en `workspace.dsl` se alinearon con este hallazgo, para que los SVG no mostraran como vigente lo que el código no hace.
- **Archivos actualizados:** `docs/02-arquitectura/adr/ADR-001-libro-de-movimientos-de-solo-insercion.md`, `docs/02-arquitectura/adr/ADR-002-monolito-modular-con-eventos-para-avisos.md`, `docs/02-arquitectura/adr/ADR-004-operacion-en-linea-con-confirmacion-idempotente.md`, `docs/02-arquitectura/arquitectura.md`, `docs/02-arquitectura/diagramas/workspace.dsl`

### HV-08 — Un código vencido sin intento no caduca por sí solo

- **Evidencia de origen:** PR-03 y revisión de `Disbursement.confirm`.
- **Qué se observó:** la caducidad se detecta al intentar confirmar. Si nadie lo intenta, el desembolso sigue `APROBADO` y no hay asiento. CA-06 se cumple porque habla de un intento, pero el flujo de la Entrega 1 dice que la operación caduca si el cliente no confirma a tiempo.
- **Interpretación:** el dinero sigue protegido, porque nada se descuenta. El vacío es de visibilidad: el administrador no distingue un desembolso pendiente de uno abandonado.
- **Decisión afectada:** alcance del recorrido.
- **Acción tomada:** diferir. Se declara en la sección 10 y en `trazabilidad-implementacion.md`, sección 6.
- **Archivos actualizados:** `docs/03-diseno-vertical/diseno-y-vertical.md`, `docs/03-diseno-vertical/trazabilidad-implementacion.md`

### HV-09 — Monolito modular y regla en el dominio confirmados, con un ajuste

- **Evidencia de origen:** EV-09, EV-11, PR-02, PR-08.
- **Qué se observó:** el grafo de módulos no tiene ciclos y el negocio no conoce los avisos. La autoaprobación se rechaza siempre. `POST .../approve` no exige el rol en la entrada, a diferencia de lo que dice ALT-06B.
- **Interpretación:** AD-02 y AD-06 se sostienen. El ajuste es necesario: si la entrada rechazara a un cobrador, el intento no llegaría al agregado y no quedaría registrado.
- **Decisión afectada:** AD-02, AD-06, ADR-002.
- **Acción tomada:** confirmar ambas decisiones. La desviación se explica en la sección 5.1.
- **Archivos actualizados:** `docs/03-diseno-vertical/diseno-y-vertical.md`

### HV-10 — Un motivo en blanco autorizaba un monto sobre el límite del cobrador

- **Evidencia de origen:** PR-10 y revisión de `Disbursement.approve`.
- **Qué se observó:** `approve` comprobaba el motivo con `not reason`, mientras que `reject` y `RenewalException.grant` usan `strip()`. Una solicitud `EN_ESPERA_AUTORIZACION` de 50 000 001 centavos, aprobada con el motivo `"   "`, quedó `APROBADO`, encoló el código y, al confirmarse, descontó la caja. La prueba de PR-10 falló con `assert 200 == 422`.
- **Interpretación:** es un defecto de la implementación, no de una decisión. El paso 4 del flujo pide indicar el motivo, y un motivo en blanco dejaba sin justificación la autorización de un monto que supera el límite del cobrador. Las demás pruebas de PR-09 a PR-11 pasaron en su primera ejecución y no aportan evidencia de este tipo.
- **Decisión afectada:** ninguna.
- **Acción tomada:** corregir la comprobación en `Disbursement.approve`, que ahora rechaza un motivo en blanco con `422 motivo-requerido`, y añadir ese caso a PR-10, que también comprueba que no se encola el código ni se mueve dinero. La prueba pasó después de la corrección. El motivo sigue sin exigirse dentro del límite: esa lectura queda abierta en la sección 10.
- **Archivos actualizados:** `backend/src/royexa/sales/domain.py`, `backend/tests/vertical/test_pr10_request_limits.py`, `docs/03-diseno-vertical/diseno-y-vertical.md`, `docs/03-diseno-vertical/trazabilidad-implementacion.md`

---

## 9. Cambios respecto de la Entrega 2

| Fecha | Cambio | Motivo | Artefactos afectados | Decisión o hallazgo relacionado |
|---|---|---|---|---|
| 2026-10-30 | Realineación de la arquitectura con la Entrega 1 sobre una demostración local de costo cero. Pendiente de confirmación docente. | Pérdida de financiamiento del producto: AWS, aplicación móvil, sincronización y multi-tenant no podían construirse. | `docs/02-arquitectura/realineacion-entrega-1.md`, `docs/02-arquitectura/arquitectura.md`, `docs/02-arquitectura/trazabilidad-arquitectonica.md`, `docs/02-arquitectura/adr/`, `docs/02-arquitectura/diagramas/workspace.dsl` | RES-06, DIV-01 a DIV-08 |
| 2026-10-30 | ADR-004 selecciona ALT-03A con confirmación idempotente. ADR-003 no cambia de estado. | La Entrega 1 excluye la operación sin conexión. | `docs/02-arquitectura/adr/ADR-004-operacion-en-linea-con-confirmacion-idempotente.md` | ADR-004, EV-12 |
| 2026-10-30 | Comparación de AD-06, que selecciona ALT-06B. | La Entrega 2 la había diferido. | `docs/02-arquitectura/arquitectura.md` | AD-06, EV-11 |
| 2026-10-31 | Vista `c4-componentes` añadida al modelo de la Entrega 2. | Requisito de esta entrega. | `docs/02-arquitectura/diagramas/workspace.dsl` | CMP-01 a CMP-13 |
| 2026-10-31 | ADR-001 pasa a `Aceptado`. | EV-01 y EV-02 quedaron `Validada`. | `docs/02-arquitectura/adr/ADR-001-libro-de-movimientos-de-solo-insercion.md` | HV-01, HV-03 |
| 2026-10-31 | Redacción de EV-02 corregida. | Citaba una tabla inexistente y un comando que no la ejecuta. | `docs/02-arquitectura/arquitectura.md`, `docs/02-arquitectura/adr/ADR-001-libro-de-movimientos-de-solo-insercion.md` | HV-02 |
| 2026-10-31 | ADR-004 añade la relectura del perdedor y RN-05 al asentar. | La decisión no decía qué recibe quien pierde la carrera. | `docs/02-arquitectura/adr/ADR-004-operacion-en-linea-con-confirmacion-idempotente.md` | HV-04 |
| 2026-10-31 | ADR-002 declara el estado real de la bandeja y de la transacción. Se añaden RA-10 y RA-11. | La implementación no cumple aún dos enunciados de la decisión. | `docs/02-arquitectura/adr/ADR-002-monolito-modular-con-eventos-para-avisos.md`, `docs/02-arquitectura/arquitectura.md` | HV-05, HV-06, HV-07 |
| 2026-10-31 | Resultado de las evidencias registrado en el rastro de la realineación. | Cerrar el estado de la matriz de identificadores. | `docs/02-arquitectura/realineacion-entrega-1.md` | HV-01 a HV-09 |
| 2026-10-31 | EV-03 pasa a `Validada` con una prueba sobre el aviso del código. La cobertura de ASR muestra el resultado de las evidencias. | Cerrar el vacío de HV-05 y el estado que seguía pendiente en la matriz. | `backend/tests/vertical/test_pr06_notifier_failure.py`, `docs/02-arquitectura/adr/ADR-002-monolito-modular-con-eventos-para-avisos.md`, `docs/02-arquitectura/arquitectura.md`, `docs/02-arquitectura/realineacion-entrega-1.md`, `docs/02-arquitectura/trazabilidad-arquitectonica.md` | HV-05 |
| 2026-10-31 | DIV-08 queda resuelta. | El docente autorizó el trabajo individual; lo confirmó el autor. | `docs/02-arquitectura/arquitectura.md`, `docs/02-arquitectura/realineacion-entrega-1.md` | DIV-08 |
| 2026-10-31 | `workspace.dsl` validado con Structurizr. Los SVG de C4 y de secuencia se exportan desde sus fuentes; los dos SVG de la Entrega 2 dibujados a mano quedan sustituidos. CON-04 y su relación con la API se alinean con HV-07. | La exportación estaba pendiente y la Entrega 3 exige SVG reproducibles. | `docs/02-arquitectura/diagramas/workspace.dsl`, `docs/02-arquitectura/diagramas/c4-contexto.svg`, `docs/02-arquitectura/diagramas/c4-contenedores.svg`, `docs/02-arquitectura/arquitectura.md`, `docs/03-diseno-vertical/diagramas/exportar-diagramas.sh`, `docs/03-diseno-vertical/diagramas/c4-componentes.svg`, `docs/03-diseno-vertical/diagramas/secuencia-vertical.svg`, `docs/03-diseno-vertical/diagramas/secuencia-alternativa.svg` | HV-07 |
| 2026-10-31 | PR-09 a PR-11 cubren el rechazo, los límites de la solicitud y las guardas del código, que estaban implementados sin prueba. `Disbursement.approve` deja de aceptar un motivo en blanco para un monto sobre el límite del cobrador. | La trazabilidad los declaraba sin cobertura, y una de las pruebas nuevas reveló el defecto. | `backend/src/royexa/sales/domain.py`, `backend/tests/vertical/test_pr09_rejection.py`, `backend/tests/vertical/test_pr10_request_limits.py`, `backend/tests/vertical/test_pr11_code_guards.py`, `backend/README.md`, `docs/03-diseno-vertical/trazabilidad-implementacion.md`, `docs/03-diseno-vertical/evidencias/resultado-pruebas.txt` | HV-10 |
| 2026-10-31 | La cobertura del recorrido declara dónde está cada dato en la Entrega 3: el Asiento en `CON-04`, la Caja y el Préstamo en memoria en `CON-03`. La plantilla de pull request pasa a la Entrega 3. | La trazabilidad contradecía HV-07, y la plantilla seguía titulada para la Entrega 0. | `docs/02-arquitectura/trazabilidad-arquitectonica.md`, `docs/02-arquitectura/realineacion-entrega-1.md`, `docs/02-arquitectura/arquitectura.md`, `.github/PULL_REQUEST_TEMPLATE.md` | HV-07 |

---

## 10. Limitaciones y trabajo pendiente

**Limitaciones del vertical**

- Solo el libro vive en PostgreSQL. Desembolsos, préstamos, cajas y avisos están en memoria, así que tras un reinicio el saldo sembrado no coincide con el libro persistido (HV-07).
- La memoria y PostgreSQL no forman una transacción atómica. Una caída entre los dos pasos del `commit` deja el asiento sin su efecto (RA-10).
- El saldo de la caja es un campo, no la suma de los asientos (HV-07).
- La identidad son usuarios sembrados y la cabecera `X-Actor-Id`, sin autenticación. Quien conozca un identificador puede actuar como ese usuario.
- `migrate.py` no tiene tabla de control: reaplica cada archivo en cada ejecución. Hoy funciona porque `001_ledger.sql` es repetible, y PR-07 lo comprueba. Una migración que no lo sea fallaría.
- La entrega de avisos es de al menos una vez: una excepción distinta de `NotifierUnavailable` aborta la ejecución del despachador, y un fallo del `commit` después de enviar puede repetir el aviso (HV-06, RA-11).
- No hay interfaz en la Entrega 3. La web mínima está prevista para la Entrega 4 (`propuesta.md`, sección L).
- Un código vencido sin intento no cambia de estado (HV-08).
- El código de confirmación no limita los intentos fallidos, y el notificador simulado lo imprime en la salida estándar porque ese es su papel en la demostración.

**Riesgos pendientes y confirmaciones que no se han obtenido**

- La confirmación docente de la realineación, de DIV-01 a DIV-07, de ADR-003 y de ADR-004 está pendiente.
- La retroalimentación de Canvas sobre la Entrega 2 está pendiente de incorporar. Si contradice este documento, prevalece.
- El repositorio no guarda la constancia de la autorización docente de DIV-08.
- El paso 4 del flujo («aprueba o rechaza indicando el motivo») admite dos lecturas: que el motivo acompañe solo al rechazo o también a toda aprobación. El código lo exige al rechazar y al autorizar un monto sobre el límite del cobrador, pero no al aprobar dentro de ese límite. La pregunta sigue abierta y HV-10 no la resuelve.

**Alcance de la validación de los diagramas**

- La validación de `workspace.dsl`, incluida la vista `c4-componentes`, comprueba su sintaxis y sus referencias. No demuestra que el modelo sea correcto.
- PlantUML procesa las secuencias, pero no las compara con el código. Esa comparación se hizo por lectura.

**Escenarios todavía no comprobados**

- `CashBoxClosed` (RN-02): está implementado, sin prueba automatizada, porque la Entrega 3 no puede cerrar cajas.
- El despachador ante otra excepción o ante un fallo del `commit` (HV-06).
- La lista completa está en `trazabilidad-implementacion.md`, sección 6.

**Siguiente incremento razonable**

- Llevar desembolsos, cajas y bandeja de salida a PostgreSQL en una sola transacción con el libro.
- Añadir la web mínima, pagos y cierre de caja, junto con EV-08 y EV-10.
- Implementar el asiento compensatorio de CA-08.

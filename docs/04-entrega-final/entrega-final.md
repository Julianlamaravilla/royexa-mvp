# Entrega 4 — Informe final del proyecto

## 0. Identificación

- **Proyecto:** ROYEXA
- **Integrantes:** Julian Andres Restrepo. El docente autorizó el trabajo individual (`DIV-08`, `docs/02-arquitectura/arquitectura.md`, sección 7.1).
- **Grupo:** 10
- **Fecha:** 2026-11-16
- **Repositorio:** <https://github.com/jyeanaqs262/repogrp10>
- **Commit o etiqueta evaluable:** etiqueta `entrega-4-final`, creada sobre la rama `entrega-4-final` al cierre de la entrega.

## 1. Resultado del proyecto

### 1.1 Problema y resultado de negocio

Las financieras pequeñas que prestan a diario y cobran puerta a puerta sufren fraude interno: un cobrador recibe un pago y no lo registra, o reporta un desembolso que nunca entregó, y el descuadre se descubre tarde o nunca (`docs/01-requisitos/requisitos.md`, sección 1.1).

La versión final de ROYEXA convierte cada movimiento de dinero en un hecho verificable por alguien distinto de quien lo registró. El cobrador opera desde el navegador del celular (`/web/`): registra pagos con contador fraccionario (RN-01) y no pagos, solicita desembolsos que solo liberan dinero cuando el cliente final dicta el código que recibió por un canal independiente (RN-03), y cierra su caja del día. El administrador aprueba sin poder aprobar lo que él mismo originó (RN-06), consulta el libro inalterable con sus ajustes compensatorios (RN-04), ve el descuadre de cada cierre el mismo día y los del periodo (RF-07), y detecta los comprobantes que no llegaron al cliente (CA-12). Todo el estado vive en PostgreSQL 17 y el libro solo admite inserciones por privilegios de la base de datos.

### 1.2 Alcance final

| Elemento | Referencias | Estado | Evidencia o ruta | Observación |
|---|---|---|---|---|
| Flujo principal: desembolso con código, pago y cierre | RF-03, RF-01, RF-02; CA-05, CA-01, CA-03; UC-01 a UC-05 | Completo | `backend/src/royexa/sales/application.py`, `backend/src/royexa/loans/application.py`, `backend/src/royexa/closing/application.py`; `evidencias/escenario-principal.txt`; PR-01 | Recorrido de la sección 2.1, por API y por la web |
| Registrar pago o no pago en ruta (Must) | RF-01; CA-01, CA-02; RN-01 | Completo | `backend/src/royexa/loans/domain.py`; `backend/tests/vertical/test_t3a_payments.py`, `backend/tests/vertical/test_t3b_visits.py`, `backend/tests/loans/test_t3a_payment_allocation.py`; EV-10 | Efectivo o transferencia; solo el efectivo suma a la caja |
| Cerrar la caja diaria y detectar descuadre (Must) | RF-02; CA-03, CA-04; RN-02 | Completo | `backend/src/royexa/closing/application.py`, `backend/src/royexa/cash_box/domain.py`; `backend/tests/vertical/test_t5b_cash_close.py`, `backend/tests/vertical/test_t5c_panels.py` | Esperado = cobros en efectivo − desembolsos confirmados del día (decisión T5-P1 en `odd/tasks/mvp.md`) |
| Aprobar un desembolso con confirmación del cliente (Must) | RF-03; CA-05, CA-06; RN-03, RN-05, RN-06 | Completo | `backend/src/royexa/sales/domain.py`; PR-01, PR-02, PR-03, PR-04, PR-05, PR-09, PR-10, PR-11; EV-11, EV-12 | Código de un solo uso, guardado como huella, con caducidad y 5 intentos |
| Conservar un libro inmutable (Must) | RF-04; CA-07, CA-08; RN-04 | Completo | `backend/migrations/001_ledger.sql`, `backend/migrations/011_adjustments.sql`, `backend/src/royexa/ledger/posting.py`; PR-07; `backend/tests/vertical/test_t5d_adjustments.py`; EV-01, EV-02 | La corrección es un asiento `AJUSTE` nuevo; el original no se toca |
| Clientes y préstamos con calendario (Must) | RF-05; CA-09, CA-10; RN-01, RN-05 | Completo, con una interpretación declarada | `backend/src/royexa/clients/application.py`, `backend/src/royexa/loans/domain.py`; `backend/tests/vertical/test_t2a_clients.py`, `backend/tests/vertical/test_t2b_loans.py`, PR-04 | El préstamo nace al confirmar un desembolso (RN-03), no por alta directa; ver 1.3 |
| Notificar el comprobante al cliente final (Must) | RF-06; CA-11, CA-12; EC-04 | Completo con notificador simulado | `backend/src/royexa/shared/outbox.py`, `backend/src/royexa/notifications/dispatcher.py`; PR-06; `backend/tests/vertical/test_t4_payment_receipt.py`; EV-03, EV-08 | `EXT-05` simulado por `RES-03` |
| Consultar los descuadres del periodo (Should) | RF-07; CA-13; RN-02 | Completo | `backend/src/royexa/closing/application.py` (`DiscrepancyQueries`); `backend/tests/vertical/test_t9_discrepancies.py`, `backend/tests/web/test_t9_discrepancy_page.py`, `backend/tests/web/test_t14b_panel.py` | API `GET /v1/cash-discrepancies` y páginas `/web/admin/descuadres` y `/web/admin` |
| Escenarios de calidad | EC-01, EC-02, EC-03, EC-04 | Completo | PR-07, PR-02, `backend/tests/loans/test_t3a_payment_allocation.py`, PR-06; `evidencias/evaluacion-ea-01.txt`, `evidencias/notificador-caido.txt` | Evaluados en la sección 6 |

### 1.3 Exclusiones y limitaciones

La Entrega 1 no declaró requisitos `Could`; el único `Should` (RF-07) está completo.

| Elemento no terminado | Motivo | Impacto | Mitigación o decisión |
|---|---|---|---|
| Aplicación móvil nativa (`CON-01`) | Excluida por la Entrega 1 (sección 1.5) y por `DIV-02` | El cobrador usa el navegador del celular | Web renderizada en el servidor, probada a 360 px (`backend/tests/e2e/test_t7d_phone_flow.py`) |
| Operación sin conexión con sincronización posterior | Excluida por la Entrega 1; `ADR-003` quedó `Rechazado (reemplazado por ADR-004)` | Sin señal no se registra el cobro | Operación en línea con confirmación idempotente (`ADR-004`) y fichas de un solo uso en los formularios web |
| Varias empresas sobre una instalación (`AD-04`, `INV-03`) | Excluida por la Entrega 1 (`DIV-03`) | Una instalación sirve a una sola financiera | Diferida con su identificador; `EV-07` sin destino en el curso |
| Proveedor real de notificaciones (SES, FCM, Telegram u otro) | `RES-03`: el canal real exige una empresa registrada | El cliente final no recibe mensajes reales; el código aparece en la salida del servidor | Puerto `Notifier` con adaptador simulado (`EXT-05`); el cambio de adaptador está probado (EV-08) |
| Almacén de fotos (`CON-05`) | Fuera de la línea base de la Entrega 1 | Sin fotos de documento ni de comprobantes | Diferido sin destino en el curso |
| Alta directa de un préstamo por el administrador (lectura literal de CA-09) | RN-03 hace nacer el préstamo al confirmar el desembolso; un alta directa saltaría el control antifraude | El administrador no crea préstamos sin desembolso | CA-09 se prueba por el camino del desembolso (`backend/tests/vertical/test_t2b_loans.py`); interpretación registrada en T2b de `odd/tasks/mvp.md` |
| Caducidad de un código vencido sin intento (`HV-08`) | No existe un barrido periódico de códigos vencidos | Un desembolso abandonado sigue `APROBADO` aunque su código ya no sirva; no mueve dinero | Se caduca al primer intento (PR-03); barrido en la deuda DT-04 |
| Usuarios y rutas sembrados (`ALT-06B`) | Sin alta de usuarios en el alcance de la Entrega 1 | Los usuarios de demostración son fijos; el piloto los lee de `backend/pilot/directory.json` | Contraseñas con `scrypt`, sesiones con token opaco y modo estricto `ROYEXA_REQUIRE_CHANGED_PASSWORDS=1` |

## 2. Demostración funcional

- **Actor o sistema iniciador:** INT-01 Cobrador (`cobrador-1`); intervienen INT-02 Administrador (`admin-1`) e INT-03 Cliente final a través de `EXT-05`.
- **Entrada:** solicitud de desembolso desde `/web/desembolso/nuevo` o `POST /v1/disbursements`, seguida de pagos y del cierre de caja.
- **Reglas ejercidas:** RN-01, RN-02, RN-03, RN-04, RN-05, RN-06.
- **Resultado observable:** préstamo con calendario de 20 cuotas, asiento en el libro y descuento de la caja tras el código; contador «19,5 de 20» tras un pago parcial; cierre con descuadre de −25,00 visible para el administrador.
- **Datos de demostración:** se siembran solos al arrancar con `ROYEXA_SEED=demo` (valor por defecto; `backend/src/royexa/seed.py`): `cobrador-1` y `cobrador-2` con sus rutas, `admin-1` y `admin-2`, `cliente-1` (sin préstamos), `cliente-2` (préstamo `prestamo-impago` con saldo de 700,00), `cliente-3` (préstamo liquidado) y `cliente-4` (de `ruta-2`). Las contraseñas públicas de demostración son `demo-<usuario>-royexa`.

### 2.1 Escenario principal

Ejecutado por HTTP el 2026-11-16 y registrado en [`evidencias/escenario-principal.txt`](evidencias/escenario-principal.txt). En la web, los mismos pasos usan las páginas indicadas.

1. `cobrador-1` solicita un desembolso de 100,00 a 20 días y 20 cuotas para `cliente-1` (`/web/desembolso/nuevo`). El sistema valida ruta, límites y RN-05; el desembolso queda `SOLICITADO`.
2. `admin-1` lo aprueba (`/web/admin/solicitudes`). Queda `APROBADO`, con quien solicitó y quien aprobó; la caja no cambia (RN-03).
3. El despacho de avisos (bucle en segundo plano cada 30 s, o «Reintentar envío» en `/web/admin/avisos`) entrega el código por `EXT-05`; el servidor imprime una línea `[EXT-05] ... kind=CODIGO_CONFIRMACION ...` que hace las veces del mensaje al cliente.
4. El cliente dicta el código y el cobrador lo valida (`/web/desembolso/{id}`). El desembolso queda `CONFIRMADO`, se crea el préstamo con 20 cuotas de 6,00 de lunes a sábado, se asienta el desembolso y la caja baja de 1.000.000,00 a 999.900,00 (CA-05, CA-07, CA-09).
5. El cobrador registra un pago parcial en efectivo de 3,00 sobre una cuota de 6,00 (`/web/pago/{loan_id}`): el préstamo queda con 19,5 cuotas restantes de 20 y saldo 117,00 (RN-01, CA-01, EC-03), y se encola el comprobante (CA-11).
6. El cobrador registra un pago de 700,00 que liquida `prestamo-impago` de `cliente-2`; ya no quedan visitas pendientes.
7. El cobrador cierra la caja (`/web/cierre`) entregando 578,00. **Resultado:** esperado 603,00 (3,00 + 700,00 − 100,00), entregado 578,00, descuadre −25,00 asentado; la caja queda cerrada y un pago posterior responde `409 caja-cerrada` (RN-02, CA-03). El administrador ve el descuadre en `/web/admin/descuadres` y en `GET /v1/cash-discrepancies` (CA-13).

Pruebas que automatizan el escenario: PR-01 (`backend/tests/vertical/test_pr01_valid_confirmation.py`) para los pasos 1 a 4, `backend/tests/vertical/test_t3a_payments.py::test_ca01_a_partial_payment_advances_the_counter_fractionally` para el paso 5, `backend/tests/vertical/test_t5b_cash_close.py::test_ca03_the_close_shows_the_difference_between_registered_and_delivered` para el paso 7 y, con un navegador real a 360 px, `backend/tests/e2e/test_t7d_phone_flow.py` (inicio de sesión, pago y cierre) y `backend/tests/e2e/test_t8_admin_approval.py` (aprobación del administrador).

### 2.2 Escenario alternativo o de error

Se demuestran tres alternativas. La primera es la que exige el enunciado sobre la integración.

**A. Notificador caído (EC-04, CA-12).**

- **Condición:** el servidor arranca con `ROYEXA_NOTIFIER_FAILING=1`; el cobrador registra un pago en efectivo de 250,00 sobre `prestamo-impago`.
- **Comportamiento esperado:** el pago, su asiento y el efecto en la caja se confirman (201); el comprobante queda `PENDIENTE`; cada despacho cuenta un intento con el motivo; al quinto queda `FALLIDO` con `attempts: 5` y deja de reintentarse; el administrador lo ve en `/web/admin/avisos` (contador rojo de fallidos) y en `GET /v1/notifications`. Observado por HTTP en [`evidencias/notificador-caido.txt`](evidencias/notificador-caido.txt).
- **Regla, riesgo o decisión comprobada:** EC-04, CA-12, RA-03, `ADR-002`. Pruebas: PR-06 (`backend/tests/vertical/test_pr06_notifier_failure.py`), `backend/tests/vertical/test_t4_payment_receipt.py` y `backend/tests/web/test_t12_notices.py`.

**B. Autoaprobación rechazada (RN-06, EC-02).**

- **Condición:** `admin-1` solicita un desembolso y luego intenta aprobarlo.
- **Comportamiento esperado:** `403 autoaprobacion-prohibida`; el desembolso sigue `SOLICITADO`, sin código, y el intento queda registrado con identidad, rol y motivo `quien_origina_no_aprueba` (pasos 11 de `evidencias/escenario-principal.txt`).
- **Regla, riesgo o decisión comprobada:** RN-06, EC-02, `AD-06`/`ALT-06B`, EV-11. Prueba: PR-02 (`backend/tests/vertical/test_pr02_self_approval_rejected.py`).

**C. Cierre con visitas pendientes y código caducado.**

- **Condición:** el cobrador intenta cerrar con clientes pendientes de visita; o se valida un código después de su caducidad.
- **Comportamiento esperado:** `409 visitas-pendientes` y la caja sigue abierta (CA-04, paso 5 de `evidencias/escenario-principal.txt`); `409 codigo-caducado`, la caja intacta y un asiento `DESEMBOLSO_CADUCADO` con motivo (CA-06).
- **Regla, riesgo o decisión comprobada:** RN-02, RN-03, RN-04. Pruebas: `backend/tests/vertical/test_t5b_cash_close.py::test_ca04_pending_visits_reject_the_close_and_the_box_stays_open` y PR-03 (`backend/tests/vertical/test_pr03_expired_code.py`).

## 3. Arquitectura final

### 3.1 Organización y fronteras

- **Unidad de ejecución:** un solo proceso, `CON-03` (Python 3.14, FastAPI, Jinja2, Uvicorn), que sirve la API JSON `/v1` (`backend/src/royexa/api.py`, `CMP-01`) y la web renderizada en el servidor `/web` (`backend/src/royexa/web/`, `CMP-14`). La web no llama a la API por HTTP: invoca los mismos casos de uso. Dentro del proceso corre el bucle de despacho de avisos (`backend/src/royexa/background.py`, `CMP-17`).
- **Almacenamiento:** `CON-04`, PostgreSQL 17 (`docker-compose.yml`, puerto 55432). Todo el estado (desembolsos, préstamos, pagos, no pagos, cajas, cierres, clientes, credenciales, sesiones, fichas de formulario y bandeja de salida) se confirma en la misma transacción que el libro (`PostgresSession`, `backend/src/royexa/adapters/postgres_state.py`). El libro concede al rol `royexa_app` solo `SELECT` e `INSERT` (`backend/migrations/001_ledger.sql`). El esquema lo aplica `backend/src/royexa/migrate.py` (`CMP-13`) con el rol propietario `royexa_migrator`. Sin `ROYEXA_LEDGER_URL` el mismo código corre con adaptadores en memoria (pruebas rápidas y demostración sin base).
- **Módulos de negocio** (`backend/src/royexa/`): `identity_access` (usuarios, sesiones, contraseñas), `clients`, `loans` (préstamos, calendario, pagos, no pagos, visitas), `sales` (desembolso y código), `ledger` (único escritor del libro), `cash_box` (caja del día), `closing` (cierre, ajustes, descuadres) y `notifications` (despachador). `shared` es el núcleo sin reglas de negocio (dinero en centavos, reloj, calendario, bandeja de salida).
- **Puertos y adaptadores:** cada módulo declara sus puertos como `Protocol` en `*/ports.py` (por ejemplo `backend/src/royexa/sales/ports.py`, `backend/src/royexa/notifications/ports.py`); los adaptadores viven en `backend/src/royexa/adapters/` y solo `backend/src/royexa/bootstrap.py` (`CMP-12`) decide cuál llena cada puerto.
- **Dirección de dependencias:** hacia adentro. Los módulos de negocio no importan FastAPI, Pydantic, psycopg ni adaptadores; el grafo de módulos es acíclico; ningún módulo de negocio llama a `notifications`, que solo lee la bandeja de salida. Lo comprueba en cada ejecución PR-08 (`backend/tests/architecture/test_pr08_dependencies.py`, EV-09).
- **Frontera externa:** `EXT-05`, notificador del cliente final, detrás del puerto `Notifier` (`CTR-10`) y simulado por `backend/src/royexa/adapters/simulated_notifier.py` (`CMP-11`).

### 3.2 Vistas vigentes

- **Fuente C4:** [`../02-arquitectura/diagramas/workspace.dsl`](../02-arquitectura/diagramas/workspace.dsl)
- **Contexto:** [`../02-arquitectura/diagramas/c4-contexto.svg`](../02-arquitectura/diagramas/c4-contexto.svg)
- **Contenedores:** [`../02-arquitectura/diagramas/c4-contenedores.svg`](../02-arquitectura/diagramas/c4-contenedores.svg)
- **Componentes:** [`../03-diseno-vertical/diagramas/c4-componentes.svg`](../03-diseno-vertical/diagramas/c4-componentes.svg)
- **Secuencias:** [`../03-diseno-vertical/diagramas/secuencia-vertical.svg`](../03-diseno-vertical/diagramas/secuencia-vertical.svg) y [`../03-diseno-vertical/diagramas/secuencia-alternativa.svg`](../03-diseno-vertical/diagramas/secuencia-alternativa.svg). Índice y comando de exportación en [`diagramas/README.md`](diagramas/README.md).

### 3.3 Cambios significativos

| Cambio | Evidencia que lo originó | Decisión o ADR | Consecuencia |
|---|---|---|---|
| La web se construye dentro de `CON-03` (componente `CMP-14`) y no como contenedor `CON-02` aparte | Una sola unidad desplegable bastaba para la demostración local (`RES-02`); la web reutiliza los casos de uso sin un segundo cliente HTTP | AD-02, `ADR-002` | `CON-02` queda histórico en `docs/02-arquitectura/diagramas/workspace.dsl`; un proceso menos que operar |
| Todo el estado pasa a PostgreSQL en la transacción del libro | HV-07, RA-10: en la Entrega 3 desembolsos, cajas y avisos vivían en memoria y se perdían al reiniciar | `ADR-001`, `ADR-002`, `ADR-004` (todos `Aceptado`) | RA-10 cerrado; `backend/tests/postgres/test_t1a_persistence.py`, `backend/tests/postgres/test_t1b_disbursements.py` |
| Sesiones con token opaco y contraseñas `scrypt` sustituyen la cabecera `X-Actor-Id` | Limitación declarada de la Entrega 3 (cualquiera podía actuar como otro usuario) | AD-06, `ALT-06B` | `backend/src/royexa/identity_access/`; `backend/tests/vertical/test_t6a_sessions.py`, `backend/tests/identity/test_t6b_lockout.py` |
| El despachador de avisos corre en un bucle en segundo plano dentro del proceso | En la Entrega 3 un aviso quedaba pendiente hasta que alguien invocara el despacho | AD-02, `ADR-002` | `CMP-17`; un aviso puede tardar hasta `ROYEXA_DISPATCH_SECONDS`; `backend/tests/shared/test_t10a_background_dispatch.py` |
| Asiento compensatorio `AJUSTE` | HV-03: la Entrega 3 solo impedía alterar, no permitía corregir (CA-08) | `ADR-001` | `backend/migrations/011_adjustments.sql`; `backend/tests/vertical/test_t5d_adjustments.py` |
| Estados finales de los ADR | EV-08 y EV-12 validadas; DIV-02 resuelta a favor de la Entrega 1 | `ADR-001`, `ADR-002`, `ADR-004` `Aceptado`; `ADR-003` `Rechazado (reemplazado por ADR-004)` | Historial en cada ADR de `docs/02-arquitectura/adr/` |
| Pagos, no pagos, cierre y descuadres (RF-01, RF-02, RF-07) | Pendientes desde la Entrega 3 (`docs/03-diseno-vertical/trazabilidad-implementacion.md`, sección 6) | AD-05 (enteros de centavos y fracciones exactas) | `CMP-16`; EV-10 validada por `backend/tests/loans/test_t3a_payment_allocation.py` |

## 4. Patrones aplicados

### PAT-01 — Repository y Unit of Work

- **Problema concreto:** cada operación de dinero toca varias entidades (desembolso, préstamo, caja, asiento, aviso) que deben confirmarse juntas o no confirmarse; y las reglas deben probarse sin PostgreSQL y también contra PostgreSQL real.
- **Contexto y fuerzas:** RN-04 y EC-01 exigen el libro en PostgreSQL con privilegios reales; la suite rápida debe correr sin Docker; RA-10 mostró que dos almacenes sin transacción común dejan asientos sin su efecto.
- **Alternativa simple considerada:** casos de uso que abren su propia conexión psycopg y escriben SQL directo. Se descartó: acopla las reglas al driver (lo prohíbe PR-08) y obliga a una base para cada prueba.
- **Decisión:** repositorios por agregado declarados como `Protocol` en el módulo dueño y una unidad de trabajo por caso de uso (`with uow: ... uow.commit()`), con dos implementaciones intercambiables.
- **Participantes:** `DisbursementRepository` y `SalesUnitOfWork`, `LoanRepository`, `PaymentRepository`, `CashRepository`, `LedgerRepository`, `Outbox`; implementaciones `InMemoryUnitOfWork` y repositorios `InMemory*`, `PostgresSession` y repositorios `Postgres*`, `PostgresLedgerRepository`.
- **Rutas de código:** `backend/src/royexa/sales/ports.py`, `backend/src/royexa/loans/ports.py`, `backend/src/royexa/cash_box/ports.py`, `backend/src/royexa/ledger/ports.py`, `backend/src/royexa/adapters/memory.py`, `backend/src/royexa/adapters/postgres_state.py`, `backend/src/royexa/adapters/postgres_ledger.py`.
- **Beneficio comprobado:** las pruebas verticales se ejecutan contra los dos adaptadores con el mismo código (fixture `backend` de `backend/tests/conftest.py`, variantes `[memory]` y `[postgres]`); el estado y el libro se confirman en una transacción (`backend/tests/postgres/test_t1a_persistence.py`); un `commit` fallido no deja nada (`test_pr07_failed_ledger_commit_changes_nothing_and_surfaces_its_error`).
- **Costo o riesgo:** cada tabla nueva exige dos implementaciones que deben comportarse igual (LSP); la unidad de trabajo es una sola clase, `InMemoryUnitOfWork`, que con base de datos delega todos los repositorios en `PostgresSession`, lo que confunde a quien lee el nombre (deuda DT-07).
- **Pruebas o evidencia:** PR-05, PR-07; `backend/tests/postgres/test_t1a_persistence.py`; EV-12.

### PAT-02 — Adapter (puertos y adaptadores) para el notificador

- **Problema concreto:** el canal real hacia el cliente final no está disponible (`RES-03`) y RF-06 no puede aplazarse (`RES-05`); la lógica de avisos no debe depender del proveedor.
- **Contexto y fuerzas:** el proveedor futuro (SMS, correo, Telegram) es desconocido; EC-04 exige reproducir su fallo en pruebas; la demostración no puede depender de un servicio externo.
- **Alternativa simple considerada:** llamar al proveedor directamente desde el caso de uso de pago (ALT-02C). Se descartó: un fallo del canal revertiría o bloquearía el dinero, y no habría simulador.
- **Decisión:** puerto `Notifier` (`CTR-10`) con un único método `send(Notification)` y la excepción `NotifierUnavailable`; el adaptador simulado lo implementa y la composición lo elige.
- **Participantes:** `Notifier`, `Notification`, `NotifierUnavailable`, `SimulatedNotifier`, `build_container(notifier=...)`.
- **Rutas de código:** `backend/src/royexa/notifications/ports.py`, `backend/src/royexa/adapters/simulated_notifier.py`, `backend/src/royexa/bootstrap.py`.
- **Beneficio comprobado:** EV-08 validada: `test_pr06_code_notice_fails_after_five_dispatches_through_a_replaced_adapter` construye el sistema con otro adaptador del puerto sin tocar ningún módulo de negocio; PR-08 comprueba que ningún módulo de negocio importa `notifications`.
- **Costo o riesgo:** el contrato no devuelve respuesta, así que no modela respuestas inválidas ni plazos (DT-02); el simulado imprime el código en la salida estándar, aceptable solo en la demostración.
- **Pruebas o evidencia:** PR-06; `backend/tests/vertical/test_t4_payment_receipt.py`; EV-03, EV-08; `evidencias/notificador-caido.txt`.

### PAT-03 — Transactional Outbox

- **Problema concreto:** el dinero se confirma en la base y el aviso sale a un tercero; si se hacen por separado, un fallo entre ambos pierde el aviso (RA-03) o revierte el dinero.
- **Contexto y fuerzas:** EC-04 y CA-12 exigen que el envío no confirmado quede visible; ASR-05 exige rastrear juntos asiento y aviso; no hay intermediario de mensajería en la línea base.
- **Alternativa simple considerada:** enviar dentro de la misma transacción (ALT-02C) o un intermediario de mensajes (ALT-02B). La primera acopla el dinero al canal; la segunda añade infraestructura sin necesidad (`ADR-002`).
- **Decisión:** el caso de uso encola un `OutboxMessage` en su propia unidad de trabajo; el despachador es su único lector, cuenta un intento por ronda y marca `FALLIDO` tras `MAX_DELIVERY_ATTEMPTS` (5); un bucle en segundo plano lo invoca cada `ROYEXA_DISPATCH_SECONDS`.
- **Participantes:** `OutboxMessage`, `NoticeStatus`, `Outbox`, `PostgresOutbox`, `InMemoryOutbox`, `NotificationDispatcher`, `NoticeQueries`, `dispatch_forever`.
- **Rutas de código:** `backend/src/royexa/shared/outbox.py`, `backend/src/royexa/notifications/dispatcher.py`, `backend/src/royexa/background.py`, `backend/src/royexa/adapters/postgres_state.py`.
- **Beneficio comprobado:** con el canal caído el pago queda confirmado y el aviso termina `FALLIDO` y visible (`evidencias/notificador-caido.txt`); al recuperarse el canal, un pendiente sale sin intervención (`test_t10a_a_notice_that_failed_goes_out_when_the_channel_recovers`).
- **Costo o riesgo:** entrega de al menos una vez (RA-11, HV-06): un fallo al confirmar después de enviar repite el aviso; latencia de hasta un intervalo; un aviso `FALLIDO` no se reenvía desde la web (decisión T12 de `odd/tasks/mvp.md`).
- **Pruebas o evidencia:** PR-06; `backend/tests/shared/test_t10a_background_dispatch.py`; `backend/tests/web/test_t12_notices.py`; EV-03.

### PAT-04 — Service Layer (casos de uso)

- **Problema concreto:** las mismas operaciones se invocan desde la API JSON y desde la web; si cada entrada coordinara repositorios, las reglas se duplicarían.
- **Contexto y fuerzas:** la web llegó en la Entrega 4 sobre un dominio ya probado por API; las reglas deben vivir en el dominio y la coordinación en un solo lugar (AD-06).
- **Alternativa simple considerada:** controladores FastAPI que operan sobre el dominio directamente. Se descartó: la web tendría que repetir cada coordinación y cada transacción.
- **Decisión:** una clase por caso de uso con `execute`, que abre la unidad de trabajo, llama al dominio y confirma; consultas en clases `*Queries`. Son clases concretas, sin interfaz, porque no hay variación que la justifique.
- **Participantes:** `RequestDisbursement`, `ApproveDisbursement`, `ConfirmDisbursement`, `RegisterPayment`, `RegisterNonPayment`, `CloseCashBox`, `RegisterAdjustment`, `RegisterClient`, `SalesQueries`, `DiscrepancyQueries`.
- **Rutas de código:** `backend/src/royexa/sales/application.py`, `backend/src/royexa/loans/application.py`, `backend/src/royexa/closing/application.py`, `backend/src/royexa/clients/application.py`, `backend/src/royexa/identity_access/application.py`.
- **Beneficio comprobado:** la web de la Entrega 4 se añadió sin reimplementar reglas; `test_t12_the_page_reads_the_same_notices_as_the_api` y las pruebas de páginas de `backend/tests/web/` ejercen los mismos casos de uso que la API.
- **Costo o riesgo:** una capa más que recorrer al leer el código; `backend/src/royexa/sales/application.py` concentra varios casos de uso del desembolso.
- **Pruebas o evidencia:** PR-01 a PR-05, PR-09 a PR-11; `backend/tests/web/test_t7b_payment_pages.py`, `backend/tests/web/test_t7c_disbursement_pages.py`.

### PAT-05 — Composition Root con fábrica (`build_container`)

- **Problema concreto:** elegir adaptadores (memoria o PostgreSQL, notificador normal, caído o de prueba, reloj real o falso, siembra demo o piloto) sin que los módulos lo sepan.
- **Contexto y fuerzas:** las pruebas necesitan un reloj controlable (`CTR-11`) y un notificador que falle; la demostración y el piloto se configuran por variables de entorno; PR-08 prohíbe que el dominio importe adaptadores.
- **Alternativa simple considerada:** que cada módulo lea variables de entorno e instancie sus dependencias. Se descartó: dispersa la configuración e impide sustituir piezas en las pruebas.
- **Decisión:** `Settings.from_env()` lee la configuración; `build_container(settings, clock, notifier)` es la única fábrica que crea los adaptadores y los casos de uso y devuelve un `Container`; `royexa.main` crea la aplicación con él.
- **Participantes:** `Settings`, `Container`, `build_container`, `ensure_production_ready`, `create_app`.
- **Rutas de código:** `backend/src/royexa/bootstrap.py`, `backend/src/royexa/main.py`, `backend/src/royexa/api.py`.
- **Beneficio comprobado:** las pruebas inyectan `FakeClock` y notificadores propios (`backend/tests/support.py`); el modo con base y sin base cambia solo por `ROYEXA_LEDGER_URL`; el modo estricto se niega a arrancar con contraseñas conocidas (`backend/tests/shared/test_t10b_pilot_seed.py`).
- **Costo o riesgo:** `Container` tiene muchos campos y crece con cada caso de uso.
- **Pruebas o evidencia:** PR-08; `backend/tests/shared/test_t10a_background_dispatch.py::test_t10a_the_interval_comes_from_the_environment`.

### PAT-06 — Decisión de no aplicar Strategy al medio de pago

- **Problema concreto:** un pago es en efectivo o por transferencia, y solo el efectivo suma a la caja (`RES-01`).
- **Contexto y fuerzas:** dos variantes cerradas que solo difieren en un efecto de caja; no hay comisiones, conciliación ni pasarela (`RES-01` excluye custodiar fondos).
- **Alternativa simple considerada:** un enumerado y una condición en un solo lugar. Es la que se aplicó.
- **Decisión:** no aplicar Strategy. `PaymentMethod` es un `StrEnum` de dos valores y el efecto en caja se decide en el asiento. Strategy pasaría a valer la pena cuando un medio necesite comportamiento propio (validación de referencia de transferencia, conciliación con un banco, comisiones) o aparezca un tercer medio con reglas distintas.
- **Participantes:** `PaymentMethod`, `RegisterPayment`, `LedgerPosting`.
- **Rutas de código:** `backend/src/royexa/shared/payments.py`, `backend/src/royexa/loans/application.py`, `backend/src/royexa/ledger/posting.py`.
- **Beneficio comprobado:** una sola condición, legible y probada; sin jerarquía de clases que mantener.
- **Costo o riesgo:** añadir un medio obliga a tocar el enumerado, el asiento y la migración (OCP no se cumple aquí de forma deliberada).
- **Pruebas o evidencia:** `backend/tests/vertical/test_t3a_payments.py::test_t3a_a_transfer_is_recorded_but_adds_no_cash`, `backend/tests/vertical/test_t5b_cash_close.py::test_t5p1_transfers_do_not_enter_the_expected_cash`.

## 5. Integración o subsistema distribuido

- **Sistema o subsistema:** `EXT-05`, notificador del cliente final (simulado).
- **Propósito:** entregar al cliente final el código de confirmación del desembolso y los comprobantes de desembolso y de pago, por un canal que no depende del cobrador (RF-06, RN-03, `RES-05`).
- **Mecanismo:** interfaz sustituible dentro del proceso (puerto `Notifier`) alimentada por una bandeja de salida en PostgreSQL y un despachador en segundo plano. No hay llamada de red en la línea base.
- **Componente responsable:** `CMP-08` (avisos), `CMP-11` (adaptador del notificador simulado) y `CMP-17` (despacho en segundo plano).
- **Contrato o puerto:** `CTR-10` (`Notifier`), con `CTR-08` (`Outbox`) y `CTR-09` (`NotificationsUnitOfWork`).
- **Datos funcionales intercambiados:** identificador del mensaje (útil para descartar duplicados en un proveedor real), cliente destinatario, tipo (`CODIGO_CONFIRMACION`, `COMPROBANTE_DESEMBOLSO`, `COMPROBANTE_PAGO`), desembolso o pago asociado y contenido: el código en claro solo en el aviso del código, o importe recibido, saldo restante y próximo vencimiento en el comprobante del pago (CA-11). Al enviarse o fallar definitivamente, el contenido se borra de la bandeja; la API de avisos nunca lo expone (`test_t4_the_notice_api_never_exposes_the_payload`).
- **Punto de sustitución:** `backend/src/royexa/notifications/ports.py` (`Notifier`) y el parámetro `notifier` de `build_container` en `backend/src/royexa/bootstrap.py`.
- **Simulador, fake o stub:** `backend/src/royexa/adapters/simulated_notifier.py`; con `ROYEXA_NOTIFIER_FAILING=1` reproduce el canal caído. Las pruebas usan además un adaptador propio del puerto (PR-06).

### 5.1 Fallos parciales

| Condición | Detección | Respuesta del sistema | Evidencia |
|---|---|---|---|
| Servicio no disponible | El adaptador lanza `NotifierUnavailable` | El dinero ya está confirmado y no se toca. El aviso sigue `PENDIENTE` con `attempts` y `last_error`; cada ronda reintenta; al quinto intento queda `FALLIDO` y sale de la cola; el administrador lo ve en `/web/admin/avisos` con su motivo y un contador en el menú (T12). Si el canal vuelve antes del quinto intento, el aviso sale solo | PR-06; `backend/tests/vertical/test_t4_payment_receipt.py`; `backend/tests/web/test_t12_notices.py`; EV-03; `evidencias/notificador-caido.txt` |
| Demora o respuesta inválida | **Demora:** no se detecta; el contrato no impone plazo y el despachador espera a que `send` termine. **Respuesta inválida:** `send` no devuelve nada que validar; una excepción distinta de `NotifierUnavailable` corta la ronda | Demora: el lote se retrasa, pero el despacho corre en un hilo aparte (`run_in_threadpool`), así que las peticiones de los usuarios no esperan, y el candado del despachador evita rondas superpuestas. Otra excepción: el aviso de esa ronda no se confirma y sigue `PENDIENTE` sin contar el intento; el bucle registra el error y continúa en la siguiente ronda (HV-06, RA-11). Ninguno de los dos casos mueve dinero. Se declara como deuda DT-02 | `backend/tests/shared/test_t10a_background_dispatch.py::test_t10a_the_loop_dispatches_every_round_and_survives_a_failure`; `backend/src/royexa/notifications/dispatcher.py` |

Consistencia: el sistema es consistente en el dinero (una transacción) y eventualmente consistente en el aviso. El cliente final puede recibir un comprobante hasta un intervalo después del pago, y en el peor caso dos veces (al menos una vez). Por eso CA-12 se cumple con un estado visible y no con una garantía de entrega.

### 5.2 Decisión de distribución

La solución es un **monolito modular** (`ADR-002`, `Aceptado`): un proceso con módulos de dueño único, llamadas directas para lo atómico y eventos por una bandeja de salida solo hacia los avisos. Se descartaron los servicios independientes por dominio (ALT-02B) porque el desembolso, el préstamo, la caja y el libro deben confirmarse juntos (RN-03, RN-04): repartirlos exigiría transacciones distribuidas o compensaciones sobre dinero, más infraestructura (intermediario de mensajes, varios despliegues) y más modos de fallo, para un equipo de una persona y una demostración local (`RES-02`, `RES-06`). Lo que se pierde es escalar o desplegar módulos por separado; ninguna evidencia lo exige (`EV-04` quedó sin destino en el curso). La frontera que sí podría salir del proceso, el notificador, ya está aislada por un puerto y una bandeja de salida, de modo que un proveedor remoto no cambia los módulos de negocio (EV-08). Las fronteras internas las vigila PR-08 para que la división futura siga siendo posible.

## 6. Evaluación arquitectónica

### EA-01 — Un asiento confirmado no puede alterarse y la corrección queda visible

- **Origen:** EC-01, ASR-01, RA-01, RA-02; RN-04, CA-08.
- **Estímulo:** el rol de la aplicación intenta `UPDATE`, `DELETE` y `TRUNCATE` sobre un asiento confirmado; el administrador corrige un asiento con un importe erróneo.
- **Resultado esperado:** el 100 % de las alteraciones falla por permiso y la fila queda intacta; la corrección crea un asiento compensatorio y ambos quedan consultables con identidad y las dos horas.
- **Elementos afectados:** `CON-03`, `CON-04`; `CMP-05`, `CMP-10`, `CMP-13`, `CMP-16`; `CTR-05`, `CTR-12`.
- **Actividad realizada:** pruebas de integración contra PostgreSQL 17 con el rol `royexa_app` (PR-07), inspección del catálogo de privilegios tras migrar, intento directo de alteración por SQL y pruebas del ajuste en memoria y en PostgreSQL.
- **Resultado y evidencia:** los tres intentos fallan con `InsufficientPrivilege` y el catálogo solo muestra `SELECT` e `INSERT` sobre `ledger_entry`; el ajuste deja el original y el compensatorio visibles, también tras reiniciar. EV-01 y EV-02 validadas. Salida en [`evidencias/evaluacion-ea-01.txt`](evidencias/evaluacion-ea-01.txt); pruebas PR-07, `backend/tests/vertical/test_t5d_adjustments.py`, `backend/tests/postgres/test_t5d_adjustments_persistence.py`.
- **Sensibilidad o trade-off:** la garantía depende de que ninguna migración conceda privilegios de más (punto sensible de `docs/02-arquitectura/arquitectura.md`, sección 6.3): por eso PR-07 revisa el catálogo de todas las tablas en cada ejecución. Quien tenga el rol propietario puede alterar el libro (RA-02); se aceptó frente a la cadena de hashes (ALT-01C), más costosa.
- **Decisión o acción:** `ADR-001` se mantiene `Aceptado` con la evidencia de la Entrega 4; RA-01 queda vigilado por PR-07 y RA-02 se acepta como riesgo residual (DT-06).

### EA-02 — El notificador falla y el control antifraude no queda en silencio

- **Origen:** EC-04, ASR-05, RA-03, RA-11; CA-12.
- **Estímulo:** el notificador no confirma ningún envío (servidor arrancado con `ROYEXA_NOTIFIER_FAILING=1`) mientras el cobrador registra un pago.
- **Resultado esperado:** el pago se confirma; el comprobante queda pendiente o fallido, nunca enviado; el administrador lo detecta.
- **Elementos afectados:** `CON-03`, `CON-04`, `EXT-05`; `CMP-08`, `CMP-11`, `CMP-17`; `CTR-08`, `CTR-10`.
- **Actividad realizada:** experimento por HTTP sobre el servidor en ejecución (pago, cinco despachos, consulta de avisos, caja, libro y préstamo, y un sexto despacho) y las pruebas automatizadas del fallo y de la recuperación.
- **Resultado y evidencia:** pago `201`; caja +250,00; asiento `PAGO` en el libro; préstamo con saldo 450,00; el comprobante pasa de `PENDIENTE` (0 intentos) a `FALLIDO` (5 intentos, motivo registrado) y el sexto despacho ya no lo intenta (`attempted: 0`). [`evidencias/notificador-caido.txt`](evidencias/notificador-caido.txt), PR-06, `backend/tests/vertical/test_t4_payment_receipt.py`, `backend/tests/shared/test_t10a_background_dispatch.py`.
- **Sensibilidad o trade-off:** separar dinero y aviso da integridad al dinero a cambio de consistencia eventual del aviso y de entrega de al menos una vez (RA-11); el número de intentos (5) y el intervalo (30 s) fijan cuánto tarda un fallo en volverse visible como `FALLIDO`.
- **Decisión o acción:** `ADR-002` pasa a `Aceptado` (EV-08 validada); RA-11 sigue abierto y se registra con la falta de plazo y de validación de respuesta (DT-02, DT-03).

## 7. Pruebas finales

Los identificadores PR-01 a PR-11 están definidos en `docs/03-diseno-vertical/diseno-y-vertical.md`, sección 6.1. PR-12 a PR-16 se definen en esta tabla para las pruebas de la Entrega 4.

| ID | Tipo | Escenario | Referencias | Ruta | Resultado |
|---|---|---|---|---|---|
| PR-01 | Componente sobre la API | Escenario principal: desembolso confirmado con asiento, calendario y descuento | UC-01, UC-02, UC-03, UC-05; CA-05, CA-07, CA-09 | `backend/tests/vertical/test_pr01_valid_confirmation.py` | Pasa |
| PR-12 | Navegador real (Playwright, Chromium a 360 px) | Escenario principal en la web: inicio de sesión, pago y cierre | CA-01, CA-03; RF-01, RF-02 | `backend/tests/e2e/test_t7d_phone_flow.py` | Pasa con Chromium instalado; sin él se omite con su motivo |
| PR-13 | Unidad (dominio puro) | Regla 1: contador fraccionario, 25 sobre una cuota de 50 deja 19,5 de 20 | RN-01; CA-01; EC-03; EV-10 | `backend/tests/loans/test_t3a_payment_allocation.py` | Pasa |
| PR-14 | Componente sobre la API | Regla 2: cierre solo sin pendientes, irreversible y con descuadre | RN-02; CA-03, CA-04 | `backend/tests/vertical/test_t5b_cash_close.py` | Pasa |
| PR-02 | Componente sobre la API | Regla 3: quien origina no aprueba | RN-06; CA-06; EC-02; EV-11 | `backend/tests/vertical/test_pr02_self_approval_rejected.py` | Pasa |
| PR-06 | Unidad/componente | Alternativo: notificador caído, el dinero se conserva y el aviso termina `FALLIDO` | CA-12; RN-03; EC-04; EV-03, EV-08 | `backend/tests/vertical/test_pr06_notifier_failure.py` | Pasa |
| PR-15 | Componente sobre la API | Alternativo: comprobante de pago fallido y reintento | CA-11, CA-12; EC-04 | `backend/tests/vertical/test_t4_payment_receipt.py` | Pasa |
| PR-07 | Integración con PostgreSQL 17 | Persistencia: privilegios reales del libro y flujo sobre el libro real | CTR-05, CTR-12; RN-04; EC-01; EV-01, EV-02, EV-12 | `backend/tests/postgres/test_pr07_ledger_privileges.py` | Pasa |
| PR-16 | Integración con PostgreSQL 17 | Persistencia: estado y libro en una transacción, ajuste compensatorio tras reiniciar | CTR-04, CTR-08; CA-08 | `backend/tests/postgres/test_t1a_persistence.py`, `backend/tests/postgres/test_t5d_adjustments_persistence.py` | Pasa |
| PR-08 | Estática | Dependencias entre módulos e integración aislada | EV-09; `ADR-002` | `backend/tests/architecture/test_pr08_dependencies.py` | Pasa |

- **Fecha de ejecución:** 2026-11-16
- **Comando:** `uv run pytest -m "" -rs` (desde `backend/`, con PostgreSQL 17 de `docker compose up -d --wait postgres`)
- **Total:** 1131
- **Exitosas:** 1120
- **Fallidas:** 0
- **Omitidas:** 11, cada una con su motivo: 9 pruebas de navegador porque esa máquina no tenía Chromium instalado (se instala con `uv run playwright install chromium`) y 2 que tienen su variante con base de datos en `backend/tests/postgres/`.
- **Evidencia:** [`evidencias/resultado-pruebas.txt`](evidencias/resultado-pruebas.txt)

## 8. Ejecución reproducible

### 8.1 Requisitos

- Git.
- Docker con Compose, para PostgreSQL 17 (`docker-compose.yml`, puerto local 55432).
- `uv` 0.11 o posterior; instala Python 3.14 por sí mismo (`backend/.python-version`, `backend/pyproject.toml`, `backend/uv.lock`).
- Chromium para Playwright, solo para las pruebas de navegador (se instala en 8.6).

### 8.2 Preparar dependencias

```bash
git clone https://github.com/jyeanaqs262/repogrp10.git
cd repogrp10
git checkout entrega-4-final
docker compose up -d --wait postgres
cd backend
uv sync
```

### 8.3 Configurar

La aplicación lee la configuración del entorno del proceso; no carga archivos `.env`. `backend/.env.example` documenta todas las variables con sus valores por defecto. Para la demostración local basta con la dirección de la base, que usa la contraseña pública de demostración del rol `royexa_app` creada por la migración (no es un secreto):

```bash
export ROYEXA_LEDGER_URL=postgresql://royexa_app:royexa_app@localhost:55432/royexa
uv run python -m royexa.migrate
```

### 8.4 Iniciar

```bash
uv run uvicorn royexa.main:app --port 8000
```

Abra <http://localhost:8000/web/> (cobrador) o <http://localhost:8000/web/admin> (administrador). La salud se consulta en <http://localhost:8000/health>.

### 8.5 Cargar datos de demostración

```bash
# No requiere un comando: con ROYEXA_SEED=demo (valor por defecto) el arranque siembra
# usuarios, rutas, clientes y préstamos de demostración; repetir el arranque no duplica nada.
# Usuarios: cobrador-1, cobrador-2, admin-1, admin-2. Contraseña pública: demo-<usuario>-royexa
```

La caja del cobrador solo existe en días de cobranza (lunes a sábado) en la zona de `ROYEXA_TIMEZONE` (por defecto `UTC`); un domingo los pagos y el cierre responden que no hay caja.

### 8.6 Ejecutar pruebas

```bash
uv run playwright install chromium   # una vez, para las pruebas de navegador
uv run pytest -m ""                   # todas, incluidas las de PostgreSQL y Playwright
uv run pytest                         # solo las que no necesitan PostgreSQL
```

### 8.7 Ejecutar la demostración principal

```text
1. Ingrese como cobrador-1 en http://localhost:8000/web/ y solicite en «Solicitar desembolso»
   100,00 para «Cliente sin prestamos» (cliente-1), 20 días, 20 cuotas.
2. En otra ventana privada ingrese como admin-1 en http://localhost:8000/web/admin y apruebe
   la solicitud en «Solicitudes».
3. Espere hasta 30 s (o pulse «Reintentar envío» en «Avisos»): la terminal del servidor imprime
   [EXT-05] ... kind=CODIGO_CONFIRMACION ... payload={'code': '...'}; ese es el código del cliente.
4. Como cobrador-1, abra la solicitud y valide el código: el desembolso queda confirmado.
5. En «Ruta del día», registre un pago en efectivo de 3,00 sobre el préstamo nuevo (19,5 de 20)
   y un pago de 700,00 sobre el préstamo de «Cliente con saldo pendiente».
6. En «Cierre», entregue 578,00: el cierre muestra un descuadre de -25,00.
7. Como admin-1, consulte «Descuadres», «Libro» y el panel de inicio.
```

Variante del notificador caído (escenario 2.2 A): detenga el servidor y arránquelo con

```bash
ROYEXA_NOTIFIER_FAILING=1 uv run uvicorn royexa.main:app --port 8000
```

registre un pago y abra «Avisos» como `admin-1`: el comprobante aparece pendiente con su motivo y, tras cinco rondas (unos 2,5 minutos con el intervalo de 30 s), fallido y contado en el menú. El mismo recorrido por HTTP, sin base de datos y con el despacho manual, es el que registra `evidencias/notificador-caido.txt`.

El despliegue de un piloto en la nube (`render.yaml`, `docs/04-operacion/guia-de-despliegue.md`) existe como trabajo adicional y no forma parte de la demostración del curso, que es local.

## 9. Deuda técnica y riesgos residuales

| ID | Deuda o riesgo | Impacto | Motivo de aceptación | Próxima acción |
|---|---|---|---|---|
| DT-01 | `POST /v1/loans/{loan_id}/payments` no tiene clave de idempotencia: un cliente JSON que reintenta tras perder la respuesta registra el pago dos veces | M | La web, que es la entrada del cobrador, ya está protegida por fichas de un solo uso por formulario (`backend/tests/web/test_t7a_form_tokens.py`, `backend/tests/e2e/test_t7d_phone_flow.py::test_t7d_a_second_tap_on_the_payment_button_sends_the_form_once`); la idempotencia formal no se exige (sección 6 del enunciado). Registrado en `ADR-004` | Aceptar una cabecera `Idempotency-Key` y guardarla con el pago |
| DT-02 | El puerto `Notifier` no impone plazo ni valida respuesta; una excepción distinta de `NotifierUnavailable` corta la ronda sin contar el intento (HV-06, RA-11) | M | El simulado no tarda ni responde; ningún caso mueve dinero y el aviso sigue visible como pendiente | Con el proveedor real: tiempo de espera en el adaptador y tratar cualquier fallo como un intento fallido |
| DT-03 | Entrega de avisos de al menos una vez y por sondeo cada 30 s | B | El cliente puede recibir un comprobante tarde o repetido, nunca un dinero distinto | Pasar `message_id` al proveedor real para descartar duplicados |
| DT-04 | Un código vencido sin intento no caduca solo (HV-08) | B | No libera dinero; solo deja un desembolso `APROBADO` aparentemente vigente | Barrido periódico en el mismo bucle de fondo |
| DT-05 | Notificador simulado: el código aparece en la salida del servidor | M | `RES-03`: no hay proveedor contratable; es el papel del simulado en la demostración | Adaptador real detrás de `Notifier` (EV-08 ya probó la sustitución) |
| DT-06 | El rol propietario de la base puede alterar el libro (RA-02) | M | Roles separados y credenciales de migración fuera de la aplicación; ALT-01C sería más costosa | Evaluar la cadena de hashes (ALT-01C) si el producto sale de la demostración |
| DT-07 | `InMemoryUnitOfWork` es también la unidad de trabajo del modo PostgreSQL (delega en `PostgresSession`) y `backend/src/royexa/migrate.py` reaplica todos los archivos en cada arranque, sin tabla de control | B | Funciona y está probado (PR-07, `test_pr07_migrations_are_repeatable`); renombrar no cambia el comportamiento | Extraer una unidad de trabajo propia del modo PostgreSQL y una tabla de migraciones aplicadas |
| DT-08 | Sin operación sin conexión ni aplicación nativa | M | Excluidas por la Entrega 1; `ADR-003` rechazado | Retomar `ADR-003` solo si el cliente lo exige |
| DT-09 | El piloto en Render usa el plan gratuito, que se duerme tras unos 15 minutos sin tráfico; mientras duerme no corre el bucle de avisos | B | El despliegue no es requisito del curso; un flujo programado consulta `/health` cada 10 minutos | Plan pagado o trabajador separado si el piloto pasa a producción |
| DT-10 | La confirmación docente de las resoluciones `DIV-01` a `DIV-07` (en particular `DIV-02`, base del rechazo de `ADR-003`) no está registrada en el repositorio | B | Las resoluciones siguen el alcance de la Entrega 1 y el enunciado de la Entrega 4 no exige operación sin conexión; así lo declaran `ADR-003` y `ADR-004` | Anexar la constancia si el docente la emite |

## 10. Conclusiones

- **Decisión técnica más importante:** garantizar la inalterabilidad del libro con privilegios de la base de datos y un único módulo escritor (`ADR-001`), y confirmar todo el estado en la misma transacción. El control antifraude no depende de la disciplina del código.
- **Evidencia que más cambió el diseño:** HV-07 (Entrega 3): tras reiniciar, el libro conservaba un asiento cuya caja y desembolso se habían perdido en memoria. Llevó todo el estado a PostgreSQL en la transacción del libro, cerró RA-10 y permitió aceptar `ADR-002` y `ADR-004`.
- **Principal trade-off aceptado:** consistencia eventual y entrega de al menos una vez en los avisos a cambio de que un fallo del canal nunca toque el dinero (bandeja de salida, `ADR-002`).
- **Siguiente incremento recomendado:** conectar un proveedor real detrás de `Notifier` con plazo, validación de respuesta e identificador de mensaje (DT-02, DT-03, DT-05), y añadir la clave de idempotencia a la API JSON de pagos (DT-01).

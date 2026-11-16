# Trazabilidad final

Esta matriz continúa `docs/01-requisitos/requisitos.md` (RF, CA, RN, EC, ASR, RES), `docs/02-arquitectura/trazabilidad-arquitectonica.md` (AD, ADR, CON, EXT, RA, EV) y `docs/03-diseno-vertical/trazabilidad-implementacion.md` (UC, CMP, CTR, PR, HV). PR-01 a PR-11 se definen en `docs/03-diseno-vertical/diseno-y-vertical.md`, sección 6.1; PR-12 a PR-16, PAT-01 a PAT-06, EA-01, EA-02 y DT-01 a DT-10 se definen en [`entrega-final.md`](entrega-final.md). Las rutas de código son relativas a la raíz del repositorio.

## 1. Matriz de cobertura

| Requisito o escenario | Reglas | Decisiones / ADR | Componentes / contratos | Código | Pruebas | Evidencia | Estado |
|---|---|---|---|---|---|---|---|
| RF-01 / CA-01, CA-02 | RN-01 | AD-05; ADR-001 | CMP-04, CMP-05, CMP-06 / CTR-05, CTR-06, CTR-07 | `backend/src/royexa/loans/application.py`, `backend/src/royexa/loans/domain.py` | PR-13; `backend/tests/vertical/test_t3a_payments.py`, `backend/tests/vertical/test_t3b_visits.py`, `backend/tests/postgres/test_t3a_payments_persistence.py` | EV-10; `evidencias/escenario-principal.txt` | Completo |
| RF-02 / CA-03, CA-04 | RN-02, RN-04 | ADR-001; decisión T5-P1 | CMP-06, CMP-16 / CTR-07 | `backend/src/royexa/closing/application.py`, `backend/src/royexa/cash_box/domain.py` | PR-14; `backend/tests/vertical/test_t5c_panels.py`, `backend/tests/postgres/test_t5b_cash_close_persistence.py`; PR-12 | `evidencias/escenario-principal.txt` | Completo |
| RF-03 / CA-05, CA-06 | RN-03, RN-05, RN-06 | AD-03, AD-06; ADR-004, ADR-002 | CMP-02, CMP-03, CMP-04, CMP-05 / CTR-01, CTR-02, CTR-04, CTR-11 | `backend/src/royexa/sales/application.py`, `backend/src/royexa/sales/domain.py` | PR-01, PR-02, PR-03, PR-04, PR-05, PR-09, PR-10, PR-11; `backend/tests/vertical/test_t10a_code_attempts.py`; `backend/tests/e2e/test_t8_admin_approval.py` | EV-11, EV-12; `evidencias/escenario-principal.txt` | Completo |
| RF-04 / CA-07, CA-08 | RN-04 | AD-01; ADR-001 | CMP-05, CMP-10, CMP-13, CMP-16 / CTR-05, CTR-12 | `backend/src/royexa/ledger/posting.py`, `backend/migrations/001_ledger.sql`, `backend/migrations/011_adjustments.sql` | PR-07, PR-16; `backend/tests/vertical/test_t5d_adjustments.py`, `backend/tests/web/test_t14a_adjustments.py` | EV-01, EV-02; `evidencias/evaluacion-ea-01.txt` | Completo |
| RF-05 / CA-09, CA-10 | RN-01, RN-05 | AD-02; ADR-004 | CMP-04, CMP-15 / CTR-06 | `backend/src/royexa/clients/application.py`, `backend/src/royexa/loans/domain.py` | PR-04; `backend/tests/vertical/test_t2a_clients.py`, `backend/tests/vertical/test_t2b_loans.py`, `backend/tests/web/test_t13_client_loan.py` | `evidencias/escenario-principal.txt` | Completo; CA-09 por el camino del desembolso (sin alta directa de préstamos) |
| RF-06 / CA-11, CA-12 | RN-03 | AD-02, AD-07; ADR-002 | CMP-08, CMP-11, CMP-17 / CTR-03, CTR-08, CTR-09, CTR-10 | `backend/src/royexa/shared/outbox.py`, `backend/src/royexa/notifications/dispatcher.py`, `backend/src/royexa/background.py` | PR-06, PR-15; `backend/tests/shared/test_t10a_background_dispatch.py`, `backend/tests/web/test_t12_notices.py` | EV-03, EV-08; `evidencias/notificador-caido.txt` | Completo con `EXT-05` simulado |
| RF-07 / CA-13 | RN-02 | Decisiones T9-P1 a T9-P4 | CMP-16, CMP-14 | `backend/src/royexa/closing/application.py`, `backend/src/royexa/web/charts.py` | `backend/tests/vertical/test_t9_discrepancies.py`, `backend/tests/web/test_t9_discrepancy_page.py`, `backend/tests/web/test_t14b_panel.py` | `evidencias/escenario-principal.txt` | Completo |
| EC-01 | RN-04 | AD-01; ADR-001 | CMP-05, CMP-10 / CTR-05 | `backend/migrations/001_ledger.sql`, `backend/src/royexa/adapters/postgres_ledger.py` | PR-07, PR-16 | EV-01, EV-02; EA-01; `evidencias/evaluacion-ea-01.txt` | Completo |
| EC-02 | RN-06 | AD-06; ALT-06B | CMP-01, CMP-03 / CTR-01 | `backend/src/royexa/sales/domain.py` | PR-02 | EV-11; `evidencias/escenario-principal.txt` | Completo |
| EC-03 | RN-01 | AD-05 | CMP-04 | `backend/src/royexa/loans/domain.py` | PR-13 | EV-10; `evidencias/evaluacion-ea-01.txt` | Completo |
| EC-04 | RN-03 | AD-02, AD-07; ADR-002 | CMP-08, CMP-11, CMP-17 / CTR-10 | `backend/src/royexa/notifications/dispatcher.py`, `backend/src/royexa/adapters/simulated_notifier.py` | PR-06, PR-15 | EV-03, EV-08; EA-02; `evidencias/notificador-caido.txt` | Completo |
| ASR-01 a ASR-05 | RN-01, RN-03, RN-04, RN-06 | AD-01, AD-02, AD-03, AD-05, AD-06 | CON-03, CON-04, EXT-05 | `backend/src/royexa/` | PR-01 a PR-16 | EV-01 a EV-03, EV-08 a EV-12 | Completo |

## 2. Patrones y problemas de diseño

| Patrón | Problema | Elementos | Decisión relacionada | Pruebas / evidencia |
|---|---|---|---|---|
| PAT-01 Repository y Unit of Work | Confirmar juntas varias entidades del dinero y probar las reglas con y sin PostgreSQL | CMP-09, CMP-10; `backend/src/royexa/sales/ports.py`, `backend/src/royexa/adapters/memory.py`, `backend/src/royexa/adapters/postgres_state.py`, `backend/src/royexa/adapters/postgres_ledger.py` | ADR-001, ADR-004; RA-10 | PR-05, PR-07; `backend/tests/postgres/test_t1a_persistence.py`; EV-12 |
| PAT-02 Adapter (puertos y adaptadores) | Canal real no disponible (RES-03) y fallo reproducible (EC-04) | CMP-11 / CTR-10; `backend/src/royexa/notifications/ports.py`, `backend/src/royexa/adapters/simulated_notifier.py`, `backend/src/royexa/bootstrap.py` | ADR-002; AD-07 | PR-06; EV-08 |
| PAT-03 Transactional Outbox | Un fallo del aviso no debe tocar el dinero ni pasar inadvertido | CMP-08, CMP-17 / CTR-08, CTR-09; `backend/src/royexa/shared/outbox.py`, `backend/src/royexa/notifications/dispatcher.py`, `backend/src/royexa/background.py` | ADR-002; RA-03, RA-11 | PR-06, PR-15; EV-03; `evidencias/notificador-caido.txt` |
| PAT-04 Service Layer | La API y la web invocan las mismas operaciones sin duplicar reglas | CMP-02, CMP-16 / CTR-02; `backend/src/royexa/sales/application.py`, `backend/src/royexa/loans/application.py`, `backend/src/royexa/closing/application.py` | AD-06; ADR-004 | PR-01 a PR-05; `backend/tests/web/test_t12_notices.py` |
| PAT-05 Composition Root con fábrica | Elegir adaptadores, reloj y siembra sin que los módulos lo sepan | CMP-12; `backend/src/royexa/bootstrap.py`, `backend/src/royexa/main.py` | ADR-001, ADR-002 | PR-08; `backend/tests/shared/test_t10b_pilot_seed.py` |
| PAT-06 Strategy no aplicado | Dos medios de pago que solo difieren en el efecto de caja | CMP-04, CMP-05; `backend/src/royexa/shared/payments.py`, `backend/src/royexa/ledger/posting.py` | RES-01 | `backend/tests/vertical/test_t3a_payments.py`, `backend/tests/vertical/test_t5b_cash_close.py` |

## 3. Integración

| Sistema externo | Propósito | Componente / contrato | Fallo considerado | Prueba / evidencia | Estado |
|---|---|---|---|---|---|
| EXT-05 | Entregar al cliente final el código del desembolso y los comprobantes (RF-06, RES-05) | CMP-08, CMP-11, CMP-17 / CTR-08, CTR-09, CTR-10 | Indisponibilidad: 5 intentos y `FALLIDO` visible. Demora y respuesta inválida: sin plazo ni validación en el contrato; una excepción ajena corta la ronda sin perder el aviso (DT-02) | PR-06, PR-15 / EV-03, EV-08; `evidencias/notificador-caido.txt` | Simulada |

## 4. ADR y evidencia final

| ADR | Estado inicial | Evidencia obtenida | Estado final | Consecuencia |
|---|---|---|---|---|
| ADR-001 | Propuesto | EV-01, EV-02 (PR-07); HV-01, HV-02, HV-03, HV-07; asiento `AJUSTE` (`backend/tests/vertical/test_t5d_adjustments.py`) | Aceptado | El libro solo admite inserciones por privilegios; las correcciones son asientos compensatorios; RA-10 cerrado |
| ADR-002 | Propuesto | EV-03, EV-08, EV-09, EV-11 (PR-06, PR-08, PR-02); HV-05, HV-06, HV-07, HV-09 | Aceptado | Monolito modular con bandeja de salida en PostgreSQL y despacho en segundo plano; RA-11 sigue abierto (DT-02, DT-03) |
| ADR-003 | Propuesto | EV-05 y EV-06 reprogramadas sin destino; DIV-02 resuelta a favor de la Entrega 1 | Rechazado (reemplazado por ADR-004) | Sin operación sin conexión ni aplicación nativa; RA-05 y RA-06 cerrados |
| ADR-004 | Propuesto | EV-12 (PR-05, PR-07, `backend/tests/postgres/test_t1b_disbursements.py`); HV-04, HV-07; fichas de un solo uso (`backend/tests/web/test_t7a_form_tokens.py`) | Aceptado | Operación en línea con confirmación idempotente; la API JSON de pagos sin clave de idempotencia queda como riesgo residual (DT-01) |

## 5. Elementos sin cobertura

| Elemento | Motivo | Riesgo | Decisión tomada |
|---|---|---|---|
| CON-01, operación sin conexión (ADR-003, EV-05, EV-06, RA-09) | Excluida por la Entrega 1 (DIV-02) | Sin señal no se registra el cobro | Excluir |
| AD-04, INV-03, EV-07 (varias empresas) | Excluido por la Entrega 1 (DIV-03) | Ninguno con una sola empresa | Diferir |
| CON-05 (almacén de fotos) | Fuera de la línea base de la Entrega 1 | Sin respaldo fotográfico | Excluir |
| EV-04, SUP-03 (rendimiento con dos tareas) | La demostración es local; sin carga real | Tiempos no medidos | Diferir |
| RA-02 (rol propietario puede alterar el libro) | La alternativa ALT-01C es más costosa | Alteración por un administrador de la base | Mitigar con roles separados (DT-06) |
| RA-11, HV-06 (excepción ajena del notificador, entrega al menos una vez, sin plazo) | El simulado no la produce | Aviso repetido o retrasado, sin efecto en el dinero | Mitigar con el proveedor real (DT-02, DT-03) |
| HV-08 (caducidad sin intento) | Sin barrido periódico | Desembolso abandonado que parece vigente, sin mover dinero | Diferir (DT-04) |
| Lectura literal de CA-09 (alta directa de préstamos por el administrador) | RN-03 hace nacer el préstamo al confirmar el desembolso | Ninguno para el control antifraude | Mitigar: CA-09 se cumple por el camino del desembolso |
| Idempotencia de `POST /v1/loans/{loan_id}/payments` | No exigida por el enunciado; la web está protegida | Pago duplicado por un cliente JSON que reintenta | Diferir (DT-01) |

## 6. Consistencia

- [x] Los identificadores de Entregas 1 a 3 existen y conservan su significado.
- [x] Cada funcionalidad declarada como completa tiene código y prueba o evidencia.
- [x] Cada patrón declarado existe en el código.
- [x] C4, secuencias, componentes, contratos y código son coherentes.
- [x] Los ADR afectados contienen historial y estado final.
- [x] Cada ruta y comando documentado existe en el commit evaluable.
- [x] Los elementos parciales o excluidos están declarados explícitamente.

Comprobación (2026-11-16): las rutas entre comillas invertidas de `entrega-final.md` y de este documento se verificaron con `test -e` desde la raíz del repositorio; los identificadores se buscaron en sus documentos de origen; los comandos de la sección 8 de `entrega-final.md` se ejecutaron en la máquina del autor con PostgreSQL 17 en Docker. La coherencia entre C4, secuencias y código se revisó por lectura en la consolidación del modelo (commit `12c2f1e`) y la sostienen PR-08 y las pruebas de cada componente.

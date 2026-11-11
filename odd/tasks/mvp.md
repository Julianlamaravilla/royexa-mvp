# Feature: mvp

Objetivo: llevar ROYEXA desde el recorrido vertical de la Entrega 3 hasta un MVP usable desde el navegador del celular, con el alcance de la Entrega 1 (`docs/01-requisitos/requisitos.md`, sección 1.4).
Problema: hoy solo existe el desembolso por API. El libro vive en PostgreSQL, pero desembolsos, préstamos, cajas y avisos están en memoria. No hay interfaz, pagos ni cierre de caja.
Repositorio de trabajo: `Julianlamaravilla/royexa-mvp`, rama base `mvp`. El repositorio del curso (`jyeanaqs262/repogrp10`) solo recibe las entregas, sincronizadas a mano.

## Reglas para cada sesión

1. Leer este archivo completo y tomar la primera tarea sin marcar, en orden. No saltar tareas.
2. Crear una rama `tasks/<id>-<nombre-corto>` desde `mvp` actualizada (no `mvp/...`: Git no permite ese prefijo mientras exista la rama `mvp`).
3. Probar primero: escribir la prueba que falla, implementar, refactorizar con las pruebas en verde.
4. Antes de abrir el pull request, ejecutar desde `backend/`: `uv run pytest -m ""`. Todas deben pasar.
5. Abrir un pull request hacia `mvp`, uno por tarea. El merge lo hace el usuario.
6. En el mismo pull request: marcar la casilla, anotar en «Evidencia» el número de pruebas y lo que quedó pendiente.
7. Commits convencionales, sin atribución de IA. Código e identificadores en inglés; documentos en español, como el resto del repositorio.
8. No borrar ni renumerar identificadores existentes (RF, RN, CA, EV, PR, ADR, HV).
9. Fuera de alcance del MVP, salvo que el usuario lo autorice: app nativa, operación sin conexión, varias empresas, proveedor real de notificaciones, cualquier servicio de nube de pago.
10. Si una tarea no cabe en un pull request revisable (unas 400 líneas de autor), dividirla en subtareas `T<n>a`, `T<n>b` en este archivo y hacer solo la primera.
11. Si falta una decisión de producto, no suponerla: dejarla en «Preguntas abiertas» y detenerse.

PostgreSQL: el repositorio usa `docker compose up -d --wait postgres`. Si la sesión no tiene Docker, instalar PostgreSQL 17 en la máquina de la sesión y exponerlo en el puerto 55432 con la base `royexa` y el usuario `royexa_migrator` de `docker-compose.yml`; la migración crea `royexa_app`. Documentar en la evidencia qué camino se usó.

## Tareas

- [x] **T0 Integración continua.** Workflow de GitHub Actions que, en cada pull request hacia `mvp`, levanta PostgreSQL 17 como servicio y ejecuta `uv run pytest -m ""` desde `backend/`.
  - Acepta: el workflow corre en el pull request de esta misma tarea y pasa con las 70 pruebas actuales.
- [x] **T1a Persistencia: cajas, préstamos, excepciones y avisos.** Migración `002` y adaptadores PostgreSQL para cajas, préstamos con su calendario, excepciones de renovación y avisos (bandeja de salida), dentro de la misma transacción del libro. Los desembolsos siguen en memoria hasta T1b.
  - Acepta: tras reiniciar el servidor, el préstamo, la caja y los avisos de un desembolso confirmado siguen consultables; dos transacciones que cambian la misma caja no se pisan; las pruebas con PostgreSQL pasan.
- [x] **T1b Persistencia: desembolsos.** Adaptador PostgreSQL para desembolsos (con sus intentos de aprobación rechazados y el código en forma de huella), migración `003`, y retirada del almacén en memoria del camino con PostgreSQL.
  - Acepta: tras reiniciar el servidor, un desembolso confirmado, su préstamo y la caja siguen consultables; las pruebas verticales pasan contra PostgreSQL; el README elimina la limitación de memoria.
- [x] **T2a Clientes (RF-05).** Alta de clientes por el administrador (nombre y ruta) y consulta de uno y de la lista, guardados en PostgreSQL con migración `004`. Sustituye el catálogo sembrado en memoria; los cuatro clientes de demostración se siembran en la base.
  - Acepta: solo el administrador da de alta; una ruta inexistente o un nombre vacío se rechazan; un cliente nuevo puede recibir un desembolso; tras reiniciar el servidor el cliente sigue consultable.
- [x] **T2b Préstamos y calendario (RF-05, CA-09, CA-10).** Consulta de un préstamo con su calendario de cuotas y de los préstamos de un cliente.
  - Acepta: CA-09 y CA-10 tienen una prueba cada uno, con un cliente dado de alta por la API.
- [x] **T3a Pago en ruta (RF-01, RN-01, CA-01, EC-03).** Registro de pago en efectivo o por transferencia sobre un préstamo, imputado a las cuotas más antiguas primero, sin exceder el saldo y con contador fraccionario exacto; cada pago genera su asiento en el libro (migración `006`). Solo el efectivo suma a la caja.
  - Acepta: CA-01 y EC-03 tienen prueba (25 sobre una cuota de 50 deja 19,5 cuotas de 20, también como cálculo puro); el pago es consultable con la identidad del cobrador; dos pagos simultáneos no se pisan.
- [x] **T3b No pago y pendientes de visita (RF-01, CA-02, T3-P1, T3-P2).** Registro de no pago con motivo y fecha de compromiso, y consulta de los clientes pendientes de visita del cobrador.
  - Acepta: CA-02 tiene prueba; las decisiones T3-P1 y T3-P2 están aplicadas tal como se resolvieron.
- [ ] **T4 Comprobante del pago (RF-06).** Cada pago emite un aviso con importe, saldo restante y próximo vencimiento, por el notificador simulado y con el mismo patrón de bandeja de salida del desembolso.
  - Acepta: los criterios de RF-06 tienen prueba; un fallo del notificador no pierde el aviso.
- [ ] **T5 Cierre de caja (RF-02, RN-02).** Cierre diario en tres paneles (pendientes, pagaron, no pagaron) con diferencia entre lo registrado y lo entregado; solo sin pendientes e irreversible.
  - Acepta: los criterios de RF-02 tienen prueba; un ajuste posterior al cierre exige un asiento nuevo.
- [ ] **T6 Inicio de sesión.** Sustituir la cabecera `X-Actor-Id` por usuario y contraseña con sesión, conservando los roles de cobrador y administrador y la regla RN-06.
  - Acepta: sin sesión válida la API responde 401; las pruebas existentes de RN-06 siguen pasando; contraseñas guardadas con hash.
- [ ] **T7 Web del cobrador.** Páginas generadas en el servidor y usables en un celular: ruta del día, registrar pago o no pago, solicitar desembolso, validar el código del cliente y cerrar la caja.
  - Acepta: el flujo completo funciona en un ancho de 360 px; una prueba de extremo a extremo cubre pago y cierre.
- [ ] **T8 Web del administrador.** Aprobar o rechazar desembolsos, consultar el libro, los clientes y las cajas cerradas.
  - Acepta: una prueba de extremo a extremo cubre la aprobación de un desembolso.
- [ ] **T9 Descuadres del periodo (RF-07).** Consulta del número de descuadres del periodo y su evolución.
  - Acepta: los criterios de RF-07 tienen prueba; esta es la métrica de éxito propuesta para el piloto.
- [ ] **T10 Despliegue.** Pendiente de autorización del usuario: proveedor de base de datos, hospedaje, cuenta y secretos. No empezar sin ella.

## Preguntas abiertas

- Ninguna por ahora.

## Decisiones resueltas

- **T3-P1. Pendiente de visita** (decidido por el usuario, opción recomendada): cada día de cobranza (lunes a sábado), todo cliente de la ruta con un préstamo `ACTIVO` es pendiente hasta que el cobrador registra un pago o un no pago ese día. Un cliente sin préstamo activo nunca es pendiente. Afecta a T3b, T5 y T7.
- **T3-P2. Fecha de compromiso** (decidido por el usuario, opción recomendada): obligatoria y posterior al día del registro; solo se guarda y se consulta, no vuelve pendiente a nadie ni cambia el saldo.
- Resuelto con los documentos, sin pregunta: el medio de pago es efectivo o transferencia y solo el efectivo suma a la caja (arquitectura, «Caja»); el pago se imputa a las cuotas más antiguas primero y nunca excede el saldo (RN-01, «Pago»); cada pago genera su asiento en el libro.

## Evidencia

- Punto de partida: commit `3677409` en `mvp`, 70 pruebas (52 sin PostgreSQL, 18 con PostgreSQL), según `backend/README.md`.
- T0: `.github/workflows/ci.yml` ejecuta `uv run pytest -m ""` en cada pull request hacia `mvp`, con PostgreSQL 17 como servicio en el puerto 55432. Local: 70 pruebas en verde contra PostgreSQL 16 instalado en la máquina (la sesión no tiene daemon de Docker y no había 17). En el propio pull request el workflow pasó con PostgreSQL 17 (todos los pasos en verde, incluido `uv run pytest -m ""`). Pendiente: nada. Nota: la rama es `mvp-t0-ci`, no `mvp/t0-ci`, porque Git no permite crear `mvp/...` mientras exista la rama `mvp`.
- T1a: migración `002_state.sql` y `adaptadores/postgres_state.py` (cajas con escritura optimista por versión, préstamos con calendario, excepciones y avisos) en la misma transacción del libro. 79 pruebas en verde con `uv run pytest -m ""` (52 sin PostgreSQL, 27 con PostgreSQL: 9 nuevas de T1a). PostgreSQL 16 instalado en la máquina de la sesión (sin daemon de Docker); la CI lo ejecuta con PostgreSQL 17. Las pruebas del PR-07 sobre privilegios y migraciones se ajustaron para declarar los permisos de las tablas nuevas (insertar y actualizar, nunca borrar). El PR pasa de las 400 líneas de autor por poco (unas 480 con pruebas); no se dividió más porque el adaptador y su prueba de reinicio no tienen sentido por separado. Pendiente: T1b (desembolsos). Rama `mvp-t1a-persistence`, por la misma razón de T0.
- T1b: migración `003_disbursements.sql` y `PostgresDisbursementRepository` (escritura optimista por versión; los intentos de aprobación rechazados solo se añaden). Con la base configurada el almacén en memoria ya no interviene. 131 pruebas en verde con `uv run pytest -m ""` (52 sin PostgreSQL, 79 con PostgreSQL), repetidas cuatro veces sin intermitencias. Las pruebas verticales ahora corren contra los dos adaptadores (fixture `backend`). PostgreSQL 16 en la máquina de la sesión; la CI usa 17.
  - Hallazgo: con el aislamiento por defecto (READ COMMITTED) el perdedor de una carrera veía el préstamo del ganador y RN-05 lo rechazaba en vez de repetir y devolver el resultado confirmado. Se pasó a `REPEATABLE READ` y los fallos de serialización se convierten en `StaleWrite`. La prueba PR-05 se reescribió para valer con ambos adaptadores (su versión anterior dependía de la copia en memoria).
  - Pendiente: nada de T1. Siguiente: T2.
- T2a: migración `004_clients.sql`, módulo `clients` con alta (`RegisterClient`), consulta (`ClientQueries`) y repositorios en memoria y PostgreSQL; `POST /v1/clients`, `GET /v1/clients` y `GET /v1/clients/{id}`. El catálogo sembrado deja de existir: los clientes viajan en la unidad de trabajo y se siembran en la base. 147 pruebas en verde con `uv run pytest -m ""` (59 sin PostgreSQL, 88 con PostgreSQL), tres corridas sin intermitencias. PostgreSQL 16 en la máquina de la sesión; la CI usa 17. Un cliente tiene nombre y ruta: no se modelan teléfono ni documento porque el notificador es simulado (EXT-05); se decidirá al llegar el proveedor real. Pendiente: T2b (préstamos y calendario). Rama `tasks/t2a-clients`.
- T2b: `GET /v1/loans/{id}` y `GET /v1/clients/{id}/loans` (casos de uso `LoanQueries`), con `client_id` y `status` (`ACTIVO` o `LIQUIDADO`) en la respuesta del préstamo; migración `005_loan_order.sql` para listar los préstamos en el orden en que se concedieron. CA-09 y CA-10 tienen una prueba cada uno, con un cliente dado de alta por la API (`tests/vertical/test_t2b_loans.py`), que corre con ambos adaptadores. 159 pruebas en verde con `uv run pytest -m ""` (65 sin PostgreSQL, 94 con PostgreSQL), tres corridas sin intermitencias. PostgreSQL 16 en la máquina de la sesión; la CI usa 17.
  - Interpretación a confirmar: CA-09 dice «el administrador registra un préstamo». El plan de T2 pide solo consultar préstamos y RN-03 establece que un préstamo nace al confirmar un desembolso, así que no hay alta directa de préstamos: el calendario se deriva al confirmar y CA-09 se prueba por ese camino. CA-10 ya lo cubría el flujo de desembolso (PR-04); aquí se prueba con un cliente nuevo.
  - Pendiente: nada de T2. Siguiente: T3.
- T3a: `Loan.apply_payment` (cuotas más antiguas primero, el excedente a la siguiente, nunca más que el saldo) y contador fraccionario exacto (`Fraction`; `exact_decimal` devuelve `19.5` o una fracción como `113/6`, sin redondeo); `Payment`, `RegisterPayment` y `PaymentQueries`; asiento `PAGO` en el libro con `payment_id` y `payment_method` (solo el efectivo suma a la caja); `POST` y `GET /v1/loans/{id}/payments`; migración `006_payments.sql` (relaja `disbursement_id`, permite `PAGO` con una restricción que exige exactamente uno de los dos identificadores, y crea `payment` y `payment_allocation`, solo de inserción). 190 pruebas en verde con `uv run pytest -m ""` (85 sin PostgreSQL, 105 con PostgreSQL), tres corridas completas y doce de la prueba de concurrencia sin intermitencias. PostgreSQL 16 en la máquina de la sesión; la CI usa 17. Rama `tasks/t3a-payments`.
  - Tamaño: unas 490 líneas de código y SQL y 343 de pruebas, por encima de las 400 de la regla 10. No se separó porque las pruebas de pago corren contra los dos adaptadores: la mitad sin PostgreSQL fallaría en la CI.
  - Dos pagos simultáneos sobre el mismo préstamo: uno gana y el otro recibe 409 (conflicto de escritura) para reintentar; nunca se pierde una actualización. No hay clave de idempotencia: un doble toque secuencial registra dos pagos. Queda como mejora para T7 (web del cobrador), donde aparece el riesgo.
  - Pendiente: T3b (no pago y pendientes de visita, con T3-P1 y T3-P2). El API del libro ahora devuelve `disbursement_id` nulo en los asientos de pago.
- T3b: `NonPayment` (motivo obligatorio, fecha de compromiso posterior al día del registro según T3-P2, solo el cobrador de la ruta, solo sobre un préstamo con saldo), `RegisterNonPayment` y `VisitQueries`; `POST` y `GET /v1/loans/{id}/non-payments` y `GET /v1/routes/{id}/pending-visits?date=` con la regla T3-P1 (lunes a sábado, cliente de la ruta con préstamo activo sin pago ni no pago ese día; el domingo, nadie); migración `007_non_payments.sql` (solo inserción). CA-02 tiene prueba, y T3-P1 y T3-P2 tienen las suyas (`tests/vertical/test_t3b_visits.py`, con ambos adaptadores, y un reinicio en PostgreSQL). 215 pruebas en verde con `uv run pytest -m ""` (97 sin PostgreSQL, 118 con PostgreSQL), tres corridas sin intermitencias. PostgreSQL 16 en la máquina de la sesión; la CI usa 17. Rama `tasks/t3b-non-payments`.
  - El día de un registro se cuenta en UTC (fecha del reloj del servidor). Si el piloto opera en otra zona horaria, la frontera del día se desplaza; queda para T5, que define el día de la caja.
  - El cálculo de pendientes consulta pagos y no pagos cliente por cliente; basta para una ruta, y se optimiza si T7 lo pide.
  - Pendiente: nada de T3. Siguiente: T4.

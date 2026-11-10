# Feature: mvp

Objetivo: llevar ROYEXA desde el recorrido vertical de la Entrega 3 hasta un MVP usable desde el navegador del celular, con el alcance de la Entrega 1 (`docs/01-requisitos/requisitos.md`, sección 1.4).
Problema: hoy solo existe el desembolso por API. El libro vive en PostgreSQL, pero desembolsos, préstamos, cajas y avisos están en memoria. No hay interfaz, pagos ni cierre de caja.
Repositorio de trabajo: `Julianlamaravilla/royexa-mvp`, rama base `mvp`. El repositorio del curso (`jyeanaqs262/repogrp10`) solo recibe las entregas, sincronizadas a mano.

## Reglas para cada sesión

1. Leer este archivo completo y tomar la primera tarea sin marcar, en orden. No saltar tareas.
2. Crear una rama `mvp/<id>-<nombre-corto>` desde `mvp` actualizada.
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
- [ ] **T1 Persistencia completa.** Adaptadores PostgreSQL para desembolsos, préstamos, cajas y avisos, con migraciones nuevas numeradas desde `002`.
  - Acepta: tras reiniciar el servidor, un desembolso confirmado, su préstamo y la caja siguen consultables; las pruebas verticales pasan contra PostgreSQL; el README elimina la limitación de memoria.
- [ ] **T2 Clientes y préstamos (RF-05).** Alta y consulta de clientes; consulta de préstamos con su calendario de cuotas derivado de monto, plazo e interés.
  - Acepta: los criterios de aceptación de RF-05 tienen una prueba cada uno.
- [ ] **T3 Pago y no pago en ruta (RF-01, RN-01).** Registro de pago con contador fraccionario y de no pago con motivo y compromiso de pago; cada pago genera su asiento en el libro.
  - Acepta: los criterios de RF-01 tienen prueba; 25 sobre una cuota de 50 deja 19,5 cuotas de 20, como exige RN-01.
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

## Evidencia

- Punto de partida: commit `3677409` en `mvp`, 70 pruebas (52 sin PostgreSQL, 18 con PostgreSQL), según `backend/README.md`.
- T0: `.github/workflows/ci.yml` ejecuta `uv run pytest -m ""` en cada pull request hacia `mvp`, con PostgreSQL 17 como servicio en el puerto 55432. Local: 70 pruebas en verde contra PostgreSQL 16 instalado en la máquina (la sesión no tiene daemon de Docker y no había 17). Pendiente: confirmar que el workflow pasa en el propio pull request. Nota: la rama es `mvp-t0-ci`, no `mvp/t0-ci`, porque Git no permite crear `mvp/...` mientras exista la rama `mvp`.

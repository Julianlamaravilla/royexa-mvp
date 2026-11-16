# Evidencias finales

Incluyan evidencia pequeña, legible y reproducible:

- salida de pruebas en texto, XML o HTML;
- mediciones asociadas a escenarios de calidad;
- solicitudes y respuestas de ejemplo sin secretos;
- simulación de indisponibilidad o respuesta inválida del servicio externo;
- informe de inspección o experimento asociado a un ADR.

No incluyan dependencias descargadas, credenciales, `.env` reales, binarios innecesarios, capturas como única evidencia cuando exista una salida exportable ni grandes volcados de consola sin explicación.

## Índice de evidencias de ROYEXA (2026-11-16)

Se obtuvieron en la rama `entrega-4-final`, commit `12c2f1e` (la suite completa se repitió en el commit `c64db4e`, con el mismo código), con PostgreSQL 17.11 en Docker, `uv` 0.11.7 y Python 3.14.6. No contienen secretos: los usuarios y contraseñas citados son los públicos de demostración (`demo-<usuario>-royexa`), los tokens de sesión y el código de confirmación se omiten, y las rutas locales se abrevian como `<repo>/` y `~/`.

| Archivo | Qué demuestra | Relación | Cómo regenerarlo (desde `backend/` salvo indicación) |
|---|---|---|---|
| [`resultado-pruebas.txt`](resultado-pruebas.txt) | La suite completa con Chromium instalado: 1131 pruebas, 1129 pasan, 0 fallan, 2 omitidas con su motivo | Sección 7 de `entrega-final.md`; PR-01 a PR-16 | `docker compose up -d --wait postgres` (desde la raíz) y `uv run pytest -m "" -rs` |
| [`escenario-principal.txt`](escenario-principal.txt) | Solicitudes y respuestas del flujo principal: desembolso con código, pago parcial con 19,5 de 20, cierre con descuadre de −25,00 y consulta de descuadres; y las alternativas de cierre con pendientes, pago tras el cierre y autoaprobación | Secciones 2.1 y 2.2 de `entrega-final.md`; RF-01, RF-02, RF-03, RF-07; RN-01, RN-02, RN-03, RN-06; CA-01, CA-03, CA-04, CA-05, CA-13; EC-02 | `ROYEXA_DISPATCH_SECONDS=0 uv run uvicorn royexa.main:app --port 8766` y las peticiones del archivo, en el orden indicado, en un día de lunes a sábado |
| [`notificador-caido.txt`](notificador-caido.txt) | Simulación de indisponibilidad de `EXT-05`: el pago se confirma, el comprobante pasa de `PENDIENTE` a `FALLIDO` tras 5 intentos y queda visible; salida de las pruebas del fallo | EA-02; EC-04, CA-11, CA-12; PR-06, PR-15; EV-03, EV-08; `ADR-002` | `uv run pytest tests/vertical/test_pr06_notifier_failure.py tests/shared/test_t10a_background_dispatch.py tests/vertical/test_t4_payment_receipt.py -v`; y `ROYEXA_NOTIFIER_FAILING=1 ROYEXA_DISPATCH_SECONDS=0 uv run uvicorn royexa.main:app --port 8765` con las peticiones del archivo |
| [`evaluacion-ea-01.txt`](evaluacion-ea-01.txt) | Inspección del catálogo de privilegios del libro, alteración directa rechazada, asiento compensatorio y cálculo exacto de 19,5 de 20 | EA-01; EC-01, EC-03; RN-01, RN-04; CA-08; PR-07, PR-13, PR-16; EV-01, EV-02, EV-10; `ADR-001` | Consultas `psql` de la Parte 1 (desde la raíz) y `uv run pytest -m "" tests/postgres/test_pr07_ledger_privileges.py tests/postgres/test_t5d_adjustments_persistence.py tests/loans/test_t3a_payment_allocation.py tests/vertical/test_t5d_adjustments.py -v` |

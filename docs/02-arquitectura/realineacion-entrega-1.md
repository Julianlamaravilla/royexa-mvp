# Realineación de la arquitectura con la Entrega 1

- **Proyecto:** ROYEXA
- **Fecha:** 2026-10-30
- **Responsable:** Julian Andres Restrepo
- **Afecta a:** [`arquitectura.md`](arquitectura.md), [`trazabilidad-arquitectonica.md`](trazabilidad-arquitectonica.md), [`adr/`](adr/) y [`diagramas/`](diagramas/)
- **Estado:** Propuesta. Pendiente de confirmación docente (sección 8).

La arquitectura vuelve al alcance de la Entrega 1 sobre una demostración local de costo cero. Ningún identificador se borra, se renumera ni se reutiliza. Este documento es el rastro único del cambio: qué se conserva, qué se difiere y qué falta confirmar.

## 1. Motivo

El producto TRACKEA/ROYEXA se quedó sin financiamiento. La Entrega 2 había prometido AWS, aplicación móvil, sincronización sin conexión y multi-tenant, y nada de eso puede construirse sin ese respaldo. La Entrega 3 necesita una base que sí se pueda implementar.

## 2. Hallazgo central

La línea base realizable casi coincide con la Entrega 1. El desvío no nació en los requisitos: nació en la Entrega 2, que decidió seguir a TRACKEA donde ambos no coincidían (`arquitectura.md`, versión de la etiqueta `entrega-2-entregada`, línea 13).

No es un recorte improvisado: es volver a lo comprometido. La propia Entrega 2 lo había previsto. Su decisión sobre `AD-03` declaraba que, si se confirmaba la exclusión de la operación sin conexión, debía revisarse hacia `ALT-03A` (misma versión, línea 595).

## 3. Alcance

| Dentro | Diferido, sin borrar identificadores |
|---|---|
| Demostración local y costo cero | AWS, Terraform y cualquier nube de pago |
| FastAPI con PostgreSQL 17 local y adaptadores en memoria | Aplicación móvil nativa y SQLCipher |
| Notificador simulado (`RES-03`, `RES-05`) | SES, FCM, Telegram y S3 |
| Una sola empresa | Multi-tenant y seguridad por fila |
| Operación en línea | Sincronización sin conexión y cola local |
| Cobrador y administrador | Socio |

- **Entrega 3:** desembolso de un préstamo por API, sin interfaz (`RF-03`, `RF-04`, `RF-06`; `RN-03` a `RN-06`).
- **Entrega 4 (provisional, el repositorio no contiene su enunciado):** web mínima renderizada en el servidor, pagos, cierre de caja, `EV-08` y `EV-10`. Sin aplicación móvil.

PostgreSQL no es opcional. Un libro en memoria equivale a `ALT-01A`, ya descartada, y `propuesta.md` (sección L) exige que la inmutabilidad no dependa solo de que la aplicación se comporte bien.

## 4. Matriz de identificadores

| Clase | Significado |
|---|---|
| Conservar | Sigue vigente sin cambio de significado. |
| Reencuadrar | Sigue vigente con otra forma o alcance, sin cambiar lo que decide. |
| Diferir | Queda fuera de la arquitectura vigente y puede retomarse. El identificador se mantiene. |
| Retirar | Deja de aplicar. El identificador se mantiene y no se reutiliza. |

### 4.1 Entrega 1

El significado de estos identificadores no cambia. La matriz solo indica dónde se ejercita cada uno.

| Identificadores | Clase | Dónde se ejercita |
|---|---|---|
| `INT-01`, `INT-02`, `INT-03` | Conservar | `INT-03` vuelve al C4 como destinatario, sin operar el sistema. |
| `RF-03`, `RF-04`, `RF-06` | Conservar | Entrega 3. |
| `RF-05` | Conservar | Entrega 3 en lo que toca al calendario y a `RN-05`. |
| `RF-01`, `RF-02` | Conservar | Entrega 4 (provisional). |
| `RF-07` | Conservar | Prioridad Should, sin fecha comprometida. |
| `CA-05`, `CA-06`, `CA-09`, `CA-10`, `CA-12` | Conservar | Entrega 3. |
| `CA-07` | Conservar | Entrega 3. Se redacta sobre un pago, pero sus campos se exigen al asiento del desembolso y deben aparecer en la traza. |
| `CA-01`, `CA-02`, `CA-03`, `CA-04`, `CA-08`, `CA-11`, `CA-13` | Conservar | Entrega 4 (provisional). `CA-11` trata de pagos, fuera del recorrido de desembolso. |
| `RN-03`, `RN-04`, `RN-05`, `RN-06` | Conservar | Entrega 3. |
| `RN-01`, `RN-02` | Conservar | Entrega 4 (provisional). |
| `EC-01`, `EC-02`, `EC-04` | Conservar | Entrega 3. |
| `EC-03` | Conservar | Entrega 4 (provisional), con `EV-10`. |
| `ASR-01`, `ASR-02`, `ASR-03`, `ASR-05` | Conservar | Entrega 3. |
| `ASR-04` | Conservar | Entrega 4 (provisional), con `EV-10`. |
| `RES-01`, `RES-02`, `RES-03`, `RES-04`, `RES-05` | Conservar | Vigentes. `RES-03` y `RES-05` sustentan el notificador simulado. |

### 4.2 Asuntos, alternativas y decisiones

| Identificador | Clase | Efecto |
|---|---|---|
| `AD-01` | Conservar | Sin cambio de decisión. |
| `AD-02` | Reencuadrar | Mismo monolito modular; los avisos van al cliente final por `EXT-05`. |
| `AD-03` | Reencuadrar | Se reformula sobre operaciones de dinero en línea. Decisión en `ADR-004`. |
| `AD-04` | Diferir | Sigue a `DIV-03`. |
| `AD-05` | Reencuadrar | Decisión heredada sin comparar; se valida con `EV-10`. |
| `AD-06` | Reencuadrar | Recibe la comparación prometida en `arquitectura.md`, sección 3.4. |
| `AD-07` | Reencuadrar | Sigue cubierto por `AD-02`, ahora sobre `EXT-05`. |
| `ALT-01A`, `ALT-01C` | Conservar | Descartadas en la Entrega 2. |
| `ALT-01B` | Conservar | Seleccionada. |
| `ALT-02A` | Reencuadrar | La cola pasa a un puerto con bandeja de salida y despachador invocable. |
| `ALT-02B`, `ALT-02C` | Conservar | Descartadas en la Entrega 2. |
| `ALT-03A` | Reencuadrar | Seleccionada por `ADR-004`, con confirmación idempotente. |
| `ALT-03B` | Diferir | Era la selección de `ADR-003`. |
| `ALT-03C` | Conservar | Descartada en la Entrega 2. |
| `ADR-001` | Reencuadrar | Costo cero, PostgreSQL local obligatorio y comando local. Sigue `Propuesto`. |
| `ADR-002` | Reencuadrar | Puerto de cola, notificador simulado y evidencia ajustada. Sigue `Propuesto`. |
| `ADR-003` | Diferir | Pasa a `Reemplazado por ADR-004` solo con la confirmación docente. |
| `INV-01` | Reencuadrar | El saldo lo calcula el servidor, sin referencia al teléfono. |
| `INV-02` | Reencuadrar | Una operación de dinero se asienta una sola vez, por desembolso y tipo. |
| `INV-03` | Diferir | Sigue a `DIV-03`. |

### 4.3 Elementos C4

| Identificador | Clase | Efecto |
|---|---|---|
| `CON-01` | Diferir | Sigue en el modelo con la etiqueta `Diferido`, fuera de las vistas. |
| `CON-02` | Reencuadrar | Web mínima renderizada en el servidor para cobrador y administrador, en la Entrega 4. |
| `CON-03` | Reencuadrar | Python 3.14, FastAPI y Uvicorn en local. |
| `CON-04` | Reencuadrar | PostgreSQL 17 local, con adaptadores en memoria para las pruebas. |
| `CON-05` | Diferir | Sigue en el modelo con la etiqueta `Diferido`, fuera de las vistas. |
| `EXT-01`, `EXT-02`, `EXT-03`, `EXT-04` | Diferir | Siguen en el modelo con la etiqueta `Diferido`, fuera de las vistas. |

### 4.4 Riesgos y supuestos

| Identificador | Clase | Efecto |
|---|---|---|
| `RA-01`, `RA-02` | Conservar | Vigentes para el libro en PostgreSQL local. |
| `RA-03` | Reencuadrar | Un evento perdido deja al cliente final sin código o comprobante. |
| `RA-04` | Reencuadrar | Las fronteras se cuidan entre los módulos de la línea base. |
| `RA-05`, `RA-06` | Retirar | Cerrados: dependían de la sincronización y del teléfono. |
| `RA-07` | Retirar | Cierra cuando se confirme `DIV-02`. Pendiente. |
| `RA-08` | Retirar | Cierra cuando se confirme `DIV-01`. Pendiente. |
| `RA-09` | Diferir | Dependía de cobros tardíos sin señal. |
| `SUP-01` | Reencuadrar | Se comprueba sobre PostgreSQL 17 local. |
| `SUP-02`, `SUP-03`, `SUP-04`, `SUP-05` | Diferir | Hablan de canales, despliegue y teléfono fuera de la línea base. |

### 4.5 Evidencias

Las evidencias se resuelven en la Entrega 3. Este documento no marca ninguna como validada.

| Identificador | Clase | Estado o momento | Ajuste |
|---|---|---|---|
| `EV-01` | Conservar | Entrega 3 | Requiere PostgreSQL local. |
| `EV-02` | Reencuadrar | Entrega 3 | Comando local en lugar de integración continua. |
| `EV-03` | Reencuadrar | Entrega 3 | Habla de desembolso, no de cobro, y usa `EXT-05`. |
| `EV-04` | Diferir | Reprogramada, sin destino en el curso | Medía dos tareas en la nube. |
| `EV-05` | Diferir | Reprogramada, sin destino en el curso | Medía lotes de sincronización. La sustituye `EV-12` en el recorrido. |
| `EV-06` | Diferir | Reprogramada, sin destino en el curso | Exigía un teléfono real. |
| `EV-07` | Diferir | Reprogramada, sin destino en el curso | Sigue a `DIV-03`. |
| `EV-08` | Reencuadrar | Entrega 4 | El adaptador que se cambia es el del notificador. |
| `EV-09` | Conservar | Entrega 3 | Se añade a `ADR-002`. |
| `EV-10` | Reencuadrar | Reprogramada a Entrega 4 | Trata de pagos, fuera del recorrido de desembolso. |
| `EV-11` | Reencuadrar | Entrega 3 | Se verifica sobre la API con el `Desembolso`. |

### 4.6 Elementos sin identificador

| Elemento | Clase | Efecto |
|---|---|---|
| Venta y llave | Reencuadrar | Vuelven a ser desembolso y código de confirmación con caducidad. |
| PIX | Reencuadrar | Transferencia. `RES-01` ya la trata como dato. |
| Avisos a administradores y socios | Reencuadrar | Comprobante y código simulados hacia el cliente final. |
| Catorce módulos | Reencuadrar | Se conservan `clients`, `loans`, `sales`, `ledger`, `cash_box`, `notifications` e `identity_access` mínimo. |
| `tenancy`, `devices`, `consent`, `sync`, `expenses`, `reporting`, `payments` | Diferir | `payments` vuelve en la Entrega 4 (provisional). |
| Umbrales de 3 días y 24 horas | Diferir | Eran de TRACKEA y seguían sin confirmarse. |
| Bolts | Diferir | Se conservan solo como contexto histórico. |
| Estado observado en TRACKEA | Retirar | Ya no describe esta arquitectura. |

## 5. Resolución de divergencias

Todas las resoluciones están pendientes de confirmación docente. El detalle original sigue en `arquitectura.md`, sección 7.1.

| ID | Resolución | Consecuencia |
|---|---|---|
| `DIV-01` | A favor de la Entrega 1 | Código con caducidad y comprobante simulado. `INT-03` vuelve al C4. |
| `DIV-02` | A favor de la Entrega 1 | Sin aplicación móvil ni sincronización. `AD-03` se decide en `ADR-004`. |
| `DIV-03` | A favor de la Entrega 1 | Una sola empresa. `AD-04` e `INV-03` se difieren. |
| `DIV-04` | Diferida | El socio sigue sin `INT` y sale de las vistas. |
| `DIV-05` | A favor de la Entrega 1 | Demostración local (`RES-02`, `RES-06`). |
| `DIV-06` | A favor de la Entrega 1 | El recorrido es el desembolso. El del Bolt B1 se difiere. |
| `DIV-07` | A favor de la Entrega 1 | Sin excepción para el administrador (`RN-06`, `EC-02`). |
| `DIV-08` | Abierta | Ver sección 8. |

## 6. Identificadores nuevos

| ID | Definición | Dónde vive |
|---|---|---|
| `RES-06` | Costo cero: el desarrollo y la demostración no usan servicios de pago. Origen: pérdida de financiamiento del producto. | Este documento. La Entrega 1 no se edita. |
| `DIV-08` | El commit `5077046` dejó un integrante, mientras `RES-02` y la regla del curso dicen pareja. | Este documento y `arquitectura.md`, sección 7.1. |
| `EXT-05` | Notificador simulado que registra el código y el comprobante dirigidos al cliente final (`RES-03`, `RES-05`). | `arquitectura.md` y `workspace.dsl`. |
| `EV-12` | Reconfirmar el código no duplica el asiento ni el descuento de caja. | `arquitectura.md`, sección 6.4, y `ADR-004`. |
| `ADR-004` | Operación en línea con confirmación idempotente del código. | [`adr/ADR-004-operacion-en-linea-con-confirmacion-idempotente.md`](adr/ADR-004-operacion-en-linea-con-confirmacion-idempotente.md) |
| `ALT-06A`, `ALT-06B`, `ALT-06C` | Alternativas de `AD-06`. Se selecciona `ALT-06B`. | `arquitectura.md`, sección 3.4. |

## 7. Puntos de recuperación

| Etiqueta | Commit | Contenido |
|---|---|---|
| `entrega-1-requisitos` | `5cbdb25` | Requisitos antes del commit `5077046`. Repara la cita de `requisitos.md`, que nombra esta etiqueta. |
| `entrega-2-entregada` | `656cca1` | Arquitectura entregada, con todo lo que este documento difiere. El nombre `entrega-2-arquitectura` corresponde a una rama. |

La Entrega 0 y la Entrega 1 no se editan en esta realineación. Después de la etiqueta `entrega-1-requisitos` solo cambiaron por el commit `5077046`, que editó los integrantes de `propuesta.md` y `requisitos.md` sin alterar ningún requisito.

## 8. Estado de la confirmación docente

| Asunto | Estado | Efecto mientras siga pendiente |
|---|---|---|
| Resolución de `DIV-01` a `DIV-07` | Pendiente | La línea base se usa como propuesta de trabajo. Si el docente la rechaza, esta realineación se revisa antes de continuar. |
| `ADR-004` y `ADR-003` | Pendiente | `ADR-004` sigue `Propuesto` y `ADR-003` no cambia de estado. |
| `DIV-08`, un integrante | Pendiente | Autorización docente: pendiente. Motivo: por aportar por el autor. |
| Retroalimentación de Canvas sobre la Entrega 2 | Pendiente de incorporar | Si contradice este documento, prevalece la retroalimentación. |

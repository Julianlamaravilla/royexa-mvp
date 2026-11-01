# Trazabilidad arquitectónica

## 1. Propósito

Esta matriz continúa la trazabilidad iniciada en `../01-requisitos/requisitos.md`.

No reemplaza ni copia la matriz funcional de la Entrega 1. Su propósito es mostrar cómo los requisitos, reglas, escenarios de calidad, ASR y restricciones originan asuntos arquitectónicos, alternativas, decisiones provisionales, ADR, elementos C4 y evidencias de validación.

El 2026-10-30 esta matriz se actualizó con la realineación descrita en [`realineacion-entrega-1.md`](realineacion-entrega-1.md). Ese documento define los identificadores nuevos, y su resolución de divergencias está pendiente de confirmación docente. El 2026-10-31 se incorporó el resultado de las evidencias de la Entrega 3, registrado en `../03-diseno-vertical/diseno-y-vertical.md`, sección 8.

```text
INT / RF / CA / RN / EC / ASR / RES
                    ↓
                    AD
                    ↓
                   ALT
                    ↓
           Decisión provisional
                    ↓
                  ADR
                    ↓
        Elemento arquitectónico C4
                    ↓
                    EV
```

---

## 2. Reglas de diligenciamiento

1. Use únicamente identificadores que existan en la Entrega 1 o que hayan sido definidos en la Entrega 2.
2. No invente relaciones para llenar todas las celdas.
3. Registre `No aplica` cuando no exista una relación.
4. Un asunto puede tener varios elementos de origen.
5. Cada asunto analizado debe incluir al menos dos alternativas.
6. Una decisión significativa debe enlazar su ADR.
7. Un ADR puede afectar varios elementos del modelo C4.
8. Toda decisión provisional debe tener al menos una evidencia pendiente o una justificación de por qué no requiere validación experimental.
9. Mantenga actualizada la matriz cuando cambie un ADR, un contenedor o una evidencia.

---

## 3. Matriz principal

| Asunto | Origen | Interesados | Alternativas | Decisión provisional | ADR | Elementos C4 afectados | Riesgos y supuestos | Evidencia |
|---|---|---|---|---|---|---|---|---|
| AD-01 | ASR-01, EC-01, RN-04, RF-04 | INT-01, INT-02 | ALT-01A, ALT-01B, ALT-01C | ALT-01B | ADR-001 | CON-03, CON-04 | RA-01, RA-02, SUP-01 | EV-01, EV-02 |
| AD-02 | ASR-01, ASR-02, ASR-05, EC-04, RES-02, RES-03, RES-05, RES-06 | INT-01, INT-02 | ALT-02A, ALT-02B, ALT-02C | ALT-02A | ADR-002 | CON-02, CON-03, CON-04, EXT-05 | RA-03, RA-04 | EV-03, EV-08, EV-09 |
| AD-03 | ASR-01, ASR-02, RF-03, RF-04, RN-03, RN-04, EC-01; DIV-02 | INT-01, INT-02, INT-03 | ALT-03A, ALT-03B, ALT-03C | ALT-03A | ADR-004 (propuesto; ADR-003 no cambia de estado hasta la confirmación docente) | CON-02, CON-03, CON-04 | RA-07 | EV-12 |
| AD-04 | DIV-03, RES-04 | INT-02 | No analizado | Diferida con DIV-03: se trabaja con una sola empresa | No aplica | No aplica | No aplica | EV-07, reprogramada sin destino en el curso |
| AD-05 | ASR-04, EC-03, RN-01 | INT-01, INT-02 | No analizado | Heredada, sin comparar: importes en enteros de centavos y cálculo en funciones puras | No aplica | CON-03 | No aplica | EV-10, reprogramada a Entrega 4 |
| AD-06 | ASR-03, EC-02, RN-06; DIV-07 | INT-02 | ALT-06A, ALT-06B, ALT-06C | ALT-06B | No aplica (sección 3.4 de `arquitectura.md`) | CON-03 | Usuarios sembrados como limitación declarada | EV-11 |
| AD-07 | ASR-05, EC-04, RF-06 | INT-02, INT-03 | Cubierto en AD-02 | ALT-02A | ADR-002 | CON-03, CON-04, EXT-05 | RA-03, RA-08 | EV-03 |

---

## 4. Cobertura de ASR

Esta vista permite detectar ASR sin tratamiento arquitectónico o decisiones sin origen justificable.

| ASR | Elemento de origen en Entrega 1 | Asuntos relacionados | Decisiones o ADR | Elementos C4 | Evidencia | Estado |
|---|---|---|---|---|---|---|
| ASR-01 | RN-04, EC-01 | AD-01, AD-02, AD-03 | ADR-001, ADR-002, ADR-004 | CON-03, CON-04 | EV-01, EV-02, EV-12 | Cubierto en la decisión; EV-01, EV-02 y EV-12 `Validada`. El asiento compensatorio queda para la Entrega 4 (HV-03) |
| ASR-02 | RN-03, RF-03, RF-06 | AD-02, AD-03 | ADR-002, ADR-004 | CON-03, CON-04, EXT-05 | EV-03, EV-12 | Cubierto en la decisión; EV-03 y EV-12 `Validada`; pendiente de la confirmación docente de DIV-01 |
| ASR-03 | RN-06, EC-02 | AD-06 | ALT-06B, sin ADR propio | CON-03 | EV-11 | Cubierto en la decisión, sin excepción (DIV-07); EV-11 `Validada`; usuarios sembrados como limitación declarada |
| ASR-04 | RN-01, EC-03 | AD-05 | Decisión heredada, sin ADR | CON-03 | EV-10 | Cubierto en la decisión; EV-10 `Reprogramada a la Entrega 4`, donde se valida EC-03 (provisional) |
| ASR-05 | EC-04, RES-03 | AD-02, AD-07 | ADR-002 | CON-03, CON-04, EXT-05 | EV-03, EV-08 | Cubierto en la decisión con el notificador simulado; EV-03 `Validada`; EV-08 prevista para la Entrega 4 |

### ASR sin decisión durante esta entrega

- **ASR-03:** la comparación diferida en la Entrega 2 está en la sección 3.4 de `arquitectura.md`, que selecciona ALT-06B.
- **ASR-04:** no se comparan alternativas: los enteros de centavos se heredan como decisión. Se cubre con `EV-10` en la Entrega 4 (provisional).

---

## 5. Cobertura del recorrido vertical

| Elemento del recorrido | Referencias funcionales | Conceptos del dominio | Contenedores | Decisiones relacionadas | Evidencia |
|---|---|---|---|---|---|
| Entrada | RF-03, CA-05 | Desembolso, Cliente | CON-03 (Entrega 3), CON-02 (Entrega 4) | AD-03, ADR-004 | EV-12 |
| Comportamiento principal | RF-03, RN-03, RN-05, RN-06, CA-06, CA-09, CA-10 | Desembolso, Código de confirmación, Préstamo, Cuota | CON-03 | AD-02, AD-03, AD-06, ADR-002, ADR-004 | EV-09, EV-11, EV-12 |
| Persistencia | ASR-01, RF-04, CA-07, RES-04 | Asiento, Caja | CON-04 (Asiento); CON-03, en memoria en la Entrega 3 (Caja, HV-07) | AD-01, ADR-001 | EV-01, EV-02 |
| Integración externa | RF-06, CA-12, EC-04, ASR-05, RES-03, RES-05 | Aviso | CON-03, EXT-05 | AD-02, ADR-002 | EV-03, EV-08 |
| Resultado observable | CA-05, CA-06 | Préstamo, Asiento | CON-03 (Préstamo, en memoria en la Entrega 3, HV-07); CON-04 (Asiento) | AD-01, AD-03, ADR-001, ADR-004 | EV-01, EV-12 |

Nota: el recorrido del Bolt B1 de TRACKEA queda diferido (`DIV-06`), y con él `EV-05` y `EV-06`. `EV-10` y `CA-11` tratan de pagos, fuera de este recorrido, y pasan a la Entrega 4 (provisional). `CA-07` se redacta sobre un pago, pero sus campos se exigen al asiento del desembolso.

---

## 6. Decisiones sin trazabilidad suficiente

| Decisión propuesta | Problema de trazabilidad | Acción requerida |
|---|---|---|
| AD-04 Aislamiento entre financieras | Su origen era el alcance de TRACKEA, que la Entrega 1 excluyó (DIV-03). | Diferida con su identificador. La resolución de DIV-03 está pendiente de confirmación docente. |
| AD-03 Operación en línea con confirmación idempotente | Cerrado: la decisión vigente (`ADR-004`) tiene origen en la Entrega 1. La operación sin conexión de `ADR-003` sigue excluida (DIV-02). | La resolución de DIV-02 está pendiente de confirmación docente. Con ella, `ADR-003` pasa a `Reemplazado por ADR-004`. |

## 7. Consistencia de identificadores

Antes de entregar, compruebe:

- [x] Todos los `INT-XX`, `RF-XX`, `CA-XX`, `RN-XX`, `EC-XX`, `ASR-XX` y `RES-XX` existen en `../01-requisitos/requisitos.md`, excepto `RES-06`, que se define en `realineacion-entrega-1.md` porque la Entrega 1 no se edita.
- [x] Todos los `AD-XX` existen en `arquitectura.md`.
- [x] Todas las alternativas `ALT-XX` están descritas.
- [x] Todos los `ADR-XXX` existen en la carpeta `adr/`.
- [x] Todos los `CON-XX` y `EXT-XX` coinciden con `workspace.dsl` y con el catálogo de contenedores.
- [x] Todos los `RA-XX`, `SUP-XX` y `EV-XX` están definidos en `arquitectura.md`.
- [x] No existen decisiones técnicas sin origen o justificación. `AD-03` se apoya en la Entrega 1 mediante `ADR-004` y `AD-04` queda diferida. Las resoluciones de la sección 6 están pendientes de confirmación docente.

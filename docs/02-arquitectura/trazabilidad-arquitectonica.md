# Trazabilidad arquitectónica

## 1. Propósito

Esta matriz continúa la trazabilidad iniciada en `../01-requisitos/requisitos.md`.

No reemplaza ni copia la matriz funcional de la Entrega 1. Su propósito es mostrar cómo los requisitos, reglas, escenarios de calidad, ASR y restricciones originan asuntos arquitectónicos, alternativas, decisiones provisionales, ADR, elementos C4 y evidencias de validación.

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

| Asunto | Origen | Interesados | Alternativas | Decisión provisional | ADR | Elementos C4 afectados | Riesgos y supuestos | Evidencia pendiente |
|---|---|---|---|---|---|---|---|---|
| AD-01 | ASR-01, EC-01, RN-04, RF-04 | INT-01, INT-02 | ALT-01A, ALT-01B, ALT-01C | ALT-01B | ADR-001 | CON-03, CON-04 | RA-01, RA-02, SUP-01 | EV-01, EV-02 |
| AD-02 | ASR-01, ASR-02, ASR-05, EC-04, RES-02, RES-03 | INT-01, INT-02 | ALT-02A, ALT-02B, ALT-02C | ALT-02A | ADR-002 | CON-02, CON-03, CON-04, EXT-01, EXT-02, EXT-03 | RA-03, RA-04, SUP-02, SUP-03 | EV-03, EV-04, EV-08, EV-09 |
| AD-03 | ASR-01, RF-01, RN-04, EC-01, RES-04; DIV-02 | INT-01, INT-02 | ALT-03A, ALT-03B, ALT-03C | ALT-03B | ADR-003 | CON-01, CON-03, CON-04 | RA-05, RA-06, RA-07, RA-09, SUP-04, SUP-05 | EV-05, EV-06 |
| AD-04 | DIV-03, RES-04 | INT-02 | No analizado | Heredada de TRACKEA: seguridad por fila con el contexto de la financiera por transacción | No aplica | CON-03, CON-04 | No aplica | EV-07 |
| AD-05 | ASR-04, EC-03, RN-01 | INT-01, INT-02 | No analizado | Heredada de TRACKEA: importes en enteros de centavos y cálculo en funciones puras | No aplica | CON-03 | No aplica | EV-10 |
| AD-06 | ASR-03, EC-02, RN-06; DIV-07 | INT-02 | No analizado | Heredada de TRACKEA: permisos evaluados en el servidor con plantillas de rol y excepciones | No aplica | CON-03 | No aplica | EV-11 |
| AD-07 | ASR-05, EC-04, RF-06 | INT-02 | Cubierto en AD-02 | ALT-02A | ADR-002 | CON-03, CON-04, EXT-01, EXT-02, EXT-03 | RA-03, RA-08 | EV-03 |

---

## 4. Cobertura de ASR

Esta vista permite detectar ASR sin tratamiento arquitectónico o decisiones sin origen justificable.

| ASR | Elemento de origen en Entrega 1 | Asuntos relacionados | Decisiones o ADR | Elementos C4 | Evidencia pendiente | Estado |
|---|---|---|---|---|---|---|
| ASR-01 | RN-04, EC-01 | AD-01, AD-02, AD-03 | ADR-001, ADR-002, ADR-003 | CON-03, CON-04 | EV-01, EV-02, EV-05 | Cubierto |
| ASR-02 | RN-03, RF-03, RF-06 | AD-02 | ADR-002 | CON-03, EXT-01, EXT-02, EXT-03 | EV-03 | Parcial: los avisos a administradores tienen tratamiento; el código de confirmación del cliente final no existe en v1 (DIV-01) |
| ASR-03 | RN-06, EC-02 | AD-06 | Decisión heredada de TRACKEA, sin ADR | CON-03 | EV-11 | Parcial: la excepción del administrador principal (DIV-07) y su construcción en los Bolts B3 y B6 |
| ASR-04 | RN-01, EC-03 | AD-05 | Decisión heredada de TRACKEA, sin ADR | CON-03 | EV-10 | Cubierto en la decisión; falta la prueba de aceptación de EC-03 |
| ASR-05 | EC-04, RES-03 | AD-02, AD-07 | ADR-002 | CON-03, CON-04, EXT-01, EXT-02, EXT-03 | EV-03, EV-08 | Parcial: el envío queda con estado consultable para administradores; el comprobante al cliente final no existe en v1 (DIV-01) |

### ASR sin decisión durante esta entrega

- **ASR-03:** se difiere la comparación de alternativas de autorización. TRACKEA construye los permisos en los Bolts B3 y B6, después del esqueleto B1. Se trata en la Entrega 3.
- **ASR-04:** no se comparan alternativas porque la representación del dinero ya está fijada en TRACKEA. Se cubre con `EV-10`.

---

## 5. Cobertura del recorrido vertical

| Elemento del recorrido | Referencias funcionales | Conceptos del dominio | Contenedores | Decisiones relacionadas | Evidencia futura |
|---|---|---|---|---|---|
| Entrada | RF-03, CA-05 | Venta, Cliente | CON-01, CON-02, CON-03 | AD-03, ADR-003 | EV-06 |
| Comportamiento principal | RF-03, RN-03, RN-05, RN-06 | Venta, Llave, Préstamo, Cuota | CON-03 | AD-02, AD-06, ADR-002 | EV-11 |
| Persistencia | ASR-01, RES-04 | Asiento, Caja | CON-04 | AD-01, ADR-001 | EV-01, EV-02 |
| Integración externa | EC-04, ASR-05, RES-03 | Aviso | CON-03, EXT-01, EXT-02, EXT-03 | AD-02, ADR-002 | EV-03, EV-08 |
| Resultado observable | CA-05, CA-06 | Préstamo, Asiento | CON-03 | AD-01 | EV-01 |

Nota: el Bolt B1 de TRACKEA ejercita otro recorrido (un cobro sin señal que llega una sola vez al libro, `RF-01` y `RF-04`; `DIV-06`). Sus evidencias son `EV-05` y `EV-06`.

---

## 6. Decisiones sin trazabilidad suficiente

| Decisión propuesta | Problema de trazabilidad | Acción requerida |
|---|---|---|
| AD-04 Aislamiento entre financieras | Su origen es el alcance de TRACKEA, que la Entrega 1 excluyó (DIV-03). No se relaciona con ningún ASR, regla ni restricción de la Entrega 1 salvo `RES-04`. | Justificar con el docente si el aislamiento entra en el alcance o eliminar el asunto. |
| AD-03 Cola local cifrada y sincronización | La operación sin conexión está excluida de la Entrega 1 (DIV-02). El origen en `ASR-01` es indirecto. | Resolver DIV-02. Si se excluye, revisar ADR-003 hacia ALT-03A. |

## 7. Consistencia de identificadores

Antes de entregar, compruebe:

- [x] Todos los `INT-XX`, `RF-XX`, `CA-XX`, `RN-XX`, `EC-XX`, `ASR-XX` y `RES-XX` existen en `../01-requisitos/requisitos.md`.
- [x] Todos los `AD-XX` existen en `arquitectura.md`.
- [x] Todas las alternativas `ALT-XX` están descritas.
- [x] Todos los `ADR-XXX` existen en la carpeta `adr/`.
- [x] Todos los `CON-XX` y `EXT-XX` coinciden con `workspace.dsl` y con el catálogo de contenedores.
- [x] Todos los `RA-XX`, `SUP-XX` y `EV-XX` están definidos en `arquitectura.md`.
- [ ] No existen decisiones técnicas sin origen o justificación. Pendiente: `AD-03` y `AD-04` tienen origen parcial en la Entrega 1 (ver sección 6).

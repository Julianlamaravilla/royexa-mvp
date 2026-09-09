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
| AD-01 | ASR-XX, EC-XX, RN-XX, RES-XX | INT-XX | ALT-01A, ALT-01B | ALT-01X | ADR-001 | CON-XX, EXT-XX | RA-XX, SUP-XX | EV-XX |
| AD-02 | ASR-XX, EC-XX, RN-XX, RES-XX | INT-XX | ALT-02A, ALT-02B | ALT-02X | ADR-002 | CON-XX | RA-XX, SUP-XX | EV-XX |
| AD-03 | ASR-XX, EC-XX, RN-XX, RES-XX | INT-XX | ALT-03A, ALT-03B | ALT-03X | ADR-003 | CON-XX | RA-XX, SUP-XX | EV-XX |

---

## 4. Cobertura de ASR

Esta vista permite detectar ASR sin tratamiento arquitectónico o decisiones sin origen justificable.

| ASR | Elemento de origen en Entrega 1 | Asuntos relacionados | Decisiones o ADR | Elementos C4 | Evidencia pendiente | Estado |
|---|---|---|---|---|---|---|
| ASR-01 | [RF-XX / RN-XX / EC-XX / RES-XX] | [AD-XX] | [ADR-XXX] | [CON-XX / EXT-XX] | [EV-XX] | [Cubierto / Parcial / Pendiente] |
| ASR-02 | [RF-XX / RN-XX / EC-XX / RES-XX] | [AD-XX] | [ADR-XXX] | [CON-XX / EXT-XX] | [EV-XX] | [Cubierto / Parcial / Pendiente] |
| ASR-03 | [RF-XX / RN-XX / EC-XX / RES-XX] | [AD-XX] | [ADR-XXX] | [CON-XX / EXT-XX] | [EV-XX] | [Cubierto / Parcial / Pendiente] |

### ASR sin decisión durante esta entrega

[Liste los ASR cuyo tratamiento se difiere y justifique la razón.]

- **ASR-XX:** [Razón y momento previsto de tratamiento]

---

## 5. Cobertura del recorrido vertical

| Elemento del recorrido | Referencias funcionales | Conceptos del dominio | Contenedores | Decisiones relacionadas | Evidencia futura |
|---|---|---|---|---|---|
| Entrada | [RF-XX, CA-XX] | [Conceptos] | [CON-XX] | [AD-XX, ADR-XXX] | [EV-XX] |
| Comportamiento principal | [RF-XX, RN-XX] | [Conceptos] | [CON-XX] | [AD-XX, ADR-XXX] | [EV-XX] |
| Persistencia | [ASR-XX, RES-XX] | [Conceptos] | [CON-XX] | [AD-XX, ADR-XXX] | [EV-XX] |
| Integración externa | [EC-XX, ASR-XX, RES-XX] | [Conceptos] | [EXT-XX, CON-XX] | [AD-XX, ADR-XXX] | [EV-XX] |
| Resultado observable | [CA-XX] | [Conceptos o estados] | [CON-XX] | [AD-XX] | [EV-XX] |

---

## 6. Decisiones sin trazabilidad suficiente

[Registre temporalmente cualquier decisión que todavía no tenga un origen claro. Antes de cerrar la entrega, la decisión debe justificarse o eliminarse.]

| Decisión propuesta | Problema de trazabilidad | Acción requerida |
|---|---|---|
| [Decisión] | [No se relaciona con ASR, regla, restricción o riesgo] | [Reformular, justificar o eliminar] |

---

## 7. Consistencia de identificadores

Antes de entregar, compruebe:

- [ ] Todos los `INT-XX`, `RF-XX`, `CA-XX`, `RN-XX`, `EC-XX`, `ASR-XX` y `RES-XX` existen en `../01-requisitos/requisitos.md`.
- [ ] Todos los `AD-XX` existen en `arquitectura.md`.
- [ ] Todas las alternativas `ALT-XX` están descritas.
- [ ] Todos los `ADR-XXX` existen en la carpeta `adr/`.
- [ ] Todos los `CON-XX` y `EXT-XX` coinciden con `workspace.dsl` y con el catálogo de contenedores.
- [ ] Todos los `RA-XX`, `SUP-XX` y `EV-XX` están definidos en `arquitectura.md`.
- [ ] No existen decisiones técnicas sin origen o justificación.

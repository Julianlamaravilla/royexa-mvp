# Trazabilidad de diseño, implementación y pruebas

## 1. Propósito

Esta matriz extiende la trazabilidad de las Entregas 1 y 2 hasta componentes, contratos, código, pruebas y evidencias. No copie el contenido de los documentos anteriores; use sus identificadores.

## 2. Matriz del recorrido vertical

| Caso de uso | Origen funcional | Reglas | Calidad / ASR / restricciones | Decisiones | Componentes | Contratos | Código | Pruebas | Evidencia | Estado |
|---|---|---|---|---|---|---|---|---|---|---|
| UC-01 | RF-XX, CA-XX | RN-XX | EC-XX, ASR-XX, RES-XX | AD-XX, ADR-XXX | CMP-XX | CTR-XX | `ruta` | PR-XX | EV-XX | [Completo/Parcial/Bloqueado] |

## 3. Trazabilidad de componentes

| Componente | Contenedor | Responsabilidad | Origen | Decisión | Contratos | Ruta de código | Pruebas |
|---|---|---|---|---|---|---|---|
| CMP-01 | CON-XX | [Responsabilidad] | [RF/RN/ASR] | [AD/ADR] | CTR-XX | `ruta` | PR-XX |

## 4. Trazabilidad de criterios y reglas comprobados

| Elemento | Comportamiento esperado | Implementación | Prueba | Resultado | Observaciones |
|---|---|---|---|---|---|
| CA-XX | [Resultado] | `ruta` | PR-XX | [Pasa/Falla/Parcial] | [Observación] |
| RN-XX | [Invariante] | `ruta` | PR-XX | [Pasa/Falla/Parcial] | [Observación] |

## 5. Validación de decisiones provisionales

| Decisión | Evidencia prevista | Evidencia obtenida | Hallazgo | Efecto sobre el ADR | Estado actual |
|---|---|---|---|---|---|
| ADR-XXX | EV-XX | [Resultado] | HV-XX | [Sin cambio/Ajustado/Reemplazado] | [Propuesto/Aceptado/etc.] |

## 6. Elementos sin cobertura

| Elemento | Motivo de falta de cobertura | Riesgo | Acción prevista |
|---|---|---|---|
| [RF/RN/ASR/EV] | [Motivo] | [Riesgo] | [Acción] |

## 7. Consistencia

- [ ] Todos los identificadores de Entrega 1 existen.
- [ ] Todos los `AD`, `ADR`, `CON`, `EV`, `RA` y `SUP` existen en la Entrega 2.
- [ ] Todos los `CMP`, `CTR`, `UC`, `PR` y `HV` están definidos en la Entrega 3.
- [ ] Cada prueba declarada existe en el repositorio.
- [ ] Cada ruta de código existe en el commit entregado.
- [ ] Los diagramas de secuencia coinciden con los componentes y contratos.
- [ ] Los hallazgos que afectan decisiones están reflejados en los ADR.

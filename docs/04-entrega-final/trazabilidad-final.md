# Trazabilidad final

## 1. Matriz de cobertura

| Requisito o escenario | Reglas | Decisiones / ADR | Componentes / contratos | Código | Pruebas | Evidencia | Estado |
|---|---|---|---|---|---|---|---|
| RF-XX / CA-XX / EC-XX | RN-XX | AD-XX / ADR-XXX | CMP-XX / CTR-XX | `ruta` | PR-XX | EV-XX | [Completo/Parcial/Excluido] |

## 2. Patrones y problemas de diseño

| Patrón | Problema | Elementos | Decisión relacionada | Pruebas / evidencia |
|---|---|---|---|---|
| PAT-01 | [Problema] | [CMP/rutas] | [AD/ADR] | [PR/EV] |

## 3. Integración

| Sistema externo | Propósito | Componente / contrato | Fallo considerado | Prueba / evidencia | Estado |
|---|---|---|---|---|---|
| EXT-XX | [Propósito] | CMP-XX / CTR-XX | [Fallo] | PR-XX / EV-XX | [Operativa/Simulada/Parcial] |

## 4. ADR y evidencia final

| ADR | Estado inicial | Evidencia obtenida | Estado final | Consecuencia |
|---|---|---|---|---|
| ADR-XXX | [Propuesto] | [EV/HV/PR] | [Aceptado/Rechazado/Reemplazado/Propuesto] | [Consecuencia] |

## 5. Elementos sin cobertura

| Elemento | Motivo | Riesgo | Decisión tomada |
|---|---|---|---|
| [RF/EC/ASR/RA] | [Motivo] | [Riesgo] | [Excluir/Diferir/Mitigar] |

## 6. Consistencia

- [ ] Los identificadores de Entregas 1 a 3 existen y conservan su significado.
- [ ] Cada funcionalidad declarada como completa tiene código y prueba o evidencia.
- [ ] Cada patrón declarado existe en el código.
- [ ] C4, secuencias, componentes, contratos y código son coherentes.
- [ ] Los ADR afectados contienen historial y estado final.
- [ ] Cada ruta y comando documentado existe en el commit evaluable.
- [ ] Los elementos parciales o excluidos están declarados explícitamente.

# Entrega 4 — Informe final del proyecto

<!-- Reemplacen los campos entre corchetes y eliminen los comentarios. -->

## 0. Identificación

- **Proyecto:** [Nombre]
- **Integrantes:** [Nombres]
- **Grupo:** [Grupo]
- **Fecha:** [AAAA-MM-DD]
- **Repositorio:** [URL]
- **Commit o etiqueta evaluable:** [Identificador]

## 1. Resultado del proyecto

### 1.1 Problema y resultado de negocio

[Explique en máximo 200 palabras qué problema atiende y qué resultado produce la versión final.]

### 1.2 Alcance final

| Elemento | Referencias | Estado | Evidencia o ruta | Observación |
|---|---|---|---|---|
| Flujo principal | [RF/CA/UC] | [Completo/Parcial/Excluido] | [Ruta/EV] | [Observación] |
| Funcionalidad Must | [RF-XX] | [Estado] | [Ruta/PR] | [Observación] |
| Funcionalidad Must | [RF-XX] | [Estado] | [Ruta/PR] | [Observación] |

### 1.3 Exclusiones y limitaciones

| Elemento no terminado | Motivo | Impacto | Mitigación o decisión |
|---|---|---|---|
| [RF/funcionalidad] | [Motivo real] | [Impacto] | [Acción] |

## 2. Demostración funcional

- **Actor o sistema iniciador:** [INT/EXT]
- **Entrada:** [Solicitud, comando o evento]
- **Reglas ejercidas:** [RN-XX]
- **Resultado observable:** [Resultado]
- **Datos de demostración:** [Ruta o instrucciones]

### 2.1 Escenario principal

1. [Paso]
2. [Paso]
3. [Paso]
4. [Resultado]

### 2.2 Escenario alternativo o de error

- **Condición:** [Condición]
- **Comportamiento esperado:** [Resultado]
- **Regla, riesgo o decisión comprobada:** [RN/RA/ADR]

## 3. Arquitectura final

### 3.1 Organización y fronteras

[Explique unidades de ejecución, almacenamiento, módulos principales, dirección de dependencias y fronteras externas.]

### 3.2 Vistas vigentes

- **Fuente C4:** [`../02-arquitectura/diagramas/workspace.dsl`](../02-arquitectura/diagramas/workspace.dsl)
- **Contexto:** [ruta al SVG]
- **Contenedores:** [ruta al SVG]
- **Componentes:** [ruta al SVG]

### 3.3 Cambios significativos

| Cambio | Evidencia que lo originó | Decisión o ADR | Consecuencia |
|---|---|---|---|
| [Cambio] | [EV/HV/PR] | [AD/ADR] | [Consecuencia] |

## 4. Patrones aplicados

### PAT-01 — [Nombre del patrón o decisión de no aplicarlo]

- **Problema concreto:** [Problema]
- **Contexto y fuerzas:** [Descripción]
- **Alternativa simple considerada:** [Alternativa]
- **Decisión:** [Patrón/solución]
- **Participantes:** [Clases/componentes]
- **Rutas de código:** [Rutas]
- **Beneficio comprobado:** [Beneficio]
- **Costo o riesgo:** [Costo]
- **Pruebas o evidencia:** [PR/EV]

<!-- Repita únicamente para patrones realmente relevantes. -->

## 5. Integración o subsistema distribuido

- **Sistema o subsistema:** [EXT-XX / nombre]
- **Propósito:** [Resultado]
- **Mecanismo:** [HTTP/REST, mensajería u otro]
- **Componente responsable:** [CMP-XX]
- **Contrato o puerto:** [CTR-XX]
- **Datos funcionales intercambiados:** [Descripción]
- **Punto de sustitución:** [Ruta/abstracción]
- **Simulador, fake o stub:** [Ruta]

### 5.1 Fallos parciales

| Condición | Detección | Respuesta del sistema | Evidencia |
|---|---|---|---|
| Servicio no disponible | [Mecanismo] | [Respuesta] | [PR/EV] |
| Demora o respuesta inválida | [Mecanismo] | [Respuesta] | [PR/EV] |

### 5.2 Decisión de distribución

[Explique por qué la solución permanece como monolito, monolito modular o incluye procesos separados. Indique costos y trade-offs.]

## 6. Evaluación arquitectónica

### EA-01 — [Escenario de calidad o cambio]

- **Origen:** [EC/ASR/RA]
- **Estímulo:** [Cambio o condición]
- **Resultado esperado:** [Medida o condición]
- **Elementos afectados:** [CON/CMP/CTR]
- **Actividad realizada:** [Prueba, inspección, simulación]
- **Resultado y evidencia:** [EV/PR/ruta]
- **Sensibilidad o trade-off:** [Hallazgo]
- **Decisión o acción:** [ADR/acción]

### EA-02 — [Escenario de integración o distribución]

- **Origen:** [EC/ASR/RA]
- **Estímulo:** [Fallo, latencia o cambio]
- **Resultado esperado:** [Condición]
- **Elementos afectados:** [CON/CMP/EXT]
- **Actividad realizada:** [Actividad]
- **Resultado y evidencia:** [EV/PR/ruta]
- **Sensibilidad o trade-off:** [Hallazgo]
- **Decisión o acción:** [ADR/acción]

## 7. Pruebas finales

| ID | Tipo | Escenario | Referencias | Ruta | Resultado |
|---|---|---|---|---|---|
| PR-XX | Unidad | Escenario principal | [CA/UC] | [ruta] | [Pasa/Falla] |
| PR-XX | Unidad | Regla 1 | [RN] | [ruta] | [Pasa/Falla] |
| PR-XX | Unidad | Regla 2 | [RN] | [ruta] | [Pasa/Falla] |
| PR-XX | Unidad/componente | Alternativo | [CA/RN] | [ruta] | [Pasa/Falla] |
| PR-XX | Integración/componente | Persistencia o integración | [CTR/EXT] | [ruta] | [Pasa/Falla] |

- **Fecha de ejecución:** [AAAA-MM-DD]
- **Comando:** `[comando]`
- **Total:** [n]
- **Exitosas:** [n]
- **Fallidas:** [n]
- **Evidencia:** [`evidencias/resultado-pruebas.*`](evidencias/)

## 8. Ejecución reproducible

### 8.1 Requisitos

- [Runtime y versión]
- [Gestor de dependencias]
- [Servicios o herramientas]

### 8.2 Preparar dependencias

```bash
[comando]
```

### 8.3 Configurar

```bash
[comando o instrucciones sin secretos]
```

### 8.4 Iniciar

```bash
[comando]
```

### 8.5 Cargar datos de demostración

```bash
[comando o No aplica]
```

### 8.6 Ejecutar pruebas

```bash
[comando]
```

### 8.7 Ejecutar la demostración principal

```bash
[comando o solicitud de ejemplo]
```

## 9. Deuda técnica y riesgos residuales

| ID | Deuda o riesgo | Impacto | Motivo de aceptación | Próxima acción |
|---|---|---|---|---|
| DT-01 | [Descripción] | [B/M/A] | [Motivo] | [Acción] |

## 10. Conclusiones

- **Decisión técnica más importante:** [Conclusión]
- **Evidencia que más cambió el diseño:** [Conclusión]
- **Principal trade-off aceptado:** [Conclusión]
- **Siguiente incremento recomendado:** [Conclusión]

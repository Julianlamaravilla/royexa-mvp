# Entrega 2 — Arquitectura candidata

## 0. Identificación

- **Proyecto:** [Nombre del proyecto]
- **Integrantes:**
  - [Nombre del integrante 1]
  - [Nombre del integrante 2]
- **Grupo:** [Identificación del grupo]
- **Fecha:** [AAAA-MM-DD]
- **Commit o etiqueta de entrega:** [Identificador]
- **Entrega 1 utilizada como línea base:** [`../01-requisitos/requisitos.md`](../01-requisitos/requisitos.md)

---

## 1. Modelo conceptual del dominio

### 1.1 Propósito y alcance del modelo

[Explique qué parte del dominio representa el modelo y qué preguntas permite responder. Indique su relación con el flujo principal y el recorrido vertical previsto.]

### 1.2 Representación visual

[Inserte o enlace aquí el modelo conceptual. Conserve también su fuente editable o reproducible.]

```markdown
![Modelo conceptual del dominio](diagramas/modelo-conceptual.svg)
```

### 1.3 Glosario del dominio

| Término | Definición contextual | Sinónimos o ambigüedades que deben evitarse | Referencias |
|---|---|---|---|
| [Término] | [Definición dentro de este dominio] | [Términos ambiguos] | [RF-XX, RN-XX] |
| [Término] | [Definición dentro de este dominio] | [Términos ambiguos] | [RF-XX, RN-XX] |

### 1.4 Conceptos principales

#### [Nombre del concepto]

- **Tipo conceptual:** [Entidad / objeto de valor / servicio de dominio / otro]
- **Definición:** [Significado dentro del negocio]
- **Identidad o valor:** [Explique qué permite distinguirlo, si aplica]
- **Ciclo de vida o estados:** [Estados principales o No aplica]
- **Reglas e invariantes:** [RN-XX y descripción breve]
- **Requisitos relacionados:** [RF-XX]
- **Criterios relevantes:** [CA-XX]
- **Relaciones principales:** [Conceptos con los que se relaciona]

[Repita esta subsección para los conceptos relevantes.]

### 1.5 Relaciones y cardinalidades relevantes

| Origen | Relación | Destino | Cardinalidad | Justificación de dominio |
|---|---|---|---|---|
| [Concepto] | [Verbo o relación] | [Concepto] | [1, 0..1, 1..*, etc.] | [Regla o necesidad que justifica la relación] |

### 1.6 Reglas e invariantes representadas

| Regla o invariante | Conceptos involucrados | Límite de consistencia | Efecto sobre el modelo |
|---|---|---|---|
| [RN-XX o invariante derivada] | [Conceptos] | [Límite] | [Qué debe permanecer verdadero] |

### 1.7 Estados y transiciones relevantes

[Complete esta sección únicamente si existen entidades cuyo ciclo de vida sea significativo.]

| Concepto | Estado inicial | Evento o acción | Estado resultante | Precondición o regla |
|---|---|---|---|---|
| [Entidad] | [Estado] | [Evento] | [Estado] | [RN-XX / CA-XX] |

### 1.8 Contextos delimitados preliminares

[Complete esta sección cuando el dominio presente vocabularios, reglas o responsabilidades claramente diferenciados. No convierta automáticamente cada contexto conceptual en un contenedor o microservicio.]

| Contexto preliminar | Responsabilidad de negocio | Conceptos principales | Relaciones con otros contextos |
|---|---|---|---|
| [Nombre] | [Responsabilidad] | [Conceptos] | [Relaciones] |

### 1.9 Comprobación del modelo

Utilice el flujo principal, el recorrido vertical y al menos dos casos límite para comprobar el modelo.

#### Escenario principal

- **Entrada:** [Entrada del recorrido]
- **Conceptos participantes:** [Conceptos]
- **Reglas activadas:** [RN-XX]
- **Estados modificados:** [Estados]
- **Resultado:** [Resultado observable]

#### Caso límite 1: [Nombre]

- **Condición:** [Situación límite]
- **Conceptos participantes:** [Conceptos]
- **Reglas o invariantes:** [RN-XX]
- **Respuesta esperada:** [Resultado]

#### Caso límite 2: [Nombre]

- **Condición:** [Situación límite]
- **Conceptos participantes:** [Conceptos]
- **Reglas o invariantes:** [RN-XX]
- **Respuesta esperada:** [Resultado]

### 1.10 Preguntas abiertas del modelo

- [Pregunta o ambigüedad pendiente]
- [Pregunta o ambigüedad pendiente]

---

## 2. Asuntos de decisión arquitectónica

### 2.1 Inventario inicial

[Identifique los asuntos arquitectónicos descubiertos. No todos deben desarrollarse con la misma profundidad ni convertirse en ADR durante esta entrega.]

| ID | Asunto formulado como pregunta neutral | Origen | Interesados afectados | Importancia y costo de cambio | Estado |
|---|---|---|---|---|---|
| AD-01 | [¿Cómo...?] | [ASR-XX, EC-XX, RN-XX, RES-XX] | [INT-XX] | [Justificación] | [Analizado / Pendiente] |
| AD-02 | [¿Cómo...?] | [ASR-XX, EC-XX, RN-XX, RES-XX] | [INT-XX] | [Justificación] | [Analizado / Pendiente] |
| AD-03 | [¿Cómo...?] | [ASR-XX, EC-XX, RN-XX, RES-XX] | [INT-XX] | [Justificación] | [Analizado / Pendiente] |

### 2.2 Priorización

[Explique por qué se analizarán en profundidad los asuntos seleccionados. Considere impacto, costo de cambio, relación con atributos de calidad, riesgo, incertidumbre y relevancia para el recorrido vertical.]

---

## 3. Evaluación de alternativas arquitectónicas

> Repita la siguiente estructura para cada asunto priorizado. Se deben analizar en profundidad entre dos y tres asuntos significativos.

### 3.1 AD-01 — [Nombre breve del asunto]

#### Asunto de decisión

> [Formule una pregunta neutral.]

#### Contexto y trazabilidad

- **ASR relacionados:** [ASR-XX]
- **Requisitos funcionales:** [RF-XX]
- **Reglas o invariantes:** [RN-XX]
- **Escenarios de calidad:** [EC-XX]
- **Restricciones:** [RES-XX]
- **Interesados afectados:** [INT-XX]
- **Riesgos iniciales:** [RA-XX o descripción]

#### Criterios de evaluación

##### Obligatorios

- [Criterio que ninguna alternativa puede incumplir]

##### Prioritarios

- [Criterio determinante para elegir]
- [Criterio determinante para elegir]

##### Deseables

- [Criterio de desempate o reducción de costo]

#### ALT-01A — [Nombre de la alternativa]

- **Descripción:** [Organización o comportamiento propuesto]
- **Supuestos:** [SUP-XX o descripción]
- **Beneficios:** [Qué favorece]
- **Costos o sacrificios:** [Qué perjudica o encarece]
- **Riesgos:** [RA-XX o descripción]
- **Puntos sensibles:** [Propiedades cuya variación produce un impacto importante]
- **Elementos arquitectónicos afectados:** [Sistema, contenedor, integración, almacenamiento]
- **Evidencia disponible:** [Evidencia actual o Ninguna]
- **Evidencia necesaria:** [EV-XX]

#### ALT-01B — [Nombre de la alternativa]

- **Descripción:** [Organización o comportamiento propuesto]
- **Supuestos:** [SUP-XX o descripción]
- **Beneficios:** [Qué favorece]
- **Costos o sacrificios:** [Qué perjudica o encarece]
- **Riesgos:** [RA-XX o descripción]
- **Puntos sensibles:** [Propiedades cuya variación produce un impacto importante]
- **Elementos arquitectónicos afectados:** [Sistema, contenedor, integración, almacenamiento]
- **Evidencia disponible:** [Evidencia actual o Ninguna]
- **Evidencia necesaria:** [EV-XX]

#### Comparación

| Criterio | Tipo | ALT-01A | ALT-01B | Observaciones y evidencia faltante |
|---|---|---|---|---|
| [Criterio] | [Obligatorio / Prioritario / Deseable] | [Cumple / No cumple / Condicionado / Requiere evidencia / Introduce riesgo] | [Resultado] | [Explicación] |

#### Decisión provisional

- **Alternativa seleccionada:** [ALT-01X]
- **Justificación:** [Razones relacionadas con los criterios y el contexto]
- **Alternativas descartadas:** [Alternativas y motivos]
- **Consecuencias positivas:** [Consecuencias]
- **Consecuencias negativas aceptadas:** [Costos, sacrificios o deuda]
- **Riesgos pendientes:** [RA-XX]
- **Supuestos pendientes:** [SUP-XX]
- **Evidencia por obtener:** [EV-XX]
- **Condiciones de revisión:** [Cambios o resultados que obligarían a reconsiderar la decisión]
- **ADR correspondiente:** [ADR-001]

---

### 3.2 AD-02 — [Nombre breve del asunto]

[Repita íntegramente la estructura utilizada en AD-01.]

---

### 3.3 AD-03 — [Nombre breve del asunto, si aplica]

[Repita íntegramente la estructura utilizada en AD-01.]

---

## 4. Consolidación de la arquitectura candidata

### 4.1 Síntesis

[Explique cómo las decisiones provisionales forman una solución coherente. No se limite a nombrar un estilo arquitectónico.]

### 4.2 Organización general

- **Sistema objeto de estudio:** [Nombre y responsabilidad]
- **Unidad o unidades de ejecución:** [Descripción]
- **Almacenamientos:** [Descripción]
- **Fronteras externas:** [Descripción]
- **Responsabilidades principales:** [Descripción]
- **Dirección de las dependencias:** [Descripción]
- **Mecanismos generales de comunicación:** [HTTP, mensajería, acceso a datos, etc., solo si están justificados]

### 4.3 Relación con el recorrido vertical

- **Entrada del recorrido:** [Entrada]
- **Contenedor que recibe la entrada:** [CON-XX]
- **Responsabilidad principal:** [Descripción]
- **Reglas protegidas:** [RN-XX]
- **Persistencia prevista:** [CON-XX o pendiente]
- **Integración externa:** [EXT-XX o No aplica]
- **Resultado observable:** [Resultado]

### 4.4 Decisiones que conforman la arquitectura

| Decisión | Contribución a la arquitectura | Elementos afectados | ADR |
|---|---|---|---|
| AD-01 | [Contribución] | [CON-XX, EXT-XX] | ADR-001 |
| AD-02 | [Contribución] | [CON-XX] | ADR-002 |

### 4.5 Decisiones diferidas

| Asunto pendiente | Razón para diferirlo | Momento o evidencia necesaria |
|---|---|---|
| [AD-XX o pregunta] | [Razón] | [Entrega, prototipo o prueba] |

---

## 5. Vistas C4

### 5.1 Fuente del modelo

- **Archivo Structurizr DSL:** [`diagramas/workspace.dsl`](diagramas/workspace.dsl)

### 5.2 C4 de Contexto, nivel 1

[Incluya la exportación SVG cuando esté disponible.]

```markdown
![C4 de Contexto](diagramas/c4-contexto.svg)
```

#### Explicación

- **Sistema representado:** [Nombre]
- **Personas:** [Relacionar con INT-XX]
- **Sistemas externos:** [Relacionar con RES-XX, ASR-XX o AD-XX]
- **Límite del sistema:** [Explicación]
- **Relaciones principales:** [Explicación]

### 5.3 C4 de Contenedores, nivel 2

[Incluya la exportación SVG cuando esté disponible.]

```markdown
![C4 de Contenedores](diagramas/c4-contenedores.svg)
```

#### Catálogo de contenedores

| ID | Contenedor | Responsabilidad | Tecnología candidata | Decisiones relacionadas |
|---|---|---|---|---|
| CON-01 | [Nombre] | [Responsabilidad] | [Tecnología o Por definir] | [AD-XX, ADR-XXX] |
| CON-02 | [Nombre] | [Responsabilidad] | [Tecnología o Por definir] | [AD-XX, ADR-XXX] |

#### Coherencia entre vistas

[Explique cómo el sistema mostrado como una unidad en el diagrama de Contexto se descompone en los contenedores de la segunda vista.]

---

## 6. Riesgos, supuestos, puntos sensibles y evidencia pendiente

### 6.1 Riesgos arquitectónicos

| ID | Riesgo | Origen | Probabilidad | Impacto | Acción inicial |
|---|---|---|---|---|---|
| RA-01 | [Riesgo] | [ASR-XX, AD-XX, ALT-XX] | [Baja / Media / Alta] | [Bajo / Medio / Alto] | [Acción] |

### 6.2 Supuestos

| ID | Supuesto | Decisión relacionada | Consecuencia si es falso | Forma de validación |
|---|---|---|---|---|
| SUP-01 | [Supuesto] | [AD-XX / ADR-XXX] | [Consecuencia] | [EV-XX] |

### 6.3 Puntos sensibles

| Elemento o propiedad | Variación considerada | Atributo o requisito afectado | Efecto esperado | Evidencia requerida |
|---|---|---|---|---|
| [Propiedad] | [Cambio] | [EC-XX / ASR-XX] | [Efecto] | [EV-XX] |

### 6.4 Evidencia pendiente

| ID | Pregunta que debe responder | Actividad de validación | Resultado esperado | Momento previsto |
|---|---|---|---|---|
| EV-01 | [Pregunta] | [Prueba, prototipo, inspección o medición] | [Resultado verificable] | [Entrega 3 / Entrega 4] |

---

## 7. Registro de cambios y observaciones

| Fecha | Cambio | Motivo | Artefactos afectados | Responsable |
|---|---|---|---|---|
| [AAAA-MM-DD] | [Cambio] | [Motivo] | [Archivos o IDs] | [Integrante] |

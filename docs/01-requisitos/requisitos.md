# Entrega 1 — Requisitos e impulsores arquitectónicos

<!--
PLANTILLA OFICIAL DE RESPUESTA

Consulten las instrucciones completas en README.md.

Reemplacen los campos entre corchetes y eliminen los comentarios antes de realizar la entrega.

No agreguen decisiones de arquitectura, patrones, componentes, clases o tecnologías, salvo que una tecnología constituya una restricción obligatoria y se identifique claramente su origen.
-->

## 0. Identificación

- **Proyecto:** [Nombre del proyecto]
- **Integrantes:**
  - [Nombre del integrante 1]
  - [Nombre del integrante 2]
- **Grupo:** [Identificación del grupo]
- **Fecha:** [AAAA-MM-DD]
- **Commit o etiqueta de entrega:** [Identificador]

---

## 1. Alcance validado

### 1.1 Propósito

[Describan brevemente el resultado que busca producir la solución.]

### 1.2 Interesados principales

| ID | Interesado o rol | Necesidad o preocupación principal |
|---|---|---|
| INT-01 | [Interesado] | [Necesidad o preocupación] |
| INT-02 | [Interesado] | [Necesidad o preocupación] |
| INT-03 | [Interesado] | [Necesidad o preocupación] |

### 1.3 Flujo principal

- **Nombre:** [Nombre del flujo]
- **Iniciado por:** [Actor o sistema]
- **Evento de inicio:** [Evento]
- **Resultado observable:** [Resultado]

1. [Paso 1]
2. [Paso 2]
3. [Paso 3]
4. [Paso 4]
5. [Paso 5]
6. [Paso 6]

### 1.4 Alcance incluido

- [Elemento incluido]
- [Elemento incluido]
- [Elemento incluido]

### 1.5 Fuera de alcance

- [Elemento excluido]
- [Elemento excluido]
- [Elemento excluido]

### 1.6 Recorrido vertical previsto

- **Entrada:** [Solicitud, comando, mensaje o evento]
- **Actor que lo inicia:** [INT-XX]
- **Comportamiento principal:** [Descripción]
- **Reglas involucradas:** [RN-XX, RN-XX]
- **Resultado observable:** [Resultado]
- **Requisitos que cubrirá:** [RF-XX, RF-XX]

---

## 2. Requisitos funcionales y criterios de aceptación

<!--
Documenten entre cinco y ocho requisitos.

Cada requisito debe tener al menos un criterio de aceptación. Los requisitos Must deben incluir un escenario alternativo o de error cuando resulte relevante.

Dupliquen la estructura cuando sea necesario y mantengan la numeración consecutiva.
-->

### RF-01 — [Nombre breve]

> Como [rol o interesado],  
> quiero [capacidad],  
> para [beneficio o resultado].

- **Prioridad:** [Must / Should / Could]
- **Reglas relacionadas:** [RN-XX o No aplica]

#### CA-01 — [Nombre del criterio]

```gherkin
Scenario: [Nombre del escenario]
  Given [contexto o estado inicial]
  When [acción o evento]
  Then [resultado observable]
```

#### CA-02 — [Escenario alternativo o de error, si aplica]

```gherkin
Scenario: [Nombre del escenario]
  Given [contexto o estado inicial]
  When [acción o evento]
  Then [resultado observable]
```

---

### RF-02 — [Nombre breve]

> Como [rol o interesado],  
> quiero [capacidad],  
> para [beneficio o resultado].

- **Prioridad:** [Must / Should / Could]
- **Reglas relacionadas:** [RN-XX o No aplica]

#### CA-03 — [Nombre del criterio]

```gherkin
Scenario: [Nombre del escenario]
  Given [contexto o estado inicial]
  When [acción o evento]
  Then [resultado observable]
```

---

### RF-03 — [Nombre breve]

> Como [rol o interesado],  
> quiero [capacidad],  
> para [beneficio o resultado].

- **Prioridad:** [Must / Should / Could]
- **Reglas relacionadas:** [RN-XX o No aplica]

#### CA-04 — [Nombre del criterio]

```gherkin
Scenario: [Nombre del escenario]
  Given [contexto o estado inicial]
  When [acción o evento]
  Then [resultado observable]
```

---

### RF-04 — [Nombre breve]

> Como [rol o interesado],  
> quiero [capacidad],  
> para [beneficio o resultado].

- **Prioridad:** [Must / Should / Could]
- **Reglas relacionadas:** [RN-XX o No aplica]

#### CA-05 — [Nombre del criterio]

```gherkin
Scenario: [Nombre del escenario]
  Given [contexto o estado inicial]
  When [acción o evento]
  Then [resultado observable]
```

---

### RF-05 — [Nombre breve]

> Como [rol o interesado],  
> quiero [capacidad],  
> para [beneficio o resultado].

- **Prioridad:** [Must / Should / Could]
- **Reglas relacionadas:** [RN-XX o No aplica]

#### CA-06 — [Nombre del criterio]

```gherkin
Scenario: [Nombre del escenario]
  Given [contexto o estado inicial]
  When [acción o evento]
  Then [resultado observable]
```

<!-- Agreguen RF-06, RF-07 y RF-08 únicamente si son necesarios. -->

---

## 3. Reglas de negocio

<!-- Documenten entre tres y seis reglas de negocio. -->

### RN-01 — [Nombre breve]

- **Descripción:** [Regla]
- **Condición:** [Cuándo se aplica]
- **Consecuencia:** [Qué ocurre al aplicarla]
- **Requisitos relacionados:** [RF-XX, RF-XX]

### RN-02 — [Nombre breve]

- **Descripción:** [Regla]
- **Condición:** [Cuándo se aplica]
- **Consecuencia:** [Qué ocurre al aplicarla]
- **Requisitos relacionados:** [RF-XX, RF-XX]

### RN-03 — [Nombre breve]

- **Descripción:** [Regla]
- **Condición:** [Cuándo se aplica]
- **Consecuencia:** [Qué ocurre al aplicarla]
- **Requisitos relacionados:** [RF-XX, RF-XX]

<!-- Agreguen RN-04, RN-05 y RN-06 únicamente si son necesarias. -->

---

## 4. Escenarios de calidad

<!-- Documenten al menos tres escenarios de calidad medibles. -->

### EC-01 — [Nombre del escenario]

- **Atributo de calidad:** [Atributo]
- **Fuente del estímulo:** [Fuente]
- **Estímulo:** [Evento o condición]
- **Entorno:** [Entorno]
- **Artefacto afectado:** [Artefacto]
- **Respuesta esperada:** [Respuesta]
- **Medida de respuesta:** [Medida]
- **Forma prevista de verificación:** [Forma de verificación]

### EC-02 — [Nombre del escenario]

- **Atributo de calidad:** [Atributo]
- **Fuente del estímulo:** [Fuente]
- **Estímulo:** [Evento o condición]
- **Entorno:** [Entorno]
- **Artefacto afectado:** [Artefacto]
- **Respuesta esperada:** [Respuesta]
- **Medida de respuesta:** [Medida]
- **Forma prevista de verificación:** [Forma de verificación]

### EC-03 — [Nombre del escenario]

- **Atributo de calidad:** [Atributo]
- **Fuente del estímulo:** [Fuente]
- **Estímulo:** [Evento o condición]
- **Entorno:** [Entorno]
- **Artefacto afectado:** [Artefacto]
- **Respuesta esperada:** [Respuesta]
- **Medida de respuesta:** [Medida]
- **Forma prevista de verificación:** [Forma de verificación]

---

## 5. Requisitos arquitectónicamente significativos

<!--
Incluyan solamente los requisitos que pueden influir de manera significativa en decisiones posteriores de arquitectura.

No registren tecnologías, patrones o estilos arquitectónicos como si fueran ASR.
-->

| ID | Elemento de origen | Justificación de importancia arquitectónica |
|---|---|---|
| ASR-01 | [RF-XX / RN-XX / EC-XX / RES-XX] | [Justificación] |
| ASR-02 | [RF-XX / RN-XX / EC-XX / RES-XX] | [Justificación] |
| ASR-03 | [RF-XX / RN-XX / EC-XX / RES-XX] | [Justificación] |

---

## 6. Restricciones

| ID | Descripción | Origen | Consecuencia para el proyecto |
|---|---|---|---|
| RES-01 | [Restricción] | [Origen] | [Consecuencia] |
| RES-02 | [Restricción] | [Origen] | [Consecuencia] |
| RES-03 | [Restricción] | [Origen] | [Consecuencia] |

---

## 7. Matriz inicial de trazabilidad

<!--
Utilicen los identificadores definidos en las secciones anteriores.

Escriban “No aplica” cuando una relación no exista. No inventen relaciones únicamente para completar las celdas.
-->

| Requisito | Interesado | Criterios de aceptación | Reglas de negocio | Escenarios de calidad | ASR | Restricciones |
|---|---|---|---|---|---|---|
| RF-01 | [INT-XX] | [CA-XX, CA-XX] | [RN-XX o No aplica] | [EC-XX o No aplica] | [ASR-XX o No] | [RES-XX o No aplica] |
| RF-02 | [INT-XX] | [CA-XX] | [RN-XX o No aplica] | [EC-XX o No aplica] | [ASR-XX o No] | [RES-XX o No aplica] |
| RF-03 | [INT-XX] | [CA-XX] | [RN-XX o No aplica] | [EC-XX o No aplica] | [ASR-XX o No] | [RES-XX o No aplica] |
| RF-04 | [INT-XX] | [CA-XX] | [RN-XX o No aplica] | [EC-XX o No aplica] | [ASR-XX o No] | [RES-XX o No aplica] |
| RF-05 | [INT-XX] | [CA-XX] | [RN-XX o No aplica] | [EC-XX o No aplica] | [ASR-XX o No] | [RES-XX o No aplica] |

<!-- Agreguen filas si documentaron RF-06, RF-07 o RF-08. -->

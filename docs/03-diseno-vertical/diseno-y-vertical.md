# Entrega 3 — Diseño interno y primer recorrido vertical

<!--
PLANTILLA OFICIAL DE RESPUESTA.
Reemplacen los campos entre corchetes y eliminen los comentarios antes de entregar.
No documenten funcionalidades que no estén implementadas en el commit de entrega.
-->

## 0. Identificación

- **Proyecto:** [Nombre]
- **Integrantes:** [Nombres]
- **Grupo:** [Grupo]
- **Fecha:** [AAAA-MM-DD]
- **Commit o etiqueta:** [Identificador]
- **Entrega 2 usada como línea base:** [`../02-arquitectura/arquitectura.md`](../02-arquitectura/arquitectura.md)

---

## 1. Delimitación del recorrido vertical

- **ID:** UC-01
- **Nombre:** [Nombre del caso de uso]
- **Actor o sistema iniciador:** [INT-XX / EXT-XX]
- **Evento de inicio:** [Solicitud, comando o evento]
- **Propósito:** [Resultado de negocio]
- **Requisitos cubiertos:** [RF-XX]
- **Criterios de aceptación:** [CA-XX]
- **Reglas ejercidas:** [RN-XX]
- **ASR o restricciones relevantes:** [ASR-XX, RES-XX o No aplica]
- **Decisiones relacionadas:** [AD-XX, ADR-XXX]
- **Resultado observable:** [Resultado]

### 1.1 Alcance incluido

- [Comportamiento incluido]
- [Comportamiento incluido]

### 1.2 Exclusiones deliberadas

- [Funcionalidad o integración excluida y razón]
- [Funcionalidad o integración excluida y razón]

### 1.3 Escenario principal

1. [Paso]
2. [Paso]
3. [Paso]
4. [Paso]
5. [Resultado]

### 1.4 Escenario alternativo seleccionado

- **Condición:** [Condición]
- **Respuesta esperada:** [Resultado observable]
- **Justificación de su relevancia:** [Regla, riesgo o decisión que permite comprobar]

---

## 2. C4 de Componentes

- **Contenedor descompuesto:** [CON-XX — Nombre]
- **Fuente:** [`../02-arquitectura/diagramas/workspace.dsl`](../02-arquitectura/diagramas/workspace.dsl)
- **Vista:** [clave de vista en Structurizr]

![C4 de Componentes](diagramas/c4-componentes.svg)

### 2.1 Catálogo de componentes

| ID | Componente | Responsabilidad | Comportamiento ofrecido | Dependencias | Trazabilidad |
|---|---|---|---|---|---|
| CMP-01 | [Nombre] | [Responsabilidad] | [Operación] | [CMP/CON/EXT/CTR] | [RF/RN/AD/ADR] |
| CMP-02 | [Nombre] | [Responsabilidad] | [Operación] | [CMP/CON/EXT/CTR] | [RF/RN/AD/ADR] |

### 2.2 Política de dependencias

[Explique la dirección permitida de las dependencias, las fronteras y qué dependencias no deberían existir.]

### 2.3 Correspondencia con la arquitectura candidata

[Explique cómo el contenedor de la Entrega 2 se descompone en componentes sin alterar injustificadamente las decisiones registradas.]

---

## 3. Contratos e interfaces

### CTR-01 — [Nombre del contrato]

- **Tipo:** [Entrada / salida / puerto requerido / puerto ofrecido]
- **Responsable:** [CMP-XX]
- **Consumido por:** [CMP-XX]
- **Operación o mensaje:** `[Firma, estructura o referencia al código]`
- **Precondiciones:** [Condiciones]
- **Resultado exitoso:** [Resultado]
- **Errores o resultados alternativos:** [Errores]
- **Reglas relacionadas:** [RN-XX]
- **Motivo de la abstracción:** [Sustitución, aislamiento, variación o frontera]
- **Ubicación en código:** [`ruta/al/archivo`]

<!-- Repita CTR-02, CTR-03... cuando sea necesario. -->

---

## 4. Diseño dinámico

### 4.1 Escenario principal

- **Fuente:** [`diagramas/secuencia-vertical.puml`](diagramas/secuencia-vertical.puml)

![Secuencia principal](diagramas/secuencia-vertical.svg)

[Explique las decisiones importantes de la interacción. No repita literalmente el diagrama.]

### 4.2 Escenario alternativo

- **Fuente:** [Ruta al archivo reproducible]

![Secuencia alternativa](diagramas/secuencia-alternativa.svg)

[Explique dónde se detecta la condición, quién protege la regla y cómo se traduce el resultado.]

---

## 5. Correspondencia entre diseño y código

| Elemento de diseño | ID | Ruta en el código | Responsabilidad implementada | Observaciones |
|---|---|---|---|---|
| Caso de uso | UC-01 | [ruta] | [Responsabilidad] | [Observación] |
| Componente | CMP-01 | [ruta o paquete] | [Responsabilidad] | [Observación] |
| Contrato | CTR-01 | [ruta] | [Contrato] | [Observación] |
| Adaptador | CMP-XX | [ruta] | [Responsabilidad] | [Observación] |

### 5.1 Decisiones de diseño interno

#### Decisión de responsabilidad

- **Problema:** [Problema]
- **Alternativas consideradas:** [Alternativas]
- **Elección:** [Elección]
- **Justificación:** [Cohesión, acoplamiento, regla o comprobabilidad]

#### Punto de sustitución

- **Dependencia sustituida:** [Persistencia, reloj, integración, etc.]
- **Contrato:** [CTR-XX]
- **Implementación usada en el vertical:** [Nombre]
- **Por qué se requiere:** [Razón concreta]

### 5.2 Aplicación razonada de SOLID

| Principio | Evidencia en el diseño o código | Problema que evita | Ruta o elemento |
|---|---|---|---|
| SRP | [Evidencia o No aplica] | [Problema] | [Ruta/CMP] |
| OCP | [Evidencia o No aplica] | [Problema] | [Ruta/CMP] |
| LSP | [Evidencia o No aplica] | [Problema] | [Ruta/CMP] |
| ISP | [Evidencia o No aplica] | [Problema] | [Ruta/CTR] |
| DIP | [Evidencia o No aplica] | [Problema] | [Ruta/CTR] |

No es obligatorio afirmar que se aplican los cinco principios. Indiquen `No aplica` cuando no exista evidencia o necesidad real.

---

## 6. Pruebas automatizadas

### 6.1 Estrategia mínima

| ID | Tipo | Escenario | Referencias | Resultado esperado | Ruta |
|---|---|---|---|---|---|
| PR-01 | Unitaria | [Principal] | [CA-XX, RN-XX, UC-01] | [Resultado] | [ruta] |
| PR-02 | Unitaria | [Regla o invariante] | [RN-XX] | [Resultado] | [ruta] |
| PR-03 | Unitaria / componente | [Alternativo] | [CA-XX, RN-XX] | [Resultado] | [ruta] |

### 6.2 Dobles o implementaciones controladas

| Dependencia | Tipo usado | Implementación | Motivo |
|---|---|---|---|
| [Dependencia] | [Fake / stub / implementación en memoria / No aplica] | [Clase] | [Motivo] |

### 6.3 Resultado de ejecución

- **Fecha de ejecución:** [AAAA-MM-DD]
- **Comando:** `[comando]`
- **Pruebas ejecutadas:** [Cantidad]
- **Pruebas exitosas:** [Cantidad]
- **Pruebas fallidas:** [Cantidad]
- **Evidencia:** [`evidencias/resultado-pruebas.*`](evidencias/)

No peguen capturas ilegibles ni grandes volcados de consola dentro de este documento.

---

## 7. Ejecución reproducible

### 7.1 Requisitos del entorno

- [Runtime y versión]
- [Gestor de dependencias y versión]
- [Variables o archivos de configuración necesarios]

### 7.2 Preparar dependencias

```bash
[comando]
```

### 7.3 Ejecutar el recorrido

```bash
[comando]
```

### 7.4 Ejecutar todas las pruebas

```bash
[comando]
```

### 7.5 Ejecutar las pruebas del vertical

```bash
[comando]
```

### 7.6 Datos de ejemplo

[Incluya una solicitud, comando o entrada mínima y el resultado esperado. No incluya secretos.]

---

## 8. Validación de decisiones y evidencia

| Evidencia | Decisión o riesgo | Actividad realizada | Resultado | Estado | Hallazgo |
|---|---|---|---|---|---|
| EV-XX | [AD/ADR/RA/SUP] | [Actividad] | [Resultado observable] | [Validada/Parcial/No validada/Reprogramada] | [HV-XX] |

### HV-01 — [Nombre del hallazgo]

- **Evidencia de origen:** [EV-XX / PR-XX]
- **Qué se observó:** [Observación]
- **Interpretación:** [Qué significa para el diseño]
- **Decisión afectada:** [AD-XX / ADR-XXX]
- **Acción tomada:** [Confirmar, ajustar, reemplazar, diferir]
- **Archivos actualizados:** [Rutas]

---

## 9. Cambios respecto de la Entrega 2

| Fecha | Cambio | Motivo | Artefactos afectados | Decisión o hallazgo relacionado |
|---|---|---|---|---|
| [AAAA-MM-DD] | [Cambio] | [Motivo] | [Rutas] | [ADR/HV/EV] |

---

## 10. Limitaciones y trabajo pendiente

- [Limitación real del vertical]
- [Riesgo pendiente]
- [Escenario todavía no comprobado]
- [Siguiente incremento razonable]

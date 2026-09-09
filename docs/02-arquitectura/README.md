# Entrega 2 — Arquitectura candidata

## 1. Propósito

En esta entrega, cada equipo deberá transformar los impulsores identificados en la Entrega 1 en un conjunto coherente de decisiones arquitectónicas provisionales.

La arquitectura presentada tendrá el carácter de **arquitectura candidata**. No se considera una solución definitiva ni congelada. Sus decisiones deberán validarse posteriormente mediante el primer recorrido vertical, las pruebas automatizadas y la evaluación arquitectónica.

La entrega debe mostrar la siguiente cadena de razonamiento:

```text
Requisitos, reglas, escenarios de calidad, ASR y restricciones
                            ↓
Modelo conceptual del dominio
                            ↓
Asuntos de decisión arquitectónica
                            ↓
Alternativas arquitectónicas comparables
                            ↓
Criterios, consecuencias, riesgos y trade-offs
                            ↓
Decisiones arquitectónicas provisionales
                            ↓
Arquitectura candidata y vistas C4
                            ↓
ADR y evidencia pendiente de validación
```

No se evaluará la arquitectura por su complejidad, modernidad o cantidad de tecnologías. Se evaluará la coherencia entre el problema, los impulsores, las alternativas consideradas, las decisiones adoptadas y las evidencias propuestas para validarlas.

---

## 2. Relación con las entregas anteriores

La Entrega 2 utiliza como entrada los artefactos existentes en:

```text
docs/00-propuesta/propuesta.md
docs/01-requisitos/requisitos.md
```

No se deben copiar ni resumir los requisitos dentro de esta carpeta. Los elementos de la Entrega 1 deberán referenciarse mediante sus identificadores existentes:

- `INT-XX`: interesado.
- `RF-XX`: requisito funcional.
- `CA-XX`: criterio de aceptación.
- `RN-XX`: regla de negocio.
- `EC-XX`: escenario de calidad.
- `ASR-XX`: requisito arquitectónicamente significativo.
- `RES-XX`: restricción.

Cuando se detecte una inconsistencia en la Entrega 1, el equipo deberá registrarla y discutirla con el docente. No se debe modificar silenciosamente el significado de un requisito o ASR ya utilizado como origen de una decisión arquitectónica.

---

## 3. Estructura de archivos

```text
docs/
└── 02-arquitectura/
    ├── README.md
    ├── arquitectura.md
    ├── trazabilidad-arquitectonica.md
    ├── diagramas/
    │   └── workspace.dsl
    └── adr/
        ├── ADR-001-*.md
        ├── ADR-002-*.md
        └── ADR-003-*.md
```

### `README.md`

Contiene el enunciado, las instrucciones, las condiciones y los criterios de evaluación. Este archivo no debe ser modificado por los equipos, salvo indicación expresa del docente.

### `arquitectura.md`

Es el documento principal. Contiene:

1. La identificación de la entrega.
2. El modelo conceptual del dominio.
3. Los asuntos de decisión arquitectónica priorizados.
4. La evaluación de alternativas arquitectónicas.
5. Las decisiones provisionales.
6. La consolidación de la arquitectura candidata.
7. Los riesgos, supuestos, puntos sensibles y evidencias pendientes.
8. Los enlaces a los diagramas C4 y los ADR.

### `trazabilidad-arquitectonica.md`

Continúa la trazabilidad iniciada en la Entrega 1. Relaciona los impulsores con los asuntos de decisión, las alternativas, las decisiones provisionales, los ADR, los elementos C4 y las evidencias pendientes.

### `diagramas/workspace.dsl`

Contiene el modelo Structurizr DSL utilizado para generar:

- Diagrama C4 de Contexto, nivel 1.
- Diagrama C4 de Contenedores, nivel 2.

Ambas vistas deben generarse a partir del mismo modelo.

### `adr/ADR-00X-*.md`

Cada archivo registra una decisión arquitectónica significativa. Se entregarán normalmente entre dos y tres ADR preliminares.

---

## 4. Identificadores nuevos

Para la Entrega 2 se utilizarán los siguientes prefijos:

| Elemento | Prefijo | Ejemplo |
|---|---|---|
| Asunto de decisión arquitectónica | `AD` | `AD-01` |
| Alternativa asociada a un asunto | `ALT` | `ALT-01A` |
| Registro de decisión arquitectónica | `ADR` | `ADR-001` |
| Riesgo arquitectónico | `RA` | `RA-01` |
| Supuesto arquitectónico | `SUP` | `SUP-01` |
| Evidencia pendiente | `EV` | `EV-01` |
| Contenedor C4 | `CON` | `CON-01` |
| Sistema externo, si se requiere referenciarlo | `EXT` | `EXT-01` |

Las alternativas deben asociarse al asunto que responden. Por ejemplo:

```text
AD-01
├── ALT-01A
├── ALT-01B
└── ALT-01C
```

El asunto `AD-01` puede formalizarse posteriormente mediante `ADR-001`. No todos los asuntos identificados deben convertirse obligatoriamente en ADR. Solo se registrarán como ADR las decisiones arquitectónicamente significativas.

---

## 5. Contenido requerido

### 5.1 Modelo conceptual del dominio

El equipo deberá representar los conceptos relevantes del negocio antes de definir estructuras detalladas de software.

Debe incluir, cuando sean pertinentes:

- Conceptos principales del dominio.
- Entidades.
- Objetos de valor.
- Relaciones y cardinalidades justificadas.
- Estados y transiciones relevantes.
- Reglas e invariantes.
- Límites de consistencia.
- Contextos delimitados preliminares.
- Glosario de términos ambiguos o fundamentales.

El modelo conceptual no debe convertirse en:

- un modelo de tablas;
- un diagrama técnico de clases;
- una lista de controladores o servicios;
- una representación del framework;
- una anticipación injustificada de microservicios.

El modelo deberá explicarse en `arquitectura.md`. Puede incluirse allí una imagen, un enlace a un archivo editable o un diagrama de texto reproducible. Las referencias a `RF-XX`, `RN-XX` y `CA-XX` deben registrarse en la explicación, sin saturar necesariamente el diagrama.

### 5.2 Asuntos de decisión arquitectónica

El equipo identificará los asuntos que requieren una decisión significativa. Cada asunto deberá:

- formularse como una pregunta neutral;
- indicar su origen;
- explicar por qué tiene impacto arquitectónico;
- reconocer a los interesados afectados;
- identificar la evidencia que falta para resolver la incertidumbre.

Ejemplo adecuado:

> ¿Cómo evitar que la indisponibilidad de una integración secundaria invalide el flujo principal?

Ejemplo inadecuado:

> ¿Cómo implementaremos el patrón Adapter?

El segundo enunciado presupone una solución antes de comparar alternativas.

### 5.3 Evaluación de alternativas arquitectónicas

Se deberán analizar en profundidad entre **dos y tres asuntos de decisión significativos**. Para cada asunto se compararán al menos **dos alternativas arquitectónicas viables y diferenciadas**.

Las alternativas deben:

- responder al mismo asunto;
- ser viables bajo las restricciones conocidas;
- representar respuestas realmente diferentes;
- hacer explícitos sus beneficios, costos, riesgos y supuestos;
- poder compararse mediante criterios relacionados con el contexto;
- indicar qué evidencia permitiría validarlas.

Cambiar únicamente el nombre de una tecnología no constituye necesariamente una alternativa arquitectónica diferente.

Para cada asunto deberán establecerse criterios:

- **Obligatorios:** si una alternativa no los cumple, se descarta o reformula.
- **Prioritarios:** influyen directamente en la selección.
- **Deseables:** ayudan a desempatar o reducir costos.

La comparación debe utilizar razonamientos como:

- Cumple.
- No cumple.
- Cumple bajo una condición.
- Requiere evidencia.
- Introduce un riesgo.

No se recomienda utilizar puntuaciones numéricas sin una justificación explícita.

### 5.4 Decisiones arquitectónicas provisionales

Para cada asunto analizado se deberá indicar:

- alternativa seleccionada;
- justificación;
- alternativas descartadas y motivo;
- consecuencias positivas;
- consecuencias negativas o costos aceptados;
- riesgos y supuestos pendientes;
- evidencia que deberá obtenerse;
- condiciones que obligarían a revisar la decisión.

La decisión es provisional hasta que la evidencia obtenida en la implementación y las pruebas permita aceptarla, modificarla o reemplazarla.

### 5.5 Arquitectura candidata

El equipo deberá explicar cómo las decisiones provisionales conforman una solución coherente. No basta con mencionar una etiqueta como “arquitectura hexagonal”, “arquitectura en capas” o “monolito modular”.

La consolidación deberá explicar:

- organización general del sistema;
- responsabilidades principales;
- límites relevantes;
- dirección de las dependencias;
- unidades de ejecución y almacenamiento;
- fronteras con sistemas externos;
- relación con el recorrido vertical previsto;
- decisiones aún no tomadas;
- aspectos que deberán comprobarse posteriormente.

### 5.6 Diagramas C4

Los diagramas C4 deberán construirse con **Structurizr DSL** a partir de un único archivo:

```text
diagramas/workspace.dsl
```

El archivo deberá definir al menos dos vistas:

- `systemContext`: C4 de Contexto.
- `container`: C4 de Contenedores.

#### C4 de Contexto

Debe mostrar:

- el sistema objeto de estudio;
- los tipos de usuario o actores relevantes;
- los sistemas externos;
- las relaciones principales;
- el propósito de las interacciones;
- el límite del sistema.

No debe mostrar bases de datos internas, clases, controladores, módulos, frameworks ni endpoints individuales.

#### C4 de Contenedores

Debe mostrar:

- aplicaciones, servicios ejecutables y almacenamientos;
- responsabilidades principales;
- relaciones y mecanismos generales de comunicación;
- sistemas externos relevantes;
- tecnologías candidatas, cuando estén justificadas.

No debe confundir capas, paquetes o namespaces con contenedores. En C4, un contenedor es una aplicación o almacenamiento que debe ejecutarse o desplegarse para que el sistema funcione.

#### Evidencia entregable

El repositorio deberá incluir:

- `workspace.dsl` como fuente editable;
- una exportación legible del diagrama de Contexto;
- una exportación legible del diagrama de Contenedores.

Se recomienda SVG. No se aceptan capturas de pantalla ni enlaces externos como única evidencia.

### 5.7 Registros de decisiones arquitectónicas

Se deberán entregar normalmente entre **dos y tres ADR preliminares**.

Cada ADR deberá:

- corresponder a una decisión significativa;
- enlazar un asunto `AD-XX`;
- referenciar sus elementos de origen;
- resumir las alternativas consideradas;
- registrar la decisión actual;
- reconocer sus consecuencias;
- indicar riesgos y evidencia pendiente;
- incluir condiciones de revisión.

Los estados permitidos inicialmente son:

- `Propuesto`.
- `Aceptado`.
- `Rechazado`.
- `Reemplazado por ADR-XXX`.

Para esta entrega es normal que los ADR permanezcan en estado `Propuesto`.

### 5.8 Riesgos, supuestos, puntos sensibles y evidencia

El equipo deberá registrar:

- riesgos que podrían impedir el cumplimiento de un requisito o escenario;
- supuestos que todavía no han sido comprobados;
- puntos sensibles donde un cambio pequeño puede afectar significativamente la calidad;
- preguntas abiertas;
- evidencia necesaria;
- momento previsto de validación.

Las evidencias pendientes deben formularse como actividades observables. Por ejemplo:

- ejecutar solicitudes concurrentes y verificar que no se viola `RN-02`;
- sustituir una integración externa por un stub;
- medir el percentil 95 del tiempo de respuesta;
- cambiar el mecanismo de persistencia y registrar los módulos afectados;
- simular indisponibilidad del servicio externo.

---

## 6. Elementos que no se solicitan todavía

En esta entrega no se requiere:

- código ejecutable completo del recorrido vertical;
- C4 de Componentes, nivel 3;
- diseño definitivo de clases;
- diagramas de secuencia;
- selección obligatoria de patrones de diseño;
- implementación de repositorios, adaptadores o servicios;
- suite completa de pruebas;
- pipeline de integración continua;
- Dockerfile;
- interfaz gráfica;
- despliegue en la nube;
- arquitectura definitiva o congelada.

Los prototipos exploratorios son válidos si sirven para reducir un riesgo, pero no sustituyen los artefactos solicitados.

---

## 7. Condiciones de entrega

Antes de entregar, el equipo deberá verificar que:

- Todos los archivos se visualizan correctamente.
- No quedan campos de plantilla sin completar.
- Los identificadores son únicos y consistentes.
- Toda referencia a `RF`, `RN`, `EC`, `ASR` o `RES` existe en la Entrega 1.
- Los asuntos están formulados como preguntas neutrales.
- Cada asunto analizado tiene al menos dos alternativas viables.
- Las alternativas responden al mismo asunto.
- Los criterios se relacionan con el contexto y no con preferencias personales.
- Las decisiones reconocen consecuencias y riesgos.
- Los ADR coinciden con las decisiones documentadas.
- El C4 de Contexto y el C4 de Contenedores provienen del mismo `workspace.dsl`.
- El C4 de Contexto no contiene detalles internos.
- El C4 de Contenedores no confunde capas con contenedores.
- Las relaciones C4 tienen descripciones comprensibles.
- Las imágenes exportadas son legibles.
- Ambos integrantes pueden explicar la totalidad de la entrega.

---

## 8. Evaluación individual

Aunque la entrega se realiza en pareja, ambos integrantes son responsables de todo su contenido. Durante la revisión, cualquiera podrá ser consultado sobre:

- conceptos, reglas e invariantes del modelo conceptual;
- origen de los asuntos arquitectónicos;
- diferencias entre las alternativas;
- criterios obligatorios y prioritarios;
- consecuencias y trade-offs;
- justificación de las decisiones provisionales;
- diferencias entre Contexto y Contenedores en C4;
- contenido de los ADR;
- riesgos y supuestos;
- evidencia requerida para validar la arquitectura.

La distribución interna del trabajo no exime a ningún integrante de comprender y defender la solución completa.

---

## 9. Criterios de evaluación sugeridos

| Criterio | Peso |
|---|---:|
| Modelo conceptual del dominio | 15 % |
| Formulación y trazabilidad de asuntos arquitectónicos | 10 % |
| Calidad de las alternativas y criterios de comparación | 20 % |
| Justificación de decisiones y arquitectura candidata | 15 % |
| C4 de Contexto | 10 % |
| C4 de Contenedores y coherencia entre vistas | 15 % |
| ADR y trazabilidad arquitectónica | 10 % |
| Riesgos, supuestos y evidencia pendiente | 5 % |
| **Total** | **100 %** |

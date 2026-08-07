# Entrega 1 — Requisitos e impulsores arquitectónicos

## 1. Propósito

En esta entrega, cada equipo deberá refinar la propuesta presentada en la Entrega 0 y convertirla en una especificación inicial de los requisitos del proyecto.

El propósito es establecer una base clara para las decisiones de arquitectura que se tomarán posteriormente. Por esta razón, la entrega deberá concentrarse en describir:

- Qué parte del problema atenderá el proyecto.
- Quiénes están interesados en la solución.
- Qué comportamientos deberá ofrecer el sistema.
- Qué reglas del dominio deberá respetar.
- Qué características de calidad deberán ser verificables.
- Qué requisitos pueden influir significativamente en la arquitectura.
- Qué restricciones condicionan el proyecto.
- Cómo se relacionan los diferentes elementos documentados.

La entrega debe mostrar una cadena coherente:

```text
Alcance
   ↓
Requisitos funcionales
   ↓
Criterios de aceptación y reglas de negocio
   ↓
Escenarios de calidad y restricciones
   ↓
Requisitos arquitectónicamente significativos
   ↓
Trazabilidad inicial
```

En esta entrega todavía no se debe definir la arquitectura del sistema.

---

## 2. Archivos de la entrega

La documentación estará organizada de la siguiente manera:

```text
docs/
└── 01-requisitos/
    ├── README.md
    └── requisitos.md
```

### `README.md`

Contiene el enunciado, las instrucciones y los criterios de evaluación.

Este archivo no debe ser modificado por los equipos.

### `requisitos.md`

Contiene la plantilla oficial de la entrega.

El equipo deberá completar sus secciones con la información correspondiente al proyecto.

No se deben crear documentos adicionales para sustituir esta plantilla, salvo autorización expresa del docente.

---

## 3. Relación con la Entrega 0

La Entrega 1 parte de la propuesta preliminar aprobada.

No se espera que el equipo copie completamente el contenido de `docs/00-propuesta/propuesta.md`. Debe revisarlo, corregirlo y convertirlo en una especificación más precisa de acuerdo a los temas vistos en clase.

El archivo de la Entrega 0 debe conservarse sin modificaciones como evidencia de la evolución del proyecto.

---

## 4. Identificadores

Los elementos de la entrega deberán tener identificadores únicos.

| Elemento | Prefijo | Ejemplo |
|---|---|---|
| Interesado | `INT` | `INT-01` |
| Requisito funcional | `RF` | `RF-01` |
| Criterio de aceptación | `CA` | `CA-01` |
| Regla de negocio | `RN` | `RN-01` |
| Escenario de calidad | `EC` | `EC-01` |
| Requisito arquitectónicamente significativo | `ASR` | `ASR-01` |
| Restricción | `RES` | `RES-01` |

Los mismos identificadores deben utilizarse en todas las secciones.

Por ejemplo, si una historia de usuario está identificada como `RF-01`, la matriz de trazabilidad debe referirse a ella como `RF-01`.

---

# 5. Contenido requerido

## 5.1 Alcance validado

El alcance validado deberá establecer qué parte del problema será atendida durante el proyecto.

Debe incluir:

- Propósito de la solución.
- Interesados principales.
- Flujo principal refinado.
- Elementos incluidos.
- Elementos fuera de alcance.
- Recorrido vertical previsto.

### Propósito

Debe expresar el resultado que busca producir la solución y no simplemente la intención de construir software.

Se debe evitar:

```text
El propósito es crear una aplicación web.
```

Es preferible expresar el resultado esperado:

```text
El propósito es reducir los conflictos en la asignación de espacios,
permitiendo registrar solicitudes y aplicar las reglas de prioridad
definidas por la institución.
```

### Interesados

Se deben identificar como mínimo tres interesados relevantes.

Para cada interesado se indicará:

- Su rol.
- Su necesidad o preocupación principal.

No se requiere realizar una matriz de poder, influencia o interés.

### Flujo principal

Debe contener entre 6 y 10 pasos y describir:

- Quién inicia el flujo.
- Qué situación lo inicia.
- Qué actividades relevantes ocurren.
- Qué resultado observable se obtiene.

El flujo debe describir el proceso del dominio, no la navegación por pantallas ni la estructura interna del código.

### Alcance incluido

Debe enumerar las capacidades que el equipo se compromete a analizar y desarrollar durante el semestre.

### Fuera de alcance

Debe enumerar las capacidades que podrían pertenecer a un producto completo, pero que no serán desarrolladas en el proyecto académico.

### Recorrido vertical previsto

Debe delimitar la parte del flujo principal que el equipo espera implementar de extremo a extremo durante el semestre.

En esta entrega basta con identificar:

- La entrada del recorrido.
- El comportamiento principal.
- Las reglas de negocio involucradas.
- El resultado observable.

Todavía no se deben definir controladores, componentes, servicios, bases de datos, patrones o clases.

---

## 5.2 Requisitos funcionales

Se deberán definir entre cinco y ocho requisitos funcionales.

Los requisitos se expresarán como historias de usuario:

```text
Como [rol],
quiero [capacidad],
para [beneficio o resultado].
```

Cada requisito funcional deberá incluir:

- Identificador.
- Nombre breve.
- Historia de usuario.
- Prioridad.
- Criterios de aceptación.
- Reglas de negocio relacionadas, cuando existan.

### Priorización

Se utilizarán las siguientes categorías:

- **Must:** imprescindible para el flujo principal o el recorrido vertical.
- **Should:** importante, pero no indispensable para el primer incremento.
- **Could:** complementario y sujeto a disponibilidad de tiempo.

Los elementos que no se desarrollarán deben registrarse en la sección de fuera de alcance, en lugar de documentarlos como requisitos comprometidos.

---

## 5.3 Criterios de aceptación

Cada requisito funcional deberá tener al menos un criterio de aceptación verificable.

Los requisitos con prioridad `Must` deberán incluir:

- Un escenario principal.
- Un escenario alternativo o de error relevante, cuando corresponda.

Los criterios se expresarán utilizando Given–When–Then:

```gherkin
Scenario: Cancelación permitida de una reserva
  Given que existe una reserva activa
  And que la cancelación se solicita dentro del plazo permitido
  When el responsable confirma la cancelación
  Then la reserva cambia al estado cancelada
  And el espacio vuelve a estar disponible
```

Los criterios deben:

- Describir comportamientos observables.
- Ser coherentes con las reglas de negocio.
- Evitar detalles internos de implementación.
- Poder convertirse posteriormente en casos de prueba.

No es necesario escribir todavía código de pruebas automatizadas.

---

## 5.4 Reglas de negocio

Se deberán especificar entre tres y seis reglas de negocio.

Una regla de negocio debe afectar alguno de los siguientes aspectos:

- Cálculos.
- Decisiones.
- Estados.
- Permisos.
- Elegibilidad.
- Prioridades.
- Restricciones temporales.
- Consecuencias ante un evento.

Ejemplo:

```text
RN-01 — Límite de reservas activas

Un usuario no puede mantener más de tres reservas activas simultáneamente.
```

No se consideran reglas de negocio suficientes las validaciones triviales, como:

- El nombre es obligatorio.
- El correo debe tener un formato válido.
- Un campo no puede estar vacío.

Una validación de datos solo se considerará regla de negocio cuando represente una política real del dominio y produzca una consecuencia relevante.

Cada regla deberá relacionarse con los requisitos funcionales que condiciona.

---

## 5.5 Escenarios de calidad

Se deberán formular al menos tres escenarios de calidad medibles.

Cada escenario deberá contener:

1. Atributo de calidad.
2. Fuente del estímulo.
3. Estímulo.
4. Entorno.
5. Artefacto afectado.
6. Respuesta esperada.
7. Medida de respuesta.
8. Forma prevista de verificación.

Los escenarios deben evitar expresiones ambiguas como:

```text
El sistema debe ser rápido.
El sistema debe ser seguro.
El sistema debe ser fácil de mantener.
```

Estas afirmaciones deben transformarse en escenarios concretos.

Ejemplo:

```text
Atributo: rendimiento
Fuente: usuario autorizado
Estímulo: consulta la disponibilidad de un espacio
Entorno: operación normal
Artefacto: sistema
Respuesta: presenta las opciones disponibles
Medida: el 95 % de las solicitudes responde en menos de dos segundos
Verificación: prueba automatizada sobre la interfaz de entrada
```

Las medidas deben ser:

- Observables.
- Realistas para el proyecto.
- Coherentes con el contexto.
- Susceptibles de ser verificadas posteriormente.

En esta entrega no es obligatorio ejecutar la verificación. Se debe indicar cómo podría realizarse en una entrega posterior.

---

## 5.6 Requisitos arquitectónicamente significativos

El equipo deberá identificar cuáles requisitos pueden tener una influencia importante sobre la arquitectura.

Un requisito arquitectónicamente significativo, o ASR, puede originarse en:

- Un requisito funcional.
- Una regla de negocio.
- Un escenario de calidad.
- Una restricción.

No todos los requisitos deben clasificarse como ASR.

Para cada ASR se deberá indicar:

- Su identificador.
- El elemento en el que se origina.
- La razón por la que puede influir en la arquitectura.

Ejemplo:

```text
ASR-01 se origina en EC-01.

Es arquitectónicamente significativo porque el tiempo máximo
de respuesta puede influir posteriormente en las decisiones
sobre persistencia, consultas y manejo de información.
```

Un ASR no es una solución técnica.

Los siguientes enunciados no son ASR:

```text
Usar PostgreSQL.
Aplicar arquitectura hexagonal.
Implementar el patrón Repository.
Construir microservicios.
```

Estos enunciados representan posibles decisiones técnicas que solo podrán justificarse posteriormente a partir de los requisitos.

En esta entrega no se deben seleccionar tácticas, estilos arquitectónicos ni patrones.

---

## 5.7 Restricciones

Se deberán registrar las restricciones conocidas que condicionan el proyecto.

Pueden ser:

- Tecnológicas.
- Académicas.
- Organizacionales.
- De infraestructura.
- De seguridad o privacidad.
- De tiempo.
- Relacionadas con una integración externa.

Cada restricción deberá indicar:

- Descripción.
- Origen.
- Consecuencia para el proyecto.

Ejemplo:

```text
RES-01

Descripción:
La aplicación debe poder ejecutarse localmente.

Origen:
Condición académica del proyecto.

Consecuencia:
La demostración no puede depender exclusivamente de servicios
disponibles en una infraestructura externa.
```

Debe distinguirse entre una restricción obligatoria y una preferencia del equipo.

Por ejemplo, si el equipo prefiere utilizar una tecnología, pero no existe una condición que la imponga, esa preferencia todavía no debe registrarse como una restricción.

---

## 5.8 Matriz inicial de trazabilidad

La matriz inicial deberá relacionar:

- Requisitos funcionales.
- Interesados.
- Criterios de aceptación.
- Reglas de negocio.
- Escenarios de calidad.
- ASR.
- Restricciones relevantes.

Las relaciones se expresarán utilizando los identificadores definidos en las demás secciones.

Ejemplo:

| Requisito | Interesado | Criterios | Reglas | Escenarios | ASR | Restricciones |
|---|---|---|---|---|---|---|
| RF-01 | INT-01 | CA-01, CA-02 | RN-01 | EC-01 | ASR-01 | RES-01 |

No todos los requisitos deben estar relacionados con todos los escenarios, restricciones o ASR.

No se deben inventar relaciones para completar todas las celdas. Cuando no exista una relación, se debe indicar `No aplica`.

La matriz es inicial: en entregas posteriores se ampliará con decisiones arquitectónicas, componentes, ADR, código y pruebas.

---

# 6. Elementos que no se solicitan

En esta entrega no se requiere:

- Definir una arquitectura candidata.
- Seleccionar un estilo arquitectónico.
- Crear diagramas C4.
- Diseñar componentes.
- Diseñar clases.
- Crear diagramas de secuencia.
- Seleccionar patrones de diseño.
- Crear registros ADR.
- Elegir una base de datos definitiva.
- Implementar el recorrido vertical.
- Escribir código de producción.
- Crear pruebas automatizadas.
- Configurar integración continua.
- Crear un Dockerfile.

Incluir estos elementos no reemplaza ninguno de los productos solicitados.

Las preferencias tecnológicas no deben presentarse como decisiones definitivas si todavía no han sido justificadas mediante requisitos, restricciones o escenarios de calidad.

---

# 7. Condiciones de entrega

Antes de entregar, el equipo deberá verificar que:

- El archivo se visualiza correctamente como Markdown.
- No quedan campos entre corchetes sin diligenciar.
- No quedan instrucciones utilizadas como respuesta.
- Los identificadores son únicos y consistentes.
- La matriz utiliza identificadores que existen.
- El alcance es coherente con la propuesta aprobada.
- Los requisitos tienen criterios de aceptación.
- Las reglas de negocio no son validaciones triviales.
- Los escenarios de calidad contienen medidas.
- Los ASR están justificados.
- No se presentan decisiones técnicas como si fueran requisitos.
- Ambos integrantes pueden explicar toda la entrega.

---


# 8. Evaluación individual

Aunque la entrega se realiza en pareja, ambos integrantes son responsables de la totalidad de su contenido.

Durante la revisión, cualquiera de los integrantes podrá ser consultado sobre:

- El alcance.
- El flujo principal.
- El recorrido vertical previsto.
- Las historias de usuario.
- Los criterios de aceptación.
- Las reglas de negocio.
- Los escenarios de calidad.
- La selección de ASR.
- Las restricciones.
- La matriz de trazabilidad.

La distribución interna del trabajo no exime a ningún integrante de comprender y defender la entrega completa.

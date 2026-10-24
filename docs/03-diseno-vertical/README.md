# Entrega 3 — Diseño interno y primer recorrido vertical

## 1. Propósito

En esta entrega, cada equipo deberá convertir una parte de la arquitectura candidata de la Entrega 2 en un diseño interno ejecutable y comprobable.

La entrega debe aportar evidencia de la siguiente cadena:

```text
RF / CA / RN / EC / ASR / RES
              ↓
Arquitectura candidata, AD y ADR
              ↓
Componentes, responsabilidades y contratos
              ↓
Interacción dinámica del caso de uso
              ↓
Código del primer recorrido vertical
              ↓
Pruebas automatizadas y evidencia
              ↓
Confirmación, ajuste o rechazo de decisiones provisionales
```

El objetivo no es completar toda la aplicación. El objetivo es implementar un recorrido pequeño, relevante y transversal que permita comprobar decisiones de diseño y arquitectura.

---

## 2. Relación con las entregas anteriores

La Entrega 3 utiliza como línea base:

```text
docs/01-requisitos/requisitos.md
docs/02-arquitectura/arquitectura.md
docs/02-arquitectura/trazabilidad-arquitectonica.md
docs/02-arquitectura/diagramas/workspace.dsl
docs/02-arquitectura/adr/
```

Los archivos de las entregas anteriores deben conservarse. Si el código o las pruebas contradicen una decisión provisional, el equipo debe registrar el hallazgo y actualizar el ADR correspondiente; no debe ocultar la inconsistencia.

---

## 3. Estructura requerida

```text
docs/
└── 03-diseno-vertical/
    ├── README.md
    ├── diseno-y-vertical.md
    ├── trazabilidad-implementacion.md
    ├── rubrica.md
    ├── diagramas/
    │   ├── README.md
    │   ├── secuencia-vertical.puml
    │   ├── c4-componentes.svg
    │   └── secuencia-vertical.svg
    └── evidencias/
        ├── README.md
        └── resultado-pruebas.*
```

Además de la documentación, el repositorio debe contener el código de producción y las pruebas automatizadas en la estructura propia de la tecnología seleccionada.

### Archivos que no deben sustituirse

- `README.md`: enunciado e instrucciones.
- `rubrica.md`: criterios de evaluación.

### Archivos que debe completar el equipo

- `diseno-y-vertical.md`.
- `trazabilidad-implementacion.md`.
- `diagramas/secuencia-vertical.puml`.
- El modelo C4 existente en `../02-arquitectura/diagramas/workspace.dsl`, añadiendo la vista de componentes correspondiente.
- Código, pruebas y evidencias.

---

## 4. Identificadores nuevos

| Elemento | Prefijo | Ejemplo |
|---|---|---|
| Componente C4 | `CMP` | `CMP-01` |
| Contrato o puerto | `CTR` | `CTR-01` |
| Caso de uso implementado | `UC` | `UC-01` |
| Prueba automatizada | `PR` | `PR-01` |
| Hallazgo de validación | `HV` | `HV-01` |

Los identificadores de las entregas anteriores deben conservarse sin renumeración.

---

## 5. Contenido requerido

### 5.1 Delimitación del primer recorrido vertical

El equipo deberá seleccionar un recorrido que:

- esté relacionado con al menos un requisito `Must`;
- produzca un resultado observable;
- ejerza al menos una regla de negocio relevante;
- atraviese la entrada, la coordinación del caso de uso, el dominio y una frontera de infraestructura;
- pueda ejecutarse y probarse de forma reproducible;
- tenga alcance suficiente para validar decisiones, pero no incluya todo el sistema.

El recorrido no debe convertirse en un conjunto de operaciones CRUD sin comportamiento de dominio.

### 5.2 C4 de Componentes, nivel 3

El equipo deberá descomponer únicamente el contenedor principal involucrado en el recorrido vertical.

La vista debe mostrar:

- componentes internos con responsabilidades diferenciadas;
- interfaces o contratos relevantes;
- dirección de las dependencias;
- relaciones con otros contenedores y sistemas externos;
- componentes que participan en el recorrido;
- trazabilidad con `CON-XX`, `AD-XX`, `ADR-XXX`, `RF-XX`, `RN-XX` o `ASR-XX` cuando corresponda.

No se debe:

- representar cada clase como componente;
- convertir paquetes del framework automáticamente en componentes;
- crear una vista de componentes por cada contenedor si no participa en el recorrido;
- dibujar manualmente un SVG que diverja del modelo fuente.

La vista deberá añadirse al mismo `workspace.dsl` utilizado en la Entrega 2. El SVG será una exportación reproducible del DSL.

### 5.3 Responsabilidades, contratos y dependencias

Para cada componente participante se deberá documentar:

- responsabilidad principal;
- comportamiento que ofrece;
- contratos de entrada y salida;
- dependencias requeridas;
- reglas que protege;
- errores o resultados alternativos relevantes.

Las abstracciones deben tener un propósito verificable. No se evaluará positivamente crear interfaces para todas las clases sin una necesidad de sustitución, aislamiento o variación.

### 5.4 Diagramas de secuencia

Se requieren dos diagramas:

1. Escenario principal del recorrido vertical.
2. Escenario alternativo o de error arquitectónicamente relevante.

Cada diagrama deberá:

- referenciar `UC-XX`, `RF-XX`, `CA-XX` y `RN-XX`;
- mostrar actor o sistema iniciador;
- mostrar entrada, caso de uso, dominio, puertos y adaptadores relevantes;
- representar retornos y resultado observable;
- evitar detalles triviales de getters, setters o framework;
- coincidir con el código entregado.

### 5.5 Código del primer recorrido vertical

El código debe incluir, cuando aplique:

- mecanismo de entrada mínimo, por ejemplo endpoint, comando o manejador;
- caso de uso o servicio de aplicación;
- objetos del dominio que protegen reglas e invariantes;
- contrato de persistencia o integración;
- adaptador ejecutable, preferentemente en memoria cuando la infraestructura real no sea necesaria para la validación;
- composición o inyección de dependencias;
- manejo explícito del escenario alternativo seleccionado.

No es obligatorio construir interfaz gráfica, autenticación completa, infraestructura de producción ni todas las funcionalidades del proyecto.

### 5.6 Pruebas automatizadas

Se deberán entregar como mínimo:

- una prueba del escenario principal;
- una prueba de una regla de negocio o invariante;
- una prueba de un escenario alternativo o de error relevante.

Las pruebas deben:

- ejecutarse mediante un único comando documentado;
- ser deterministas y repetibles;
- evitar dependencia obligatoria de servicios externos no controlados;
- comprobar resultados observables y cambios de estado;
- relacionarse con `CA-XX`, `RN-XX` y `PR-XX`.

No se exige un porcentaje mínimo de cobertura. La cobertura, si se reporta, no sustituye la calidad de los escenarios comprobados.

### 5.7 Validación de decisiones y ADR

Cada evidencia `EV-XX` prevista para la Entrega 3 deberá quedar en uno de estos estados:

- `Validada`.
- `Parcialmente validada`.
- `No validada`.
- `Reprogramada`, con justificación.

El equipo deberá registrar hallazgos `HV-XX` y determinar si cada hallazgo:

- confirma una decisión;
- exige ajustar el diseño;
- exige modificar un ADR;
- revela un riesgo o supuesto nuevo;
- obliga a revisar el alcance del recorrido.

Los ADR afectados deben actualizar su estado, evidencia e historial.

---

## 6. Elementos que no se solicitan todavía

- Aplicación completa.
- Todos los casos de uso.
- Persistencia definitiva en producción.
- Integración real con todos los servicios externos.
- Suite completa de pruebas de integración y API.
- Patrones de diseño aplicados por obligación.
- Microservicios, mensajería o eventos si el recorrido no los justifica.
- Pipeline de CI.
- Dockerfile.
- Despliegue en la nube.
- Cobertura del 100 %.
- Diseño definitivo o arquitectura congelada.

---

## 7. Comandos reproducibles

El archivo `diseno-y-vertical.md` debe documentar comandos exactos para:

1. Preparar dependencias.
2. Ejecutar el recorrido o iniciar la aplicación.
3. Ejecutar todas las pruebas.
4. Ejecutar únicamente las pruebas del vertical, si la tecnología lo permite.

No se aceptará como única instrucción “ejecutar desde el IDE”.

---

## 8. Condiciones de entrega

Antes de entregar, el equipo debe comprobar:

- [ ] El recorrido está delimitado y relacionado con requisitos existentes.
- [ ] El C4 de Componentes procede del `workspace.dsl` de la Entrega 2.
- [ ] Los SVG son legibles y reproducibles.
- [ ] Los diagramas de secuencia coinciden con el código.
- [ ] Las responsabilidades no están concentradas injustificadamente en el controlador o servicio de aplicación.
- [ ] Las dependencias apuntan en la dirección documentada.
- [ ] Existen al menos tres pruebas relevantes y todas pasan.
- [ ] Los comandos de ejecución funcionan desde un clon limpio.
- [ ] La trazabilidad usa identificadores existentes.
- [ ] Las evidencias `EV-XX` de esta entrega tienen estado y resultado.
- [ ] Los ADR afectados fueron actualizados.
- [ ] No quedan campos de plantilla sin completar.
- [ ] Ambos integrantes pueden explicar el diseño, el código y las pruebas.

---

## 9. Evaluación individual

Aunque la entrega se realiza en equipo, cualquiera de los integrantes podrá ser consultado sobre:

- selección y alcance del recorrido;
- correspondencia entre C4, secuencia y código;
- responsabilidad de cada componente;
- contratos y dirección de dependencias;
- ubicación de las reglas del dominio;
- propósito de los puntos de sustitución;
- estructura y resultado de las pruebas;
- evidencia obtenida;
- ajustes realizados a decisiones y ADR.

La división interna del trabajo no exime a ningún integrante de comprender la entrega completa.

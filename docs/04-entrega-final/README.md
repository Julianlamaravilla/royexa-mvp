# Entrega 4 — Producto final, arquitectura consolidada y sustentación

## 1. Propósito

Esta es la última entrega del curso. Cada equipo deberá terminar el alcance comprometido de su proyecto y demostrar una solución funcional, ejecutable y técnicamente defendible, consolidando lo trabajado en clase.

La entrega debe aportar evidencia de la cadena:

```text
Requisitos, reglas y escenarios de calidad
                    ↓
Arquitectura y decisiones (C4, AD y ADR)
                    ↓
Diseño interno, SOLID y patrones justificados
                    ↓
Implementación funcional del alcance comprometido
                    ↓
Integración con un servicio externo o subsistema
                    ↓
Pruebas y evidencia de evaluación
                    ↓
Sustentación y demostración final
```

## 2. Línea base y relación con entregas anteriores

La entrega parte de los artefactos existentes:

```text
docs/01-requisitos/
docs/02-arquitectura/
docs/03-diseno-vertical/
```

Los equipos deben conservar las entregas anteriores y actualizar los artefactos que hayan evolucionado. No deben duplicar toda la documentación en esta carpeta. `entrega-final.md` sintetiza el estado final y referencia los archivos fuente mediante rutas e identificadores existentes.

## 3. Resultado mínimo esperado

El repositorio debe contener una aplicación que:

- implemente de extremo a extremo el recorrido vertical principal;
- complete las funcionalidades `Must` comprometidas que sean necesarias para producir el resultado de negocio;
- proteja las reglas e invariantes relevantes del dominio;
- utilice persistencia ejecutable, ya sea permanente o controlada, según la decisión documentada;
- integre un servicio externo o subsistema distribuido real, simulado o sustituible;
- aplique patrones únicamente cuando exista un problema de diseño concreto;
- incluya pruebas automatizadas suficientes para demostrar el comportamiento crítico;
- pueda prepararse, ejecutarse y probarse con comandos reproducibles desde un ambiente limpio;
- pueda demostrarse sin depender obligatoriamente de servicios externos inestables.

No se exige implementar todas las funcionalidades `Should` o `Could`. Toda exclusión debe declararse y justificarse.

## 4. Estructura requerida

```text
docs/
└── 04-entrega-final/
    ├── README.md
    ├── entrega-final.md
    ├── trazabilidad-final.md
    ├── rubrica.md
    ├── sustentacion.md
    ├── diagramas/
    │   └── README.md
    └── evidencias/
        └── README.md
```

Además, el repositorio debe conservar el código fuente, las pruebas y los archivos de configuración propios de la tecnología del proyecto.

## 5. Contenido requerido

### 5.1 Producto funcional terminado

El equipo debe completar el alcance viable del proyecto. Como mínimo:

- escenario principal completo;
- al menos un escenario alternativo o de error relevante;
- reglas de negocio centrales implementadas;
- entrada funcional, caso de uso, dominio y persistencia o integración atravesados de extremo a extremo;
- datos mínimos para realizar la demostración;
- manejo explícito de errores esperables.

No se aceptará como producto terminado una colección de pantallas, endpoints CRUD o clases desconectadas que no produzcan el resultado de negocio documentado.

### 5.2 Arquitectura consolidada

Se debe actualizar el mismo modelo `docs/02-arquitectura/diagramas/workspace.dsl` y exportar las vistas vigentes:

- C4 de Contexto, nivel 1;
- C4 de Contenedores, nivel 2;
- C4 de Componentes, nivel 3, para el contenedor principal.

Las vistas deben coincidir con la solución implementada. No se debe crear un segundo modelo C4 independiente ni dibujar manualmente SVG que contradigan el DSL.

### 5.3 Decisiones y ADR

Cada ADR existente debe quedar en un estado coherente con la evidencia obtenida:

- `Aceptado`;
- `Rechazado`;
- `Reemplazado por ADR-XXX`;
- `Propuesto`, únicamente si la decisión sigue realmente abierta y se justifica.

El historial debe registrar los cambios provocados por el recorrido vertical, los patrones aplicados, la integración y la evaluación arquitectónica. Incluyan nuevos ADR solo para decisiones significativas, no para cada clase o biblioteca.

### 5.4 Patrones de diseño y empresariales

Documenten los patrones efectivamente presentes en el código. Para cada uno indiquen:

- problema concreto observado;
- contexto;
- alternativa simple considerada;
- patrón aplicado o decisión de no aplicarlo;
- participantes y rutas del código;
- beneficio comprobado;
- costo, complejidad o riesgo introducido;
- prueba o evidencia relacionada.

Pueden aparecer, cuando estén justificados, `Strategy`, `Observer`, `Factory Method`, `Abstract Factory`, `Adapter`, `Facade`, `Repository` o `Service Layer`. No existe una cantidad mínima obligatoria. Nombrar un patrón sin evidencia en el código no otorga puntaje.

### 5.5 Integración o distribución

La solución debe demostrar una frontera de integración con un servicio externo o subsistema. Puede resolverse mediante HTTP/REST, una interfaz sustituible, mensajería ya implementada por el equipo u otro mecanismo justificado.

Se debe demostrar:

- responsabilidad de la integración;
- datos intercambiados a nivel funcional;
- punto de sustitución o aislamiento;
- comportamiento ante indisponibilidad, demora o respuesta inválida;
- alternativa local o simulador para la sustentación;
- implicaciones de latencia, fallo parcial y consistencia cuando resulten pertinentes.

No se exige convertir el proyecto en microservicios. Si el equipo separó procesos o servicios, deberá justificar el costo adicional y demostrar su ejecución.

### 5.6 Pruebas y evidencia

Se requieren como mínimo pruebas automatizadas para:

- el escenario principal del flujo final;
- dos reglas o invariantes relevantes;
- un escenario alternativo o de error;
- la frontera de persistencia o integración mediante una prueba de integración o componente.

Todas deben ejecutarse con un comando documentado. No se establece porcentaje mínimo de cobertura. La calidad, relevancia y trazabilidad de las pruebas prevalecen sobre la cifra de cobertura.

### 5.7 Reproducibilidad

`entrega-final.md` debe incluir comandos exactos para:

1. instalar o preparar dependencias;
2. preparar configuración no secreta;
3. iniciar la aplicación;
4. cargar datos de demostración, si aplica;
5. ejecutar todas las pruebas;
6. ejecutar la demostración principal.

No se aceptará como única instrucción “abrir y ejecutar desde el IDE”. No incluyan credenciales, tokens, archivos `.env` reales, dependencias descargadas ni binarios innecesarios.

## 6. Elementos que no se exigen

- Versión formal o política de compatibilidad de una API.
- Arquitectura orientada a eventos.
- Idempotencia formal.
- Microservicios.
- Interfaz gráfica completa.
- Despliegue en nube.
- Pipeline de CI/CD.
- Dockerfile.
- Cobertura del 100 %.
- Aplicación de una cantidad mínima de patrones.
- Implementación de todas las funcionalidades `Should` o `Could`.

## 7. Condiciones de entrega

Antes del cierre, el equipo debe verificar:

- [ ] La aplicación ejecuta el flujo principal y produce un resultado observable.
- [ ] Las funcionalidades terminadas corresponden a requisitos existentes.
- [ ] Las exclusiones y limitaciones están declaradas.
- [ ] C4, secuencias y código representan la misma solución.
- [ ] Los ADR tienen estado, evidencia e historial actualizados.
- [ ] Los patrones documentados existen y responden a problemas reales.
- [ ] La integración se puede demostrar aun si el servicio externo falla.
- [ ] Las pruebas mínimas existen y pasan.
- [ ] Los comandos funcionan desde un clon limpio.
- [ ] No existen secretos en el repositorio.
- [ ] La matriz final no referencia identificadores o rutas inexistentes.
- [ ] No quedan campos de plantilla sin completar.
- [ ] Ambos integrantes pueden ejecutar y explicar la totalidad del proyecto.

## 8. Forma de entrega

Entreguen la URL del repositorio y el commit o etiqueta inmutable que será evaluado. El commit debe contener documentación, fuentes, pruebas y evidencias. Los cambios posteriores al cierre no se considerarán salvo autorización del docente.

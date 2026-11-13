# Guía de sustentación final

## 0. Dinámica general: video + sustentación en vivo

Somos **11-12 grupos** y solo hay **2 sesiones de 90 minutos** para escucharlos a todos, así que vamos a dividir la sustentación en dos partes:

1. **Video del proyecto completo (máx. 5 min)** — grabado y subido por ustedes *antes* de la sesión de su grupo. Es la presentación de **todo el proyecto**, en su estado final, integrando el trabajo de las cuatro entregas. La idea es proyectarlo  en clase mientras el equipo se instala.
2. **Sustentación en vivo (8 min)** — defensa oral, preguntas y, si se pide, evidencia puntual en vivo (correr pruebas, mostrar un archivo). La idea No es repetir en vivo lo que ya mostraron en el video.

Cada equipo ocupa entonces un bloque total aproximado de **13 minutos de clase** (5 de video + 8 en vivo). 

## 1. Video del proyecto completo (entregable previo)

### 1.1 Plazo y entrega

- **Duración máxima: 5 minutos** (se cortará en ese punto si se excede).
- Debe quedar subido **máximo el día de su sustentación a las 6pm**.
- Súbanlo a: [esta carpeta](https://universidadeaneduco-my.sharepoint.com/:f:/g/personal/jydelapava_universidadean_edu_co/IgCeXUEYaeAKSpD0EyB2R4X3ASRnW7aC-41n1ohAgftp4Ic?e=jpfcB1) con su cuenta de la universidad.
- Nombre del archivo: `grupoXX-proyecto-final.mp4`.
- Formato del video MP4.

### 1.2 Contenido obligatorio del video

El video debe mostrar **el proyecto completo en su estado final**, no solo lo que agregaron en esta última entrega. Puede ayudarles pensar en él como "la película completa del semestre" condensada en 5 minutos: de dónde partieron, qué construyeron y cómo quedó.

| Bloque | Tiempo sugerido | Qué deben mostrar y cómo explicarlo |
|---|---:|---|
| Problema y resultado final | 1 min | En qué consiste el problema de negocio que atiende el proyecto completo (no solo esta entrega), quién es el usuario principal, y qué resultado produce la versión final que van a sustentar. Mencionen brevemente qué quedó fuera de alcance. |
| Demostración funcional de punta a punta | 1,5 min | Ejecuten en vivo (grabado, no diapositivas) el flujo principal completo del sistema tal como quedó al final del proyecto, y un escenario alternativo o de fallo. Debe verse el software corriendo de verdad, con datos reales o de ejemplo. |
| Arquitectura final y decisiones clave | 1 min | Muestren la vista C4 vigente (contenedores y/o componentes) y expliquen el ADR o decisión arquitectónica más importante del proyecto: por qué la tomaron y qué alternativa descartaron. Si esa decisión cambió entre entregas, cuéntenlo en una frase. |
| Diseño, patrones e integración | 1 min | Señalen un problema de diseño real que resolvieron con un patrón (cuál y por qué, no solo el nombre) y cómo aislaron la integración con el sistema o servicio externo (qué pasa si ese servicio falla). |
| Pruebas y cierre | 0,5 min | Muestren brevemente la suite de pruebas automatizadas ejecutándose y mencionen la deuda técnica o riesgo más relevante que dejan pendiente. |

### 1.3 Reglas del video

- Identifiquen el grupo y los integrantes al inicio (texto en pantalla es suficiente).
- Pantalla legible (código y diagramas con zoom adecuado).
- Puede narrarlo una sola persona, pero cualquier integrante debe poder defender cualquier parte en la sustentación en vivo.
- Sin música ni relleno; el tiempo es demasiado corto para desperdiciarlo.
- Un video no entregado a tiempo (sin aviso previo justificado) no se repone; el grupo pasa directamente a los 8 minutos en vivo cubriendo también el contenido del video dentro de ese tiempo.


## 2. Sustentación en vivo (8 minutos)

Inmediatamente después de proyectar su video, el equipo pasa a la defensa en vivo:

Preguntas sobre requisitos, arquitectura, diseño, patrones, pruebas y deuda técnica (ver sección 3), de todo el proyecto y no solo de esta entrega.
Se puede pedir: ejecutar una prueba, mostrar un archivo o fragmento de código puntual. 

### 2.1 Reglas de la sustentación en vivo

- Tengan el repositorio clonado y el entorno ya corriendo *antes* de que empiece su bloque (no usen tiempo en vivo para instalar dependencias).
- No repitan el contenido del video; úsenlo como punto de partida para profundizar.
- No editen código durante la sustentación salvo que se les solicite explícitamente.
- Tengan disponible el fake, stub o simulador si el servicio externo falla durante la evidencia en vivo.

## 3. Defensa individual

Al integrante que se indique se le pedirá que responda preguntas como:

- ¿Qué requisito y regla protege este fragmento?
- ¿Por qué esta responsabilidad está en este componente?
- ¿Qué dependencia se invierte y por qué?
- ¿Qué problema motivó el patrón aplicado?
- ¿Qué alternativa más simple se consideró?
- ¿Qué ocurre si el servicio externo no responde?
- ¿Qué evidencia permitió aceptar o modificar el ADR?
- ¿Qué prueba detectaría una regresión del flujo principal?
- ¿Qué deuda técnica se aceptó y cuál es su impacto?
- ¿Por qué el sistema es un monolito, monolito modular o solución distribuida?

La división del trabajo no exime a ningún integrante de comprender la solución completa.

## 4. Respaldo

Antes de presentar (video y sustentación en vivo), preparen:

- una ejecución local comprobada;
- una salida reciente de pruebas;
- solicitudes o datos de ejemplo;
- SVG legibles de C4;
- plan de demostración sin conexión externa;
- copia local del repositorio en el commit evaluable;
- el video ya subido y probado (ábranlo desde la plataforma para confirmar que reproduce bien antes del día de la sesión).

## 5. Dinámica de la sesión y cronograma

### 5.1 Cómo funciona el bloque de cada grupo

1. Mientras el grupo anterior termina y el siguiente conecta su equipo, proyectamos el **video del siguiente grupo** (5 min). Esto evita tiempos muertos de instalación.
2. Al terminar el video, el equipo pasa directamente a los **8 minutos de sustentación en vivo** (sección 2).
3. Al cerrar ese bloque, se proyecta el video del grupo siguiente y se repite el ciclo.

### 5.2 Orden y horario

- Se publicará con anticipación el orden de presentación en la sección **Anuncios** de Canvas.
- Lleguen 10 minutos antes del inicio de la sesión con el entorno ya corriendo.
- Si su grupo es de los primeros en el orden, suban el video con mayor anticipación para evitar contratiempos de última hora.


## 6. Plazos clave

- Trabajan en la Entrega 4 durante el fin de semana.
- **Antes de su sesión de sustentación la próxima semana:** suben el video (máx. 5 min) a la plataforma del curso.
- **Día de su sesión:** sustentación en vivo de 8 minutos según el orden publicado.

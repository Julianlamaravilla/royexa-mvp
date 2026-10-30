# ADR-004: Operación en línea con confirmación idempotente del código

- **Estado:** Propuesto
- **Fecha:** 2026-10-30
- **Responsables:** Julian Andres Restrepo
- **Asunto relacionado:** AD-03
- **Alternativa seleccionada:** ALT-03A

## 1. Contexto

ADR-003 seleccionó ALT-03B porque la Entrega 2 seguía a TRACKEA, y declaró que esa decisión dependía de DIV-02. La Entrega 1 excluye la aplicación móvil nativa y la operación sin conexión, y la línea base de [`realineacion-entrega-1.md`](../realineacion-entrega-1.md) vuelve a ese alcance: una demostración local de costo cero, operada por API en la Entrega 3 y por una web mínima en la Entrega 4.

Volver al alcance no elimina el problema de fondo. El recorrido vertical confirma un desembolso por HTTP: si la respuesta se pierde, el cobrador repite la confirmación. Sin protección, el libro recibiría dos asientos y la caja dos descuentos.

### Trazabilidad

- **Interesados:** INT-01, INT-02, INT-03
- **Requisitos funcionales:** RF-03, RF-04
- **Reglas o invariantes:** RN-03, RN-04, INV-02
- **Escenarios de calidad:** EC-01
- **ASR:** ASR-01, ASR-02
- **Restricciones:** RES-02, RES-06
- **Riesgos:** RA-07
- **Supuestos:** No aplica. SUP-04 y SUP-05 se difieren con ALT-03B.

## 2. Asunto de decisión

> ¿Cómo asegurar que una operación de dinero confirmada por el cobrador llegue al libro una sola vez, sin duplicarse ni perderse?

La formulación de la Entrega 2 hablaba de «un cobro registrado sin señal». Esa frase ya presuponía la operación sin conexión, así que AD-03 se reformula sin cambiar su identificador.

## 3. Criterios de decisión

### Obligatorios

- No duplicar ni perder una operación de dinero confirmada (O1 de AD-03).

### Criterios obligatorios de AD-03 que caen

Este cambio de criterios decide el resultado, por lo que se declara de forma explícita. La Entrega 2 descartó ALT-03A por incumplir O2 (`arquitectura.md`, sección 3.3). Ese razonamiento no se reescribe: se conserva como historia y sus premisas se retiran aquí.

| Criterio | Por qué cae |
|---|---|
| O2. Registrar un cobro sin señal y dejarlo firme | Provenía de DIV-02, no de la Entrega 1. La propuesta describe que el cobrador pasa buena parte de la jornada sin señal, pero la misma propuesta y la Entrega 1 excluyen la operación sin conexión y la sustituyen por la interfaz web. La necesidad del contexto es real; el criterio obligatorio no estaba comprometido. |
| O3. Cifrar los datos guardados en el teléfono | Citaba RES-04, que no menciona el teléfono. Solo existía porque DIV-02 introducía datos locales. Sin aplicación móvil no hay datos locales que proteger. |

### Prioritarios

- Reintentos seguros ante cortes.
- Que el servidor decida el resultado y lo explique al cobrador.
- Complejidad asumible por un equipo mínimo (RES-02).
- Costo cero (RES-06).

### Deseables

- Bajo consumo de datos. No discrimina en una demostración local y se mantiene solo como criterio de la comparación original.

## 4. Alternativas consideradas

### ALT-03A — Operación en línea con confirmación idempotente

- **Descripción:** Toda operación de dinero se registra directamente en el servidor. La confirmación del código es idempotente: repetirla devuelve el resultado original sin escribir de nuevo.
- **Beneficios:** Sin cola local ni sincronización. Es el alcance de la Entrega 1.
- **Costos y sacrificios:** El registro depende de la conexión. Sin señal, el cobrador anotaría en papel, lo que reintroduce el hueco de cobrar y no registrar.
- **Riesgos:** El cobrador no puede demostrar de inmediato lo cobrado si no tiene conexión. El curso no ejercita este riesgo porque la demostración es local.
- **Supuestos:** La ruta tiene señal suficiente durante la jornada. El curso no lo mide.
- **Evidencia necesaria:** EV-12

**Corrección a la Entrega 2.** `arquitectura.md` atribuía a esta alternativa «sin duplicados posibles». Es falso ante un reintento HTTP: la ausencia de cola local no impide que el cliente repita una petición cuya respuesta no recibió. Por eso esta decisión añade la idempotencia y EV-12.

### ALT-03B — Cola local cifrada, lotes con identificador único y descarga por cursor

- **Descripción:** La alternativa seleccionada por ADR-003. El teléfono guarda cada operación con un identificador único y el servidor lo usa como barrera de idempotencia.
- **Beneficios:** El cobro queda firme sin señal y los reintentos son seguros.
- **Costos y sacrificios:** Exige aplicación móvil, base cifrada, cola y un contrato de sincronización.
- **Riesgos:** RA-05, RA-06, RA-07.
- **Supuestos:** SUP-04, SUP-05
- **Evidencia necesaria:** EV-05, EV-06

### ALT-03C — Réplica local con fusión automática

- **Descripción:** El teléfono guarda una copia de las entidades y ambas partes reconcilian los cambios con una regla automática.
- **Beneficios:** Más libertad para el cobrador sin señal.
- **Costos y sacrificios:** La regla puede sobrescribir dinero y contradice el libro de solo inserción.
- **Riesgos:** Un pago perdido o alterado por la fusión.
- **Supuestos:** Los conflictos se resuelven sin intervención humana.
- **Evidencia necesaria:** Ninguna prevista: sigue descartada por incumplir el criterio obligatorio.

## 5. Decisión

Se selecciona **ALT-03A** porque cumple el criterio obligatorio con una complejidad asumible y costo cero, dentro del alcance comprometido en la Entrega 1. ALT-03B queda diferida porque depende de una aplicación móvil fuera de la línea base.

La idempotencia se construye con dos mecanismos y un contrato de respuesta:

| Mecanismo | Qué aporta |
|---|---|
| Máquina de estados del desembolso | Solo un desembolso `Aprobado` puede pasar a `Confirmado` o `Caducado`. Un desembolso en estado final no vuelve a transitar. |
| Restricción de unicidad sobre el asiento, por desembolso y tipo | Si dos confirmaciones compiten, la base de datos rechaza el segundo asiento y su transacción se revierte. |
| Resultado original en el reintento | La repetición responde con el resultado de la primera confirmación, sin asiento nuevo, sin descuento de caja y sin nueva notificación. |

ADR-003 pasa a `Reemplazado por ADR-004` solo cuando el docente confirme la resolución de DIV-02. Hasta entonces ambos registros siguen en `Propuesto` y la línea base de trabajo se apoya en este.

La decisión se considera provisional hasta obtener la evidencia indicada en este registro.

## 6. Consecuencias

### Positivas

- Desaparecen la cola local, el contrato de sincronización y el riesgo técnico del teléfono.
- Un reintento HTTP no duplica el asiento ni el descuento de caja.
- La garantía se apoya en la base de datos, no solo en el código, en línea con ADR-001.

### Negativas o costos aceptados

- El registro depende de la conexión. Si el producto llegara a operar en una ruta real, el hueco del papel volvería a estar abierto.
- La preocupación de INT-01 por demostrar lo cobrado sin señal queda sin respuesta en el curso.
- La idempotencia cubre la confirmación del desembolso. Los pagos de la Entrega 4 no tienen un código que sirva de barrera y necesitarán su propia clave.

### Riesgos residuales

- RA-07: cierra cuando el docente confirme la resolución de DIV-02. Pendiente.
- Una migración podría retirar la restricción de unicidad. Se registra como punto sensible en `arquitectura.md`, sección 6.3.

## 7. Elementos arquitectónicos afectados

- **Sistemas:** ROYEXA
- **Contenedores:** CON-02 (Entrega 4), CON-03, CON-04
- **Sistemas externos:** EXT-05, que no recibe un segundo envío en el reintento
- **Relaciones C4:** «API del servidor → Base de datos» (inserta el asiento una sola vez por desembolso y tipo)
- **Artefactos adicionales:** módulos `sales` y `ledger`, y la migración que define la restricción de unicidad, que se producen en la Entrega 3

## 8. Evidencia y validación

| Evidencia | Actividad | Resultado esperado | Momento previsto |
|---|---|---|---|
| EV-12 | Repetir por HTTP la confirmación de un desembolso ya confirmado y lanzar dos confirmaciones concurrentes del mismo código. | Un solo asiento y un solo descuento de caja; todas las respuestas devuelven el resultado original. | Entrega 3 |

## 9. Condiciones de revisión

Esta decisión deberá revisarse si ocurre alguna de las siguientes condiciones:

- El docente no confirma la resolución de DIV-02.
- EV-12 demuestra que un reintento o una confirmación concurrente duplica el asiento.
- Un requisito exige operar sin conexión; en ese caso se retoma ALT-03B.
- Los pagos de la Entrega 4 no pueden reintentarse con seguridad con un mecanismo equivalente.

## 10. Decisiones relacionadas

- ADR-001 (el libro de solo inserción es el destino del asiento único).
- ADR-002 (la confirmación ocurre en una transacción dentro del monolito modular).
- ADR-003 (decisión anterior sobre AD-03; pasa a `Reemplazado por ADR-004` con la confirmación docente).

## 11. Historial

| Fecha | Estado | Cambio | Motivo |
|---|---|---|---|
| 2026-10-30 | Propuesto | Creación inicial | Realineación con la Entrega 1 sobre una demostración local de costo cero |

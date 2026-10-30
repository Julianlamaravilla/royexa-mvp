# ADR-001: Libro de movimientos de solo inserción garantizado por la base de datos

- **Estado:** Propuesto
- **Fecha:** 2026-09-20
- **Responsables:** Julian Andres Restrepo
- **Asunto relacionado:** AD-01
- **Alternativa seleccionada:** ALT-01B

## 1. Contexto

El producto existe para impedir el fraude interno. Ese propósito se pierde si un movimiento de dinero puede modificarse o borrarse después de confirmado, porque un fraude se ocultaría editando el pasado. Reciben asientos los pagos, los desembolsos, los movimientos de caja y las correcciones. Además, el saldo debe poder derivarse de los asientos y no de una columna que alguien edite.

La pregunta es dónde vive la garantía: en la disciplina del código de la aplicación o en la propia base de datos.

### Trazabilidad

- **Interesados:** INT-01, INT-02
- **Requisitos funcionales:** RF-04, RF-02, RF-03
- **Reglas o invariantes:** RN-04, INV-02
- **Escenarios de calidad:** EC-01
- **ASR:** ASR-01
- **Restricciones:** RES-04, RES-02, RES-06
- **Riesgos:** RA-01, RA-02
- **Supuestos:** SUP-01

## 2. Asunto de decisión

> ¿Cómo garantizar que un movimiento de dinero, una vez confirmado, no pueda alterarse ni borrarse, incluso si el código de la aplicación falla?

## 3. Criterios de decisión

### Obligatorios

- Rechazar la modificación o el borrado aunque el código de la aplicación tenga un defecto o reciba una consulta manipulada.
- Dejar visibles el asiento original y el compensatorio en toda corrección.
- Confirmar el asiento y su efecto sobre el pago, el saldo y la caja de forma conjunta.

### Prioritarios

- Ser verificable con una prueba automatizada repetible.
- Ser operable por un equipo mínimo.
- Costo cero: no añadir servicios de pago (RES-06).

### Deseables

- Dejar evidencia de una manipulación hecha por quien tenga acceso privilegiado a la base de datos.

## 4. Alternativas consideradas

### ALT-01A — Inalterabilidad por convención en la aplicación

- **Descripción:** El código no ofrece operaciones de actualizar ni borrar; la tabla las admite al rol de la aplicación.
- **Beneficios:** La más simple; sin configuración adicional.
- **Costos y sacrificios:** La garantía vive solo en el código y no puede demostrarse a quien desconfíe de él.
- **Riesgos:** Un defecto, una consulta cruda o una inyección de SQL alteran el pasado sin obstáculo.
- **Supuestos:** Todo acceso pasa por el código y este no tiene defectos.
- **Evidencia necesaria:** EV-01

### ALT-01B — Solo inserción por privilegios de la base de datos y un único módulo escritor

- **Descripción:** El rol de la aplicación solo tiene inserción y lectura sobre el libro y se le retiran de forma explícita la modificación, el borrado y el vaciado. Otro rol ejecuta las migraciones. Un solo módulo escribe el libro y los demás le piden los asientos. Las correcciones son contra-asientos y el saldo es la suma de los asientos.
- **Beneficios:** El rechazo lo hace la base de datos aunque el código falle; se demuestra con una prueba automatizada.
- **Costos y sacrificios:** Los privilegios deben mantenerse en cada migración. Cada operación de dinero pasa por una llamada más. Los estados de las solicitudes viven en sus módulos dueños, no en el libro.
- **Riesgos:** Una migración con una concesión demasiado amplia anula la garantía; el rol propietario puede alterar el libro.
- **Supuestos:** SUP-01
- **Evidencia necesaria:** EV-01, EV-02

### ALT-01C — Cadena de hashes sobre los asientos

- **Descripción:** Cada asiento guarda un valor calculado a partir del anterior y un proceso periódico verifica la cadena.
- **Beneficios:** Detecta la manipulación incluso de quien tenga acceso privilegiado.
- **Costos y sacrificios:** Detecta y no impide. Añade un cálculo serializado a cada inserción y un proceso de verificación.
- **Riesgos:** La alteración puede tardar en detectarse. Puede degradar el cobro concurrente.
- **Supuestos:** Es posible serializar la cadena por caja sin degradar el registro de cobros.
- **Evidencia necesaria:** Medición del costo bajo cobros concurrentes (no planificada).

## 5. Decisión

Se selecciona **ALT-01B** porque es la única alternativa que cumple el criterio obligatorio de rechazo aunque el código falle y permite demostrarlo con una prueba automatizada, que es la forma de verificación prevista para EC-01. TRACKEA, que queda como referencia, tomó la misma decisión.

PostgreSQL local es obligatorio para EV-01 y EV-02. Un libro en memoria equivale a ALT-01A, ya descartada, y `propuesta.md` (sección L) exige que la inmutabilidad no dependa solo de que la aplicación se comporte bien. Los adaptadores en memoria sirven para otras pruebas, no para demostrar esta garantía.

La decisión se considera provisional hasta obtener la evidencia indicada en este registro.

Este registro pasa a `Aceptado` solo si EV-01 y EV-02 quedan `Validada`.

## 6. Consecuencias

### Positivas

- La garantía antifraude tiene un solo lugar donde probarse.
- Un defecto de código no puede alterar el pasado.

### Negativas o costos aceptados

- Cada operación de dinero pasa por una llamada más al módulo del libro.
- Los privilegios exigen una prueba de ausencia en cada migración.
- El propietario de la base de datos sigue pudiendo alterar el libro.

### Riesgos residuales

- RA-01: una migración concede privilegios de más.
- RA-02: acceso privilegiado a la base de datos.

## 7. Elementos arquitectónicos afectados

- **Sistemas:** ROYEXA
- **Contenedores:** CON-03, CON-04
- **Sistemas externos:** No aplica
- **Relaciones C4:** «API del servidor → Base de datos» (lee y escribe el dominio; inserta asientos con un rol que no puede modificarlos)
- **Artefactos adicionales:** migración del esquema inicial, módulo `ledger` y prueba de privilegios, que se producen en la Entrega 3. Las rutas de TRACKEA citadas en la versión anterior de este registro quedan retiradas.

## 8. Evidencia y validación

| Evidencia | Actividad | Resultado esperado | Momento previsto |
|---|---|---|---|
| EV-01 | Ejecutar la prueba que intenta modificar, borrar y vaciar un asiento con el rol de la aplicación y consulta después la fila. | El 100 % de los intentos falla con error de permiso y la fila queda intacta. | Entrega 3 |
| EV-02 | Consultar el catálogo de privilegios tras aplicar todas las migraciones. | Ausencia de modificar, borrar y vaciar sobre el libro y el registro de cambios, en cada ejecución del comando local de pruebas. | Entrega 3 |

## 9. Condiciones de revisión

Esta decisión deberá revisarse si ocurre alguna de las siguientes condiciones:

- EV-02 encuentra privilegios de más que no pueden mantenerse de forma estable.
- Un requisito exige detectar la manipulación hecha por quien tenga acceso privilegiado; en ese caso se añade ALT-01C como refuerzo.
- El recorrido vertical revela que pasar cada operación por un módulo único introduce un costo o acoplamiento no previsto.
- Aparece una alternativa viable con consecuencias significativamente mejores.

## 10. Decisiones relacionadas

- ADR-002 (el libro es escrito por un módulo y comunicado con el resto por llamadas directas).
- ADR-004 (la restricción de unicidad por desembolso y tipo evita que el libro reciba dos veces el mismo desembolso). Sustituye a ADR-003 en esta relación cuando el docente confirme la resolución de DIV-02.

## 11. Historial

| Fecha | Estado | Cambio | Motivo |
|---|---|---|---|
| 2026-09-20 | Propuesto | Creación inicial | Sincronización con el estado de TRACKEA |
| 2026-10-30 | Propuesto | Costo cero en lugar de presupuesto de infraestructura; PostgreSQL local obligatorio para EV-01 y EV-02; comando local en lugar de integración continua; rutas de TRACKEA retiradas; relación con ADR-004 | Realineación con la Entrega 1 (`realineacion-entrega-1.md`) |

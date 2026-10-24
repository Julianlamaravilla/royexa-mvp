# ADR-003: Sincronización de cobros sin señal por identificador único de operación

- **Estado:** Propuesto
- **Fecha:** 2026-09-20
- **Responsables:** Julian Andres Restrepo
- **Asunto relacionado:** AD-03
- **Alternativa seleccionada:** ALT-03B

## 1. Contexto

El cobrador trabaja buena parte de la jornada sin señal y necesita que su registro quede firme en ese momento, porque de otro modo no puede demostrar lo que cobró. Al volver la señal, el registro debe llegar al libro una sola vez: sin duplicarse por un reintento y sin perderse por un corte.

**Esta decisión depende de DIV-02.** La Entrega 1 excluye la operación sin conexión de su alcance; TRACKEA la incluye en el hito 1 y el Bolt B1 la ejercita.

### Trazabilidad

- **Interesados:** INT-01, INT-02
- **Requisitos funcionales:** RF-01, RF-04
- **Reglas o invariantes:** RN-04, RN-01, INV-02
- **Escenarios de calidad:** EC-01, EC-03
- **ASR:** ASR-01
- **Restricciones:** RES-04
- **Riesgos:** RA-05, RA-06, RA-07
- **Supuestos:** SUP-04, SUP-05

## 2. Asunto de decisión

> ¿Cómo asegurar que un cobro registrado sin señal llegue una sola vez, sin duplicarse ni perderse?

## 3. Criterios de decisión

### Obligatorios

- No duplicar ni perder un cobro registrado.
- Permitir registrar un cobro sin señal y dejarlo firme.
- Cifrar los datos guardados en el teléfono.

### Prioritarios

- Reintentos seguros ante cortes.
- Que el servidor decida el resultado y lo explique al cobrador.
- Complejidad asumible por un desarrollador sin experiencia móvil previa.

### Deseables

- Bajo consumo de datos: la jornada cabe en menos de 1 minuto de conexión 4G.

## 4. Alternativas consideradas

### ALT-03A — Aplicación solo en línea

- **Descripción:** El cobro se registra directamente en el servidor; sin señal, el cobrador anota en papel y registra después.
- **Beneficios:** Sin cola local ni sincronización; sin duplicados posibles. Coherente con el alcance de la Entrega 1.
- **Costos y sacrificios:** El registro depende de la señal y el papel reintroduce el hueco de cobrar y no registrar.
- **Riesgos:** El cobrador no puede demostrar de inmediato lo cobrado.
- **Supuestos:** La ruta tiene señal suficiente durante la jornada.
- **Evidencia necesaria:** Proporción de visitas sin señal en la ruta piloto (no planificada).

### ALT-03B — Cola local cifrada, lotes con identificador único y descarga por cursor

- **Descripción:** El teléfono guarda cada operación en una base local cifrada con un identificador único y la envía en lotes de hasta 100 al volver la señal. El servidor usa el identificador como barrera de idempotencia: repetirlo devuelve el resultado original. Ordena las operaciones por préstamo, guarda el resultado y publica los cambios que el teléfono descarga por cursor.
- **Beneficios:** El cobro queda firme sin señal; los reintentos son seguros; el servidor conserva la decisión.
- **Costos y sacrificios:** El teléfono concentra el riesgo técnico. Hay acciones que no se permiten sin señal (una venta nueva, pedir una llave, cerrar la caja).
- **Riesgos:** RA-05, RA-06, RA-07.
- **Supuestos:** SUP-04, SUP-05
- **Evidencia necesaria:** EV-05, EV-06

### ALT-03C — Réplica local con fusión automática

- **Descripción:** El teléfono guarda una copia de las entidades y ambas partes reconcilian los cambios con una regla automática, por ejemplo la última escritura gana.
- **Beneficios:** Más libertad para el cobrador sin señal.
- **Costos y sacrificios:** La regla puede sobrescribir dinero y contradice el libro de solo inserción.
- **Riesgos:** Un pago perdido o alterado por la fusión.
- **Supuestos:** Los conflictos se resuelven sin intervención humana.
- **Evidencia necesaria:** Ninguna prevista: se descarta por incumplir el primer criterio obligatorio.

## 5. Decisión

Se selecciona **ALT-03B** porque es la única que cumple el registro firme sin señal y mantiene la integridad con el servidor como autoridad. Coincide con la decisión ya tomada en TRACKEA. Si el docente confirma que la operación sin conexión queda excluida (DIV-02), la decisión debe revisarse hacia ALT-03A.

La decisión se considera provisional hasta obtener la evidencia indicada en este registro.

## 6. Consecuencias

### Positivas

- El cobro queda firme en el teléfono.
- Los reintentos no duplican el cobro.
- El servidor conserva la decisión y la explica.

### Negativas o costos aceptados

- Riesgo técnico concentrado en el teléfono: base cifrada, cola y reintentos.
- Acciones deshabilitadas sin señal.
- Un contrato de sincronización que debe versionarse.

### Riesgos residuales

- RA-05: la resolución del ciclo entre pagos y sincronización.
- RA-06: riesgo técnico de la aplicación móvil.
- RA-07: la operación sin conexión no está en la Entrega 1.

## 7. Elementos arquitectónicos afectados

- **Sistemas:** ROYEXA
- **Contenedores:** CON-01, CON-03, CON-04
- **Sistemas externos:** No aplica
- **Relaciones C4:** «Aplicación móvil → API del servidor» (envía operaciones por lote con identificador único y descarga cambios por cursor)
- **Artefactos adicionales:** módulo de sincronización (`backend/src/royexa/sync/`), rutas `/sync/operations` y `/sync/changes` en `contracts/openapi.json` y pruebas de integración (`backend/tests/integration/sync/`)

## 8. Evidencia y validación

| Evidencia | Actividad | Resultado esperado | Momento previsto |
|---|---|---|---|
| EV-05 | Enviar el mismo identificador desde el mismo dispositivo y desde otro, un lote de 101 y una falla a mitad de la transacción. | Un solo pago y un solo asiento; el reintento devuelve el resultado original. | Entrega 3 |
| EV-06 | Registrar un cobro sin señal en un Android 10 real y devolver la señal. | El cobro aparece una sola vez en el libro del entorno de pruebas y el teléfono ve el saldo actualizado. | Entrega 3 |

## 9. Condiciones de revisión

Esta decisión deberá revisarse si ocurre alguna de las siguientes condiciones:

- DIV-02 se resuelve excluyendo la operación sin conexión.
- El cifrado local no supera la verificación previa en el Android de referencia.
- La evidencia contradice SUP-04 o SUP-05.
- La proporción de visitas sin señal resulta baja.

## 10. Decisiones relacionadas

- ADR-001 (el identificador evita que el libro reciba dos veces el mismo cobro).
- ADR-002 (la sincronización se comunica con los módulos por llamada directa).

## 11. Historial

| Fecha | Estado | Cambio | Motivo |
|---|---|---|---|
| 2026-09-20 | Propuesto | Creación inicial | Sincronización con el estado de TRACKEA |

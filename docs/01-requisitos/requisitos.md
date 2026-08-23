# Entrega 1 — Requisitos e impulsores arquitectónicos

## 0. Identificación

- **Proyecto:** ROYEXA
- **Integrantes:**
  - Julian Andres Restrepo Castaño
  - Jeison David Tibaduiza Sanchez
- **Grupo:** 10
- **Fecha:** 2026-08-22
- **Commit o etiqueta de entrega:** entrega-1-requisitos

---

## 1. Alcance validado

### 1.1 Propósito

El propósito es impedir el fraude interno en la cobranza en calle: que el cobrador reciba un pago y no lo registre, o que reporte un desembolso que nunca entregó. La solución debe convertir cada movimiento de dinero en un hecho verificable por alguien distinto de quien lo registró, detectar el descuadre de caja el mismo día y dejar un rastro que no pueda alterarse después de creado.

### 1.2 Interesados principales

| ID | Interesado o rol | Necesidad o preocupación principal |
|---|---|---|
| INT-01 | Cobrador | Registrar cobros de forma rápida durante la ruta y poder demostrar que entregó todo lo que recibió, porque hoy cualquier diferencia de caja se interpreta en su contra. |
| INT-02 | Administrador | Aprobar los desembolsos antes de que salga el dinero y verificar al cierre que lo registrado coincide con lo entregado, sin que un registro pueda editarse después de creado. |
| INT-03 | Cliente final | Recibir un comprobante independiente de la palabra del cobrador, para saber cuánto pagó y cuánto le queda por pagar. No opera el sistema: solo recibe la notificación. |

### 1.3 Flujo principal

- **Nombre:** Desembolso de un préstamo
- **Iniciado por:** INT-01 Cobrador
- **Evento de inicio:** El cobrador registra una solicitud de desembolso para un cliente de su ruta, indicando monto, plazo y número de cuotas.
- **Resultado observable:** El desembolso queda asentado en el libro de movimientos, se genera el calendario de cuotas, se descuenta el importe de la caja del cobrador y la operación es consultable con la identidad de quien la solicitó y de quien la aprobó. Si el cliente no confirma a tiempo, la operación caduca, el dinero no se descuenta y queda un asiento del intento con su motivo.

1. El cobrador registra una solicitud de desembolso para un cliente de su ruta, con monto, plazo y número de cuotas.
2. El sistema valida que el cliente exista, que no tenga un préstamo anterior sin liquidar y que el monto esté dentro de los límites de la ruta.
3. Si el monto supera el límite del cobrador, la solicitud queda en espera de autorización; si no lo supera, avanza.
4. El administrador revisa el historial del cliente y aprueba o rechaza indicando el motivo. No puede aprobar una solicitud que él mismo haya originado.
5. Si aprueba, el sistema genera un código de confirmación único, con caducidad, asociado a esa operación y a ese cliente, y lo envía por el canal de notificación.
6. El cliente confirma la recepción del dinero presentando el código. El sistema asienta el desembolso, genera el calendario de cuotas y descuenta el importe de la caja. Si el código caduca, no se descuenta dinero y queda registrado el intento.

### 1.4 Alcance incluido

- Registro de pago y de no pago durante la ruta, con motivo y compromiso de pago cuando no hay cobro, y con contador fraccionario cuando el pago es parcial.
- Cierre diario de caja en tres paneles (pendientes, pagaron, no pagaron) y cálculo de la diferencia entre lo registrado y lo entregado.
- Aprobación de desembolsos con código de confirmación del cliente final, incluyendo el camino de caducidad.
- Libro de movimientos inmutable, con correcciones mediante asientos compensatorios visibles.
- Alta y consulta de clientes y préstamos, con calendario de cuotas derivado del monto, el plazo y el interés.
- Notificación de comprobante al cliente final mediante un servicio reemplazable, simulado durante el curso.

### 1.5 Fuera de alcance

- Aplicación móvil nativa y operación completa sin conexión, con sincronización posterior.
- Aislamiento entre varias empresas sobre una misma instalación.
- Portal de consulta para el cliente final, evaluación crediticia automática, asistente de inteligencia artificial, reportes a socios y ordenación geográfica de rutas.
- Conexión del proveedor real de notificaciones y certificaciones formales de protección de datos o de seguridad.
- Custodia, retención o transferencia de fondos. El sistema solo registra información sobre una gestión que ocurre fuera de él.

### 1.6 Recorrido vertical previsto

- **Entrada:** solicitud de desembolso de un préstamo, con monto, plazo y número de cuotas
- **Actor que lo inicia:** INT-01
- **Comportamiento principal:** el cobrador origina la solicitud, el administrador la aprueba o la rechaza, el cliente final confirma con el código o el código caduca, y el resultado queda asentado de forma consultable
- **Reglas involucradas:** RN-03, RN-04, RN-05, RN-06
- **Resultado observable:** desembolso confirmado con calendario de cuotas y descuento en caja, o intento caducado sin descuento de dinero y con asiento del motivo
- **Requisitos que cubrirá:** RF-03, RF-04, RF-06

---

## 2. Requisitos funcionales y criterios de aceptación

### RF-01 — Registrar pago o no pago en ruta

> Como cobrador,  
> quiero registrar el pago o el no pago de un cliente durante la ruta,  
> para que quede constancia de lo ocurrido en la visita y pueda demostrar el trabajo realizado.

- **Prioridad:** Must
- **Reglas relacionadas:** RN-01

#### CA-01 — Registro de un pago parcial

```gherkin
Scenario: El cobrador registra un pago parcial y el contador avanza de forma fraccionaria
  Given que el cliente tiene un préstamo activo de 20 cuotas de 50
  And que aún no se ha registrado ningún pago sobre ese préstamo
  When el cobrador registra un pago de 25
  Then el sistema acepta el pago
  And el contador de cuotas queda en 19,5 restantes de 20
  And el medio de pago queda registrado
  And la operación es consultable con la identidad del cobrador
```

#### CA-02 — Registro de un no pago

```gherkin
Scenario: El cobrador registra un no pago con motivo y compromiso
  Given que el cliente tiene un préstamo activo y está pendiente de visita
  When el cobrador registra un no pago con motivo "no tiene dinero" y una fecha de compromiso
  Then el sistema acepta el registro
  And el cliente deja de estar pendiente de visita
  And el motivo y el compromiso quedan consultables
  And no se reduce el saldo del préstamo
```

---

### RF-02 — Cerrar la caja diaria y detectar descuadre

> Como cobrador,  
> quiero cerrar la caja al terminar la ruta e indicar el dinero entregado,  
> para que el administrador vea el mismo día si lo registrado coincide con lo recibido.

- **Prioridad:** Must
- **Reglas relacionadas:** RN-02, RN-04

#### CA-03 — Cierre con descuadre visible

```gherkin
Scenario: El cierre calcula la diferencia entre lo registrado y lo entregado
  Given que la caja del cobrador no tiene clientes pendientes de visita
  And que lo registrado en pagos en efectivo del día es 750
  When el cobrador cierra la caja indicando que entrega 725
  Then el sistema acepta el cierre
  And muestra un descuadre de 25
  And el descuadre queda asentado y consultable por el administrador
  And la caja queda cerrada
```

#### CA-04 — Cierre rechazado si hay visitas pendientes

```gherkin
Scenario: El cierre se rechaza cuando aún hay clientes pendientes
  Given que la caja del cobrador tiene al menos un cliente pendiente de visita
  When el cobrador solicita el cierre de la caja
  Then el sistema rechaza el cierre
  And la caja permanece abierta
  And se informa que existen visitas pendientes
```

---

### RF-03 — Aprobar un desembolso con confirmación del cliente

> Como administrador,  
> quiero aprobar o rechazar una solicitud de desembolso y exigir la confirmación del cliente final,  
> para que el dinero no se libere si la entrega no ocurrió.

- **Prioridad:** Must
- **Reglas relacionadas:** RN-03, RN-05, RN-06

#### CA-05 — Aprobación, confirmación y asiento del desembolso

```gherkin
Scenario: El cliente confirma el desembolso dentro del plazo del código
  Given que el cobrador registró una solicitud de desembolso para un cliente sin préstamo pendiente
  And que el administrador, distinto de quien originó la solicitud, la aprueba
  And que el sistema genera un código de confirmación vigente
  When el cliente presenta el código y el cobrador lo valida
  Then el sistema registra el desembolso en el libro de movimientos
  And genera el calendario de cuotas
  And descuenta el importe de la caja del cobrador
  And la operación queda consultable con quien la solicitó y quien la aprobó
```

#### CA-06 — Caducidad del código o autoaprobación prohibida

```gherkin
Scenario: El código caduca sin confirmación y el dinero no se libera
  Given que existe un desembolso aprobado con un código de confirmación
  And que el plazo del código ya venció
  When se intenta validar ese código
  Then el sistema rechaza la confirmación
  And no descuenta dinero de la caja
  And deja un asiento del intento con el motivo de caducidad

Scenario: Quien originó la solicitud no puede aprobarla
  Given que un administrador originó una solicitud de desembolso
  When ese mismo administrador intenta aprobarla
  Then el sistema rechaza la aprobación
  And la solicitud permanece sin aprobar
  And queda registrada la identidad de quien intentó aprobarla
```

---

### RF-04 — Conservar un libro de movimientos inmutable

> Como administrador,  
> quiero que toda operación de dinero quede asentada y que no pueda editarse ni borrarse,  
> para reconstruir lo ocurrido y evitar que un fraude se oculte alterando el pasado.

- **Prioridad:** Must
- **Reglas relacionadas:** RN-04

#### CA-07 — Asiento de una operación de dinero

```gherkin
Scenario: Un pago queda asentado con identidad y marcas de tiempo
  Given que el cobrador registra un pago válido
  When el sistema confirma la operación
  Then se crea un asiento en el libro de movimientos
  And el asiento conserva el importe, el tipo de operación y la identidad de quien la ejecutó
  And el asiento conserva la hora informada por el dispositivo y la hora del servidor
  And el asiento es consultable por el administrador
```

#### CA-08 — Un error se corrige sin borrar el original

```gherkin
Scenario: La corrección deja visibles el asiento original y el compensatorio
  Given que existe un asiento confirmado por un importe incorrecto
  When el administrador registra la corrección
  Then el asiento original permanece consultable
  And se crea un asiento compensatorio visible
  And el sistema no permite modificar ni eliminar el asiento original
```

---

### RF-05 — Registrar clientes y préstamos con calendario de cuotas

> Como administrador,  
> quiero dar de alta clientes y préstamos y consultar su calendario de cuotas,  
> para operar la ruta sobre información actual del saldo y de los vencimientos.

- **Prioridad:** Must
- **Reglas relacionadas:** RN-01, RN-05

#### CA-09 — Alta de préstamo con calendario derivado

```gherkin
Scenario: El sistema genera el calendario a partir del monto, el plazo y el interés
  Given que existe un cliente activo sin préstamo pendiente de liquidar
  When el administrador registra un préstamo de 1000 a 20 cuotas con interés fijo de 200
  Then el sistema crea el préstamo en estado activo
  And genera 20 cuotas de 60
  And las fechas de vencimiento corresponden a días de cobranza, de lunes a sábado
  And el calendario queda consultable
```

#### CA-10 — Renovación bloqueada si el préstamo anterior no está liquidado

```gherkin
Scenario: No se crea un nuevo préstamo si el anterior tiene saldo
  Given que el cliente tiene un préstamo activo con saldo pendiente
  When se intenta registrar un nuevo desembolso o renovación para ese cliente
  Then el sistema rechaza la operación
  And informa que el préstamo anterior no está liquidado
  And solo permite continuar si el administrador registra una excepción explícita
```

---

### RF-06 — Notificar el comprobante al cliente final

> Como cliente final,  
> quiero recibir un comprobante de cada pago y el código de confirmación de un desembolso,  
> para disponer de una prueba que no dependa de la palabra del cobrador.

- **Prioridad:** Must
- **Reglas relacionadas:** RN-03

#### CA-11 — Envío del comprobante de pago

```gherkin
Scenario: Tras un pago confirmado se emite el comprobante
  Given que el cobrador registró un pago válido
  When el sistema confirma la operación
  Then se emite una notificación al cliente final
  And la notificación indica el importe recibido, el saldo restante y la fecha del próximo vencimiento
  And el envío queda registrado con un estado consultable
```

#### CA-12 — El fallo de notificación no pasa inadvertido

```gherkin
Scenario: Un envío fallido deja rastro y no se da por notificado
  Given que el sistema debe notificar un pago o un código de confirmación
  When el servicio de notificación no confirma el envío
  Then la operación de negocio no se da por notificada
  And el estado del envío queda como fallido o pendiente de reintento
  And el administrador puede consultar que el cliente no recibió el comprobante
```

---

### RF-07 — Consultar los descuadres del periodo

> Como administrador,  
> quiero ver el número de descuadres de caja del periodo y su detalle,  
> para saber si la métrica prioritaria del negocio está mejorando.

- **Prioridad:** Should
- **Reglas relacionadas:** RN-02

#### CA-13 — Listado de descuadres del periodo

```gherkin
Scenario: El administrador consulta los descuadres registrados
  Given que en el periodo hubo al menos un cierre de caja con diferencia entre lo registrado y lo entregado
  When el administrador consulta los descuadres del periodo
  Then el sistema muestra la cantidad de descuadres
  And permite ver la fecha, el cobrador y el importe de cada diferencia
```

---

## 3. Reglas de negocio

### RN-01 — Contador fraccionario de cuotas

- **Descripción:** La cuota es indivisible: no se descompone en interés y capital. El pago parcial se acepta y avanza el contador de forma fraccionaria. No hay descuento por pago anticipado ni cargo de mora: el atraso es un estado, no un valor que crece.
- **Condición:** El cobrador registra un pago cuyo importe es menor, igual o mayor que el de una cuota.
- **Consecuencia:** Una entrega de 25 sobre una cuota de 50 deja 19,5 cuotas restantes de 20. El excedente, si existe, se imputa a la cuota siguiente. El saldo no se redondea a un número entero de cuotas.
- **Requisitos relacionados:** RF-01, RF-05

### RN-02 — Cierre de caja solo sin pendientes e irreversible

- **Descripción:** La caja del cobrador solo puede cerrarse cuando no quedan clientes pendientes de visita. Una vez cerrada es irreversible.
- **Condición:** El cobrador solicita el cierre diario o alguien intenta ajustar una caja ya cerrada.
- **Consecuencia:** Si hay pendientes, el cierre se rechaza. Si el cierre procede, cualquier ajuste posterior exige un asiento nuevo. La caja no se reabre ni se edita.
- **Requisitos relacionados:** RF-02, RF-07

### RN-03 — El desembolso no libera dinero hasta la confirmación del cliente

- **Descripción:** Un desembolso aprobado no descuenta dinero de la caja hasta que el cliente final confirma la recepción con el código. El código es único, está asociado a esa operación y a ese cliente, y caduca pasado su plazo.
- **Condición:** El administrador aprueba una solicitud, el cliente presenta el código, o vence el plazo sin confirmación.
- **Consecuencia:** La confirmación vigente asienta el desembolso y descuenta la caja. La caducidad no descuenta dinero y deja un asiento del intento con su motivo.
- **Requisitos relacionados:** RF-03, RF-06

### RN-04 — Libro de movimientos de solo inserción

- **Descripción:** El libro de movimientos solo admite inserciones. Un error no se edita ni se borra: se corrige con un asiento que lo compensa, y ambos quedan visibles.
- **Condición:** Se confirma una operación de dinero o se detecta un error en un asiento ya creado.
- **Consecuencia:** Queda prohibido modificar o eliminar un asiento existente. La corrección no oculta el original.
- **Requisitos relacionados:** RF-02, RF-03, RF-04

### RN-05 — Renovación solo con préstamo liquidado

- **Descripción:** La renovación o un nuevo desembolso exige que el préstamo anterior esté pagado en su totalidad, salvo que el administrador autorice expresamente la excepción, que queda registrada como tal.
- **Condición:** Se solicita un desembolso para un cliente que ya tiene un préstamo.
- **Consecuencia:** Si hay saldo pendiente, la operación se bloquea. Solo avanza con una excepción explícita del administrador.
- **Requisitos relacionados:** RF-03, RF-05

### RN-06 — Quien origina no aprueba

- **Descripción:** Quien origina una operación no puede aprobarla. Un administrador no puede crear una solicitud de desembolso y aprobársela a sí mismo.
- **Condición:** Un usuario intenta aprobar una solicitud que él mismo originó.
- **Consecuencia:** La aprobación se rechaza y queda registrada la identidad de quien la intentó.
- **Requisitos relacionados:** RF-03

---

## 4. Escenarios de calidad

### EC-01 — Un asiento confirmado no puede alterarse

- **Atributo de calidad:** Auditabilidad
- **Fuente del estímulo:** Administrador u otro usuario autorizado
- **Estímulo:** Intenta modificar o eliminar un asiento ya confirmado en el libro de movimientos
- **Entorno:** Operación normal, con al menos un asiento confirmado
- **Artefacto afectado:** Libro de movimientos
- **Respuesta esperada:** El sistema rechaza la alteración. Si hay que corregir, se crea un asiento compensatorio y ambos permanecen consultables, con identidad de quien ejecutó cada uno y con hora del dispositivo y del servidor.
- **Medida de respuesta:** El 100 % de los intentos de modificación o borrado de un asiento confirmado es rechazado. En toda corrección quedan visibles el asiento original y el compensatorio.
- **Forma prevista de verificación:** Prueba automatizada que intenta alterar un asiento confirmado y consulta después el libro de movimientos.

### EC-02 — La autoaprobación de un desembolso se rechaza siempre

- **Atributo de calidad:** Seguridad
- **Fuente del estímulo:** Usuario con rol de administrador que originó la solicitud
- **Estímulo:** Intenta aprobar el desembolso que él mismo registró
- **Entorno:** Operación normal
- **Artefacto afectado:** Cadena de aprobación del desembolso
- **Respuesta esperada:** El sistema rechaza la aprobación, no genera código de confirmación y registra el intento con la identidad del usuario.
- **Medida de respuesta:** El 100 % de las autoaprobaciones es rechazado. Ningún desembolso originado y aprobado por la misma persona llega a generar código.
- **Forma prevista de verificación:** Prueba automatizada del flujo de aprobación, ejecutada sobre la interfaz de entrada del sistema.

### EC-03 — El cálculo de un pago parcial es exacto y repetible

- **Atributo de calidad:** Exactitud del cálculo
- **Fuente del estímulo:** Cobrador o suite de prueba
- **Estímulo:** Registra un pago de 25 sobre un préstamo de 20 cuotas de 50, sin pagos previos
- **Entorno:** Operación normal o ejecución de pruebas
- **Artefacto afectado:** Cálculo de imputación de pagos y contador de cuotas
- **Respuesta esperada:** El sistema deja 19,5 cuotas restantes de 20 y un saldo restante coherente con ese avance. El mismo caso produce siempre el mismo resultado.
- **Medida de respuesta:** En el 100 % de las repeticiones del caso, el contador es 19,5 de 20 y no existe diferencia de redondeo respecto del valor esperado.
- **Forma prevista de verificación:** Pruebas automatizadas sobre el cálculo de imputación y del contador fraccionario, con casos de pago parcial, pago exacto y excedente.

### EC-04 — Una notificación fallida no deja el control antifraude en silencio

- **Atributo de calidad:** Integridad
- **Fuente del estímulo:** Servicio externo de notificación
- **Estímulo:** No confirma el envío del comprobante o del código de confirmación
- **Entorno:** Operación normal, con el servicio de notificación no disponible o en error
- **Artefacto afectado:** Emisión de notificaciones asociada a un asiento de dinero
- **Respuesta esperada:** El sistema no marca la operación como notificada. El estado del envío queda fallido o pendiente, y el administrador puede detectarlo.
- **Medida de respuesta:** El 100 % de los envíos no confirmados queda en estado fallido o pendiente. Ningún asiento confirmado aparece como notificado si el envío no se completó.
- **Forma prevista de verificación:** Prueba con el servicio de notificación sustituido por una implementación que simula el fallo, y consulta posterior del estado del envío.

---

## 5. Requisitos arquitectónicamente significativos

| ID | Elemento de origen | Justificación de importancia arquitectónica |
|---|---|---|
| ASR-01 | RN-04 / EC-01 | La inmutabilidad del libro de movimientos obliga a decidir cómo se persisten las operaciones de dinero y cómo se corrigen sin perder el pasado. Si un asiento puede alterarse, el producto deja de resolver el problema que lo justifica. |
| ASR-02 | RN-03 / RF-03 / RF-06 | El desembolso depende de un código con caducidad y de una notificación a un tercero que no opera el sistema. Eso condiciona el manejo de estados, plazos y la frontera con un servicio externo reemplazable. |
| ASR-03 | RN-06 / EC-02 | La regla de que quien origina no aprueba condiciona el modelo de autorización y la verificación de límites del lado del servidor, no solo en la interfaz. |
| ASR-04 | RN-01 / EC-03 | El contador fraccionario y la prohibición de redondear el dinero condicionan la forma de representar importes y de aislar el cálculo para poder demostrarlo. |
| ASR-05 | EC-04 / RES-03 | El asiento y la notificación deben poder rastrearse de forma conjunta. Un envío perdido sin estado visible rompe el control antifraude y obliga a tratar la integración como un componente con contrato y fallo explícito. |

---

## 6. Restricciones

| ID | Descripción | Origen | Consecuencia para el proyecto |
|---|---|---|---|
| RES-01 | El sistema no custodia dinero: no recibe, no retiene y no transfiere fondos. El efectivo y las transferencias se registran como información. | Regla de negocio del cliente y límite legal del producto | No se construye wallet, pasarela ni conciliación bancaria. El medio de pago es un dato del asiento, no un flujo de fondos. |
| RES-02 | El trabajo lo realizan dos estudiantes durante el semestre y la demostración debe poder hacerse en un entorno local. | Condición académica de la asignatura | El compromiso se limita al módulo de registro y conciliación de cobranza diaria. Quedan fuera la aplicación nativa, el aislamiento entre empresas y el despliegue en nube pública. |
| RES-03 | El canal real de notificación al cliente final no está disponible: el proveedor previsto exige una empresa formalmente registrada. | Restricción del entorno del cliente | La notificación se trata como servicio reemplazable. Durante el curso se usa un adaptador simulado y no se conecta el proveedor real. |
| RES-04 | El sistema trata datos personales del cliente final y una cadena de aprobación sobre dinero. | Privacidad y seguridad del dominio | Hay que conservar identidad de quien ejecuta cada operación y no exponer al cliente final como usuario del sistema. No se exigirá certificación formal en el curso. |
| RES-05 | Los dos controles antifraude —comprobante al cliente y confirmación del desembolso— son no negociables para el valor del producto. | Decisión confirmada del cliente | RF-03 y RF-06 no pueden aplazarse ni sustituirse por un registro interno que solo vea la empresa. |

---

## 7. Matriz inicial de trazabilidad

| Requisito | Interesado | Criterios de aceptación | Reglas de negocio | Escenarios de calidad | ASR | Restricciones |
|---|---|---|---|---|---|---|
| RF-01 | INT-01 | CA-01, CA-02 | RN-01 | EC-03 | ASR-04 | RES-01 |
| RF-02 | INT-01, INT-02 | CA-03, CA-04 | RN-02, RN-04 | EC-01 | ASR-01 | RES-01 |
| RF-03 | INT-02, INT-03 | CA-05, CA-06 | RN-03, RN-05, RN-06 | EC-02, EC-04 | ASR-02, ASR-03 | RES-05 |
| RF-04 | INT-02 | CA-07, CA-08 | RN-04 | EC-01 | ASR-01 | RES-04 |
| RF-05 | INT-02 | CA-09, CA-10 | RN-01, RN-05 | EC-03 | ASR-04 | RES-01 |
| RF-06 | INT-03 | CA-11, CA-12 | RN-03 | EC-04 | ASR-02, ASR-05 | RES-03, RES-05 |
| RF-07 | INT-02 | CA-13 | RN-02 | No aplica | No aplica | No aplica |

# Ficha de propuesta del proyecto

Asignatura: Arquitectura de Software, Universidad Ean
Integrantes: Julian Andres Restrepo

## A. Identificacion

- Nombre provisional: ROYEXA
- Integrante 1: Julian Andres Restrepo
- Dominio o sector: tecnología financiera aplicada a la gestión de cobranza en calle. El sistema se dirige a financieras pequeñas que prestan cantidades reducidas y las cobran a diario, puerta a puerta.
- Contexto: una financiera pequeña presta cantidades reducidas a muchas personas y las cobra de lunes a sábado en la calle. El cobrador recorre su ruta solo, sin supervisión y buena parte de la jornada sin señal de móvil. El control se lleva hoy con un producto de terceros apoyado en hojas de cálculo.

## B. Problema

### Situacion actual

Una financiera pequeña presta cantidades reducidas a muchas personas y las cobra a diario, de lunes a sábado, en la calle. El dinero pasa por las manos de un cobrador que recorre su ruta solo, sin supervisión y buena parte de la jornada sin señal de móvil. El control se lleva hoy con un producto de terceros apoyado en hojas de cálculo, donde los registros pueden editarse después de haberse creado.

### Personas o entidades afectadas

El dueño de la financiera, que no puede verificar lo que se cobró; el administrador, que aprueba desembolsos sin información suficiente; el cobrador, que no tiene forma de demostrar que hizo su trabajo y queda expuesto a sospechas; y el cliente final, que paga en efectivo y no recibe ningún comprobante independiente de la palabra del cobrador.

### Consecuencias

Se abren dos huecos por los que se escapa el dinero. El primero es que el cobrador reciba el pago y no lo registre: el cliente queda satisfecho, el importe nunca entra al sistema y, sin un tercero que lo confirme, la palabra del cobrador es el único registro que existe. El segundo es que se reporte un desembolso que nunca se entregó, quedándose con el efectivo. A esto se suma que los descuadres de caja se detectan tarde, cuando ya no es posible reconstruir qué ocurrió.

### Solucion actual

El producto que usan hoy no incorpora ninguno de los dos controles, permite modificar registros ya creados y no ofrece exportación de los datos propios, de modo que la información queda cautiva. La conciliación se hace a mano, en hojas de cálculo, y depende de llamadas telefónicas entre el cobrador y el administrador.

### Evidencia o fuente

Observación de la operación diaria de una financiera pequeña que cobra en calle y del producto de terceros que usa hoy. El dueño declaró los descuadres de caja mensuales como la métrica prioritaria del negocio.

## C. Proposito de la solucion

- Resultado que se busca alcanzar: construir un sistema de registro de cobranza en el que cada movimiento de dinero deje evidencia que pueda verificar alguien distinto de quien lo registró, de modo que el dueño de la financiera pueda delegar el cobro sin delegar la confianza. El objetivo no es gestionar la cobranza, que ya se gestiona, sino impedir el fraude interno.
- Beneficiarios: el dueño y el administrador de la financiera, que obtienen un registro que no puede alterarse y una detección de descuadres el mismo día; el cobrador, que obtiene una prueba de su propio trabajo; y el cliente final, que recibe un comprobante que no depende de la buena fe del cobrador.
- Valor esperado: reducir los descuadres de caja mensuales, que es la métrica que el cliente declaró como prioritaria, y convertir cada pago en un hecho verificable por dos partes independientes.
- Limites iniciales: el sistema no custodia dinero en ningún momento: no recibe, no retiene y no transfiere fondos. El efectivo y las transferencias se registran como información sobre una gestión que ocurre fuera del sistema. Tampoco sustituye el criterio humano en la concesión de préstamos, que sigue siendo una decisión del administrador.

## D. Interesados preliminares

### Interesado 1

- Rol: cobrador
- Necesidad: registrar cobros de forma rápida durante la ruta y que ese registro quede firme aunque no tenga conexión en el momento.
- Preocupacion principal: poder demostrar que entregó todo lo que recibió, porque hoy cualquier diferencia en la caja se interpreta en su contra sin que pueda probar lo contrario.
- Participacion en el sistema: registra solicitudes de desembolso, pagos y no pagos, y cierra la caja al final de la ruta.

### Interesado 2

- Rol: administrador
- Necesidad: aprobar los desembolsos antes de que salga el dinero y revisar al cierre del día que lo registrado coincide con lo entregado.
- Preocupacion principal: que un registro pueda modificarse después de creado, porque eso permitiría ocultar una diferencia editando el pasado.
- Participacion en el sistema: aprueba o rechaza desembolsos, consulta el libro de movimientos y supervisa el cierre de caja.

### Interesado 3

- Rol: cliente final
- Necesidad: saber cuánto pagó y cuánto le queda por pagar.
- Preocupacion principal: no tener ninguna prueba de sus propios pagos, de modo que ante una discrepancia con el cobrador su versión no puede sostenerse.
- Participacion en el sistema: no opera el sistema; solo recibe la notificación de comprobante o el código de confirmación del desembolso. Esa notificación es lo que convierte el pago en un hecho verificable por un tercero.

## E. Flujo principal candidato

- Nombre del flujo: desembolso de un préstamo
- Actor o sistema que lo inicia: cobrador
- Resultado observable esperado: el desembolso queda asentado en el libro de movimientos, se genera el calendario de cuotas, se descuenta el importe de la caja del cobrador y la operación es consultable con la identidad de quien la solicitó y de quien la aprobó. Si el cliente no confirma a tiempo, la operación caduca, el dinero no se descuenta y queda un asiento del intento con su motivo.

### Pasos

1. El cobrador registra en el sistema una solicitud de desembolso para un cliente de su ruta, indicando el monto, el plazo y el número de cuotas.
2. El sistema valida las reglas de negocio: comprueba que el cliente exista, que no tenga un préstamo anterior sin liquidar y que el monto esté dentro de los límites configurados para esa ruta.
3. Si el monto supera el límite del cobrador, la solicitud queda en espera de autorización; si no lo supera, avanza directamente al paso siguiente.
4. El administrador revisa la solicitud junto con el historial del cliente y la aprueba o la rechaza indicando el motivo. No puede aprobar una solicitud que él mismo haya originado.
5. Si la aprueba, el sistema genera un código de confirmación único, con caducidad, asociado a esa operación y a ese cliente.
6. El sistema envía el código al cliente final por el canal de notificación configurado.
7. El cliente confirma la recepción del dinero presentando el código, que el cobrador valida desde la aplicación.
8. El sistema registra el desembolso como asiento en el libro de movimientos, genera el calendario de cuotas y descuenta el importe de la caja del cobrador.
9. La operación queda consultable por el administrador, con la hora del dispositivo y la del servidor, y con la identidad de quien la solicitó y de quien la aprobó.

### Parte que se espera implementar

El flujo de desembolso de extremo a extremo, incluyendo la validación de reglas, la aprobación del administrador, el código de confirmación del cliente final, el asiento en el libro de movimientos y el camino alternativo de caducidad. Queda fuera la operación sin conexión en un dispositivo nativo; la demostración se hará sobre la interfaz web.

## F. Funcionalidades iniciales

### Esenciales

- Registro de pago y de no pago durante la ruta, con motivo y compromiso de pago en el segundo caso, y con contador fraccionario de cuotas cuando el pago es parcial.
- Cierre diario de caja en tres paneles, que muestra clientes pendientes, clientes que pagaron y clientes que no pagaron, y que calcula la diferencia entre lo registrado y lo entregado.
- Aprobación de desembolsos con código de confirmación del cliente final, según el flujo de la sección E.
- Libro de movimientos inmutable, donde toda operación de dinero queda asentada y las correcciones se hacen mediante asientos compensatorios visibles.
- Alta y consulta de clientes y préstamos, con el calendario de cuotas derivado del monto, el plazo y el interés.
- Notificación de comprobante al cliente final tras cada pago, indicando el importe recibido, el saldo restante y la fecha del próximo vencimiento.

### Complementarias

- Tablero de administración con el número de descuadres del periodo y su evolución.
- Gestión de usuarios con roles y límites de autorización configurables por ruta.
- Alertas automáticas por atraso del cliente y por caja que lleva demasiadas horas sin cerrarse.

### Fuera del alcance inicial

- Aplicación móvil nativa con operación completa sin conexión y sincronización posterior.
- Aislamiento entre varias empresas sobre una misma instalación, portal de consulta para el cliente final, evaluación crediticia automática y asistente de inteligencia artificial.

## G. Reglas de negocio preliminares

### RN-01. Contador fraccionario de cuotas

- Descripcion: la cuota es indivisible, pero el pago parcial se acepta y avanza el contador de forma fraccionaria.
- Condicion o situacion que la activa: el cobrador registra un pago cuyo importe es menor que el de una cuota.
- Resultado o restriccion: una entrega de 25 sobre una cuota de 50 deja 19,5 cuotas restantes de 20, no 20 ni 19. El sistema no descompone la cuota en interés y capital.

### RN-02. Cierre de caja irreversible

- Descripcion: la caja del cobrador solo puede cerrarse cuando no quedan clientes pendientes de visita, y una vez cerrada es irreversible.
- Condicion o situacion que la activa: el cobrador solicita el cierre diario de su caja.
- Resultado o restriccion: si hay clientes pendientes, el cierre se rechaza. Si el cierre procede, cualquier ajuste posterior exige un asiento nuevo; la caja cerrada no se reabre ni se edita.

### RN-03. Confirmacion del desembolso por el cliente final

- Descripcion: un desembolso aprobado no libera el dinero hasta que el cliente final confirma la recepción con el código, y el código caduca pasado su plazo.
- Condicion o situacion que la activa: el administrador aprueba una solicitud de desembolso, o vence el plazo del código sin confirmación.
- Resultado o restriccion: el importe no se descuenta de la caja hasta la confirmación. Si el código caduca, la operación no libera dinero y queda un asiento del intento con su motivo.

### RN-04. Libro de movimientos de solo insercion

- Descripcion: el libro de movimientos solo admite inserciones. Un error no se edita ni se borra: se corrige con un asiento que lo compensa, y ambos quedan visibles.
- Condicion o situacion que la activa: se registra una operación de dinero o se detecta un error en un asiento ya creado.
- Resultado o restriccion: no es posible modificar ni eliminar un asiento existente. La corrección deja rastros del original y del compensatorio.

### RN-05. Renovacion solo con prestamo liquidado

- Descripcion: la renovación de un préstamo exige que el anterior esté pagado en su totalidad, salvo que el administrador autorice expresamente la excepción, que queda registrada como tal.
- Condicion o situacion que la activa: se solicita un nuevo desembolso para un cliente que ya tiene un préstamo.
- Resultado o restriccion: si el préstamo anterior no está liquidado, la solicitud se bloquea. Solo avanza si el administrador registra una excepción explícita.

### RN-06. Quien origina no aprueba

- Descripcion: quien origina una operación no puede aprobarla. Un administrador no puede crear una solicitud de desembolso y aprobársela a sí mismo.
- Condicion o situacion que la activa: un usuario intenta aprobar una solicitud que él mismo originó.
- Resultado o restriccion: el sistema rechaza la aprobación y conserva la identidad de quien intentó ejecutarla.

## H. Atributos de calidad preliminares

### Atributo 1

- Nombre: auditabilidad
- Justificacion: es el atributo que sostiene el propósito del sistema. Si el registro puede alterarse, el producto deja de resolver el problema que lo justifica, porque un fraude se oculta editando el pasado.
- Respuesta esperada, cuando sea posible: toda operación de dinero queda en un libro de solo inserción, con doble marca de tiempo del dispositivo y del servidor, y con la identidad de quien la ejecutó. Las correcciones no borran el pasado: dejan un asiento compensatorio visible.

### Atributo 2

- Nombre: seguridad
- Justificacion: el sistema maneja dinero, datos personales y una cadena de aprobación donde el abuso de permisos es exactamente el riesgo que se combate.
- Respuesta esperada, cuando sea posible: el acceso se controla por rol, quien origina no aprueba, y los límites de autorización se verifican del lado del servidor, nunca solo en el cliente.

### Atributo 3

- Nombre: capacidad de prueba
- Justificacion: es lo que permite demostrar los dos atributos anteriores de forma objetiva. El cálculo de intereses, la imputación de pagos y el contador fraccionario deben poder verificarse de manera determinista.
- Respuesta esperada, cuando sea posible: las reglas de dinero pueden comprobarse con casos de prueba repetibles, y las dependencias externas, como la notificación, pueden sustituirse por una implementación falsa durante las pruebas.

No se priorizan la alta disponibilidad ni la escalabilidad, porque el volumen previsto no las justifica y su exigencia desplazaría el esfuerzo desde el diseño hacia la infraestructura.

## I. Restricciones

- Restriccion tecnica, si existe: el sistema no custodia dinero en ningún momento. El efectivo y las transferencias se registran como información sobre una gestión que ocurre fuera del sistema.
- Restriccion institucional o de entorno: el trabajo se realiza en pareja, en el marco de la asignatura de Arquitectura de Software de la Universidad Ean, y debe poder demostrarse de forma local.
- Restriccion de tiempo o conocimiento: el producto completo excede la capacidad del equipo en el periodo del semestre. El compromiso se limita al módulo de registro y conciliación de cobranza diaria.
- Restriccion de seguridad o privacidad, si aplica: el sistema trata datos personales del cliente final y una cadena de aprobación. Se diseñará de forma compatible con la protección de esos datos, pero no se obtendrán certificaciones formales durante el curso.

## J. Integracion candidata

- Sistema o servicio: servicio externo de notificación al cliente final.
- Proposito de la integracion: enviar el comprobante de cada pago y el código de confirmación del desembolso, que son los dos controles que convierten el movimiento de dinero en un hecho verificable por un tercero.
- Datos intercambiados: destinatario, importe recibido, saldo restante, fecha del próximo vencimiento y, en el desembolso, el código de confirmación con su plazo de caducidad.
- Riesgo principal: si el asiento se confirma y la notificación se pierde, el cliente no recibe su comprobante y nadie se entera, con lo que el control antifraude queda roto en silencio. El canal definitivo no está decidido, porque el proveedor previsto exige una empresa formalmente registrada y las financieras destinatarias no cumplen ese requisito.
- Forma de simularla si el servicio no esta disponible: tratar la notificación como componente reemplazable. Durante el curso se construye un adaptador simulado que registra los mensajes emitidos, y un adaptador falso para las pruebas, de modo que el proveedor real pueda conectarse después sin alterar la lógica de negocio.

## K. Riesgos preliminares

### Riesgo funcional o de requisitos

- Descripcion: el diseño gira alrededor del efectivo, pero una parte creciente de los pagos llega por transferencia, caso en el que el cobrador no visita al cliente y la caja física deja de describir la operación. Si esa proporción es mayor de lo previsto, el modelo centrado en la caja explica solo una fracción del negocio y el primero de los dos fraudes deja de ser el problema principal. Mitigación: cerrar la duda antes de diseñar el modelo de datos y mantener el libro de movimientos independiente del medio de pago.

### Riesgo tecnico o arquitectonico

- Descripcion: la consistencia entre el asiento en el libro de movimientos y el envío de la notificación. Si el asiento se confirma y la notificación se pierde, el cliente no recibe su comprobante y el control antifraude queda roto en silencio. Mitigación: el asiento y el registro de la notificación deben ocurrir juntos o no ocurrir, y cada envío debe dejar un estado consultable.

### Riesgo de tiempo, conocimiento o dependencia externa

- Descripcion: el alcance completo del producto excede la capacidad del equipo en el periodo disponible, y una de sus piezas centrales depende de un servicio externo cuya contratación no está garantizada. Mitigación: las secciones L y M delimitan lo que efectivamente se construye, y la integración se trata como componente reemplazable para no detener el avance si el proveedor no está disponible.

## L. Alcance de implementacion

- Parte del flujo principal que se implementara: el desembolso de un préstamo de extremo a extremo, desde la solicitud del cobrador hasta la confirmación del cliente final o la caducidad del código, incluyendo el asiento en el libro de movimientos.
- Funcionalidades esenciales comprometidas: registro de pago y de no pago, cierre diario de caja con detección de descuadre, aprobación de desembolsos con código de confirmación, libro de movimientos inmutable, alta y consulta de clientes y préstamos, y notificación de comprobante mediante adaptador simulado.
- Posible necesidad de persistencia: sí. El modelo de dominio queda en ocho conceptos: cliente, préstamo, cuota, pago, no pago, caja, desembolso y asiento del libro de movimientos. El libro de movimientos debe restringir las alteraciones, de modo que la inmutabilidad no dependa solo de que la aplicación se comporte bien.
- Integracion contemplada inicialmente: notificación al cliente final por interfaz, con adaptador simulado. No se conecta el proveedor real.
- Resultado funcional esperado al finalizar el curso: una interfaz web que cubra los dos roles operativos, cobrador y administrador, sobre el módulo de registro y conciliación de cobranza diaria, con el flujo de desembolso demostrable, el cierre de caja que detecta descuadre y el libro de movimientos consultable. El cliente final aparece como destinatario de la notificación, sin acceso al sistema.

## M. Fuera de alcance

- Aplicación móvil nativa y operación completa sin conexión, incluyendo sincronización posterior, cola local de operaciones y tratamiento de los casos límite asociados. Se sustituye por la interfaz web.
- Aislamiento entre varias empresas sobre una misma instalación. Se trabajará con una sola empresa.
- Portal de consulta para el cliente final, evaluación crediticia automática, asistente de inteligencia artificial, reportes a socios, analítica avanzada y ordenación geográfica de rutas.
- Conexión del proveedor real de notificaciones y obtención de certificaciones formales de protección de datos o de seguridad de la información.
- Despliegue en una nube pública y automatización de infraestructura. El entorno de demostración será local.

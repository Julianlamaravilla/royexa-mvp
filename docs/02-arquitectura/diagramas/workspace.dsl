workspace "ROYEXA" "Arquitectura consolidada de la Entrega 4, realineada con la Entrega 1" {

    !identifiers hierarchical

    model {
        // =============================================================
        // 1. PERSONAS
        // =============================================================
        // Roles del sistema. Se relacionan con los INT-XX de la Entrega 1.
        // Los elementos con la etiqueta "Diferido" o "Historico" conservan su
        // identificador en el modelo y quedan fuera de las vistas. "Diferido"
        // marca lo que salió del alcance (ver realineacion-entrega-1.md);
        // "Historico", lo que la implementación absorbió en otro elemento.

        cobrador = person "Cobrador" "Recorre su ruta de lunes a sábado, solicita desembolsos, valida el código del cliente, registra cobros y no pagos, y cierra su caja del día." {
            properties {
                "Identificador" "INT-01"
            }
        }

        administrador = person "Administrador" "Aprueba o rechaza los desembolsos que no originó antes de que salga el dinero, y verifica cada cierre de caja." {
            properties {
                "Identificador" "INT-02"
            }
        }

        clienteFinal = person "Cliente final" "Recibe el código de confirmación y los comprobantes. No opera el sistema." {
            properties {
                "Identificador" "INT-03"
            }
        }

        socio = person "Socio" "Dueño o inversionista de la financiera. Consultaba reportes en solo lectura." {
            tags "Diferido"
            properties {
                "Identificador" "Sin INT en la Entrega 1 (DIV-04)"
            }
        }

        // =============================================================
        // 2. SISTEMA OBJETO DE ESTUDIO
        // =============================================================

        sistema = softwareSystem "ROYEXA" "Registro de cobranza en calle donde cada movimiento de dinero deja evidencia inalterable que puede verificar alguien distinto de quien lo registró, para impedir el fraude interno y detectar el descuadre de caja el mismo día." {

            // =========================================================
            // 2.1 CONTENEDORES
            // =========================================================

            movil = container "Aplicación móvil del cobrador" "Registraba cobros sin señal en una cola local cifrada y sincronizaba al volver la señal." "React Native + TypeScript, SQLCipher (Android 10+)" {
                tags "Diferido"
                properties {
                    "Identificador" "CON-01"
                    "Decisiones" "ADR-003 (Rechazado, reemplazado por ADR-004)"
                }
            }

            web = container "Aplicación web mínima" "Se previó como contenedor aparte que llamaría a la API. En la Entrega 4 las páginas se renderizan en el mismo proceso que la API y forman el componente CMP-14 de CON-03. Se conserva como registro histórico y queda fuera de las vistas." "Plantillas renderizadas en el servidor" {
                tags "Historico"
                properties {
                    "Identificador" "CON-02"
                    "Decisiones" "AD-02, AD-03, ADR-002, ADR-004"
                    "Reemplazado por" "CON-03 / CMP-14 (Entrega 4)"
                }
            }

            api = container "Servidor de aplicación" "Monolito modular en un solo proceso: sirve la API JSON y las páginas web renderizadas en el servidor, valida las reglas de negocio, calcula el dinero, escribe el libro mayor y despacha los avisos en segundo plano." "Python 3.14, FastAPI, Jinja2, Uvicorn; local o un servicio web en Docker" {
                properties {
                    "Identificador" "CON-03"
                    "Decisiones" "AD-01, AD-02, AD-03, AD-06, ADR-001, ADR-002, ADR-004"
                }

                // =====================================================
                // 2.2 COMPONENTES DE CON-03 (Entrega 4, MVP completo)
                // =====================================================
                // Solo se descompone CON-03, el contenedor principal.
                // Cada componente agrupa un módulo real de backend/src/royexa.
                // shared/ es un núcleo compartido sin dependencias hacia los
                // módulos (dinero, reloj, calendario, errores): no se modela
                // como componente, salvo la bandeja de salida, que se cuenta
                // dentro de Avisos.

                entradaHttp = component "Entrada HTTP/JSON" "Traduce HTTP a casos de uso, resuelve el actor por el token de sesión (Authorization: Bearer o cookie), exige el rol de administrador donde corresponde, convierte los errores de dominio en detalles de problema, expone /health y arranca el despacho en segundo plano con el ciclo de vida de la aplicación." "FastAPI, api.py" {
                    properties {
                        "Identificador" "CMP-01"
                        "Contratos" "CTR-01"
                        "Origen" "RF-02, RF-03, RF-04, RF-05, RF-06, AD-06"
                    }
                }

                webPaginas = component "Web" "Páginas en español renderizadas en el servidor bajo /web: ingreso, ruta del día, pagos y no pagos, desembolsos, cierre de caja, panel del administrador con gráficos dibujados en el servidor, clientes, ajustes, descuadres y avisos. Sesión por cookie y fichas de formulario de un solo uso." "FastAPI, Jinja2, web/" {
                    properties {
                        "Identificador" "CMP-14"
                        "Origen" "CON-02, RF-02, RF-03, RF-04, RF-05, RF-06"
                    }
                }

                casosUso = component "Casos de uso de desembolso" "Coordina solicitar, aprobar, rechazar, confirmar y conceder la excepción, y las consultas del desembolso, el libro y la caja. No decide reglas: abre la unidad de trabajo y aplica lo que deciden los agregados." "Python, sales/application.py" {
                    properties {
                        "Identificador" "CMP-02"
                        "Contratos" "CTR-02, CTR-04, CTR-11"
                        "Origen" "RF-03, RF-05, ADR-004"
                    }
                }

                dominioDesembolso = component "Dominio del desembolso" "Agregado Disbursement y código de confirmación: estados, autoaprobación prohibida, caducidad, intentos fallidos e idempotencia de la confirmación." "Python, sales/domain.py" {
                    properties {
                        "Identificador" "CMP-03"
                        "Origen" "RF-03, RN-03, RN-06, EC-02, ADR-004"
                    }
                }

                prestamos = component "Préstamos, pagos y no pagos" "Condiciones, calendario de cuotas de lunes a sábado, regla de renovación y excepción de un solo uso; registra pagos con su imputación a cuotas y no pagos, y calcula las visitas pendientes y los paneles del día." "Python, loans/" {
                    properties {
                        "Identificador" "CMP-04"
                        "Contratos" "CTR-06"
                        "Origen" "RF-01, RF-05, RN-05, CA-09, CA-10"
                    }
                }

                clientes = component "Clientes" "Registro y consulta de los clientes finales de cada ruta." "Python, clients/" {
                    properties {
                        "Identificador" "CMP-15"
                        "Origen" "RF-05, INT-03"
                    }
                }

                libro = component "Libro de movimientos" "Único escritor del libro: crea cada asiento (desembolso, intento caducado, pago y ajuste) y lo enlaza con su efecto sobre la caja." "Python, ledger/" {
                    properties {
                        "Identificador" "CMP-05"
                        "Contratos" "CTR-05"
                        "Origen" "RF-04, RN-04, CA-07, CA-08, INV-02, ADR-001"
                    }
                }

                caja = component "Caja" "Caja del día de cada cobrador: se abre con el primer movimiento y el fondo del cobrador, solo admite movimientos mientras está abierta y queda cerrada tras el cierre." "Python, cash_box/" {
                    properties {
                        "Identificador" "CMP-06"
                        "Contratos" "CTR-07"
                        "Origen" "RF-02, RN-02, RN-03"
                    }
                }

                cierre = component "Cierre, ajustes y descuadres" "Cierra la caja del día contra el efectivo que entrega el cobrador, registra ajustes como contra-asientos y calcula los descuadres y el flujo de caja que consulta el administrador." "Python, closing/" {
                    properties {
                        "Identificador" "CMP-16"
                        "Origen" "RF-02, RN-02, CA-03, CA-04, CA-08"
                    }
                }

                identidadCatalogos = component "Identidad y sesiones" "Usuarios y rutas sembrados, contraseñas con scrypt, bloqueo por intentos, y sesiones con token opaco del que solo se guarda el resumen." "Python, identity_access/" {
                    properties {
                        "Identificador" "CMP-07"
                        "Origen" "RES-04, AD-06, ALT-06B"
                    }
                }

                avisos = component "Avisos" "Bandeja de salida (shared/outbox.py) donde los módulos de negocio encolan avisos en su propia transacción, y despachador que es su único lector: envía cada aviso pendiente, cuenta intentos y expone el estado al administrador." "Python, notifications/, shared/outbox.py" {
                    properties {
                        "Identificador" "CMP-08"
                        "Contratos" "CTR-03, CTR-08, CTR-09, CTR-10, CTR-11"
                        "Origen" "RF-06, CA-12, EC-04, ASR-05, ADR-002"
                    }
                }

                despachoFondo = component "Despacho en segundo plano" "Bucle dentro del proceso que invoca el despachador cada ROYEXA_DISPATCH_SECONDS. Una ronda fallida se registra y el bucle continúa." "asyncio, background.py" {
                    properties {
                        "Identificador" "CMP-17"
                        "Origen" "ADR-002, RA-03"
                    }
                }

                persistenciaMemoria = component "Persistencia en memoria" "Implementa la unidad de trabajo. Sin base de datos guarda todo el estado en tablas en memoria con transacciones por copia (pruebas rápidas y modo sin PostgreSQL); con ROYEXA_LEDGER_URL toma todos los repositorios de la sesión PostgreSQL." "Python, adapters/memory.py" {
                    tags "Adaptador"
                    properties {
                        "Identificador" "CMP-09"
                        "Contratos" "CTR-04, CTR-05, CTR-06, CTR-07, CTR-08, CTR-09, CTR-12"
                        "Origen" "ADR-002, ADR-004"
                    }
                }

                adaptadorPostgres = component "Adaptadores PostgreSQL" "Implementan el libro y todos los repositorios del estado (desembolsos, préstamos, pagos, no pagos, cajas, cierres, clientes, credenciales, sesiones, fichas de formulario y bandeja de salida) sobre una sola conexión: una transacción REPEATABLE READ por unidad de trabajo, con el rol de la aplicación." "psycopg, adapters/postgres_ledger.py, adapters/postgres_state.py" {
                    tags "Adaptador"
                    properties {
                        "Identificador" "CMP-10"
                        "Contratos" "CTR-04, CTR-05, CTR-06, CTR-07, CTR-08, CTR-12"
                        "Origen" "ADR-001, ADR-002, ADR-004, EV-01, EV-02, EV-12"
                    }
                }

                adaptadorNotificador = component "Adaptador del notificador simulado" "Implementa el puerto del notificador hacia EXT-05. Reproduce el fallo del canal cuando se configura." "Python, adapters/simulated_notifier.py" {
                    tags "Adaptador"
                    properties {
                        "Identificador" "CMP-11"
                        "Contratos" "CTR-10"
                        "Origen" "RES-03, RES-05, ADR-002, EC-04"
                    }
                }

                composicion = component "Composición" "Elige qué adaptador llena cada puerto a partir de la configuración, siembra los datos de demostración o del piloto y crea la aplicación." "Python, bootstrap.py, main.py, seed.py" {
                    properties {
                        "Identificador" "CMP-12"
                        "Origen" "RES-02, ADR-001"
                    }
                }

                migrador = component "Migrador" "Aplica el esquema y sus privilegios con el rol propietario, con reintento ante un bloqueo al arrancar. No participa en las peticiones." "psycopg, migrate.py" {
                    tags "Soporte"
                    properties {
                        "Identificador" "CMP-13"
                        "Origen" "ADR-001, RA-01"
                    }
                }

                fijarContrasena = component "Fijación de contraseñas" "Herramienta de línea de órdenes que fija la contraseña real de un usuario sembrado y revoca sus sesiones. No participa en las peticiones." "psycopg, set_password.py" {
                    tags "Soporte"
                    properties {
                        "Identificador" "CMP-18"
                        "Origen" "RES-04, AD-06"
                    }
                }
            }

            baseDatos = container "Base de datos" "Conserva todo el estado: el libro de solo inserción y los desembolsos, préstamos, pagos, no pagos, cajas, cierres, clientes, credenciales, sesiones, fichas de formulario y la bandeja de salida." "PostgreSQL 17 local (Docker Compose); PostgreSQL gestionado en el piloto" {
                tags "Database"
                properties {
                    "Identificador" "CON-04"
                    "Decisiones" "AD-01, AD-02, AD-03, ADR-001, ADR-002, ADR-004"
                }
            }

            almacenObjetos = container "Almacén de fotos" "Guardaba las fotos de documento, residencia, comercio y comprobantes de gasto, con verificación de hash." "Amazon S3" {
                tags "Database" "Diferido"
                properties {
                    "Identificador" "CON-05"
                    "Decisiones" "Sin decisión"
                }
            }
        }

        // =============================================================
        // 3. SISTEMAS EXTERNOS
        // =============================================================

        notificador = softwareSystem "Notificador simulado" "Registra el código de confirmación y los comprobantes dirigidos al cliente final. Reemplaza al proveedor real, que no se conecta durante el curso." {
            tags "Existing System"
            properties {
                "Identificador" "EXT-05"
                "Origen" "RES-03, RES-05, ASR-05, AD-02"
            }
        }

        ses = softwareSystem "Amazon SES" "Entregaba el correo de alertas a los administradores." {
            tags "Existing System" "Diferido"
            properties {
                "Identificador" "EXT-01"
                "Origen" "ASR-05, AD-02"
            }
        }

        fcm = softwareSystem "Firebase Cloud Messaging" "Entregaba los avisos push al teléfono del cobrador y del administrador." {
            tags "Existing System" "Diferido"
            properties {
                "Identificador" "EXT-02"
                "Origen" "ASR-05, AD-02"
            }
        }

        telegram = softwareSystem "Telegram Bot API" "Entregaba los reportes y alertas a administradores y socios." {
            tags "Existing System" "Diferido"
            properties {
                "Identificador" "EXT-03"
                "Origen" "ASR-05, AD-02, RES-03"
            }
        }

        sentry = softwareSystem "Servicio de captura de errores" "Recibía los errores del servidor sin datos personales ni cuerpos de petición." {
            tags "Existing System" "Diferido"
            properties {
                "Identificador" "EXT-04"
                "Origen" "EC-01, AD-02"
            }
        }

        // =============================================================
        // 4. RELACIONES DEL MODELO
        // =============================================================

        cobrador -> sistema "Solicita desembolsos, valida el código, registra cobros y no pagos, y cierra su caja"
        administrador -> sistema "Aprueba o rechaza desembolsos y verifica descuadres"
        socio -> sistema "Consulta reportes en solo lectura"
        sistema -> notificador "Envía el código de confirmación y los comprobantes" "Llamada local a través de un puerto"
        notificador -> clienteFinal "Entrega el código de confirmación y los comprobantes (simulado)"
        sistema -> ses "Envía alertas por correo" "HTTPS"
        sistema -> fcm "Envía avisos push" "HTTPS"
        sistema -> telegram "Envía reportes y alertas" "HTTPS"
        sistema -> sentry "Envía errores sin datos personales" "HTTPS"

        cobrador -> sistema.api "Registra pagos y no pagos, solicita y confirma desembolsos y cierra su caja, con páginas web o la API JSON" "HTTP, HTML y JSON"
        administrador -> sistema.api "Aprueba desembolsos, registra clientes y ajustes, y consulta caja, descuadres y avisos, con páginas web o la API JSON" "HTTP, HTML y JSON"
        sistema.movil -> sistema.api "Envía operaciones por lote con identificador único y descarga cambios por cursor" "HTTPS/JSON"
        sistema.api -> sistema.baseDatos "Lee y escribe todo el estado en una transacción por unidad de trabajo; inserta asientos con un rol que no puede modificarlos" "SQL"
        sistema.api -> sistema.almacenObjetos "Emite URL prefirmadas para subir y descargar fotos y registra su hash" "HTTPS"
        sistema.api -> notificador "Envía el código de confirmación y los comprobantes" "Llamada local a través de un puerto"
        sistema.api -> ses "Envía alertas por correo" "HTTPS"
        sistema.api -> fcm "Envía avisos push" "HTTPS"
        sistema.api -> telegram "Envía reportes y alertas" "HTTPS"
        sistema.api -> sentry "Envía errores sin datos personales" "HTTPS"

        // -------------------------------------------------------------
        // Relaciones entre componentes de CON-03 (Entrega 4)
        // -------------------------------------------------------------
        // Se declaran después de las relaciones entre contenedores: así las
        // relaciones implícitas no duplican las que ya existen. Las flechas
        // hacia un adaptador son de ejecución y atraviesan el puerto indicado.
        // La dependencia de código va al revés: el adaptador importa el puerto.

        cobrador -> sistema.api.webPaginas "Registra pagos y no pagos, solicita y confirma desembolsos y cierra su caja" "HTTP/HTML, cookie de sesión"
        administrador -> sistema.api.webPaginas "Aprueba desembolsos, registra clientes y ajustes, y consulta panel, descuadres y avisos" "HTTP/HTML, cookie de sesión"
        cobrador -> sistema.api.entradaHttp "Opera los mismos casos de uso por JSON" "HTTP/JSON, CTR-01"
        administrador -> sistema.api.entradaHttp "Aprueba, rechaza, concede excepciones, despacha avisos y consulta el libro" "HTTP/JSON, CTR-01"

        sistema.api.entradaHttp -> sistema.api.webPaginas "Monta las rutas /web en la misma aplicación" "Llamada directa"
        sistema.api.entradaHttp -> sistema.api.despachoFondo "Arranca y detiene el bucle con el ciclo de vida de la aplicación" "Llamada directa"
        sistema.api.entradaHttp -> sistema.api.identidadCatalogos "Inicia y cierra sesiones y resuelve el actor del token" "Llamada directa"
        sistema.api.entradaHttp -> sistema.api.casosUso "Invoca casos de uso y consultas del desembolso" "CTR-02"
        sistema.api.entradaHttp -> sistema.api.prestamos "Registra pagos y no pagos y consulta préstamos y visitas" "Llamada directa"
        sistema.api.entradaHttp -> sistema.api.clientes "Registra y consulta clientes" "Llamada directa"
        sistema.api.entradaHttp -> sistema.api.cierre "Cierra la caja, registra ajustes y consulta cierres y descuadres" "Llamada directa"
        sistema.api.entradaHttp -> sistema.api.avisos "Invoca el despachador y lee el estado de los avisos" "CTR-03"

        sistema.api.webPaginas -> sistema.api.identidadCatalogos "Inicia sesión y resuelve el actor de la cookie" "Llamada directa"
        sistema.api.webPaginas -> sistema.api.casosUso "Solicita, aprueba, rechaza y confirma desembolsos" "CTR-02"
        sistema.api.webPaginas -> sistema.api.prestamos "Registra pagos y no pagos y lee la ruta del día" "Llamada directa"
        sistema.api.webPaginas -> sistema.api.clientes "Registra y consulta clientes" "Llamada directa"
        sistema.api.webPaginas -> sistema.api.cierre "Cierra la caja, registra ajustes y dibuja descuadres y flujo" "Llamada directa"
        sistema.api.webPaginas -> sistema.api.avisos "Lista los avisos fallidos y pide reintentarlos" "CTR-03"
        sistema.api.webPaginas -> sistema.api.persistenciaMemoria "Guarda y consume las fichas de formulario de un solo uso" "Unidad de trabajo"

        sistema.api.despachoFondo -> sistema.api.avisos "Invoca el despachador cada ROYEXA_DISPATCH_SECONDS" "Llamada directa"

        sistema.api.casosUso -> sistema.api.dominioDesembolso "Delega transiciones, RN-03 y RN-06" "Llamada directa"
        sistema.api.casosUso -> sistema.api.prestamos "Aplica RN-05 y origina el préstamo" "Llamada directa"
        sistema.api.casosUso -> sistema.api.libro "Pide el asiento del desembolso o del intento caducado" "Llamada directa"
        sistema.api.casosUso -> sistema.api.clientes "Resuelve el cliente" "Llamada directa"
        sistema.api.casosUso -> sistema.api.identidadCatalogos "Resuelve ruta y cobrador" "Llamada directa"
        sistema.api.casosUso -> sistema.api.persistenciaMemoria "Abre la unidad de trabajo, guarda estados y encola avisos" "CTR-04, CTR-06, CTR-08"

        sistema.api.dominioDesembolso -> sistema.api.prestamos "Usa las condiciones del préstamo" "Llamada directa"
        sistema.api.prestamos -> sistema.api.libro "Pide el asiento del pago" "Llamada directa"
        sistema.api.prestamos -> sistema.api.persistenciaMemoria "Guarda préstamos, pagos y no pagos y encola el comprobante de pago" "CTR-06, CTR-08"
        sistema.api.clientes -> sistema.api.persistenciaMemoria "Guarda y lee clientes" "Unidad de trabajo"
        sistema.api.cierre -> sistema.api.caja "Cierra la caja del día" "Llamada directa"
        sistema.api.cierre -> sistema.api.libro "Pide el asiento de ajuste" "Llamada directa"
        sistema.api.cierre -> sistema.api.prestamos "Lee las visitas pendientes del día" "Llamada directa"
        sistema.api.cierre -> sistema.api.persistenciaMemoria "Guarda cierres y lee cajas y asientos" "Unidad de trabajo"
        sistema.api.identidadCatalogos -> sistema.api.persistenciaMemoria "Guarda credenciales y sesiones" "Unidad de trabajo"

        sistema.api.libro -> sistema.api.caja "Ubica la caja del día y le aplica el movimiento" "Llamada directa"
        sistema.api.libro -> sistema.api.persistenciaMemoria "Inserta asientos" "CTR-05"
        sistema.api.caja -> sistema.api.persistenciaMemoria "Lee, abre y guarda la caja del día" "CTR-07"

        sistema.api.avisos -> sistema.api.persistenciaMemoria "Lee y actualiza la bandeja de salida" "CTR-08, CTR-09"
        sistema.api.avisos -> sistema.api.adaptadorNotificador "Envía cada aviso pendiente" "CTR-10"

        sistema.api.persistenciaMemoria -> sistema.api.adaptadorPostgres "Con ROYEXA_LEDGER_URL toma todos los repositorios de la sesión y confirma o revierte su transacción" "CTR-12"

        sistema.api.composicion -> sistema.api.entradaHttp "Crea la aplicación y le entrega el contenedor" "Llamada directa"
        sistema.api.composicion -> sistema.api.casosUso "Inyecta el contexto de los casos de uso" "Llamada directa"
        sistema.api.composicion -> sistema.api.avisos "Inyecta unidad de trabajo, notificador y reloj" "Llamada directa"
        sistema.api.composicion -> sistema.api.persistenciaMemoria "Crea el almacén y la unidad de trabajo" "Llamada directa"
        sistema.api.composicion -> sistema.api.adaptadorPostgres "Siembra la base y crea una sesión por unidad de trabajo si existe ROYEXA_LEDGER_URL" "Llamada directa"
        sistema.api.composicion -> sistema.api.adaptadorNotificador "Crea el notificador simulado" "Llamada directa"

        sistema.api.adaptadorPostgres -> sistema.baseDatos "Lee y escribe todo el estado con el rol royexa_app" "SQL"
        sistema.api.migrador -> sistema.baseDatos "Aplica migraciones con el rol royexa_migrator" "SQL"
        sistema.api.fijarContrasena -> sistema.baseDatos "Reemplaza la contraseña y revoca las sesiones del usuario" "SQL"
        sistema.api.adaptadorNotificador -> notificador "Registra el código de confirmación y los comprobantes" "Llamada local a través de un puerto"
    }

    views {
        // =============================================================
        // C4 NIVEL 1: CONTEXTO
        // =============================================================

        systemContext sistema "c4-contexto" "Diagrama C4 de Contexto de ROYEXA." {
            include *
            include clienteFinal
            exclude "element.tag==Diferido"
            exclude "element.tag==Historico"
            autoLayout lr
        }

        // =============================================================
        // C4 NIVEL 2: CONTENEDORES
        // =============================================================

        container sistema "c4-contenedores" "Diagrama C4 de Contenedores de ROYEXA." {
            include *
            include clienteFinal
            exclude "element.tag==Diferido"
            exclude "element.tag==Historico"
            autoLayout tb
        }

        // =============================================================
        // C4 NIVEL 3: COMPONENTES DE CON-03 (Entrega 4)
        // =============================================================

        component sistema.api "c4-componentes" "Componentes de CON-03 en el MVP: desembolsos, préstamos, pagos y no pagos, clientes, caja, cierre, ajustes y descuadres, identidad y sesiones, avisos y su despacho, y los adaptadores." {
            include *
            include clienteFinal
            exclude "element.tag==Diferido"
            exclude "element.tag==Historico"
            autoLayout lr
        }

        styles {
            element "Person" {
                shape Person
                background #08427b
                color #ffffff
            }

            element "Software System" {
                background #1168bd
                color #ffffff
            }

            element "Existing System" {
                background #999999
                color #ffffff
            }

            element "Container" {
                background #438dd5
                color #ffffff
            }

            element "Database" {
                shape Cylinder
            }

            element "Component" {
                background #85bbf0
                color #000000
            }

            element "Adaptador" {
                background #b8d4f0
                color #000000
            }

            element "Soporte" {
                border dashed
            }
        }
    }

    configuration {
        scope softwaresystem
    }
}

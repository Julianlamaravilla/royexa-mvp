workspace "ROYEXA" "Arquitectura candidata realineada con la Entrega 1" {

    !identifiers hierarchical

    model {
        // =============================================================
        // 1. PERSONAS
        // =============================================================
        // Roles del sistema. Se relacionan con los INT-XX de la Entrega 1.
        // Los elementos con la etiqueta "Diferido" conservan su identificador
        // en el modelo y quedan fuera de las vistas. Ver
        // realineacion-entrega-1.md.

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
                    "Decisiones" "ADR-003"
                }
            }

            web = container "Aplicación web mínima" "Permite al cobrador y al administrador operar desembolsos, pagos y cierre de caja. Se construye en la Entrega 4 (provisional)." "Plantillas renderizadas en el servidor, en local" {
                properties {
                    "Identificador" "CON-02"
                    "Decisiones" "AD-02, AD-03, ADR-002, ADR-004"
                }
            }

            api = container "API del servidor" "Monolito modular que valida las reglas de negocio, calcula el dinero, escribe el libro mayor y registra eventos para avisos." "Python 3.14, FastAPI, Uvicorn local" {
                properties {
                    "Identificador" "CON-03"
                    "Decisiones" "AD-01, AD-02, AD-03, AD-06, ADR-001, ADR-002, ADR-004"
                }

                // =====================================================
                // 2.2 COMPONENTES DE CON-03 (Entrega 3)
                // =====================================================
                // Solo se descompone CON-03, el contenedor del recorrido.
                // Cada componente agrupa un módulo real de backend/src/royexa.
                // shared/ es un núcleo compartido sin dependencias hacia los
                // módulos: no se modela como componente.

                entradaHttp = component "Entrada HTTP" "Traduce HTTP a casos de uso, resuelve el actor, exige el rol de administrador donde corresponde y convierte los errores de dominio en detalles de problema." "FastAPI, api.py" {
                    properties {
                        "Identificador" "CMP-01"
                        "Contratos" "CTR-01"
                        "Origen" "RF-03, RF-04, RF-06, AD-06"
                    }
                }

                casosUso = component "Casos de uso de desembolso" "Coordina solicitar, aprobar, rechazar, confirmar y conceder la excepción. No decide reglas: abre la unidad de trabajo y aplica lo que deciden los agregados." "Python, sales/application.py" {
                    properties {
                        "Identificador" "CMP-02"
                        "Contratos" "CTR-02, CTR-04, CTR-11"
                        "Origen" "RF-03, RF-05, ADR-004"
                    }
                }

                dominioDesembolso = component "Dominio del desembolso" "Agregado Disbursement y código de confirmación: estados, autoaprobación prohibida, caducidad e idempotencia de la confirmación." "Python, sales/domain.py" {
                    properties {
                        "Identificador" "CMP-03"
                        "Origen" "RF-03, RN-03, RN-06, EC-02, ADR-004"
                    }
                }

                prestamos = component "Préstamos" "Condiciones, calendario de cuotas de lunes a sábado, regla de renovación y excepción de un solo uso." "Python, loans/" {
                    properties {
                        "Identificador" "CMP-04"
                        "Contratos" "CTR-06"
                        "Origen" "RF-05, RN-05, CA-09, CA-10"
                    }
                }

                libro = component "Libro de movimientos" "Único escritor del libro: crea cada asiento y lo enlaza con su efecto sobre la caja." "Python, ledger/" {
                    properties {
                        "Identificador" "CMP-05"
                        "Contratos" "CTR-05"
                        "Origen" "RF-04, RN-04, CA-07, INV-02, ADR-001"
                    }
                }

                caja = component "Caja" "Saldo de la caja del cobrador. Solo admite movimientos mientras está abierta." "Python, cash_box/" {
                    properties {
                        "Identificador" "CMP-06"
                        "Contratos" "CTR-07"
                        "Origen" "RN-02, RN-03"
                    }
                }

                identidadCatalogos = component "Identidad y catálogos" "Usuarios, roles, rutas y clientes sembrados, sin gestión de cuentas." "Python, identity_access/ y clients/" {
                    properties {
                        "Identificador" "CMP-07"
                        "Origen" "RES-04, AD-06, ALT-06B"
                    }
                }

                avisos = component "Avisos" "Único lector de la bandeja de salida: despacha cada aviso pendiente, cuenta intentos y expone el estado al administrador." "Python, notifications/" {
                    properties {
                        "Identificador" "CMP-08"
                        "Contratos" "CTR-03, CTR-09, CTR-10, CTR-11"
                        "Origen" "RF-06, CA-12, EC-04, ASR-05, ADR-002"
                    }
                }

                persistenciaMemoria = component "Persistencia en memoria" "Implementa la unidad de trabajo con transacciones por copia: desembolsos, préstamos, cajas y bandeja de salida viven aquí durante la Entrega 3." "Python, adapters/memory.py" {
                    tags "Adaptador"
                    properties {
                        "Identificador" "CMP-09"
                        "Contratos" "CTR-04, CTR-05, CTR-06, CTR-07, CTR-08, CTR-09, CTR-12"
                        "Origen" "ADR-002, ADR-004"
                    }
                }

                adaptadorPostgres = component "Adaptador PostgreSQL del libro" "Implementa el puerto del libro sobre PostgreSQL con el rol de la aplicación, una transacción por unidad de trabajo." "psycopg, adapters/postgres_ledger.py" {
                    tags "Adaptador"
                    properties {
                        "Identificador" "CMP-10"
                        "Contratos" "CTR-05, CTR-12"
                        "Origen" "ADR-001, ADR-004, EV-01, EV-02, EV-12"
                    }
                }

                adaptadorNotificador = component "Adaptador del notificador" "Implementa el puerto del notificador. Reproduce el fallo del canal cuando se configura." "Python, adapters/simulated_notifier.py" {
                    tags "Adaptador"
                    properties {
                        "Identificador" "CMP-11"
                        "Contratos" "CTR-10"
                        "Origen" "RES-03, RES-05, ADR-002, EC-04"
                    }
                }

                composicion = component "Composición" "Elige qué adaptador llena cada puerto a partir de la configuración y siembra los datos de la demostración." "Python, bootstrap.py, main.py, seed.py" {
                    properties {
                        "Identificador" "CMP-12"
                        "Origen" "RES-02, ADR-001"
                    }
                }

                migrador = component "Migrador" "Aplica el esquema del libro y sus privilegios con el rol propietario. No participa en las peticiones." "psycopg, migrate.py" {
                    tags "Soporte"
                    properties {
                        "Identificador" "CMP-13"
                        "Origen" "ADR-001, RA-01"
                    }
                }
            }

            baseDatos = container "Base de datos" "Conserva el libro mayor de solo inserción. En la Entrega 3 los demás datos del recorrido siguen en memoria (HV-07)." "PostgreSQL 17 local" {
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

        cobrador -> sistema.api "Solicita y confirma desembolsos por la API (Entrega 3)" "HTTP/JSON local"
        cobrador -> sistema.web "Opera desembolsos, pagos y cierre de caja (Entrega 4)" "HTTP local"
        administrador -> sistema.api "Aprueba o rechaza desembolsos por la API (Entrega 3)" "HTTP/JSON local"
        administrador -> sistema.web "Aprueba desembolsos y consulta caja y descuadres (Entrega 4)" "HTTP local"
        socio -> sistema.web "Consulta reportes en solo lectura" "HTTPS"
        sistema.movil -> sistema.api "Envía operaciones por lote con identificador único y descarga cambios por cursor" "HTTPS/JSON"
        sistema.web -> sistema.api "Realiza operaciones y consultas" "HTTP/JSON local, REST con OpenAPI"
        sistema.api -> sistema.baseDatos "Inserta y lee asientos con un rol que no puede modificarlos" "SQL local"
        sistema.api -> sistema.almacenObjetos "Emite URL prefirmadas para subir y descargar fotos y registra su hash" "HTTPS"
        sistema.api -> notificador "Envía el código de confirmación y los comprobantes" "Llamada local a través de un puerto"
        sistema.api -> ses "Envía alertas por correo" "HTTPS"
        sistema.api -> fcm "Envía avisos push" "HTTPS"
        sistema.api -> telegram "Envía reportes y alertas" "HTTPS"
        sistema.api -> sentry "Envía errores sin datos personales" "HTTPS"

        // -------------------------------------------------------------
        // Relaciones entre componentes de CON-03 (Entrega 3)
        // -------------------------------------------------------------
        // Se declaran después de las relaciones entre contenedores: así las
        // relaciones implícitas no duplican las que ya existen. Las flechas
        // hacia un adaptador son de ejecución y atraviesan el puerto indicado.
        // La dependencia de código va al revés: el adaptador importa el puerto.

        cobrador -> sistema.api.entradaHttp "Solicita y confirma desembolsos" "HTTP/JSON local, CTR-01"
        administrador -> sistema.api.entradaHttp "Aprueba, rechaza, concede excepciones, despacha avisos y consulta el libro" "HTTP/JSON local, CTR-01"

        sistema.api.entradaHttp -> sistema.api.casosUso "Invoca casos de uso y consultas" "CTR-02"
        sistema.api.entradaHttp -> sistema.api.avisos "Invoca el despachador y lee el estado de los avisos" "CTR-03"
        sistema.api.entradaHttp -> sistema.api.identidadCatalogos "Resuelve el actor de la cabecera X-Actor-Id" "Llamada directa"

        sistema.api.casosUso -> sistema.api.dominioDesembolso "Delega transiciones, RN-03 y RN-06" "Llamada directa"
        sistema.api.casosUso -> sistema.api.prestamos "Aplica RN-05 y origina el préstamo" "Llamada directa"
        sistema.api.casosUso -> sistema.api.libro "Pide el asiento del desembolso o del intento caducado" "Llamada directa"
        sistema.api.casosUso -> sistema.api.identidadCatalogos "Resuelve cliente, ruta y cobrador" "Llamada directa"
        sistema.api.casosUso -> sistema.api.persistenciaMemoria "Abre la unidad de trabajo, guarda estados y encola avisos" "CTR-04, CTR-06, CTR-08"

        sistema.api.dominioDesembolso -> sistema.api.prestamos "Usa las condiciones del préstamo" "Llamada directa"
        sistema.api.dominioDesembolso -> sistema.api.identidadCatalogos "Recibe cliente, ruta y actor" "Llamada directa"
        sistema.api.prestamos -> sistema.api.identidadCatalogos "Comprueba el rol de quien concede la excepción" "Llamada directa"

        sistema.api.libro -> sistema.api.caja "Descuenta la caja al asentar" "Llamada directa"
        sistema.api.libro -> sistema.api.persistenciaMemoria "Localiza y guarda la caja; inserta asientos si no hay PostgreSQL configurado" "CTR-05, CTR-07"
        sistema.api.libro -> sistema.api.adaptadorPostgres "Inserta asientos cuando PostgreSQL está configurado" "CTR-05"

        sistema.api.avisos -> sistema.api.persistenciaMemoria "Lee y actualiza la bandeja de salida" "CTR-08, CTR-09"
        sistema.api.avisos -> sistema.api.adaptadorNotificador "Envía cada aviso pendiente" "CTR-10"

        sistema.api.persistenciaMemoria -> sistema.api.adaptadorPostgres "Confirma o revierte la sesión del libro con la unidad de trabajo" "CTR-12"

        sistema.api.composicion -> sistema.api.entradaHttp "Crea la aplicación y le entrega el contenedor" "Llamada directa"
        sistema.api.composicion -> sistema.api.casosUso "Inyecta el contexto de los casos de uso" "Llamada directa"
        sistema.api.composicion -> sistema.api.avisos "Inyecta unidad de trabajo, notificador y reloj" "Llamada directa"
        sistema.api.composicion -> sistema.api.persistenciaMemoria "Crea el almacén sembrado y la unidad de trabajo" "Llamada directa"
        sistema.api.composicion -> sistema.api.adaptadorPostgres "Crea la sesión del libro si existe ROYEXA_LEDGER_URL" "Llamada directa"
        sistema.api.composicion -> sistema.api.adaptadorNotificador "Crea el notificador simulado" "Llamada directa"

        sistema.api.adaptadorPostgres -> sistema.baseDatos "Inserta y lee asientos con el rol royexa_app" "SQL local"
        sistema.api.migrador -> sistema.baseDatos "Aplica migraciones con el rol royexa_migrator" "SQL local"
        sistema.api.adaptadorNotificador -> notificador "Registra el código de confirmación y el comprobante" "Llamada local a través de un puerto"
    }

    views {
        // =============================================================
        // C4 NIVEL 1: CONTEXTO
        // =============================================================

        systemContext sistema "c4-contexto" "Diagrama C4 de Contexto de ROYEXA." {
            include *
            include clienteFinal
            exclude "element.tag==Diferido"
            autoLayout lr
        }

        // =============================================================
        // C4 NIVEL 2: CONTENEDORES
        // =============================================================

        container sistema "c4-contenedores" "Diagrama C4 de Contenedores de ROYEXA." {
            include *
            include clienteFinal
            exclude "element.tag==Diferido"
            autoLayout tb
        }

        // =============================================================
        // C4 NIVEL 3: COMPONENTES DE CON-03 (Entrega 3)
        // =============================================================

        component sistema.api "c4-componentes" "Componentes de CON-03 que participan en el recorrido de desembolso, UC-01 a UC-05." {
            include *
            include clienteFinal
            exclude "element.tag==Diferido"
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

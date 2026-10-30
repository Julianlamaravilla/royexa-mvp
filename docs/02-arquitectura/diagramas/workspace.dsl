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
            }

            baseDatos = container "Base de datos" "Conserva el libro mayor de solo inserción, préstamos, cajas y la bandeja de salida de eventos." "PostgreSQL 17 local" {
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
        sistema.api -> sistema.baseDatos "Lee y escribe el dominio; inserta asientos con un rol que no puede modificarlos" "SQL local"
        sistema.api -> sistema.almacenObjetos "Emite URL prefirmadas para subir y descargar fotos y registra su hash" "HTTPS"
        sistema.api -> notificador "Envía el código de confirmación y los comprobantes" "Llamada local a través de un puerto"
        sistema.api -> ses "Envía alertas por correo" "HTTPS"
        sistema.api -> fcm "Envía avisos push" "HTTPS"
        sistema.api -> telegram "Envía reportes y alertas" "HTTPS"
        sistema.api -> sentry "Envía errores sin datos personales" "HTTPS"
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
        }
    }

    configuration {
        scope softwaresystem
    }
}

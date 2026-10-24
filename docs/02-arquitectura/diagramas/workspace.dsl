workspace "ROYEXA" "Arquitectura candidata de la Entrega 2" {

    !identifiers hierarchical

    model {
        // =============================================================
        // 1. PERSONAS
        // =============================================================
        // Roles del sistema. Se relacionan con los INT-XX de la Entrega 1.
        // El cliente final (INT-03) no aparece: en el estado actual del
        // producto (TRACKEA, v1) no opera el sistema ni recibe mensajería
        // (ver DIV-01 en arquitectura.md, sección 7.1).

        cobrador = person "Cobrador" "Recorre su ruta de lunes a sábado, registra cobros y no pagos aunque no haya señal, y cierra su caja del día." {
            properties {
                "Identificador" "INT-01"
            }
        }

        administrador = person "Administrador" "Aprueba ventas, llaves y gastos antes de que salga el dinero, y verifica cada cierre de caja. Puede ser principal o secundario." {
            properties {
                "Identificador" "INT-02"
            }
        }

        socio = person "Socio" "Dueño o inversionista de la financiera. Consulta reportes en solo lectura desde el hito 2." {
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

            movil = container "Aplicación móvil del cobrador" "Registra cobros, no pagos, promesas y gastos sin señal en una cola local cifrada; sincroniza al volver la señal; muestra el saldo y la caja del día." "React Native + TypeScript, SQLCipher (Android 10+)" {
                properties {
                    "Identificador" "CON-01"
                    "Decisiones" "AD-03, ADR-003"
                }
            }

            web = container "Aplicación web de administración" "Permite a administradores y socios aprobar ventas, llaves y gastos, gestionar clientes y consultar caja, descuadres y tablero." "React 19 + Vite, SPA estática" {
                properties {
                    "Identificador" "CON-02"
                    "Decisiones" "AD-02, ADR-002"
                }
            }

            api = container "API del servidor" "Monolito modular que valida las reglas de negocio, calcula el dinero, escribe el libro mayor y publica eventos para alertas y tablero." "Python 3.14, FastAPI, SQLAlchemy 2 asíncrono, ECS Fargate" {
                properties {
                    "Identificador" "CON-03"
                    "Decisiones" "AD-01, AD-02, AD-03, ADR-001, ADR-002, ADR-003"
                }
            }

            baseDatos = container "Base de datos" "Conserva el libro mayor de solo inserción, préstamos, cajas, operaciones de sincronización y la cola de eventos, con seguridad a nivel de fila por financiera." "PostgreSQL 17+ (RDS)" {
                tags "Database"
                properties {
                    "Identificador" "CON-04"
                    "Decisiones" "AD-01, AD-02, ADR-001, ADR-002"
                }
            }

            almacenObjetos = container "Almacén de fotos" "Guarda las fotos de documento, residencia, comercio y comprobantes de gasto, con verificación de hash." "Amazon S3" {
                tags "Database"
                properties {
                    "Identificador" "CON-05"
                    "Decisiones" "Pendiente (B4, B11)"
                }
            }
        }

        // =============================================================
        // 3. SISTEMAS EXTERNOS
        // =============================================================

        ses = softwareSystem "Amazon SES" "Entrega el correo de alertas a los administradores." {
            tags "Existing System"
            properties {
                "Identificador" "EXT-01"
                "Origen" "ASR-05, AD-02"
            }
        }

        fcm = softwareSystem "Firebase Cloud Messaging" "Entrega los avisos push al teléfono del cobrador y del administrador." {
            tags "Existing System"
            properties {
                "Identificador" "EXT-02"
                "Origen" "ASR-05, AD-02"
            }
        }

        telegram = softwareSystem "Telegram Bot API" "Entrega los reportes y alertas a administradores y socios (canal por confirmar con el cliente)." {
            tags "Existing System"
            properties {
                "Identificador" "EXT-03"
                "Origen" "ASR-05, AD-02, RES-03"
            }
        }

        sentry = softwareSystem "Servicio de captura de errores" "Recibe los errores del servidor sin datos personales ni cuerpos de petición." {
            tags "Existing System"
            properties {
                "Identificador" "EXT-04"
                "Origen" "EC-01, AD-02"
            }
        }

        // =============================================================
        // 4. RELACIONES DEL MODELO
        // =============================================================

        cobrador -> sistema "Registra cobros, no pagos y gastos, y cierra su caja"
        administrador -> sistema "Aprueba ventas, llaves y gastos, y verifica descuadres"
        socio -> sistema "Consulta reportes en solo lectura"
        sistema -> ses "Envía alertas por correo" "HTTPS"
        sistema -> fcm "Envía avisos push" "HTTPS"
        sistema -> telegram "Envía reportes y alertas" "HTTPS"
        sistema -> sentry "Envía errores sin datos personales" "HTTPS"

        cobrador -> sistema.movil "Registra cobros, no pagos y gastos, y cierra su caja"
        administrador -> sistema.web "Aprueba ventas, llaves y gastos, y consulta caja y descuadres" "HTTPS"
        socio -> sistema.web "Consulta reportes en solo lectura" "HTTPS"
        sistema.movil -> sistema.api "Envía operaciones por lote con identificador único y descarga cambios por cursor" "HTTPS/JSON, REST con OpenAPI, TLS 1.3"
        sistema.web -> sistema.api "Realiza operaciones y consultas de administración" "HTTPS/JSON, REST con OpenAPI, TLS 1.3"
        sistema.api -> sistema.baseDatos "Lee y escribe el dominio; inserta asientos con un rol que no puede modificarlos" "SQL sobre TLS"
        sistema.api -> sistema.almacenObjetos "Emite URL prefirmadas para subir y descargar fotos y registra su hash" "HTTPS"
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
            include cobrador
            include administrador
            include socio
            include sistema
            include ses
            include fcm
            include telegram
            include sentry
            autoLayout lr
        }

        // =============================================================
        // C4 NIVEL 2: CONTENEDORES
        // =============================================================

        container sistema "c4-contenedores" "Diagrama C4 de Contenedores de ROYEXA." {
            include cobrador
            include administrador
            include socio
            include sistema.movil
            include sistema.web
            include sistema.api
            include sistema.baseDatos
            include sistema.almacenObjetos
            include ses
            include fcm
            include telegram
            include sentry
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

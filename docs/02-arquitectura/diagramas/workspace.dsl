workspace "[Nombre del proyecto]" "Arquitectura candidata de la Entrega 2" {

    !identifiers hierarchical

    model {
        // =============================================================
        // 1. PERSONAS
        // =============================================================
        // Use personas o roles, no individuos concretos.
        // Relacione cada persona con los INT-XX de la Entrega 1 mediante
        // la descripción o una propiedad.

        usuarioPrincipal = person "[Rol principal]" "[Descripción del rol y su objetivo principal]." {
            properties {
                "Identificador" "INT-01"
            }
        }

        usuarioSecundario = person "[Rol secundario]" "[Descripción del rol y su objetivo principal]." {
            properties {
                "Identificador" "INT-02"
            }
        }

        // =============================================================
        // 2. SISTEMA OBJETO DE ESTUDIO
        // =============================================================

        sistema = softwareSystem "[Nombre del sistema]" "[Propósito del sistema expresado como resultado de negocio]." {

            // =========================================================
            // 2.1 CONTENEDORES
            // =========================================================
            // Un contenedor es una aplicación o almacenamiento que debe
            // ejecutarse o desplegarse para que el sistema funcione.
            // No modele capas, paquetes, namespaces o clases como contenedores.

            aplicacion = container "[Aplicación principal]" "[Responsabilidad principal y recorrido que coordina]." "[Tecnología candidata o Por definir]" {
                properties {
                    "Identificador" "CON-01"
                    "Decisiones" "AD-01, ADR-001"
                }
            }

            baseDatos = container "[Almacenamiento principal]" "[Información que conserva y responsabilidad de persistencia]." "[Tecnología candidata o Por definir]" {
                tags "Database"
                properties {
                    "Identificador" "CON-02"
                    "Decisiones" "AD-02, ADR-002"
                }
            }

            // Agregue otros contenedores solo cuando exista una necesidad
            // arquitectónica justificada. Elimine este ejemplo si no aplica.
            // trabajador = container "[Proceso en segundo plano]" "[Responsabilidad]." "[Tecnología]" {
            //     properties {
            //         "Identificador" "CON-03"
            //         "Decisiones" "AD-XX, ADR-XXX"
            //     }
            // }
        }

        // =============================================================
        // 3. SISTEMAS EXTERNOS
        // =============================================================
        // Incluya solo sistemas fuera del límite de la solución con los
        // que exista una interacción relevante.

        sistemaExterno = softwareSystem "[Sistema externo]" "[Servicio que presta o información que intercambia]." {
            tags "Existing System"
            properties {
                "Identificador" "EXT-01"
                "Origen" "RES-XX, ASR-XX"
            }
        }

        // =============================================================
        // 4. RELACIONES DEL MODELO
        // =============================================================
        // Toda relación debe indicar su propósito. Evite rótulos vagos como
        // "usa" cuando sea posible describir la interacción concreta.

        usuarioPrincipal -> sistema "[Inicia el flujo o consulta un resultado]"
        usuarioSecundario -> sistema "[Administra, consulta o participa en el proceso]"
        sistema -> sistemaExterno "[Solicita o intercambia información]" "[HTTPS/JSON u otro mecanismo, si está justificado]"

        usuarioPrincipal -> sistema.aplicacion "[Envía una solicitud y recibe el resultado]" "[HTTPS/JSON u otro mecanismo]"
        usuarioSecundario -> sistema.aplicacion "[Realiza una operación o consulta]" "[HTTPS/JSON u otro mecanismo]"
        sistema.aplicacion -> sistema.baseDatos "[Lee y escribe información del dominio]" "[Protocolo o mecanismo]"
        sistema.aplicacion -> sistemaExterno "[Solicita o intercambia información]" "[HTTPS/JSON u otro mecanismo]"
    }

    views {
        // =============================================================
        // C4 NIVEL 1: CONTEXTO
        // =============================================================
        // Debe mostrar el sistema como una sola unidad, las personas y los
        // sistemas externos. No incluya contenedores internos en esta vista.

        systemContext sistema "c4-contexto" "Diagrama C4 de Contexto del sistema." {
            include usuarioPrincipal
            include usuarioSecundario
            include sistema
            include sistemaExterno
            autoLayout lr
        }

        // =============================================================
        // C4 NIVEL 2: CONTENEDORES
        // =============================================================
        // Debe mostrar los contenedores internos, las personas y los sistemas
        // externos relevantes para comprender las interacciones.

        container sistema "c4-contenedores" "Diagrama C4 de Contenedores del sistema." {
            include usuarioPrincipal
            include usuarioSecundario
            include sistema.aplicacion
            include sistema.baseDatos
            include sistemaExterno
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
        }
    }

    configuration {
        scope softwaresystem
    }
}

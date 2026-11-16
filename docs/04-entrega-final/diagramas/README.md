# Diagramas finales

No creen un modelo C4 nuevo en esta carpeta. Actualicen la fuente existente:

```text
docs/02-arquitectura/diagramas/workspace.dsl
```

Conserven allí o exporten en una ruta estable:

- `c4-contexto.svg`;
- `c4-contenedores.svg`;
- `c4-componentes.svg`.

Los diagramas de secuencia vigentes pueden mantenerse en `docs/03-diseno-vertical/diagramas/` y actualizarse si el flujo cambió. Todas las exportaciones deben proceder de fuentes reproducibles y coincidir con el código final.

## Vistas vigentes de ROYEXA (Entrega 4)

Esta carpeta no contiene copias: las vistas viven en una ruta estable junto a su fuente, para que no existan dos versiones.

| Vista | Archivo exportado | Fuente | Clave en la fuente |
|---|---|---|---|
| C4 de Contexto, nivel 1 | [`docs/02-arquitectura/diagramas/c4-contexto.svg`](../../02-arquitectura/diagramas/c4-contexto.svg) | [`docs/02-arquitectura/diagramas/workspace.dsl`](../../02-arquitectura/diagramas/workspace.dsl) | `c4-contexto` |
| C4 de Contenedores, nivel 2 | [`docs/02-arquitectura/diagramas/c4-contenedores.svg`](../../02-arquitectura/diagramas/c4-contenedores.svg) | [`docs/02-arquitectura/diagramas/workspace.dsl`](../../02-arquitectura/diagramas/workspace.dsl) | `c4-contenedores` |
| C4 de Componentes de `CON-03`, nivel 3 | [`docs/03-diseno-vertical/diagramas/c4-componentes.svg`](../../03-diseno-vertical/diagramas/c4-componentes.svg) | [`docs/02-arquitectura/diagramas/workspace.dsl`](../../02-arquitectura/diagramas/workspace.dsl) | `c4-componentes` |
| Secuencia del escenario principal (UC-01, UC-02, UC-05, UC-03) | [`docs/03-diseno-vertical/diagramas/secuencia-vertical.svg`](../../03-diseno-vertical/diagramas/secuencia-vertical.svg) | [`docs/03-diseno-vertical/diagramas/secuencia-vertical.puml`](../../03-diseno-vertical/diagramas/secuencia-vertical.puml) | No aplica |
| Secuencia de los escenarios alternativos y de error | [`docs/03-diseno-vertical/diagramas/secuencia-alternativa.svg`](../../03-diseno-vertical/diagramas/secuencia-alternativa.svg) | [`docs/03-diseno-vertical/diagramas/secuencia-alternativa.puml`](../../03-diseno-vertical/diagramas/secuencia-alternativa.puml) | No aplica |

Lo que muestran las vistas en su estado final:

- **Contexto:** ROYEXA como una unidad, con `INT-01` Cobrador, `INT-02` Administrador, `INT-03` Cliente final y el notificador simulado `EXT-05`.
- **Contenedores:** `CON-03` (servidor de aplicación: API JSON y web renderizada en el mismo proceso) y `CON-04` (PostgreSQL 17 con todo el estado). `CON-02` queda en el modelo como registro histórico y `CON-01` y `CON-05` como diferidos, fuera de las vistas.
- **Componentes de `CON-03`:** `CMP-01` a `CMP-18`, incluidos los añadidos en la Entrega 4: web (`CMP-14`), clientes (`CMP-15`), cierre, ajustes y descuadres (`CMP-16`), despacho en segundo plano (`CMP-17`) y fijación de contraseñas (`CMP-18`).

## Cómo regenerarlas

Requiere Docker. Desde la raíz del repositorio:

```bash
bash docs/03-diseno-vertical/diagramas/exportar-diagramas.sh
```

El script valida `workspace.dsl` con Structurizr CLI (`structurizr/cli:2024.03.03`), lo exporta a C4-PlantUML y genera los cinco SVG con PlantUML (`plantuml/plantuml:1.2024.8`), sobrescribiéndolos en las rutas de la tabla. La última exportación (2026-11-16, commit `12c2f1e`) terminó con código de salida 0; `c4-contexto.svg` no cambió en ese commit porque la vista de contexto ya coincidía con el modelo. La validación comprueba sintaxis y referencias del modelo; la correspondencia con el código se revisó por lectura y la sostienen las pruebas citadas en [`../trazabilidad-final.md`](../trazabilidad-final.md).

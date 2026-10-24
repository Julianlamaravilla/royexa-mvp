# Diagramas de la Entrega 3

## C4 de Componentes

La vista de componentes debe añadirse a:

```text
docs/02-arquitectura/diagramas/workspace.dsl
```

No cree un segundo modelo C4 independiente. Exporte la vista como:

```text
docs/03-diseno-vertical/diagramas/c4-componentes.svg
```

Ejemplo orientativo de la estructura que debe integrarse y adaptar, no copiar literalmente:

```dsl
container aplicacion "[Aplicación]" {
    entrada = component "[Entrada]" "Recibe y traduce solicitudes." "[Tecnología]" {
        properties { "Identificador" "CMP-01" }
    }
    casoUso = component "[Caso de uso]" "Coordina UC-01." "[Tecnología]" {
        properties { "Identificador" "CMP-02" }
    }
    dominio = component "[Dominio]" "Protege RN-XX." "[Tecnología]" {
        properties { "Identificador" "CMP-03" }
    }
    adaptador = component "[Adaptador]" "Implementa CTR-XX." "[Tecnología]" {
        properties { "Identificador" "CMP-04" }
    }
}

component aplicacion "c4-componentes" "Componentes del recorrido UC-01." {
    include *
    autoLayout lr
}
```

Ajuste la sintaxis al modelo real y valide el DSL antes de exportar.

## Diagramas de secuencia

- Conserve la fuente reproducible.
- Exporte los SVG al mismo directorio.
- No incluya llamadas triviales.
- Use notas o referencias para `UC-XX`, `RF-XX`, `CA-XX` y `RN-XX`.

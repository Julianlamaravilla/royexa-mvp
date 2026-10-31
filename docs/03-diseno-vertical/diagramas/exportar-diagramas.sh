#!/usr/bin/env bash
# Validates workspace.dsl and regenerates every SVG of Entregas 2 and 3. Needs Docker.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
C4_DIR="$ROOT/docs/02-arquitectura/diagramas"
DESIGN_DIR="$ROOT/docs/03-diseno-vertical/diagramas"
STRUCTURIZR=structurizr/cli:2024.03.03
PLANTUML=plantuml/plantuml:1.2024.8

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cp "$C4_DIR/workspace.dsl" "$DESIGN_DIR"/secuencia-*.puml "$WORK/"

docker run --rm -v "$WORK:/usr/local/structurizr" "$STRUCTURIZR" \
    validate -workspace workspace.dsl
docker run --rm -v "$WORK:/usr/local/structurizr" "$STRUCTURIZR" \
    export -workspace workspace.dsl -format plantuml/c4plantuml -output .
docker run --rm -v "$WORK:/data" -w /data "$PLANTUML" -tsvg -failfast2 \
    structurizr-c4-contexto.puml structurizr-c4-contenedores.puml \
    structurizr-c4-componentes.puml secuencia-vertical.puml secuencia-alternativa.puml

mv "$WORK/structurizr-c4-contexto.svg" "$C4_DIR/c4-contexto.svg"
mv "$WORK/structurizr-c4-contenedores.svg" "$C4_DIR/c4-contenedores.svg"
mv "$WORK/structurizr-c4-componentes.svg" "$DESIGN_DIR/c4-componentes.svg"
mv "$WORK/secuencia-vertical.svg" "$WORK/secuencia-alternativa.svg" "$DESIGN_DIR/"

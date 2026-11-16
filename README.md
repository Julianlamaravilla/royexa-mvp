# ROYEXA

Sistema de registro de cobranza para financieras pequeñas que prestan cantidades reducidas y las cobran a diario, puerta a puerta.
Cada movimiento de dinero deja evidencia que puede verificar alguien distinto de quien lo registró.
El propósito es impedir el fraude interno y detectar los descuadres de caja el mismo día.

## Integrantes

- Julian Andres Restrepo

Grupo: 10

## Documentacion

- [docs/00-propuesta/propuesta.md](docs/00-propuesta/propuesta.md)
- [docs/01-requisitos/requisitos.md](docs/01-requisitos/requisitos.md)
- [docs/02-arquitectura/arquitectura.md](docs/02-arquitectura/arquitectura.md)
- [docs/02-arquitectura/trazabilidad-arquitectonica.md](docs/02-arquitectura/trazabilidad-arquitectonica.md)
- [docs/04-entrega-final/entrega-final.md](docs/04-entrega-final/entrega-final.md)
- [backend/README.md](backend/README.md)

## Estado actual

- Entrega actual: Entrega 4 (entrega final), rama `entrega-4-final`.
- Estado: producto final de la demostración local de costo cero. Informe final, demostración guiada y trazabilidad en [docs/04-entrega-final/entrega-final.md](docs/04-entrega-final/entrega-final.md). Instrucciones completas del backend en [backend/README.md](backend/README.md).

## Cómo ejecutar

Requisitos: `uv` 0.11 y Docker con Compose. Desde la raíz del repositorio:

```bash
docker compose up -d --wait postgres
cd backend
uv sync
uv run python -m royexa.migrate
ROYEXA_LEDGER_URL=postgresql://royexa_app:royexa_app@localhost:55432/royexa \
  uv run uvicorn royexa.main:app --port 8000
```

Abra <http://localhost:8000/web/> (cobrador) o <http://localhost:8000/web/admin> (administrador) con un usuario de demostración, por ejemplo `cobrador-1` / `demo-cobrador-1-royexa`. Las pruebas se ejecutan desde `backend/` con `uv run pytest -m ""`.

## Instruccion oficial de entrega

Elaboren en pareja la ficha de propuesta del proyecto utilizando la plantilla ubicada en:

[docs/00-propuesta/propuesta.md](docs/00-propuesta/propuesta.md)

Actualicen el nombre, la descripcion y los integrantes en este archivo:

README.md

Realicen el trabajo en una rama diferente de main y, cuando la propuesta este lista, creen un pull request hacia main con el titulo:

Entrega 0: propuesta de [nombre del proyecto]

**No realicen el merge del pull request.** El docente revisara la propuesta y registrara sus observaciones directamente en el PR. Las correcciones deben realizarse en la misma rama y el mismo pull request. El PR se integra a main unicamente despues de recibir la aprobacion del docente.

## Advertencia para Entrega 0

En la Entrega 0 no deben:

- Implementar codigo.
- Crear diagramas de arquitectura.
- Seleccionar patrones.
- Definir una estructura de capas.
- Crear ADR.
- Configurar CI/CD.
- Crear un Dockerfile.
- Elegir microservicios, arquitectura hexagonal u otro estilo como decision definitiva.

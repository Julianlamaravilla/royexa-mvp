# ROYEXA — Backend

Recorrido vertical de la Entrega 3: desembolso de un préstamo por API. El diseño está en [`../docs/03-diseno-vertical/diseno-y-vertical.md`](../docs/03-diseno-vertical/diseno-y-vertical.md).

## Requisitos

- [`uv`](https://docs.astral.sh/uv/) 0.11. Descarga Python 3.14 si no está instalado.
- Docker con Compose, solo para las pruebas y la ejecución con PostgreSQL.

## Desde un clon limpio

```bash
git clone <url-del-repositorio> repogrp10
cd repogrp10
git switch entrega-3-linea-base
cd backend
uv sync
```

## Pruebas

Desde `backend/`. El comando por defecto no necesita Docker:

```bash
uv run pytest                # 25 pruebas, sin PostgreSQL
uv run pytest tests/vertical # solo las 21 pruebas del recorrido
```

Las pruebas de privilegios del libro necesitan PostgreSQL. Levántelo desde la raíz del repositorio:

```bash
docker compose up -d --wait postgres
```

Después, desde `backend/`:

```bash
uv run pytest -m postgres    # las 18 pruebas de PR-07
uv run pytest -m ""          # las 43 pruebas
```

Las pruebas aplican la migración por sí mismas.

## Ejecutar la API

Con el libro en PostgreSQL, desde `backend/`:

```bash
uv run python -m royexa.migrate
ROYEXA_LEDGER_URL=postgresql://royexa_app:royexa_app@localhost:55432/royexa \
  uv run uvicorn royexa.main:app --port 8000
```

Sin PostgreSQL, el libro queda en memoria:

```bash
uv run uvicorn royexa.main:app --port 8000
```

La documentación OpenAPI queda en <http://localhost:8000/docs>. El recorrido completo con `curl` está en la sección 7.6 del documento de diseño.

| Variable | Valor por defecto | Efecto |
|---|---|---|
| `ROYEXA_LEDGER_URL` | Sin definir: libro en memoria | Conexión del rol de la aplicación |
| `ROYEXA_CODE_TTL_MINUTES` | `60` | Vigencia del código de confirmación |
| `ROYEXA_NOTIFIER_FAILING` | Sin definir | Con `1`, el notificador simulado falla |
| `ROYEXA_MIGRATOR_URL` | Rol `royexa_migrator` en `localhost:55432` | Conexión del rol propietario |

Las credenciales de `docker-compose.yml` y de la migración son valores de demostración local.

## Limitaciones

Solo el libro se guarda en PostgreSQL. Desembolsos, préstamos, cajas y avisos están en memoria y se pierden al reiniciar el servidor, así que después de un reinicio el saldo sembrado no coincide con el libro. La lista completa está en la sección 10 del documento de diseño.

## Al terminar

Desde la raíz del repositorio:

```bash
docker compose down
```

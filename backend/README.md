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
uv run pytest                # 52 pruebas, sin PostgreSQL
uv run pytest tests/vertical # solo las 48 pruebas del recorrido
```

Las pruebas de privilegios del libro necesitan PostgreSQL. Levántelo desde la raíz del repositorio:

```bash
docker compose up -d --wait postgres
```

Después, desde `backend/`:

```bash
uv run pytest -m postgres    # las 118 pruebas con PostgreSQL
uv run pytest -m ""          # las 215 pruebas
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

Con `ROYEXA_LEDGER_URL`, todo el estado se guarda en PostgreSQL y sobrevive a un reinicio: libro, cajas, clientes, préstamos con su calendario, excepciones de renovación, avisos y desembolsos. Sin esa variable todo vive en memoria y se pierde al apagar el servidor. Los usuarios y las rutas siguen sembrados en código; los clientes se dan de alta con `POST /v1/clients` (solo el administrador) y se leen con `GET /v1/clients` y `GET /v1/clients/{id}`. Los préstamos, con su calendario de cuotas, se leen con `GET /v1/loans/{id}` y `GET /v1/clients/{id}/loans`; nacen al confirmar un desembolso (RN-03). El cobrador de la ruta registra un pago con `POST /v1/loans/{id}/payments` (efectivo o transferencia; se imputa a las cuotas más antiguas y no puede exceder el saldo) y se leen con `GET /v1/loans/{id}/payments`. El contador `remaining_installments` es exacto: `19.5`, o una fracción como `113/6` cuando no tiene decimal finito. Cada pago deja su asiento `PAGO` en el libro; solo el efectivo suma a la caja. Si el cliente no paga, el cobrador lo registra con `POST /v1/loans/{id}/non-payments` (motivo y fecha de compromiso posterior al día del registro; no cambia el saldo) y se lee con `GET /v1/loans/{id}/non-payments`. `GET /v1/routes/{id}/pending-visits?date=AAAA-MM-DD` lista los clientes pendientes de visita: de lunes a sábado, todo cliente de la ruta con un préstamo activo sin pago ni no pago ese día; el domingo no hay pendientes. Lo lee el cobrador de la ruta o un administrador. El día se cuenta en UTC. La lista completa está en la sección 10 del documento de diseño.

Cada unidad de trabajo usa el aislamiento `REPEATABLE READ`: lee una copia consistente y, si otra transacción cambió antes la misma fila, pierde con un conflicto de escritura y reintenta (ADR-004).

## Al terminar

Desde la raíz del repositorio:

```bash
docker compose down
```

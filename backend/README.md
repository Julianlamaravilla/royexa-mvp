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
uv run pytest                # 210 pruebas, sin PostgreSQL
```

Las pruebas de privilegios del libro necesitan PostgreSQL. Levántelo desde la raíz del repositorio:

```bash
docker compose up -d --wait postgres
```

Después, desde `backend/`:

```bash
uv run pytest -m postgres    # las 238 pruebas con PostgreSQL (1 se omite a propósito)
uv run pytest -m ""          # las 448 pruebas
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
| `ROYEXA_TIMEZONE` | `UTC` | Zona horaria del piloto (por ejemplo `America/Bogota`): fija el día de la caja y de los pendientes de visita. Un nombre desconocido impide arrancar |
| `ROYEXA_REQUIRE_CHANGED_PASSWORDS` | Sin definir | Con `1`, no se siembra ninguna contraseña de demostración y el servidor se niega a arrancar si queda alguna, o si no hay base de datos. Se aprovisionan con `python -m royexa.set_password` |
| `ROYEXA_SESSION_HOURS` | `12` | Duración de una sesión desde el inicio de sesión, sin renovación |
| `ROYEXA_SCRYPT_N` | `16384` | Coste del hash de contraseñas. Solo las pruebas lo bajan; el hash guarda su coste, así que cambiarlo no invalida los existentes |
| `ROYEXA_MIGRATOR_URL` | Rol `royexa_migrator` en `localhost:55432` | Conexión del rol propietario |

Las credenciales de `docker-compose.yml` y de la migración son valores de demostración local.

## Sesiones y contraseñas

La cabecera `X-Actor-Id` ya no identifica a nadie. Se inicia sesión con usuario y contraseña y se usa el token que devuelve:

```bash
curl -s -X POST localhost:8000/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"user_id": "admin-1", "password": "demo-admin-1-royexa"}'
curl localhost:8000/v1/clients -H "Authorization: Bearer $TOKEN"
curl -X POST localhost:8000/v1/auth/logout -H "Authorization: Bearer $TOKEN"
```

- El token es opaco y aleatorio (256 bits) y solo se guarda su huella SHA-256. Viaja en `Authorization: Bearer`; el mismo token se entrega también en la cookie `royexa_session` (`HttpOnly`, `SameSite=Lax`, y `Secure` bajo HTTPS) para las páginas del servidor. Si hay cabecera `Authorization` manda ella y nunca se mezcla con la cookie.
- Dura 12 horas sin renovación, sobrevive a un reinicio, un usuario puede tener varias sesiones y `POST /v1/auth/logout` revoca solo la que se usa. Sin sesión válida (ausente, inválida, vencida o revocada) el API responde 401 `sesion-requerida`.
- Usuario inexistente y contraseña errónea dan la misma respuesta 401 `credenciales-invalidas`.
- Las contraseñas se guardan con `scrypt` y sal propia; nunca en claro. Los cuatro usuarios sembrados traen contraseñas de **demostración**, válidas solo para desarrollo y pruebas: `demo-<usuario>-royexa` (por ejemplo `demo-cobrador-1-royexa`). 
- **Cambio de contraseña:** `POST /v1/auth/password` con la actual y la nueva (de 12 a 256 caracteres y distinta de la actual). Termina las demás sesiones de ese usuario y deja la que se usa. Una contraseña actual errónea responde 403 y cuenta como un intento fallido.
- **Bloqueo:** 5 intentos fallidos seguidos bloquean al usuario 15 minutos, también para la contraseña correcta, con la misma respuesta 401 que un usuario inexistente o una contraseña errónea (no se revela cuál fue). El bloqueo no cierra las sesiones que ya tenga abiertas. Un usuario bloqueado por error espera los 15 minutos o recibe una contraseña nueva con `set_password`. Riesgo aceptado: un tercero puede bloquear temporalmente a un cobrador conociendo su usuario.
- **Despliegue:** con `ROYEXA_REQUIRE_CHANGED_PASSWORDS=1` el servidor no arranca mientras algún usuario conserve la contraseña de demostración. Como tampoco se siembran, las reales se ponen antes de arrancar:

```bash
ROYEXA_LEDGER_URL=postgresql://royexa_app:...@host/royexa python -m royexa.set_password admin-1
```

## Limitaciones

Con `ROYEXA_LEDGER_URL`, todo el estado se guarda en PostgreSQL y sobrevive a un reinicio: libro, cajas, clientes, préstamos con su calendario, excepciones de renovación, avisos y desembolsos. Sin esa variable todo vive en memoria y se pierde al apagar el servidor. Los usuarios y las rutas siguen sembrados en código, sin registro ni recuperación de cuentas; los clientes se dan de alta con `POST /v1/clients` (solo el administrador) y se leen con `GET /v1/clients` y `GET /v1/clients/{id}`. Los préstamos, con su calendario de cuotas, se leen con `GET /v1/loans/{id}` y `GET /v1/clients/{id}/loans`; nacen al confirmar un desembolso (RN-03). El cobrador de la ruta registra un pago con `POST /v1/loans/{id}/payments` (efectivo o transferencia; se imputa a las cuotas más antiguas y no puede exceder el saldo) y se leen con `GET /v1/loans/{id}/payments`. El contador `remaining_installments` es exacto: `19.5`, o una fracción como `113/6` cuando no tiene decimal finito. Cada cobrador tiene una caja por día (`GET /v1/cash-boxes/{cobrador}?date=`): se abre sola con el primer movimiento de cada día de cobranza (lunes a sábado) con el fondo del cobrador como saldo inicial; el domingo no hay caja y pagos y confirmaciones de desembolso se rechazan. La caja de ayer no hace falta cerrarla para abrir la de hoy. El cobrador cierra la de hoy con `POST /v1/cash-boxes/{cobrador}/close` indicando el efectivo entregado: solo sin pendientes de visita (409 `visitas-pendientes`), una sola vez y sin vuelta atrás; tras el cierre la caja rechaza pagos y desembolsos (409 `caja-cerrada`). El cierre guarda el efectivo esperado (cobros en efectivo del día menos desembolsos confirmados; las transferencias no entran), lo entregado y el descuadre con signo (`entregado − esperado`; cero no es descuadre). El administrador los consulta con `GET /v1/cash-closes?collector_id=&date=`. Un error se corrige sin tocar el asiento original: el administrador registra un ajuste con `POST /v1/ledger/{asiento}/adjustments` (importe con signo distinto de cero, motivo obligatorio). Queda como un asiento `AJUSTE` nuevo que nombra al original, en la caja del cobrador dueño del original del día en que se registra: una caja cerrada se corrige al día siguiente y ni ella ni su cierre cambian. Suma o resta efectivo como cualquier asiento y entra en el efectivo esperado del día en que cae. Los tres paneles del día de la caja (`GET /v1/cash-boxes/{cobrador}/panels`, para el cobrador o un administrador, solo el día de hoy) son: pendientes (T3-P1), pagaron (con algún pago ese día, con efectivo y transferencia por separado y en total) y no pagaron (con no pago y sin pago ese día, con motivo y compromiso). Un cliente está en un panel como máximo. Cada pago deja su asiento `PAGO` en el libro; solo el efectivo suma a la caja. Cada pago también encola su comprobante (`COMPROBANTE_PAGO`) en la bandeja de salida, en la misma transacción, con el importe recibido, el saldo restante y la fecha del próximo vencimiento (vacía si el préstamo queda liquidado). El administrador lo envía con `POST /v1/notifications/dispatch` y consulta su estado con `GET /v1/notifications?payment_id=`; un fallo del canal deja el aviso pendiente y, al quinto intento, fallido. Si el cliente no paga, el cobrador lo registra con `POST /v1/loans/{id}/non-payments` (motivo y fecha de compromiso posterior al día del registro; no cambia el saldo) y se lee con `GET /v1/loans/{id}/non-payments`. `GET /v1/routes/{id}/pending-visits?date=AAAA-MM-DD` lista los clientes pendientes de visita: de lunes a sábado, todo cliente de la ruta con un préstamo activo sin pago ni no pago ese día; el domingo no hay pendientes. Lo lee el cobrador de la ruta o un administrador. El día se cuenta en UTC. La lista completa está en la sección 10 del documento de diseño.

Cada unidad de trabajo usa el aislamiento `REPEATABLE READ`: lee una copia consistente y, si otra transacción cambió antes la misma fila, pierde con un conflicto de escritura y reintenta (ADR-004).

## Al terminar

Desde la raíz del repositorio:

```bash
docker compose down
```

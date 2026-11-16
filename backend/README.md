# ROYEXA — Backend

Monolito modular en FastAPI (Python 3.14) para la cobranza diaria de microcréditos: desembolsos con doble control, pagos y no pagos, caja diaria con cierre y descuadres, ajustes sobre un libro de solo inserción y avisos al cliente por una bandeja de salida. El estado vive en PostgreSQL 17 o, sin base de datos, en memoria.

La entrega final, con la demostración guiada y la trazabilidad, está en [`../docs/04-entrega-final/entrega-final.md`](../docs/04-entrega-final/entrega-final.md).

## Requisitos

- [`uv`](https://docs.astral.sh/uv/) 0.11. Descarga Python 3.14 si no está instalado.
- Docker con Compose, para PostgreSQL. Sin Docker la aplicación corre en memoria y solo se ejecutan las pruebas que no usan base de datos.
- Chromium de Playwright, solo para las pruebas de navegador (se instala con `uv` más abajo).

## Desde un clon limpio

```bash
git clone <url-del-repositorio> repogrp10
cd repogrp10
git checkout entrega-4                   # etiqueta evaluable de la Entrega 4
docker compose up -d --wait postgres     # PostgreSQL 17 en localhost:55432
cd backend
uv sync                                  # dependencias, incluidas las de pruebas
uv run python -m royexa.migrate          # aplica las migraciones; imprime los archivos aplicados
```

La migración se conecta por defecto como el rol propietario `royexa_migrator` en `localhost:55432` (el de `docker-compose.yml`) y crea el rol de la aplicación `royexa_app`. Se puede repetir sin efecto.

## Configuración

No hay archivo `.env` ni secretos: la aplicación lee variables del proceso, no carga archivos `.env`, y todos los valores por defecto sirven para la demostración local. Las variables se pasan en la línea de comandos o se exportan en la sesión (los archivos `.env` están ignorados por git):

```bash
export ROYEXA_LEDGER_URL=postgresql://royexa_app:royexa_app@localhost:55432/royexa
export ROYEXA_TIMEZONE=America/Bogota
```

| Variable | Valor por defecto | Efecto |
|---|---|---|
| `ROYEXA_LEDGER_URL` | Sin definir: estado en memoria | Conexión del rol de la aplicación (`royexa_app`) |
| `ROYEXA_MIGRATOR_URL` | `postgresql://royexa_migrator:royexa_migrator@localhost:55432/royexa` | Conexión del rol propietario que usa `royexa.migrate` |
| `ROYEXA_APP_PASSWORD` | Sin definir: queda la contraseña de demostración `royexa_app` | Si se define (20 caracteres o más), `royexa.migrate` la pone al rol `royexa_app` |
| `ROYEXA_SEED` | `demo` | `demo` siembra usuarios, clientes, préstamos y contraseñas de demostración. `pilot` lee usuarios y rutas de `pilot/directory.json` y no siembra datos ni contraseñas |
| `ROYEXA_DIRECTORY_FILE` | `pilot/directory.json` | Archivo de usuarios y rutas con `ROYEXA_SEED=pilot` |
| `ROYEXA_DISPATCH_SECONDS` | `30` | Cada cuántos segundos el proceso envía los avisos pendientes y reintenta los fallidos. `0` apaga el ciclo; queda el envío manual del administrador |
| `ROYEXA_NOTIFIER_FAILING` | Sin definir | Con `1`, el notificador simulado falla siempre (modo «proveedor caído») |
| `ROYEXA_TIMEZONE` | `UTC` | Zona horaria del día de la caja y de los pendientes (por ejemplo `America/Bogota`). Un nombre desconocido impide arrancar |
| `ROYEXA_CURRENCY_SYMBOL` | Vacío | Símbolo antes de los importes en las páginas (`$ 1.234,56`) |
| `ROYEXA_CODE_TTL_MINUTES` | `60` | Vigencia del código de confirmación de un desembolso |
| `ROYEXA_SESSION_HOURS` | `12` | Duración de una sesión, sin renovación |
| `ROYEXA_REQUIRE_CHANGED_PASSWORDS` | Sin definir | Con `1` (modo estricto): exige base de datos, no siembra contraseñas de demostración y no arranca si queda alguna o si `royexa_app` conserva su contraseña conocida |
| `ROYEXA_SCRYPT_N` | `16384` | Coste del hash de contraseñas. Solo las pruebas lo bajan |
| `ROYEXA_CHROMIUM` | Sin definir | Pruebas de navegador: ruta de un Chromium distinto al de Playwright |
| `ROYEXA_REQUIRE_E2E` | Sin definir | Pruebas de navegador: con `1`, la falta de Chromium hace fallar en lugar de omitir (lo usa la CI) |

Las credenciales de `docker-compose.yml`, de la migración y de los usuarios sembrados son valores públicos de demostración local, no secretos.

## Ejecutar la aplicación

Desde `backend/`, con PostgreSQL levantado y migrado:

```bash
ROYEXA_LEDGER_URL=postgresql://royexa_app:royexa_app@localhost:55432/royexa \
  uv run uvicorn royexa.main:app --port 8000
```

Sin `ROYEXA_LEDGER_URL` todo queda en memoria y se pierde al apagar:

```bash
uv run uvicorn royexa.main:app --port 8000
```

- Páginas del cobrador: <http://localhost:8000/web/> (ruta del día, pagos, no pagos, solicitudes de desembolso, cierre de caja).
- Panel del administrador: <http://localhost:8000/web/admin> (solicitudes, clientes, cajas, descuadres, libro y ajustes, avisos).
- Estado: <http://localhost:8000/health>. API y OpenAPI: <http://localhost:8000/docs>.

### Datos y usuarios de demostración

Con `ROYEXA_SEED=demo` (el valor por defecto) el arranque siembra, sin pasos adicionales, dos cobradores con su ruta, dos administradores, cuatro clientes y dos préstamos previos. Repetir el arranque no duplica nada. Las contraseñas son públicas y solo valen para la demostración: `demo-<usuario>-royexa`.

| Usuario | Rol | Contraseña |
|---|---|---|
| `cobrador-1` | Cobrador de `ruta-1` | `demo-cobrador-1-royexa` |
| `cobrador-2` | Cobrador de `ruta-2` | `demo-cobrador-2-royexa` |
| `admin-1` | Administrador | `demo-admin-1-royexa` |
| `admin-2` | Administrador | `demo-admin-2-royexa` |

### Proveedor de avisos caído

Los comprobantes de pago salen por una bandeja de salida y un notificador simulado que escribe en la consola. Para demostrar la falla del proveedor:

```bash
ROYEXA_NOTIFIER_FAILING=1 \
ROYEXA_LEDGER_URL=postgresql://royexa_app:royexa_app@localhost:55432/royexa \
  uv run uvicorn royexa.main:app --port 8000
```

El pago se registra igual; el aviso queda pendiente, se reintenta en cada ciclo y al quinto intento queda fallido. El administrador lo ve y lo reintenta en `/web/admin/avisos`.

## Pruebas

Desde `backend/`:

```bash
uv run pytest                # pruebas sin base de datos (no necesitan Docker)
uv run pytest -m postgres    # solo las de PostgreSQL (docker compose up -d --wait postgres)
uv run pytest -m ""          # todas
```

Las pruebas de PostgreSQL aplican la migración por sí mismas. Las de navegador (Playwright, pantalla de 360 px) necesitan Chromium; sin él se omiten:

```bash
uv run playwright install chromium
```

El último resultado registrado, con fecha, está en [`../docs/04-entrega-final/evidencias/resultado-pruebas.txt`](../docs/04-entrega-final/evidencias/resultado-pruebas.txt).

## Módulos

| Paquete | Responsabilidad |
|---|---|
| `identity_access` | Usuarios, rutas, sesiones y contraseñas (scrypt, bloqueo por intentos) |
| `sales` | Solicitud, aprobación, rechazo y confirmación de desembolsos; excepciones de renovación |
| `loans` | Préstamos, calendario de cuotas, pagos, no pagos y pendientes de visita |
| `clients` | Alta y consulta de clientes |
| `cash_box`, `closing` | Caja diaria, cierre, descuadres y ajustes |
| `ledger` | Libro de solo inserción |
| `notifications` | Bandeja de salida y despachador de avisos |
| `adapters` | Memoria, PostgreSQL y notificador simulado |
| `web` | Páginas del servidor (cobrador y administrador) |
| `bootstrap.py`, `main.py` | Composición y punto de entrada ASGI |

## Despliegue del piloto (opcional)

No hace falta para la demostración del curso. El despliegue de un piloto con contenedor, `ROYEXA_SEED=pilot`, modo estricto y contraseñas reales (`python -m royexa.set_password <usuario>`) está en [`../docs/04-operacion/guia-de-despliegue.md`](../docs/04-operacion/guia-de-despliegue.md).

## Al terminar

Desde la raíz del repositorio:

```bash
docker compose down
```

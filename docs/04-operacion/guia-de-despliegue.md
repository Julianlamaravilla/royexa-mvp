# Guía de despliegue y operación del piloto

Cubre T10 del plan (`odd/tasks/mvp.md`). El piloto usa **Supabase** (PostgreSQL) y **Render** (el servidor), ambos en su plan gratuito. Los límites de esos planes cambian: lo marcado «a verificar» se comprueba en el panel de cada servicio al contratar.

## 1. Piezas

| Pieza | Dónde | Qué hace |
|---|---|---|
| Servidor | Render, servicio web con la imagen `backend/Dockerfile` (plano en `render.yaml`) | Sirve las páginas y el API; al arrancar aplica las migraciones y arranca el ciclo de avisos. |
| Base de datos | Supabase, proyecto con PostgreSQL | Guarda el libro y todo el estado. |
| Aviso periódico | GitHub Actions, `.github/workflows/keepalive.yml` | Consulta `/health` cada 10 minutos para que el servicio gratuito no se duerma y la base no se pause. |

## 2. Variables de entorno

Las fija `render.yaml` o el panel de Render. Los tres secretos no se escriben nunca en el repositorio (`sync: false`).

| Variable | Valor en el piloto | Para qué |
|---|---|---|
| `ROYEXA_SEED` | `pilot` | Usuarios y rutas desde `backend/pilot/directory.json`; sin clientes, préstamos ni contraseñas de demostración. |
| `ROYEXA_DIRECTORY_FILE` | (vacía) | Otro archivo de usuarios y rutas en lugar del del repositorio. |
| `ROYEXA_REQUIRE_CHANGED_PASSWORDS` | `1` | El servidor no arranca con contraseñas de demostración ni con la clave conocida del rol de la aplicación. |
| `ROYEXA_TIMEZONE` | `America/Bogota` (supuesta) | Zona horaria que fija el día de cada caja. Cambiarla por la real. |
| `ROYEXA_CURRENCY_SYMBOL` | `$` (supuesto) | Símbolo que antecede a los importes. |
| `ROYEXA_DISPATCH_SECONDS` | `30` | Cada cuántos segundos se envían y reintentan los avisos; `0` lo apaga. |
| `ROYEXA_LEDGER_URL` | **secreto** | Conexión de la aplicación (rol `royexa_app`). |
| `ROYEXA_MIGRATOR_URL` | **secreto** | Conexión del dueño del esquema (usuario `postgres` del proyecto), solo para las migraciones. |
| `ROYEXA_APP_PASSWORD` | **secreto**, 20 caracteres o más | Contraseña del rol `royexa_app`; el arranque la fija cada vez. |
| `ROYEXA_CODE_TTL_MINUTES` | `60` por defecto | Vigencia del código de confirmación. |
| `ROYEXA_SESSION_HOURS` | `12` por defecto | Duración de una sesión. |
| `ROYEXA_NOTIFIER_FAILING` | no usar | Simula un canal de avisos caído; solo para pruebas. |
| `ROYEXA_SCRYPT_N` | no usar | Baja el coste del hash de contraseñas; solo para pruebas. |
| `ROYEXA_HEALTH_URL` | variable del **repositorio** de GitHub, no de Render | Dirección completa de `/health`, por ejemplo `https://royexa.onrender.com/health`. Mientras no exista, el aviso periódico no hace nada. |

## 3. Pasos manuales, en orden

1. **Supabase.** Crear un proyecto (plan gratuito) y apuntar su contraseña de base de datos. En el botón *Connect* del proyecto copiar la cadena del **agrupador de conexiones en modo sesión** (`pooler`, puerto 5432): la conexión directa solo va por IPv6 y Render no la alcanza por IPv4. Las cadenas llevan el usuario con el identificador del proyecto, `postgres.<id>`, y deben terminar en `?sslmode=require`.
2. **Contraseña del rol de la aplicación.** Inventar una clave larga y al azar (20 caracteres o más); es `ROYEXA_APP_PASSWORD`.
3. **Cadenas de conexión.**
   - `ROYEXA_MIGRATOR_URL`: la del paso 1 con el usuario `postgres.<id>` y la contraseña del proyecto.
   - `ROYEXA_LEDGER_URL`: la misma dirección con el usuario `royexa_app.<id>` y `ROYEXA_APP_PASSWORD`.
4. **Render.** Crear el servicio desde `render.yaml` (Blueprint sobre este repositorio, rama `mvp`) y cargar los tres secretos. El primer arranque crea las tablas, el rol y las políticas (migraciones `001` a `016`).
5. **Variable de GitHub.** En el repositorio: *Settings → Secrets and variables → Actions → Variables*, crear `ROYEXA_HEALTH_URL` con la dirección de `/health`.
6. **Contraseñas reales.** En el modo exigente nadie puede entrar hasta que se ponen. El plan gratuito de Render no tiene consola, así que se hace **desde su equipo**, contra la base de Supabase, una vez por usuario (`admin-1`, `admin-2`, `cobrador-1`, `cobrador-2`, o los del archivo real). Las contraseñas las escribe quien las usará; no se pasan por ningún chat:

   ```bash
   cd backend
   uv sync
   ROYEXA_SEED=pilot ROYEXA_LEDGER_URL='<la misma de ROYEXA_LEDGER_URL, con el usuario royexa_app.<id>>' \
     uv run python -m royexa.set_password admin-1
   ```

   (`set_password` se conecta como la aplicación, con los mismos privilegios que el servidor: cambia el hash, quita la marca de demostración y cierra las sesiones de ese usuario.)
7. **Comprobar.** `https://<servicio>.onrender.com/health` responde `{"status":"ok"}`; un cobrador inicia sesión desde el celular y recorre su ruta.

## 4. Operación

- **Un solo servidor.** El ciclo de avisos corre dentro del proceso y no se coordina entre réplicas: no escalar a más de una instancia.
- **Dormido.** Sin el aviso periódico, el servicio gratuito se duerme tras unos 15 minutos sin tráfico (a verificar) y el primer visitante espera a que despierte; mientras duerme no se envían avisos.
- **Actualizar.** Se fusiona en `mvp` y se lanza el despliegue a mano desde Render (`autoDeploy: false`). Cada arranque reaplica las migraciones, que son idempotentes.
- **Datos de ejemplo.** `backend/pilot/directory.json` trae usuarios, rutas, límites, fondo y tasa **inventados**. Cambiarlos por los reales antes de manejar dinero; los clientes los da de alta el administrador.
- **Copias de seguridad.** El plan gratuito de Supabase puede no incluir copias automáticas (a verificar). Si no las hay, exportar la base con regularidad: el libro es el registro del negocio.
- **Seguridad de la base.** La migración `016` cierra todas las tablas a `anon`, `authenticated` y `service_role` y activa seguridad por filas. Toda migración que añada una tabla debe ir seguida de esa (corre en cada arranque y ordena la última). El consejero de seguridad del panel de Supabase no debe marcar tablas expuestas.

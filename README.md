# Vilas Motor — Sistema de gestión de mantenimiento (MVP)

Aplicación web en Django para planificar la mantención por horómetro de la flota
de arriendo de Vilas Motor: solicitud y registro de horómetros, cálculo del
próximo servicio, órdenes de trabajo, arriendos, planes de mantención e insumos.

**Alcance MVP:** planificación de mantenciones, horómetros, OT, arriendos, insumos,
usuarios y auditoría.
**Fuera de alcance:** stock, facturación, notificaciones, telemetría JCB, técnico
como usuario del sistema.

## Tecnologías

- Python 3.12 o superior, Django 5.2
- MySQL 8 en producción; SQLite como opción para desarrollo y pruebas locales
- WhiteNoise para servir los archivos estáticos en Vercel
- Correo saliente por la API de Brevo, Gmail (SMTP) o consola

## Estructura

| App | Contenido |
|---|---|
| `cuentas` | Usuarios, roles, clientes, inicio de sesión, verificación de correo, recuperación de contraseña, dashboard y bandejas de mantención |
| `flota` | Tipos de equipo y equipos (código automático o manual) |
| `horometros` | Solicitudes y lecturas de horómetro |
| `arriendos` | Contratos de arriendo y regreso de equipos |
| `mantencion` | Planes, servicios y órdenes de trabajo |
| `insumos` | Catálogo de insumos |
| `auditoria` | Registro automático de altas, cambios y borrados |
| `vilas_motor` | Configuración del proyecto y datos de demostración |

## Instalación local (Windows, con SQLite)

Es la forma más rápida de probar el sistema: no requiere MySQL.

### Opción rápida: `iniciar_local.bat`

Con Python 3.12 o superior instalado, basta con hacer doble clic en
`iniciar_local.bat` (en la raíz del proyecto). El script crea el entorno virtual,
instala las dependencias, genera un `.env` con SQLite si no existe, aplica las
migraciones, crea el administrador `admin@vilasmotor.cl` (clave `VilasMotor2026!`),
carga los datos de demostración y abre http://127.0.0.1:8000/. Se puede ejecutar
cuantas veces se quiera: no duplica el administrador ni los datos.

### Opción manual

```powershell
# 1. Clonar la rama de trabajo
git clone -b Gama https://github.com/kbdd23/vilas_motorMVP_E2.git
cd vilas_motorMVP_E2

# 2. Entorno virtual y dependencias
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Variables de entorno
copy .env.example .env
```

Edita `.env` y deja estas líneas (el resto se puede borrar):

```env
SECRET_KEY=una-clave-larga-cualquiera-para-desarrollo
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=sqlite
DB_NAME=db.sqlite3
```

```powershell
# 4. Crear la base, el administrador y los datos de demostración
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo

# 5. Levantar el servidor
python manage.py runserver
```

Abre <http://127.0.0.1:8000/> e inicia sesión con el correo y la contraseña del
superusuario. `seed_demo` necesita que exista ese usuario antes de ejecutarse.

Si PowerShell bloquea `Activate.ps1`, ejecuta una vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y vuelve a activar el entorno.
En Linux o macOS se activa con `source .venv/bin/activate`.

## Instalación con MySQL

En `.env`, quita `DB_ENGINE` (por defecto se usa MySQL) y completa la conexión:

```env
DB_NAME=vilas_motor
DB_USER=vilas
DB_PASSWORD=<CLAVE>
DB_HOST=127.0.0.1
DB_PORT=3306
```

La base se crea con juego de caracteres `utf8mb4`:

```sql
CREATE DATABASE vilas_motor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'vilas'@'localhost' IDENTIFIED BY '<CLAVE>';
GRANT ALL PRIVILEGES ON vilas_motor.* TO 'vilas'@'localhost';
FLUSH PRIVILEGES;
```

Luego se siguen los pasos 4 y 5 de la sección anterior.

## Usuarios y acceso

- No hay registro abierto: solo el personal autorizado crea cuentas desde el menú
  **Usuarios** (`/usuarios/`). Las cuentas creadas ahí no reciben privilegios de
  superusuario.
- Una cuenta creada desde la pantalla confirma su correo en el primer ingreso con
  un código de 6 caracteres (vigencia de 30 minutos; se puede pedir otro).
- Las cuentas creadas por consola (`createsuperuser`), por `seed_demo` o por las
  pruebas nacen verificadas.
- **¿Olvidaste tu contraseña?** en el login envía un enlace que vence en 24 horas.
- Sin credenciales de correo configuradas, los códigos y enlaces se imprimen en la
  consola donde corre `runserver`.

## Carga de la flota completa

La planilla con las maquinarias de la empresa (columnas MAQUINARIA, FABRICANTE,
MODELO, N° INTERNO y PPU) **no se incluye en el repositorio**. Para cargarla, se
copia en `flota/datos/Equipos.xlsx` (carpeta ignorada por git) o se indica su ruta:

```powershell
python manage.py cargar_flota --archivo "C:\ruta\Equipos.xlsx" --simular   # resumen, sin guardar
python manage.py cargar_flota --archivo "C:\ruta\Equipos.xlsx"             # carga o actualiza
```

- El tipo de equipo sale de la columna MAQUINARIA ("GRUA HORQUILLA 7 TON" → Grúa
  horquilla) y la capacidad se guarda junto al modelo (`FD70-10 (7 TON)`).
- Vehículos y remolques se miden en km; el resto de la maquinaria, en horas.
- Sin N° interno, el código es el prefijo del tipo más un correlativo (`GH-001`,
  `GEN-001`, `CTA-001`). Con N° interno se usa ese número.
- Se puede ejecutar varias veces: no duplica equipos ni toca su estado u horómetro.
- `iniciar_local.bat` la ejecuta solo si existe `flota/datos/Equipos.xlsx`.

## Código de equipo

Al crear un equipo se elige cómo se asigna el código:

- **Automático:** prefijo con las primeras 8 letras del tipo de equipo, más un
  correlativo de 3 dígitos. Ejemplo: tipo "Generador" → `GENERADO-001`, `GENERADO-002`.
- **Manual:** se escribe a mano y se guarda en mayúsculas (`mi-eq-14` → `MI-EQ-14`).

El código no se puede cambiar al editar el equipo.

## Variables de entorno

| Variable | Uso |
|---|---|
| `SECRET_KEY` | Clave larga y aleatoria, distinta en cada entorno |
| `DEBUG` | `True` en desarrollo; `False` en producción activa HTTPS obligatorio, cookies seguras y HSTS |
| `ALLOWED_HOSTS` | Dominios permitidos separados por comas (obligatorio con `DEBUG=False`) |
| `DB_ENGINE` | `sqlite` para usar SQLite; si se omite se usa MySQL |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexión a la base de datos |
| `BREVO_API_KEY`, `BREVO_REMITENTE` | Envío de correo por la API de Brevo (necesario en Vercel, que bloquea SMTP) |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_HOST`, `EMAIL_PORT` | Envío por SMTP (Gmail por defecto) si no hay clave de Brevo |

| `LOGIN_MAX_INTENTOS`, `LOGIN_BLOQUEO_SEGUNDOS` | Intentos fallidos permitidos y duración del bloqueo (por defecto 5 y 900) |

Las contraseñas deben tener al menos 12 caracteres.

## Despliegue en Vercel

`vercel.json` publica `vilas_motor/wsgi.py`. Los archivos estáticos se sirven
con WhiteNoise desde `staticfiles/`, que está versionada: al cambiar algo en
`static/`, copia el archivo también a `staticfiles/` o ejecuta
`python manage.py collectstatic`, y agrégalo con `git add -f`.

## Pruebas y verificación

```powershell
python manage.py test
```

- Con `DB_ENGINE=sqlite` las pruebas corren sin MySQL.
- GitHub Actions ejecuta las pruebas en cada push y pull request a `main`, `Beta` y `Gama`
  (`.github/workflows/django-tests.yml`).
- `python herramientas/medir_rendimiento.py 150 5`: mide tiempo y consultas SQL con
  una flota ampliada.
- `python herramientas/recorrido_navegador.py`: recorre los casos manuales M1 a M8
  en un navegador real (requiere Playwright y el servidor en 127.0.0.1:8765 con los
  datos de demostración).

## Seguridad y auditoría

- Acceso obligatorio por middleware a todas las pantallas, salvo login,
  recuperación de contraseña y verificación.
- Sesión de 8 horas y cookies HttpOnly y SameSite.
- Permisos por rol: crear, editar y borrar datos (planes, servicios, OT, equipos,
  arriendos, horómetros, insumos, clientes y usuarios) exige rol `planificador` o
  `administrador` (o superusuario). Otro rol solo consulta y recibe un 403
  (`cuentas/permisos.py`, decorador `requiere_rol_gestion`).
- Bloqueo por fuerza bruta: tras 5 intentos fallidos seguidos, ese correo no puede
  ingresar por 15 minutos (`LOGIN_MAX_INTENTOS`, `LOGIN_BLOQUEO_SEGUNDOS`). El contador
  usa la caché de Django; en Vercel es por instancia, así que es una protección básica.
- Los INSERT, UPDATE y DELETE de las entidades de negocio quedan registrados con
  usuario, IP y valor anterior y nuevo; la auditoría es de solo lectura.
- `/diagnostico/` es un endpoint temporal para revisar el backend de correo en
  producción; se retirará al terminar esa configuración.

## Retroalimentación al usuario

- Confirmaciones al pasar el cursor y efectos visuales en botones e interfaz.
- Diálogos para los formularios y confirmación de borrado en dos pasos.
- Tema claro u oscuro, celdas plegables y tablas ordenables; las preferencias se
  guardan en el navegador.

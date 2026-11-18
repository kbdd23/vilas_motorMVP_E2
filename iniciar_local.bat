@echo off
setlocal
REM ============================================================
REM  Vilas Motor - inicializacion y servidor local (SQLite)
REM  Uso: copiar este archivo en la raiz del proyecto (donde esta
REM  manage.py) y hacer doble clic.
REM ============================================================
cd /d "%~dp0"
title Vilas Motor - servidor local

if not exist "manage.py" (
    echo [ERROR] Este archivo debe estar en la carpeta del proyecto, junto a manage.py.
    pause & exit /b 1
)

REM --- 1. Buscar Python 3.12 o superior ---------------------------------
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo [ERROR] No se encontro Python. Instala Python 3.12+ desde python.org
    echo         y marca "Add python.exe to PATH" durante la instalacion.
    pause & exit /b 1
)
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)"
if errorlevel 1 (
    echo [ERROR] Se necesita Python 3.12 o superior. Version encontrada:
    %PY% --version
    pause & exit /b 1
)

REM --- 2. Entorno virtual ----------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo [1/6] Creando entorno virtual .venv ...
    %PY% -m venv .venv || (echo [ERROR] No se pudo crear el entorno virtual. & pause & exit /b 1)
) else (
    echo [1/6] Entorno virtual ya existe.
)
set "VPY=.venv\Scripts\python.exe"

REM --- 3. Dependencias -------------------------------------------------
echo [2/6] Instalando dependencias ...
"%VPY%" -m pip install --upgrade pip -q
"%VPY%" -m pip install -r requirements.txt -q || (echo [ERROR] Fallo la instalacion de dependencias. & pause & exit /b 1)

REM --- 4. Archivo .env (solo si no existe) -----------------------------
for /f "delims=" %%K in ('%VPY% -c "import secrets; print(secrets.token_urlsafe(50))"') do set "SK=%%K"
if not exist ".env" (
    echo [3/6] Creando .env para desarrollo con SQLite ...
    > .env (
        echo SECRET_KEY=%SK%
        echo DEBUG=True
        echo ALLOWED_HOSTS=localhost,127.0.0.1
        echo DB_ENGINE=sqlite
        echo DB_NAME=db.sqlite3
    )
) else (
    echo [3/6] Ya existe .env: se usa tal cual. Si apunta a MySQL, ese servidor debe estar encendido.
)

REM --- 5. Base de datos, administrador y datos de demostracion --------
echo [4/6] Aplicando migraciones ...
"%VPY%" manage.py migrate --noinput || (echo [ERROR] Fallaron las migraciones. & pause & exit /b 1)

echo [5/6] Creando administrador (si no existe) y datos de demostracion ...
set "DJANGO_SUPERUSER_EMAIL=admin@vilasmotor.cl"
set "DJANGO_SUPERUSER_PASSWORD=VilasMotor2026!"
set "DJANGO_SUPERUSER_NOMBRE=Administrador"
"%VPY%" manage.py shell -c "from cuentas.models import Usuario; import sys; sys.exit(0 if Usuario.objects.filter(is_superuser=True).exists() else 1)"
if errorlevel 1 (
    "%VPY%" manage.py createsuperuser --noinput || (echo [ERROR] No se pudo crear el administrador. & pause & exit /b 1)
    echo       Administrador creado: %DJANGO_SUPERUSER_EMAIL%  /  %DJANGO_SUPERUSER_PASSWORD%
) else (
    echo       Ya existe un administrador; se mantiene.
)
"%VPY%" manage.py seed_demo || (echo [ERROR] Fallo la carga de datos de demostracion. & pause & exit /b 1)
if exist "flota\datos\Equipos.xlsx" (
    echo       Cargando la flota completa desde flota\datos\Equipos.xlsx ...
    "%VPY%" manage.py cargar_flota || (echo [ERROR] Fallo la carga de la flota. & pause & exit /b 1)
)

REM --- 6. Servidor ------------------------------------------------------
echo.
echo [6/6] Servidor en http://127.0.0.1:8000/   (Ctrl+C para detenerlo)
echo       Usuario: %DJANGO_SUPERUSER_EMAIL%   Clave: %DJANGO_SUPERUSER_PASSWORD%
echo.
start "" /min cmd /c "timeout /t 4 /nobreak >nul & start "" http://127.0.0.1:8000/"
"%VPY%" manage.py runserver 127.0.0.1:8000
pause

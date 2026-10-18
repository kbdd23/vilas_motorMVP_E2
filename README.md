##Django vilas_motor system

#Comandos para la instalación de requerimientos

```
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt

```

#Comandos para inicializar la base de datos.

```

$ sudo systemctl start mysql  //(levantar mysql)
$ sudo mysql -e "CREATE DATABASE vilas_motor CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci" //(Creamos la db y establecemos su configuracion para simbolos.)
$ sudo mysql -e "CREATE USER 'vilas'@'localhost' IDENTIFIED BY '<CLAVE>'; GRANT ALL PRIVILEGES ON vilas_motor.* TO 'vilas'@'localhost'; FLUSH PRIVILEGES;"

```

#Creación de apps y proyecto
**Alcance MVP:** planificación de mantenciones, horómetros, OT, insumos, auditoría. 
**Out-scope:** stock, facturación, notificaciones, telemetría, técnico como actor.


```
django-admin startproject vilas_motor . (con el venv activo y descargado el requirements)

python manage.py startapp cuentas
python manage.py startapp flota
python manage.py startapp insumos
python manage.py startapp mantencion
python manage.py startapp horometros
python manage.py startapp arriendos
python manage.py startapp auditoria

```

## Configuración de seguridad (variables de entorno)

- `DEBUG`: usar `False` en producción. Con `DEBUG=False` se activan HTTPS obligatorio, cookies seguras y HSTS.
- `ALLOWED_HOSTS`: lista separada por comas con los dominios permitidos (obligatorio con `DEBUG=False`).
- `SECRET_KEY`: valor largo y aleatorio, distinto en cada entorno.
- Contraseñas: largo mínimo de 12 caracteres.
- Auditoría: los INSERT, UPDATE y DELETE de las entidades de negocio quedan registrados automáticamente con usuario, IP y valores anterior y nuevo.

## Herramientas de verificación

- `python manage.py test`: pruebas automatizadas.
- `python herramientas/medir_rendimiento.py 150 5`: mide tiempo y consultas SQL con una flota ampliada.
- `python herramientas/recorrido_navegador.py`: recorre los casos manuales M1 a M8 en un navegador real (requiere Playwright y el servidor en 127.0.0.1:8765 con los datos de demostración).

## Herramientas de retroalimentación al usuario:

-Hovers de confirmación
-Dialogos para los formularios
-Efectos de feedback visual al usuario en cada botón e interfaz.

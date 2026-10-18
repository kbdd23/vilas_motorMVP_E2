##Bitacora de desarrollo del proyecto Django Vilas Motor
Autor: Francisco Vera. 
Este documento no debe entregarse en la entrega del MVP, es para los integrantes del grupo. Para que Daniel compare cambios respecto a los UML. Para que Rodrigo analice qué redactar en cada punto y para que Marcos cuadre el roadmap donde todos trabajamos en el desarrollo para el cronograma Microsoft Proyect. 

##Jerarquía de bitacoras:
Se nombrará de más vieja a más nueva.

-Diagramas UML pre-eliminares (png's)
-Esquema SQL depurado con su propia bitacora interpretado a partir del diag preliminar
-Boceto de clases depurado considerando al esquema SQL.
-Bitacoras_<prefijo_diagrama> 
-App.txt

#Precedencias importantes
El diagrama relacional preliminar dió vida al esquema SQL depurado, el esquema SQL permitió el discernimiento para la 
depuración y creación del mapeo de clases del diagrama de clases para que respetara el modelo de datos. 
El boceto de clases permitió el discenirmiento y comprensión de los demás diagramas, dando a luz a sus bitacoras.
Finalmente todos los diagramas anteriores ayudaron a la comprensión del nuevo alcance del MVP lo que permitió el 
diseño de aplicaciones para el backend django en app.txt

##Desarrollo de modelos

Según requerimientos... una vez creadas las bases de datos mediante las instrucciones del README,
y la redacción del .env que definió:
DB_NAME, DB_PASSWORD, DB_USER, DB_HOST, DEBUG y SECRET_KEY.

Posteriormente se decidió primero crear los modelos de cada aplicación, se detalla el proceso paso a paso llevado a cabo

#I.-Settings.py
1.-Se crearon las apps del proyecto y luego fueron añadidas.
2.-Preconfiguraciones de secret_key y debug.
3.-La base de datos MySQL fue configurada
4.-Directorio de templates y static conectadas
5.-Configuración de idioma y zona horaria
6.-Inicialización con de AUTH_USER_MODEL mediante un comentario, se deja en blanco hasta crear 'cuentas.Usuario'

#II.-cuentas/managers.py y cuentas/models.py

1.-Se creó un manager de usuario propio utilizando el patrón factory mediante BaseUserManager (custom user)
2.-Se creó el modelo para usuarios, roles, y clientes.
3.-En el manager se creó un sistema de anti-escalada para en caso de escalada de roles mediante insersión. (seguridad)
4.-Se descomenta el comentario de AUTH_USER_MODEL en settings.py ahora que se ha implementado los módulo.

Notas:

N.1: El planificador (único rol) administra: create_user fija is_staff=True.
N.2: PermissionsMixin agrega la columna is_superuser y las tablas M2M usuario_groups y usuario_user_permissions; is_staff se declara a mano.
Django suma además sus tablas propias (auth_group, auth_permission, django_content_type, django_session, django_migrations). Nada de esto está en schema.sql: es infraestructura del framework, no redundancia.
N.3: Ahora se entra con email, no con nombre de usuario. Además se forzó a Django a mantener los nombres del esquema en la base de datos. Las columnas siguen manteniendo sus nombres.

#III.-flota/models.py

1.-Se crea a partir del modelo al ORM
2.-Hallazgo: estado no tiene default, corregido en el esquema y documentado en la bitacora_esquema. Debe nacer disponible y debe ser no nulo. Implementado en el modelo.

#IV.- insumos/models.py & arriendos/models.py

1.-Se crean respetando las reglas de negocio.

N.1: Arriendo tiene FK' s de Cliente y flota, asi que se implementa correctamente.
N.2: fecha_termino nullable = la señal de "vigente". Null significa arriendo abierto. No hay campo estado: la vigencia se infiere.

#V.- horometros/models.py

1.-Se crea el modelo
2.-Hallazgo: atributo 'fuente' debe ser no nulo y el atributo 'estado' debe tener el estado por default "pendiente". Se actualizó el schema.sql y se agregó un punto en su bitacora.


#VI.- mantencion/models.py

1.-Se crea el modelo siguiendo la documentación y modelos anteriores.
2.-Hallazgo menor sobre sintaxis erronea en el schemaSQL
3.- atributo "tipo" modelado como NOT NULL sin default: el planificador elige preventiva o correctiva
al crear la OT

N.1:PK compuesta. El schema usa PRIMARY KEY (id_servicio_plan, id_insumo) y (id_ot, id_insumo). Django no soporta PK compuesta. Lo resolví con UniqueConstraint + on_delete=CASCADE. Consecuencia honesta: Django agregará una columna id extra y la clave será UNIQUE, no PRIMARY KEY. No hay forma limpia de
evitarlo.

#VII.- auditoria/models.py

1.-Se crea los modelos Auditoria y ArchivoAdjunto
2.-Hallazgo: 'id_registro' no es fk, es una referencia genérica(out-scoping) Se modeló como BigIhtegerField.
3.-'ruta' se cambia de CharField a FileField para la gestión real de archivos y exportaciones.
4.-Se configura MEDIA_ROOT y MEDIA_URL en settings.py, y el serving de media en urls.py (media serving se activa solo en debug; en producción lo sirve el servidor web.)

N.1: FileField(upload_to='adjuntos/', max_length=500) sigue mapeando. VARCHAR(500)
N.2:nombre_original y mime se conservan aunque FileField exponga name y content_type: guardan el nombre humano y el MIME explícito, que FileField no persiste.

#VIII.- Migración de los modelos para validar

1.-Se migran los modelos para validar sus referencias cruzadas, dando todas éxito. 
(python manage.py makemigrations, luego migrate)

#IX.- Lógica de dominio, servicios y pruebas

1.-Se trasladan los métodos de dominio restantes del boceto de clases (classes.py) a modelos ORM:

-Equipo (cambiarEstado, actualizarHorometro, ultimaLectura), PlanMantencion(serviciosOrdenados)
-ServicioPlan (insumosRequeridos)
-Arriendo (cerrar, estaVigente)
-SolicitudHorometro (cumplir, marcarVencida)
-OrdenTrabajo (programar, registrarInsumo, cerrar).

2.-Se descartaron los métodos autenticación, set_password, save, permisos y los de fuera de alcance(stock, notificación, telemetria) por que django los cobre o están fuera de scope.

3.-Se crea el servicio puro CalculadoraProximoServicio en mantencion/services.py

4.-Se crea el servicio puro ValidadorDatos en horometros/services.py

5.Población de pruebas: se escribieron 20 tests en flota, mantención, horometros y arrendos que validan métodos y servicios. 20/20 aprobados en todos. (usar pyhton manage.py test)

N.1: ValidadorDatos rechaza lecturas negativas o menores al horómetro actual (el horómetro no retrocede).

N.2: CalculadoraProximoServicio define "próximo servicio" como el de menos horas restantes: intervalo − (horómetro_actual − último cierre de OT de ese servicio). 

N.3: Los servicios no son tablas: viven en services.py y no generan migración (makemigrations --check reportó "sin cambios").

N.4: OrdenTrabajo.cerrar() también fija fecha_ejecucion, dato que el boceto omitía.

#X.-Registro de CRUDs en admin.py de las aplicaciones y superusuario

1.-Se registran los 16 modelos en los admin.py de las 7 apps 
2.-Hallazgo: nuestro create_superuser exige que exista el rol planificador en la tabla rol Se crea el módulo de data migration 'seed_rol_planificador' en cuentas/migrations con el fin de sembrar el rol planificador con get_or_create, asegurando su existencia al hacer migrate.

3.-Se crea el superusuario con las siguientes credenciales:
-email: test@vilasmotor.cl
-Nombre: Planificador
-Password: Seguridad2026!

#XI.- Vistas de listado, templates y navegación

1.-Se crearon las vistas de listado de las 6 apps (equipos, tipos, insumos, solicitudes, lecturas, arriendos, planes, OT, clientes, catálogos, home y dashboard); todas responden 200.
2.-Se creó base.html (header con logo y nav, footer) y los templates de cada listado, conectados con namespaces ({% url 'app:nombre' %}).
3.-El dashboard usa CalculadoraProximoServicio con un umbral de alerta (100 horas) para marcar equipos en alerta.

#XII.- Login y protección de vistas

1.-Login por email (LoginForm + LoginView/LogoutView), con LOGIN_URL apuntando al login propio.
2.-Se protegió todo el sistema con LoginRequiredMiddleware: toda vista pide login; login, logout y admin quedan exentos.
3.-El header muestra "Entrar"/"Cerrar sesión" según la sesión.

#XIII.- Forms de escritura y alta de catálogos

1.-Horómetros: solicitar lectura y registrar lectura (ValidadorDatos rechaza el retroceso del horómetro).
2.-Arriendos: crear y cerrar (rechaza re-arrendar un equipo ya vigente).
3.-Órdenes de trabajo: crear (número auto OT-0001...), registrar insumo y cerrar.
4.-Alta de catálogos en la app: cliente, tipo de equipo, equipo, insumo, plan y servicio (sin depender del admin).
5.-Detalle de equipo: ficha con historial (lecturas, OT, arriendos) y botones de acción.

#XIV.- Pruebas

1.-Se ampliaron los tests de 20 a 35, cubriendo vistas de escritura, alta de catálogos y detalle de equipo. 35/35 aprobados.

N.1: numero_ot se genera automáticamente al crear la OT (OT-0001, OT-0002...).
N.2: arriendo con fecha_termino nula = vigente (regla ya documentada en IV).


#Perfectivos.

1.Un contrato se queda visible mientras se cumpla alguna de estas dos cosas:

   - Vigente — sin fecha de término (NULL). Es el contrato abierto.
   - Dentro de la ventana — se cerró hace menos de N horas. Así ves que el cierre
     de hoy ocurrió y se limpia solo al vencer el plazo.
   - Pendiente de traspaso — el equipo todavía no está DISPONIBLE. Esta condición
     no expira con el reloj, expira con tu acción

#Perfectivos: bandeja de horómetros.

1.Se reestructura el módulo como bandeja de trabajo, igual que arriendos. Antes
  eran dos listados sueltos (solicitudes y lecturas) que no se hablaban:

   - SolicitudHorometro.cumplir() y marcarVencida() existían en el modelo pero no
     los llamaba ninguna vista: la solicitud nacía PENDIENTE y moría PENDIENTE.
   - La lectura registrada nunca se vinculaba a la solicitud que la había pedido.
   - La lectura nacía validada=False y no había forma de validarla, así que el
     badge "Pendiente" era permanente.

2.Regla de la bandeja: aparece toda solicitud que tenga un paso pendiente.

   - PENDIENTE — siempre, sin importar cuánto tiempo pase.
   - CUMPLIDA o VENCIDA — solo dentro de la ventana.
   - Sin deduplicar por equipo, a diferencia de arriendos: dos pendientes de la
     misma máquina son dos obligaciones distintas y el planificador necesita
     verlas para contrastar el dato real.

3.Columna Acción: "Registrar lectura" (btn-secondary) y "Marcar vencida"
  (btn-danger, con <dialog> de confirmación). Un solo acto cierra el paso: crea
  la lectura, llama cumplir() y actualiza equipo.horometro_actual. La lectura
  nace validada=True porque la tipea el planificador, que es quien confirma.

4.Se agrega SolicitudHorometro.fecha_resolucion (migración 0002, con backfill de
  las ya resueltas): es la que gobierna la ventana, igual que fecha_termino en
  arriendos. La lista de ventanas pasa a vilas_motor/ventanas.py para que las dos
  bandejas compartan la misma preferencia.

5.El formulario de solicitud limita el equipo a los que están EN FAENA y el
  cliente al de su arriendo más reciente: la máquina puede seguir en faena con el
  contrato ya cerrado (devolución tardía) y el horómetro se le sigue pidiendo a
  quien la tiene. Esto invierte el test 'test_arriendo_cerrado_no_cuenta', que
  afirmaba lo contrario.

N.1: Hallazgo: el lookup '__date__gte' sobre un DateTimeField no devuelve nada en
     este entorno (SQLite + USE_TZ=True). Con una fecha de hoy y límite de ayer
     dio [] mientras el '__gte' equivalente devolvió [25]. La ventana de
     horómetros compara contra un datetime.

N.2: La ventana se cuenta en horas en horómetros y en días en arriendos, porque
     fecha_termino es un DateField y fecha_resolucion un DateTimeField.

N.3: Hueco conocido: las lecturas validada=False (telemetría) no tienen acción de
     validación en la bandeja. Todavía no hay ingesta real de telemetría, así que
     solo las produce el seed.

6.Las rutas del módulo pasan a colgar de /horometros/ (antes /solicitudes/ y
  /lecturas/ quedaban a nivel raíz, fuera del patrón de las demás apps).

N.4: Se agrega un aviso en la vista de solicitud cuando no hay equipos en faena:
     el desplegable salía vacío sin explicación.

#Perfectivos: fuente por solicitud.

1.Se agrega SolicitudHorometro.fuente (migración 0003). Dice a quién se le pidió
  el dato y no es decorativa: gobierna qué equipos se pueden elegir.

   - Cliente    -> equipos EN_FAENA (el que la tiene es el arrendatario)
   - Técnico    -> equipos DISPONIBLE (el técnico revisa la máquina en bodega)
   - Telemetría -> cualquier estado

2.El desplegable de fuente va primero y recarga con ?fuente=: el filtrado de
  equipos lo hace el servidor, no el navegador. La celda del cliente es
  informativa: consulta /horometros/equipos/<id>/arrendatario/ (JSON) y mientras
  llega muestra un spinner. Elegir el equipo ya no recarga la página.

3.El cliente deja de ser campo del formulario y pasa a derivarse del equipo
  (SolicitudHorometro.cliente queda nullable, migración 0003). Una solicitud al
  técnico o a la telemetría no se le pide a nadie de afuera, así que no hay
  cliente que inyectar.

4.La lectura hereda la fuente de la solicitud: el formulario de respuesta ya no
  pregunta la fuente, solo el valor. Se elimina el registro de lectura directa,
  que quedaba subsumido por las tres fuentes.

5.'Marcar vencida' se reemplaza por 'Borrar' con confirmación doble. El estado
  VENCIDA sale del modelo y las vencidas existentes vuelven a PENDIENTE (migración
  0003): una solicitud se cierra ingresando el dato o se borra, y la que nunca
  recibió su dato es una obligación viva, no un estado final.

6.fuenteSugerida() elige la fuente del enlace de la ficha según el estado del
  equipo: faena -> cliente, bodega -> técnico, el resto -> telemetría.

N.5: Hallazgo: la migración 0003 copió la fuente de la lectura vinculada, y una
     lectura sí puede ser PLANIFICACION, que no es fuente de solicitud. La 0004
     normaliza esos casos a CLIENTE.

N.6: Hallazgo: con la flota entera DISPONIBLE no hay a quién pedirle en faena y el
     desplegable de la fuente Cliente queda vacío. El formulario expone
     sinEquipos() y la vista muestra un aviso que explica la regla.

7.Registrar lectura deja de ser una página y pasa a ser un <dialog> de la bandeja.
  El botón de la fila lleva el encabezado en atributos data, así que abrirlo no
  consulta al servidor. Si el POST no pasa la validación, la vista reenvía la
  bandeja con el diálogo abierto (data-abrir-al-cargar) para que el error quede a
  la vista y no se pierda lo que se había escrito. Se elimina registrar.html.

N.7: El formulario del diálogo se renderiza con {{ form_lectura.as_p }}, la misma
     clase que valida el POST, para que los campos y las reglas no se separen.

8.La bandeja y el historial de lecturas pasan a ser dos celdas plegables de la
  misma página (/horometros/, ruta renombrada a horometros:index). Nacen cerradas
  y el estado se recuerda en localStorage (static/js/plegables.js), porque el
  despliegue es una preferencia de la persona y no de la pantalla. Se eliminan la
  vista lista_lecturas, su ruta y las plantillas bandeja.html y lecturas.html.

N.8: Las celdas usan <details>/<summary> nativo: abrir y cerrar no necesita
     JavaScript, solo recordar cómo quedaron.

9.El alta de solicitud se muda a un diálogo de la bandeja: el botón "Solicitar
  lectura" vive dentro de la celda y abre el formulario ahí mismo, sin pasar de
  página. No hay paso de confirmación: la solicitud se puede borrar, así que el
  error se corrige después y no antes. Se elimina la plantilla solicitar.html.

N.9: Hallazgo: ventana.js reemplazaba el search entero ("?ventana=24"), así que se
     llevaba puestos los otros parámetros. En la bandeja de arriendos no se notaba
     porque es el único; en horómetros convive con fuente y nueva, y el diálogo se
     cerraba solo al elegir la fuente. Ahora hay un ayudante compartido
     (static/js/parametros.js, recargarCon) que cambia un parámetro y deja quietos
     los demás. arriendos.html también carga ese archivo.

N.10: Hallazgo: la fuente no tiene valor por defecto y Django ya agregaba su opción
      vacía ('---------'). Se descarta y se reemplaza por una con nombre
      ('— Elige una fuente —'), para no mostrar dos opciones vacías.

11.El dashboard deja de ser un informe de pronóstico y pasa a ser un panel de
  trabajo: arriba una franja de contadores (contexto, no trabajo), después las
  colas de "qué hacer" (pedir horómetros, mantención vencida, por vencer, órdenes
  abiertas y equipos sin devolver, cada una con su enlace), y abajo el pronóstico
  por equipo. La entrada / redirige al dashboard: queda un solo panel y se elimina
  la plantilla home.html.

N.11: Hallazgo: el dashboard pintaba igual un servicio VENCIDO y uno POR VENCER.
      estaEnAlerta devuelve horas_restantes <= umbral, que incluye los negativos,
      así que un intervalo ya cumplido se mostraba como "próximo a vencer". Ahora
      se separan: VENCIDO (rojo), POR_VENCER (ámbar), AL_DÍA (verde) y SIN_PLAN
      (gris). La bajada lo pedía ("generar alertas cuando esté próximo a cumplir su
      intervalo") y su templates.txt también ("alerta si está en umbral o vencido").

N.12: El dashboard recorre los equipos y calcula en Python (N+1). Con la flota
      actual está bien; con cientos de equipos habrá que cachear o llevar el cálculo
      a una consulta. Queda anotado para no perderlo.

13.Las órdenes de trabajo ganan administración: editar y borrar. Ambas solo
  aplican a PROGRAMADA y EN_CURSO; una CERRADA es historial de mantención (su
  horómetro de cierre alimenta la calculadora del próximo servicio) y no se toca,
  ni para editar ni para borrar. Borrar es un POST con doble confirmación, como la
  bandeja de horómetros, y se lleva los insumos cargados.

N.13: No hay un rol "admin" separado: el planificador es quien administra. Es la
      decisión tomada, porque el único actor del MVP es el planificador y no hay
      que abrir una puerta de permisos que hoy no se usa.

14.La OT completa su máquina de estados: PROGRAMADA → (iniciar) EN_CURSO →
  (cerrar) CERRADA. El botón "Iniciar" (naranja) pasa a en curso, y solo una OT en
  curso se puede cerrar: ya no existe el salto directo de programada a cerrada. El
  alta se muda a un diálogo de la lista (igual que el alta de solicitud en
  horómetros) y se elimina crear_orden.html. Cerrar conserva su página porque pide
  el horómetro de cierre.

15.La página de planes gana una columna Acción: editar y borrar, tanto para
  planes como para servicios. Borrar respeta las dependencias: un plan con
  servicios no se borra (primero hay que quitar sus servicios) y un servicio con
  OTs no se borra (es historial). Editar un servicio sí se permite aunque tenga
  OTs: cambiar el intervalo redefine el plan hacia adelante, no toca el historial.
  El nav suma "Mantención" → /planes/, porque la página estaba huérfana.

N.14: La confirmación de borrado en dos pasos estaba duplicada (horómetros y
      OTs). Se extrajo a static/js/borrado.js (iniciarCierreDeDialogos +
      iniciarBorradoEnDosPasos), que ahora comparten las tres páginas.

16.El pronóstico del dashboard gana su botón de acción: cada fila tiene "Crear
  OT", que abre el alta con el equipo y el servicio vencido ya seleccionados. Es
  la respuesta a "¿qué hago con un vencido?": programar la OT, ejecutarla y
  cerrarla con el nuevo horómetro, que es lo que recalcula el pronóstico. El alta
  acepta el parámetro ?servicio= para preseleccionar el servicio, igual que ya
  hacía con ?equipo=.
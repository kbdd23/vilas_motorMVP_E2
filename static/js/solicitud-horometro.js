/*
 * Formulario de solicitud de horómetro, que vive en un diálogo de la bandeja.
 *
 * 1. La fuente manda: define de dónde salen los equipos, así que al cambiarla se
 *    recarga la página con ?fuente= y el servidor devuelve el desplegable ya
 *    filtrado, manteniendo el diálogo abierto con ?nueva=. El filtrado no se hace
 *    acá para que las reglas vivan en un solo lugar, que es el servidor.
 * 2. La celda del cliente es informativa: consulta el arrendatario del equipo para
 *    que se vea a quién se le va a pedir, y mientras llega avisa que está cargando.
 *    El cliente real lo deriva el servidor al guardar la solicitud, así que esto no
 *    reemplaza ninguna validación.
 */
(function () {
    'use strict';

    function iniciarSelectorDeFuente() {
        var selectorFuente = document.getElementById('id_fuente');

        if (!selectorFuente) {
            return;
        }

        selectorFuente.addEventListener('change', function () {
            recargarCon({fuente: selectorFuente.value, nueva: '1'});
        });
    }

    function iniciarDialogoDeSolicitud() {
        var dialogo = document.getElementById('dialogo-solicitud');

        if (!dialogo) {
            return;
        }

        document.querySelectorAll('[data-abrir-solicitud]').forEach(function (boton) {
            boton.addEventListener('click', function () {
                dialogo.showModal();
            });
        });

        // El servidor deja ?nueva= cuando reenvía la página con el diálogo abierto,
        // sea porque el POST no pasó la validación o porque se entró por la URL
        // directa. Se abre solo para que el error quede a la vista.
        if (dialogo.dataset.abrirAlCargar === 'si') {
            dialogo.showModal();
        }

        // Al cerrarlo se limpia ?nueva= de la URL. Si quedara ahí, cualquier recarga
        // posterior lo volvería a abrir sin que nadie lo haya pedido.
        dialogo.addEventListener('close', function () {
            if (window.location.search.indexOf('nueva=') !== -1) {
                var url = new URL(window.location.href);
                url.searchParams.delete('nueva');
                history.replaceState({}, '', url.toString());
            }
        });
    }

    function iniciarCeldaDelCliente() {
        var campo = document.getElementById('campo-cliente');
        var celda = document.getElementById('celda-cliente');
        var selectorFuente = document.getElementById('id_fuente');
        var selectorEquipo = document.getElementById('id_equipo');

        if (!campo || !celda || !selectorFuente || !selectorEquipo) {
            return;
        }

        function mostrar(texto, estado) {
            celda.textContent = texto;
            celda.dataset.estado = estado;
        }

        function cargar() {
            if (selectorFuente.value !== 'CLIENTE') {
                campo.dataset.visible = 'no';
                return;
            }

            campo.dataset.visible = 'si';

            if (!selectorEquipo.value) {
                mostrar('Elige un equipo para ver a quién se le pide.', 'inactivo');
                return;
            }

            mostrar('Consultando el arrendatario', 'cargando');

            // El 0 de la URL es un marcador: se reemplaza por el equipo elegido.
            fetch(celda.dataset.url.replace('/0/', '/' + selectorEquipo.value + '/'))
                .then(function (respuesta) {
                    return respuesta.json();
                })
                .then(function (datos) {
                    if (datos.cliente) {
                        mostrar(datos.cliente, 'ok');
                    } else {
                        mostrar(datos.mensaje, 'error');
                    }
                })
                .catch(function () {
                    mostrar('No se pudo consultar el arrendatario.', 'error');
                });
        }

        selectorEquipo.addEventListener('change', cargar);
        cargar();
    }

    iniciarSelectorDeFuente();
    iniciarDialogoDeSolicitud();
    iniciarCeldaDelCliente();
})();

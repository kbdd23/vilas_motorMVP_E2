/*
 * Buscador global del panel.
 *
 * Pide las coincidencias al endpoint /buscar/?formato=json mientras se escribe y
 * las dibuja en un desplegable bajo el input. El servidor hace todo el trabajo de
 * coincidencia y ranking; aca solo queda el ritmo de las peticiones (debounce),
 * el teclado y el cierre del panel.
 */
(function () {
    'use strict';

    var ESPERA_ENTRE_TECLAS = 250;
    var LARGO_MINIMO = 2;

    var formulario = document.querySelector('[data-buscador-global]');
    if (!formulario) {
        return;
    }

    var entrada = formulario.querySelector('#buscador-global');
    var panel = formulario.querySelector('#buscador-panel');
    if (!entrada || !panel) {
        return;
    }

    var temporizador = null;
    var peticionEnCurso = null;
    var indiceActivo = -1;

    function escaparHtml(texto) {
        var contenedor = document.createElement('div');
        contenedor.textContent = texto == null ? '' : texto;
        return contenedor.innerHTML;
    }

    function urlBusqueda(texto) {
        return formulario.getAttribute('action') + '?formato=json&q=' + encodeURIComponent(texto);
    }

    function cerrarPanel() {
        panel.hidden = true;
        panel.innerHTML = '';
        indiceActivo = -1;
        entrada.setAttribute('aria-expanded', 'false');
    }

    function abrirPanel() {
        panel.hidden = false;
        entrada.setAttribute('aria-expanded', 'true');
    }

    function seccion(titulo, resultados) {
        if (!resultados.length) {
            return '';
        }
        var filas = resultados.map(function (resultado) {
            return '<a class="buscador-item" role="option" href="' + escaparHtml(resultado.url) + '">' +
                '<strong>' + escaparHtml(resultado.titulo) + '</strong>' +
                '<small>' + escaparHtml(resultado.detalle) + '</small>' +
                '</a>';
        }).join('');
        return '<div class="buscador-grupo"><span class="buscador-grupo-titulo">' +
            escaparHtml(titulo) + '</span>' + filas + '</div>';
    }

    function dibujar(datos) {
        var contenido = seccion('Equipos', datos.equipos) +
            seccion('Órdenes de trabajo', datos.ordenes) +
            seccion('Clientes', datos.clientes);

        if (!contenido) {
            panel.innerHTML = '<p class="buscador-vacio">Sin coincidencias para «' +
                escaparHtml(datos.consulta) + '».</p>';
        } else {
            panel.innerHTML = contenido;
        }
        indiceActivo = -1;
        abrirPanel();
    }

    function dibujarError() {
        panel.innerHTML = '<p class="buscador-vacio">No se pudo buscar en este momento.</p>';
        abrirPanel();
    }

    function consultar(texto) {
        if (peticionEnCurso) {
            peticionEnCurso.abort();
        }
        peticionEnCurso = new AbortController();

        fetch(urlBusqueda(texto), {
            signal: peticionEnCurso.signal,
            headers: { 'X-Requested-With': 'fetch' }
        })
            .then(function (respuesta) {
                if (!respuesta.ok) {
                    throw new Error('Respuesta ' + respuesta.status);
                }
                return respuesta.json();
            })
            .then(dibujar)
            .catch(function (error) {
                // Un abort es el resultado normal de seguir escribiendo: se ignora.
                if (error.name !== 'AbortError') {
                    dibujarError();
                }
            });
    }

    function moverSeleccion(paso) {
        var items = panel.querySelectorAll('.buscador-item');
        if (!items.length) {
            return;
        }
        indiceActivo = (indiceActivo + paso + items.length) % items.length;
        items.forEach(function (item, posicion) {
            item.classList.toggle('activo', posicion === indiceActivo);
        });
        items[indiceActivo].scrollIntoView({ block: 'nearest' });
    }

    entrada.addEventListener('input', function () {
        var texto = entrada.value.trim();
        window.clearTimeout(temporizador);

        if (texto.length < LARGO_MINIMO) {
            cerrarPanel();
            return;
        }

        temporizador = window.setTimeout(function () {
            consultar(texto);
        }, ESPERA_ENTRE_TECLAS);
    });

    entrada.addEventListener('keydown', function (evento) {
        if (panel.hidden) {
            return;
        }
        if (evento.key === 'ArrowDown') {
            evento.preventDefault();
            moverSeleccion(1);
        } else if (evento.key === 'ArrowUp') {
            evento.preventDefault();
            moverSeleccion(-1);
        } else if (evento.key === 'Enter') {
            var activo = panel.querySelector('.buscador-item.activo');
            if (activo) {
                evento.preventDefault();
                window.location.href = activo.getAttribute('href');
            }
        } else if (evento.key === 'Escape') {
            cerrarPanel();
        }
    });

    document.addEventListener('click', function (evento) {
        if (!formulario.contains(evento.target)) {
            cerrarPanel();
        }
    });

    formulario.addEventListener('submit', function () {
        cerrarPanel();
    });
}());

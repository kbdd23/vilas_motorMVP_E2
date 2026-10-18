from django import forms

from flota.models import Equipo

from .models import LecturaHorometro, SolicitudHorometro

# Estados en los que puede estar el equipo según a quién se le pida el horómetro.
# Al técnico se le pide con la máquina en bodega (está presente), al cliente con la
# máquina en faena (la tiene él), al interno con la máquina en uso interno, y la
# telemetría no depende de dónde esté. Una lista vacía significa "cualquier estado".
ESTADOS_POR_FUENTE = {
    'CLIENTE': [Equipo.Estado.EN_FAENA],
    'TECNICO': [Equipo.Estado.DISPONIBLE],
    'TELEMETRIA': [],
    'INTERNO': [Equipo.Estado.INTERNO],
}


class SolicitudHorometroForm(forms.ModelForm):
    """Solicitud de horómetro: a quién se le pide y de qué equipo.

    La fuente no es decorativa, es la que define de dónde salen los equipos. Se
    resuelve en el servidor y no solo en la pantalla, así que un POST manipulado
    con un equipo que no corresponde a la fuente no pasa la validación.

    El cliente no es un campo: se deriva del equipo al guardar, así que acá no hay
    nada que inyectar.
    """

    class Meta:
        model = SolicitudHorometro
        fields = ['fuente', 'equipo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fuente'].choices = self._fuentes_con_la_vacia()
        self.fields['fuente'].help_text = 'A quién se le va a pedir el horómetro.'
        self.fields['equipo'].queryset = self._equipos_de_la_fuente()
        self.fields['equipo'].help_text = self._ayuda_del_equipo()
        self.fields['equipo'].error_messages['invalid_choice'] = (
            'Ese equipo no corresponde a la fuente elegida.'
        )

    def _fuentes_con_la_vacia(self):
        """Fuentes con una sola opción vacía adelante, y con nombre.

        La fuente no tiene valor por defecto a propósito: es la que decide qué
        equipos se ofrecen. Django agrega su propia opción vacía ('---------')
        cuando el campo acepta quedar en blanco, así que se descarta para no
        mostrar dos y para que la que quede diga qué se está eligiendo.
        """
        vacia = ('', '— Elige una fuente —')
        return [vacia] + [
            opcion for opcion in self.fields['fuente'].choices if opcion[0] != ''
        ]

    def _fuente_elegida(self):
        """Fuente elegida, venga del POST o del enlace que abrió el formulario."""
        if self.is_bound:
            return self.data.get('fuente') or None
        return self.initial.get('fuente') or None

    def _equipos_de_la_fuente(self):
        """Equipos que tienen sentido para la fuente elegida.

        Sin fuente no se ofrece ninguno: primero hay que decidir a quién se le
        pide, porque eso es lo que define qué equipos aparecen.
        """
        estados = ESTADOS_POR_FUENTE.get(self._fuente_elegida())
        if estados is None:
            return Equipo.objects.none()
        if not estados:
            return Equipo.objects.order_by('codigo')
        return Equipo.objects.filter(estado__in=estados).order_by('codigo')

    def _ayuda_del_equipo(self):
        fuente = self._fuente_elegida()
        if fuente is None:
            return 'Elige primero a quién le vas a pedir el horómetro.'
        if fuente == LecturaHorometro.Fuente.CLIENTE:
            return 'Solo equipos en faena: el horómetro se le pide a quien tiene la máquina.'
        if fuente == LecturaHorometro.Fuente.TECNICO:
            return 'Solo equipos disponibles: el técnico revisa la máquina en bodega.'
        if fuente == LecturaHorometro.Fuente.INTERNO:
            return 'Solo equipos en uso interno: el dato lo reporta quien los tiene.'
        return 'La telemetría no depende del estado del equipo.'

    def sinEquipos(self):
        """True si la fuente elegida no tiene ningún equipo que ofrecer.

        Con la flota entera en bodega, por ejemplo, no hay a quién pedirle el dato
        en faena. La vista lo usa para explicar el desplegable vacío en vez de
        dejarlo mudo.
        """
        return self._fuente_elegida() is not None and not self.fields['equipo'].queryset.exists()


class LecturaDeSolicitudForm(forms.ModelForm):
    """Lectura que cierra una solicitud de horómetro.

    El equipo, el cliente y la fuente ya los fija la solicitud, así que acá solo
    se reporta el dato que se recibió.
    """

    class Meta:
        model = LecturaHorometro
        fields = ['valor', 'observacion']

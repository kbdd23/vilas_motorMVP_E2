"""Ventana de trazabilidad compartida por las bandejas de trabajo.

Una bandeja lista lo que tiene un paso pendiente y, además, lo que se resolvió
hace poco, para que el trabajo del día no se desvanezca antes de verlo. Ese
"hace poco" es la ventana, y es una preferencia de la persona que la elige, no de
la pantalla: por eso la lista de opciones y el valor por defecto viven acá y las
dos bandejas (arriendos y horómetros) leen lo mismo.
"""

VENTANAS = [
    ('24', '24 horas', 1),
    ('48', '48 horas', 2),
    ('72', '72 horas', 3),
    ('168', '7 días', 7),
]

VENTANA_POR_DEFECTO = '24'


def dias_de_ventana(clave):
    """Días de la ventana pedida, o los del valor por defecto si no es válida."""
    for valor, _, dias in VENTANAS:
        if valor == clave:
            return dias
    return VENTANAS[0][2]

from django.shortcuts import redirect, render

from .forms import InsumoForm
from .models import Insumo


def lista_insumos(request):
    """Catálogo de insumos usados en mantención."""
    insumos = Insumo.objects.order_by('nombre')
    return render(request, 'insumos/insumos.html', {'insumos': insumos})


def crear_insumo(request):
    """Crea un insumo en el catálogo."""
    if request.method == 'POST':
        form = InsumoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('insumos:insumos')
    else:
        form = InsumoForm()
    return render(request, 'insumos/crear_insumo.html', {'form': form})

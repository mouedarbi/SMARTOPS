from django import forms
from .models import Building

class BuildingForm(forms.ModelForm):
    """
    Formulaire pour la création et l'édition d'un bâtiment.
    """
    class Meta:
        model = Building
        fields = ['client', 'name', 'address']
        widgets = {
            'client': forms.Select(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl'}),
            'address': forms.Textarea(attrs={'class': 'w-full p-3 border border-slate-200 rounded-xl', 'rows': 2}),
        }

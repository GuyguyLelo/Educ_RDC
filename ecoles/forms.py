"""
Formulaires — StructureOrganisationnelle et spécialisations (héritage).
"""
from django import forms

from .models import (
    StructureOrganisationnelle,
    ProvinceAdministrative,
    ProvinceEducationnelle,
    Antenne,
)


class StructureBaseForm(forms.ModelForm):
    """Champs communs hérités de StructureOrganisationnelle."""

    class Meta:
        model = StructureOrganisationnelle
        fields = ['nom', 'code', 'actif']
        widgets = {
            'nom': forms.TextInput(attrs={
                'placeholder': 'Ex: Kinshasa',
                'required': True,
            }),
            'code': forms.TextInput(attrs={
                'placeholder': 'Ex: KIN',
                'maxlength': 20,
                'required': True,
            }),
            'actif': forms.CheckboxInput(),
        }

    def clean_code(self):
        code = (self.cleaned_data.get('code') or '').strip().upper()
        if not code:
            raise forms.ValidationError('Le code est obligatoire.')
        qs = StructureOrganisationnelle.objects.filter(code__iexact=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(
                'Ce code est déjà utilisé par une autre structure (PA, PE ou antenne).'
            )
        return code

    def clean_nom(self):
        nom = (self.cleaned_data.get('nom') or '').strip()
        if not nom:
            raise forms.ValidationError('Le nom est obligatoire.')
        return nom


class ProvinceAdministrativeForm(StructureBaseForm):
    """Formulaire — Province administrative."""

    class Meta(StructureBaseForm.Meta):
        model = ProvinceAdministrative


class ProvinceEducationnelleForm(StructureBaseForm):
    """Formulaire — Province éducationnelle."""

    class Meta(StructureBaseForm.Meta):
        model = ProvinceEducationnelle
        fields = ['nom', 'code', 'province_administrative', 'actif']
        widgets = {
            **StructureBaseForm.Meta.widgets,
            'province_administrative': forms.Select(attrs={'required': True}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['province_administrative'].queryset = (
            ProvinceAdministrative.objects.filter(actif=True).order_by('nom')
        )
        self.fields['province_administrative'].empty_label = '— Choisir une province admin. —'


class AntenneForm(StructureBaseForm):
    """Formulaire — Antenne."""

    class Meta(StructureBaseForm.Meta):
        model = Antenne
        fields = [
            'nom', 'code', 'province_educationnelle',
            'adresse', 'telephone', 'actif',
        ]
        widgets = {
            **StructureBaseForm.Meta.widgets,
            'province_educationnelle': forms.Select(attrs={'required': True}),
            'adresse': forms.TextInput(attrs={
                'placeholder': 'Adresse de l’antenne',
            }),
            'telephone': forms.TextInput(attrs={
                'placeholder': '+243 …',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['province_educationnelle'].queryset = (
            ProvinceEducationnelle.objects.filter(actif=True)
            .select_related('province_administrative')
            .order_by('nom')
        )
        self.fields['province_educationnelle'].empty_label = '— Choisir une province éduc. —'


class StructureOrganisationnelleForm(forms.Form):
    """
    Formulaire unique avec choix du type (héritage).
    Crée l’instance concrète : PA, PE ou Antenne.
    """

    TYPE_PA = 'province_administrative'
    TYPE_PE = 'province_educationnelle'
    TYPE_ANTENNE = 'antenne'

    TYPE_CHOICES = [
        (TYPE_PA, 'Province administrative'),
        (TYPE_PE, 'Province éducationnelle'),
        (TYPE_ANTENNE, 'Antenne'),
    ]

    type_structure = forms.ChoiceField(
        label='Type de structure',
        choices=TYPE_CHOICES,
        widget=forms.Select(attrs={'id': 'id_type_structure'}),
    )
    nom = forms.CharField(
        label='Nom',
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Ex: Kinshasa'}),
    )
    code = forms.CharField(
        label='Code',
        max_length=20,
        widget=forms.TextInput(attrs={
            'placeholder': 'Ex: KIN',
            'style': 'text-transform:uppercase',
        }),
    )
    actif = forms.BooleanField(
        label='Actif',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(),
    )
    province_administrative = forms.ModelChoiceField(
        label='Province administrative',
        queryset=ProvinceAdministrative.objects.none(),
        required=False,
        empty_label='— Choisir —',
        widget=forms.Select(attrs={'id': 'id_province_administrative'}),
    )
    province_educationnelle = forms.ModelChoiceField(
        label='Province éducationnelle',
        queryset=ProvinceEducationnelle.objects.none(),
        required=False,
        empty_label='— Choisir —',
        widget=forms.Select(attrs={'id': 'id_province_educationnelle'}),
    )
    adresse = forms.CharField(
        label='Adresse',
        max_length=255,
        required=False,
        widget=forms.TextInput(),
    )
    telephone = forms.CharField(
        label='Téléphone',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '+243 …'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['province_administrative'].queryset = (
            ProvinceAdministrative.objects.filter(actif=True).order_by('nom')
        )
        self.fields['province_educationnelle'].queryset = (
            ProvinceEducationnelle.objects.filter(actif=True)
            .select_related('province_administrative')
            .order_by('nom')
        )

    def clean_code(self):
        code = (self.cleaned_data.get('code') or '').strip().upper()
        if not code:
            raise forms.ValidationError('Le code est obligatoire.')
        if StructureOrganisationnelle.objects.filter(code__iexact=code).exists():
            raise forms.ValidationError(
                'Ce code est déjà utilisé par une autre structure (PA, PE ou antenne).'
            )
        return code

    def clean(self):
        cleaned = super().clean()
        type_structure = cleaned.get('type_structure')
        if type_structure == self.TYPE_PE and not cleaned.get('province_administrative'):
            self.add_error(
                'province_administrative',
                'Obligatoire pour une province éducationnelle.',
            )
        if type_structure == self.TYPE_ANTENNE and not cleaned.get('province_educationnelle'):
            self.add_error(
                'province_educationnelle',
                'Obligatoire pour une antenne.',
            )
        return cleaned

    def save(self):
        """Crée l’instance héritée selon le type choisi."""
        data = self.cleaned_data
        type_structure = data['type_structure']
        communs = {
            'nom': data['nom'].strip(),
            'code': data['code'],
            'actif': data.get('actif', True),
        }

        if type_structure == self.TYPE_PA:
            return ProvinceAdministrative.objects.create(**communs)

        if type_structure == self.TYPE_PE:
            return ProvinceEducationnelle.objects.create(
                **communs,
                province_administrative=data['province_administrative'],
            )

        return Antenne.objects.create(
            **communs,
            province_educationnelle=data['province_educationnelle'],
            adresse=data.get('adresse') or '',
            telephone=data.get('telephone') or '',
        )

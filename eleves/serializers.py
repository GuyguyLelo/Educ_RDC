"""Serializers élèves."""
from rest_framework import serializers
from .models import Eleve


class EleveSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)
    ecole_nom = serializers.CharField(source='ecole.nom', read_only=True)
    ecole_code = serializers.CharField(source='ecole.code', read_only=True)
    province_nom = serializers.CharField(source='ecole.province.nom', read_only=True)
    antenne_nom = serializers.CharField(source='ecole.antenne.nom', read_only=True)
    sexe_display = serializers.CharField(source='get_sexe_display', read_only=True)
    photo_url = serializers.SerializerMethodField()
    a_photo = serializers.SerializerMethodField()

    class Meta:
        model = Eleve
        fields = [
            'id', 'matricule', 'nom', 'postnom', 'prenom', 'nom_complet',
            'date_naissance', 'lieu_naissance', 'sexe', 'sexe_display',
            'ecole', 'ecole_nom', 'ecole_code', 'province_nom', 'antenne_nom',
            'classe', 'adresse', 'nom_tuteur', 'telephone_tuteur',
            'photo', 'photo_url', 'a_photo', 'actif', 'date_inscription',
        ]
        read_only_fields = ['photo_url', 'a_photo']
        extra_kwargs = {
            'photo': {'required': False, 'allow_null': True},
        }

    def get_photo_url(self, obj):
        photo = obj.get_photo()
        if not photo:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(photo.url)
        return photo.url

    def get_a_photo(self, obj):
        return bool(obj.get_photo())


class EleveDetailSerializer(EleveSerializer):
    """Détail enrichi : biométrie, enrôlements, cartes."""
    biometrie = serializers.SerializerMethodField()
    enrolements = serializers.SerializerMethodField()
    cartes = serializers.SerializerMethodField()

    class Meta(EleveSerializer.Meta):
        fields = EleveSerializer.Meta.fields + [
            'biometrie', 'enrolements', 'cartes', 'date_modification',
        ]

    def get_biometrie(self, obj):
        bio = getattr(obj, 'biometrie', None)
        if not bio:
            return None
        request = self.context.get('request')
        photo_url = None
        if bio.photo:
            photo_url = request.build_absolute_uri(bio.photo.url) if request else bio.photo.url
        return {
            'id': bio.id,
            'photo_url': photo_url,
            'empreinte_hash': bio.empreinte_hash,
            'validee': bio.validee,
            'date_capture': bio.date_capture,
            'observations': bio.observations,
        }

    def get_enrolements(self, obj):
        return [
            {
                'id': e.id,
                'annee_scolaire': e.annee_scolaire,
                'statut': e.statut,
                'statut_display': e.get_statut_display(),
                'date_enrolement': e.date_enrolement,
            }
            for e in obj.enrolements.all()[:10]
        ]

    def get_cartes(self, obj):
        request = self.context.get('request')
        result = []
        for c in obj.cartes.all()[:10]:
            qr = None
            if c.qr_code:
                qr = request.build_absolute_uri(c.qr_code.url) if request else c.qr_code.url
            result.append({
                'id': c.id,
                'numero_carte': c.numero_carte,
                'statut': c.statut,
                'statut_display': c.get_statut_display(),
                'date_emission': c.date_emission,
                'date_expiration': c.date_expiration,
                'qr_code_url': qr,
            })
        return result

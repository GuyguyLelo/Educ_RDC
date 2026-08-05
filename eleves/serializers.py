"""Serializers élèves."""
from rest_framework import serializers
from .models import Eleve


class EleveSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)
    nom_complet_pere = serializers.CharField(read_only=True)
    nom_complet_mere = serializers.CharField(read_only=True)
    ecole_nom = serializers.CharField(source='ecole.nom', read_only=True)
    ecole_code = serializers.CharField(source='ecole.code', read_only=True)
    province_nom = serializers.CharField(source='ecole.province_educationnelle.nom', read_only=True)
    antenne_nom = serializers.CharField(source='ecole.antenne.nom', read_only=True)
    province_administrative_nom = serializers.CharField(
        source='ecole.province_administrative.nom', read_only=True,
    )
    classe_nom = serializers.CharField(source='classe.nom', read_only=True, allow_null=True, default=None)
    sexe_display = serializers.CharField(source='get_sexe_display', read_only=True)
    lien_tuteur_display = serializers.CharField(source='get_lien_tuteur_display', read_only=True)
    photo_url = serializers.SerializerMethodField()
    a_photo = serializers.SerializerMethodField()
    photo_pere_url = serializers.SerializerMethodField()
    photo_mere_url = serializers.SerializerMethodField()
    photo_tuteur_url = serializers.SerializerMethodField()

    class Meta:
        model = Eleve
        fields = [
            'id', 'matricule', 'numero_identification', 'numero_permanent',
            'nom', 'postnom', 'prenom', 'nom_complet',
            'date_naissance', 'lieu_naissance', 'sexe', 'sexe_display',
            'ecole', 'ecole_nom', 'ecole_code',
            'province_nom', 'province_administrative_nom', 'antenne_nom',
            'classe', 'classe_nom', 'adresse',
            'nom_pere', 'postnom_pere', 'prenom_pere', 'nom_complet_pere',
            'telephone_pere', 'email_pere', 'profession_pere',
            'photo_pere', 'photo_pere_url',
            'nom_mere', 'postnom_mere', 'prenom_mere', 'nom_complet_mere',
            'telephone_mere', 'email_mere', 'profession_mere',
            'photo_mere', 'photo_mere_url',
            'nom_tuteur', 'telephone_tuteur', 'email_tuteur',
            'lien_tuteur', 'lien_tuteur_display',
            'photo_tuteur', 'photo_tuteur_url',
            'photo', 'photo_url', 'a_photo', 'actif', 'date_inscription',
        ]
        read_only_fields = [
            'photo_url', 'a_photo', 'classe_nom',
            'photo_pere_url', 'photo_mere_url', 'photo_tuteur_url',
            'nom_complet_pere', 'nom_complet_mere', 'lien_tuteur_display',
        ]
        extra_kwargs = {
            'photo': {'required': False, 'allow_null': True},
            'photo_pere': {'required': False, 'allow_null': True},
            'photo_mere': {'required': False, 'allow_null': True},
            'photo_tuteur': {'required': False, 'allow_null': True},
            'numero_identification': {'required': False, 'allow_blank': True, 'allow_null': True},
            'numero_permanent': {'required': False, 'allow_blank': True, 'allow_null': True},
            'classe': {'required': True, 'allow_null': False},
        }

    def _abs_url(self, file_field):
        if not file_field:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(file_field.url)
        return file_field.url

    def validate_numero_identification(self, value):
        value = (value or '').strip()
        return value or None

    def validate_numero_permanent(self, value):
        value = (value or '').strip()
        return value or None

    def validate(self, attrs):
        ecole = attrs.get('ecole') or getattr(self.instance, 'ecole', None)
        classe = attrs.get('classe') if 'classe' in attrs else getattr(self.instance, 'classe', None)
        if not classe:
            raise serializers.ValidationError({'classe': 'La classe est obligatoire.'})
        if ecole and classe and classe.ecole_id != ecole.id:
            raise serializers.ValidationError({
                'classe': "La classe doit appartenir à l'école de l'élève.",
            })
        return attrs

    def get_photo_url(self, obj):
        return self._abs_url(obj.get_photo())

    def get_a_photo(self, obj):
        return bool(obj.get_photo())

    def get_photo_pere_url(self, obj):
        return self._abs_url(obj.photo_pere)

    def get_photo_mere_url(self, obj):
        return self._abs_url(obj.photo_mere)

    def get_photo_tuteur_url(self, obj):
        return self._abs_url(obj.photo_tuteur)


class EleveDetailSerializer(EleveSerializer):
    """Détail enrichi : biométrie et cartes."""
    biometrie = serializers.SerializerMethodField()
    cartes = serializers.SerializerMethodField()

    class Meta(EleveSerializer.Meta):
        fields = EleveSerializer.Meta.fields + [
            'biometrie', 'cartes', 'date_modification',
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
            'observations': getattr(bio, 'observations', ''),
        }

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

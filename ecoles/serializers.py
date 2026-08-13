"""Serializers écoles / structures hiérarchiques."""
from rest_framework import serializers
from .models import (
    StructureOrganisationnelle,
    ProvinceAdministrative,
    ProvinceEducationnelle,
    Antenne,
    Arrete,
    Ecole,
    SectionScolaire,
    OptionScolaire,
    Classe,
    PhotoEcole,
    DocumentEcole,
    PersonnelEcole,
)


class StructureOrganisationnelleSerializer(serializers.ModelSerializer):
    type_structure = serializers.CharField(read_only=True)

    class Meta:
        model = StructureOrganisationnelle
        fields = [
            'id', 'nom', 'code', 'actif', 'type_structure',
            'date_creation', 'date_modification',
        ]


class ProvinceAdministrativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProvinceAdministrative
        fields = [
            'id', 'nom', 'code', 'actif',
            'date_creation', 'date_modification',
        ]
        read_only_fields = ['date_creation', 'date_modification']
        extra_kwargs = {
            'code': {'validators': []},
        }

    def validate_code(self, value):
        code = (value or '').strip().upper()
        if not code:
            raise serializers.ValidationError('Le code est obligatoire.')
        qs = StructureOrganisationnelle.objects.filter(code__iexact=code)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'Ce code est déjà utilisé par une autre structure (PA, PE ou antenne).'
            )
        return code

    def create(self, validated_data):
        validated_data['code'] = validated_data['code'].strip().upper()
        return ProvinceAdministrative.objects.create(**validated_data)

    def update(self, instance, validated_data):
        if 'code' in validated_data:
            validated_data['code'] = validated_data['code'].strip().upper()
        return super().update(instance, validated_data)


class ProvinceEducationnelleSerializer(serializers.ModelSerializer):
    province_administrative_nom = serializers.CharField(
        source='province_administrative.nom', read_only=True,
    )

    class Meta:
        model = ProvinceEducationnelle
        fields = [
            'id', 'nom', 'code', 'actif',
            'province_administrative', 'province_administrative_nom',
            'date_creation', 'date_modification',
        ]


class AntenneSerializer(serializers.ModelSerializer):
    province_educationnelle_nom = serializers.CharField(
        source='province_educationnelle.nom', read_only=True,
    )
    province_administrative_nom = serializers.CharField(
        source='province_administrative.nom', read_only=True,
    )
    province_administrative_id = serializers.IntegerField(
        source='province_administrative.id', read_only=True,
    )

    class Meta:
        model = Antenne
        fields = [
            'id', 'nom', 'code', 'actif',
            'province_educationnelle', 'province_educationnelle_nom',
            'province_administrative_id', 'province_administrative_nom',
            'adresse', 'telephone',
            'date_creation', 'date_modification',
        ]


class PhotoEcoleSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PhotoEcole
        fields = ['id', 'ecole', 'image', 'image_url', 'legende', 'est_principale', 'date_ajout']
        read_only_fields = ['date_ajout']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if not obj.image:
            return None
        url = obj.image.url
        if request:
            return request.build_absolute_uri(url)
        return url


class DocumentEcoleSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_document_display', read_only=True)
    fichier_url = serializers.SerializerMethodField()
    nom_fichier = serializers.CharField(read_only=True)
    arrete_numero = serializers.CharField(source='arrete.numero', read_only=True, default=None)

    class Meta:
        model = DocumentEcole
        fields = [
            'id', 'ecole', 'type_document', 'type_display', 'titre',
            'fichier', 'fichier_url', 'nom_fichier', 'arrete', 'arrete_numero',
            'date_document', 'date_ajout',
        ]
        read_only_fields = ['date_ajout', 'nom_fichier']

    def get_fichier_url(self, obj):
        request = self.context.get('request')
        if not obj.fichier:
            return None
        url = obj.fichier.url
        if request:
            return request.build_absolute_uri(url)
        return url


class ArreteSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_arrete_display', read_only=True)
    fichier_url = serializers.SerializerMethodField()
    nom_fichier = serializers.SerializerMethodField()
    nombre_ecoles = serializers.IntegerField(read_only=True)

    class Meta:
        model = Arrete
        fields = [
            'id', 'numero', 'objet', 'type_arrete', 'type_display',
            'date_arrete', 'signataire', 'autorite', 'description',
            'fichier', 'fichier_url', 'nom_fichier',
            'actif', 'nombre_ecoles', 'date_creation', 'date_modification',
        ]
        read_only_fields = ['date_creation', 'date_modification', 'nombre_ecoles']
        extra_kwargs = {
            'fichier': {'required': False, 'allow_null': True},
        }

    def get_fichier_url(self, obj):
        request = self.context.get('request')
        if not obj.fichier:
            return None
        url = obj.fichier.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_nom_fichier(self, obj):
        if not obj.fichier:
            return ''
        return obj.fichier.name.rsplit('/', 1)[-1]

    def validate_numero(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('Le N° référence est obligatoire.')
        qs = Arrete.objects.filter(numero__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Un document avec ce N° référence existe déjà.')
        return value


class EcoleOptionSerializer(serializers.ModelSerializer):
    """Liste légère pour sélecteurs (sans photos ni agrégats)."""

    class Meta:
        model = Ecole
        fields = ['id', 'nom', 'code', 'niveau', 'active']


class EcoleSerializer(serializers.ModelSerializer):
    province_educationnelle_nom = serializers.CharField(
        source='province_educationnelle.nom', read_only=True,
    )
    province_administrative_nom = serializers.CharField(
        source='province_administrative.nom', read_only=True,
    )
    province_administrative_id = serializers.IntegerField(
        source='province_administrative.id', read_only=True,
    )
    antenne_nom = serializers.CharField(source='antenne.nom', read_only=True)
    type_display = serializers.CharField(source='get_type_ecole_display', read_only=True)
    niveau_display = serializers.CharField(source='get_niveau_display', read_only=True)
    nombre_eleves = serializers.IntegerField(read_only=True)
    nombre_personnels = serializers.IntegerField(read_only=True)
    # Alias pour compatibilité frontend
    province_nom = serializers.CharField(source='province_educationnelle.nom', read_only=True)
    province = serializers.IntegerField(source='province_educationnelle_id', read_only=True)
    photos = PhotoEcoleSerializer(many=True, read_only=True)
    documents = DocumentEcoleSerializer(many=True, read_only=True)
    photo_principale_url = serializers.SerializerMethodField()
    maps_url = serializers.SerializerMethodField()
    arrete_numero = serializers.CharField(source='arrete.numero', read_only=True, default=None)
    arrete_objet = serializers.CharField(source='arrete.objet', read_only=True, default=None)

    class Meta:
        model = Ecole
        fields = [
            'id', 'nom', 'code', 'numero_agrement', 'arrete', 'arrete_numero', 'arrete_objet',
            'type_ecole', 'type_display', 'niveau',
            'niveau_display', 'adresse', 'telephone', 'email',
            'latitude', 'longitude', 'maps_url',
            'directeur',
            'effectif_mat', 'effectif_prim', 'effectif_sec', 'effectifs',
            'province_educationnelle', 'province_educationnelle_nom',
            'province_administrative_id', 'province_administrative_nom',
            'province', 'province_nom',
            'antenne', 'antenne_nom',
            'photos', 'documents', 'photo_principale_url',
            'active', 'nombre_eleves', 'nombre_personnels', 'date_creation',
        ]
        extra_kwargs = {
            'arrete': {'required': False, 'allow_null': True},
        }

    def create(self, validated_data):
        arrete = validated_data.get('arrete')
        if arrete and not validated_data.get('numero_agrement'):
            validated_data['numero_agrement'] = arrete.numero
        return super().create(validated_data)

    def update(self, instance, validated_data):
        arrete = validated_data.get('arrete', serializers.empty)
        if arrete is not serializers.empty and arrete and not validated_data.get('numero_agrement'):
            if not instance.numero_agrement or instance.numero_agrement == getattr(instance.arrete, 'numero', None):
                validated_data['numero_agrement'] = arrete.numero
        return super().update(instance, validated_data)

    def get_photo_principale_url(self, obj):
        photo = obj.photo_principale
        if not photo or not photo.image:
            return None
        request = self.context.get('request')
        url = photo.image.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_maps_url(self, obj):
        if obj.latitude is None or obj.longitude is None:
            return None
        return f'https://www.google.com/maps?q={obj.latitude},{obj.longitude}'


class SectionScolaireSerializer(serializers.ModelSerializer):
    ecole_nom = serializers.CharField(source='ecole.nom', read_only=True)
    nb_options = serializers.SerializerMethodField()

    class Meta:
        model = SectionScolaire
        fields = [
            'id', 'ecole', 'ecole_nom', 'nom', 'code', 'active',
            'nb_options', 'date_creation',
        ]
        read_only_fields = ['date_creation']

    def get_nb_options(self, obj):
        return obj.options.filter(active=True).count()


class OptionScolaireSerializer(serializers.ModelSerializer):
    section_nom = serializers.CharField(source='section.nom', read_only=True)
    ecole = serializers.IntegerField(source='section.ecole_id', read_only=True)

    class Meta:
        model = OptionScolaire
        fields = [
            'id', 'section', 'section_nom', 'ecole',
            'nom', 'code', 'active', 'date_creation',
        ]
        read_only_fields = ['date_creation']


class ClasseSerializer(serializers.ModelSerializer):
    ecole_nom = serializers.CharField(source='ecole.nom', read_only=True)
    ecole_code = serializers.CharField(source='ecole.code', read_only=True)
    section_nom = serializers.SerializerMethodField()
    option_nom = serializers.SerializerMethodField()
    nb_eleves = serializers.SerializerMethodField()

    class Meta:
        model = Classe
        fields = [
            'id', 'ecole', 'ecole_nom', 'ecole_code',
            'section', 'section_nom', 'option', 'option_nom',
            'nom', 'code', 'active', 'nb_eleves', 'date_creation',
        ]
        read_only_fields = ['date_creation']

    def get_section_nom(self, obj):
        return obj.section.nom if obj.section_id else ''

    def get_option_nom(self, obj):
        return obj.option.nom if obj.option_id else ''

    def get_nb_eleves(self, obj):
        return obj.eleves.filter(actif=True).count()

    def validate(self, attrs):
        ecole = attrs.get('ecole') or getattr(self.instance, 'ecole', None)
        nom = (attrs.get('nom') or getattr(self.instance, 'nom', '') or '').strip()
        option = attrs.get('option', getattr(self.instance, 'option', None) if self.instance else None)
        section = attrs.get('section', getattr(self.instance, 'section', None) if self.instance else None)
        if option and ecole and option.section.ecole_id != ecole.id:
            raise serializers.ValidationError({'option': 'Option hors de cette école.'})
        if option and section and option.section_id != section.id:
            raise serializers.ValidationError({'option': "L'option ne correspond pas à la section."})
        if option and not section:
            attrs['section'] = option.section
        if ecole and nom:
            qs = Classe.objects.filter(ecole=ecole, nom__iexact=nom)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({
                    'nom': 'Cette classe existe déjà pour cette école.',
                })
        return attrs


class PersonnelEcoleSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)
    fonction_display = serializers.CharField(source='get_fonction_display', read_only=True)
    sexe_display = serializers.CharField(source='get_sexe_display', read_only=True)
    ecole_nom = serializers.CharField(source='ecole.nom', read_only=True)
    ecole_code = serializers.CharField(source='ecole.code', read_only=True)
    a_compte = serializers.SerializerMethodField()
    utilisateur_username = serializers.CharField(
        source='utilisateur.username', read_only=True, allow_null=True, default=None,
    )

    class Meta:
        model = PersonnelEcole
        fields = [
            'id', 'ecole', 'ecole_nom', 'ecole_code',
            'utilisateur', 'a_compte', 'utilisateur_username',
            'matricule', 'reference_acte_engagement',
            'nom', 'postnom', 'prenom', 'nom_complet',
            'sexe', 'sexe_display', 'fonction', 'fonction_display',
            'telephone', 'email', 'date_naissance', 'date_prise_service',
            'actif', 'date_creation',
        ]
        read_only_fields = ['utilisateur', 'a_compte', 'utilisateur_username']

    def get_a_compte(self, obj):
        return bool(obj.utilisateur_id)

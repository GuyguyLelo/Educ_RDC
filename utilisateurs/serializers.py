"""Serializers utilisateurs."""
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Utilisateur


def _valider_rattachement_scolaire(attrs, instance=None):
    role = attrs.get('role', getattr(instance, 'role', None))
    ecole = attrs.get('ecole', getattr(instance, 'ecole', None))
    classe = attrs.get('classe', getattr(instance, 'classe', None) if instance else None)
    if role in Utilisateur.ROLES_ECOLE and not ecole:
        raise serializers.ValidationError({
            'ecole': "L'école est obligatoire pour un administratif ou un enseignant.",
        })
    if role == Utilisateur.Role.ENSEIGNANT:
        if not classe:
            raise serializers.ValidationError({
                'classe': "Sélectionnez la classe dont l'enseignant est titulaire.",
            })
        if ecole and classe.ecole_id != ecole.id:
            raise serializers.ValidationError({
                'classe': "La classe doit appartenir à l'école sélectionnée.",
            })
        if not getattr(classe, 'section_id', None):
            raise serializers.ValidationError({
                'classe': "La classe de l'enseignant doit être rattachée à une section (et option si applicable).",
            })
    return attrs


class UtilisateurSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    province_administrative_nom = serializers.CharField(
        source='province_administrative.nom', read_only=True, allow_null=True, default=None,
    )
    province_educationnelle_nom = serializers.CharField(
        source='province_educationnelle.nom', read_only=True, allow_null=True, default=None,
    )
    antenne_nom = serializers.CharField(
        source='antenne.nom', read_only=True, allow_null=True, default=None,
    )
    ecole_nom = serializers.CharField(
        source='ecole.nom', read_only=True, allow_null=True, default=None,
    )
    ecole_code = serializers.CharField(
        source='ecole.code', read_only=True, allow_null=True, default=None,
    )
    classe_nom = serializers.CharField(
        source='classe.nom', read_only=True, allow_null=True, default=None,
    )
    section = serializers.SerializerMethodField()
    section_nom = serializers.SerializerMethodField()
    option = serializers.SerializerMethodField()
    option_nom = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Utilisateur
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_display', 'telephone',
            'province_administrative', 'province_administrative_nom',
            'province_educationnelle', 'province_educationnelle_nom',
            'antenne', 'antenne_nom',
            'ecole', 'ecole_nom', 'ecole_code',
            'classe', 'classe_nom',
            'section', 'section_nom', 'option', 'option_nom',
            'photo', 'photo_url',
            'is_active', 'date_creation', 'password',
        ]
        read_only_fields = [
            'date_creation', 'classe_nom',
            'section', 'section_nom', 'option', 'option_nom',
            'photo_url',
        ]
        extra_kwargs = {
            'photo': {'required': False, 'allow_null': True, 'write_only': True},
        }

    def get_photo_url(self, obj):
        if not obj.photo:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.photo.url)
        return obj.photo.url

    def get_section(self, obj):
        return obj.classe.section_id if obj.classe_id else None

    def get_section_nom(self, obj):
        if not obj.classe_id or not getattr(obj.classe, 'section_id', None):
            return None
        return obj.classe.section.nom

    def get_option(self, obj):
        return obj.classe.option_id if obj.classe_id else None

    def get_option_nom(self, obj):
        if not obj.classe_id or not getattr(obj.classe, 'option_id', None):
            return None
        return obj.classe.option.nom

    def validate(self, attrs):
        return _valider_rattachement_scolaire(attrs, self.instance)

    def validate_password(self, value):
        if value:
            validate_password(value)
        return value

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class ProfilSerializer(serializers.ModelSerializer):
    """Mise à jour du profil par l'utilisateur connecté (champs limités)."""

    role_display = serializers.CharField(source='get_role_display', read_only=True)
    ecole_nom = serializers.CharField(source='ecole.nom', read_only=True, allow_null=True, default=None)
    classe_nom = serializers.CharField(source='classe.nom', read_only=True, allow_null=True, default=None)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Utilisateur
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'telephone',
            'role', 'role_display', 'ecole_nom', 'classe_nom',
            'photo_url',
        ]
        read_only_fields = [
            'id', 'username', 'first_name', 'last_name',
            'role', 'role_display', 'ecole_nom', 'classe_nom', 'photo_url',
        ]

    def get_photo_url(self, obj):
        if not obj.photo:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.photo.url)
        return obj.photo.url


class ChangerMotDePasseSerializer(serializers.Serializer):
    mot_de_passe_actuel = serializers.CharField(write_only=True)
    nouveau_mot_de_passe = serializers.CharField(write_only=True)
    confirmation = serializers.CharField(write_only=True)

    def validate_nouveau_mot_de_passe(self, value):
        validate_password(value, user=self.context.get('user'))
        return value

    def validate(self, attrs):
        if attrs['nouveau_mot_de_passe'] != attrs['confirmation']:
            raise serializers.ValidationError({
                'confirmation': 'La confirmation ne correspond pas au nouveau mot de passe.',
            })
        user = self.context.get('user')
        if user and not user.check_password(attrs['mot_de_passe_actuel']):
            raise serializers.ValidationError({
                'mot_de_passe_actuel': 'Mot de passe actuel incorrect.',
            })
        return attrs


class UtilisateurCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    personnel = serializers.IntegerField(
        write_only=True,
        required=False,
        allow_null=True,
        help_text='Fiche Personnel existante (obligatoire pour un enseignant).',
    )

    class Meta:
        model = Utilisateur
        fields = [
            'id', 'username', 'email', 'password', 'first_name', 'last_name',
            'role', 'telephone',
            'province_administrative', 'province_educationnelle', 'antenne',
            'ecole', 'classe', 'personnel', 'is_active',
        ]

    def validate(self, attrs):
        attrs = _valider_rattachement_scolaire(attrs)
        role = attrs.get('role')
        personnel_id = attrs.get('personnel')
        ecole = attrs.get('ecole')
        # Section / option / classe : uniquement via le rattachement classe enseignant
        if role != Utilisateur.Role.ENSEIGNANT:
            attrs['classe'] = None
        if personnel_id or role == Utilisateur.Role.ENSEIGNANT:
            if role == Utilisateur.Role.ENSEIGNANT and not personnel_id:
                raise serializers.ValidationError({
                    'personnel': (
                        "Créez d'abord la fiche Personnel enseignant, puis sélectionnez-la "
                        "pour ouvrir le compte."
                    ),
                })
            if personnel_id:
                from ecoles.models import PersonnelEcole
                personnel = PersonnelEcole.objects.filter(pk=personnel_id).first()
                if not personnel:
                    raise serializers.ValidationError({'personnel': 'Fiche personnel introuvable.'})
                if ecole and personnel.ecole_id != ecole.id:
                    raise serializers.ValidationError({
                        'personnel': "La fiche personnel doit appartenir à l'école du compte.",
                    })
                if personnel.utilisateur_id:
                    raise serializers.ValidationError({
                        'personnel': 'Cette fiche personnel a déjà un compte associé.',
                    })
                if role == Utilisateur.Role.ENSEIGNANT and personnel.fonction != PersonnelEcole.Fonction.ENSEIGNANT:
                    raise serializers.ValidationError({
                        'personnel': (
                            "Seule une fiche à fonction « Enseignant(e) » peut ouvrir "
                            "un compte enseignant (section, option, classe)."
                        ),
                    })
                attrs['_personnel_obj'] = personnel
        return attrs

    def create(self, validated_data):
        personnel = validated_data.pop('_personnel_obj', None)
        validated_data.pop('personnel', None)
        password = validated_data.pop('password')
        # Identité depuis la fiche personnel (source de vérité)
        if personnel is not None:
            validated_data['first_name'] = (personnel.prenom or '').strip()
            validated_data['last_name'] = ' '.join(
                p for p in [personnel.nom, personnel.postnom] if (p or '').strip()
            ).strip() or (personnel.nom or '').strip()
            if personnel.email and not validated_data.get('email'):
                validated_data['email'] = personnel.email
            if personnel.telephone and not validated_data.get('telephone'):
                validated_data['telephone'] = personnel.telephone
        user = Utilisateur(**validated_data)
        user.set_password(password)
        user.save()
        if personnel is not None:
            from ecoles.services_personnel import lier_personnel_a_utilisateur
            lier_personnel_a_utilisateur(personnel, user)
        return user

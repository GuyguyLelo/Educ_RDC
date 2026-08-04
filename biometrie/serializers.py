"""Serializers biométrie."""
from rest_framework import serializers
from .models import Biometrie


class BiometrieSerializer(serializers.ModelSerializer):
    eleve_nom = serializers.CharField(source='eleve.nom_complet', read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Biometrie
        fields = [
            'id', 'eleve', 'eleve_nom', 'photo', 'photo_url',
            'empreinte_hash', 'date_capture', 'validee', 'observations',
        ]

    def get_photo_url(self, obj):
        request = self.context.get('request')
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        if obj.photo:
            return obj.photo.url
        return None

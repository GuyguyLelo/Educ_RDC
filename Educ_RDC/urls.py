"""
URLs principales — Educ_RDC
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from utilisateurs.views import UtilisateurViewSet, CustomTokenObtainPairView
from ecoles.views import (
    ProvinceAdministrativeViewSet,
    ProvinceEducationnelleViewSet,
    AntenneViewSet,
    EcoleViewSet,
    PersonnelEcoleViewSet,
)
from eleves.views import EleveViewSet
from biometrie.views import BiometrieViewSet
from enrolement.views import EnrolementViewSet
from cartes.views import CarteViewSet
from paiements.views import PaiementViewSet
from rapports.views import statistiques_dashboard, export_rapport_pdf
from administration import views as admin_views

# Router API REST
router = DefaultRouter()
router.register(r'utilisateurs', UtilisateurViewSet, basename='utilisateur')
router.register(r'provinces-administratives', ProvinceAdministrativeViewSet, basename='province-administrative')
router.register(r'provinces-educationnelles', ProvinceEducationnelleViewSet, basename='province-educationnelle')
router.register(r'provinces', ProvinceAdministrativeViewSet, basename='province')  # alias
router.register(r'antennes', AntenneViewSet, basename='antenne')
router.register(r'ecoles', EcoleViewSet, basename='ecole')
router.register(r'personnels', PersonnelEcoleViewSet, basename='personnel')
router.register(r'eleves', EleveViewSet, basename='eleve')
router.register(r'biometrie', BiometrieViewSet, basename='biometrie')
router.register(r'enrolements', EnrolementViewSet, basename='enrolement')
router.register(r'cartes', CarteViewSet, basename='carte')
router.register(r'paiements', PaiementViewSet, basename='paiement')

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentification pages
    path('', admin_views.vue_login, name='login'),
    path('logout/', admin_views.vue_logout, name='logout'),
    path('dashboard/', admin_views.vue_dashboard, name='dashboard'),
    path('ecoles/', admin_views.vue_ecoles, name='ecoles'),
    path('ecoles/<int:ecole_id>/', admin_views.vue_ecole_detail, name='ecole_detail'),
    path('eleves/', admin_views.vue_eleves, name='eleves'),
    path('eleves/<int:eleve_id>/', admin_views.vue_eleve_detail, name='eleve_detail'),
    path('enrolement/', admin_views.vue_enrolement, name='enrolement'),
    path('cartes/', admin_views.vue_cartes, name='cartes'),
    path('rapports/', admin_views.vue_rapports, name='rapports'),
    path('parametres/', admin_views.vue_parametres, name='parametres'),
    path(
        'parametres/structure/nouvelle/',
        admin_views.vue_structure_formulaire,
        name='structure_nouvelle',
    ),

    # API JWT
    path('api/auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # API REST
    path('api/', include(router.urls)),
    path('api/stats/', statistiques_dashboard, name='api_stats'),
    path('api/rapports/pdf/', export_rapport_pdf, name='api_rapport_pdf'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

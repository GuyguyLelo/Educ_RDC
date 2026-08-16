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
from utilisateurs import webauthn_views
from ecoles.views import (
    ProvinceAdministrativeViewSet,
    ProvinceEducationnelleViewSet,
    AntenneViewSet,
    ArreteViewSet,
    EcoleViewSet,
    SectionScolaireViewSet,
    OptionScolaireViewSet,
    ClasseViewSet,
    PersonnelEcoleViewSet,
)
from eleves.views import EleveViewSet
from biometrie.views import BiometrieViewSet
from cartes.views import CarteViewSet
from paiements.views import PaiementViewSet
from rapports.views import statistiques_dashboard, export_rapport_pdf
from administration.api_monitoring import (
    MonitoringSessionsView,
    MonitoringSessionDetailView,
    PresenceGeoView,
    AccesExterieurListView,
    AccesExterieurDecisionView,
)
from evaluations.views import (
    AnneeScolaireViewSet,
    BulletinViewSet,
    MatiereViewSet,
    NoteViewSet,
    PeriodeEvaluationViewSet,
    ProgrammeClasseViewSet,
)
from administration import views as admin_views
from administration import import_modeles as admin_import_modeles

# Router API REST
router = DefaultRouter()
router.register(r'utilisateurs', UtilisateurViewSet, basename='utilisateur')
router.register(r'provinces-administratives', ProvinceAdministrativeViewSet, basename='province-administrative')
router.register(r'provinces-educationnelles', ProvinceEducationnelleViewSet, basename='province-educationnelle')
router.register(r'provinces', ProvinceAdministrativeViewSet, basename='province')  # alias
router.register(r'antennes', AntenneViewSet, basename='antenne')
router.register(r'arretes', ArreteViewSet, basename='arrete')
router.register(r'ecoles', EcoleViewSet, basename='ecole')
router.register(r'sections-scolaires', SectionScolaireViewSet, basename='section-scolaire')
router.register(r'options-scolaires', OptionScolaireViewSet, basename='option-scolaire')
router.register(r'classes', ClasseViewSet, basename='classe')
router.register(r'personnels', PersonnelEcoleViewSet, basename='personnel')
router.register(r'eleves', EleveViewSet, basename='eleve')
router.register(r'biometrie', BiometrieViewSet, basename='biometrie')
router.register(r'cartes', CarteViewSet, basename='carte')
router.register(r'paiements', PaiementViewSet, basename='paiement')
router.register(r'annees-scolaires', AnneeScolaireViewSet, basename='annee-scolaire')
router.register(r'periodes-evaluation', PeriodeEvaluationViewSet, basename='periode-evaluation')
router.register(r'matieres', MatiereViewSet, basename='matiere')
router.register(r'programmes-classe', ProgrammeClasseViewSet, basename='programme-classe')
router.register(r'notes', NoteViewSet, basename='note')
router.register(r'bulletins', BulletinViewSet, basename='bulletin')

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentification pages
    path('', admin_views.vue_login, name='login'),
    path('logout/', admin_views.vue_logout, name='logout'),
    path('api/auth/webauthn/status/', webauthn_views.webauthn_status, name='webauthn_status'),
    path('api/auth/webauthn/register/begin/', webauthn_views.webauthn_register_begin, name='webauthn_register_begin'),
    path('api/auth/webauthn/register/complete/', webauthn_views.webauthn_register_complete, name='webauthn_register_complete'),
    path('api/auth/webauthn/login/begin/', webauthn_views.webauthn_login_begin, name='webauthn_login_begin'),
    path('api/auth/webauthn/login/complete/', webauthn_views.webauthn_login_complete, name='webauthn_login_complete'),
    path('api/auth/webauthn/delete/', webauthn_views.webauthn_delete, name='webauthn_delete'),
    path('dashboard/', admin_views.vue_dashboard, name='dashboard'),
    path('ecoles/', admin_views.vue_ecoles, name='ecoles'),
    path('ecoles/<int:ecole_id>/', admin_views.vue_ecole_detail, name='ecole_detail'),
    path('eleves/', admin_views.vue_eleves, name='eleves'),
    path('eleves/<int:eleve_id>/', admin_views.vue_eleve_detail, name='eleve_detail'),
    path('evaluations/', admin_views.vue_evaluations, name='evaluations'),
    path('cartes/', admin_views.vue_cartes, name='cartes'),
    path('rapports/', admin_views.vue_rapports, name='rapports'),
    path('parametres/', admin_views.vue_parametres, name='parametres'),
    path(
        'parametres/structure-scolaire/',
        admin_views.vue_parametres_scolaire,
        name='parametres_scolaire',
    ),
    path(
        'parametres/annees-scolaires/',
        admin_views.vue_parametres_annees,
        name='parametres_annees',
    ),
    path(
        'parametres/gestion-documentaire/',
        admin_views.vue_parametres_gestion_documentaire,
        name='parametres_gestion_documentaire',
    ),
    # Alias historique
    path(
        'parametres/arretes/',
        admin_views.vue_parametres_gestion_documentaire,
        name='parametres_arretes',
    ),
    path(
        'parametres/structure/nouvelle/',
        admin_views.vue_structure_formulaire,
        name='structure_nouvelle',
    ),
    path('utilisateurs/', admin_views.vue_utilisateurs, name='utilisateurs'),
    path(
        'utilisateurs/permissions/',
        admin_views.vue_gestion_permissions,
        name='gestion_permissions',
    ),
    path(
        'utilisateurs/permissions/pdf/',
        admin_views.vue_gestion_permissions_pdf,
        name='gestion_permissions_pdf',
    ),
    path(
        'utilisateurs/<int:utilisateur_id>/',
        admin_views.vue_utilisateur_detail,
        name='utilisateur_detail',
    ),
    path(
        'monitoring/utilisateurs-connectes/',
        admin_views.vue_monitoring_utilisateurs,
        name='monitoring_utilisateurs',
    ),
    path(
        'monitoring/utilisateurs-connectes/carte/',
        admin_views.vue_monitoring_utilisateurs_carte,
        name='monitoring_utilisateurs_carte',
    ),

    # API JWT
    path('api/auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # API REST
    path('api/', include(router.urls)),
    path('api/stats/', statistiques_dashboard, name='api_stats'),
    path('api/rapports/pdf/', export_rapport_pdf, name='api_rapport_pdf'),
    path(
        'api/monitoring/sessions/',
        MonitoringSessionsView.as_view(),
        name='api_monitoring_sessions',
    ),
    path(
        'api/monitoring/sessions/<str:session_key>/',
        MonitoringSessionDetailView.as_view(),
        name='api_monitoring_session_detail',
    ),
    path(
        'api/monitoring/presence-geo/',
        PresenceGeoView.as_view(),
        name='api_monitoring_presence_geo',
    ),
    path(
        'api/monitoring/acces-exterieur/',
        AccesExterieurListView.as_view(),
        name='api_monitoring_acces_exterieur',
    ),
    path(
        'api/monitoring/acces-exterieur/<int:pk>/',
        AccesExterieurDecisionView.as_view(),
        name='api_monitoring_acces_exterieur_decision',
    ),
    path(
        'api/modeles-import/',
        admin_import_modeles.api_liste_modeles_import,
        name='api_modeles_import',
    ),
    path(
        'api/modeles-import/<slug:cle>/',
        admin_import_modeles.api_telecharger_modele_import,
        name='api_modele_import_detail',
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

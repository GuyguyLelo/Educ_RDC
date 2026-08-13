"""API Évaluation — notes, programmes, bulletins."""
from decimal import Decimal

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response

from ecoles.models import Classe
from eleves.models import Eleve
from .defaults import (
    creer_periodes_pour_annee,
    matieres_queryset_pour_classe,
    synchroniser_matieres_ecole,
)
from .models import (
    AnneeScolaire,
    BulletinDecision,
    Matiere,
    Note,
    PeriodeEvaluation,
    ProgrammeClasse,
    VerrouillagePeriode,
)
from .serializers import (
    AnneeScolaireSerializer,
    BulletinDecisionSerializer,
    MatiereSerializer,
    NoteBulkSerializer,
    NoteSerializer,
    PeriodeEvaluationSerializer,
    ProgrammeClasseSerializer,
)
from .services import (
    actualiser_classement,
    calculer_bulletin_eleve,
    generer_pdf_bulletin,
    ids_periodes_verrouillees,
    maximum_periode,
    periode_est_verrouillee,
    verrouiller_periodes_anterieures,
)


class GestionEvaluation(BasePermission):
    """
    Lecture : authentifiés (filtrés dans get_queryset).
    Écriture notes : enseignant titulaire, admin_ecole, admin.
    Config matières / années : admin_ecole ou admin.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if user.est_admin or user.role == 'admin_ecole':
            return True
        if getattr(user, 'est_enseignant', False):
            # Notes et décisions de sa classe uniquement (vérifié dans perform_*)
            return view.action in (
                'create', 'update', 'partial_update', 'saisie_bulk',
                'destroy', 'classer', 'decision', 'ouvrir',
            )
        return user.role in ('agent_provincial', 'agent_antenne', 'agent_national')


def _scope_ecole_ids(user):
    if user.est_admin or user.est_national:
        return None
    if getattr(user, 'est_utilisateur_ecole', False) and user.ecole_id:
        return [user.ecole_id]
    if user.role == 'agent_antenne' and user.antenne_id:
        return list(
            Classe.objects.filter(ecole__antenne_id=user.antenne_id).values_list('ecole_id', flat=True).distinct()
        )
    if user.role == 'agent_provincial' and user.province_educationnelle_id:
        return list(
            Classe.objects.filter(
                ecole__province_educationnelle_id=user.province_educationnelle_id,
            ).values_list('ecole_id', flat=True).distinct()
        )
    return []


def _peut_saisir_classe(user, classe: Classe) -> bool:
    if user.est_admin:
        return True
    if user.role == 'admin_ecole' and user.ecole_id == classe.ecole_id:
        return True
    if getattr(user, 'est_enseignant', False) and user.classe_id == classe.id:
        return True
    return False


class PermissionAnneesScolaires(BasePermission):
    """Référentiel national : écriture réservée à l'admin / agent national."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return bool(user.est_admin or getattr(user, 'est_national', False))


class AnneeScolaireViewSet(viewsets.ModelViewSet):
    """
    Référentiel national des années scolaires.
    Lecture : tous les authentifiés. Écriture : national / admin.
    """
    serializer_class = AnneeScolaireSerializer
    permission_classes = [IsAuthenticated, GestionEvaluation]

    def get_queryset(self):
        from django.db.models import Count
        qs = (
            AnneeScolaire.objects
            .annotate(nb_periodes=Count('periodes'))
            .order_by('-date_debut', '-id')
        )
        active = self.request.query_params.get('active')
        if active in ('1', 'true', 'True'):
            qs = qs.filter(active=True)
        return qs

    def get_permissions(self):
        if self.action in (
            'create', 'update', 'partial_update', 'destroy',
            'init_periodes',
        ):
            return [IsAuthenticated(), PermissionAnneesScolaires()]
        return super().get_permissions()

    def perform_create(self, serializer):
        annee = serializer.save()
        creer_periodes_pour_annee(annee)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        annee = self.get_queryset().get(pk=serializer.instance.pk)
        out = self.get_serializer(annee)
        headers = self.get_success_headers(out.data)
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['get'], url_path='courante')
    def courante(self, request):
        """Année scolaire nationale active."""
        annee = AnneeScolaire.get_active()
        if not annee:
            return Response(
                {'detail': 'Aucune année scolaire active.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        annee = self.get_queryset().filter(pk=annee.pk).first() or annee
        return Response(self.get_serializer(annee).data)

    @action(detail=True, methods=['post'], url_path='init-periodes')
    def init_periodes(self, request, pk=None):
        annee = self.get_object()
        n = creer_periodes_pour_annee(annee)
        return Response({'detail': f'{n} période(s) créée(s).', 'periodes': n})


class PeriodeEvaluationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PeriodeEvaluationSerializer
    permission_classes = [IsAuthenticated, GestionEvaluation]

    def get_queryset(self):
        qs = PeriodeEvaluation.objects.select_related('annee').all()
        annee = self.request.query_params.get('annee')
        if annee:
            qs = qs.filter(annee_id=annee)
        return qs.order_by('ordre')

    def list(self, request, *args, **kwargs):
        """Liste des périodes + statut verrouillé si classe fournie."""
        response = super().list(request, *args, **kwargs)
        annee = request.query_params.get('annee')
        classe = request.query_params.get('classe')
        if not annee or not classe:
            return response
        locked = ids_periodes_verrouillees(int(annee), int(classe))
        data = response.data
        rows = data.get('results', data) if isinstance(data, dict) else data
        for row in rows:
            row['verrouillee'] = row.get('id') in locked
        return response

    @action(detail=True, methods=['post'], url_path='ouvrir')
    def ouvrir(self, request, pk=None):
        """
        Ouvre une période pour saisie : verrouille automatiquement
        toutes les périodes antérieures de la classe.
        """
        periode = self.get_object()
        classe_id = request.data.get('classe')
        if getattr(request.user, 'est_enseignant', False):
            classe_id = request.user.classe_id
        if not classe_id:
            return Response({'detail': 'classe requise.'}, status=status.HTTP_400_BAD_REQUEST)
        classe = get_object_or_404(Classe, pk=classe_id)
        if not _peut_saisir_classe(request.user, classe):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Classe non autorisée.')
        if periode_est_verrouillee(periode.annee_id, classe.id, periode.id):
            return Response({
                'detail': 'Cette période est déjà verrouillée. Saisie en lecture seule.',
                'verrouillee': True,
                'verrouilles': 0,
            })
        n = verrouiller_periodes_anterieures(
            periode.annee, classe.id, periode, user=request.user,
        )
        return Response({
            'detail': (
                f'Période « {periode.libelle} » ouverte.'
                + (f' {n} période(s) précédente(s) verrouillée(s).' if n else '')
            ),
            'verrouillee': False,
            'verrouilles': n,
            'periode': PeriodeEvaluationSerializer(periode).data,
        })

    @action(detail=True, methods=['post'], url_path='deverrouiller')
    def deverrouiller(self, request, pk=None):
        """Déverrouille une période (admin école / admin uniquement)."""
        user = request.user
        if not (user.est_admin or user.role == 'admin_ecole'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Seul l\'administratif peut déverrouiller.')
        periode = self.get_object()
        classe_id = request.data.get('classe')
        if not classe_id:
            return Response({'detail': 'classe requise.'}, status=status.HTTP_400_BAD_REQUEST)
        deleted, _ = VerrouillagePeriode.objects.filter(
            annee_id=periode.annee_id, classe_id=classe_id, periode=periode,
        ).delete()
        return Response({
            'detail': 'Période déverrouillée.' if deleted else 'Période déjà ouverte.',
            'verrouillee': False,
        })


class MatiereViewSet(viewsets.ModelViewSet):
    serializer_class = MatiereSerializer
    permission_classes = [IsAuthenticated, GestionEvaluation]
    search_fields = ['nom', 'code', 'section__nom', 'option__nom', 'classe__nom']

    def get_queryset(self):
        qs = Matiere.objects.select_related(
            'ecole', 'section', 'option', 'classe',
        ).all()
        ecole = self.request.query_params.get('ecole')
        user = self.request.user
        ids = _scope_ecole_ids(user)
        if ids is not None:
            qs = qs.filter(ecole_id__in=ids)
        if ecole:
            qs = qs.filter(ecole_id=ecole)

        classe_id = self.request.query_params.get('classe')
        option_id = self.request.query_params.get('option')
        section_id = self.request.query_params.get('section')
        # Enseignant : forcément sa classe titulaire
        if getattr(user, 'est_enseignant', False):
            if not user.classe_id:
                return qs.none()
            classe_id = str(user.classe_id)
        # scope=hierarchie (défaut si classe fournie) : classe + option (+ section)
        scope = (self.request.query_params.get('scope') or '').lower()
        use_hierarchie = scope in ('hierarchie', '1', 'true') or (
            bool(classe_id) and scope not in ('exact', 'strict')
        )

        if classe_id and use_hierarchie:
            classe = Classe.objects.select_related('section', 'option').filter(pk=classe_id).first()
            if classe:
                qs = matieres_queryset_pour_classe(qs, classe, mode='liste')
            else:
                qs = qs.none()
        else:
            if section_id:
                qs = qs.filter(section_id=section_id)
            if option_id:
                qs = qs.filter(option_id=option_id)
            if classe_id:
                qs = qs.filter(classe_id=classe_id)

        if self.request.query_params.get('actif') in ('1', 'true'):
            qs = qs.filter(active=True)
        return qs.order_by('ordre', 'nom')

    def perform_create(self, serializer):
        user = self.request.user
        ecole = serializer.validated_data.get('ecole')
        if user.role == 'admin_ecole' and user.ecole_id:
            if ecole and ecole.id != user.ecole_id:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Vous ne pouvez créer des matières que pour votre école.')
            serializer.save(ecole_id=user.ecole_id)
        else:
            serializer.save()

    @action(detail=False, methods=['post'], url_path='charger-catalogue')
    def charger_catalogue(self, request):
        """Charge les matières types pour une section / option / classe."""
        ecole_id = request.data.get('ecole')
        regime = request.data.get('regime') or AnneeScolaire.Regime.SECONDAIRE
        classe_id = request.data.get('classe')
        section_id = request.data.get('section')
        option_id = request.data.get('option')
        user = request.user
        if user.role == 'admin_ecole' and user.ecole_id:
            ecole_id = user.ecole_id

        # Résoudre école / section / option depuis la classe si fournie
        classe = None
        if classe_id:
            classe = Classe.objects.select_related('section', 'option', 'ecole').filter(
                pk=classe_id,
            ).first()
            if classe:
                ecole_id = ecole_id or classe.ecole_id
                section_id = section_id or classe.section_id
                option_id = option_id or classe.option_id

        if not ecole_id:
            return Response({'detail': 'École ou classe requise.'}, status=status.HTTP_400_BAD_REQUEST)
        if not classe_id and not option_id and not section_id:
            return Response(
                {'detail': 'Sélectionnez une classe (ou section / option) pour charger le catalogue.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = synchroniser_matieres_ecole(
            int(ecole_id),
            regime,
            classe_id=int(classe_id) if classe_id else None,
            section_id=int(section_id) if section_id else None,
            option_id=int(option_id) if option_id else None,
        )
        scope_label = ''
        if classe:
            parts = [p for p in (classe.section.nom if classe.section_id else '',
                                 classe.option.nom if classe.option_id else '',
                                 classe.nom) if p]
            scope_label = ' · '.join(parts)
        return Response({
            'detail': (
                f"{result['created']} matière(s) ajoutée(s), "
                f"{result['updated']} mise(s) à jour"
                + (f' — {scope_label}' if scope_label else ' (section / option / classe)')
                + '.'
            ),
            **result,
        })


class ProgrammeClasseViewSet(viewsets.ModelViewSet):
    serializer_class = ProgrammeClasseSerializer
    permission_classes = [IsAuthenticated, GestionEvaluation]

    def get_queryset(self):
        qs = ProgrammeClasse.objects.select_related('matiere', 'classe', 'annee').all()
        annee = self.request.query_params.get('annee')
        classe = self.request.query_params.get('classe')
        user = self.request.user
        if getattr(user, 'est_enseignant', False):
            # Uniquement le programme de sa classe titulaire (section/option via la classe)
            if not user.classe_id:
                return qs.none()
            qs = qs.filter(classe_id=user.classe_id)
        elif user.role == 'admin_ecole' and user.ecole_id:
            qs = qs.filter(classe__ecole_id=user.ecole_id)
        if annee:
            qs = qs.filter(annee_id=annee)
        if classe and not getattr(user, 'est_enseignant', False):
            qs = qs.filter(classe_id=classe)
        return qs

    def perform_create(self, serializer):
        classe = serializer.validated_data['classe']
        if not _peut_saisir_classe(self.request.user, classe) and not self.request.user.est_admin:
            if self.request.user.role != 'admin_ecole' or self.request.user.ecole_id != classe.ecole_id:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Accès refusé pour cette classe.')
        serializer.save()

    @action(detail=False, methods=['post'], url_path='appliquer-matieres-ecole')
    def appliquer_matieres_ecole(self, request):
        """Attache toutes les matières actives de l'école au programme de la classe."""
        annee_id = request.data.get('annee')
        classe_id = request.data.get('classe')
        if not annee_id or not classe_id:
            return Response(
                {'detail': 'annee et classe sont requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        classe = get_object_or_404(
            Classe.objects.select_related('section', 'option'),
            pk=classe_id,
        )
        if not (
            request.user.est_admin
            or getattr(request.user, 'est_national', False)
            or (request.user.role == 'admin_ecole' and request.user.ecole_id == classe.ecole_id)
        ):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Réservé à l\'administratif de l\'école.')

        # Si aucune matière pour cette option/classe → charger le catalogue d'abord
        matieres = matieres_queryset_pour_classe(
            Matiere.objects.filter(ecole_id=classe.ecole_id, active=True),
            classe,
        )
        sync_info = None
        if not matieres.exists():
            annee = AnneeScolaire.objects.filter(pk=annee_id).first()
            regime = annee.regime if annee else AnneeScolaire.Regime.SECONDAIRE
            sync_info = synchroniser_matieres_ecole(
                classe.ecole_id,
                regime,
                classe_id=classe.id,
                section_id=classe.section_id,
                option_id=classe.option_id,
            )
            matieres = matieres_queryset_pour_classe(
                Matiere.objects.filter(ecole_id=classe.ecole_id, active=True),
                classe,
            )

        created = 0
        for m in matieres.order_by('ordre', 'nom'):
            _, was = ProgrammeClasse.objects.get_or_create(
                annee_id=annee_id,
                classe=classe,
                matiere=m,
                defaults={'ordre': m.ordre, 'maximum': m.maximum},
            )
            if was:
                created += 1
        opt = classe.option.nom if classe.option_id else ''
        sec = classe.section.nom if classe.section_id else ''
        scope = ' · '.join(p for p in (sec, opt, classe.nom) if p)
        detail = f'{created} matière(s) programmée(s) pour {scope or "la classe"}.'
        if sync_info and sync_info.get('created'):
            detail += f" Catalogue : {sync_info['created']} créée(s)."
        return Response({
            'detail': detail,
            'created': created,
            'matieres': matieres.count(),
            'sync': sync_info,
        })


class NoteViewSet(viewsets.ModelViewSet):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated, GestionEvaluation]

    def get_queryset(self):
        qs = Note.objects.select_related(
            'eleve', 'programme__matiere', 'programme__classe', 'periode',
        ).all()
        user = self.request.user
        if getattr(user, 'est_enseignant', False):
            if not user.classe_id:
                return qs.none()
            qs = qs.filter(eleve__classe_id=user.classe_id)
        elif user.role == 'admin_ecole' and user.ecole_id:
            qs = qs.filter(eleve__ecole_id=user.ecole_id)
        programme = self.request.query_params.get('programme')
        classe = self.request.query_params.get('classe')
        annee = self.request.query_params.get('annee')
        eleve = self.request.query_params.get('eleve')
        if programme:
            qs = qs.filter(programme_id=programme)
        if classe:
            qs = qs.filter(programme__classe_id=classe)
        if annee:
            qs = qs.filter(periode__annee_id=annee)
        if eleve:
            qs = qs.filter(eleve_id=eleve)
        return qs

    def perform_create(self, serializer):
        programme = serializer.validated_data['programme']
        periode = serializer.validated_data['periode']
        if not _peut_saisir_classe(self.request.user, programme.classe):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Seul le titulaire ou l\'administratif peut saisir.')
        if periode_est_verrouillee(programme.annee_id, programme.classe_id, periode.id):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Cette période est verrouillée.')
        self._valider_note(serializer.validated_data)
        serializer.save(saisi_par=self.request.user)

    def perform_update(self, serializer):
        programme = serializer.instance.programme
        periode = serializer.validated_data.get('periode', serializer.instance.periode)
        if not _peut_saisir_classe(self.request.user, programme.classe):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Seul le titulaire ou l\'administratif peut modifier.')
        if periode_est_verrouillee(programme.annee_id, programme.classe_id, periode.id):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Cette période est verrouillée.')
        self._valider_note({**{'programme': programme, 'periode': periode}, **serializer.validated_data})
        serializer.save(saisi_par=self.request.user)

    def _valider_note(self, data):
        programme = data.get('programme')
        periode = data.get('periode')
        valeur = data.get('valeur')
        if valeur is None or programme is None or periode is None:
            return
        maxi = maximum_periode(programme, periode)
        if Decimal(str(valeur)) > maxi:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'valeur': f'La note ne peut pas dépasser {maxi}.'})

    @action(detail=False, methods=['post'], url_path='saisie-bulk')
    def saisie_bulk(self, request):
        """Saisie groupée des notes pour une matière (programme)."""
        ser = NoteBulkSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        programme = get_object_or_404(
            ProgrammeClasse.objects.select_related('classe'),
            pk=ser.validated_data['programme'],
        )
        if not _peut_saisir_classe(request.user, programme.classe):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Seul le titulaire ou l\'administratif peut saisir.')

        # Une seule période autorisée par lot ; refus si verrouillée
        periode_ids = {item['periode'] for item in ser.validated_data['notes']}
        if len(periode_ids) != 1:
            return Response(
                {'detail': 'La saisie ne peut concerner qu\'une seule période à la fois.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        periode_id = next(iter(periode_ids))
        if periode_est_verrouillee(programme.annee_id, programme.classe_id, periode_id):
            return Response(
                {'detail': 'Cette période est verrouillée. Impossible de modifier les notes.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        saved = 0
        errors = []
        for item in ser.validated_data['notes']:
            try:
                periode = PeriodeEvaluation.objects.get(pk=item['periode'])
                if periode.annee_id != programme.annee_id:
                    raise ValueError('Période hors année du programme.')
                eleve = Eleve.objects.get(pk=item['eleve'], classe_id=programme.classe_id)
                valeur = item.get('valeur', None)
                if valeur is not None:
                    maxi = maximum_periode(programme, periode)
                    if Decimal(str(valeur)) > maxi:
                        raise ValueError(f'Note > maximum ({maxi})')
                Note.objects.update_or_create(
                    eleve=eleve,
                    programme=programme,
                    periode=periode,
                    defaults={'valeur': valeur, 'saisi_par': request.user},
                )
                saved += 1
            except Exception as exc:  # noqa: BLE001
                errors.append({'eleve': item.get('eleve'), 'message': str(exc)})

        return Response({
            'detail': f'{saved} note(s) enregistrée(s).',
            'saved': saved,
            'errors': errors[:20],
            'errors_count': len(errors),
        })

    @action(detail=False, methods=['get'], url_path='grille')
    def grille(self, request):
        """Grille de saisie : élèves × une période pour un programme."""
        programme_id = request.query_params.get('programme')
        periode_id = request.query_params.get('periode')
        if not programme_id:
            return Response({'detail': 'programme requis.'}, status=status.HTTP_400_BAD_REQUEST)
        if not periode_id:
            return Response({'detail': 'periode requise.'}, status=status.HTTP_400_BAD_REQUEST)
        programme = get_object_or_404(
            ProgrammeClasse.objects.select_related('matiere', 'classe', 'annee'),
            pk=programme_id,
        )
        periode = get_object_or_404(
            PeriodeEvaluation.objects.filter(annee_id=programme.annee_id),
            pk=periode_id,
        )
        user = request.user
        if getattr(user, 'est_enseignant', False) and user.classe_id != programme.classe_id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Classe non autorisée.')
        verrouillee = periode_est_verrouillee(
            programme.annee_id, programme.classe_id, periode.id,
        )
        eleves = list(
            Eleve.objects.filter(classe_id=programme.classe_id, actif=True)
            .order_by('nom', 'postnom', 'prenom')
        )
        notes = Note.objects.filter(programme=programme, periode=periode)
        note_map = {n.eleve_id: n.valeur for n in notes}
        maxi = maximum_periode(programme, periode)
        rows = []
        for el in eleves:
            val = note_map.get(el.id)
            rows.append({
                'eleve_id': el.id,
                'eleve_nom': el.nom_complet,
                'matricule': el.matricule,
                'note': str(val) if val is not None else '',
            })
        return Response({
            'programme': ProgrammeClasseSerializer(programme).data,
            'periode': PeriodeEvaluationSerializer(periode).data,
            'verrouillee': verrouillee,
            'maximum': str(maxi),
            'eleves': rows,
        })


class BulletinViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        annee_id = request.query_params.get('annee')
        classe_id = request.query_params.get('classe')
        user = request.user
        if getattr(user, 'est_enseignant', False):
            classe_id = user.classe_id
        if not annee_id or not classe_id:
            return Response(
                {'detail': 'annee et classe sont requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        annee = get_object_or_404(AnneeScolaire, pk=annee_id)
        eleves = Eleve.objects.filter(classe_id=classe_id, actif=True).order_by(
            'nom', 'postnom', 'prenom',
        )
        results = []
        for el in eleves:
            try:
                data = calculer_bulletin_eleve(el, annee)
            except ValueError:
                continue
            results.append({
                'eleve_id': el.id,
                'eleve_nom': el.nom_complet,
                'matricule': el.matricule,
                'total_obtenu': data['total_obtenu'],
                'total_max': data['total_max'],
                'pourcentage': data['pourcentage'],
                'place': data['decision'].place,
                'decision': data['decision'].decision,
                'decision_display': data['decision'].get_decision_display(),
            })
        return Response({'count': len(results), 'results': results})

    @action(detail=False, methods=['get'], url_path=r'(?P<eleve_id>[0-9]+)/pdf')
    def pdf(self, request, eleve_id=None):
        annee_id = request.query_params.get('annee')
        if not annee_id:
            return Response({'detail': 'annee requis.'}, status=status.HTTP_400_BAD_REQUEST)
        eleve = get_object_or_404(Eleve.objects.select_related('ecole', 'classe'), pk=eleve_id)
        user = request.user
        if getattr(user, 'est_enseignant', False) and user.classe_id != eleve.classe_id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Bulletin hors de votre classe.')
        if user.role == 'admin_ecole' and user.ecole_id != eleve.ecole_id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Bulletin hors de votre école.')
        annee = get_object_or_404(AnneeScolaire, pk=annee_id)
        pdf = generer_pdf_bulletin(eleve, annee)
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f'bulletin_{eleve.matricule}_{annee.libelle}.pdf'.replace('/', '-')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    @action(detail=False, methods=['post'], url_path='classer')
    def classer(self, request):
        annee_id = request.data.get('annee')
        classe_id = request.data.get('classe')
        user = request.user
        if getattr(user, 'est_enseignant', False):
            classe_id = user.classe_id
        if not annee_id or not classe_id:
            return Response(
                {'detail': 'annee et classe requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        classe = get_object_or_404(Classe, pk=classe_id)
        if not _peut_saisir_classe(user, classe):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Accès refusé.')
        annee = get_object_or_404(AnneeScolaire, pk=annee_id)
        actualiser_classement(annee, classe.id)
        return Response({'detail': 'Classement actualisé.'})

    @action(detail=False, methods=['patch'], url_path=r'(?P<eleve_id>[0-9]+)/decision')
    def decision(self, request, eleve_id=None):
        annee_id = request.data.get('annee')
        eleve = get_object_or_404(Eleve, pk=eleve_id)
        if not eleve.classe_id or not _peut_saisir_classe(
            request.user, eleve.classe,
        ):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Accès refusé.')
        annee = get_object_or_404(AnneeScolaire, pk=annee_id)
        obj, _ = BulletinDecision.objects.get_or_create(eleve=eleve, annee=annee)
        ser = BulletinDecisionSerializer(obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

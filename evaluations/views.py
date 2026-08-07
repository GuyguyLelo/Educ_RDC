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
from .defaults import creer_periodes_pour_annee, synchroniser_matieres_ecole
from .models import (
    AnneeScolaire,
    BulletinDecision,
    Matiere,
    Note,
    PeriodeEvaluation,
    ProgrammeClasse,
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
from .services import actualiser_classement, calculer_bulletin_eleve, generer_pdf_bulletin, maximum_periode


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
                'destroy', 'classer', 'decision',
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


class AnneeScolaireViewSet(viewsets.ModelViewSet):
    queryset = AnneeScolaire.objects.all()
    serializer_class = AnneeScolaireSerializer
    permission_classes = [IsAuthenticated, GestionEvaluation]

    def perform_create(self, serializer):
        annee = serializer.save()
        creer_periodes_pour_annee(annee)

    @action(detail=True, methods=['post'], url_path='init-periodes')
    def init_periodes(self, request, pk=None):
        annee = self.get_object()
        n = creer_periodes_pour_annee(annee)
        return Response({'detail': f'{n} période(s) créée(s).', 'periodes': n})


class PeriodeEvaluationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PeriodeEvaluationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = PeriodeEvaluation.objects.select_related('annee').all()
        annee = self.request.query_params.get('annee')
        if annee:
            qs = qs.filter(annee_id=annee)
        return qs


class MatiereViewSet(viewsets.ModelViewSet):
    serializer_class = MatiereSerializer
    permission_classes = [IsAuthenticated, GestionEvaluation]

    def get_queryset(self):
        qs = Matiere.objects.select_related('ecole').all()
        ecole = self.request.query_params.get('ecole')
        user = self.request.user
        ids = _scope_ecole_ids(user)
        if ids is not None:
            qs = qs.filter(ecole_id__in=ids)
        if ecole:
            qs = qs.filter(ecole_id=ecole)
        if self.request.query_params.get('actif') in ('1', 'true'):
            qs = qs.filter(active=True)
        return qs

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
        """Charge les matières types (primaire/secondaire) pour une école."""
        ecole_id = request.data.get('ecole')
        regime = request.data.get('regime') or AnneeScolaire.Regime.SECONDAIRE
        user = request.user
        if user.role == 'admin_ecole' and user.ecole_id:
            ecole_id = user.ecole_id
        if not ecole_id:
            return Response({'detail': 'École requise.'}, status=status.HTTP_400_BAD_REQUEST)
        result = synchroniser_matieres_ecole(int(ecole_id), regime)
        return Response({
            'detail': (
                f"{result['created']} matière(s) ajoutée(s), "
                f"{result['updated']} mise(s) à jour "
                f"(catalogue bulletin IGE/EPSP)."
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
        if getattr(user, 'est_enseignant', False) and user.classe_id:
            qs = qs.filter(classe_id=user.classe_id)
        elif user.role == 'admin_ecole' and user.ecole_id:
            qs = qs.filter(classe__ecole_id=user.ecole_id)
        if annee:
            qs = qs.filter(annee_id=annee)
        if classe:
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
        classe = get_object_or_404(Classe, pk=classe_id)
        if not (
            request.user.est_admin
            or (request.user.role == 'admin_ecole' and request.user.ecole_id == classe.ecole_id)
        ):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Réservé à l\'administratif de l\'école.')
        matieres = Matiere.objects.filter(ecole_id=classe.ecole_id, active=True)
        created = 0
        for m in matieres:
            _, was = ProgrammeClasse.objects.get_or_create(
                annee_id=annee_id,
                classe=classe,
                matiere=m,
                defaults={'ordre': m.ordre, 'maximum': m.maximum},
            )
            if was:
                created += 1
        return Response({'detail': f'{created} matière(s) programmée(s).', 'created': created})


class NoteViewSet(viewsets.ModelViewSet):
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated, GestionEvaluation]

    def get_queryset(self):
        qs = Note.objects.select_related(
            'eleve', 'programme__matiere', 'programme__classe', 'periode',
        ).all()
        user = self.request.user
        if getattr(user, 'est_enseignant', False) and user.classe_id:
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
        if not _peut_saisir_classe(self.request.user, programme.classe):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Seul le titulaire ou l\'administratif peut saisir.')
        self._valider_note(serializer.validated_data)
        serializer.save(saisi_par=self.request.user)

    def perform_update(self, serializer):
        programme = serializer.instance.programme
        if not _peut_saisir_classe(self.request.user, programme.classe):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Seul le titulaire ou l\'administratif peut modifier.')
        self._valider_note({**{'programme': programme, 'periode': serializer.instance.periode}, **serializer.validated_data})
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
        """Grille de saisie : élèves × périodes pour un programme."""
        programme_id = request.query_params.get('programme')
        if not programme_id:
            return Response({'detail': 'programme requis.'}, status=status.HTTP_400_BAD_REQUEST)
        programme = get_object_or_404(
            ProgrammeClasse.objects.select_related('matiere', 'classe', 'annee'),
            pk=programme_id,
        )
        user = request.user
        if getattr(user, 'est_enseignant', False) and user.classe_id != programme.classe_id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Classe non autorisée.')
        periodes = list(programme.annee.periodes.all().order_by('ordre'))
        eleves = list(
            Eleve.objects.filter(classe_id=programme.classe_id, actif=True)
            .order_by('nom', 'postnom', 'prenom')
        )
        notes = Note.objects.filter(programme=programme)
        note_map = {(n.eleve_id, n.periode_id): n.valeur for n in notes}
        rows = []
        for el in eleves:
            cells = {}
            for p in periodes:
                cells[str(p.id)] = (
                    str(note_map[(el.id, p.id)])
                    if (el.id, p.id) in note_map and note_map[(el.id, p.id)] is not None
                    else ''
                )
            rows.append({
                'eleve_id': el.id,
                'eleve_nom': el.nom_complet,
                'matricule': el.matricule,
                'notes': cells,
            })
        return Response({
            'programme': ProgrammeClasseSerializer(programme).data,
            'periodes': PeriodeEvaluationSerializer(periodes, many=True).data,
            'maxima': {
                str(p.id): str(maximum_periode(programme, p)) for p in periodes
            },
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

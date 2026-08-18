from django.test import Client, TestCase
from django.urls import reverse

from administration.models import JournalActivite
from utilisateurs.models import Utilisateur


class SessionUniqueTests(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            username='agent_session',
            password='MotDePasse123!',
            role=Utilisateur.Role.ADMIN,
        )
        self.creds = {
            'username': 'agent_session',
            'password': 'MotDePasse123!',
        }

    def test_seconde_connexion_refusee_tant_que_session_en_ligne(self):
        c1 = Client()
        r1 = c1.post(reverse('login'), self.creds)
        self.assertEqual(r1.status_code, 302)

        c2 = Client()
        r2 = c2.post(reverse('login'), self.creds)
        self.assertEqual(r2.status_code, 200)
        self.assertContains(r2, 'déjà une session en ligne')
        self.assertFalse(r2.wsgi_request.user.is_authenticated)

        r3 = c1.get(reverse('dashboard'))
        self.assertEqual(r3.status_code, 200)

    def test_reconnexion_autorisee_apres_deconnexion(self):
        c1 = Client()
        self.assertEqual(c1.post(reverse('login'), self.creds).status_code, 302)
        self.assertEqual(c1.get(reverse('logout')).status_code, 302)

        c2 = Client()
        self.assertEqual(c2.post(reverse('login'), self.creds).status_code, 302)
        self.assertEqual(c2.get(reverse('dashboard')).status_code, 200)


class HistoriqueMonitoringTests(TestCase):
    def setUp(self):
        self.admin = Utilisateur.objects.create_user(
            username='admin_mon',
            password='MotDePasse123!',
            role=Utilisateur.Role.ADMIN,
        )
        self.cible = Utilisateur.objects.create_user(
            username='enseignant_mon',
            password='MotDePasse123!',
            first_name='Amina',
            last_name='Kabila',
            role=Utilisateur.Role.ENSEIGNANT,
        )
        JournalActivite.objects.create(
            utilisateur=self.cible,
            action='Connexion',
            details='IP 10.0.0.8',
            adresse_ip='10.0.0.8',
        )
        JournalActivite.objects.create(
            utilisateur=self.cible,
            action='Déconnexion',
            details='',
            adresse_ip='10.0.0.8',
        )

    def test_admin_voit_historique(self):
        self.client.force_login(self.admin)
        url = reverse('api_monitoring_historique_utilisateur', args=[self.cible.pk])
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['utilisateur']['username'], 'enseignant_mon')
        actions = [r['action'] for r in data['results']]
        self.assertIn('Connexion', actions)
        self.assertIn('Déconnexion', actions)

    def test_filtre_historique(self):
        self.client.force_login(self.admin)
        url = reverse('api_monitoring_historique_utilisateur', args=[self.cible.pk])
        res = self.client.get(url, {'q': 'IP 10'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['count'], 1)

    def test_non_admin_interdit(self):
        self.client.force_login(self.cible)
        url = reverse('api_monitoring_historique_utilisateur', args=[self.cible.pk])
        self.assertEqual(self.client.get(url).status_code, 403)

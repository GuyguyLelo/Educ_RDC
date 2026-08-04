# Educ_RDC

Plateforme nationale d'identification scolaire — République Démocratique du Congo.

## Fonctionnalités

- Identification des écoles (province / antenne)
- Enrôlement des élèves
- Capture biométrique (photo + empreinte simulée)
- Génération de cartes scolaires avec QR code
- Dashboard statistique
- Export PDF
- API REST + authentification JWT
- Rôles : admin, agent_national, agent_provincial, agent_antenne

## Installation

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py init_donnees
python manage.py runserver
```

Ouvrir : http://127.0.0.1:8000/

### Compte démo

- Identifiant : `admin`
- Mot de passe : `admin123`

## Charte graphique RDC

- Bleu `#007FFF`
- Rouge `#CE1126`
- Jaune `#FCD116`

## API

- JWT : `POST /api/auth/token/`
- Refresh : `POST /api/auth/refresh/`
- Endpoints : `/api/ecoles/`, `/api/eleves/`, `/api/enrolements/`, `/api/cartes/`, `/api/stats/`, etc.

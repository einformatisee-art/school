Déploiement sur Render

1) Sur https://dashboard.render.com, connectez votre compte GitHub et importez le dépôt `einformatisee-art/school`.

2) Créez un nouveau `Web Service` :
   - Environment: `Python`
   - Name: `gestion-scolaires`
   - Branch: `master`
   - Build command: `pip install -r requirements.txt -r requirements-extra.txt && python manage.py collectstatic --noinput`
   - Start command: `gunicorn Scolaires.wsgi:application --bind 0.0.0.0:$PORT`
   - Instance type: `Free` (si disponible)

3) Variables d'environnement à définir dans Render -> Environment:
   - `DJANGO_SECRET_KEY` : (valeur secrète)
   - `DEBUG` : `False`
   - `ALLOWED_HOSTS` : `*` ou votre domaine
   - Si vous utilisez une base de données PostgreSQL fournie par Render : `DATABASE_URL` sera défini automatiquement.

4) Base de données :
   - Pour la production, ajoutez un service `PostgreSQL` sur Render et récupérez la variable `DATABASE_URL`.

5) Après le premier build, ouvrez la console (Render shell) et exécutez :
   - `python manage.py migrate`
   - `python manage.py createsuperuser`

6) Remarques :
   - Si vous laissez SQLite, les fichiers ne seront pas persistants après redéploiement. Utilisez PostgreSQL en production.

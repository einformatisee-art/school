# Gestion Scolaires

Application Django de gestion scolaire.

## Déploiement sur une plateforme compatible Heroku/Railway/Render

1. Assurez-vous d'avoir un dépôt GitHub et un accès au repository.
2. Configurez un remote GitHub :
   ```powershell
   cd "c:\Users\IR  JUNIOR\OneDrive\Documents\Gestion_Scolaires"
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/<votre-utilisateur>/<votre-repo>.git
   git push -u origin master
   ```
3. Sur Railway ou Render, connectez votre dépôt GitHub.
4. Définissez les variables d'environnement :
   - `DJANGO_SECRET_KEY` : une clé secrète Django
   - `DEBUG` : `False`
   - `ALLOWED_HOSTS` : le domaine de l'app (par exemple `*` pour test)
5. Exécutez les migrations.
6. Si votre plateforme ne propose pas de base de données externe, l'application utilisera SQLite localement.

## Commandes utiles

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

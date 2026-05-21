from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages as django_messages
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse, FileResponse, Http404
from django.utils import timezone
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from .models import (
    Eleve, Enseignant, Parent, Classe, Matiere,
    Cours, RessourcePedagogique, Devoir, DevoirSoumis,
    Note, Evaluation, Portfolio, Message, Notification,
    SoumissionEvaluation, SuiviPedagogique, AutoEvaluation,
    FraisAcademique, PaiementFrais, JournalConnexion, Competence
)
from decimal import Decimal, InvalidOperation
import mimetypes
import os


def est_eleve(user):
    return hasattr(user, 'eleve')

def est_enseignant(user):
    return hasattr(user, 'enseignant')

def est_parent(user):
    return hasattr(user, 'parent')

def est_admin(user):
    return user.is_staff or user.is_superuser


def lien_messages_pour(user):
    if est_enseignant(user):
        return '/enseignant/messages/'
    if est_parent(user):
        return '/parent/messages/'
    return '/eleve/messages/'


def contacts_messagerie(user):
    if est_enseignant(user):
        enseignant = user.enseignant
        return User.objects.filter(
            parent__enfants__classe__cours__enseignant=enseignant
        ).distinct().exclude(id=user.id)
    if est_parent(user):
        parent = user.parent
        return User.objects.filter(
            enseignant__cours__classe__eleves__parents=parent
        ).distinct().exclude(id=user.id)
    if est_eleve(user):
        eleve = user.eleve
        return User.objects.filter(
            Q(enseignant__cours__classe=eleve.classe) | Q(parent__enfants=eleve)
        ).distinct().exclude(id=user.id)
    return User.objects.none()


def creer_message_avec_notification(expediteur, destinataire, sujet, contenu):
    message = Message.objects.create(
        expediteur=expediteur,
        destinataire=destinataire,
        sujet=sujet,
        contenu=contenu
    )
    Notification.objects.create(
        utilisateur=destinataire,
        type_notification='MESSAGE',
        titre='Nouveau message',
        message=f'Vous avez reçu un message de {expediteur.get_full_name() or expediteur.username}',
        lien=lien_messages_pour(destinataire)
    )
    return message


def construire_bulletin(eleve):
    notes = Note.objects.filter(eleve=eleve).select_related(
        'evaluation__cours__matiere',
        'evaluation__cours__classe',
    ).order_by('evaluation__cours__matiere__nom', '-evaluation__date_evaluation')
    bulletin = {}
    total_general = 0
    coef_general = 0
    maximum_general = 0

    for note in notes:
        matiere = note.evaluation.cours.matiere.nom
        coefficient = float(note.evaluation.coefficient or 1)
        valeur = float(note.valeur)
        maximum = 20 * coefficient
        if matiere not in bulletin:
            bulletin[matiere] = {
                'notes': [],
                'moyenne': 0,
                'coef_total': 0,
                'total': 0,
                'maximum': 0,
                'pourcentage': 0,
                'appreciation': '',
            }
        bulletin[matiere]['notes'].append(note)
        bulletin[matiere]['total'] += valeur * coefficient
        bulletin[matiere]['coef_total'] += coefficient
        bulletin[matiere]['maximum'] += maximum
        total_general += valeur * coefficient
        coef_general += coefficient
        maximum_general += maximum

    for data in bulletin.values():
        moyenne = round(data['total'] / data['coef_total'], 2) if data['coef_total'] else 0
        data['moyenne'] = moyenne
        data['total'] = round(data['total'], 2)
        data['maximum'] = round(data['maximum'], 2)
        data['pourcentage'] = round((data['total'] / data['maximum']) * 100, 2) if data['maximum'] else 0
        if moyenne >= 16:
            data['appreciation'] = 'Excellent'
        elif moyenne >= 14:
            data['appreciation'] = 'Très bien'
        elif moyenne >= 12:
            data['appreciation'] = 'Bien'
        elif moyenne >= 10:
            data['appreciation'] = 'Assez bien'
        elif moyenne >= 8:
            data['appreciation'] = 'Passable'
        else:
            data['appreciation'] = 'Insuffisant'

    moyenne_generale = round(total_general / coef_general, 2) if coef_general else None
    total_general = round(total_general, 2)
    maximum_general = round(maximum_general, 2)
    pourcentage_general = round((total_general / maximum_general) * 100, 2) if maximum_general else None
    if moyenne_generale is None:
        mention_generale = 'Non calculée'
        decision = 'Statut non disponible'
    elif moyenne_generale >= 16:
        mention_generale = 'Excellent'
        decision = 'Admis'
    elif moyenne_generale >= 14:
        mention_generale = 'Très bien'
        decision = 'Admis'
    elif moyenne_generale >= 12:
        mention_generale = 'Bien'
        decision = 'Admis'
    elif moyenne_generale >= 10:
        mention_generale = 'Assez bien'
        decision = 'Admis'
    elif moyenne_generale >= 8:
        mention_generale = 'Passable'
        decision = 'Admis conditionnel'
    else:
        mention_generale = 'Insuffisant'
        decision = 'Ajourné'
    return {
        'mention_generale': mention_generale,
        'decision': decision,
        'annee_scolaire': eleve.classe.annee_scolaire if eleve.classe else 'N/A',
        'notes': notes,
        'bulletin': bulletin,
        'moyenne_generale': moyenne_generale,
        'coef_general': coef_general,
        'total_general': total_general,
        'maximum_general': maximum_general,
        'pourcentage_general': pourcentage_general,
    }


def reponse_bulletin_html(eleve, demandeur):
    donnees = construire_bulletin(eleve)
    contenu = render_to_string('bulletin_telechargeable.html', {
        'eleve': eleve,
        'demandeur': demandeur,
        **donnees,
        'date_generation': timezone.now(),
    })
    nom = f"bulletin_{eleve.matricule}.html"
    response = HttpResponse(contenu, content_type='text/html; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{nom}"'
    return response


def infos_frais_eleve(eleve):
    frais = None
    if eleve.classe:
        frais = FraisAcademique.objects.filter(
            classe=eleve.classe,
            annee_scolaire=eleve.classe.annee_scolaire
        ).first()
    paiements = PaiementFrais.objects.filter(eleve=eleve, frais=frais).order_by('date_paiement') if frais else []
    total_paye = paiements.aggregate(total=Sum('montant'))['total'] if frais else Decimal('0.00')
    total_paye = total_paye or Decimal('0.00')
    montant_total = frais.montant_total if frais else Decimal('0.00')
    reste = max(montant_total - total_paye, Decimal('0.00'))
    types_payes = set(paiements.values_list('type_paiement', flat=True)) if frais else set()
    prochain_type = None
    if frais and 'ACOMPTE' not in types_payes:
        prochain_type = 'ACOMPTE'
    elif frais and reste > 0 and 'SOLDE' not in types_payes:
        prochain_type = 'SOLDE'
    return {
        'eleve': eleve,
        'frais': frais,
        'paiements': paiements,
        'total_paye': total_paye,
        'reste': reste,
        'prochain_type': prochain_type,
        'est_solde': frais is not None and reste == 0,
    }


def reponse_recu_paiement(paiement):
    contenu = render_to_string('recu_paiement_frais.html', {
        'paiement': paiement,
        'eleve': paiement.eleve,
        'frais': paiement.frais,
        'date_generation': timezone.now(),
    })
    nom = f"recu_{paiement.reference_recu}.html"
    response = HttpResponse(contenu, content_type='text/html; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{nom}"'
    return response


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            JournalConnexion.objects.create(
                utilisateur=user,
                adresse_ip=request.META.get('REMOTE_ADDR'),
                navigateur=request.META.get('HTTP_USER_AGENT', '')[:200],
                succes=True
            )
            if est_admin(user):
                return redirect('admin_dashboard')
            elif est_enseignant(user):
                return redirect('enseignant_dashboard')
            elif est_eleve(user):
                return redirect('eleve_dashboard')
            elif est_parent(user):
                return redirect('parent_dashboard')
            else:
                return redirect('login')
        else:
            django_messages.error(request, 'Identifiants incorrects.')
            JournalConnexion.objects.create(
                utilisateur=User.objects.filter(username=username).first(),
                adresse_ip=request.META.get('REMOTE_ADDR'),
                navigateur=request.META.get('HTTP_USER_AGENT', '')[:200],
                succes=False
            )
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    django_messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('login')


def register_view(request):
    if request.method == 'POST':
        role = request.POST.get('role')
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '')

        if not username or not password:
            django_messages.error(request, 'Veuillez remplir tous les champs obligatoires.')
            return redirect('register')
        if password != password2:
            django_messages.error(request, 'Les mots de passe ne correspondent pas.')
            return redirect('register')
        if User.objects.filter(username=username).exists():
            django_messages.error(request, 'Ce nom d\'utilisateur est déjà pris.')
            return redirect('register')

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email
        )

        try:
            if role == 'eleve':
                # Auto-générer le matricule à 7 caractères
                from .models import generer_matricule
                matricule = generer_matricule()
                classe_id = request.POST.get('classe')
                classe = Classe.objects.filter(id=classe_id).first() if classe_id else None
                Eleve.objects.create(
                    user=user,
                    matricule=matricule,
                    telephone=request.POST.get('telephone', ''),
                    date_naissance=request.POST.get('date_naissance') or None,
                    classe=classe
                )
                django_messages.success(request, f'Compte créé avec succès. Votre matricule est : {matricule}')
            elif role == 'enseignant':
                specialite_id = request.POST.get('specialite')
                specialite = Matiere.objects.filter(id=specialite_id).first() if specialite_id else None
                Enseignant.objects.create(
                    user=user,
                    telephone=request.POST.get('telephone', ''),
                    specialite=specialite
                )
            elif role == 'parent':
                parent = Parent.objects.create(
                    user=user,
                    telephone=request.POST.get('telephone', '')
                )
                enfants_ids = request.POST.getlist('enfants')
                if enfants_ids:
                    parent.enfants.set(Eleve.objects.filter(id__in=enfants_ids))
            elif role == 'admin':
                user.is_staff = True
                user.save()
            else:
                user.delete()
                django_messages.error(request, 'Rôle invalide.')
                return redirect('register')
        except Exception as e:
            user.delete()
            django_messages.error(request, f'Erreur lors de la création du compte : {e}')
            return redirect('register')

        django_messages.success(request, 'Compte créé avec succès. Vous pouvez maintenant vous connecter.')
        return redirect('login')

    context = {
        'classes': Classe.objects.all(),
        'matieres': Matiere.objects.all(),
        'eleves': Eleve.objects.all(),
        'cours': Cours.objects.all().select_related('matiere', 'classe'),
    }
    return render(request, 'register.html', context)


# ==================== Portail Élève ====================

@login_required
def eleve_dashboard(request):
    if not est_eleve(request.user):
        return redirect('login')
    eleve = request.user.eleve
    notes = Note.objects.filter(eleve=eleve)
    moyenne = round(notes.aggregate(Avg('valeur'))['valeur__avg'], 2) if notes.exists() else None
    
    jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
    jour_actuel = jours[timezone.now().weekday()] if timezone.now().weekday() < 6 else 'Lundi'
    cours_jour = Cours.objects.filter(classe=eleve.classe, jour=jour_actuel).order_by('heure_debut') if eleve.classe else []
    
    devoirs = Devoir.objects.filter(cours__classe=eleve.classe, date_rendu__gte=timezone.now()).order_by('date_rendu')[:5] if eleve.classe else []
    evaluations_a_venir = Evaluation.objects.filter(
        cours__classe=eleve.classe,
        type_evaluation__in=['INTERROGATION', 'EXAMEN'],
        date_evaluation__gte=timezone.localdate(),
    ).select_related('cours__matiere', 'cours__enseignant').order_by('date_evaluation')[:5] if eleve.classe else []
    notifications = Notification.objects.filter(utilisateur=request.user, lu=False).order_by('-date_creation')[:5]
    dernieres_notes = notes.select_related('evaluation__cours__matiere').order_by('-date_saisie')[:5]
    
    context = {
        'eleve': eleve,
        'moyenne': moyenne,
        'cours_jour': cours_jour,
        'devoirs': devoirs,
        'interrogations': evaluations_a_venir,
        'evaluations_a_venir': evaluations_a_venir,
        'notifications': notifications,
        'dernieres_notes': dernieres_notes,
    }
    return render(request, 'eleve/dashboard.html', context)


@login_required
def eleve_emploi_temps(request):
    if not est_eleve(request.user):
        return redirect('login')
    eleve = request.user.eleve
    jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
    emploi = {}
    for jour in jours:
        emploi[jour] = Cours.objects.filter(classe=eleve.classe, jour=jour).order_by('heure_debut') if eleve.classe else []
    context = {'eleve': eleve, 'emploi': emploi, 'jours': jours}
    return render(request, 'eleve/emploi_temps.html', context)


@login_required
def eleve_cours_liste(request):
    if not est_eleve(request.user):
        return redirect('login')
    eleve = request.user.eleve
    cours_list = Cours.objects.filter(classe=eleve.classe).select_related('matiere', 'enseignant').order_by('jour', 'heure_debut') if eleve.classe else []
    context = {'eleve': eleve, 'cours_list': cours_list}
    return render(request, 'eleve/cours_liste.html', context)


@login_required
def eleve_cours_detail(request, cours_id):
    if not est_eleve(request.user):
        return redirect('login')
    eleve = request.user.eleve
    cours = get_object_or_404(Cours, id=cours_id, classe=eleve.classe)
    ressources = cours.ressources.all()
    context = {'eleve': eleve, 'cours': cours, 'ressources': ressources}
    return render(request, 'eleve/cours_detail.html', context)


@login_required
def telecharger_ressource(request, ressource_id):
    if not est_eleve(request.user):
        return redirect('login')
    ressource = get_object_or_404(RessourcePedagogique, id=ressource_id)
    if not ressource.fichier:
        raise Http404("Aucun fichier associé.")
    file_path = ressource.fichier.path
    if not os.path.exists(file_path):
        raise Http404("Fichier introuvable.")
    content_type, _ = mimetypes.guess_type(file_path)
    response = FileResponse(open(file_path, 'rb'), content_type=content_type or 'application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
    return response


@login_required
def eleve_devoirs(request):
    if not est_eleve(request.user):
        return redirect('login')
    eleve = request.user.eleve
    devoirs = Devoir.objects.filter(cours__classe=eleve.classe).order_by('-date_attribution') if eleve.classe else []
    soumissions = {s.devoir_id: s for s in DevoirSoumis.objects.filter(eleve=eleve)}
    context = {'eleve': eleve, 'devoirs': devoirs, 'soumissions': soumissions}
    return render(request, 'eleve/devoirs.html', context)


@login_required
def eleve_evaluations(request):
    if not est_eleve(request.user):
        return redirect('login')
    eleve = request.user.eleve
    evaluations = Evaluation.objects.filter(
        cours__classe=eleve.classe,
        type_evaluation__in=['INTERROGATION', 'EXAMEN'],
    ).select_related('cours__matiere', 'cours__enseignant').order_by('-date_evaluation') if eleve.classe else []
    soumissions = {s.evaluation_id: s for s in SoumissionEvaluation.objects.filter(eleve=eleve)}
    context = {'eleve': eleve, 'evaluations': evaluations, 'soumissions': soumissions}
    return render(request, 'eleve/evaluations.html', context)


@login_required
def resoudre_evaluation(request, evaluation_id):
    if not est_eleve(request.user):
        return redirect('login')
    eleve = request.user.eleve
    evaluation = get_object_or_404(
        Evaluation,
        id=evaluation_id,
        cours__classe=eleve.classe,
        type_evaluation__in=['INTERROGATION', 'EXAMEN'],
    )
    soumission = SoumissionEvaluation.objects.filter(evaluation=evaluation, eleve=eleve).first()
    if soumission:
        django_messages.info(request, 'Vous avez déjà envoyé cette évaluation.')
        return redirect('eleve_evaluations')
    if request.method == 'POST':
        reponse = request.POST.get('reponse', '').strip()
        fichier = request.FILES.get('fichier')
        if reponse or fichier:
            SoumissionEvaluation.objects.create(
                evaluation=evaluation,
                eleve=eleve,
                reponse=reponse,
                fichier=fichier
            )
            Notification.objects.create(
                utilisateur=evaluation.cours.enseignant.user,
                type_notification='RAPPEL',
                titre='Évaluation soumise',
                message=f'{eleve} a soumis {evaluation.titre}',
                lien=f'/enseignant/evaluations/{evaluation.id}/soumissions/'
            )
            django_messages.success(request, 'Évaluation envoyée à votre enseignant.')
            return redirect('eleve_evaluations')
        django_messages.error(request, 'Veuillez saisir une réponse ou joindre un fichier.')
    context = {'eleve': eleve, 'evaluation': evaluation}
    return render(request, 'eleve/resoudre_evaluation.html', context)


@login_required
def soumettre_devoir(request, devoir_id):
    if not est_eleve(request.user):
        return redirect('login')
    eleve = request.user.eleve
    devoir = get_object_or_404(Devoir, id=devoir_id, cours__classe=eleve.classe)
    if request.method == 'POST':
        fichier = request.FILES.get('fichier')
        commentaire = request.POST.get('commentaire', '')
        if fichier:
            DevoirSoumis.objects.update_or_create(
                devoir=devoir,
                eleve=eleve,
                defaults={'fichier': fichier, 'commentaire_eleve': commentaire, 'statut': 'SOUMIS'}
            )
            django_messages.success(request, 'Devoir soumis avec succès.')
            return redirect('eleve_devoirs')
        else:
            django_messages.error(request, 'Veuillez joindre un fichier.')
    context = {'eleve': eleve, 'devoir': devoir}
    return render(request, 'eleve/soumettre_devoir.html', context)


@login_required
def eleve_notes(request):
    if not est_eleve(request.user):
        return redirect('login')
    eleve = request.user.eleve
    context = {'eleve': eleve, **construire_bulletin(eleve)}
    return render(request, 'eleve/notes.html', context)


@login_required
def telecharger_bulletin_eleve(request):
    if not est_eleve(request.user):
        return redirect('login')
    return reponse_bulletin_html(request.user.eleve, request.user)


@login_required
def eleve_progression(request):
    if not est_eleve(request.user):
        return redirect('login')
    eleve = request.user.eleve
    notes = Note.objects.filter(eleve=eleve).select_related('evaluation__cours__matiere').order_by('date_saisie')
    progression = {}
    for note in notes:
        matiere = note.evaluation.cours.matiere.nom
        if matiere not in progression:
            progression[matiere] = []
        progression[matiere].append({'date': note.date_saisie.strftime('%d/%m'), 'valeur': float(note.valeur)})
    context = {'eleve': eleve, 'progression': progression}
    return render(request, 'eleve/progression.html', context)


@login_required
def eleve_portfolio(request):
    if not est_eleve(request.user):
        return redirect('login')
    eleve = request.user.eleve
    if request.method == 'POST':
        titre = request.POST.get('titre')
        description = request.POST.get('description')
        type_item = request.POST.get('type_item', 'PROJET')
        fichier = request.FILES.get('fichier')
        lien_externe = request.POST.get('lien_externe', '')
        date_realisation = request.POST.get('date_realisation')
        if titre and date_realisation:
            Portfolio.objects.create(
                eleve=eleve,
                titre=titre,
                description=description,
                type_item=type_item,
                fichier=fichier,
                lien_externe=lien_externe,
                date_realisation=date_realisation
            )
            django_messages.success(request, 'Élément ajouté au portfolio.')
            return redirect('eleve_portfolio')
        else:
            django_messages.error(request, 'Veuillez remplir les champs obligatoires.')
    portfolio_items = eleve.portfolio.all()
    context = {'eleve': eleve, 'portfolio_items': portfolio_items}
    return render(request, 'eleve/portfolio.html', context)


@login_required
def eleve_messages(request):
    if not est_eleve(request.user):
        return redirect('login')
    recus = Message.objects.filter(destinataire=request.user).order_by('-date_envoi')
    envoyes = Message.objects.filter(expediteur=request.user).order_by('-date_envoi')
    context = {'recus': recus, 'envoyes': envoyes}
    return render(request, 'eleve/messages.html', context)


@login_required
def envoyer_message(request):
    if not est_eleve(request.user):
        return redirect('login')
    if request.method == 'POST':
        destinataire_id = request.POST.get('destinataire')
        sujet = request.POST.get('sujet')
        contenu = request.POST.get('contenu')
        if destinataire_id and sujet and contenu:
            destinataire = get_object_or_404(contacts_messagerie(request.user), id=destinataire_id)
            creer_message_avec_notification(request.user, destinataire, sujet, contenu)
            django_messages.success(request, 'Message envoyé.')
            return redirect('eleve_messages')
    eleve = request.user.eleve
    contacts = contacts_messagerie(request.user)
    context = {'contacts': contacts}
    return render(request, 'eleve/envoyer_message.html', context)


@login_required
def lire_message(request, message_id):
    if not (est_eleve(request.user) or est_enseignant(request.user) or est_parent(request.user)):
        return redirect('login')
    message = get_object_or_404(Message, id=message_id, destinataire=request.user)
    if not message.lu:
        message.lu = True
        message.date_lecture = timezone.now()
        message.save()
    context = {'msg': message, 'retour_messages_url': lien_messages_pour(request.user)}
    return render(request, 'eleve/lire_message.html', context)


@login_required
def eleve_suivi(request):
    if not est_eleve(request.user):
        return redirect('login')
    eleve = request.user.eleve
    suivis = SuiviPedagogique.objects.filter(eleve=eleve).select_related('cours__matiere').order_by('-date_signalement')
    context = {'eleve': eleve, 'suivis': suivis}
    return render(request, 'eleve/suivi.html', context)


@login_required
def signaler_not_compris(request):
    if not est_eleve(request.user):
        return redirect('login')
    eleve = request.user.eleve
    if request.method == 'POST':
        cours_id = request.POST.get('cours')
        notion = request.POST.get('notion')
        niveau = request.POST.get('niveau', 'NON_COMPRISE')
        commentaire = request.POST.get('commentaire', '')
        if cours_id and notion:
            cours = get_object_or_404(Cours, id=cours_id, classe=eleve.classe)
            SuiviPedagogique.objects.create(
                eleve=eleve,
                cours=cours,
                notion=notion,
                niveau=niveau,
                commentaire_eleve=commentaire
            )
            Notification.objects.create(
                utilisateur=cours.enseignant.user,
                type_notification='ALERTE',
                titre='Nouveau suivi pédagogique',
                message=f'{eleve} signale une difficulté : {notion}',
                lien='/enseignant/suivis/'
            )
            django_messages.success(request, 'Signalement envoyé à votre enseignant.')
            return redirect('eleve_suivi')
        else:
            django_messages.error(request, 'Veuillez remplir les champs obligatoires.')
    cours_list = Cours.objects.filter(classe=eleve.classe).select_related('matiere') if eleve.classe else []
    context = {'eleve': eleve, 'cours_list': cours_list}
    return render(request, 'eleve/signaler_not_compris.html', context)


@login_required
def eleve_auto_evaluation(request):
    if not est_eleve(request.user):
        return redirect('login')
    eleve = request.user.eleve
    if request.method == 'POST':
        cours_id = request.POST.get('cours')
        titre = request.POST.get('titre')
        comprehension = request.POST.get('comprehension_notion', 3)
        facilite = request.POST.get('facilite_exercices', 3)
        interet = request.POST.get('interet_matiere', 3)
        difficultes = request.POST.get('points_difficultes', '')
        suggestions = request.POST.get('suggestions', '')
        if cours_id and titre:
            AutoEvaluation.objects.create(
                eleve=eleve,
                cours_id=cours_id,
                titre=titre,
                comprehension_notion=comprehension,
                facilite_exercices=facilite,
                interet_matiere=interet,
                points_difficultes=difficultes,
                suggestions=suggestions
            )
            django_messages.success(request, 'Auto-évaluation enregistrée.')
            return redirect('eleve_auto_evaluation')
        else:
            django_messages.error(request, 'Veuillez remplir les champs obligatoires.')
    auto_evaluations = eleve.auto_evaluations.select_related('cours__matiere').order_by('-date_evaluation')
    cours_list = Cours.objects.filter(classe=eleve.classe).select_related('matiere') if eleve.classe else []
    context = {'eleve': eleve, 'auto_evaluations': auto_evaluations, 'cours_list': cours_list}
    return render(request, 'eleve/auto_evaluation.html', context)


@login_required
def eleve_profil(request):
    if not est_eleve(request.user):
        return redirect('login')
    eleve = request.user.eleve
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        eleve.telephone = request.POST.get('telephone', eleve.telephone)
        eleve.save()
        django_messages.success(request, 'Profil mis à jour.')
    context = {'eleve': eleve}
    return render(request, 'eleve/profil.html', context)


@login_required
def marquer_notification_lue(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id, utilisateur=request.user)
    notif.lu = True
    notif.save()
    if est_enseignant(request.user):
        return redirect('enseignant_dashboard')
    if est_parent(request.user):
        return redirect('parent_dashboard')
    return redirect('eleve_dashboard')


# ==================== Portail Enseignant ====================

@login_required
def enseignant_dashboard(request):
    if not est_enseignant(request.user):
        return redirect('login')
    enseignant = request.user.enseignant
    cours_list = Cours.objects.filter(enseignant=enseignant).select_related('matiere', 'classe')
    devoirs = Devoir.objects.filter(cours__enseignant=enseignant).order_by('-date_attribution')[:5]
    evaluations_a_corriger = Evaluation.objects.filter(cours__enseignant=enseignant).annotate(
        notes_saisies=Count('notes', distinct=True),
        soumissions_count=Count('soumissions', distinct=True)
    ).order_by('-date_evaluation')[:5]
    messages_non_lus = Message.objects.filter(destinataire=request.user, lu=False).count()
    notifications = Notification.objects.filter(utilisateur=request.user, lu=False).order_by('-date_creation')[:5]
    total_eleves = Eleve.objects.filter(classe__cours__enseignant=enseignant).distinct().count()
    suivis_a_traiter = SuiviPedagogique.objects.filter(
        cours__enseignant=enseignant,
        resolu=False
    ).select_related('eleve__user', 'cours__matiere', 'cours__classe').order_by('-date_signalement')[:5]
    total_suivis_a_traiter = SuiviPedagogique.objects.filter(cours__enseignant=enseignant, resolu=False).count()
    context = {
        'enseignant': enseignant,
        'cours_list': cours_list,
        'devoirs': devoirs,
        'evaluations_a_corriger': evaluations_a_corriger,
        'messages_non_lus': messages_non_lus,
        'notifications': notifications,
        'total_eleves': total_eleves,
        'suivis_a_traiter': suivis_a_traiter,
        'total_suivis_a_traiter': total_suivis_a_traiter,
    }
    return render(request, 'enseignant/dashboard.html', context)


@login_required
def enseignant_suivis_liste(request):
    if not est_enseignant(request.user):
        return redirect('login')
    enseignant = request.user.enseignant
    statut = request.GET.get('statut', 'ouverts')
    suivis = SuiviPedagogique.objects.filter(cours__enseignant=enseignant).select_related(
        'eleve__user', 'cours__matiere', 'cours__classe'
    )
    if statut == 'resolus':
        suivis = suivis.filter(resolu=True)
    elif statut != 'tous':
        statut = 'ouverts'
        suivis = suivis.filter(resolu=False)
    context = {
        'enseignant': enseignant,
        'suivis': suivis.order_by('resolu', '-date_signalement'),
        'statut': statut,
        'total_ouverts': SuiviPedagogique.objects.filter(cours__enseignant=enseignant, resolu=False).count(),
        'total_resolus': SuiviPedagogique.objects.filter(cours__enseignant=enseignant, resolu=True).count(),
    }
    return render(request, 'enseignant/suivis_liste.html', context)


@login_required
def enseignant_suivi_detail(request, suivi_id):
    if not est_enseignant(request.user):
        return redirect('login')
    enseignant = request.user.enseignant
    suivi = get_object_or_404(
        SuiviPedagogique.objects.select_related('eleve__user', 'cours__matiere', 'cours__classe'),
        id=suivi_id,
        cours__enseignant=enseignant
    )
    if request.method == 'POST':
        resolu = request.POST.get('resolu') == 'on'
        suivi.niveau = request.POST.get('niveau', suivi.niveau)
        suivi.commentaire_enseignant = request.POST.get('commentaire_enseignant', '').strip()
        if suivi.date_prise_en_charge is None:
            suivi.date_prise_en_charge = timezone.now()
        suivi.resolu = resolu
        suivi.save()
        Notification.objects.create(
            utilisateur=suivi.eleve.user,
            type_notification='ALERTE',
            titre='Suivi pédagogique mis à jour',
            message=f'Votre enseignant a répondu au suivi : {suivi.notion}',
            lien='/eleve/suivi/'
        )
        django_messages.success(request, 'Suivi pédagogique mis à jour.')
        return redirect('enseignant_suivis_liste')
    context = {
        'enseignant': enseignant,
        'suivi': suivi,
        'niveaux': SuiviPedagogique.NIVEAU_DIFFICULTE,
    }
    return render(request, 'enseignant/suivi_detail.html', context)


@login_required
def enseignant_cours_liste(request):
    if not est_enseignant(request.user):
        return redirect('login')
    enseignant = request.user.enseignant
    cours = Cours.objects.filter(enseignant=enseignant).select_related('matiere', 'classe').order_by('jour', 'heure_debut')
    context = {'enseignant': enseignant, 'cours_list': cours}
    return render(request, 'enseignant/cours_liste.html', context)


@login_required
def enseignant_cours_creer(request):
    if not est_enseignant(request.user):
        return redirect('login')
    enseignant = request.user.enseignant
    if request.method == 'POST':
        matiere_id = request.POST.get('matiere')
        classe_id = request.POST.get('classe')
        titre = request.POST.get('titre', '').strip()
        jour = request.POST.get('jour')
        heure_debut = request.POST.get('heure_debut')
        heure_fin = request.POST.get('heure_fin')
        salle = request.POST.get('salle', '')
        if matiere_id and classe_id and jour and heure_debut and heure_fin:
            matiere = get_object_or_404(Matiere, id=matiere_id)
            classe = get_object_or_404(Classe, id=classe_id)
            Cours.objects.create(
                matiere=matiere,
                enseignant=enseignant,
                classe=classe,
                titre=titre or f"{matiere.nom} - {classe.nom}",
                jour=jour,
                heure_debut=heure_debut,
                heure_fin=heure_fin,
                salle=salle
            )
            django_messages.success(request, 'Cours créé avec succès.')
            return redirect('enseignant_cours_liste')
        else:
            django_messages.error(request, 'Veuillez remplir tous les champs obligatoires.')
    context = {
        'enseignant': enseignant,
        'matieres': Matiere.objects.all(),
        'classes': Classe.objects.all(),
        'jours': ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'],
    }
    return render(request, 'enseignant/cours_form.html', context)


@login_required
def enseignant_cours_modifier(request, cours_id):
    if not est_enseignant(request.user):
        return redirect('login')
    enseignant = request.user.enseignant
    cours = get_object_or_404(Cours, id=cours_id, enseignant=enseignant)
    if request.method == 'POST':
        matiere_id = request.POST.get('matiere')
        classe_id = request.POST.get('classe')
        titre = request.POST.get('titre', '').strip()
        cours.matiere_id = matiere_id
        cours.classe_id = classe_id
        if titre:
            cours.titre = titre
        elif matiere_id and classe_id:
            matiere = get_object_or_404(Matiere, id=matiere_id)
            classe = get_object_or_404(Classe, id=classe_id)
            cours.titre = f"{matiere.nom} - {classe.nom}"
        cours.jour = request.POST.get('jour')
        cours.heure_debut = request.POST.get('heure_debut')
        cours.heure_fin = request.POST.get('heure_fin')
        cours.salle = request.POST.get('salle', '')
        cours.save()
        django_messages.success(request, 'Cours modifié avec succès.')
        return redirect('enseignant_cours_liste')
    context = {
        'enseignant': enseignant,
        'cours': cours,
        'matieres': Matiere.objects.all(),
        'classes': Classe.objects.all(),
        'jours': ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'],
    }
    return render(request, 'enseignant/cours_form.html', context)


@login_required
def enseignant_cours_supprimer(request, cours_id):
    if not est_enseignant(request.user):
        return redirect('login')
    enseignant = request.user.enseignant
    cours = get_object_or_404(Cours, id=cours_id, enseignant=enseignant)
    if request.method == 'POST':
        cours.delete()
        django_messages.success(request, 'Cours supprimé avec succès.')
        return redirect('enseignant_cours_liste')
    context = {'enseignant': enseignant, 'cours': cours}
    return render(request, 'enseignant/cours_confirmer_suppression.html', context)


@login_required
def enseignant_devoirs_liste(request):
    if not est_enseignant(request.user):
        return redirect('login')
    enseignant = request.user.enseignant
    devoirs = Devoir.objects.filter(cours__enseignant=enseignant).select_related('cours', 'cours__matiere', 'cours__classe').order_by('-date_attribution')
    context = {'enseignant': enseignant, 'devoirs': devoirs}
    return render(request, 'enseignant/devoirs_liste.html', context)


@login_required
def enseignant_devoir_creer(request):
    if not est_enseignant(request.user):
        return redirect('login')
    enseignant = request.user.enseignant
    if request.method == 'POST':
        cours_id = request.POST.get('cours')
        titre = request.POST.get('titre')
        description = request.POST.get('description')
        date_rendu = request.POST.get('date_rendu')
        fichier_attache = request.FILES.get('fichier_attache')
        if cours_id and titre and date_rendu:
            Devoir.objects.create(
                cours_id=cours_id,
                titre=titre,
                description=description,
                date_rendu=date_rendu,
                fichier_attache=fichier_attache
            )
            cours = Cours.objects.get(id=cours_id)
            for eleve in Eleve.objects.filter(classe=cours.classe):
                Notification.objects.create(
                    utilisateur=eleve.user,
                    type_notification='DEVOIR',
                    titre='Nouveau devoir',
                    message=f'Nouveau devoir en {cours.matiere} : {titre}',
                    lien='/eleve/devoirs/'
                )
            django_messages.success(request, 'Devoir créé avec succès.')
            return redirect('enseignant_devoirs_liste')
        else:
            django_messages.error(request, 'Veuillez remplir tous les champs obligatoires.')
    cours_list = Cours.objects.filter(enseignant=enseignant).select_related('matiere', 'classe')
    context = {'enseignant': enseignant, 'cours_list': cours_list}
    return render(request, 'enseignant/devoir_form.html', context)


@login_required
def enseignant_evaluations_liste(request):
    if not est_enseignant(request.user):
        return redirect('login')
    enseignant = request.user.enseignant
    evaluations = Evaluation.objects.filter(cours__enseignant=enseignant).select_related(
        'cours', 'cours__matiere', 'cours__classe'
    ).annotate(soumissions_count=Count('soumissions')).order_by('-date_evaluation')
    context = {'enseignant': enseignant, 'evaluations': evaluations}
    return render(request, 'enseignant/evaluations_liste.html', context)


@login_required
def enseignant_soumissions_evaluation(request, evaluation_id):
    if not est_enseignant(request.user):
        return redirect('login')
    enseignant = request.user.enseignant
    evaluation = get_object_or_404(Evaluation, id=evaluation_id, cours__enseignant=enseignant)
    soumissions = SoumissionEvaluation.objects.filter(
        evaluation=evaluation
    ).select_related('eleve__user').order_by('-date_soumission')
    context = {'enseignant': enseignant, 'evaluation': evaluation, 'soumissions': soumissions}
    return render(request, 'enseignant/soumissions_evaluation.html', context)


@login_required
def enseignant_soumission_evaluation_detail(request, soumission_id):
    if not est_enseignant(request.user):
        return redirect('login')
    enseignant = request.user.enseignant
    soumission = get_object_or_404(
        SoumissionEvaluation.objects.select_related('evaluation__cours__matiere', 'eleve__user'),
        id=soumission_id,
        evaluation__cours__enseignant=enseignant
    )
    if request.method == 'POST':
        soumission.commentaire_enseignant = request.POST.get('commentaire_enseignant', '')
        soumission.statut = request.POST.get('statut', soumission.statut)
        soumission.save()
        django_messages.success(request, 'Soumission mise à jour.')
        return redirect('enseignant_soumissions_evaluation', evaluation_id=soumission.evaluation_id)
    context = {'enseignant': enseignant, 'soumission': soumission, 'evaluation': soumission.evaluation}
    return render(request, 'enseignant/soumission_evaluation_detail.html', context)


@login_required
def enseignant_evaluation_creer(request):
    if not est_enseignant(request.user):
        return redirect('login')
    enseignant = request.user.enseignant
    if request.method == 'POST':
        cours_id = request.POST.get('cours')
        titre = request.POST.get('titre')
        type_evaluation = request.POST.get('type_evaluation')
        date_evaluation = request.POST.get('date_evaluation')
        coefficient = request.POST.get('coefficient', 1.0)
        description = request.POST.get('description', '')
        fichier_attache = request.FILES.get('fichier_attache')
        if cours_id and titre and type_evaluation and date_evaluation:
            evaluation = Evaluation.objects.create(
                cours_id=cours_id,
                titre=titre,
                type_evaluation=type_evaluation,
                date_evaluation=date_evaluation,
                coefficient=coefficient,
                description=description,
                fichier_attache=fichier_attache
            )
            for eleve in Eleve.objects.filter(classe=evaluation.cours.classe).select_related('user'):
                Notification.objects.create(
                    utilisateur=eleve.user,
                    type_notification='RAPPEL',
                    titre='Nouvelle évaluation',
                    message=(
                        f'{evaluation.get_type_evaluation_display()} en '
                        f'{evaluation.cours.matiere} : {evaluation.titre}'
                    ),
                    lien='/eleve/',
                )
            django_messages.success(request, 'Évaluation créée avec succès.')
            return redirect('enseignant_evaluations_liste')
        else:
            django_messages.error(request, 'Veuillez remplir tous les champs obligatoires.')
    cours_list = Cours.objects.filter(enseignant=enseignant).select_related('matiere', 'classe')
    context = {
        'enseignant': enseignant,
        'cours_list': cours_list,
        'types_eval': Evaluation.TYPE_EVAL,
    }
    return render(request, 'enseignant/evaluation_form.html', context)


@login_required
def enseignant_notes_liste(request):
    if not est_enseignant(request.user):
        return redirect('login')
    enseignant = request.user.enseignant
    evaluations = Evaluation.objects.filter(cours__enseignant=enseignant).select_related('cours', 'cours__matiere')
    context = {'enseignant': enseignant, 'evaluations': evaluations}
    return render(request, 'enseignant/notes_liste.html', context)


@login_required
def enseignant_notes_saisir(request):
    if not est_enseignant(request.user):
        return redirect('login')
    enseignant = request.user.enseignant
    evaluation_id = request.GET.get('evaluation') or request.POST.get('evaluation')
    evaluation = get_object_or_404(Evaluation, id=evaluation_id, cours__enseignant=enseignant) if evaluation_id else None
    if request.method == 'POST' and evaluation:
        eleves = Eleve.objects.filter(classe=evaluation.cours.classe)
        for eleve in eleves:
            note_val = request.POST.get(f'note_{eleve.id}')
            appreciation = request.POST.get(f'appreciation_{eleve.id}', '')
            if note_val:
                Note.objects.update_or_create(
                    evaluation=evaluation,
                    eleve=eleve,
                    defaults={
                        'valeur': note_val,
                        'appreciation': appreciation,
                        'saisi_par': request.user,
                    }
                )
                Notification.objects.create(
                    utilisateur=eleve.user,
                    type_notification='NOTE',
                    titre='Nouvelle note disponible',
                    message=f'{evaluation.titre} en {evaluation.cours.matiere} : {note_val}/20',
                    lien='/eleve/notes/'
                )
        django_messages.success(request, 'Notes enregistrées avec succès.')
        return redirect('enseignant_notes_liste')
    eleves = Eleve.objects.filter(classe=evaluation.cours.classe).select_related('user') if evaluation else []
    notes_existantes = {}
    if evaluation:
        for note in Note.objects.filter(evaluation=evaluation):
            notes_existantes[note.eleve_id] = note
    moyenne_evaluation = None
    if evaluation and notes_existantes:
        total = sum(float(note.valeur) for note in notes_existantes.values())
        moyenne_evaluation = round(total / len(notes_existantes), 2)
    context = {
        'enseignant': enseignant,
        'evaluation': evaluation,
        'eleves': eleves,
        'notes_existantes': notes_existantes,
        'moyenne_evaluation': moyenne_evaluation,
    }
    return render(request, 'enseignant/notes_saisir.html', context)


@login_required
def enseignant_messages(request):
    if not est_enseignant(request.user):
        return redirect('login')
    recus = Message.objects.filter(destinataire=request.user).order_by('-date_envoi')
    envoyes = Message.objects.filter(expediteur=request.user).order_by('-date_envoi')
    context = {'recus': recus, 'envoyes': envoyes}
    return render(request, 'enseignant/messages.html', context)


@login_required
def enseignant_envoyer_message(request):
    if not est_enseignant(request.user):
        return redirect('login')
    if request.method == 'POST':
        destinataire_id = request.POST.get('destinataire')
        sujet = request.POST.get('sujet')
        contenu = request.POST.get('contenu')
        if destinataire_id and sujet and contenu:
            destinataire = get_object_or_404(contacts_messagerie(request.user), id=destinataire_id)
            creer_message_avec_notification(request.user, destinataire, sujet, contenu)
            django_messages.success(request, 'Message envoyé.')
            return redirect('enseignant_messages')
    contacts = contacts_messagerie(request.user)
    context = {'contacts': contacts}
    return render(request, 'enseignant/envoyer_message.html', context)


@login_required
def enseignant_profil(request):
    if not est_enseignant(request.user):
        return redirect('login')
    enseignant = request.user.enseignant
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        enseignant.telephone = request.POST.get('telephone', enseignant.telephone)
        enseignant.save()
        django_messages.success(request, 'Profil mis à jour.')
    context = {'enseignant': enseignant}
    return render(request, 'enseignant/profil.html', context)


# ==================== Portail Parent ====================

@login_required
def parent_dashboard(request):
    if not est_parent(request.user):
        return redirect('login')
    parent = request.user.parent
    enfants = parent.enfants.all().select_related('user', 'classe')
    messages_non_lus = Message.objects.filter(destinataire=request.user, lu=False).count()
    notifications = Notification.objects.filter(utilisateur=request.user, lu=False).order_by('-date_creation')[:5]
    notes_enfants = {}
    for enfant in enfants:
        notes_enfants[enfant.id] = Note.objects.filter(eleve=enfant).order_by('-date_saisie')[:3]
    context = {
        'parent': parent,
        'enfants': enfants,
        'messages_non_lus': messages_non_lus,
        'notifications': notifications,
        'notes_enfants': notes_enfants,
    }
    return render(request, 'parent/dashboard.html', context)


@login_required
def parent_notes_enfants(request):
    if not est_parent(request.user):
        return redirect('login')
    parent = request.user.parent
    enfants = parent.enfants.all().select_related('user', 'classe')
    notes_enfants = {}
    bulletins = {}
    moyennes_generales = {}
    totaux_generaux = {}
    maxima_generaux = {}
    pourcentages_generaux = {}
    for enfant in enfants:
        donnees = construire_bulletin(enfant)
        notes_enfants[enfant.id] = donnees['notes']
        bulletins[enfant.id] = donnees['bulletin']
        moyennes_generales[enfant.id] = donnees['moyenne_generale']
        totaux_generaux[enfant.id] = donnees['total_general']
        maxima_generaux[enfant.id] = donnees['maximum_general']
        pourcentages_generaux[enfant.id] = donnees['pourcentage_general']
    context = {
        'parent': parent,
        'enfants': enfants,
        'notes_enfants': notes_enfants,
        'bulletins': bulletins,
        'moyennes_generales': moyennes_generales,
        'totaux_generaux': totaux_generaux,
        'maxima_generaux': maxima_generaux,
        'pourcentages_generaux': pourcentages_generaux,
    }
    return render(request, 'parent/notes_enfants.html', context)


@login_required
def parent_frais_academiques(request):
    if not est_parent(request.user):
        return redirect('login')
    parent = request.user.parent
    enfants = parent.enfants.all().select_related('user', 'classe')
    if request.method == 'POST':
        eleve_id = request.POST.get('eleve')
        type_paiement = request.POST.get('type_paiement')
        eleve = get_object_or_404(enfants, id=eleve_id)
        infos = infos_frais_eleve(eleve)
        frais = infos['frais']
        if not frais:
            django_messages.error(request, 'Aucun barème de frais académiques n’est configuré pour cette classe.')
            return redirect('parent_frais_academiques')
        if type_paiement != infos['prochain_type']:
            django_messages.error(request, 'Cette étape de paiement n’est pas disponible pour cet élève.')
            return redirect('parent_frais_academiques')
        if type_paiement == 'SOLDE':
            montant = infos['reste']
        else:
            try:
                montant = Decimal(request.POST.get('montant', '0')).quantize(Decimal('0.01'))
            except (InvalidOperation, TypeError):
                montant = Decimal('0.00')
        if montant <= 0:
            django_messages.error(request, 'Le montant du paiement doit être supérieur à zéro.')
            return redirect('parent_frais_academiques')
        if montant > infos['reste']:
            django_messages.error(request, 'Le montant dépasse le solde restant.')
            return redirect('parent_frais_academiques')
        nom_payeur = request.POST.get('nom_payeur', '').strip()
        telephone_payeur = request.POST.get('telephone_payeur', '').strip()
        mode_paiement = request.POST.get('mode_paiement', 'ESPECES')
        reference_transaction = request.POST.get('reference_transaction', '').strip()
        observation = request.POST.get('observation', '').strip()
        modes_valides = [mode[0] for mode in PaiementFrais.MODE_PAIEMENT]
        if not nom_payeur:
            django_messages.error(request, 'Veuillez renseigner le nom du payeur.')
            return redirect('parent_frais_academiques')
        if mode_paiement not in modes_valides:
            django_messages.error(request, 'Le mode de paiement sélectionné est invalide.')
            return redirect('parent_frais_academiques')
        paiement = PaiementFrais.objects.create(
            eleve=eleve,
            frais=frais,
            type_paiement=type_paiement,
            montant=montant,
            nom_payeur=nom_payeur,
            telephone_payeur=telephone_payeur,
            mode_paiement=mode_paiement,
            reference_transaction=reference_transaction,
            observation=observation,
            enregistre_par=request.user
        )
        Notification.objects.create(
            utilisateur=request.user,
            type_notification='RAPPEL',
            titre='Reçu de paiement généré',
            message=f'Reçu {paiement.reference_recu} généré pour {eleve}.',
            lien=f'/parent/frais/recu/{paiement.id}/'
        )
        django_messages.success(request, 'Paiement enregistré. Le reçu a été généré automatiquement.')
        return redirect('parent_recu_paiement_frais', paiement_id=paiement.id)
    frais_enfants = [infos_frais_eleve(enfant) for enfant in enfants]
    context = {
        'parent': parent,
        'frais_enfants': frais_enfants,
        'modes_paiement': PaiementFrais.MODE_PAIEMENT,
    }
    return render(request, 'parent/frais_academiques.html', context)


@login_required
def parent_recu_paiement_frais(request, paiement_id):
    if not est_parent(request.user):
        return redirect('login')
    paiement = get_object_or_404(
        PaiementFrais.objects.select_related('eleve__user', 'eleve__classe', 'frais__classe'),
        id=paiement_id,
        eleve__parents=request.user.parent
    )
    return reponse_recu_paiement(paiement)


@login_required
def telecharger_bulletin_parent(request, eleve_id):
    if not est_parent(request.user):
        return redirect('login')
    eleve = get_object_or_404(Eleve, id=eleve_id, parents=request.user.parent)
    return reponse_bulletin_html(eleve, request.user)


@login_required
def parent_devoirs_enfants(request):
    if not est_parent(request.user):
        return redirect('login')
    parent = request.user.parent
    enfants = parent.enfants.all().select_related('user', 'classe')
    devoirs_enfants = {}
    for enfant in enfants:
        devoirs = Devoir.objects.filter(cours__classe=enfant.classe, date_rendu__gte=timezone.now()).order_by('date_rendu') if enfant.classe else []
        soumissions = {s.devoir_id: s for s in DevoirSoumis.objects.filter(eleve=enfant)}
        devoirs_enfants[enfant.id] = {'devoirs': devoirs, 'soumissions': soumissions}
    context = {'parent': parent, 'enfants': enfants, 'devoirs_enfants': devoirs_enfants}
    return render(request, 'parent/devoirs_enfants.html', context)


@login_required
def parent_messages(request):
    if not est_parent(request.user):
        return redirect('login')
    recus = Message.objects.filter(destinataire=request.user).order_by('-date_envoi')
    envoyes = Message.objects.filter(expediteur=request.user).order_by('-date_envoi')
    context = {'recus': recus, 'envoyes': envoyes}
    return render(request, 'parent/messages.html', context)


@login_required
def parent_envoyer_message(request):
    if not est_parent(request.user):
        return redirect('login')
    if request.method == 'POST':
        destinataire_id = request.POST.get('destinataire')
        sujet = request.POST.get('sujet')
        contenu = request.POST.get('contenu')
        if destinataire_id and sujet and contenu:
            destinataire = get_object_or_404(contacts_messagerie(request.user), id=destinataire_id)
            creer_message_avec_notification(request.user, destinataire, sujet, contenu)
            django_messages.success(request, 'Message envoyé.')
            return redirect('parent_messages')
    contacts = contacts_messagerie(request.user)
    context = {'contacts': contacts}
    return render(request, 'parent/envoyer_message.html', context)


@login_required
def parent_profil(request):
    if not est_parent(request.user):
        return redirect('login')
    parent = request.user.parent
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.save()
        parent.telephone = request.POST.get('telephone', parent.telephone)
        parent.save()
        django_messages.success(request, 'Profil mis à jour.')
    context = {'parent': parent}
    return render(request, 'parent/profil.html', context)


# ==================== Portail Admin ====================

@login_required
def admin_dashboard(request):
    if not est_admin(request.user):
        return redirect('login')
    stats = {
        'total_eleves': Eleve.objects.count(),
        'total_enseignants': Enseignant.objects.count(),
        'total_parents': Parent.objects.count(),
        'total_classes': Classe.objects.count(),
        'total_matieres': Matiere.objects.count(),
        'total_cours': Cours.objects.count(),
    }
    recent_connexions = JournalConnexion.objects.select_related('utilisateur').order_by('-date_connexion')[:10]
    notifications = Notification.objects.filter(utilisateur=request.user, lu=False).order_by('-date_creation')[:5]
    context = {
        'stats': stats,
        'recent_connexions': recent_connexions,
        'notifications': notifications,
    }
    return render(request, 'admin/dashboard.html', context)

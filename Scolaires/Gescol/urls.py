from django.urls import path, include
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False), name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # Portail Élève
    path('eleve/', views.eleve_dashboard, name='eleve_dashboard'),
    path('eleve/emploi-du-temps/', views.eleve_emploi_temps, name='eleve_emploi_temps'),
    path('eleve/cours/', views.eleve_cours_liste, name='eleve_cours_liste'),
    path('eleve/cours/<int:cours_id>/', views.eleve_cours_detail, name='eleve_cours_detail'),
    path('eleve/ressources/<int:ressource_id>/telecharger/', views.telecharger_ressource, name='telecharger_ressource'),
    path('eleve/devoirs/', views.eleve_devoirs, name='eleve_devoirs'),
    path('eleve/evaluations/', views.eleve_evaluations, name='eleve_evaluations'),
    path('eleve/evaluations/<int:evaluation_id>/resoudre/', views.resoudre_evaluation, name='resoudre_evaluation'),
    path('eleve/devoirs/<int:devoir_id>/soumettre/', views.soumettre_devoir, name='soumettre_devoir'),
    path('eleve/notes/', views.eleve_notes, name='eleve_notes'),
    path('eleve/notes/bulletin/telecharger/', views.telecharger_bulletin_eleve, name='telecharger_bulletin_eleve'),
    path('eleve/progression/', views.eleve_progression, name='eleve_progression'),
    path('eleve/portfolio/', views.eleve_portfolio, name='eleve_portfolio'),
    path('eleve/messages/', views.eleve_messages, name='eleve_messages'),
    path('eleve/messages/envoyer/', views.envoyer_message, name='envoyer_message'),
    path('eleve/messages/<int:message_id>/', views.lire_message, name='lire_message'),
    path('eleve/suivi/', views.eleve_suivi, name='eleve_suivi'),
    path('eleve/suivi/signaler/', views.signaler_not_compris, name='signaler_not_compris'),
    path('eleve/auto-evaluation/', views.eleve_auto_evaluation, name='eleve_auto_evaluation'),
    path('eleve/profil/', views.eleve_profil, name='eleve_profil'),
    path('eleve/notifications/<int:notif_id>/lue/', views.marquer_notification_lue, name='marquer_notification_lue'),

    # Portail Enseignant
    path('enseignant/', views.enseignant_dashboard, name='enseignant_dashboard'),
    path('enseignant/suivis/', views.enseignant_suivis_liste, name='enseignant_suivis_liste'),
    path('enseignant/suivis/<int:suivi_id>/', views.enseignant_suivi_detail, name='enseignant_suivi_detail'),
    path('enseignant/cours/', views.enseignant_cours_liste, name='enseignant_cours_liste'),
    path('enseignant/cours/creer/', views.enseignant_cours_creer, name='enseignant_cours_creer'),
    path('enseignant/cours/<int:cours_id>/modifier/', views.enseignant_cours_modifier, name='enseignant_cours_modifier'),
    path('enseignant/cours/<int:cours_id>/supprimer/', views.enseignant_cours_supprimer, name='enseignant_cours_supprimer'),
    path('enseignant/devoirs/', views.enseignant_devoirs_liste, name='enseignant_devoirs_liste'),
    path('enseignant/devoirs/creer/', views.enseignant_devoir_creer, name='enseignant_devoir_creer'),
    path('enseignant/evaluations/', views.enseignant_evaluations_liste, name='enseignant_evaluations_liste'),
    path('enseignant/evaluations/creer/', views.enseignant_evaluation_creer, name='enseignant_evaluation_creer'),
    path('enseignant/evaluations/<int:evaluation_id>/soumissions/', views.enseignant_soumissions_evaluation, name='enseignant_soumissions_evaluation'),
    path('enseignant/evaluations/soumissions/<int:soumission_id>/', views.enseignant_soumission_evaluation_detail, name='enseignant_soumission_evaluation_detail'),
    path('enseignant/notes/', views.enseignant_notes_liste, name='enseignant_notes_liste'),
    path('enseignant/notes/saisir/', views.enseignant_notes_saisir, name='enseignant_notes_saisir'),
    path('enseignant/messages/', views.enseignant_messages, name='enseignant_messages'),
    path('enseignant/messages/envoyer/', views.enseignant_envoyer_message, name='enseignant_envoyer_message'),
    path('enseignant/messages/<int:message_id>/', views.lire_message, name='enseignant_lire_message'),
    path('enseignant/profil/', views.enseignant_profil, name='enseignant_profil'),

    # Portail Parent
    path('parent/', views.parent_dashboard, name='parent_dashboard'),
    path('parent/notes/', views.parent_notes_enfants, name='parent_notes_enfants'),
    path('parent/notes/<int:eleve_id>/bulletin/telecharger/', views.telecharger_bulletin_parent, name='telecharger_bulletin_parent'),
    path('parent/frais/', views.parent_frais_academiques, name='parent_frais_academiques'),
    path('parent/frais/recu/<int:paiement_id>/', views.parent_recu_paiement_frais, name='parent_recu_paiement_frais'),
    path('parent/devoirs/', views.parent_devoirs_enfants, name='parent_devoirs_enfants'),
    path('parent/messages/', views.parent_messages, name='parent_messages'),
    path('parent/messages/envoyer/', views.parent_envoyer_message, name='parent_envoyer_message'),
    path('parent/messages/<int:message_id>/', views.lire_message, name='parent_lire_message'),
    path('parent/profil/', views.parent_profil, name='parent_profil'),

    # Portail Admin
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Password Reset (no conflict with logout)
    path('reset-mot-de-passe/', include('django.contrib.auth.urls')),
]

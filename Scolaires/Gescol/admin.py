from django.contrib import admin
from .models import (
    Niveau, Classe, Matiere, Enseignant, Eleve, Parent,
    Cours, RessourcePedagogique, Devoir, DevoirSoumis,
    Competence, Evaluation, Note, Portfolio,
    SoumissionEvaluation, Message, Notification, SuiviPedagogique,
    AutoEvaluation, FraisAcademique, PaiementFrais, JournalConnexion
)

admin.site.site_header = 'Gescol Administration'
admin.site.site_title = 'Gescol Admin'
admin.site.index_title = 'Pilotage de la gestion scolaire'


@admin.register(Niveau)
class NiveauAdmin(admin.ModelAdmin):
    list_display = ('nom',)
    search_fields = ('nom',)


@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ('nom', 'niveau', 'annee_scolaire')
    list_filter = ('niveau', 'annee_scolaire')
    search_fields = ('nom',)


@admin.register(Matiere)
class MatiereAdmin(admin.ModelAdmin):
    list_display = ('nom', 'code')
    search_fields = ('nom', 'code')


@admin.register(Enseignant)
class EnseignantAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'specialite', 'telephone', 'actif')
    list_filter = ('actif', 'specialite')
    search_fields = ('user__first_name', 'user__last_name', 'user__username')


@admin.register(Eleve)
class EleveAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'matricule', 'classe', 'actif', 'date_inscription')
    list_filter = ('actif', 'classe')
    search_fields = ('user__first_name', 'user__last_name', 'matricule')
    readonly_fields = ('date_inscription',)


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'telephone', 'actif')
    list_filter = ('actif',)
    search_fields = ('user__first_name', 'user__last_name', 'user__username')
    filter_horizontal = ('enfants',)


@admin.register(Cours)
class CoursAdmin(admin.ModelAdmin):
    list_display = ('titre', 'matiere', 'classe', 'enseignant', 'jour', 'heure_debut', 'heure_fin')
    list_filter = ('jour', 'matiere', 'classe')
    search_fields = ('titre', 'matiere__nom')


@admin.register(RessourcePedagogique)
class RessourcePedagogiqueAdmin(admin.ModelAdmin):
    list_display = ('titre', 'cours', 'type_ressource', 'date_ajout')
    list_filter = ('type_ressource',)
    search_fields = ('titre', 'cours__titre')


@admin.register(Devoir)
class DevoirAdmin(admin.ModelAdmin):
    list_display = ('titre', 'cours', 'date_attribution', 'date_rendu')
    list_filter = ('cours__matiere',)
    search_fields = ('titre', 'description')


@admin.register(DevoirSoumis)
class DevoirSoumisAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'devoir', 'statut', 'date_soumission', 'note')
    list_filter = ('statut',)
    search_fields = ('eleve__user__first_name', 'eleve__user__last_name', 'devoir__titre')


@admin.register(Competence)
class CompetenceAdmin(admin.ModelAdmin):
    list_display = ('nom', 'matiere', 'coefficient')
    list_filter = ('matiere',)


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('titre', 'cours', 'type_evaluation', 'date_evaluation', 'coefficient')
    list_filter = ('type_evaluation',)


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'evaluation', 'valeur', 'date_saisie')
    list_filter = ('evaluation__type_evaluation',)
    search_fields = ('eleve__user__first_name', 'eleve__user__last_name')


@admin.register(SoumissionEvaluation)
class SoumissionEvaluationAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'evaluation', 'statut', 'date_soumission')
    list_filter = ('statut', 'evaluation__type_evaluation')
    search_fields = ('eleve__user__first_name', 'eleve__user__last_name', 'evaluation__titre')


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'titre', 'type_item', 'date_realisation')
    list_filter = ('type_item',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('expediteur', 'destinataire', 'sujet', 'date_envoi', 'lu')
    list_filter = ('lu',)
    search_fields = ('sujet', 'contenu')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'type_notification', 'titre', 'date_creation', 'lu')
    list_filter = ('type_notification', 'lu')


@admin.register(SuiviPedagogique)
class SuiviPedagogiqueAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'notion', 'niveau', 'date_signalement', 'resolu')
    list_filter = ('niveau', 'resolu')


@admin.register(AutoEvaluation)
class AutoEvaluationAdmin(admin.ModelAdmin):
    list_display = ('eleve', 'cours', 'titre', 'date_evaluation')


@admin.register(FraisAcademique)
class FraisAcademiqueAdmin(admin.ModelAdmin):
    list_display = ('libelle', 'classe', 'annee_scolaire', 'montant_total')
    list_filter = ('annee_scolaire', 'classe')
    search_fields = ('libelle', 'classe__nom')


@admin.register(PaiementFrais)
class PaiementFraisAdmin(admin.ModelAdmin):
    list_display = ('reference_recu', 'eleve', 'frais', 'type_paiement', 'montant', 'mode_paiement', 'nom_payeur', 'date_paiement')
    list_filter = ('type_paiement', 'mode_paiement', 'frais__annee_scolaire', 'frais__classe')
    search_fields = ('reference_recu', 'reference_transaction', 'nom_payeur', 'eleve__matricule', 'eleve__user__first_name', 'eleve__user__last_name')
    readonly_fields = ('reference_recu', 'date_paiement')


@admin.register(JournalConnexion)
class JournalConnexionAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'date_connexion', 'adresse_ip', 'succes')
    list_filter = ('succes',)


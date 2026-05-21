from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import os
import random


def generer_matricule():
    """Génère un numéro de matricule unique à 7 caractères (format: ELV + 4 chiffres)."""
    while True:
        chiffres = ''.join(random.choices('0123456789', k=4))
        matricule = f"ELV{chiffres}"
        if not Eleve.objects.filter(matricule=matricule).exists():
            return matricule


class Niveau(models.Model):
    nom = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Niveau'
        verbose_name_plural = 'Niveaux'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Classe(models.Model):
    nom = models.CharField(max_length=50)
    niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE, related_name='classes')
    annee_scolaire = models.CharField(max_length=20, default='2024-2025')

    class Meta:
        verbose_name = 'Classe'
        verbose_name_plural = 'Classes'
        unique_together = ['nom', 'annee_scolaire']
        ordering = ['niveau', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.annee_scolaire})"


class Matiere(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Matière'
        verbose_name_plural = 'Matières'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Enseignant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='enseignant')
    telephone = models.CharField(max_length=20, blank=True)
    specialite = models.ForeignKey(Matiere, on_delete=models.SET_NULL, null=True, blank=True, related_name='enseignants')
    date_embauche = models.DateField(null=True, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Enseignant'
        verbose_name_plural = 'Enseignants'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"


class Eleve(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='eleve')
    matricule = models.CharField(max_length=30, unique=True)
    telephone = models.CharField(max_length=20, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    classe = models.ForeignKey(Classe, on_delete=models.SET_NULL, null=True, blank=True, related_name='eleves')
    actif = models.BooleanField(default=True)
    date_inscription = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Élève'
        verbose_name_plural = 'Élèves'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.matricule})"

    def moyenne_generale(self):
        notes = Note.objects.filter(eleve=self)
        if notes.exists():
            return round(notes.aggregate(models.Avg('valeur'))['valeur__avg'], 2)
        return None


class Parent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent')
    telephone = models.CharField(max_length=20, blank=True)
    enfants = models.ManyToManyField(Eleve, related_name='parents', blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Parent'
        verbose_name_plural = 'Parents'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"


class Cours(models.Model):
    JOURS_SEMAINE = [
        ('Lundi', 'Lundi'),
        ('Mardi', 'Mardi'),
        ('Mercredi', 'Mercredi'),
        ('Jeudi', 'Jeudi'),
        ('Vendredi', 'Vendredi'),
        ('Samedi', 'Samedi'),
    ]

    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, related_name='cours')
    enseignant = models.ForeignKey(Enseignant, on_delete=models.CASCADE, related_name='cours')
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='cours')
    titre = models.CharField(max_length=200)
    contenu = models.TextField(blank=True)
    jour = models.CharField(max_length=10, choices=JOURS_SEMAINE)
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    salle = models.CharField(max_length=50, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cours'
        verbose_name_plural = 'Cours'
        ordering = ['jour', 'heure_debut']

    def __str__(self):
        return f"{self.matiere} - {self.classe} ({self.jour} {self.heure_debut})"


class RessourcePedagogique(models.Model):
    TYPE_RESSOURCE = [
        ('COURS', 'Support de cours'),
        ('EXERCICE', 'Exercice'),
        ('CORRIGE', 'Corrigé'),
        ('DOCUMENT', 'Document général'),
        ('VIDEO', 'Vidéo'),
        ('LIEN', 'Lien externe'),
    ]

    cours = models.ForeignKey(Cours, on_delete=models.CASCADE, related_name='ressources')
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    type_ressource = models.CharField(max_length=20, choices=TYPE_RESSOURCE, default='COURS')
    fichier = models.FileField(upload_to='ressources/%Y/%m/', blank=True, null=True)
    lien_externe = models.URLField(blank=True)
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ressource Pédagogique'
        verbose_name_plural = 'Ressources Pédagogiques'
        ordering = ['-date_ajout']

    def __str__(self):
        return self.titre

    def filename(self):
        if self.fichier:
            return os.path.basename(self.fichier.name)
        return None


class Devoir(models.Model):
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE, related_name='devoirs')
    titre = models.CharField(max_length=200)
    description = models.TextField()
    date_attribution = models.DateTimeField(auto_now_add=True)
    date_rendu = models.DateTimeField()
    fichier_attache = models.FileField(upload_to='devoirs/consignes/%Y/%m/', blank=True, null=True)

    class Meta:
        verbose_name = 'Devoir'
        verbose_name_plural = 'Devoirs'
        ordering = ['-date_attribution']

    def __str__(self):
        return f"{self.titre} ({self.cours.matiere})"

    def est_en_retard(self):
        return timezone.now() > self.date_rendu


class DevoirSoumis(models.Model):
    STATUT_SOUMISSION = [
        ('SOUMIS', 'Soumis'),
        ('CORRIGE', 'Corrigé'),
        ('RETOURNE', 'Retourné pour modification'),
    ]

    devoir = models.ForeignKey(Devoir, on_delete=models.CASCADE, related_name='soumissions')
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='devoirs_soumis')
    fichier = models.FileField(upload_to='devoirs/soumis/%Y/%m/')
    commentaire_eleve = models.TextField(blank=True)
    date_soumission = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=STATUT_SOUMISSION, default='SOUMIS')
    note = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    commentaire_enseignant = models.TextField(blank=True)
    date_correction = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Devoir Soumis'
        verbose_name_plural = 'Devoirs Soumis'
        unique_together = ['devoir', 'eleve']
        ordering = ['-date_soumission']

    def __str__(self):
        return f"{self.eleve} - {self.devoir}"


class Competence(models.Model):
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, related_name='competences')
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    coefficient = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)

    class Meta:
        verbose_name = 'Compétence'
        verbose_name_plural = 'Compétences'
        ordering = ['matiere', 'nom']

    def __str__(self):
        return f"{self.matiere} - {self.nom}"


class Evaluation(models.Model):
    TYPE_EVAL = [
        ('DEVOIR', 'Devoir'),
        ('INTERROGATION', 'Interrogation'),
        ('EXAMEN', 'Examen'),
        ('PROJET', 'Projet'),
        ('PARTICIPATION', 'Participation'),
    ]

    cours = models.ForeignKey(Cours, on_delete=models.CASCADE, related_name='evaluations')
    titre = models.CharField(max_length=200)
    type_evaluation = models.CharField(max_length=20, choices=TYPE_EVAL, default='DEVOIR')
    date_evaluation = models.DateField()
    coefficient = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    description = models.TextField(blank=True)
    fichier_attache = models.FileField(upload_to='evaluations/consignes/%Y/%m/', blank=True, null=True)

    class Meta:
        verbose_name = 'Évaluation'
        verbose_name_plural = 'Évaluations'
        ordering = ['-date_evaluation']

    def __str__(self):
        return f"{self.titre} ({self.cours.matiere})"


class Note(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name='notes')
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='notes')
    competence = models.ForeignKey(Competence, on_delete=models.SET_NULL, null=True, blank=True, related_name='notes')
    valeur = models.DecimalField(max_digits=5, decimal_places=2)
    appreciation = models.TextField(blank=True)
    date_saisie = models.DateTimeField(auto_now_add=True)
    saisi_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'Note'
        verbose_name_plural = 'Notes'
        unique_together = ['evaluation', 'eleve']
        ordering = ['-date_saisie']

    def __str__(self):
        return f"{self.eleve} - {self.evaluation}: {self.valeur}"


class SoumissionEvaluation(models.Model):
    STATUT_SOUMISSION = [
        ('SOUMIS', 'Soumis'),
        ('CORRIGE', 'Corrigé'),
    ]

    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name='soumissions')
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='evaluations_soumises')
    reponse = models.TextField()
    fichier = models.FileField(upload_to='evaluations/soumissions/%Y/%m/', blank=True, null=True)
    date_soumission = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=STATUT_SOUMISSION, default='SOUMIS')
    commentaire_enseignant = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Soumission d’évaluation'
        verbose_name_plural = 'Soumissions d’évaluations'
        unique_together = ['evaluation', 'eleve']
        ordering = ['-date_soumission']

    def __str__(self):
        return f"{self.eleve} - {self.evaluation}"


class Portfolio(models.Model):
    TYPE_PORTFOLIO = [
        ('PROJET', 'Projet scolaire'),
        ('CERTIFICATION', 'Certification'),
        ('EXTRA_SCO', 'Accomplissement extra-scolaire'),
        ('AUTRE', 'Autre'),
    ]

    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='portfolio')
    titre = models.CharField(max_length=200)
    description = models.TextField()
    type_item = models.CharField(max_length=20, choices=TYPE_PORTFOLIO, default='PROJET')
    fichier = models.FileField(upload_to='portfolio/%Y/%m/', blank=True, null=True)
    lien_externe = models.URLField(blank=True)
    date_realisation = models.DateField()
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Portfolio'
        verbose_name_plural = 'Portfolios'
        ordering = ['-date_ajout']

    def __str__(self):
        return f"{self.eleve} - {self.titre}"


class Message(models.Model):
    expediteur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_envoyes')
    destinataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_recus')
    sujet = models.CharField(max_length=200)
    contenu = models.TextField()
    date_envoi = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)
    date_lecture = models.DateTimeField(null=True, blank=True)
    devoir_associe = models.ForeignKey(Devoir, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    note_associee = models.ForeignKey(Note, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')

    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['-date_envoi']

    def __str__(self):
        return f"De: {self.expediteur} À: {self.destinataire} - {self.sujet}"


class Notification(models.Model):
    TYPE_NOTIF = [
        ('DEVOIR', 'Nouveau devoir'),
        ('NOTE', 'Nouvelle note'),
        ('MESSAGE', 'Nouveau message'),
        ('COURS', 'Modification de cours'),
        ('RAPPEL', 'Rappel'),
        ('ALERTE', 'Alerte pédagogique'),
    ]

    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type_notification = models.CharField(max_length=20, choices=TYPE_NOTIF)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)
    lien = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.utilisateur} - {self.titre}"


class SuiviPedagogique(models.Model):
    NIVEAU_DIFFICULTE = [
        ('NON_COMPRISE', 'Non comprise'),
        ('PARTIELLEMENT', 'Partiellement comprise'),
        ('COMPRISE', 'Comprise'),
        ('MAITRISEE', 'Maîtrisée'),
    ]

    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='suivi_pedagogique')
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE, related_name='suivi')
    notion = models.CharField(max_length=200)
    niveau = models.CharField(max_length=20, choices=NIVEAU_DIFFICULTE, default='NON_COMPRISE')
    commentaire_eleve = models.TextField(blank=True)
    commentaire_enseignant = models.TextField(blank=True)
    date_signalement = models.DateTimeField(auto_now_add=True)
    date_prise_en_charge = models.DateTimeField(null=True, blank=True)
    resolu = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Suivi Pédagogique'
        verbose_name_plural = 'Suivis Pédagogiques'
        ordering = ['-date_signalement']

    def __str__(self):
        return f"{self.eleve} - {self.notion} ({self.niveau})"


class AutoEvaluation(models.Model):
    NIVEAU_CONFIDENCE = [
        (1, 'Très insuffisant'),
        (2, 'Insuffisant'),
        (3, 'Passable'),
        (4, 'Bien'),
        (5, 'Très bien'),
    ]

    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='auto_evaluations')
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE, related_name='auto_evaluations')
    titre = models.CharField(max_length=200)
    comprehension_notion = models.IntegerField(choices=NIVEAU_CONFIDENCE, default=3)
    facilite_exercices = models.IntegerField(choices=NIVEAU_CONFIDENCE, default=3)
    interet_matiere = models.IntegerField(choices=NIVEAU_CONFIDENCE, default=3)
    points_difficultes = models.TextField(blank=True)
    suggestions = models.TextField(blank=True)
    date_evaluation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Auto-Évaluation'
        verbose_name_plural = 'Auto-Évaluations'
        ordering = ['-date_evaluation']

    def __str__(self):
        return f"{self.eleve} - {self.cours.matiere} ({self.date_evaluation.date()})"


class FraisAcademique(models.Model):
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='frais_academiques')
    annee_scolaire = models.CharField(max_length=20)
    libelle = models.CharField(max_length=150, default='Frais académiques')
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Frais Académique'
        verbose_name_plural = 'Frais Académiques'
        unique_together = ['classe', 'annee_scolaire']
        ordering = ['classe__nom', '-annee_scolaire']

    def __str__(self):
        return f"{self.libelle} - {self.classe} ({self.annee_scolaire})"


class PaiementFrais(models.Model):
    TYPE_PAIEMENT = [
        ('ACOMPTE', 'Acompte'),
        ('SOLDE', 'Solde'),
    ]
    MODE_PAIEMENT = [
        ('ESPECES', 'Espèces'),
        ('MOBILE_MONEY', 'Mobile money'),
        ('VIREMENT', 'Virement bancaire'),
        ('CARTE', 'Carte bancaire'),
    ]

    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='paiements_frais')
    frais = models.ForeignKey(FraisAcademique, on_delete=models.CASCADE, related_name='paiements')
    type_paiement = models.CharField(max_length=20, choices=TYPE_PAIEMENT)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    nom_payeur = models.CharField(max_length=150)
    telephone_payeur = models.CharField(max_length=30, blank=True)
    mode_paiement = models.CharField(max_length=20, choices=MODE_PAIEMENT, default='ESPECES')
    reference_transaction = models.CharField(max_length=80, blank=True)
    observation = models.TextField(blank=True)
    reference_recu = models.CharField(max_length=40, unique=True, blank=True)
    date_paiement = models.DateTimeField(auto_now_add=True)
    enregistre_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='paiements_frais_enregistres')

    class Meta:
        verbose_name = 'Paiement de Frais'
        verbose_name_plural = 'Paiements de Frais'
        unique_together = ['eleve', 'frais', 'type_paiement']
        ordering = ['-date_paiement']

    def save(self, *args, **kwargs):
        if not self.reference_recu:
            prefix = timezone.now().strftime('RECU%Y%m%d')
            dernier = PaiementFrais.objects.filter(reference_recu__startswith=prefix).count() + 1
            self.reference_recu = f"{prefix}-{dernier:04d}"
        self.montant = Decimal(self.montant).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference_recu} - {self.eleve} - {self.get_type_paiement_display()}"


class JournalConnexion(models.Model):
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='journaux_connexion', null=True, blank=True)
    date_connexion = models.DateTimeField(auto_now_add=True)
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    navigateur = models.CharField(max_length=200, blank=True)
    succes = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Journal de Connexion'
        verbose_name_plural = 'Journaux de Connexion'
        ordering = ['-date_connexion']

    def __str__(self):
        return f"{self.utilisateur} - {self.date_connexion}"


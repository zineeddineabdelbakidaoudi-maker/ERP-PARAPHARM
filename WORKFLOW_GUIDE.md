# Guide d'Utilisation — ParaFarm ERP

Bienvenue dans le guide d'utilisation complet de ParaFarm ERP. Ce manuel vous accompagnera pas à pas dans l'utilisation de tous les modules de l'application.

## 1. Connexion & Navigation
- **Connexion** : Lancez l'application et entrez votre nom d'utilisateur et votre mot de passe sur l'écran d'accueil. Cliquez sur "Se connecter". En cas d'oubli, contactez votre administrateur.
- **Navigation** : Le menu principal est situé sur la gauche de l'écran (ou en haut selon la configuration). Il vous permet d'accéder rapidement à tous les modules (Ventes, Achats, Stocks, Finances, etc.). Utilisez la barre de recherche rapide en haut pour trouver des clients, fournisseurs ou articles.

## 2. Tableau de Bord
Le tableau de bord est votre écran d'accueil après connexion. Il vous offre une vue d'ensemble de l'activité de votre entreprise :
- **Indicateurs clés** : Chiffre d'affaires du jour, nombre de ventes, alertes de stock, créances échues.
- **Graphiques** : Évolution des ventes sur la semaine/le mois.
- Vous pouvez personnaliser l'affichage des widgets selon vos préférences dans les options.

## 3. Point de Vente (POS)
Le module POS est conçu pour les ventes au comptoir rapides.

- **Comment créer une vente** :
  1. Allez dans le menu **Ventes > Point de Vente**.
  2. Scannez le code-barres d'un article ou utilisez la barre de recherche pour l'ajouter au panier.
  3. Ajustez les quantités avec les boutons `+` / `-` ou en tapant la quantité directement.

- **Comment appliquer une remise** :
  1. Cliquez sur le champ "Remise" situé en bas du ticket.
  2. Entrez le pourcentage (%) ou le montant fixe de la remise.
  3. La remise peut aussi s'appliquer ligne par ligne en cliquant sur le prix d'un article spécifique.

- **Comment encaisser (Espèce / Chèque / Terme)** :
  1. Cliquez sur le bouton **Encaisser** (ou tapez F12).
  2. Choisissez le mode de paiement :
     - **Espèce** : Saisissez le montant remis par le client, le système calculera la monnaie à rendre.
     - **Chèque** : Saisissez le numéro du chèque et la banque.
     - **Terme** (Crédit) : Associez un client à la vente et validez.

- **Comment faire un paiement partiel** :
  1. Lors de l'encaissement, entrez un montant inférieur au total à payer dans "Espèce" ou "Chèque".
  2. Le reste sera automatiquement enregistré comme une créance (nécessite l'identification du client).

## 4. Bons de Livraison (BL)
Le BL est utilisé pour les ventes en gros ou les livraisons différées.

- **Comment sélectionner un client** :
  1. Allez dans **Ventes > Bon de Livraison > Nouveau BL**.
  2. Dans la zone "Client", tapez le nom ou le code du client. Sélectionnez-le dans la liste déroulante.

- **Comment ajouter des articles** :
  1. Scannez ou recherchez l'article dans la barre de recherche des lignes.
  2. Saisissez la quantité et vérifiez le prix unitaire.
  3. Appuyez sur **Entrée** pour ajouter la ligne.

- **Comment appliquer TVA** :
  1. Cochez la case "TVA" située en bas du document ou au niveau des lignes si les articles ont des taux de TVA différents.
  2. Le système calculera automatiquement le montant HT, le montant de la TVA et le montant TTC.

- **Comment saisir un versement/acompte** :
  1. Avant de valider, allez dans la section "Paiement / Versement".
  2. Entrez le montant versé par le client et sélectionnez le mode de paiement.
  3. Le solde restant mettra automatiquement à jour la créance du client.

- **Comment valider et imprimer** :
  1. Vérifiez toutes les informations.
  2. Cliquez sur **Valider**.
  3. Une fenêtre de confirmation s'affiche avec le bouton **Imprimer** pour générer le format A4, A5 ou ticket selon votre configuration.

## 5. Commandes Client
- **Créer une commande** : Allez dans **Ventes > Commandes > Nouvelle Commande**. Sélectionnez votre client.
- **Ajouter des articles** : Saisissez les articles souhaités de la même manière que pour un BL.
- **Valider → Compléter** :
  1. Cliquez sur **Valider** pour enregistrer la commande. Le stock n'est pas encore déduit.
  2. Pour transformer la commande en livraison, cliquez sur **Compléter en BL** ou **Générer Facture** selon votre flux de travail.

## 6. Factures
- **Créer une facture** : Allez dans **Ventes > Factures > Nouvelle Facture**. Sélectionnez le client. (Vous pouvez aussi importer un ou plusieurs BL validés).
- **Ajouter lignes avec TVA** : Ajoutez les articles. Assurez-vous que les taux de TVA sont correctement configurés sur chaque ligne d'article pour l'édition de la facture.
- **Valider → Imprimer PDF** : Cliquez sur **Valider**. Le système attribue un numéro de facture unique (ex: FAC-2026-001). Cliquez sur **Imprimer / PDF** pour générer le document officiel.

## 7. Avoirs Client
En cas de retour de marchandise par un client :
1. Allez dans **Ventes > Avoirs > Nouvel Avoir**.
2. Sélectionnez le client. Vous pouvez lier l'avoir à un BL ou une facture existante.
3. Ajoutez les articles retournés.
4. Validez l'avoir. Le montant viendra automatiquement en déduction de la créance du client ou pourra être remboursé ultérieurement. Le stock est réintégré.

## 8. Clients
- **Créer / Modifier un client (tous les champs)** :
  1. Allez dans **Tiers > Clients**. Cliquez sur **Nouveau Client**.
  2. Renseignez les informations : Code, Nom/Raison Sociale, Adresse, Téléphone, Email, NIF/STAT/RC (pour la facturation), Plafond de crédit. Cliquez sur **Sauvegarder**.
  3. Pour modifier, double-cliquez sur un client dans la liste.

- **Voir la Fiche Client (créances, versements, retours)** :
  1. Dans la liste des clients, sélectionnez un client et cliquez sur **Fiche Client**.
  2. Vous y verrez l'historique complet : Solde actuel, liste des BL/Factures, détails des versements effectués, et historique des retours/avoirs.

- **Objectifs client** :
  Dans l'onglet "Objectifs" de la fiche client, vous pouvez définir un volume de chiffre d'affaires à atteindre mensuellement ou annuellement pour lui accorder des remises spéciales.

## 9. Créances (Dettes Clients)
- Allez dans **Finances > Créances Clients**.
- Vous y trouverez la liste de tous les clients avec un solde débiteur.
- Vous pouvez filtrer par date d'échéance.
- Pour enregistrer un paiement groupé, sélectionnez le client, cliquez sur **Nouveau Règlement**, saisissez le montant et ventilez-le sur les différentes factures/BL impayés.

## 10. Achats — Bons de Commande Fournisseur
- Pour passer commande à un fournisseur : **Achats > Commandes Fournisseur > Nouvelle Commande**.
- Sélectionnez le fournisseur, ajoutez les articles avec les quantités souhaitées et les coûts d'achat estimés.
- Validez et envoyez la commande au fournisseur (par email ou impression).

## 11. Réceptions (BR)
- Lorsqu'une marchandise arrive : **Achats > Bons de Réception > Nouveau BR**.
- **Sélectionnez le fournisseur**. (Vous pouvez importer une commande existante pour gagner du temps).
- Vérifiez que les quantités reçues correspondent aux quantités facturées par le fournisseur. Mettez à jour le coût d'achat si nécessaire (cela mettra à jour le PUMP).
- Validez pour que le stock soit mis à jour instantanément.

## 12. Retours Fournisseur
- En cas de marchandise défectueuse ou erreur de livraison : **Achats > Retours > Nouveau Retour**.
- Sélectionnez le fournisseur et les articles à retourner.
- La validation déduira les articles de votre stock et créera un avoir côté fournisseur (réduisant votre dette).

## 13. Fournisseurs & Fiche Fournisseur
- **Tiers > Fournisseurs**.
- Fonctionne exactement comme le module client.
- La **Fiche Fournisseur** permet de voir l'historique des achats, les règlements effectués et le solde dû (vos dettes).

## 14. Dettes Fournisseurs
- Allez dans **Finances > Dettes Fournisseurs**.

- **Comment faire un versement fournisseur** :
  1. Sélectionnez un fournisseur ayant un solde créditeur.
  2. Cliquez sur **Nouveau Décaissement**.
  3. Saisissez le montant, le mode de paiement (chèque, virement, espèce) et validez. Le solde du fournisseur diminuera.

- **Comment appliquer une remise globale** :
  1. Si un fournisseur vous accorde une remise globale exceptionnelle, vous pouvez l'enregistrer depuis le module Dettes ou lors de la saisie d'un Bon de Réception dans la case "Remise Globale".

## 15. Entrepôts & Inventaire
- **Entrepôts** : Dans **Stocks > Entrepôts**, vous pouvez créer plusieurs lieux de stockage (ex: Magasin, Dépôt Principal). Vous pouvez faire des transferts inter-dépôts.
- **Inventaire** :
  1. Allez dans **Stocks > Inventaire Périodique**.
  2. Lancez une nouvelle session d'inventaire.
  3. Saisissez les quantités réelles comptées sur le terrain.
  4. Validez l'inventaire : le système générera automatiquement des mouvements de "Perte" ou de "Surplus" pour ajuster le stock informatique au stock réel.

## 16. Logistique — Véhicules & Tournées
- Allez dans **Logistique > Flotte & Tournées**.
- **Véhicules** : Enregistrez vos camions/fourgonnettes de livraison.
- **Tournées** : Assignez des BL validés à un chauffeur et à un véhicule pour organiser l'itinéraire de livraison de la journée. Imprimez le bon de chargement pour le livreur.

## 17. Finances — Caisse
- **Finances > Mouvements de Caisse**.
- Visualisez toutes les entrées (ventes POS, versements clients) et sorties (dépenses, versements fournisseurs, retraits).
- **Fermeture de caisse (Z)** : À la fin de la journée, effectuez un "Arrêt de caisse". Le système compare le montant théorique calculé et le montant réel compté. Enregistrez les écarts de caisse éventuels.

## 18. Rapports & Générateur
- Accédez à **Rapports**.
- Vous y trouverez de nombreux rapports prédéfinis : Chiffre d'affaires par article/client, marges bénéficiaires, état des stocks, journal des ventes.
- **Générateur** : Utilisez le générateur de requêtes pour créer des rapports sur mesure en sélectionnant les colonnes et les filtres souhaités, puis exportez vers Excel ou PDF.

## 19. Banque
- **Finances > Banque**.
- Suivez le solde de vos comptes bancaires.
- Enregistrez les remises de chèques (dépôt des chèques clients à la banque).
- Effectuez vos rapprochements bancaires mensuels.

## 20. Facturation & Fiscal
- Ce module centralise tous les documents à transmettre à la comptabilité.
- Générez le **Journal des Ventes**, le **Journal des Achats** et la **Déclaration de TVA** sur une période donnée.
- Exportez les données vers des formats standards compatibles avec les logiciels comptables classiques.

## 21. Options & Administration
- **Administration > Paramètres**.
- **Utilisateurs & Droits** : Créez des comptes utilisateurs et limitez leurs accès (ex: empêcher un caissier de modifier un prix ou de voir les marges).
- **Configuration** : Paramétrez les informations de votre société, le logo, les formats d'impression, les taux de TVA par défaut, la gestion du code-barres.

## 22. Objectifs
- **Ressources Humaines / Commerciaux > Objectifs**.
- Définissez des objectifs de vente pour vos commerciaux ou magasins.
- Suivez en temps réel le taux de réalisation via un tableau de bord spécifique pour motiver les équipes.

## 23. Raccourcis Clavier (liste complète)
Gagnez du temps en utilisant le clavier, particulièrement au Point de Vente :

- **F1** : Ouvrir l'Aide
- **F2** : Nouvelle Vente / Nouveau Document
- **F3** : Focus sur la barre de recherche article
- **F4** : Modifier la quantité de la ligne sélectionnée
- **F5** : Actualiser / Rafraîchir l'écran
- **F6** : Modifier le prix de la ligne (si autorisé)
- **F7** : Appliquer une remise globale
- **F8** : Sélectionner un client
- **F9** : Mettre la vente en attente
- **F10** : Rappeler une vente en attente
- **F11** : Annuler la ligne sélectionnée / Supprimer l'article
- **F12** : Encaisser / Valider
- **Échap (Esc)** : Annuler le ticket / Fermer la fenêtre active
- **Entrée** : Valider la saisie / Ajouter au panier
- **Ctrl + P** : Réimprimer le dernier ticket/document
- **Ctrl + S** : Sauvegarder
- **Ctrl + F** : Recherche avancée

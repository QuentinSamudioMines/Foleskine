# FoleskineNotes

FoleskineNotes est une application de prise de notes en **style carnet Foleskine**. Elle permet de créer, organiser et éditer plusieurs carnets numériques avec un éditeur de texte simple et élégant, incluant un mode **pleine écran** pour l'écriture immersive.  

---

## Fonctionnalités

- Créer, renommer, supprimer des carnets.
- Ajouter, supprimer et naviguer entre les pages.
- Autosauvegarde automatique du contenu toutes les 30 secondes et après chaque saisie.
- Importer et exporter des carnets au format JSON.
- Mode **pleine écran** minimaliste pour se concentrer sur l’écriture.
- Interface claire avec thème Foleskine (fond sépia, police Georgia).
- Compatible Windows, macOS et Linux.
- Stockage des carnets dans un dossier dédié par OS :
  - Windows : `%APPDATA%\FoleskineNotes`
  - macOS : `~/Library/Application Support/FoleskineNotes`
  - Linux : `~/.local/share/FoleskineNotes`

---

## Installation

1. **Prérequis :**  
   - Python 3.10+  
   - Bibliothèques Python standard (tkinter, json, os, sys, re, datetime)

2. **Installation à partir des sources :**  
   - Cloner ou télécharger le projet.
   - Exécuter le fichier principal :  
     ```bash
     python main.py
     ```

3. **Création d’un exécutable avec PyInstaller :**  
   - Installer PyInstaller si nécessaire :  
     ```bash
     pip install pyinstaller
     ```
   - Générer un exécutable unique :  
     ```bash
     pyinstaller --onefile --windowed main.py
     ```
   - L’exécutable se trouve dans le dossier `dist/`.  
   - Vous pouvez envoyer **l’exécutable seul**, mais assurez-vous d’inclure le dossier `icons/` avec l’icône si nécessaire, sauf si l’icône est intégrée via PyInstaller.

---

## Utilisation

- Ouvrir l’application.
- Créer un nouveau carnet avec le bouton `Nouveau`.
- Éditer le contenu, ajouter des pages et naviguer avec les flèches ou le bouton `Aller…`.
- Activer le mode pleine écran avec le bouton `🖥️`.
- Importer ou exporter vos carnets au format JSON pour les sauvegarder ou partager.

---

## Structure des données

Chaque carnet est sauvegardé en JSON avec la structure suivante :

```json
{
  "title": "Titre du carnet",
  "created_at": "2025-08-26T12:00:00",
  "updated_at": "2025-08-26T12:34:56",
  "pages": ["Page 1 texte", "Page 2 texte", ...]
}

## Contribuer

Cloner le projet et créer une branche pour vos modifications.

Respecter le style et la structure du code.

Soumettre une pull request.

Licence

Ce projet est open source sous licence MIT.

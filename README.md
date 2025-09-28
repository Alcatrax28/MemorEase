# Présentation de MemorEase
## Fonctionnalités
### Sauvegarde via ADB
Via le bouton **commencer la sauvegarde**, vous allez pouvoir télécharger vos photos (et/ou vidéos) depuis un appareil __Android__ à condition que celui-ci :
> Soit connecté à votre PC;
> Soit en partage de fichiers;
> Ait le mode déboguage activé (*obligatoire pour faire la passerelle ADB*).

Vous pourrez déterminer l'emplacement de stockage de vos médias.

__**POURQUOI UN PROGRAMME POUR LE FAIRE ?**__
Certaines plateformes comme OneDrive, Google Photos, ... permettent une synchronisation en direct. Personnellement ce n'est pas possible pour moi car je dois trier entre des photos professionnelles (que je ne veux pas sauvegarder) et les photos de ma vie privée.
M'est alors venue l'idée de ce script.

Le téléchargement me permet alors de plus facilement trier les fichiers depuis mon ordinateur, et finalement de les synchroniser sur mon cloud et sur une disque dur externe afin d'avoir une sauvegarde de secours en cas de problème.

#### Les avantages de l'application
> Détection des fichiers déjà sauvegardés.
> Plus rapide et ergonomique que via le gestionnaire de fichiers Windows qui est lent et à tendance à planter (via MTP).

### Tri et sauvegarde
Une fois que vous avez terminé de trier vos médias, le bouton **Trier et sauvegarder les fichiers téléchargés** va permettre de reprendre votre vrac de médias téléchargés, les renommer selon le format suivant : `IMGaaaammjjHHMMSS.jpg` pour les photos, `VIDaaaammjjHHMMSS.mp4` pour les vidéos, et les archiver dans le dossier de votre choix, en créant un sous-répertoire par année.
Avant de déplacer un fichier, celui-ci est comparé au reste du dossier pour détecter et éliminer d'éventuels doublons.
Vous retrouverez donc plus facilement vos fichiers car le nom sera systématiquement au même format, et la gestion des albums par année rend les opérations moins lourdes.
>
## Backup de sécurité
Vous pouvez également utiliser **"Réaliser un backup vers un périphérique externe"** pour faire une copie __miroir__ de votre sauvegarde sur un disque ou périphérique différent.
### Copie miroir ?
Les fichiers qui ne sont pas encore présents sont ajoutés.
Les fichiers modifiés sont modifiés.
Les fichiers supprimés le sont aussi du backup.
Les deux emplacements sont donc systématiquement des copies conformes -> plus besoin de faire les opérations deux fois pour avoir un backup fiable.

## Mises à jour intégrées
Via le menu supérieur > Options > Vérifier les mises à jour, vous pourrez mettre la plateforme à jour si des correctifs, améliorations ou nouvelles fonctionnaités devaient être publiées.
Pour garantir la tranquilité, aucune vérification n'est faite au démarrage.

## Activer le déboguage sur mon téléphone ?
Vous pouvez consulter cet article qui explique comment débloquer et activer l'option (gratuitement) : https://www.frandroid.com/comment-faire/tutoriaux/229753_questcequelemodedebogageusb

## Précautions
Le programme a été rédigé bénévolement, au vu des prix des licences, il n'est pas signé, SmartScreen pourrait afficher un avertissement. Le code source est disponible si vous souhaitez vous assurer de la régularité du code.

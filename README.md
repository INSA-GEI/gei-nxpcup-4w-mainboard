# GEI NXP Cup — Mainboard

Dépôt dédié au développement logiciel et à la génération de l'image Linux embarquée pour la carte principale du robot NXP Cup du département Génie Électrique et Informatique (GEI) de l'INSA Toulouse.

La carte principale est basée sur la **FRDM-IMX8MP de NXP**. Le système embarqué s'appuie sur la plateforme Yocto Robotics Edge de NXP, adaptée aux besoins du projet au moyen d'un layer spécifique au GEI.

## Organisation du dépôt

Le dépôt est organisé autour de deux répertoires principaux et d'un fichier manifeste.

| Élément | Description |
|---|---|
| [`software/`](software/) | Logiciel de commande du véhicule : code Python, code C/C++, bibliothèque de communication I²C et nœuds ROS 2 |
| [`yocto/`](yocto/) | Scripts permettant de récupérer les sources Yocto, de configurer l'environnement de compilation et de construire l'image Linux |
| [`manifest.xml`](manifest.xml) | Manifeste utilisé par l'outil `repo` pour récupérer les dépôts constituant l'environnement Yocto |

## 1. Logiciel de commande du véhicule

Le répertoire [`software/`](software/) regroupe les composants logiciels nécessaires au fonctionnement du robot.

Il contient notamment :

- du code Python et C/C++ ;
- une bibliothèque de communication avec les périphériques utilisant le bus I²C ;
- des nœuds ROS 2 participant à la commande du véhicule.

Ces composants sont destinés à être exécutés sur le système Linux embarqué de la FRDM-IMX8MP.

## 2. Construction de l'image Yocto

### Principe général

L'image Linux est construite à partir de la plateforme [NXP Robotics Edge](https://github.com/nxp-imx/meta-robotics-edge), en utilisant la branche `walnascar`.

Le projet utilise un layer Yocto spécifique au GEI pour adapter la plateforme NXP aux besoins du robot :

- **Plateforme de base :** [NXP Robotics Edge — branche `walnascar`](https://github.com/nxp-imx/meta-robotics-edge/tree/walnascar)
- **Layer spécifique au GEI :** [meta-gei-nxpcup — branche `walnascar`](https://github.com/INSA-GEI/meta-gei-nxpcup/tree/walnascar)
- **Manifeste du projet :** [`manifest.xml`](manifest.xml)

Le fichier `manifest.xml` décrit les dépôts à récupérer. L'outil `repo` permet de synchroniser ces dépôts et de préparer l'environnement de compilation Yocto.

Pour les instructions détaillées concernant la plateforme de base, consulter le [README de NXP Robotics Edge — branche `walnascar`](https://github.com/nxp-imx/meta-robotics-edge/blob/walnascar/README.md).

### Configuration matérielle requise

La compilation d'une image Yocto complète est une opération exigeante en ressources.

Prévoir au minimum :

- **Espace disque :** environ 1 To disponible ;
- **Mémoire vive :** 32 Go de RAM ;
- **Système hôte Linux :** une distribution et les dépendances compatibles avec la version de Yocto utilisée.

L'espace disque doit être disponible sur un système de fichiers adapté à la compilation. La construction génère de nombreux fichiers intermédiaires et des caches ; l'espace réellement consommé dépend notamment des sources, des options de compilation et de la conservation des artefacts.

### Étapes de compilation

Les scripts d'automatisation se trouvent dans le répertoire [`yocto/`](yocto/).

#### Étape 1 — Installer l'outil `repo`

Le script `setup_repo.sh` installe l'outil `repo`, utilisé pour gérer un ensemble de dépôts Git à partir d'un manifeste.

```bash
cd yocto
./setup_repo.sh
```

Si le script n'est pas exécutable, lancer :

```bash
bash setup_repo.sh
```

#### Étape 2 — Récupérer les sources et initialiser l'environnement

Le script `setup_image.sh` utilise le fichier `manifest.xml` situé à la racine du dépôt pour récupérer les sources nécessaires et initialiser l'environnement de compilation.

Depuis le répertoire `yocto/` :

```bash
./setup_image.sh
```

Cette étape peut télécharger un volume important de données. Elle nécessite une connexion réseau et un espace disque suffisant.

#### Étape 3 — Construire l'image Linux

Le script `build_image.sh` lance la construction de l'image à partir de l'environnement préparé précédemment.

Depuis le répertoire `yocto/` :

```bash
./build_image.sh
```

La durée de compilation dépend de la machine hôte, de l'état des caches et des composants à reconstruire. Une première compilation complète peut être particulièrement longue.

**Attention :** ne pas lancer la compilation sans avoir vérifié l'espace disque disponible et la mémoire vive. Prévoir environ 1 To de disque et au moins 32 Go de RAM.

### Récapitulatif

Depuis la racine du dépôt, les trois scripts peuvent être exécutés dans l'ordre suivant :

```bash
cd yocto

./setup_repo.sh
./setup_image.sh
./build_image.sh
```

Chaque étape doit se terminer correctement avant de lancer la suivante.

## 3. Documentation et ressources

- [Dépôt principal de la carte — `walnascar-dev`](https://github.com/INSA-GEI/gei-nxpcup-4w-mainboard/tree/walnascar-dev)
- [Plateforme NXP Robotics Edge — `walnascar`](https://github.com/nxp-imx/meta-robotics-edge/tree/walnascar)
- [Documentation de construction NXP Robotics Edge](https://github.com/nxp-imx/meta-robotics-edge/blob/walnascar/README.md)
- [Layer Yocto spécifique au GEI — `meta-gei-nxpcup`](https://github.com/INSA-GEI/meta-gei-nxpcup/tree/walnascar)


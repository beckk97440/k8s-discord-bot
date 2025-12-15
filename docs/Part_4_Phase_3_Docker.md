# 🐳 Phase 3 : Conteneurisation du Bot Discord avec Docker

[← Phase 2 - Infrastructure](Part_3_Phase_2_Infrastructure_AWS.md) | [Phase 4 - Kubernetes →](Part_5_Phase_4_Kubernetes.md)

---

## 📚 Table des matières

1. [Comprendre Docker](#comprendre-docker)
2. [Prérequis](#pr%C3%A9requis)
3. [Structure du projet bot Discord](#structure-du-projet)
4. [Créer le Dockerfile](#cr%C3%A9er-le-dockerfile)
5. [Build de l'image](#build-de-limage)
6. [Tester localement](#tester-localement)
7. [Push vers Docker Hub](#push-vers-docker-hub)
8. [Best practices Docker](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## 📖 Comprendre Docker

### Qu'est-ce qu'un container ?

**Analogie** : Container = Tupperware pour applications

Imagine que tu veux envoyer un gâteau par la poste :

- **Sans container** : Tu mets le gâteau nu dans le colis → Il arrive écrasé
- **Avec container** : Tu mets le gâteau dans un Tupperware → Il arrive intact

**Application classique** :

```
Serveur A (Ubuntu 20.04, Python 3.8)
  → Ton bot marche ✅

Serveur B (Ubuntu 22.04, Python 3.11)
  → Ton bot crash ❌ (dépendances incompatibles)
```

**Application containerisée** :

```
Serveur A → Container (Ubuntu 22.04 + Python 3.11 + dépendances)
  → Ton bot marche ✅

Serveur B → Container (Ubuntu 22.04 + Python 3.11 + dépendances)
  → Ton bot marche ✅
```

### Container vs Machine Virtuelle

|Aspect|Machine Virtuelle|Container|
|---|---|---|
|**Taille**|Plusieurs GB|Quelques MB|
|**Démarrage**|Minutes|Secondes|
|**Isolation**|OS complet|Processus isolé|
|**Performance**|Overhead hypervisor|Quasi-natif|

**Schéma** :

```
MACHINE VIRTUELLE                    CONTAINER
┌─────────────────────┐             ┌─────────────────────┐
│   App A   App B     │             │   App A   App B     │
│   ┌───┐   ┌───┐     │             │   ┌───┐   ┌───┐     │
│   └───┘   └───┘     │             │   └───┘   └───┘     │
├─────────────────────┤             ├─────────────────────┤
│  Guest OS  Guest OS │             │   Docker Engine     │
├─────────────────────┤             ├─────────────────────┤
│     Hypervisor      │             │     Host OS         │
├─────────────────────┤             ├─────────────────────┤
│      Host OS        │             │    Infrastructure   │
├─────────────────────┤             └─────────────────────┘
│   Infrastructure    │
└─────────────────────┘

  Lourd, lent               Léger, rapide
```

### Docker : Les concepts clés

#### 1. **Image Docker**

**Image** = Modèle/Template immuable

**Analogie** : Une recette de cuisine

- Tu peux faire 10 gâteaux à partir de la même recette
- La recette ne change pas, les gâteaux sont des "instances"

**Caractéristiques** :

- Read-only (en lecture seule)
- Composée de layers (couches)
- Stockée dans un registry (Docker Hub, GitHub Container Registry, etc.)

#### 2. **Container**

**Container** = Instance d'une image en cours d'exécution

**Analogie** : Le gâteau fait à partir de la recette

- Basé sur une image
- En cours d'exécution (processus actif)
- Peut être démarré, arrêté, supprimé

#### 3. **Dockerfile**

**Dockerfile** = Instructions pour construire une image

**Analogie** : La recette détaillée étape par étape

```dockerfile
FROM ubuntu:22.04           # Commencer avec Ubuntu
RUN apt-get install python  # Installer Python
COPY app.py /app/           # Copier ton code
CMD python /app/app.py      # Lancer l'app
```

#### 4. **Layers (Couches)**

Docker construit les images en **couches empilées**.

```
┌─────────────────────────┐  ← Layer 4: CMD (ta commande)
├─────────────────────────┤  ← Layer 3: COPY (ton code)
├─────────────────────────┤  ← Layer 2: RUN (dépendances)
├─────────────────────────┤  ← Layer 1: FROM (OS de base)
└─────────────────────────┘
```

**Avantage** : Les layers sont cachées !

Si tu changes ton code (Layer 3), Docker réutilise les layers 1-2 → Build ultra rapide !

---

## 🔧 Prérequis

### Vérifier que Docker est installé

```bash
# Vérifier la version
docker --version
# Output: Docker version 24.0.7, build afdd53b

# Tester avec hello-world
docker run hello-world
```

**🎓 Que fait cette commande ?**

```bash
docker run hello-world
```

1. Docker cherche l'image `hello-world` localement
2. Pas trouvée → Télécharge depuis Docker Hub
3. Crée un container basé sur l'image
4. Exécute le container (affiche un message)
5. Le container se termine

### Créer un compte Docker Hub

**Docker Hub** = GitHub pour images Docker

1. Aller sur https://hub.docker.com
2. Créer un compte (gratuit)
3. Noter ton username (ex: `tonusername`)

### Se connecter à Docker Hub

```bash
docker login

# Il demande :
# Username: tonusername
# Password: ********

# Output:
# Login Succeeded
```

---

## 📂 Structure du projet

### Ton setup actuel

Tu as déjà un bot Discord fonctionnel ! Vérifions la structure :

```
lol-esports-bot/
├── bot.py                 # ✅ Code principal du bot (scraping LoL Esports)
├── Dockerfile             # ✅ Dockerfile basique
├── docker-compose.yml     # ✅ Docker Compose (à migrer vers K8s)
├── requirements.txt       # ✅ Dépendances Python
├── .env                   # ✅ Variables d'environnement
└── .gitignore            # ✅ Git config
```

**État actuel** :

- ✅ Bot fonctionne avec `docker-compose up -d`
- ✅ Container simple sans orchestration
- ⏭️ On va migrer vers Kubernetes

### Ton bot actuel

**Tu as déjà un bot fonctionnel** qui :

- ✅ Scrape l'API LoL Esports (matches, schedules)
- ✅ Scrape les news Sheep Esports
- ✅ Commandes Discord : `!matches`, `!team`, `!today`, `!league`
- ✅ Notifications automatiques (matchs dans 1h, nouvelles actus)

**Code** : `bot.py` (~250 lignes)

**Dépendances** (`requirements.txt`) :

```
discord.py>=2.0.0
aiohttp>=3.8.0
feedparser>=6.0.0
beautifulsoup4
lxml
```

**Variables d'environnement** (`.env`) :

```bash
DISCORD_TOKEN=ton_token_discord
ESPORTS_CHANNEL_ID=123456789  # ⚠️ Incohérence à corriger
NEWS_CHANNEL_ID=987654321
```

**⚠️ BUG À CORRIGER** :

Dans ton `.env`, tu as `ESPORTS_CHANNEL_ID` mais dans `bot.py` :

```python
MATCH_CHANNEL_ID = int(os.getenv('MATCH_CHANNEL_ID', '0'))  # ← Différent !
```

**Fix** : Dans `.env`, renomme en `MATCH_CHANNEL_ID` :

```bash
DISCORD_TOKEN=ton_token_discord
MATCH_CHANNEL_ID=123456789    # ← Corrigé
NEWS_CHANNEL_ID=987654321
```

---

## 🐳 Améliorer le Dockerfile pour Kubernetes

### Ton Dockerfile actuel

```dockerfile
FROM python:3.11-slim
WORKDIR /app
# Installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Copier le code
COPY bot.py .
# Lancer le bot
CMD ["python", "-u", "bot.py"]
```

**✅ Ce qui est bien** :

- Image slim (légère)
- `--no-cache-dir` (économie d'espace)
- `-u` pour unbuffered output (logs immédiats)

**❌ Ce qui manque pour Kubernetes production** :

1. Utilisateur non-root (sécurité)
2. Dossier `/app/data` pour le PVC
3. Read-only filesystem compatible
4. Metadata (labels)
5. Healthcheck

### Le Dockerfile amélioré

**Créer** : `Dockerfile` (remplace l'ancien)

```dockerfile
# ══════════════════════════════════════════════════════════════
# ÉTAPE 1 : IMAGE DE BASE
# ══════════════════════════════════════════════════════════════

FROM python:3.11-slim

# ══════════════════════════════════════════════════════════════
# ÉTAPE 2 : MÉTADONNÉES (OPTIONNEL MAIS RECOMMANDÉ)
# ══════════════════════════════════════════════════════════════

LABEL maintainer="ton-email@example.com"
LABEL description="LoL Esports Discord Bot"
LABEL version="1.0.0"

# ══════════════════════════════════════════════════════════════
# ÉTAPE 3 : DÉFINIR LE RÉPERTOIRE DE TRAVAIL
# ══════════════════════════════════════════════════════════════

WORKDIR /app

# ══════════════════════════════════════════════════════════════
# ÉTAPE 4 : COPIER ET INSTALLER LES DÉPENDANCES PYTHON
# ══════════════════════════════════════════════════════════════

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ══════════════════════════════════════════════════════════════
# ÉTAPE 5 : CRÉER UN UTILISATEUR NON-ROOT (SÉCURITÉ)
# ══════════════════════════════════════════════════════════════

RUN useradd -m -u 1000 botuser && \
    mkdir -p /app/data && \
    chown -R botuser:botuser /app

# ══════════════════════════════════════════════════════════════
# ÉTAPE 6 : COPIER LE CODE DE L'APPLICATION
# ══════════════════════════════════════════════════════════════

COPY --chown=botuser:botuser bot.py .

# ══════════════════════════════════════════════════════════════
# ÉTAPE 7 : BASCULER VERS L'UTILISATEUR NON-ROOT
# ══════════════════════════════════════════════════════════════

USER botuser

# ══════════════════════════════════════════════════════════════
# ÉTAPE 8 : HEALTHCHECK (OPTIONNEL)
# ══════════════════════════════════════════════════════════════

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# ══════════════════════════════════════════════════════════════
# ÉTAPE 9 : DÉFINIR LA COMMANDE PAR DÉFAUT
# ══════════════════════════════════════════════════════════════

CMD ["python", "-u", "bot.py"]
```

### 🎓 Différences expliquées

#### Ajout 1 : LABEL (metadata)

```dockerfile
LABEL maintainer="ton-email@example.com"
LABEL description="LoL Esports Discord Bot"
LABEL version="1.0.0"
```

**Pourquoi ?**

- Documentation de l'image
- Visible avec `docker inspect`
- Best practice professionnelle

**🔍 Ce qui vient de quoi** : TON CHOIX (optionnel)

#### Ajout 2 : Utilisateur non-root

```dockerfile
RUN useradd -m -u 1000 botuser && \
    mkdir -p /app/data && \
    chown -R botuser:botuser /app
```

**Pourquoi CRITIQUE ?**

Par défaut, containers tournent en **root** (UID 0).

**Danger si ton bot est hacké** :

- ❌ En root → Attaquant a tous les droits
- ✅ En botuser (UID 1000) → Droits limités

**Création du dossier `/app/data`** :

- Pour le PersistentVolume Kubernetes
- Le bot pourra écrire des fichiers persistants ici

**🔍 Ce qui vient de quoi** :

- `useradd` : Standard Linux
- UID `1000` : Convention (premier user normal)
- `/app/data` : TON CHOIX (pour PVC)

#### Ajout 3 : COPY avec chown

```dockerfile
COPY --chown=botuser:botuser bot.py .
```

**Différence vs ton ancien** :

```dockerfile
# Ancien (fichier appartient à root)
COPY bot.py .

# Nouveau (fichier appartient à botuser)
COPY --chown=botuser:botuser bot.py .
```

**Pourquoi ?**

- Les fichiers doivent appartenir à botuser
- Sinon → Permission denied quand le bot essaie de lire

#### Ajout 4 : USER botuser

```dockerfile
USER botuser
```

**Change l'utilisateur** pour toutes les commandes suivantes.

**Impact** :

- CMD s'exécute en tant que botuser (pas root)
- Le bot tourne avec UID 1000

#### Ajout 5 : HEALTHCHECK

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"
```

**Vérifie que le container est sain** :

- Toutes les 30 secondes
- Timeout de 10s
- 3 échecs consécutifs → container "unhealthy"

**Check actuel** : Simple (vérifie que Python fonctionne)

**Amélioration future** : Vérifier la connexion Discord réelle

---

## 🏗️ Build de l'image

### Commande de build

```bash
# Se placer dans le dossier du projet
cd discord-bot/

# Builder l'image
docker build -t tonusername/lol-esports-bot:v1.0.0 .
```

**🎓 Explication de la commande** :

```bash
docker build
# Commande pour construire une image

-t tonusername/lol-esports-bot:v1.0.0
# -t = Tag (nom + version de l'image)
# Format : [username]/[nom-image]:[version]
#   tonusername = Ton username Docker Hub
#   lol-esports-bot = Nom de ton image
#   v1.0.0 = Version (semantic versioning)

.
# Le point = "Contexte de build"
# Docker va envoyer tous les fichiers du dossier actuel au daemon Docker
# (sauf ceux dans .dockerignore)
```

### Ce qui se passe pendant le build

```
[+] Building 45.2s (12/12) FINISHED
 => [internal] load build definition from Dockerfile
 => => transferring dockerfile: 1.23kB
 
 => [internal] load .dockerignore
 => => transferring context: 120B
 
 => [internal] load metadata for docker.io/library/python:3.11-slim
 => => resolve docker.io/library/python:3.11-slim
 
 => [1/7] FROM docker.io/library/python:3.11-slim
 => => resolve docker.io/library/python:3.11-slim
 => => sha256:abc123... 1.86kB / 1.86kB
 
 => [internal] load build context
 => => transferring context: 15.2kB
 
 => [2/7] WORKDIR /app
 => CACHED [3/7] RUN apt-get update && apt-get install...
 => CACHED [4/7] COPY requirements.txt .
 => CACHED [5/7] RUN pip install --no-cache-dir -r requirements.txt
 => [6/7] RUN useradd -m -u 1000 botuser...
 => [7/7] COPY --chown=botuser:botuser . .
 
 => exporting to image
 => => exporting layers
 => => writing image sha256:def456...
 => => naming to docker.io/tonusername/lol-esports-bot:v1.0.0
```

**🎓 Comprendre le output** :

```
=> [1/7] FROM python:3.11-slim
# Layer 1 : Image de base

=> [2/7] WORKDIR /app
# Layer 2 : Créer le répertoire de travail

=> CACHED [3/7] RUN apt-get update...
# Layer 3 : Installer gcc (CACHED = réutilisé du cache !)

=> CACHED [4/7] COPY requirements.txt .
# Layer 4 : Copier requirements.txt (CACHED)

=> CACHED [5/7] RUN pip install...
# Layer 5 : Installer les dépendances Python (CACHED)

=> [6/7] RUN useradd -m -u 1000 botuser...
# Layer 6 : Créer l'utilisateur non-root

=> [7/7] COPY --chown=botuser:botuser . .
# Layer 7 : Copier le code (PAS de cache car le code a changé)
```

**📖 Le cache en action** :

Si tu rebuildas après avoir changé `bot.py` :

```
=> CACHED [3/7] RUN apt-get update...
=> CACHED [4/7] COPY requirements.txt .
=> CACHED [5/7] RUN pip install...
=> [7/7] COPY --chown=botuser:botuser . .
```

Seul le dernier layer est rebuild → **Build ultra rapide (5s au lieu de 45s) !**

### Vérifier l'image créée

```bash
# Lister les images
docker images

# Output :
# REPOSITORY                      TAG       IMAGE ID       CREATED         SIZE
# tonusername/lol-esports-bot    v1.0.0    abc123def456   2 minutes ago   245MB
```

### Inspecter l'image

```bash
# Voir les layers
docker history tonusername/lol-esports-bot:v1.0.0

# Voir les métadonnées
docker inspect tonusername/lol-esports-bot:v1.0.0
```

---

## 🧪 Tester localement

### Migration de Docker Compose vers Docker simple

**Actuellement tu utilises** :

```bash
docker-compose up -d
```

**Pour Kubernetes, on va tester avec** :

```bash
docker run ...
```

**Pourquoi ?**

- Kubernetes remplacera Docker Compose
- Les variables d'environnement seront gérées par Kubernetes
- On teste que l'image fonctionne de manière isolée

### Corriger le bug des variables d'environnement

**Dans `.env`, change** :

```bash
# Avant
ESPORTS_CHANNEL_ID=123456789

# Après
MATCH_CHANNEL_ID=123456789  # ← Match le code dans bot.py
```

### Build la nouvelle image

```bash
# Se placer dans le dossier du projet
cd lol-esports-bot/

# Builder l'image avec le nouveau Dockerfile
docker build -t tonusername/lol-esports-bot:v1.0.0 .
```

**Output attendu** :

```
[+] Building 45.2s (12/12) FINISHED
 => [1/7] FROM docker.io/library/python:3.11-slim
 => [2/7] WORKDIR /app
 => [3/7] COPY requirements.txt .
 => [4/7] RUN pip install --no-cache-dir -r requirements.txt
 => [5/7] RUN useradd -m -u 1000 botuser...
 => [6/7] COPY --chown=botuser:botuser bot.py .
 => exporting to image
 => => naming to docker.io/tonusername/lol-esports-bot:v1.0.0
```

### Tester avec docker run

```bash
# Lancer le bot
docker run -d \
  --name lol-bot-test \
  -e DISCORD_TOKEN="$(grep DISCORD_TOKEN .env | cut -d '=' -f2)" \
  -e MATCH_CHANNEL_ID="$(grep MATCH_CHANNEL_ID .env | cut -d '=' -f2)" \
  -e NEWS_CHANNEL_ID="$(grep NEWS_CHANNEL_ID .env | cut -d '=' -f2)" \
  tonusername/lol-esports-bot:v1.0.0
```

**🎓 Explication** :

```bash
docker run
# Créer et démarrer un container

-d
# Detached mode = En arrière-plan

--name lol-bot-test
# Nom du container

-e DISCORD_TOKEN="..."
# Variables d'environnement passées depuis .env
# $(grep ... | cut ...) = Lit la valeur depuis .env

tonusername/lol-esports-bot:v1.0.0
# Quelle image utiliser
```

### Voir les logs

```bash
# Logs en temps réel
docker logs -f lol-bot-test

# Output attendu :
# ✅ Bot connecté en tant que <BotUser>
# 📺 Match Channel: 123456789
# 📰 News Channel: 987654321
```

### Vérifier le processus dans le container

```bash
# Entrer dans le container
docker exec -it lol-bot-test /bin/bash

# Tu es maintenant DANS le container !

# Vérifier l'utilisateur
whoami
# Output: botuser ✅

id
# Output: uid=1000(botuser) gid=1000(botuser) ✅

# Voir les processus
ps aux
# Output:
# USER       PID  COMMAND
# botuser      1  python -u bot.py  ← PID 1 ✅

# Vérifier le dossier data
ls -la /app/data
# drwxr-xr-x botuser botuser /app/data ✅

# Quitter le container
exit
```

### Tester sur Discord

Dans ton serveur Discord :

```
!matches
→ 🔍 Récupération des matchs...
→ 📊 Derniers résultats: [...]
→ 📅 Prochains matchs: [...]

!today
→ 🔍 Matchs d'aujourd'hui...
→ 📅 Matchs d'aujourd'hui (X): [...]

!league lec
→ 🔍 Matchs de la LEC...
→ LEC Matchs (X): [...]

!team g2
→ 🔍 Recherche des matchs de G2...
→ Matchs de g2: [...]
```

**✅ Tout fonctionne !**

### Arrêter et nettoyer

```bash
# Arrêter le container de test
docker stop lol-bot-test

# Supprimer le container
docker rm lol-bot-test

# L'image reste disponible pour Docker Hub
docker images | grep lol-esports-bot
```

---

## 📤 Push vers Docker Hub

### Pourquoi ?

Pour que Kubernetes puisse télécharger ton image depuis n'importe quel node du cluster.

### Se connecter

```bash
docker login

# Username: tonusername
# Password: ********
# Login Succeeded
```

### Push l'image

```bash
docker push tonusername/lol-esports-bot:v1.0.0
```

**Output** :

```
The push refers to repository [docker.io/tonusername/lol-esports-bot]
abc123: Pushed
def456: Pushed
ghi789: Pushed
v1.0.0: digest: sha256:xyz... size: 1234
```

**Durée** : 1-3 minutes (dépend de ta connexion Internet)

### Vérifier sur Docker Hub

1. Aller sur https://hub.docker.com
2. Cliquer sur **"Repositories"**
3. Tu devrais voir `tonusername/lol-esports-bot`

### Tester le pull

```bash
# Sur une autre machine (ou après avoir supprimé l'image locale)
docker pull tonusername/lol-esports-bot:v1.0.0

# Ça devrait télécharger l'image depuis Docker Hub
```

### Créer un tag `latest`

**Best practice** : Avoir toujours un tag `latest` qui pointe vers la dernière version.

```bash
# Créer un nouveau tag
docker tag tonusername/lol-esports-bot:v1.0.0 tonusername/lol-esports-bot:latest

# Push le tag latest
docker push tonusername/lol-esports-bot:latest
```

**Maintenant tu as 2 tags** :

- `tonusername/lol-esports-bot:v1.0.0` (version spécifique)
- `tonusername/lol-esports-bot:latest` (dernière version)

---

## ✅ Best Practices Docker

### 1. Toujours utiliser des tags de version

```dockerfile
# ❌ MAUVAIS
FROM python

# ✅ BON
FROM python:3.11-slim
```

**Pourquoi ?**

- Sans version, tu prends `latest` qui peut changer
- Ton build pourrait casser dans 6 mois avec une nouvelle version Python

### 2. Minimiser le nombre de layers

```dockerfile
# ❌ MAUVAIS (3 layers)
RUN apt-get update
RUN apt-get install -y gcc
RUN rm -rf /var/lib/apt/lists/*

# ✅ BON (1 layer)
RUN apt-get update && \
    apt-get install -y gcc && \
    rm -rf /var/lib/apt/lists/*
```

### 3. Utiliser .dockerignore

```
.env
.git
__pycache__/
*.pyc
venv/
.venv/
```

### 4. Copier requirements.txt avant le code

```dockerfile
# ✅ BON (cache optimal)
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# ❌ MAUVAIS (pas de cache)
COPY . .
RUN pip install -r requirements.txt
```

### 5. Toujours créer un user non-root

```dockerfile
RUN useradd -m -u 1000 botuser
USER botuser
```

### 6. Nettoyer dans le même RUN

```dockerfile
RUN apt-get update && \
    apt-get install -y gcc && \
    rm -rf /var/lib/apt/lists/*  # ← Nettoyer dans le même layer
```

### 7. Utiliser multi-stage builds (pour apps complexes)

Si tu avais besoin de compiler des trucs :

```dockerfile
# Stage 1: Build
FROM python:3.11 AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
CMD ["python", "bot.py"]
```

### 8. Scanner l'image pour les vulnérabilités

```bash
# Avec Docker Scout (intégré dans Docker Desktop)
docker scout cves tonusername/lol-esports-bot:v1.0.0

# Avec Trivy (outil open-source)
trivy image tonusername/lol-esports-bot:v1.0.0
```

---

## 🚨 Troubleshooting

### Le build échoue : "gcc: command not found"

**Cause** : Un package Python nécessite un compilateur C.

**Solution** : Installer gcc dans le Dockerfile (déjà fait dans notre exemple).

### Le bot ne démarre pas : "DISCORD_TOKEN not set"

**Cause** : Variable d'environnement manquante.

**Solution** :

```bash
docker run -e DISCORD_TOKEN="ton_token" tonusername/lol-esports-bot:v1.0.0
```

### L'image est très grosse (1 GB+)

**Causes possibles** :

- Image de base trop grosse (utilise `slim` ou `alpine`)
- Cache pip non nettoyé (utilise `--no-cache-dir`)
- Logs ou fichiers inutiles copiés (utilise `.dockerignore`)

**Vérifier la taille des layers** :

```bash
docker history tonusername/lol-esports-bot:v1.0.0
```

### Permission denied lors du COPY

**Cause** : Le user `botuser` n'a pas les droits.

**Solution** : Utilise `COPY --chown=botuser:botuser`.

### Le container redémarre en boucle

```bash
# Voir les logs
docker logs lol-bot

# Voir pourquoi il a crashé
docker inspect lol-bot | grep -A 5 "State"
```

---

## 📝 Récapitulatif

### Ce qu'on a fait

✅ Compris Docker (images, containers, layers)  
✅ Créé un Dockerfile optimisé pour notre bot Discord  
✅ Utilisé les best practices (multi-layer, cache, non-root)  
✅ Buildé l'image localement  
✅ Testé le container  
✅ Pushé l'image vers Docker Hub

### Ce qu'on va utiliser dans Kubernetes

Dans la Phase 4 (Déploiements Kubernetes), on va utiliser cette image :

```yaml
spec:
  containers:
  - name: discord-bot
    image: tonusername/lol-esports-bot:v1.0.0
    # ↑ Kubernetes va pull cette image depuis Docker Hub
```

### Commandes essentielles à retenir

```bash
# Build
docker build -t tonusername/lol-esports-bot:v1.0.0 .

# Run localement
docker run -d --name lol-bot -e DISCORD_TOKEN="xxx" tonusername/lol-esports-bot:v1.0.0

# Logs
docker logs -f lol-bot

# Push
docker push tonusername/lol-esports-bot:v1.0.0

# Cleanup
docker stop lol-bot && docker rm lol-bot
```

---

## 🎉 Félicitations !

Ton bot Discord est maintenant **containerisé** et prêt à être déployé sur Kubernetes !

**Prochaine étape** : Phase 4 - Déploiements Kubernetes avec Sealed Secrets, PVC, et Security Context.

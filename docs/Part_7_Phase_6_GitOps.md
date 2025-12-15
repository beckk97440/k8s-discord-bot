# 🔄 Phase 6 : GitOps avec ArgoCD

[← Phase 5 - Monitoring](Part_6_Phase_5_Monitoring.md) | [Phase 7 - Lambda →](Part_8_Phase_7_Lambda.md)

---

## 📚 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Comprendre GitOps](#comprendre-gitops)
3. [Comprendre ArgoCD](#comprendre-argocd)
4. [Installation d'ArgoCD](#installation-dargocd)
5. [Accéder à l'interface ArgoCD](#acc%C3%A9der-%C3%A0-linterface)
6. [Préparer le repo Git](#pr%C3%A9parer-le-repo-git)
7. [Créer une Application ArgoCD](#cr%C3%A9er-une-application)
8. [Synchronisation automatique](#synchronisation-automatique)
9. [Tester le workflow GitOps](#tester-le-workflow)
10. [Configuration pour Failover Automatique](#configuration-pour-failover-automatique)
11. [Troubleshooting](#troubleshooting)

---

## 🎯 Vue d'ensemble

### Qu'est-ce qu'on va mettre en place ?

**Workflow GitOps complet** :

```
1. Tu modifies un YAML (ex: nouvelle version du bot)
   ↓
2. Tu commit dans Git
   ↓
3. Tu push sur GitHub
   ↓
4. ArgoCD détecte le changement (< 3 min)
   ↓
5. ArgoCD synchronise automatiquement le cluster
   ↓
6. Nouveau pod déployé automatiquement !
```

**Résultat** : Git = Source de vérité unique pour ton cluster

### Pourquoi GitOps ?

**Sans GitOps (CI/CD classique)** :

```bash
# Tu fais ça manuellement à chaque fois :
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f sealed-secret.yaml
```

❌ Erreurs humaines  
❌ Pas d'historique  
❌ Difficile à reproduire  
❌ Pas de rollback facile

**Avec GitOps (ArgoCD)** :

```bash
# Tu fais juste :
git commit -m "Update bot to v1.1.0"
git push

# ArgoCD fait le reste automatiquement
```

✅ Git = historique complet  
✅ Rollback = `git revert`  
✅ Reproductible (tout est dans Git)  
✅ Automatisé  
✅ Self-healing (si quelqu'un modifie manuellement, ArgoCD remet l'état Git)

---

## 📖 Comprendre GitOps

### Définition

**GitOps** = Pratique où Git est la source de vérité pour l'infrastructure

**Principes** :

1. **Déclaratif** : Tu déclares l'état désiré (YAML)
2. **Versionné** : Tout dans Git (avec historique)
3. **Automatique** : Synchronisation automatique Git → Cluster
4. **Self-healing** : Si drift détecté, réconciliation automatique

### Git comme source de vérité

**Analogie** : Git = Blueprint (plan) de ta maison

```
Git Repository
  ↓ (source of truth)
Cluster Kubernetes
```

Si quelqu'un modifie la maison (cluster) manuellement : → GitOps détecte la différence (drift) → GitOps remet comme dans le blueprint (Git)

### Workflow GitOps

```
┌─────────────────────────────────────────────────────────┐
│                    WORKFLOW GITOPS                       │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐                                        │
│  │  DEVELOPER   │                                        │
│  │              │                                        │
│  │ 1. Edit YAML │                                        │
│  │ 2. Commit    │                                        │
│  │ 3. Push      │                                        │
│  └──────┬───────┘                                        │
│         │                                                │
│         ▼                                                │
│  ┌──────────────────────────────┐                       │
│  │      GIT REPOSITORY           │                       │
│  │  ───────────────────────────  │                       │
│  │  k8s/                         │                       │
│  │  ├── base/                    │                       │
│  │  │   ├── namespace.yaml       │                       │
│  │  │   └── quotas.yaml          │                       │
│  │  └── apps/                    │                       │
│  │      └── discord-bot/         │                       │
│  │          ├── deployment.yaml  │                       │
│  │          ├── pvc.yaml         │                       │
│  │          └── sealed-secret.yaml│                      │
│  └────────────┬─────────────────┘                       │
│               │                                          │
│               │ Poll / Webhook                           │
│               ▼                                          │
│  ┌─────────────────────────────┐                        │
│  │         ARGOCD              │                        │
│  │  ─────────────────────────  │                        │
│  │  1. Détecte changement      │                        │
│  │  2. Compare Git vs Cluster  │                        │
│  │  3. Sync si différence      │                        │
│  └────────────┬────────────────┘                        │
│               │                                          │
│               │ kubectl apply                            │
│               ▼                                          │
│  ┌─────────────────────────────┐                        │
│  │    CLUSTER KUBERNETES       │                        │
│  │  ─────────────────────────  │                        │
│  │  Pods, Deployments,         │                        │
│  │  Services, etc.             │                        │
│  └─────────────────────────────┘                        │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### GitOps vs CI/CD classique

|Aspect|CI/CD classique|GitOps|
|---|---|---|
|**Déclencheur**|Push déclenche le déploiement|Agent pull depuis Git|
|**Credentials**|Pipeline a accès au cluster|Seul l'agent a accès|
|**État**|Pipeline sait ce qu'il a déployé|Git sait l'état complet|
|**Rollback**|Re-run pipeline|`git revert`|
|**Drift detection**|Aucune|Automatique|

**Exemple CI/CD classique** :

```yaml
# .gitlab-ci.yml
deploy:
  script:
    - kubectl apply -f deployment.yaml
  environment:
    name: production
```

**Problème** : Le pipeline a besoin de credentials pour le cluster (sécurité).

**Exemple GitOps** :

```yaml
# Pas de pipeline !
# ArgoCD tourne DANS le cluster
# Aucun credential externe nécessaire
```

---

## 🐙 Comprendre ArgoCD

### Qu'est-ce qu'ArgoCD ?

**ArgoCD** = Outil GitOps pour Kubernetes

**Créé par** : Intuit (2018), maintenant projet CNCF

**Caractéristiques** :

- 🎯 Application-centric (gère des "Applications")
- 🔄 Continuous Deployment automatique
- 🌐 Interface web intuitive
- 🔍 Drift detection et reconciliation
- 📊 Health status des ressources
- 🔙 Rollback facile

### Concepts ArgoCD

#### 1. Application

**Application** = Ensemble de ressources Kubernetes déployées ensemble

**Exemple** : Notre bot Discord = 1 Application ArgoCD contenant :

- Deployment
- PVC
- SealedSecret

**Définition d'une Application** :

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: discord-bot
spec:
  source:
    repoURL: https://github.com/ton-username/repo.git
    path: k8s/apps/discord-bot
    targetRevision: HEAD
  destination:
    server: https://kubernetes.default.svc
    namespace: lol-esports
```

#### 2. Sync Status

**Sync Status** = État de synchronisation Git ↔ Cluster

|Status|Signification|
|---|---|
|**Synced**|Git = Cluster ✅|
|**OutOfSync**|Git ≠ Cluster ⚠️|
|**Unknown**|ArgoCD ne peut pas déterminer|

#### 3. Health Status

**Health Status** = État de santé des ressources

|Status|Signification|
|---|---|
|**Healthy**|Ressources opérationnelles ✅|
|**Progressing**|En cours de déploiement 🔄|
|**Degraded**|Problème détecté ❌|
|**Missing**|Ressource manquante ⚠️|

#### 4. Sync Policy

**Sync Policy** = Comment synchroniser ?

**Manual** :

- Tu cliques sur "Sync" manuellement dans l'UI

**Automatic** :

- ArgoCD synchronise automatiquement
- Options :
    - **Prune** : Supprimer les ressources qui ne sont plus dans Git
    - **SelfHeal** : Corriger automatiquement les drifts

```yaml
syncPolicy:
  automated:
    prune: true      # Supprimer ce qui n'est plus dans Git
    selfHeal: true   # Corriger les modifications manuelles
```

#### 5. Project

**Project** = Groupement logique d'Applications

**Par défaut** : Projet "default"

**Use case** : Séparer dev/staging/prod

```
Project: discord-bot
├── App: discord-bot-dev
├── App: discord-bot-staging
└── App: discord-bot-prod
```

### Architecture ArgoCD

```
┌─────────────────────────────────────────────────┐
│              CLUSTER KUBERNETES                  │
├─────────────────────────────────────────────────┤
│                                                   │
│  Namespace: argocd                               │
│  ┌─────────────────────────────────────────┐    │
│  │  ArgoCD Components                      │    │
│  │  ─────────────────────────────────────  │    │
│  │                                          │    │
│  │  ┌────────────────────────────────┐     │    │
│  │  │  argocd-server                 │     │    │
│  │  │  • API Server                  │     │    │
│  │  │  • Web UI                      │     │    │
│  │  │  • gRPC/REST API               │     │    │
│  │  └────────────────────────────────┘     │    │
│  │                                          │    │
│  │  ┌────────────────────────────────┐     │    │
│  │  │  argocd-repo-server            │     │    │
│  │  │  • Clone Git repos             │     │    │
│  │  │  • Générer manifests           │     │    │
│  │  └────────────────────────────────┘     │    │
│  │                                          │    │
│  │  ┌────────────────────────────────┐     │    │
│  │  │  argocd-application-controller │     │    │
│  │  │  • Reconciliation loop         │     │    │
│  │  │  • Compare Git vs Cluster      │     │    │
│  │  │  • Sync resources              │     │    │
│  │  └────────────────────────────────┘     │    │
│  │                                          │    │
│  │  ┌────────────────────────────────┐     │    │
│  │  │  argocd-redis                  │     │    │
│  │  │  • Cache                       │     │    │
│  │  └────────────────────────────────┘     │    │
│  └─────────────────────────────────────────┘    │
│                                                   │
└───────────────────────────────────────────────────┘
```

**Rôles des composants** :

|Composant|Rôle|
|---|---|
|**argocd-server**|Interface web + API|
|**argocd-repo-server**|Gère les repos Git|
|**argocd-application-controller**|Cœur de la synchronisation|
|**argocd-redis**|Cache pour performances|

---

## 🚀 Installation d'ArgoCD

### Via Helm (recommandé)

#### Ajouter le repo Helm

```bash
# Ajouter le repo ArgoCD
helm repo add argo https://argoproj.github.io/argo-helm

# Mettre à jour
helm repo update
```

#### Créer le namespace

```bash
kubectl create namespace argocd
```

#### Créer le fichier de configuration

**Créer** : `argocd-values.yaml`

```yaml
# ══════════════════════════════════════════════════════════════
# ARGOCD CONFIGURATION
# ══════════════════════════════════════════════════════════════

# Désactiver Dex (OAuth) pour simplifier
dex:
  enabled: false

# Server configuration
server:
  # Service type (ClusterIP car on utilise port-forward)
  service:
    type: ClusterIP
  
  # Resources
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 200m
      memory: 256Mi

# Application Controller
controller:
  resources:
    requests:
      cpu: 200m
      memory: 256Mi
    limits:
      cpu: 500m
      memory: 512Mi

# Repo Server
repoServer:
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 200m
      memory: 256Mi

# Redis
redis:
  resources:
    requests:
      cpu: 100m
      memory: 64Mi
    limits:
      cpu: 200m
      memory: 128Mi

# Config
configs:
  # Params
  params:
    # Timeout pour les syncs
    server.repo.server.timeout.seconds: 120
```

**🎓 Explication** :

```yaml
dex:
  enabled: false
# Dex = OAuth provider pour SSO (Google, GitHub, etc.)
# On le désactive pour simplifier (login avec admin/password)
```

```yaml
server:
  service:
    type: ClusterIP
# ClusterIP = Service interne seulement
# On n'expose pas ArgoCD publiquement
# On utilisera kubectl port-forward
```

**🔍 Ce qui vient de quoi** :

|Section|Source|
|---|---|
|Structure YAML (server, controller, etc.)|**Chart ArgoCD**|
|Options disponibles|**Chart ArgoCD**|
|Valeurs resources|**TON CHOIX** (optimisé pour petit cluster)|
|dex.enabled: false|**TON CHOIX** (simplification)|

#### Installer avec Helm

```bash
helm install argocd argo/argo-cd \
  --namespace argocd \
  --values argocd-values.yaml
```

**Output** :

```
NAME: argocd
LAST DEPLOYED: Wed Dec  3 15:30:00 2025
NAMESPACE: argocd
STATUS: deployed
REVISION: 1
```

**Durée** : 1-2 minutes

#### Vérifier l'installation

```bash
# Voir les pods
kubectl get pods -n argocd

# Output attendu :
# NAME                                            READY   STATUS    AGE
# argocd-server-xxx                               1/1     Running   1m
# argocd-repo-server-xxx                          1/1     Running   1m
# argocd-application-controller-xxx               1/1     Running   1m
# argocd-redis-xxx                                1/1     Running   1m
```

**Attendre que tous soient Running** :

```bash
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s
```

---

## 🌐 Accéder à l'interface ArgoCD

### Récupérer le mot de passe admin

**Par défaut**, ArgoCD crée un password dans un Secret :

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
echo  # Pour le newline
```

**Output** (exemple) :

```
aB3dEfG7hJ9kL2mN
```

**📝 Copie ce mot de passe !**

### Port-forward ArgoCD

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

**🎓 Explication** :

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Port local:Port remote
# localhost:8080 → service:443 (HTTPS)
```

**Output** :

```
Forwarding from 127.0.0.1:8080 -> 8080
Forwarding from [::1]:8080 -> 8080
```

**⚠️ Important** : Garde ce terminal ouvert !

### Se connecter

1. Ouvrir le navigateur : **https://localhost:8080**
2. ⚠️ Certificat invalide → Cliquer **"Advanced"** → **"Proceed"**
3. Login :
    - **Username** : `admin`
    - **Password** : (celui récupéré ci-dessus)
4. **Bienvenue dans ArgoCD !**

### Interface ArgoCD

**Écran principal** :

```
┌────────────────────────────────────────────────┐
│  ArgoCD                      admin  ⚙️  🔔    │
├────────────────────────────────────────────────┤
│                                                │
│  🔍 Search applications                        │
│                                                │
│  + NEW APP                                     │
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │  Applications (0)                        │ │
│  │  ────────────────────────────────────    │ │
│  │                                          │ │
│  │  No applications yet                     │ │
│  │                                          │ │
│  └──────────────────────────────────────────┘ │
│                                                │
└────────────────────────────────────────────────┘
```

**Menu gauche** :

- **Applications** : Liste des apps
- **Settings** : Configuration
- **User Info** : Info utilisateur

### Changer le mot de passe (recommandé)

```bash
# Via CLI argocd
# D'abord, installer argocd CLI

# Sur Arch Linux
yay -S argocd

# Sur Mac
brew install argocd

# Login
argocd login localhost:8080

# Username: admin
# Password: [le mot de passe initial]
# ⚠️ Certificat invalide → Accepter (y)

# Changer le password
argocd account update-password
```

**Ou via l'UI** :

1. Cliquer sur **User Info** (menu gauche)
2. **Update Password**
3. Entrer l'ancien et le nouveau password

---

## 📦 Préparer le repo Git

### Créer le repo GitHub

1. Aller sur https://github.com/new
2. Nom du repo : `lol-esports-k8s-manifests`
3. Visibilité : **Public** (pour faciliter, sinon il faut configurer des credentials)
4. ✅ Cocher **"Add a README file"**
5. Cliquer **"Create repository"**

### Cloner le repo

```bash
# Cloner
git clone https://github.com/ton-username/lol-esports-k8s-manifests.git
cd lol-esports-k8s-manifests
```

### Créer la structure

```bash
# Créer les dossiers
mkdir -p k8s/base
mkdir -p k8s/apps/discord-bot
```

**Structure** :

```
lol-esports-k8s-manifests/
├── README.md
└── k8s/
    ├── base/
    │   ├── namespace.yaml
    │   └── resource-quota.yaml
    └── apps/
        └── discord-bot/
            ├── sealed-secret.yaml
            ├── pvc.yaml
            └── deployment.yaml
```

### Copier les manifests

**Copier tous tes fichiers YAML créés dans les phases précédentes** :

```bash
# Depuis ton projet local
cp k8s/base/namespace.yaml lol-esports-k8s-manifests/k8s/base/
cp k8s/base/resource-quota.yaml lol-esports-k8s-manifests/k8s/base/

cp k8s/apps/discord-bot/sealed-secret.yaml lol-esports-k8s-manifests/k8s/apps/discord-bot/
cp k8s/apps/discord-bot/pvc.yaml lol-esports-k8s-manifests/k8s/apps/discord-bot/
cp k8s/apps/discord-bot/deployment.yaml lol-esports-k8s-manifests/k8s/apps/discord-bot/
```

### Créer un README

**Éditer** : `README.md`

````markdown
# LoL Esports Bot - Kubernetes Manifests

GitOps repository for the LoL Esports Discord Bot Kubernetes deployment.

## Structure

- `k8s/base/` : Base resources (namespace, quotas)
- `k8s/apps/discord-bot/` : Discord bot application

## Deployment

Managed by ArgoCD. Any change pushed to `main` branch will be automatically synced to the cluster.

## Manual apply

```bash
kubectl apply -f k8s/base/
kubectl apply -f k8s/apps/discord-bot/
````

````

### Commit et push

```bash
# Ajouter tous les fichiers
git add .

# Commit
git commit -m "Initial commit: Kubernetes manifests for Discord bot"

# Push
git push origin main
````

### Vérifier sur GitHub

Aller sur **https://github.com/ton-username/lol-esports-k8s-manifests**

Tu devrais voir tous tes fichiers !

---

## 🎯 Créer une Application ArgoCD

### Via l'interface web (recommandé pour débuter)

1. Dans ArgoCD UI, cliquer **+ NEW APP**
2. **Application Name** : `discord-bot`
3. **Project** : `default`
4. **Sync Policy** : `Manual` (on activera automatic après)

**Source section** :

5. **Repository URL** : `https://github.com/ton-username/lol-esports-k8s-manifests`
6. **Revision** : `HEAD` (ou `main`)
7. **Path** : `k8s/apps/discord-bot`

**Destination section** :

8. **Cluster URL** : `https://kubernetes.default.svc`
9. **Namespace** : `lol-esports`

**Directory** :

10. Laisser les valeurs par défaut

Cliquer **CREATE**

### Via YAML (alternative)

**Créer** : `argocd/discord-bot-app.yaml`

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: discord-bot
  namespace: argocd
spec:
  # Project
  project: default
  
  # Source (Git)
  source:
    repoURL: https://github.com/ton-username/lol-esports-k8s-manifests.git
    targetRevision: HEAD
    path: k8s/apps/discord-bot
  
  # Destination (Cluster)
  destination:
    server: https://kubernetes.default.svc
    namespace: lol-esports
  
  # Sync Policy
  syncPolicy:
    # Manual pour l'instant
    automated: null
    
    # Options
    syncOptions:
    - CreateNamespace=true
```

**🎓 Explication** :

```yaml
apiVersion: argoproj.io/v1alpha1
# API custom (CRD fournie par ArgoCD)

kind: Application
# Type de ressource ArgoCD

metadata:
  name: discord-bot
  # Nom de l'Application (dans ArgoCD UI)
  
  namespace: argocd
  # L'Application CRD doit être dans le namespace argocd
```

```yaml
spec:
  project: default
  # Quel Project ArgoCD ?
  # default = Projet par défaut
```

```yaml
  source:
    repoURL: https://github.com/ton-username/lol-esports-k8s-manifests.git
    # URL du repo Git
    
    targetRevision: HEAD
    # Quelle branche/tag/commit ?
    # HEAD = Dernière version de la branche par défaut
    # Ou : main, v1.0.0, abc123def
    
    path: k8s/apps/discord-bot
    # Chemin dans le repo où sont les YAMLs
```

```yaml
  destination:
    server: https://kubernetes.default.svc
    # Cluster de destination
    # https://kubernetes.default.svc = Cluster local (où ArgoCD tourne)
    
    namespace: lol-esports
    # Namespace de destination
```

```yaml
  syncPolicy:
    automated: null
    # null = Sync manuel
    # On configurera l'automatic sync après
    
    syncOptions:
    - CreateNamespace=true
    # Si le namespace n'existe pas, le créer
```

**Appliquer** :

```bash
kubectl apply -f argocd/discord-bot-app.yaml
```

### Voir l'Application dans ArgoCD

Retourner dans l'interface ArgoCD.

Tu devrais voir une nouvelle carte **discord-bot** :

```
┌────────────────────────────────────┐
│  discord-bot                       │
│  ────────────────────────────────  │
│  Status: OutOfSync                 │
│  Health: Missing                   │
│                                    │
│  lol-esports                       │
│  default                           │
└────────────────────────────────────┘
```

**Status** :

- **OutOfSync** : Git ≠ Cluster (normal, on n'a pas encore sync)
- **Missing** : Ressources n'existent pas encore dans le cluster

### Synchroniser manuellement

1. Cliquer sur la carte **discord-bot**
2. Tu vois un graphe des ressources à créer :
    - Deployment
    - PVC
    - SealedSecret
3. Cliquer sur **SYNC**
4. Confirmer → Cliquer **SYNCHRONIZE**

**ArgoCD va** :

1. Cloner le repo Git
2. Lire les YAMLs
3. Appliquer au cluster (`kubectl apply`)

**Durée** : 30 secondes

### Vérifier la synchronisation

Dans ArgoCD UI :

```
┌────────────────────────────────────┐
│  discord-bot                       │
│  ────────────────────────────────  │
│  Status: Synced ✅                 │
│  Health: Healthy ✅                │
│                                    │
│  lol-esports                       │
│  default                           │
└────────────────────────────────────┘
```

Cliquer sur la carte pour voir le graphe détaillé :

```
Application: discord-bot
  │
  ├─ SealedSecret: discord-bot-secret [Synced/Healthy]
  │   └─ Secret: discord-bot-secret [Synced/Healthy]
  │
  ├─ PVC: discord-bot-data [Synced/Bound]
  │
  └─ Deployment: discord-bot [Synced/Healthy]
      └─ ReplicaSet: discord-bot-xxx [Synced/Healthy]
          └─ Pod: discord-bot-xxx-yyy [Synced/Running]
```

**Icônes** :

- ✅ Vert : Healthy
- 🔄 Bleu : Progressing
- ❌ Rouge : Degraded

---

## 🔄 Synchronisation automatique

### Activer le sync automatique

#### Via l'UI

1. Ouvrir l'Application **discord-bot**
2. Cliquer sur **APP DETAILS** (en haut à droite)
3. Section **SYNC POLICY**
4. Cliquer **ENABLE AUTO-SYNC**
5. Options :
    - ✅ **PRUNE RESOURCES** : Supprimer les ressources qui ne sont plus dans Git
    - ✅ **SELF HEAL** : Corriger automatiquement les modifications manuelles
6. Cliquer **OK**

#### Via YAML

**Éditer** : `argocd/discord-bot-app.yaml`

```yaml
spec:
  syncPolicy:
    automated:
      prune: true      # Supprimer ce qui n'est plus dans Git
      selfHeal: true   # Corriger les drifts
    
    syncOptions:
    - CreateNamespace=true
```

**Appliquer** :

```bash
kubectl apply -f argocd/discord-bot-app.yaml
```

### Comprendre les options

#### Prune

**Prune** = Supprimer les ressources qui ne sont plus dans Git

**Exemple** :

```bash
# Tu as un ConfigMap dans Git
k8s/apps/discord-bot/
├── deployment.yaml
└── configmap.yaml  ← Dans Git

# ArgoCD le crée dans le cluster

# Tu supprimes le ConfigMap de Git
git rm k8s/apps/discord-bot/configmap.yaml
git commit -m "Remove configmap"
git push

# Avec prune: true
# → ArgoCD supprime automatiquement le ConfigMap du cluster ✅

# Avec prune: false
# → Le ConfigMap reste dans le cluster (orphelin) ⚠️
```

#### Self Heal

**Self Heal** = Corriger automatiquement les modifications manuelles

**Exemple** :

```bash
# Quelqu'un modifie le deployment manuellement
kubectl scale deployment discord-bot --replicas=3 -n lol-esports

# Dans Git, replicas: 1

# Avec selfHeal: true
# → ArgoCD détecte le drift
# → ArgoCD rescale automatiquement à 1 ✅

# Avec selfHeal: false
# → Le cluster reste avec replicas=3 (OutOfSync) ⚠️
```

**📖 Quand utiliser selfHeal ?**

✅ Production : Oui (enforce l'état Git)  
⚠️ Dev : Peut-être (permet les tests manuels)

---

## 🧪 Tester le workflow GitOps

### Test 1 : Modifier l'image du bot

**Objectif** : Mettre à jour le bot vers une nouvelle version

#### Étape 1 : Build une nouvelle version

```bash
# Build la nouvelle image
docker build -t tonusername/lol-esports-bot:v1.1.0 .

# Push
docker push tonusername/lol-esports-bot:v1.1.0
```

#### Étape 2 : Modifier le YAML dans Git

**Éditer** : `k8s/apps/discord-bot/deployment.yaml`

```yaml
spec:
  template:
    spec:
      containers:
      - name: discord-bot
        image: tonusername/lol-esports-bot:v1.1.0  # ← Changé de v1.0.0 à v1.1.0
```

#### Étape 3 : Commit et push

```bash
cd lol-esports-k8s-manifests

git add k8s/apps/discord-bot/deployment.yaml
git commit -m "Update bot to v1.1.0"
git push origin main
```

#### Étape 4 : Observer ArgoCD

**Dans l'UI ArgoCD** :

1. L'Application passe en **OutOfSync** (jaune)
2. Après < 3 minutes, ArgoCD détecte le changement
3. Si auto-sync : Synchronisation automatique
4. Sinon : Cliquer **SYNC** manuellement
5. ArgoCD fait un rolling update du Deployment
6. Le nouveau pod démarre avec v1.1.0
7. Status retourne à **Synced** ✅

**Logs ArgoCD** :

```
Sync operation to 1234abcd started
Applying resource Deployment/lol-esports/discord-bot
Deployment discord-bot configured
Sync operation to 1234abcd completed
Application reconciled
```

**Vérifier dans le cluster** :

```bash
kubectl get pods -n lol-esports -o wide

# Nouveau pod avec nouvelle image
kubectl describe pod -l app=discord-bot -n lol-esports | grep Image:
# Image: tonusername/lol-esports-bot:v1.1.0 ✅
```

### Test 2 : Rollback avec Git

**Objectif** : Revenir à la version précédente

#### Étape 1 : Revert le commit

```bash
# Voir l'historique
git log --oneline

# Output:
# abc123 Update bot to v1.1.0
# def456 Initial commit

# Revert le dernier commit
git revert abc123

# Ou reset (attention, destructif)
git reset --hard def456
git push --force origin main
```

#### Étape 2 : Observer ArgoCD

ArgoCD détecte le revert et redéploie v1.0.0 automatiquement !

```bash
kubectl describe pod -l app=discord-bot -n lol-esports | grep Image:
# Image: tonusername/lol-esports-bot:v1.0.0 ✅
```

**🎉 Rollback en 2 commandes Git !**

### Test 3 : Drift detection et self-healing

**Objectif** : Modifier manuellement le cluster et voir ArgoCD corriger

#### Étape 1 : Modifier manuellement

```bash
# Changer les replicas (dans Git = 1)
kubectl scale deployment discord-bot --replicas=3 -n lol-esports

# Vérifier
kubectl get deployment discord-bot -n lol-esports
# READY: 3/3 ⚠️
```

#### Étape 2 : Observer ArgoCD

**Avec selfHeal: true** :

1. ArgoCD détecte le drift (< 3 min)
2. Application passe en **OutOfSync**
3. ArgoCD rescale automatiquement à 1
4. Status retourne à **Synced**

```bash
kubectl get deployment discord-bot -n lol-esports
# READY: 1/1 ✅ (corrigé automatiquement)
```

**Logs ArgoCD** :

```
Application discord-bot has OutOfSync resources
Auto-sync is enabled
Initiating automatic sync to revision main
Sync operation started
Applying resource Deployment/lol-esports/discord-bot
Deployment scaled to 1 replica
Sync completed
```

### Test 4 : Ajouter une nouvelle ressource

**Objectif** : Ajouter un ConfigMap

#### Étape 1 : Créer le ConfigMap

**Créer** : `k8s/apps/discord-bot/configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: discord-bot-config
  namespace: lol-esports
data:
  LOG_LEVEL: "INFO"
  RATE_LIMIT: "10"
```

#### Étape 2 : Commit et push

```bash
git add k8s/apps/discord-bot/configmap.yaml
git commit -m "Add ConfigMap for bot configuration"
git push origin main
```

#### Étape 3 : ArgoCD crée le ConfigMap

```bash
# Attendre < 3 min

kubectl get configmap discord-bot-config -n lol-esports
# NAME                  DATA   AGE
# discord-bot-config    2      30s ✅
```

**Dans ArgoCD UI** :

Le graphe montre maintenant le ConfigMap en plus !

### Test 5 : Supprimer une ressource (avec prune)

**Objectif** : Supprimer le ConfigMap

#### Étape 1 : Supprimer du Git

```bash
git rm k8s/apps/discord-bot/configmap.yaml
git commit -m "Remove ConfigMap"
git push origin main
```

#### Étape 2 : ArgoCD supprime du cluster

**Avec prune: true** :

```bash
# Attendre < 3 min

kubectl get configmap discord-bot-config -n lol-esports
# Error: configmaps "discord-bot-config" not found ✅
```

**Logs ArgoCD** :

```
Pruning resource ConfigMap/lol-esports/discord-bot-config
ConfigMap deleted
```

---

## 🎛️ Fonctionnalités avancées ArgoCD

### History et Rollback

**Voir l'historique des syncs** :

1. Ouvrir l'Application **discord-bot**
2. Onglet **HISTORY**
3. Tu vois tous les syncs avec :
    - Revision Git (commit SHA)
    - Date/heure
    - Initiateur (auto vs manuel)

**Rollback vers une version précédente** :

1. Cliquer sur une révision dans l'historique
2. Cliquer **ROLLBACK**
3. Confirmer

ArgoCD va :

- Checkout le commit Git de cette révision
- Resync le cluster

### Diff

**Voir les différences Git vs Cluster** :

1. Ouvrir l'Application **discord-bot**
2. Cliquer sur **APP DIFF**
3. Tu vois un diff détaillé (comme `git diff`)

Exemple :

```diff
--- Cluster
+++ Git
@@ -12,7 +12,7 @@
   spec:
     containers:
     - name: discord-bot
-      image: tonusername/lol-esports-bot:v1.0.0
+      image: tonusername/lol-esports-bot:v1.1.0
```

### Health Checks custom

Par défaut, ArgoCD sait vérifier la santé des ressources standards (Deployment, Service, etc.).

Pour des ressources custom (CRDs), tu peux définir des health checks :

**Exemple** : `argocd-cm` ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  resource.customizations: |
    argoproj.io/Application:
      health.lua: |
        hs = {}
        hs.status = "Healthy"
        if obj.status ~= nil then
          if obj.status.health ~= nil then
            hs.status = obj.status.health.status
            hs.message = obj.status.health.message
          end
        end
        return hs
```

---

## 🚨 Troubleshooting

### Application reste OutOfSync

**Causes possibles** :

1. **Sync automatique désactivé** → Activer auto-sync
2. **Erreur dans les YAMLs** → Voir les logs ArgoCD
3. **Permissions insuffisantes** → Vérifier RBAC

**Debug** :

```bash
# Voir les events
kubectl get events -n lol-esports --sort-by='.lastTimestamp'

# Logs du controller ArgoCD
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller

# Forcer un refresh
argocd app get discord-bot --refresh
```

### Application en Degraded

**Cause** : Une ressource n'est pas healthy

**Debug** :

1. Dans ArgoCD UI, ouvrir l'Application
2. Voir quelle ressource est rouge
3. Cliquer dessus → **LOGS** ou **EVENTS**
4. Corriger le problème dans Git

### Repo Git inaccessible

**Erreur** : `Unable to clone repository`

**Causes** :

1. **Repo privé sans credentials** → Ajouter un Secret avec SSH key ou token
2. **URL incorrecte** → Vérifier l'URL
3. **Branche inexistante** → Vérifier targetRevision

**Ajouter des credentials (si repo privé)** :

```bash
# Via CLI
argocd repo add https://github.com/ton-username/repo.git \
  --username ton-username \
  --password ghp_xxx

# Ou via SSH
argocd repo add git@github.com:ton-username/repo.git \
  --ssh-private-key-path ~/.ssh/id_rsa
```

### Self-heal ne fonctionne pas

**Vérifier** :

```bash
# L'option est bien activée ?
kubectl get app discord-bot -n argocd -o yaml | grep selfHeal
# selfHeal: true ✅

# Forcer une reconciliation
argocd app sync discord-bot
```

---

## 🔄 Configuration pour Failover Automatique

### ArgoCD sur les deux clusters (Recommandé)

**Pour un failover 100% automatique**, ArgoCD doit être installé sur **les deux clusters** (laptop ET EC2).

#### Pourquoi sur les deux clusters ?

**Scénario de failover** :

```
1. Laptop éteint (panne, batterie, etc.)
   ↓
2. Lambda détecte la panne (< 5 min)
   ↓
3. Lambda démarre l'EC2
   ↓
4. EC2 boot (2-3 min)
   ↓
5. K3s démarre automatiquement (systemd)
   ↓
6. ArgoCD démarre sur l'EC2
   ↓
7. ArgoCD redéploie automatiquement le bot depuis Git
   ↓
8. Bot opérationnel sur EC2 ! ✅
```

#### Configuration sur laptop

**Sur le laptop** (déjà fait dans cette phase) :

```bash
# ArgoCD est installé et configuré
helm install argocd argo/argo-cd \
  --namespace argocd \
  --values argocd-values.yaml
```

**ArgoCD laptop** :
- Surveille le repo Git
- Déploie automatiquement le bot
- Self-heal activé
- **Cluster primaire** (99% du temps)

#### Configuration sur EC2 (identique)

**Sur l'EC2** (à faire après avoir configuré K3s sur EC2 en Phase 4) :

```bash
# Se connecter à l'EC2
ssh ubuntu@ec2-ip

# Installer ArgoCD (même commandes que sur laptop)
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update

kubectl create namespace argocd

# Utiliser le même fichier argocd-values.yaml
helm install argocd argo/argo-cd \
  --namespace argocd \
  --values argocd-values.yaml

# Créer la même Application ArgoCD
kubectl apply -f argocd/discord-bot-app.yaml
```

**ArgoCD EC2** :
- Surveille le **même repo Git**
- Quand l'EC2 démarre (failover), ArgoCD redéploie automatiquement le bot
- **Cluster de backup** (1% du temps)
- **Pas besoin d'intervention manuelle lors du failover !**

#### Option alternative (non recommandée)

**ArgoCD uniquement sur laptop** :

❌ Failover **manuel** requis :
- Lambda démarre l'EC2
- Tu dois SSH sur l'EC2
- Tu dois déployer le bot manuellement avec `kubectl apply`

✅ Avantage : Légèrement plus simple
❌ Inconvénient : Pas de failover 100% automatique

**Conclusion** : Pour un vrai failover automatique, **installer ArgoCD sur les deux clusters**.

---

## 📝 Récapitulatif

### Ce qu'on a mis en place

✅ **ArgoCD installé** : Helm chart avec config optimisée
✅ **Repo Git** : GitHub avec tous les manifests
✅ **Application ArgoCD** : discord-bot avec auto-sync
✅ **Workflow GitOps** : Commit → Push → Sync automatique
✅ **Self-healing** : Détection et correction des drifts
✅ **Prune** : Suppression automatique des ressources obsolètes
✅ **Configuration deux clusters** : ArgoCD sur laptop ET EC2 pour failover automatique

### Workflow complet

```
1. Développement
   └─ Modifier YAML localement

2. Git
   ├─ git add
   ├─ git commit
   └─ git push

3. ArgoCD (automatique)
   ├─ Détecte le changement (< 3 min)
   ├─ Clone le repo
   ├─ Compare Git vs Cluster
   ├─ Sync les différences
   └─ Vérifie la santé

4. Cluster
   └─ Ressources à jour ✅
```

### Commandes essentielles

```bash
# Port-forward ArgoCD
kubectl port-forward svc/argocd-server -n argocd 8080:443

# CLI ArgoCD
argocd login localhost:8080
argocd app list
argocd app get discord-bot
argocd app sync discord-bot
argocd app history discord-bot

# Forcer un refresh
argocd app get discord-bot --refresh

# Voir les logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller
```

### Architecture finale

```
GitHub Repo
  ↓ (Source of Truth)
ArgoCD
  ├─ Détecte changements
  ├─ Synchronise
  └─ Self-heal
  ↓
Cluster K8s
  └─ discord-bot Application
      ├─ Deployment ✅
      ├─ PVC ✅
      └─ SealedSecret ✅
```

---

## 🎉 Félicitations !

Tu as maintenant un **workflow GitOps complet** :

- ✅ Git comme source de vérité unique
- ✅ Déploiements automatiques
- ✅ Rollback facile (`git revert`)
- ✅ Historique complet
- ✅ Self-healing (drift correction)

**Prochaine étape** : Phase 7 - Lambda Watchdog (code Python pour le failover automatique) ! 🤖

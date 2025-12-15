# ☸️ Phase 4 : Déploiements Kubernetes Production-Ready

[← Phase 3 - Docker](Part_4_Phase_3_Docker.md) | [Phase 5 - Monitoring →](Part_6_Phase_5_Monitoring.md)

---

## 📚 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Comprendre les ressources Kubernetes](#comprendre-les-ressources-kubernetes)
3. [Créer le namespace](#cr%C3%A9er-le-namespace)
4. [Sealed Secrets - Secrets sécurisés](#sealed-secrets)
5. [PersistentVolumeClaim - Storage persistant](#persistentvolumeclaim)
6. [Security Context - Sécurité des pods](#security-context)
7. [Deployment complet](#deployment-complet)
8. [Resource Quotas - Limites](#resource-quotas)
9. [Validation et tests](#validation-et-tests)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Vue d'ensemble

### Qu'est-ce qu'on va déployer ?

On va créer un déploiement **production-ready** de notre bot Discord avec :

✅ **Namespace** : Isolation logique  
✅ **Sealed Secrets** : Secrets chiffrés pour Git (GitOps)  
✅ **PVC** : Storage persistant pour les données  
✅ **Security Context** : Pod non-root, filesystem read-only  
✅ **Deployment** : 1 replica avec health checks  
✅ **Resource Quotas** : Limites CPU/RAM

### Pourquoi tout ça ?

**Sans ces composants** :

- ❌ Secrets en clair dans Git (danger !)
- ❌ Données perdues à chaque redémarrage
- ❌ Pods tournent en root (vulnérable)
- ❌ Un pod peut monopoliser toutes les ressources

**Avec ces composants** :

- ✅ Secrets sécurisés dans Git
- ✅ Données persistantes
- ✅ Sécurité renforcée
- ✅ Resources contrôlées

### Architecture du déploiement

```
┌─────────────────────────────────────────────────────┐
│           Namespace: lol-esports                     │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────────────┐      ┌──────────────────┐    │
│  │ SealedSecret     │      │ PVC (1Gi)        │    │
│  │ ──────────────   │      │ ──────────────   │    │
│  │ DISCORD_TOKEN    │      │ /app/data        │    │
│  │ (chiffré)        │      │ ReadWriteOnce    │    │
│  └────────┬─────────┘      └────────┬─────────┘    │
│           │                         │               │
│           ▼                         ▼               │
│  ┌─────────────────────────────────────────┐       │
│  │         Deployment                      │       │
│  │  ─────────────────────────────────────  │       │
│  │  Replicas: 1                            │       │
│  │  Security Context:                      │       │
│  │    - runAsUser: 1000                    │       │
│  │    - readOnlyRootFilesystem: true       │       │
│  │  Resources:                             │       │
│  │    - CPU: 100m-200m                     │       │
│  │    - RAM: 128Mi-256Mi                   │       │
│  │  Health checks: ✓                       │       │
│  └─────────────────────────────────────────┘       │
│                                                      │
│  ┌──────────────────┐                               │
│  │ ResourceQuota    │                               │
│  │ ──────────────   │                               │
│  │ Max CPU: 2       │                               │
│  │ Max RAM: 4Gi     │                               │
│  └──────────────────┘                               │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## 📖 Comprendre les ressources Kubernetes

### Qu'est-ce qu'une "ressource" Kubernetes ?

**Ressource** = Objet que tu déclares dans un fichier YAML

Exemples :

- **Pod** : Le plus petit objet déployable (1+ containers)
- **Deployment** : Gère des pods avec des replicas
- **Service** : Expose des pods sur le réseau
- **Secret** : Stocke des données sensibles
- **PersistentVolumeClaim** : Demande de stockage

### Format YAML standard

Toutes les ressources Kubernetes suivent ce format :

```yaml
apiVersion: v1          # ← Version de l'API Kubernetes
kind: Pod               # ← Type de ressource
metadata:               # ← Métadonnées (nom, labels, etc.)
  name: mon-pod
  namespace: default
spec:                   # ← Spécification (configuration)
  containers:
  - name: mon-container
    image: nginx
```

**🎓 Anatomie complète** :

```yaml
apiVersion: apps/v1
# API version = Quelle version de l'API Kubernetes utiliser
# Format : <groupe>/<version>
# Exemples :
#   v1                    (core API, pas de groupe)
#   apps/v1               (deployments, daemonsets)
#   batch/v1              (jobs, cronjobs)
#   networking.k8s.io/v1  (ingress)

kind: Deployment
# Type de ressource
# Défini par Kubernetes (tu ne peux pas inventer)

metadata:
# Métadonnées = Informations sur la ressource
  name: mon-app
  # Nom unique dans le namespace
  
  namespace: production
  # Dans quel namespace ? (défaut = "default")
  
  labels:
  # Labels = Key-value pairs pour organiser
    app: mon-app
    version: v1.0.0
  
  annotations:
  # Annotations = Métadonnées non-identifiantes
    description: "Mon application"

spec:
# Spécification = Comment configurer cette ressource
# Le contenu dépend du "kind"
  # ...
```

**🔍 Ce qui vient de quoi** :

|Élément|Source|
|---|---|
|Structure `apiVersion, kind, metadata, spec`|**Standard Kubernetes**|
|Valeurs `apiVersion` (ex: apps/v1)|**Standard Kubernetes**|
|Valeurs `kind` (ex: Deployment)|**Standard Kubernetes**|
|Noms, labels, annotations|**TON CHOIX**|
|Contenu de `spec`|**Mix** (champs Kubernetes + tes valeurs)|

### Comment Kubernetes utilise les YAML ?

```
1. Tu écris le YAML (déclaratif)
   ↓
2. kubectl apply -f fichier.yaml
   ↓
3. kubectl envoie au cluster
   ↓
4. API Server valide le YAML
   ↓
5. etcd stocke la configuration
   ↓
6. Controller reconcilie l'état
   ↓
7. Scheduler place les pods
   ↓
8. Kubelet démarre les containers
```

**Déclaratif vs Impératif** :

```bash
# Impératif (tu dis COMMENT faire)
kubectl create deployment mon-app --image=nginx
kubectl scale deployment mon-app --replicas=3
kubectl set image deployment/mon-app nginx=nginx:1.20

# Déclaratif (tu dis CE QUE tu veux)
kubectl apply -f deployment.yaml
# Kubernetes fait le nécessaire pour atteindre cet état
```

---

## 📁 Créer le namespace

### 📖 Qu'est-ce qu'un namespace ?

**Namespace** = Espace de noms = Partition logique dans le cluster

**Analogie** : C'est comme des dossiers sur ton ordinateur

- `/home/user/projets/projet-a/`
- `/home/user/projets/projet-b/`

Dans Kubernetes :

- `namespace: production`
- `namespace: staging`
- `namespace: lol-esports`

**Avantages** :

- ✅ Isolation : Les ressources ne se mélangent pas
- ✅ Organisation : Facile de retrouver ses ressources
- ✅ Sécurité : Tu peux limiter les permissions par namespace
- ✅ Quotas : Tu peux définir des limites par namespace

### Les namespaces par défaut

Kubernetes crée automatiquement ces namespaces :

```bash
kubectl get namespaces

# Output :
# NAME              STATUS   AGE
# default           Active   10d   ← Namespace par défaut
# kube-system       Active   10d   ← Composants système K8s
# kube-public       Active   10d   ← Données publiques
# kube-node-lease   Active   10d   ← Info sur les nodes
```

**⚠️ Best practice** : Ne PAS utiliser `default` pour tes apps !

Crée toujours un namespace dédié.

### Créer notre namespace

#### Option 1 : Commande impérative

```bash
kubectl create namespace lol-esports
```

#### Option 2 : Fichier YAML (recommandé pour GitOps)

**Créer le fichier** : `k8s/base/namespace.yaml`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: lol-esports
  labels:
    app.kubernetes.io/name: lol-esports
    app.kubernetes.io/part-of: discord-bot
```

**🎓 Explication** :

```yaml
apiVersion: v1
# Namespaces sont dans la core API (pas de groupe)

kind: Namespace
# Type de ressource

metadata:
  name: lol-esports
  # Nom du namespace (doit être unique dans le cluster)
  # Conventions : lowercase, hyphens (pas underscore)
  
  labels:
    app.kubernetes.io/name: lol-esports
    # Label standard Kubernetes
    # Aide à organiser et filtrer
    
    app.kubernetes.io/part-of: discord-bot
    # Indique que ce namespace fait partie du projet discord-bot
```

**🔍 Labels standards Kubernetes** :

|Label|Usage|
|---|---|
|`app.kubernetes.io/name`|Nom de l'application|
|`app.kubernetes.io/instance`|Instance unique (ex: production, staging)|
|`app.kubernetes.io/version`|Version de l'app|
|`app.kubernetes.io/component`|Composant (ex: database, frontend)|
|`app.kubernetes.io/part-of`|Nom du projet/système parent|
|`app.kubernetes.io/managed-by`|Outil de gestion (ex: Helm, ArgoCD)|

Ces labels sont **optionnels** mais **recommandés** pour l'organisation.

#### Appliquer

```bash
kubectl apply -f k8s/base/namespace.yaml

# Output:
# namespace/lol-esports created
```

#### Vérifier

```bash
# Lister les namespaces
kubectl get namespaces

# Voir les détails
kubectl describe namespace lol-esports

# Output:
# Name:         lol-esports
# Labels:       app.kubernetes.io/name=lol-esports
#               app.kubernetes.io/part-of=discord-bot
# Status:       Active
```

### Utiliser le namespace

**Toutes les commandes suivantes** devront spécifier le namespace :

```bash
# Avec -n
kubectl get pods -n lol-esports

# Ou définir le namespace par défaut pour le contexte
kubectl config set-context --current --namespace=lol-esports

# Maintenant, plus besoin de -n !
kubectl get pods
```

---

## 🔐 Sealed Secrets

### 📖 Le problème des secrets Kubernetes

**Secrets Kubernetes natifs** sont encodés en Base64, **pas chiffrés** !

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: discord-bot-secret
type: Opaque
data:
  DISCORD_TOKEN: VG9rZW5IZXJl  # ← Base64, facile à décoder !
```

Décoder :

```bash
echo "VG9rZW5IZXJl" | base64 -d
# Output: TokenHere
```

**❌ Problème** : Tu ne peux PAS commiter ce fichier dans Git !

**GitOps cassé** : Comment gérer les secrets dans Git ?

### 📖 La solution : Sealed Secrets

**Sealed Secrets** = Secrets chiffrés avec cryptographie asymétrique

**Comment ça marche ?**

```
1. Tu as un Secret normal (YAML)
   ↓
2. Tu utilises kubeseal avec la clé publique du cluster
   ↓
3. kubeseal chiffre le Secret → SealedSecret (YAML chiffré)
   ↓
4. Tu commites le SealedSecret dans Git ✅
   ↓
5. Tu appliques le SealedSecret au cluster
   ↓
6. Le controller Sealed Secrets déchiffre avec la clé privée
   ↓
7. Un Secret normal est créé dans le cluster
   ↓
8. Ton pod lit le Secret
```

**Schéma** :

```
┌────────────────┐
│  TON LAPTOP    │
│                │
│  Secret.yaml   │  ────kubeseal────►  SealedSecret.yaml
│  (clair)       │     (clé pub)       (chiffré) ✅ Commit Git
└────────────────┘                            │
                                              │
                                              â–¼
                                  ┌───────────────────────┐
                                  │   CLUSTER K8S         │
                                  │                       │
                                  │  SealedSecret         │
                                  │        │              │
                                  │        ▼              │
                                  │  Controller déchiffre │
                                  │   (clé privée)        │
                                  │        │              │
                                  │        ▼              │
                                  │   Secret (clair)      │
                                  │        │              │
                                  │        ▼              │
                                  │     Pod lit           │
                                  └───────────────────────┘
```

### Installation du controller Sealed Secrets

```bash
# Installer le controller dans kube-system
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml
```

**🎓 Que fait cette commande ?**

Elle crée :

- Un **Deployment** : Le controller qui tourne en pod
- Un **Service** : Pour exposer le controller
- Un **ServiceAccount** : Pour les permissions
- Des **RBAC rules** : Permissions pour déchiffrer

**Vérifier l'installation** :

```bash
kubectl get pods -n kube-system | grep sealed-secrets

# Output:
# sealed-secrets-controller-xxxx   1/1   Running   0   30s
```

### Installer kubeseal (CLI)

**Sur Arch Linux** :

```bash
yay -S kubeseal
```

**Sur Mac** :

```bash
brew install kubeseal
```

**Vérifier** :

```bash
kubeseal --version

# Output:
# kubeseal version: 0.24.0
```

### Créer un Sealed Secret

#### Étape 1 : Créer le secret normal (ne PAS commiter !)

```bash
kubectl create secret generic discord-bot-secret \
  --from-literal=DISCORD_TOKEN="TON_TOKEN_DISCORD" \
  --from-literal=MATCH_CHANNEL_ID="123456789" \
  --from-literal=NEWS_CHANNEL_ID="987654321" \
  --namespace=lol-esports \
  --dry-run=client -o yaml > discord-bot-secret.yaml
```

**🎓 Explication** :

```bash
kubectl create secret generic discord-bot-secret
# Créer un secret de type "generic" (Opaque)
# Nom : discord-bot-secret

--from-literal=DISCORD_TOKEN="TON_TOKEN_DISCORD"
# Créer une clé DISCORD_TOKEN avec la valeur
# from-literal = Depuis la ligne de commande (pas un fichier)

--from-literal=MATCH_CHANNEL_ID="123456789"
# ID du channel Discord pour les matchs
# Remplace par ton vrai ID

--from-literal=NEWS_CHANNEL_ID="987654321"
# ID du channel Discord pour les news
# Remplace par ton vrai ID

--namespace=lol-esports
# Dans quel namespace ?

--dry-run=client
# Ne PAS créer réellement (simulation)
# client = Simulation côté client (kubectl)

-o yaml
# Output en format YAML

> discord-bot-secret.yaml
# Rediriger vers un fichier
```

**Contenu de `discord-bot-secret.yaml`** :

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: discord-bot-secret
  namespace: lol-esports
type: Opaque
data:
  DISCORD_TOKEN: VG9uVG9rZW5EaXNjb3JkSGVyZQ==        # Base64 !
  MATCH_CHANNEL_ID: MTIzNDU2Nzg5                    # Base64 !
  NEWS_CHANNEL_ID: OTg3NjU0MzIx                      # Base64 !
```

**⚠️ NE JAMAIS COMMITER CE FICHIER !**

#### Étape 2 : Sceller le secret (chiffrer)

```bash
kubeseal --format yaml < discord-bot-secret.yaml > discord-bot-sealed-secret.yaml
```

**🎓 Que fait kubeseal ?**

1. Lit le Secret en clair depuis stdin (`< discord-bot-secret.yaml`)
2. Se connecte au cluster pour récupérer la clé publique du controller
3. Chiffre chaque valeur avec la clé publique
4. Génère un SealedSecret en YAML
5. Écrit vers stdout (`> discord-bot-sealed-secret.yaml`)

**Contenu de `discord-bot-sealed-secret.yaml`** :

```yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: discord-bot-secret
  namespace: lol-esports
spec:
  encryptedData:
    DISCORD_TOKEN: AgBHj8xVGq2K... (500+ caractères chiffrés)
    MATCH_CHANNEL_ID: AgCYt9Kp3mL... (500+ caractères chiffrés)
    NEWS_CHANNEL_ID: AgDZa1Lq4nM... (500+ caractères chiffrés)
  template:
    metadata:
      name: discord-bot-secret
      namespace: lol-esports
    type: Opaque
```

**🎓 Anatomie du SealedSecret** :

```yaml
apiVersion: bitnami.com/v1alpha1
# API custom (CRD = Custom Resource Definition)
# Fournie par le controller Sealed Secrets

kind: SealedSecret
# Type de ressource custom

metadata:
  name: discord-bot-secret
  # Nom du SealedSecret
  # Générera un Secret avec le même nom
  
  namespace: lol-esports
  # IMPORTANT : Doit matcher le namespace du Secret

spec:
  encryptedData:
    DISCORD_TOKEN: AgBHj8xVGq2K...
    # Token Discord chiffré avec la clé publique du cluster
    # Préfixe "AgB" = Indicateur de version de chiffrement
    
    MATCH_CHANNEL_ID: AgCYt9Kp3mL...
    # ID du channel Discord pour les matchs (chiffré)
    
    NEWS_CHANNEL_ID: AgDZa1Lq4nM...
    # ID du channel Discord pour les news (chiffré)
  
  template:
    # Template du Secret qui sera créé après déchiffrement
    metadata:
      name: discord-bot-secret
      namespace: lol-esports
    type: Opaque
    # Type du Secret final
```

**🔍 Ce qui vient de quoi** :

|Élément|Source|
|---|---|
|`apiVersion: bitnami.com/v1alpha1`|**Controller Sealed Secrets**|
|`kind: SealedSecret`|**Controller Sealed Secrets**|
|Structure `encryptedData`|**Controller Sealed Secrets**|
|Données chiffrées|**TON SECRET + clé publique cluster**|
|Noms, namespace|**TON CHOIX**|

#### Étape 3 : Nettoyer le secret non chiffré

```bash
# SUPPRIMER le fichier non chiffré !
rm discord-bot-secret.yaml

# ✅ Garder seulement le SealedSecret
# ✅ Ce fichier PEUT être commité dans Git
```

#### Étape 4 : Appliquer le SealedSecret

```bash
kubectl apply -f discord-bot-sealed-secret.yaml

# Output:
# sealedsecret.bitnami.com/discord-bot-secret created
```

**Ce qui se passe** :

1. Le SealedSecret est créé dans le cluster
2. Le controller Sealed Secrets détecte le nouveau SealedSecret
3. Il déchiffre les données avec sa clé privée
4. Il crée un Secret classique `discord-bot-secret`
5. Les pods peuvent maintenant lire ce Secret !

#### Vérifier

```bash
# Voir le SealedSecret
kubectl get sealedsecrets -n lol-esports

# Output:
# NAME                  STATUS   SYNCED   AGE
# discord-bot-secret             True     10s

# Voir le Secret créé automatiquement
kubectl get secrets -n lol-esports

# Output:
# NAME                  TYPE     DATA   AGE
# discord-bot-secret    Opaque   2      10s

# Vérifier le contenu (Base64)
kubectl get secret discord-bot-secret -n lol-esports -o yaml
```

### Mettre à jour un Sealed Secret

**Problème** : Le token Discord a changé, comment mettre à jour ?

**Solution** : Recréer et resceller le secret

```bash
# 1. Créer le nouveau secret
kubectl create secret generic discord-bot-secret \
  --from-literal=DISCORD_TOKEN="NOUVEAU_TOKEN" \
  --from-literal=MATCH_CHANNEL_ID="123456789" \
  --from-literal=NEWS_CHANNEL_ID="987654321" \
  --namespace=lol-esports \
  --dry-run=client -o yaml > discord-bot-secret-new.yaml

# 2. Resceller
kubeseal --format yaml < discord-bot-secret-new.yaml > discord-bot-sealed-secret.yaml

# 3. Nettoyer
rm discord-bot-secret-new.yaml

# 4. Appliquer (écrase l'ancien)
kubectl apply -f discord-bot-sealed-secret.yaml

# 5. Redémarrer les pods pour recharger le secret
kubectl rollout restart deployment/discord-bot -n lol-esports
```

### Créer le fichier final

**Créer** : `k8s/apps/discord-bot/sealed-secret.yaml`

Copier le contenu de `discord-bot-sealed-secret.yaml` que tu viens de créer.

**✅ Ce fichier peut être commité dans Git !**

---

## 💾 PersistentVolumeClaim

### 📖 Le problème du storage éphémère

**Par défaut**, les données dans un container sont **éphémères** :

```
Pod démarre → Écrit fichier → Pod crash
                  ↓
           Fichier perdu ! ❌
```

**Exemple** :

```bash
# Dans le pod
echo "Hello" > /app/data.txt

# Pod redémarre
# data.txt n'existe plus !
```

### 📖 La solution : Volumes persistants

Kubernetes sépare le **storage** du **pod** :

```
Pod ──► PVC ──► PV ──► Disk physique
        │       │
        │       └─ PersistentVolume (géré par le cluster)
        │
        └─ PersistentVolumeClaim (demande de storage)
```

**Analogie** :

- **PV** = Espace de stockage physique (disque dur)
- **PVC** = "Bon de commande" pour du stockage
- **Pod** = Utilise le stockage via la PVC

### Types de volumes

|Type|Persistant ?|Use case|
|---|---|---|
|**emptyDir**|❌|Cache temporaire, partagé entre containers du pod|
|**hostPath**|⚠️|Monter un dossier de l'hôte (dangereux, pas portable)|
|**PersistentVolume**|✅|Storage qui survit au pod|

### Access Modes

|Mode|Abréviation|Signification|
|---|---|---|
|**ReadWriteOnce**|RWO|Lecture/écriture par **1 seul node**|
|**ReadOnlyMany**|ROX|Lecture seule par **plusieurs nodes**|
|**ReadWriteMany**|RWX|Lecture/écriture par **plusieurs nodes**|

**Notre cas** : Bot Discord = 1 replica = **ReadWriteOnce** suffit

### Comment K3s gère le storage

K3s inclut **local-path-provisioner** :

- Crée automatiquement des PV sur demande
- Stocke les données dans `/var/lib/rancher/k3s/storage/`
- Pas besoin de créer manuellement les PV !

### Créer le PVC

**Créer** : `k8s/apps/discord-bot/pvc.yaml`

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: discord-bot-data
  namespace: lol-esports
  labels:
    app: discord-bot
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

**🎓 Explication ligne par ligne** :

```yaml
apiVersion: v1
# PVC est dans la core API

kind: PersistentVolumeClaim
# Type de ressource

metadata:
  name: discord-bot-data
  # Nom de la PVC
  # On va référencer ce nom dans le Deployment
  
  namespace: lol-esports
  # Dans quel namespace
  
  labels:
    app: discord-bot
    # Label pour organiser

spec:
  accessModes:
    - ReadWriteOnce
    # RWO = Un seul node peut monter ce volume
    # Suffisant pour notre bot (1 replica)
  
  resources:
    requests:
      storage: 1Gi
      # On demande 1 Gigabyte de stockage
      # Valeurs possibles : 100Mi, 1Gi, 10Gi, etc.
```

**🔍 Ce qui vient de quoi** :

|Élément|Source|
|---|---|
|`apiVersion: v1`|**Standard Kubernetes**|
|`kind: PersistentVolumeClaim`|**Standard Kubernetes**|
|`accessModes`|**Standard Kubernetes** (liste finie d'options)|
|`ReadWriteOnce`|**TON CHOIX** (adapté à ton use case)|
|`storage: 1Gi`|**TON CHOIX** (besoin estimé)|

**📖 Pourquoi 1Gi ?**

Bot Discord :

- Logs : quelques MB
- Base SQLite : quelques MB
- Cache : quelques MB

**Total** : < 100 MB → 1Gi largement suffisant avec marge

#### Appliquer

```bash
kubectl apply -f k8s/apps/discord-bot/pvc.yaml

# Output:
# persistentvolumeclaim/discord-bot-data created
```

#### Vérifier

```bash
# Voir la PVC
kubectl get pvc -n lol-esports

# Output:
# NAME               STATUS   VOLUME                                     CAPACITY   ACCESS MODES   AGE
# discord-bot-data   Bound    pvc-abc123-def456-...                     1Gi        RWO            10s

# Voir le PV créé automatiquement
kubectl get pv

# Output:
# NAME                      CAPACITY   ACCESS MODES   RECLAIM POLICY   STATUS   CLAIM                          AGE
# pvc-abc123-def456-...    1Gi        RWO            Delete           Bound    lol-esports/discord-bot-data   10s
```

**📖 Status "Bound"** :

- **Pending** : En attente de création du PV
- **Bound** : PVC liée à un PV ✅
- **Lost** : PV a été supprimé mais PVC existe encore

#### Détails de la PVC

```bash
kubectl describe pvc discord-bot-data -n lol-esports

# Output:
# Name:          discord-bot-data
# Namespace:     lol-esports
# StorageClass:  local-path
# Status:        Bound
# Volume:        pvc-abc123-def456-...
# Labels:        app=discord-bot
# Capacity:      1Gi
# Access Modes:  RWO
# VolumeMode:    Filesystem
# Used By:       <none> (pas encore utilisé par un pod)
```

**📖 StorageClass "local-path"** :

C'est le provisioner de K3s. Il crée automatiquement un dossier sur le node.

---

## 🛡️ Security Context

### 📖 Le problème de root

**Par défaut**, containers tournent en **root** (UID 0) :

```bash
# Dans un pod par défaut
whoami
# Output: root ❌
```

**Dangers** :

1. **Si le bot est hacké** → L'attaquant a les droits root
2. **Il peut** :
    - Installer des packages malveillants
    - Lire des secrets d'autres containers
    - Modifier le filesystem
    - Escalader vers l'hôte (si mal configuré)

**Analogie** : C'est comme donner les clés de ta maison à un inconnu.

### 📖 La solution : Security Context

**Security Context** = Configuration de sécurité d'un pod/container

**2 niveaux** :

1. **Pod Security Context** : S'applique à tous les containers du pod
2. **Container Security Context** : S'applique à un container spécifique

### Pod Security Context

Paramètres au niveau du **pod** :

|Paramètre|Effet|
|---|---|
|`runAsUser`|UID de l'utilisateur (ex: 1000)|
|`runAsGroup`|GID du groupe (ex: 1000)|
|`fsGroup`|Groupe propriétaire des volumes montés|
|`runAsNonRoot`|Vérifie que l'user n'est pas root|
|`seccompProfile`|Profil seccomp (filtrage syscalls)|
|`seLinuxOptions`|Options SELinux|

### Container Security Context

Paramètres au niveau du **container** :

|Paramètre|Effet|
|---|---|
|`runAsUser`|Override du pod-level|
|`runAsGroup`|Override du pod-level|
|`runAsNonRoot`|Vérifie que l'user n'est pas root|
|`allowPrivilegeEscalation`|Autoriser l'escalade de privilèges ?|
|`readOnlyRootFilesystem`|Filesystem racine en lecture seule|
|`capabilities`|Ajouter/retirer des Linux capabilities|

### Notre configuration

**Objectif** : Configuration **Restricted** (la plus sécurisée)

```yaml
spec:
  # Pod-level
  securityContext:
    runAsUser: 1000      # UID non-root
    runAsGroup: 1000     # GID non-root
    fsGroup: 1000        # Groupe pour volumes
  
  containers:
  - name: discord-bot
    # Container-level
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      runAsNonRoot: true
      capabilities:
        drop:
          - ALL
```

**🎓 Explication détaillée** :

#### Pod-level Security Context

```yaml
securityContext:
  runAsUser: 1000
  # Tous les processus tournent avec UID 1000
  # Match le user "botuser" créé dans le Dockerfile
  # Pas root (UID 0) ✅
  
  runAsGroup: 1000
  # Group ID = 1000
  # Match le groupe "botuser"
  
  fsGroup: 1000
  # Les volumes montés (PVC) appartiennent au groupe 1000
  # Permet au user 1000 d'écrire dans le volume
```

**📖 Pourquoi fsGroup ?**

Sans `fsGroup`, le volume pourrait appartenir à root :

```bash
# Sans fsGroup
ls -la /app/data
# drwxr-xr-x root root /app/data
# ↑ Le user 1000 ne peut pas écrire ! ❌

# Avec fsGroup: 1000
ls -la /app/data
# drwxrwsr-x root 1000 /app/data
# ↑ Le groupe 1000 peut écrire ✅
```

#### Container-level Security Context

```yaml
securityContext:
  allowPrivilegeEscalation: false
  # Empêche un processus d'obtenir plus de privilèges
  # Exemple : Empêche sudo, setuid binaries
  # Best practice : toujours false
  
  readOnlyRootFilesystem: true
  # Le filesystem racine (/) est en lecture seule
  # Le container ne peut PAS écrire dans /etc, /usr, /bin, etc.
  # Il peut SEULEMENT écrire dans les volumes montés
  
  runAsNonRoot: true
  # Kubernetes vérifie que l'user n'est PAS root
  # Si l'image essaie de tourner en root → Pod refuse de démarrer
  
  capabilities:
    drop:
      - ALL
    # Retire TOUTES les Linux capabilities
    # Capabilities = Privilèges granulaires (ex: CAP_NET_ADMIN)
```

**📖 readOnlyRootFilesystem**

Avec `readOnlyRootFilesystem: true`, le container ne peut écrire nulle part sauf :

- Volumes montés (PVC)
- emptyDir volumes

**Problème** : Certaines apps ont besoin d'écrire dans `/tmp`

**Solution** : Monter un volume tmpfs sur `/tmp`

```yaml
volumeMounts:
- name: tmp
  mountPath: /tmp

volumes:
- name: tmp
  emptyDir: {}
```

### 🔍 Ce qui vient de quoi

|Paramètre|Source|
|---|---|
|Tous les champs Security Context|**Standard Kubernetes**|
|UID/GID `1000`|**TON CHOIX** (mais convention Linux)|
|`allowPrivilegeEscalation: false`|**Best practice** (toujours false)|
|`readOnlyRootFilesystem: true`|**Best practice** (prod)|
|`runAsNonRoot: true`|**Best practice** (prod)|
|`capabilities: drop ALL`|**Best practice** (principe du moindre privilège)|

### Pod Security Standards (PSS)

Kubernetes définit 3 niveaux de sécurité :

#### 1. Privileged (permissif)

**Aucune restriction**

- Containers peuvent tourner en root
- Privilèges complets

**Use case** : Outils système (monitoring agents, CNI plugins)

#### 2. Baseline (minimal)

**Restrictions de base**

- ❌ hostNetwork, hostPID, hostIPC
- ❌ Privilèges élevés
- ✅ Peut tourner en root (mais déconseillé)

**Use case** : Apps legacy qui nécessitent root

#### 3. Restricted (strict)

**Restrictions maximales**

- ✅ runAsNonRoot: true
- ✅ allowPrivilegeEscalation: false
- ✅ Capabilities drop ALL
- ✅ seccompProfile type RuntimeDefault

**Use case** : Applications production (nous !)

**Notre config suit le niveau Restricted** ✅

---

## 🚀 Deployment complet

### 📖 Qu'est-ce qu'un Deployment ?

**Deployment** = Gère des pods avec :

- Nombre de replicas
- Rolling updates (mises à jour progressives)
- Rollback automatique si problème
- Self-healing (redémarre les pods crashés)

**Schéma** :

```
Deployment
  │
  ├─ ReplicaSet (v1.0.0)
  │   ├─ Pod 1 ✅
  │   ├─ Pod 2 ✅
  │   └─ Pod 3 ✅
  │
  └─ ReplicaSet (v1.1.0) - ancien
      └─ (vide)
```

### Le fichier Deployment complet

**Créer** : `k8s/apps/discord-bot/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: discord-bot
  namespace: lol-esports
  labels:
    app: discord-bot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: discord-bot
  template:
    metadata:
      labels:
        app: discord-bot
    spec:
      # ══════════════════════════════════════════════════════
      # SECURITY CONTEXT (POD-LEVEL)
      # ══════════════════════════════════════════════════════
      securityContext:
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      
      # ══════════════════════════════════════════════════════
      # NODE AFFINITY - Préférer le laptop
      # ══════════════════════════════════════════════════════
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: kubernetes.io/hostname
                operator: In
                values:
                - laptop-hostname  # ← Remplace par le hostname de ton laptop
      
      # ══════════════════════════════════════════════════════
      # CONTAINERS
      # ══════════════════════════════════════════════════════
      containers:
      - name: discord-bot
        image: tonusername/lol-esports-bot:v1.0.0
        imagePullPolicy: Always
        
        # ────────────────────────────────────────────────────
        # SECURITY CONTEXT (CONTAINER-LEVEL)
        # ────────────────────────────────────────────────────
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          capabilities:
            drop:
              - ALL
        
        # ────────────────────────────────────────────────────
        # VARIABLES D'ENVIRONNEMENT (depuis Secret)
        # ────────────────────────────────────────────────────
        env:
        - name: DISCORD_TOKEN
          valueFrom:
            secretKeyRef:
              name: discord-bot-secret
              key: DISCORD_TOKEN
        - name: MATCH_CHANNEL_ID
          valueFrom:
            secretKeyRef:
              name: discord-bot-secret
              key: MATCH_CHANNEL_ID
        - name: NEWS_CHANNEL_ID
          valueFrom:
            secretKeyRef:
              name: discord-bot-secret
              key: NEWS_CHANNEL_ID
        
        # ────────────────────────────────────────────────────
        # RESOURCES (CPU + RAM)
        # ────────────────────────────────────────────────────
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        
        # ────────────────────────────────────────────────────
        # VOLUME MOUNTS
        # ────────────────────────────────────────────────────
        volumeMounts:
        - name: bot-data
          mountPath: /app/data
        - name: tmp
          mountPath: /tmp
        
        # ────────────────────────────────────────────────────
        # HEALTH CHECKS
        # ────────────────────────────────────────────────────
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "import sys; sys.exit(0)"
          initialDelaySeconds: 30
          periodSeconds: 30
          timeoutSeconds: 5
          failureThreshold: 3
        
        readinessProbe:
          exec:
            command:
            - python
            - -c
            - "import sys; sys.exit(0)"
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
      
      # ══════════════════════════════════════════════════════
      # VOLUMES
      # ══════════════════════════════════════════════════════
      volumes:
      - name: bot-data
        persistentVolumeClaim:
          claimName: discord-bot-data
      - name: tmp
        emptyDir: {}
```

### 🎓 Explication section par section

#### Metadata

```yaml
apiVersion: apps/v1
# Deployments sont dans le groupe "apps"

kind: Deployment

metadata:
  name: discord-bot
  # Nom du Deployment
  
  namespace: lol-esports
  
  labels:
    app: discord-bot
    # Label pour identifier ce Deployment
```

#### Spec - Replicas et Selector

```yaml
spec:
  replicas: 1
  # Nombre de pods à maintenir
  # Pour Discord bot : 1 seul (limite Discord)
  
  selector:
    matchLabels:
      app: discord-bot
    # Comment le Deployment trouve ses pods ?
    # Il cherche les pods avec le label app=discord-bot
```

**📖 Pourquoi le selector ?**

Kubernetes utilise des **labels** pour lier les ressources :

```
Deployment (selector: app=discord-bot)
    │
    â–¼
ReplicaSet (labels: app=discord-bot)
    │
    â–¼
Pods (labels: app=discord-bot)
```

#### Template - Le pod

```yaml
template:
  metadata:
    labels:
      app: discord-bot
      # Labels du pod (doivent matcher le selector !)
  
  spec:
    # Configuration du pod
```

**📖 template vs spec** :

- `spec` du Deployment : Configuration du Deployment lui-même
- `template.spec` : Configuration des pods que le Deployment crée

#### Node Affinity

```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    # "preferred" = Préférence (pas obligation)
    # "required" = Obligation (doit matcher)
    
    - weight: 100
      # Poids de la préférence (1-100)
      # 100 = Forte préférence
      
      preference:
        matchExpressions:
        - key: kubernetes.io/hostname
          # Label du node
          
          operator: In
          # Opérateur de comparaison
          # In, NotIn, Exists, DoesNotExist, Gt, Lt
          
          values:
          - laptop-hostname
          # Valeur à matcher
```

**🎓 Comment ça marche ?**

1. Scheduler K8s cherche où placer le pod
2. Il voit la node affinity
3. Il **préfère** le node avec hostname = laptop-hostname
4. Mais si ce node n'est pas disponible → il place sur un autre node (EC2)

**📖 Pourquoi "preferred" et pas "required" ?**

- **required** : Si le laptop est down → pod ne démarre PAS
- **preferred** : Si le laptop est down → pod démarre sur l'EC2 ✅

**Trouver le hostname de ton laptop** :

```bash
kubectl get nodes

# Output:
# NAME              STATUS   ROLE
# laptop-thinkpad   Ready    control-plane,master
# ip-10-0-1-5       Ready    <none>
```

Remplace `laptop-hostname` par le vrai nom (ex: `laptop-thinkpad`).

#### Container - Image

```yaml
containers:
- name: discord-bot
  # Nom du container (arbitraire)
  
  image: tonusername/lol-esports-bot:v1.0.0
  # Quelle image utiliser
  # Format : [registry/][username/]image[:tag]
  
  imagePullPolicy: Always
  # Quand pull l'image ?
  # Always = À chaque fois (vérifie si nouvelle version)
  # IfNotPresent = Seulement si pas en local
  # Never = Ne jamais pull
```

**📖 imagePullPolicy** :

|Policy|Quand utiliser ?|
|---|---|
|`Always`|Images en développement (tag `latest` ou version qui change)|
|`IfNotPresent`|Images stables (tag de version figé)|
|`Never`|Images locales (debugging)|

#### Variables d'environnement

```yaml
env:
- name: DISCORD_TOKEN
  # Nom de la variable d'env
  # Accessible via os.getenv('DISCORD_TOKEN') en Python
  
  valueFrom:
    secretKeyRef:
      name: discord-bot-secret
      # Nom du Secret
      
      key: DISCORD_TOKEN
      # Clé dans le Secret

- name: MATCH_CHANNEL_ID
  valueFrom:
    secretKeyRef:
      name: discord-bot-secret
      key: MATCH_CHANNEL_ID
  # ID du channel Discord pour les notifications de matchs

- name: NEWS_CHANNEL_ID
  valueFrom:
    secretKeyRef:
      name: discord-bot-secret
      key: NEWS_CHANNEL_ID
  # ID du channel Discord pour les news Sheep Esports
```

**📖 Autres sources de variables** :

```yaml
# Valeur directe (pour données non-sensibles)
- name: LOG_LEVEL
  value: "INFO"

# Depuis un ConfigMap
- name: CONFIG_PATH
  valueFrom:
    configMapKeyRef:
      name: bot-config
      key: path

# Depuis un Secret
- name: API_KEY
  valueFrom:
    secretKeyRef:
      name: api-secrets
      key: key
```

#### Resources - CPU et RAM

```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "256Mi"
    cpu: "200m"
```

**🎓 requests vs limits** :

||Requests|Limits|
|---|---|---|
|**Signification**|Minimum garanti|Maximum autorisé|
|**Scheduling**|Utilisé par le scheduler|Non utilisé|
|**Dépassement**|N/A|Pod kill (OOM) ou throttle (CPU)|

**📖 Unités** :

**CPU** :

- `100m` = 100 millicores = 0.1 CPU
- `1` = 1 CPU complet
- `2` = 2 CPUs

**Mémoire** :

- `128Mi` = 128 Mebibytes (≈ 134 MB)
- `1Gi` = 1 Gibibyte (≈ 1.07 GB)

**📖 QoS Classes** (Quality of Service) :

Kubernetes assigne une classe selon les resources :

|Classe|Condition|Comportement si ressources insuffisantes|
|---|---|---|
|**Guaranteed**|requests = limits|Tué en dernier|
|**Burstable**|requests < limits|Tué au milieu|
|**BestEffort**|Pas de requests/limits|Tué en premier|

**Notre config** : Burstable (requests < limits)

#### Volume Mounts

```yaml
volumeMounts:
- name: bot-data
  # Nom du volume (doit matcher volumes[].name)
  
  mountPath: /app/data
  # Où monter dans le container
  # Le container voit /app/data
  
- name: tmp
  mountPath: /tmp
  # Pour le filesystem read-only
```

**📖 Options avancées** :

```yaml
volumeMounts:
- name: bot-data
  mountPath: /app/data
  readOnly: false           # false = lecture/écriture
  subPath: bot1             # Monter un sous-dossier seulement
  mountPropagation: None    # Propagation des mounts
```

#### Health Checks - Probes

**3 types de probes** :

|Probe|Quand ?|Si échec ?|
|---|---|---|
|**livenessProbe**|Le container est-il vivant ?|Redémarre le container|
|**readinessProbe**|Le container est-il prêt ?|Retire du service (pas de trafic)|
|**startupProbe**|Le container a-t-il démarré ?|Attend avant liveness|

##### Liveness Probe

```yaml
livenessProbe:
  exec:
    command:
    - python
    - -c
    - "import sys; sys.exit(0)"
    # Commande à exécuter
    # sys.exit(0) = Succès
    # sys.exit(1) = Échec
  
  initialDelaySeconds: 30
  # Attendre 30s après le démarrage avant le 1er check
  # Laisse le temps au bot de se connecter à Discord
  
  periodSeconds: 30
  # Check toutes les 30 secondes
  
  timeoutSeconds: 5
  # Timeout de la commande
  
  failureThreshold: 3
  # Si 3 checks consécutifs échouent → restart
```

**📖 Types de probes** :

```yaml
# Exec (exécute une commande)
livenessProbe:
  exec:
    command: ["python", "-c", "import sys; sys.exit(0)"]

# HTTP (requête GET)
livenessProbe:
  httpGet:
    path: /health
    port: 8080
    httpHeaders:
    - name: Custom-Header
      value: Awesome
  initialDelaySeconds: 3
  periodSeconds: 3

# TCP (connexion socket)
livenessProbe:
  tcpSocket:
    port: 8080
  initialDelaySeconds: 15
  periodSeconds: 20
```

**Notre bot** : Probe simple avec exec (vérifie que Python fonctionne)

**Amélioration future** : Vérifier la connexion Discord

##### Readiness Probe

```yaml
readinessProbe:
  exec:
    command:
    - python
    - -c
    - "import sys; sys.exit(0)"
  
  initialDelaySeconds: 10
  # Plus court que liveness (10s vs 30s)
  
  periodSeconds: 10
  
  timeoutSeconds: 5
  
  failureThreshold: 3
```

**📖 Différence liveness vs readiness** :

```
Liveness échoue → Container restart
Readiness échoue → Pod retiré du Service (pas de trafic)
                    Mais container continue de tourner
```

**Notre cas** : Pas de Service (bot Discord), donc readiness moins critique. Mais bonne pratique de l'avoir !

#### Volumes

```yaml
volumes:
- name: bot-data
  # Nom du volume (référencé dans volumeMounts)
  
  persistentVolumeClaim:
    claimName: discord-bot-data
    # Nom de la PVC créée précédemment

- name: tmp
  emptyDir: {}
  # Volume temporaire (vide au démarrage)
  # Supprimé quand le pod est supprimé
```

**📖 Types de volumes** :

```yaml
# PVC
- name: data
  persistentVolumeClaim:
    claimName: my-pvc

# emptyDir
- name: cache
  emptyDir: {}

# emptyDir (en RAM)
- name: fast-cache
  emptyDir:
    medium: Memory

# ConfigMap
- name: config
  configMap:
    name: my-config

# Secret
- name: certs
  secret:
    secretName: tls-certs

# hostPath (déconseillé)
- name: host-data
  hostPath:
    path: /data
    type: Directory
```

### Appliquer le Deployment

```bash
kubectl apply -f k8s/apps/discord-bot/deployment.yaml

# Output:
# deployment.apps/discord-bot created
```

### Vérifier le déploiement

```bash
# Voir le Deployment
kubectl get deployment discord-bot -n lol-esports

# Output:
# NAME          READY   UP-TO-DATE   AVAILABLE   AGE
# discord-bot   1/1     1            1           30s

# Voir les pods
kubectl get pods -n lol-esports

# Output:
# NAME                          READY   STATUS    RESTARTS   AGE
# discord-bot-abc123-xyz789     1/1     Running   0          30s

# Voir sur quel node
kubectl get pods -n lol-esports -o wide

# Output:
# NAME                          READY   STATUS    RESTARTS   NODE
# discord-bot-abc123-xyz789     1/1     Running   0          laptop-thinkpad
```

### Voir les logs

```bash
kubectl logs -f deployment/discord-bot -n lol-esports

# Output attendu:
# <BotUser> has connected to Discord!
# Connected to 1 guilds
```

---

## 📊 Resource Quotas

### 📖 Pourquoi des quotas ?

**Problème** : Une application mal configurée peut monopoliser tout le cluster

```
Bot mal configuré demande 10 CPU + 100 GB RAM
  ↓
Cluster n'a plus de ressources
  ↓
Autres apps ne peuvent plus démarrer ❌
```

**Solution** : Définir des limites par namespace

### Créer les Resource Quotas

**Créer** : `k8s/base/resource-quota.yaml`

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: lol-esports-quota
  namespace: lol-esports
spec:
  hard:
    requests.cpu: "2"
    requests.memory: "4Gi"
    limits.cpu: "4"
    limits.memory: "8Gi"
    persistentvolumeclaims: "5"
    pods: "10"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: lol-esports-limits
  namespace: lol-esports
spec:
  limits:
  - max:
      cpu: "1"
      memory: "1Gi"
    min:
      cpu: "50m"
      memory: "64Mi"
    default:
      cpu: "200m"
      memory: "256Mi"
    defaultRequest:
      cpu: "100m"
      memory: "128Mi"
    type: Container
```

### 🎓 ResourceQuota expliqué

```yaml
spec:
  hard:
    requests.cpu: "2"
    # Total des CPU requests dans le namespace ≤ 2
    
    requests.memory: "4Gi"
    # Total des RAM requests dans le namespace ≤ 4Gi
    
    limits.cpu: "4"
    # Total des CPU limits dans le namespace ≤ 4
    
    limits.memory: "8Gi"
    # Total des RAM limits dans le namespace ≤ 8Gi
    
    persistentvolumeclaims: "5"
    # Maximum 5 PVCs dans le namespace
    
    pods: "10"
    # Maximum 10 pods dans le namespace
```

**📖 Calcul** :

Si tu as 3 pods avec chacun :

- requests.cpu: 100m
- requests.memory: 128Mi

Total namespace :

- requests.cpu: 300m (< 2 ✅)
- requests.memory: 384Mi (< 4Gi ✅)

### 🎓 LimitRange expliqué

```yaml
spec:
  limits:
  - max:
      cpu: "1"
      memory: "1Gi"
    # Un seul container ne peut pas dépasser 1 CPU / 1Gi
    
    min:
      cpu: "50m"
      memory: "64Mi"
    # Un container doit demander au moins 50m CPU / 64Mi RAM
    
    default:
      cpu: "200m"
      memory: "256Mi"
    # Si le container ne spécifie pas de limits → utiliser ces valeurs
    
    defaultRequest:
      cpu: "100m"
      memory: "128Mi"
    # Si le container ne spécifie pas de requests → utiliser ces valeurs
    
    type: Container
    # S'applique aux containers (pas aux pods)
```

**📖 Différence ResourceQuota vs LimitRange** :

||ResourceQuota|LimitRange|
|---|---|---|
|**Scope**|Namespace entier|Par container|
|**Usage**|Limite totale|Limite individuelle|
|**Exemple**|"Max 10 pods dans le namespace"|"Max 1 CPU par container"|

### Appliquer

```bash
kubectl apply -f k8s/base/resource-quota.yaml

# Output:
# resourcequota/lol-esports-quota created
# limitrange/lol-esports-limits created
```

### Vérifier

```bash
# Voir le quota
kubectl describe resourcequota lol-esports-quota -n lol-esports

# Output:
# Name:                   lol-esports-quota
# Namespace:              lol-esports
# Resource                Used   Hard
# --------                ----   ----
# limits.cpu              200m   4
# limits.memory           256Mi  8Gi
# persistentvolumeclaims  1      5
# pods                    1      10
# requests.cpu            100m   2
# requests.memory         128Mi  4Gi

# Voir les limits
kubectl describe limitrange lol-esports-limits -n lol-esports
```

---

## ✅ Validation et tests

### Test 1 : Le pod démarre

```bash
kubectl get pods -n lol-esports

# STATUS devrait être "Running"
```

### Test 2 : Le bot est connecté à Discord

```bash
kubectl logs deployment/discord-bot -n lol-esports

# Devrait contenir :
# has connected to Discord!
```

### Test 3 : Security Context appliqué

```bash
# Entrer dans le pod
kubectl exec -it deployment/discord-bot -n lol-esports -- /bin/bash

# Vérifier l'utilisateur
whoami
# Output: botuser ✅

id
# Output: uid=1000(botuser) gid=1000(botuser) ✅

# Essayer d'installer un package (devrait échouer)
apt-get update
# Output: Permission denied ✅

# Essayer d'écrire dans / (devrait échouer)
echo "test" > /test.txt
# Output: Read-only file system ✅

# Mais on peut écrire dans /app/data et /tmp
echo "test" > /app/data/test.txt  # ✅
echo "test" > /tmp/test.txt        # ✅

exit
```

### Test 4 : Persistence du PVC

```bash
# Écrire des données
kubectl exec deployment/discord-bot -n lol-esports -- \
  sh -c "echo 'Persistence test' > /app/data/test.txt"

# Supprimer le pod (va être recréé automatiquement)
kubectl delete pod -l app=discord-bot -n lol-esports

# Attendre que le nouveau pod soit Running
kubectl wait --for=condition=ready pod -l app=discord-bot -n lol-esports --timeout=60s

# Vérifier que les données sont toujours là
kubectl exec deployment/discord-bot -n lol-esports -- cat /app/data/test.txt

# Output: Persistence test ✅
```

### Test 5 : Secrets montés

```bash
kubectl exec deployment/discord-bot -n lol-esports -- env | grep DISCORD_TOKEN

# Devrait afficher la valeur (tronquée pour sécurité)
```

### Test 6 : Resources limits

```bash
# Voir l'utilisation des ressources
kubectl top pod -n lol-esports

# Output:
# NAME                          CPU(cores)   MEMORY(bytes)
# discord-bot-abc123-xyz789     50m          120Mi

# Vérifier que c'est dans les limites (< 200m CPU, < 256Mi RAM)
```

### Test 7 : Le bot répond sur Discord

Dans Discord :

```
!ping
→ 🏓 Pong! Latency: XXms

!hello
→ Hello @toi! 👋

!info
→ [Embed avec infos]
```

---

## 🚨 Troubleshooting

### Pod en CrashLoopBackOff

```bash
# Voir les logs
kubectl logs deployment/discord-bot -n lol-esports

# Voir les events
kubectl describe pod -l app=discord-bot -n lol-esports

# Causes fréquentes :
# - Secret manquant ou invalide
# - Image incorrecte
# - Health check trop agressif
```

### Permission denied dans le pod

**Cause** : User non-root ne peut pas écrire

**Solution** : Vérifier fsGroup et permissions

```bash
kubectl exec deployment/discord-bot -n lol-esports -- ls -la /app/data

# Devrait montrer :
# drwxrwsr-x 1000 1000 /app/data
```

### PVC pending

```bash
kubectl describe pvc discord-bot-data -n lol-esports

# Chercher "Events"
# Causes possibles :
# - Pas de StorageClass disponible
# - Quota dépassé
# - Node avec espace insuffisant
```

### Pod ne démarre pas sur le bon node

```bash
kubectl get pods -n lol-esports -o wide

# Si le pod est sur l'EC2 au lieu du laptop :
# 1. Vérifier le hostname dans l'affinity
# 2. Vérifier que le laptop node est Ready
```

### Resources limits dépassés

```bash
kubectl describe resourcequota lol-esports-quota -n lol-esports

# Si "Used" >= "Hard" :
# - Réduire les resources des pods existants
# - Ou augmenter le quota
```

---

## 📝 Récapitulatif

### Ce qu'on a créé

✅ **Namespace** : lol-esports (isolation)  
✅ **SealedSecret** : Secrets chiffrés dans Git  
✅ **PVC** : 1Gi de storage persistant  
✅ **Deployment** : 1 replica avec Security Context  
✅ **ResourceQuota** : Limites CPU/RAM par namespace  
✅ **LimitRange** : Limites par container

### Architecture finale

```
lol-esports namespace
├── discord-bot-secret (SealedSecret → Secret)
├── discord-bot-data (PVC → PV)
├── discord-bot (Deployment)
│   └── Pod
│       ├── Security Context (non-root, read-only FS)
│       ├── Volume: bot-data (/app/data)
│       ├── Volume: tmp (/tmp)
│       └── Container: discord-bot (image Docker Hub)
├── lol-esports-quota (ResourceQuota)
└── lol-esports-limits (LimitRange)
```

### Fichiers créés

```
k8s/
├── base/
│   ├── namespace.yaml
│   └── resource-quota.yaml
└── apps/
    └── discord-bot/
        ├── sealed-secret.yaml  ✅ Peut être commité !
        ├── pvc.yaml
        └── deployment.yaml
```

### Commandes essentielles

```bash
# Appliquer tout
kubectl apply -f k8s/base/
kubectl apply -f k8s/apps/discord-bot/

# Vérifier
kubectl get all -n lol-esports
kubectl get pvc,secrets -n lol-esports

# Logs
kubectl logs -f deployment/discord-bot -n lol-esports

# Shell dans le pod
kubectl exec -it deployment/discord-bot -n lol-esports -- /bin/bash

# Redémarrer
kubectl rollout restart deployment/discord-bot -n lol-esports
```

---

## 🎉 Félicitations !

Tu as un déploiement Kubernetes **production-ready** avec :

- ✅ Sécurité (Security Context, non-root, read-only FS)
- ✅ Secrets sécurisés (Sealed Secrets pour GitOps)
- ✅ Persistence (PVC pour les données)
- ✅ Resource management (Quotas et Limits)
- ✅ Health checks (Liveness et Readiness probes)

**Prochaine étape** : Phase 5 - Monitoring avec Prometheus et Grafana ! 📊

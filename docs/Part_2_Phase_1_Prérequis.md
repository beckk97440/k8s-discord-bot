# Phase 1 : Prérequis et Préparation

[← Retour à l'introduction](Part_1_Introduction.md)

---

### 📖 Contexte

Avant de construire notre infrastructure Kubernetes, on doit préparer nos machines.

**Ce qu'on va faire** :

1. Configurer le laptop pour tourner 24/7 (même couvercle fermé)
2. Installer K3s sur le laptop
3. Configurer le Mac pour gérer le cluster à distance
4. Installer Tailscale (VPN) pour connecter laptop et AWS

### 1.1 Configuration du laptop pour 24/7

#### 📖 Pourquoi ?

Par défaut, quand tu fermes le couvercle d'un laptop → il se met en veille On veut que le laptop continue à tourner 24/7, couvercle fermé, dans un support vertical.

#### 🔧 Comment ?

On dit à `systemd` (le gestionnaire de système Linux) d'ignorer le couvercle.

```bash
# Éditer le fichier de configuration
sudo vim /etc/systemd/logind.conf

# Trouver et modifier ces lignes (enlever le #) :
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
HandleLidSwitchDocked=ignore

# Redémarrer le service pour appliquer
sudo systemctl restart systemd-logind
```

**🎓 Explication ligne par ligne** :

- `HandleLidSwitch=ignore` : Quand tu fermes le couvercle → ne rien faire
- `HandleLidSwitchExternalPower=ignore` : Pareil mais sur secteur
- `HandleLidSwitchDocked=ignore` : Pareil mais en station d'accueil

**✅ Validation** :

```bash
# Fermer le couvercle, attendre 10 secondes, rouvrir
# Le laptop ne devrait PAS s'être mis en veille
```

### 1.2 Installation de K3s sur le laptop

#### 📖 Pourquoi K3s ?

On veut transformer notre laptop en **cluster Kubernetes**. K3s est parfait car :

- Léger (< 512 MB RAM)
- Installation en 1 commande
- 100% compatible Kubernetes

#### 🔧 Installation

```bash
# Mettre à jour le système
sudo pacman -Syu

# Installer les outils de base
sudo pacman -S kubectl helm terraform git vim docker

# Installer K3s (version serveur = control plane + worker)
curl -sfL https://get.k3s.io | sh -
```

**🎓 Que fait cette commande ?**

`curl -sfL https://get.k3s.io | sh -` télécharge et exécute un script qui :

1. Télécharge K3s
2. L'installe comme service systemd
3. Crée un **control plane** (cerveau du cluster)
4. Crée un **worker node** (exécute les applications)
5. Configure tout automatiquement

**✅ Validation** :

```bash
# Vérifier que K3s tourne
sudo k3s kubectl get nodes

# Tu devrais voir :
# NAME              STATUS   ROLE                  AGE   VERSION
# ton-laptop-name   Ready    control-plane,master  10s   v1.28.x
```

#### 📖 C'est quoi un "node" ?

**Node** = Machine (physique ou virtuelle) qui fait partie du cluster

Dans Kubernetes, il y a 2 types de nodes :

1. **Control Plane** : Le cerveau (API, scheduler, etc.)
2. **Worker** : Les muscles (exécutent les applications)

Ton laptop est les 2 à la fois !

### 1.3 Configuration kubectl (accès non-root)

#### 📖 Pourquoi ?

Par défaut, K3s nécessite `sudo` pour tout. C'est pénible ! On va configurer kubectl pour qu'il marche sans sudo.

#### 🔧 Configuration

```bash
# Créer le dossier config
mkdir -p ~/.kube

# Copier la config K3s
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config

# Prendre ownership du fichier
sudo chown $USER:$USER ~/.kube/config

# Tester (sans sudo cette fois !)
kubectl get nodes
```

**🎓 C'est quoi ce fichier `k3s.yaml` ?**

Ce fichier contient :

- L'adresse du cluster (ex: https://127.0.0.1:6443)
- Les certificats pour s'authentifier
- Le contexte (quel cluster utiliser)

**Analogie** : C'est comme un badge d'accès à un building sécurisé.

### 1.4 Installation de Tailscale (VPN)

#### 📖 Pourquoi Tailscale ?

**Problème** : Comment faire communiquer ton laptop (chez toi) avec AWS EC2 (dans le cloud) de façon sécurisée ?

**Solutions possibles** :

1. ❌ IP publique + port forwarding : Danger, tout Internet peut accéder
2. ❌ VPN classique (OpenVPN) : Complexe à configurer
3. ✅ **Tailscale** : VPN mesh automatique, zéro config

**Tailscale = VPN moderne** :

- Chaque machine a une IP privée (ex: 100.64.1.5)
- Communication chiffrée (WireGuard)
- Gratuit pour usage perso
- Setup en 2 minutes

#### 🔧 Installation

```bash
# Installer Tailscale
sudo pacman -S tailscale

# Démarrer le service
sudo systemctl enable --now tailscaled

# S'authentifier (ouvre le navigateur)
sudo tailscale up

# Noter ton IP Tailscale
tailscale ip -4
# Exemple: 100.64.1.5 -----> 100.124.236.9 (le mien)
```

**🎓 Que fait `tailscale up` ?**

1. Ouvre ton navigateur
2. Te demande de te connecter (Google/GitHub/etc.)
3. Enregistre ta machine dans ton réseau Tailscale
4. Lui assigne une IP privée (100.64.x.x)

**✅ Validation** :

```bash
# Voir ton réseau Tailscale
tailscale status

# Tu devrais voir :
# 100.64.1.5    ton-laptop    -        online
```

**📝 Note importante** : Garde cette IP sous la main, on en aura besoin !

### 1.5 Configuration du Mac

#### 📖 Pourquoi ?

Tu veux gérer ton cluster Kubernetes depuis ton Mac (plus confortable que le laptop).

**Ce qu'on va faire** :

1. Installer les outils (kubectl, terraform, helm)
2. Copier la config K3s depuis le laptop
3. Installer Tailscale sur Mac

#### 🔧 Installation des outils

```bash
# Installer via Homebrew
brew install kubectl terraform helm
```

#### 🔧 Copier la config K3s

```bash
# Créer le dossier config
mkdir -p ~/.kube

# Copier depuis le laptop (remplace par ta vraie IP ou hostname)
scp user@laptop-ip:~/.kube/config ~/.kube/config

# Vérifier qu'on est bien connecté au laptop
kubectl get nodes
# Tu devrais voir le node de ton laptop !
```

**🎓 C'est quoi ce fichier `config` ?**

Ce fichier contient :

- L'adresse du cluster K3s (ex: https://127.0.0.1:6443)
- Les certificats pour s'authentifier
- Le contexte (quel cluster utiliser)

**Analogie** : C'est comme un badge d'accès à un building sécurisé.

**📖 Si tu as plusieurs clusters plus tard**

Tu pourras avoir plusieurs configs et switcher entre elles :

```bash
# Voir tous les contextes disponibles
kubectl config get-contexts

# Switcher entre clusters
kubectl config use-context mon-cluster-prod
kubectl config use-context mon-cluster-dev
```

#### 🔧 Installer Tailscale sur Mac

```bash
brew install tailscale
sudo tailscale up
tailscale ip -4
# Exemple: 100.64.1.20  --> 100.113.44.119 le MAC
```

**✅ Validation finale** :

```bash
# Depuis le Mac, ping le laptop via Tailscale
tailscale ping 100.64.1.5  #100.124.236.9 TPRE NAS

# Tu devrais voir :
# pong from ton-laptop (100.64.1.5) via ... in 10ms

# Vérifier qu'on peut gérer le cluster depuis le Mac
kubectl get nodes

# Tu devrais voir ton laptop node !
```

**🎉 Félicitations !** Ton Mac est configuré pour gérer le cluster K3s à distance !

---
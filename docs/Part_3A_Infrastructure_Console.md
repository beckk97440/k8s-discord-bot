# 🖱️ Phase 2-A : Infrastructure AWS - Console Web

## 📚 Introduction

Ce guide te montre comment créer **manuellement** ton infrastructure AWS via la **Console Web** (interface graphique).

**Pourquoi commencer par la Console ?**

- ✅ **Visuel** : Tu vois tous les champs, options, configurations
- ✅ **Pédagogique** : Tu comprends ce que chaque ressource fait
- ✅ **Intuitive** : Clics et formulaires, pas de syntaxe à apprendre

**⚠️ Important** :

- Méthode pour **apprendre** AWS
- **Pas recommandé pour production** (pas reproductible, pas versionné)
- Après ce guide, passe à **Phase 2-C (Terraform)** pour automatiser

---

## 🎯 Ce qu'on va créer

```
Infrastructure AWS (Région eu-west-3 - Paris)
├─ VPC (10.0.0.0/16)
├─ Subnet (10.0.1.0/24)
├─ Internet Gateway
├─ Route Table (avec route vers Internet)
├─ Security Group (SSH, Tailscale, K3s)
├─ EC2 Instance (t3.micro, Ubuntu 22.04)
├─ IAM Role (pour Lambda)
├─ Lambda Function (watchdog Python)
└─ EventBridge Rule (trigger toutes les 5 min)
```

**Temps total** : ~30-45 minutes

**Coût** : ~€0.10/mois (EC2 éteint 99% du temps)

---

## ✅ Prérequis

### Compte AWS

Tu as besoin d'un compte AWS : https://aws.amazon.com/free/

**Configuration recommandée** :

- ✅ Activer MFA (Multi-Factor Authentication)
- ✅ Configurer Billing Alerts (alertes si dépenses > $5)
- ✅ Utiliser eu-west-3 (Paris) comme région

### Se connecter

1. Aller sur https://console.aws.amazon.com
2. Se connecter avec tes credentials
3. **Vérifier la région en haut à droite** : `Paris (eu-west-3)` ✅

**⚠️ IMPORTANT** : Toutes les ressources doivent être dans **la même région** !

---

## Section 1 : VPC - Virtual Private Cloud

### 🎓 Concept

**VPC** = Ton réseau privé dans AWS

**Analogie** : Un VPC c'est comme avoir ton propre bâtiment dans une grande ville (AWS).

- Tu choisis la taille (CIDR)
- Tu crées des étages (Subnets)
- Tu décides qui peut entrer (Security Groups)

**Ce qu'on crée** :

- CIDR : `10.0.0.0/16` (65,536 adresses IP)
- Nom : `k8s-hybrid-vpc`

### 📝 Étapes détaillées

**1. Aller dans VPC**

- Dans la barre de recherche AWS (en haut) : Taper "**VPC**"
- Cliquer sur "**VPC**" (service)

**2. Créer le VPC**

- Cliquer sur le bouton orange "**Create VPC**"

**3. Remplir le formulaire**

```
┌────────────────────────────────────────────┐
│ Resources to create                        │
│ ● VPC only          ← Sélectionner         │
│ ○ VPC and more                             │
└────────────────────────────────────────────┘
```

**Pourquoi "VPC only" ?**

- "VPC and more" crée automatiquement Subnets + IGW (trop magique)
- On veut tout créer manuellement pour comprendre

```
┌────────────────────────────────────────────┐
│ Name tag - optional                        │
│ k8s-hybrid-vpc      ← Entrer ce nom        │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ IPv4 CIDR block                            │
│ ● IPv4 CIDR manual input                   │
│ 10.0.0.0/16         ← Entrer ce CIDR       │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ IPv6 CIDR block                            │
│ ● No IPv6 CIDR block   ← Laisser comme ça  │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Tenancy                                    │
│ ● Default          ← Laisser Default       │
└────────────────────────────────────────────┘
```

**📖 CIDR `10.0.0.0/16` signifie** :

- Plage : 10.0.0.0 → 10.0.255.255
- Total : 65,536 adresses IP
- `10.x.x.x` = Plage privée (RFC 1918)

**4. Créer**

- Scroller en bas
- Cliquer "**Create VPC**"

**5. Résultat**

```
✓ Successfully created VPC vpc-0123456789abcdef
```

**⚠️ IMPORTANT : Noter le VPC ID** quelque part !

Exemple : `vpc-0123456789abcdef`

### ✅ Vérification

Dans la liste des VPCs :

- ✅ State : `Available`
- ✅ Name : `k8s-hybrid-vpc`
- ✅ IPv4 CIDR : `10.0.0.0/16`

**Temps** : ~2 minutes

---

## Section 2 : Subnet

### 🎓 Concept

**Subnet** = Sous-réseau = Subdivision du VPC

**Analogie** : Si le VPC est un bâtiment, le Subnet est un étage.

**Types** :

- **Public Subnet** : Accessible depuis Internet (avec Internet Gateway)
- **Private Subnet** : Isolé d'Internet

**Notre subnet** : Public (pour SSH sur EC2)

**Ce qu'on crée** :

- CIDR : `10.0.1.0/24` (256 IPs)
- Availability Zone : `eu-west-3a`
- Nom : `k8s-hybrid-subnet-public`

### 📝 Étapes

**1. Aller dans Subnets**

- Console VPC
- Menu gauche : "**Subnets**"

**2. Créer le Subnet**

- Cliquer "**Create subnet**"

**3. Remplir**

```
┌────────────────────────────────────────────┐
│ VPC ID                                     │
│ [Sélectionner] k8s-hybrid-vpc              │
│ vpc-0123456789abcdef                       │
└────────────────────────────────────────────┘
```

**💡 Astuce** : Tu peux chercher par nom "k8s-hybrid-vpc" dans le dropdown.

```
┌────────────────────────────────────────────┐
│ Subnet name                                │
│ k8s-hybrid-subnet-public                   │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Availability Zone                          │
│ [Sélectionner] eu-west-3a                  │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ IPv4 subnet CIDR block                     │
│ 10.0.1.0/24                                │
└────────────────────────────────────────────┘
```

**📖 Availability Zone** :

- AWS a plusieurs datacenters par région (a, b, c)
- On choisit `eu-west-3a` (arbitraire)

**📖 CIDR `10.0.1.0/24`** :

- Sous-ensemble de `10.0.0.0/16` (VPC)
- 256 IPs (10.0.1.0 → 10.0.1.255)
- AWS réserve 5 IPs → 251 utilisables

**4. Créer**

- Cliquer "**Create subnet**"

```
✓ Successfully created subnet subnet-0123456789abcdef
```

**⚠️ Noter le Subnet ID**

### Rendre le Subnet public

Par défaut le subnet est **privé**. Pour le rendre public :

**1. Activer Auto-assign Public IP**

- Sélectionner le subnet (checkbox)
- Menu "**Actions**" → "**Edit subnet settings**"
- ✅ Cocher "**Enable auto-assign public IPv4 address**"
- Cliquer "**Save**"

**Pourquoi ?** Les instances EC2 dans ce subnet recevront une IP publique automatiquement (nécessaire pour SSH).

### ✅ Vérification

- ✅ State : `Available`
- ✅ Available IPs : `251`
- ✅ VPC : `k8s-hybrid-vpc`
- ✅ Auto-assign public IPv4 : `Yes`

**Temps** : ~2 minutes

---

## Section 3 : Internet Gateway

### 🎓 Concept

**Internet Gateway (IGW)** = Porte d'entrée du VPC vers Internet

**Analogie** : La porte principale du bâtiment.

- Sans IGW → Bâtiment fermé
- Avec IGW → Connexion à Internet

**Pourquoi on en a besoin ?**

- SSH sur EC2 depuis Internet
- EC2 peut télécharger des packages (`apt update`)
- Tailscale peut se connecter

**Ce qu'on crée** :

- Un Internet Gateway
- Attaché au VPC

### 📝 Étapes

**1. Aller dans Internet Gateways**

- Console VPC
- Menu gauche : "**Internet gateways**"

**2. Créer l'IGW**

- Cliquer "**Create internet gateway**"

**3. Remplir**

```
┌────────────────────────────────────────────┐
│ Name tag                                   │
│ k8s-hybrid-igw                             │
└────────────────────────────────────────────┘
```

- Cliquer "**Create internet gateway**"

```
✓ Successfully created internet gateway igw-0123456789abcdef
```

**⚠️ Noter l'IGW ID**

### Attacher au VPC

**⚠️ IMPORTANT** : L'IGW est créé mais **PAS encore attaché** au VPC !

**1. Attacher**

Tu es déjà sur la page de l'IGW créé :

- En haut, un banner jaune dit : "Gateway is detached"
- Cliquer "**Actions**" → "**Attach to VPC**"

**2. Sélectionner le VPC**

```
┌────────────────────────────────────────────┐
│ Available VPCs                             │
│ [Sélectionner] k8s-hybrid-vpc              │
│ vpc-0123456789abcdef                       │
└────────────────────────────────────────────┘
```

- Cliquer "**Attach internet gateway**"

```
✓ Successfully attached igw-0123456789abcdef to vpc-0123456789abcdef
```

### ✅ Vérification

- ✅ State : `Attached`
- ✅ VPC ID : `vpc-0123456789abcdef` (ton VPC)

**Temps** : ~1 minute

---

## Section 4 : Route Table

### 🎓 Concept

**Route Table** = Table de routage = GPS du réseau

**Analogie** : Panneau de direction :

- "Pour Internet → Passer par l'Internet Gateway"
- "Pour le VPC → Rester local"

**Ce qu'on va faire** :

- Utiliser la Route Table créée automatiquement avec le VPC
- Ajouter une route vers Internet (0.0.0.0/0 → IGW)

### 📝 Étapes

**1. Aller dans Route Tables**

- Console VPC
- Menu gauche : "**Route tables**"

**2. Identifier la Route Table du VPC**

Dans la liste :

- Chercher la route table avec VPC = `k8s-hybrid-vpc`
- Colonne "Main" = `Yes`

**3. Renommer (optionnel mais recommandé)**

- Sélectionner la route table
- Cliquer sur le nom vide (ou icône crayon)
- Entrer : `k8s-hybrid-rt-public`
- Save (icône check)

**4. Ajouter la route vers Internet**

- Onglet "**Routes**" (en bas de l'écran)
- Cliquer "**Edit routes**"
- Cliquer "**Add route**"

```
┌────────────────────────────────────────────┐
│ Destination          Target                │
├────────────────────────────────────────────┤
│ 10.0.0.0/16          local   (déjà là ✅)  │
│                                            │
│ 0.0.0.0/0            [Cliquer dropdown]    │
│                      → Internet Gateway    │
│                      → igw-xxx (sélect.)   │
└────────────────────────────────────────────┘
```

**Explication** :

- `10.0.0.0/16 → local` : Trafic dans le VPC reste local (déjà créé)
    
- `0.0.0.0/0 → igw-xxx` : Tout le reste va vers Internet (on ajoute)
    
- Cliquer "**Save changes**"
    

**5. Associer le Subnet**

Par défaut, le subnet utilise la "Main" route table. On va l'associer explicitement.

- Onglet "**Subnet associations**"
- Section "Explicit subnet associations"
- Cliquer "**Edit subnet associations**"
- ✅ Cocher `k8s-hybrid-subnet-public`
- Cliquer "**Save associations**"

### ✅ Vérification

**Onglet Routes** :

- ✅ 2 routes :
    - `10.0.0.0/16 → local`
    - `0.0.0.0/0 → igw-xxx`

**Onglet Subnet associations** :

- ✅ 1 subnet : `k8s-hybrid-subnet-public`

**Temps** : ~2 minutes

---

## Section 5 : Security Group

### 🎓 Concept

**Security Group** = Firewall virtuel pour EC2

**Analogie** : Videur à l'entrée d'une boîte de nuit :

- Règles **Inbound** : Qui peut entrer
- Règles **Outbound** : Qui peut sortir

**Ce qu'on va créer** :

**Inbound** (trafic vers EC2) :

1. SSH (port 22) depuis partout
2. Tailscale (port UDP 41641) depuis partout
3. K3s API (port 6443) depuis le VPC

**Outbound** (trafic depuis EC2) :

- Tout autorisé (EC2 peut aller partout)

### 📝 Étapes

**1. Aller dans Security Groups**

- Console AWS → **EC2** (pas VPC !)
- Menu gauche : "**Security Groups**"

**2. Créer le Security Group**

- Cliquer "**Create security group**"

**3. Basic details**

```
┌────────────────────────────────────────────┐
│ Security group name                        │
│ k8s-hybrid-worker-sg                       │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Description                                │
│ Security group for K8s worker node        │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ VPC                                        │
│ [Sélectionner] k8s-hybrid-vpc              │
│ vpc-0123456789abcdef                       │
└────────────────────────────────────────────┘
```

**4. Inbound rules**

Cliquer "**Add rule**" pour chaque règle :

**Règle 1 : SSH**

```
Type: SSH
Protocol: TCP
Port range: 22
Source: 0.0.0.0/0
Description: SSH from anywhere
```

**Règle 2 : Tailscale**

```
Type: Custom UDP
Protocol: UDP
Port range: 41641
Source: 0.0.0.0/0
Description: Tailscale VPN
```

**Règle 3 : K3s API**

```
Type: Custom TCP
Protocol: TCP
Port range: 6443
Source: 10.0.0.0/16
Description: K3s API from VPC
```

**📖 Pourquoi ces ports ?**

- **22** : SSH standard
- **41641** : Port Tailscale par défaut
- **6443** : API Kubernetes (K3s)

**5. Outbound rules**

AWS crée automatiquement une règle :

```
Type: All traffic
Protocol: All
Port range: All
Destination: 0.0.0.0/0
```

**✅ Laisser comme ça** (l'EC2 peut tout faire sortir)

**6. Créer**

- Scroller en bas
- Cliquer "**Create security group**"

```
✓ Successfully created security group sg-0123456789abcdef
```

**⚠️ Noter le Security Group ID**

### ✅ Vérification

- ✅ 3 règles inbound
- ✅ 1 règle outbound
- ✅ VPC : `k8s-hybrid-vpc`

**Temps** : ~3 minutes

---

## Section 6 : EC2 Instance

### 🎓 Concept

**EC2** = Serveur virtuel dans le cloud

**Ce qu'on va créer** :

- OS : Ubuntu 22.04
- Type : t3.micro (1 vCPU, 1 GB RAM)
- Storage : 8 GB SSD
- Nom : `k8s-hybrid-worker`

**💰 Coût** : ~€1.20/mois (éteint 95% du temps)

### 📝 Étape 1 : Créer une Key Pair (clé SSH)

**Qu'est-ce qu'une Key Pair ?**

Paire de clés pour SSH :

- **Private key** : Sur ton laptop (secret)
- **Public key** : Sur EC2
- Permet SSH sans mot de passe

**Créer la Key Pair** :

1. Console EC2
2. Menu gauche : "**Key Pairs**"
3. Cliquer "**Create key pair**"

```
┌────────────────────────────────────────────┐
│ Name                                       │
│ k8s-hybrid-key                             │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Key pair type                              │
│ ● RSA                                      │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Private key file format                    │
│ ● .pem                                     │
└────────────────────────────────────────────┘
```

4. Cliquer "**Create key pair**"

**Fichier téléchargé** : `k8s-hybrid-key.pem`

**⚠️ Sauvegarder la clé** :

```bash
# Sur Mac ou Arch Linux
mv ~/Downloads/k8s-hybrid-key.pem ~/.ssh/
chmod 400 ~/.ssh/k8s-hybrid-key.pem
```

**Pourquoi chmod 400 ?** SSH refuse si la clé est accessible par d'autres utilisateurs.

### 📝 Étape 2 : Lancer l'instance EC2

**1. Launch instance**

- Console EC2
- Cliquer "**Launch instances**" (gros bouton orange)

**2. Name and tags**

```
┌────────────────────────────────────────────┐
│ Name                                       │
│ k8s-hybrid-worker                          │
└────────────────────────────────────────────┘
```

**3. Application and OS Images (AMI)**

- **Quick Start** : Ubuntu
- **Amazon Machine Image** : Ubuntu Server 22.04 LTS (HVM), SSD Volume Type
- **Architecture** : 64-bit (x86)

**4. Instance type**

```
┌────────────────────────────────────────────┐
│ Instance type                              │
│ [Sélectionner] t3.micro                    │
│                                            │
│ • 2 vCPUs                                  │
│ • 1 GiB Memory                             │
│ • $0.0104/hour                             │
└────────────────────────────────────────────┘
```

**5. Key pair**

```
┌────────────────────────────────────────────┐
│ Key pair (login)                           │
│ [Sélectionner] k8s-hybrid-key              │
└────────────────────────────────────────────┘
```

**6. Network settings**

Cliquer "**Edit**" :

```
┌────────────────────────────────────────────┐
│ VPC                                        │
│ [Sélectionner] k8s-hybrid-vpc              │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Subnet                                     │
│ [Sélectionner] k8s-hybrid-subnet-public    │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Auto-assign public IP                      │
│ ● Enable                                   │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Firewall (security groups)                 │
│ ● Select existing security group           │
│                                            │
│ [Sélectionner] k8s-hybrid-worker-sg        │
└────────────────────────────────────────────┘
```

**7. Configure storage**

Laisser par défaut :

```
Volume 1 (Root):
  Size: 8 GiB
  Volume type: gp3
```

**8. Advanced details (optionnel)**

Tu peux ajouter un script de démarrage automatique :

Scroller jusqu'à "**User data**" et coller :

```bash
#!/bin/bash
apt-get update
apt-get upgrade -y
apt-get install -y curl wget vim htop
hostnamectl set-hostname k8s-worker-aws
```

**Ce script s'exécutera au premier boot.**

**9. Summary**

Vérifier dans la colonne de droite :

- Instance type : t3.micro ✅
- VPC : k8s-hybrid-vpc ✅
- Subnet : k8s-hybrid-subnet-public ✅
- Security group : k8s-hybrid-worker-sg ✅
- Key pair : k8s-hybrid-key ✅

**10. Launch**

- Cliquer "**Launch instance**"

```
✓ Successfully initiated launch of instance i-0123456789abcdef
```

**⚠️ Noter l'Instance ID**

### 📝 Étape 3 : Vérifier l'instance

1. Cliquer "**View all instances**"
2. Attendre que :
    - **Instance state** : `Running` (~30 sec)
    - **Status checks** : `2/2 checks passed` (~2 min)

**Noter les IPs** :

- **Public IPv4 address** : `3.250.123.45` (exemple)
- **Private IPv4 address** : `10.0.1.10`

### 📝 Étape 4 : Se connecter en SSH

```bash
ssh -i ~/.ssh/k8s-hybrid-key.pem ubuntu@3.250.123.45
```

**⚠️ Remplace par ta vraie IP publique !**

**Première connexion** :

```
Are you sure you want to continue connecting (yes/no)? yes
```

**✅ Connecté** :

```
ubuntu@k8s-worker-aws:~$ 
```

**Tester** :

```bash
# OS
lsb_release -a
# Ubuntu 22.04 ✅

# RAM
free -h
# 981Mi ✅

# Hostname
hostname
# k8s-worker-aws ✅

# Internet
ping -c 2 google.com
# 64 bytes from google.com ✅
```

**Déconnecter** :

```bash
exit
```

### ✅ Vérification

- ✅ Instance Running
- ✅ 2/2 checks passed
- ✅ SSH fonctionne
- ✅ Internet accessible

**Temps** : ~5 minutes

---

## Section 7 : IAM Role pour Lambda

### 🎓 Concept

**IAM** = Identity and Access Management

**IAM Role** = Ensemble de permissions

- Notre Lambda aura besoin de :
    - Démarrer/arrêter l'EC2
    - Écrire des logs CloudWatch

**Ce qu'on va créer** :

- Role : `lambda-watchdog-role`
- Permissions : EC2 (start/stop) + CloudWatch Logs

### 📝 Étapes

**1. Aller dans IAM**

- Console AWS → IAM
- Menu gauche : "**Roles**"

**2. Créer le Role**

- Cliquer "**Create role**"

**3. Select trusted entity**

```
┌────────────────────────────────────────────┐
│ Trusted entity type                        │
│ ● AWS service                              │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Use case                                   │
│ [Sélectionner] Lambda                      │
└────────────────────────────────────────────┘
```

**Pourquoi Lambda ?** Le role sera utilisé par une fonction Lambda.

- Cliquer "**Next**"

**4. Add permissions**

Dans la barre de recherche, chercher et sélectionner :

✅ **AmazonEC2FullAccess** (pour start/stop EC2) ✅ **CloudWatchLogsFullAccess** (pour les logs)

**⚠️ En production** : Créer des policies custom avec permissions minimales (principe du moindre privilège).

- Cliquer "**Next**"

**5. Name, review, and create**

```
┌────────────────────────────────────────────┐
│ Role name                                  │
│ lambda-watchdog-role                       │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Description                                │
│ Role for Lambda watchdog function         │
└────────────────────────────────────────────┘
```

- Cliquer "**Create role**"

```
✓ Role lambda-watchdog-role created
```

### ✅ Vérification

- ✅ Role créé
- ✅ 2 policies attachées (EC2 + CloudWatch)

**Temps** : ~2 minutes

---

## Section 8 : Lambda Function

### 🎓 Concept

**Lambda** = Fonction serverless (code qui tourne sans serveur)

**Notre Lambda** :

- Check si le laptop est UP
- Si DOWN → Démarre l'EC2
- Si UP → Arrête l'EC2

**Code** : Python (~300 lignes, on va l'uploader)

### 📝 Étape 1 : Préparer le code Python

**Sur ton Mac ou laptop, créer le fichier** :

```bash
mkdir -p ~/lambda-watchdog
cd ~/lambda-watchdog
vim handler.py
```

**Coller ce code** :

```python
import os
import boto3
import json
import requests

# Variables d'environnement
WORKER_INSTANCE_ID = os.environ['WORKER_INSTANCE_ID']
HEALTHCHECK_URL = os.environ['HEALTHCHECK_URL']

# Clients AWS
ec2_client = boto3.client('ec2')

def check_laptop_health():
    """Vérifie si le laptop est accessible via healthcheck HTTPS"""
    try:
        response = requests.get(HEALTHCHECK_URL, timeout=10, verify=True)
        return response.status_code == 200
    except Exception as e:
        print(f"Error checking laptop: {e}")
        return False

def get_ec2_state():
    """Récupère l'état de l'instance EC2"""
    response = ec2_client.describe_instances(InstanceIds=[WORKER_INSTANCE_ID])
    state = response['Reservations'][0]['Instances'][0]['State']['Name']
    return state

def start_ec2():
    """Démarre l'instance EC2"""
    print(f"Starting EC2 instance {WORKER_INSTANCE_ID}")
    ec2_client.start_instances(InstanceIds=[WORKER_INSTANCE_ID])

def stop_ec2():
    """Arrête l'instance EC2"""
    print(f"Stopping EC2 instance {WORKER_INSTANCE_ID}")
    ec2_client.stop_instances(InstanceIds=[WORKER_INSTANCE_ID])

def lambda_handler(event, context):
    """Fonction principale Lambda"""
    
    # Check laptop health
    laptop_up = check_laptop_health()
    print(f"Laptop status: {'UP' if laptop_up else 'DOWN'}")
    
    # Check EC2 state
    ec2_state = get_ec2_state()
    print(f"EC2 state: {ec2_state}")
    
    # Logique de décision
    if laptop_up and ec2_state == 'running':
        # Laptop OK + EC2 running → Arrêter EC2 (pas besoin)
        stop_ec2()
        action = "Stopped EC2 (laptop is back up)"
    elif not laptop_up and ec2_state == 'stopped':
        # Laptop DOWN + EC2 stopped → Démarrer EC2 (failover)
        start_ec2()
        action = "Started EC2 (laptop is down)"
    elif laptop_up and ec2_state == 'stopped':
        # Laptop OK + EC2 stopped → Rien (état normal)
        action = "None (normal state)"
    elif not laptop_up and ec2_state == 'running':
        # Laptop DOWN + EC2 running → Rien (failover déjà actif)
        action = "None (failover active)"
    else:
        # État transitoire (pending, stopping, etc.)
        action = f"None (EC2 in transitional state: {ec2_state})"
    
    print(f"Action: {action}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'laptop_up': laptop_up,
            'ec2_state': ec2_state,
            'action': action
        })
    }
```

**Sauvegarder et quitter** (`:wq`)

**Créer le ZIP** :

```bash
cd ~/lambda-watchdog
zip function.zip handler.py
```

**Fichier créé** : `function.zip` (~2 KB)

### 📝 Étape 2 : Créer la fonction Lambda

**1. Aller dans Lambda**

- Console AWS → Lambda
- Cliquer "**Create function**"

**2. Basic information**

```
┌────────────────────────────────────────────┐
│ Function option                            │
│ ● Author from scratch                      │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Function name                              │
│ k8s-watchdog                               │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Runtime                                    │
│ [Sélectionner] Python 3.11                 │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Architecture                               │
│ ● x86_64                                   │
└────────────────────────────────────────────┘
```

**3. Permissions**

- Expand "**Change default execution role**"
- ● Use an existing role
- [Sélectionner] `lambda-watchdog-role`

**4. Créer**

- Cliquer "**Create function**"

```
✓ Successfully created function k8s-watchdog
```

### 📝 Étape 3 : Uploader le code

**1. Upload le ZIP**

Tu es sur la page de la fonction :

- Section "**Code source**"
- Cliquer "**Upload from**" → ".zip file"
- Cliquer "**Upload**"
- Sélectionner `function.zip`
- Cliquer "**Save**"

**2. Vérifier**

Dans l'éditeur de code, tu devrais voir `handler.py` avec le code Python.

### 📝 Étape 4 : Configurer les variables d'environnement

**1. Aller dans Configuration**

- Onglet "**Configuration**"
- Menu gauche : "**Environment variables**"
- Cliquer "**Edit**"

**2. Ajouter les variables**

Cliquer "**Add environment variable**" :

```
Key: WORKER_INSTANCE_ID
Value: i-0123456789abcdef   ← Ton Instance ID EC2
```

```
Key: HEALTHCHECK_URL
Value: https://laptop.ts.net/health   ← URL healthcheck Tailscale Funnel
```

**⚠️ Pour l'instant, mets une URL factice** (ex: `https://laptop.ts.net/health`)

Tu la changeras quand tu auras configuré Tailscale Funnel (Phase 7 - Lambda).

- Cliquer "**Save**"

### 📝 Étape 5 : Augmenter le timeout

Par défaut : 3 secondes (trop court).

**1. Configuration → General configuration**

- Cliquer "**Edit**"

**2. Timeout**

```
┌────────────────────────────────────────────┐
│ Timeout                                    │
│ 1 min 0 sec                                │
└────────────────────────────────────────────┘
```

- Cliquer "**Save**"

### 📝 Étape 6 : Tester la fonction

**1. Test**

- Onglet "**Test**"
- Event name : `test-event`
- Event JSON : (laisser par défaut `{}`)
- Cliquer "**Test**"

**2. Résultat**

```
✓ Execution result: succeeded

Response:
{
  "statusCode": 200,
  "body": "{\"laptop_up\": false, \"ec2_state\": \"stopped\", \"action\": \"Started EC2\"}"
}

Logs:
Laptop status: DOWN
EC2 state: stopped
Starting EC2 instance i-xxx
Action: Started EC2 (laptop is down)
```

**💡 C'est normal que laptop soit DOWN** (tu n'as pas encore Tailscale)

**Vérifie que** :

- ✅ Pas d'erreur
- ✅ Les logs s'affichent
- ✅ L'EC2 démarre (optionnel : vérifier dans EC2 console)

### ✅ Vérification

- ✅ Fonction créée
- ✅ Code uploadé
- ✅ Variables d'environnement configurées
- ✅ Test réussit (même si laptop DOWN)

**Temps** : ~5 minutes

---

## Section 9 : EventBridge Rule

### 🎓 Concept

**EventBridge** = Scheduler (lance des tâches à intervalles réguliers)

**Notre rule** :

- Toutes les 5 minutes
- Trigger la Lambda watchdog

### 📝 Étapes

**1. Aller dans EventBridge**

- Console AWS → EventBridge
- Menu gauche : "**Rules**"
- Cliquer "**Create rule**"

**2. Define rule detail**

```
┌────────────────────────────────────────────┐
│ Name                                       │
│ k8s-watchdog-trigger                       │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Description (optional)                     │
│ Trigger watchdog every 5 minutes          │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Event bus                                  │
│ ● default                                  │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Rule type                                  │
│ ● Schedule                                 │
└────────────────────────────────────────────┘
```

- Cliquer "**Next**"

**3. Define schedule**

```
┌────────────────────────────────────────────┐
│ Schedule pattern                           │
│ ● A schedule that runs at a regular rate   │
│   such as every 10 minutes                 │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Rate expression                            │
│ Value: 5                                   │
│ Unit: [Sélectionner] Minutes               │
└────────────────────────────────────────────┘
```

**💡 Rate expression** : `rate(5 minutes)` = Toutes les 5 minutes

- Cliquer "**Next**"

**4. Select target(s)**

```
┌────────────────────────────────────────────┐
│ Target types                               │
│ ● AWS service                              │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Select a target                            │
│ [Dropdown] Lambda function                 │
└────────────────────────────────────────────┘

┌────────────────────────────────────────────┐
│ Function                                   │
│ [Sélectionner] k8s-watchdog                │
└────────────────────────────────────────────┘
```

- Scroller en bas
- Cliquer "**Next**"

**5. Configure tags (optional)**

- Skip
- Cliquer "**Next**"

**6. Review and create**

- Vérifier :
    
    - Rule name : k8s-watchdog-trigger ✅
    - Schedule : rate(5 minutes) ✅
    - Target : k8s-watchdog (Lambda) ✅
- Cliquer "**Create rule**"
    

```
✓ Successfully created rule k8s-watchdog-trigger
```

### ✅ Vérification

**1. La rule est active**

- Status : `Enabled` ✅

**2. La Lambda est trigger automatiquement**

Attendre 5 minutes, puis :

- Aller dans Lambda → k8s-watchdog
- Onglet "**Monitor**"
- Cliquer "**View CloudWatch logs**"

Tu devrais voir des logs toutes les 5 minutes ! ✅

**Temps** : ~2 minutes

---

## 🎉 Récapitulatif : Tu as créé

✅ **VPC** (`10.0.0.0/16`) ✅ **Subnet** (`10.0.1.0/24`, public) ✅ **Internet Gateway** (attaché au VPC) ✅ **Route Table** (avec route vers Internet) ✅ **Security Group** (SSH, Tailscale, K3s) ✅ **EC2 Instance** (t3.micro, Ubuntu 22.04) ✅ **IAM Role** (permissions EC2 + CloudWatch) ✅ **Lambda Function** (watchdog Python) ✅ **EventBridge Rule** (trigger toutes les 5 min)

**Infrastructure complète créée ! 🚀**

---

## 🧹 Nettoyage (si tu veux tout supprimer)

**⚠️ Dans l'ordre inverse de création !**

1. **EventBridge** : Delete rule `k8s-watchdog-trigger`
2. **Lambda** : Delete function `k8s-watchdog`
3. **IAM** : Delete role `lambda-watchdog-role`
4. **EC2** : Terminate instance `k8s-hybrid-worker`
5. **Security Group** : Delete `k8s-hybrid-worker-sg`
6. **Route Table** : Dissociate subnet, delete routes (sauf local)
7. **Internet Gateway** : Detach from VPC, delete `k8s-hybrid-igw`
8. **Subnet** : Delete `k8s-hybrid-subnet-public`
9. **VPC** : Delete `k8s-hybrid-vpc`

**Temps** : ~5 minutes

---

## ➡️ Prochaine étape

Maintenant que tu comprends comment créer manuellement, passe à :

**Phase 2-C : Terraform** (automatiser tout ça en 1 commande !)

**Avantages** :

- ✅ Reproductible
- ✅ Versionné dans Git
- ✅ `terraform destroy` pour tout nettoyer en 1 commande
- ✅ Industry standard

**Temps de création avec Terraform** : ~3 minutes (vs 45 minutes manuellement)

---

## 📊 Comparaison Console vs Terraform

|Aspect|Console Web|Terraform|
|---|---|---|
|**Temps initial**|45 min|3 min|
|**Reproductible**|❌ Non|✅ Oui|
|**Versionné**|❌ Non|✅ Oui (Git)|
|**Collaboration**|❌ Difficile|✅ Facile|
|**Documentation**|❌ Externe|✅ Code = doc|
|**Modifications**|Re-cliquer tout|Modifier code → apply|
|**Suppression**|9 étapes manuelles|`terraform destroy`|
|**Apprendre AWS**|✅✅✅ Excellent|✅ Bon|
|**Production**|❌ Non recommandé|✅✅✅ Standard|

**Conclusion** : Console pour apprendre, Terraform pour déployer ! 🎯
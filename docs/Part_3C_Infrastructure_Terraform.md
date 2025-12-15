# Phase 3-C : Infrastructure AWS avec Terraform (Production)

<- Phase 2-B (AWS CLI) | Phase 3 (Docker) ->

---

## Introduction

Ce guide te montre comment créer ton infrastructure AWS avec **Terraform** (Infrastructure as Code).

**Pourquoi Terraform ?**

- [OK] **Industry Standard** : Utilisé par 95% des entreprises en production
- [OK] **Reproductible** : Crée/détruit/recrée en 1 commande
- [OK] **Versionné** : Code dans Git, historique complet
- [OK] **Plan Preview** : `terraform plan` montre ce qui va changer AVANT
- [OK] **Collaboratif** : Équipe peut travailler sur le même code
- [OK] **State Management** : Terraform sait ce qui existe déjà

**[!] Important** :

- Méthode **recommandée pour production**
- Les concepts AWS sont expliqués dans **Phase 2-A (Console Web)**
- Cette version automatise tout avec Tailscale + K3s inclus

---

## Ce qu'on va créer

```
Infrastructure AWS (Région eu-west-3 - Paris)
|-- VPC (10.0.0.0/16)
|-- Subnet Public (10.0.1.0/24)
|-- Internet Gateway
|-- Route Table
|-- Security Group (SSH + Tailscale + K3s + HTTPS)
|-- EC2 Instance (t3.micro, Ubuntu 22.04)
|   |-- Tailscale installé automatiquement
|   |-- K3s server standalone (pas d'agent, control plane indépendant)
|   `-- ArgoCD pour redéploiement automatique
|-- IAM Role (pour Lambda)
|-- Lambda Function (watchdog healthcheck HTTPS)
`-- EventBridge Rule (trigger toutes les 5 min)
```

**Temps total** : ~5 minutes (après configuration initiale)

**Commandes principales** :

```bash
terraform init      # Initialiser (1 fois)
terraform plan      # Voir les changements
terraform apply     # Créer l'infrastructure
terraform destroy   # Tout supprimer
```

---

## Prérequis

### 1. Installer Terraform

**Sur Mac** :

```bash
brew install terraform
```

**Sur Arch Linux** :

```bash
sudo pacman -S terraform
```

**Vérifier** :

```bash
terraform --version
# Terraform v1.6.x ou plus
```

### 2. AWS CLI configuré

```bash
# Doit être déjà fait (voir Phase 2-B)
aws configure

# Tester la connexion
aws sts get-caller-identity
# Doit afficher ton User ID
```

### 3. Clé SSH existante

```bash
# Vérifier si tu as une clé SSH
ls -la ~/.ssh/id_rsa.pub

# Si elle n'existe pas, en créer une :
ssh-keygen -t rsa -b 4096 -C "ton-email@example.com"
# Appuie sur Enter pour accepter les valeurs par défaut
```

### 4. Informations requises

Tu auras besoin de ces informations (on les récupérera étape par étape) :

- [ ] URL Healthcheck Tailscale Funnel du laptop (ex: `https://laptop-name.tailxxx.ts.net/health`)
- [ ] Clé d'auth Tailscale (ex: `tskey-auth-xxx`)

**Note** : Plus besoin du token K3s car l'EC2 a son propre cluster standalone !

**Ne t'inquiète pas, on va les récupérer ensemble plus tard !**

---

## Structure du projet

Voici la structure **DÉFINITIVE** de ton projet :

```
~/k8s-discord-bot-portfolio/
|
|-- infrastructure/              # INFRASTRUCTURE AS CODE
|   |-- main.tf                  # Config Terraform + Provider AWS
|   |-- variables.tf             # Variables (project_name, region, etc.)
|   |-- vpc.tf                   # VPC + Subnet + IGW + Route Table
|   |-- security-group.tf        # Security Group (firewall)
|   |-- ec2.tf                   # EC2 Instance + AMI + SSH Key
|   |-- iam.tf                   # IAM Role pour Lambda
|   |-- lambda.tf                # Lambda Function
|   |-- eventbridge.tf           # EventBridge Rule (cron)
|   |-- outputs.tf               # Outputs (IPs, IDs, commande SSH)
|   |-- user-data.sh             # Script de boot EC2 (Tailscale + K3s)
|   |-- terraform.tfvars         # TES VALEURS (secrets, pas dans Git)
|   `-- .gitignore               # Ignorer secrets
|
|-- lambda/                      # CODE LAMBDA
|   `-- watchdog/
|       `-- handler.py           # Code Python du watchdog
|
|-- app/                         # APPLICATION (bot Discord)
|   |-- bot.py
|   |-- Dockerfile
|   `-- ...
|
`-- kubernetes/                  # MANIFESTS K8S (Phase 4)
    `-- ...
```

**Créer la structure** :

```bash
# Sur ton MAC
cd ~
mkdir -p k8s-discord-bot-portfolio/infrastructure
mkdir -p k8s-discord-bot-portfolio/lambda/watchdog

cd k8s-discord-bot-portfolio/infrastructure
```

---

## Fichier 1 : main.tf

Configuration Terraform et provider AWS.

**Créer** : `infrastructure/main.tf`

```hcl
# ==================================================================
# TERRAFORM CONFIGURATION
# ==================================================================

terraform {
  required_version = ">= 1.6.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ==================================================================
# AWS PROVIDER
# ==================================================================

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = var.project_name
      ManagedBy   = "terraform"
      Environment = "production"
    }
  }
}
```

**Explication** :

- `required_version` : Version minimum de Terraform
- `required_providers` : On dit à Terraform qu'on utilise AWS
- `provider "aws"` : Configuration du provider AWS
- `region` : Région où créer les ressources (eu-west-3 = Paris)
- `default_tags` : Tags automatiques sur toutes les ressources

---

## Fichier 2 : variables.tf

Déclaration de toutes les variables.

**Créer** : `infrastructure/variables.tf`

```hcl
# ==================================================================
# VARIABLES - CONFIGURATION GÉNÉRALE
# ==================================================================

variable "project_name" {
  description = "Nom du projet (préfixe pour toutes les ressources)"
  type        = string
  default     = "k8s-hybrid"
}

variable "aws_region" {
  description = "Région AWS"
  type        = string
  default     = "eu-west-3"  # Paris
}

# ==================================================================
# VARIABLES - RÉSEAU
# ==================================================================

variable "vpc_cidr" {
  description = "CIDR block du VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR block du subnet public"
  type        = string
  default     = "10.0.1.0/24"
}

# ==================================================================
# VARIABLES - EC2
# ==================================================================

variable "instance_type" {
  description = "Type d'instance EC2"
  type        = string
  default     = "t3.micro"  # Free tier eligible
}

# ==================================================================
# VARIABLES - TAILSCALE + HEALTHCHECK (à remplir dans terraform.tfvars)
# ==================================================================

variable "healthcheck_url" {
  description = "URL du healthcheck Tailscale Funnel (ex: https://laptop.tailxxx.ts.net/health)"
  type        = string
  # Pas de default - DOIT être fourni dans terraform.tfvars
}

variable "tailscale_auth_key" {
  description = "Clé d'authentification Tailscale"
  type        = string
  sensitive   = true  # Cache dans les logs
  # Pas de default - DOIT être fourni dans terraform.tfvars
}
```

**Explication** :

- Variables avec `default` : optionnelles
- Variables sans `default` : obligatoires (DOIVENT être dans terraform.tfvars)
- `sensitive = true` : La valeur ne sera pas affichée dans les logs

---

## Fichier 3 : vpc.tf

Réseau AWS (VPC, subnet, internet gateway, route table).

**Créer** : `infrastructure/vpc.tf`

```hcl
# ==================================================================
# VPC - VIRTUAL PRIVATE CLOUD
# ==================================================================

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# ==================================================================
# SUBNET PUBLIC
# ==================================================================

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.subnet_cidr
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-subnet-public"
    Type = "public"
  }
}

# ==================================================================
# INTERNET GATEWAY
# ==================================================================

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

# ==================================================================
# ROUTE TABLE
# ==================================================================

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-rt-public"
  }
}

# Association subnet <-> route table
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
```

**Explication** :

- **VPC** : Réseau privé virtuel (10.0.0.0/16 = 65,536 adresses IP)
- **Subnet** : Sous-réseau public (10.0.1.0/24 = 256 adresses IP)
- **Internet Gateway** : Porte vers Internet
- **Route Table** : Route tout le trafic (0.0.0.0/0) vers l'IGW

---

## Fichier 4 : security-group.tf

Firewall (qui peut se connecter à l'EC2).

**Créer** : `infrastructure/security-group.tf`

```hcl
# ==================================================================
# SECURITY GROUP - WORKER NODE
# ==================================================================

resource "aws_security_group" "worker" {
  name        = "${var.project_name}-worker-sg"
  description = "Security group for K8s worker node"
  vpc_id      = aws_vpc.main.id

  # Règle entrante : SSH
  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Règle entrante : Tailscale VPN
  ingress {
    description = "Tailscale VPN"
    from_port   = 41641
    to_port     = 41641
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Règle entrante : K3s API (depuis le VPC seulement)
  ingress {
    description = "K3s API from VPC"
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  # Règle sortante : Tout autorisé
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-worker-sg"
  }
}
```

**Explication** :

- **Port 22 (SSH)** : Pour se connecter en SSH
- **Port 41641 (Tailscale)** : Pour le VPN Tailscale
- **Port 6443 (K3s)** : Pour K3s API
- **Egress** : Tout autorisé (l'EC2 peut contacter Internet)

---

## Fichier 5 : ec2.tf

Instance EC2 (serveur virtuel).

**Créer** : `infrastructure/ec2.tf`

```hcl
# ==================================================================
# AMI UBUNTU 22.04
# ==================================================================

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ==================================================================
# SSH KEY PAIR
# ==================================================================

resource "aws_key_pair" "main" {
  key_name   = "${var.project_name}-key"
  public_key = file("~/.ssh/id_rsa.pub")

  tags = {
    Name = "${var.project_name}-key"
  }
}

# ==================================================================
# EC2 INSTANCE - WORKER NODE
# ==================================================================

resource "aws_instance" "worker" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.main.key_name
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.worker.id]

  user_data = templatefile("${path.module}/user-data.sh", {
    tailscale_auth_key = var.tailscale_auth_key
  })
  # Note : Plus besoin de k3s_url ni k3s_token car EC2 = control plane standalone

  root_block_device {
    volume_type = "gp3"
    volume_size = 8
    encrypted   = true
  }

  tags = {
    Name = "${var.project_name}-worker"
    Role = "k8s-worker"
  }

  instance_initiated_shutdown_behavior = "stop"
}
```

**Explication** :

- **AMI** : Image Ubuntu 22.04 officielle
- **instance_type** : t3.micro (le moins cher)
- **user_data** : Script qui s'exécute au boot (installe Tailscale + K3s)
- **templatefile** : Injecte les variables dans user-data.sh

---

## Fichier 6 : user-data.sh

Script de boot EC2 (installe Tailscale et K3s).

**Créer** : `infrastructure/user-data.sh`

```bash
#!/bin/bash
set -e

# ==================================================================
# MISE À JOUR DU SYSTÈME
# ==================================================================

apt-get update
apt-get upgrade -y
apt-get install -y curl wget vim htop

# ==================================================================
# INSTALLATION DE TAILSCALE
# ==================================================================

echo "Installing Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh

echo "Starting Tailscale..."
tailscale up --authkey=${tailscale_auth_key} --advertise-tags=tag:k8s-worker

sleep 10

# ==================================================================
# INSTALLATION DE K3S SERVER (STANDALONE)
# ==================================================================

echo "Installing K3s server (standalone control plane)..."
curl -sfL https://get.k3s.io | sh -

echo "Checking K3s server status..."
systemctl status k3s --no-pager

echo "Waiting for K3s to be ready..."
until kubectl get nodes &> /dev/null; do
  echo "Waiting for K3s API..."
  sleep 5
done

echo "K3s server is ready!"
kubectl get nodes

echo "Setup complete!"
```

**Explication** :

- **apt-get update/upgrade** : Met à jour le système
- **Tailscale** : Installe et démarre avec ta clé d'auth
- **K3s** : Installe en mode **server standalone** (pas d'agent, cluster indépendant)
- **${variables}** : Remplacées par Terraform via templatefile()
- **Note** : Plus besoin de K3S_URL ni K3S_TOKEN car c'est un control plane standalone

---

**[SUITE DANS LE PROCHAIN MESSAGE : IAM, Lambda, EventBridge, Outputs, Déploiement]**

## Fichier 7 : iam.tf

Permissions IAM pour Lambda.

**Créer** : `infrastructure/iam.tf`

```hcl
# ==================================================================
# IAM ROLE POUR LAMBDA WATCHDOG
# ==================================================================

resource "aws_iam_role" "lambda_watchdog" {
  name = "${var.project_name}-lambda-watchdog-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Name = "${var.project_name}-lambda-watchdog-role"
  }
}

# ==================================================================
# POLICIES - PERMISSIONS EC2
# ==================================================================

resource "aws_iam_role_policy_attachment" "lambda_ec2" {
  role       = aws_iam_role.lambda_watchdog.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
}

# ==================================================================
# POLICIES - PERMISSIONS CLOUDWATCH LOGS
# ==================================================================

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_watchdog.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}
```

**Explication** :

- **IAM Role** : Permissions pour Lambda
- **assume_role_policy** : Seul Lambda peut utiliser ce rôle
- **AmazonEC2FullAccess** : Peut start/stop/describe EC2
- **CloudWatchLogsFullAccess** : Peut écrire des logs

---

## Fichier 8 : lambda.tf

Fonction Lambda watchdog.

**Créer** : `infrastructure/lambda.tf`

```hcl
# ==================================================================
# ARCHIVER LE CODE LAMBDA
# ==================================================================

data "archive_file" "lambda_watchdog" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/watchdog"
  output_path = "${path.module}/lambda_watchdog.zip"
}

# ==================================================================
# FONCTION LAMBDA
# ==================================================================

resource "aws_lambda_function" "watchdog" {
  filename         = data.archive_file.lambda_watchdog.output_path
  function_name    = "${var.project_name}-watchdog"
  role            = aws_iam_role.lambda_watchdog.arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.11"
  timeout         = 60
  source_code_hash = data.archive_file.lambda_watchdog.output_base64sha256

  environment {
    variables = {
      WORKER_INSTANCE_ID  = aws_instance.worker.id
      HEALTHCHECK_URL     = var.healthcheck_url
    }
  }

  tags = {
    Name = "${var.project_name}-watchdog"
  }
}
```

**Explication** :

- **archive_file** : Zippe le code Python pour Lambda
- **source_dir** : Dossier ../lambda/watchdog (on le créera après)
- **handler** : Fichier handler.py, fonction lambda_handler()
- **environment** : Variables d'env accessibles dans le code Python

---

## Fichier 9 : eventbridge.tf

Déclencheur cron pour Lambda (toutes les 5 minutes).

**Créer** : `infrastructure/eventbridge.tf`

```hcl
# ==================================================================
# EVENTBRIDGE RULE - CRON
# ==================================================================

resource "aws_cloudwatch_event_rule" "watchdog_trigger" {
  name                = "${var.project_name}-watchdog-trigger"
  description         = "Trigger watchdog every 5 minutes"
  schedule_expression = "rate(5 minutes)"

  tags = {
    Name = "${var.project_name}-watchdog-trigger"
  }
}

# ==================================================================
# EVENTBRIDGE TARGET - LAMBDA
# ==================================================================

resource "aws_cloudwatch_event_target" "watchdog" {
  rule      = aws_cloudwatch_event_rule.watchdog_trigger.name
  target_id = "lambda"
  arn       = aws_lambda_function.watchdog.arn
}

# ==================================================================
# PERMISSION EVENTBRIDGE -> LAMBDA
# ==================================================================

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.watchdog.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.watchdog_trigger.arn
}
```

**Explication** :

- **event_rule** : Déclencheur toutes les 5 minutes
- **event_target** : Quelle Lambda appeler (notre watchdog)
- **lambda_permission** : Autorise EventBridge à invoquer Lambda

---

## Fichier 10 : outputs.tf

Valeurs affichées après déploiement.

**Créer** : `infrastructure/outputs.tf`

```hcl
# ==================================================================
# OUTPUTS
# ==================================================================

output "vpc_id" {
  description = "ID du VPC"
  value       = aws_vpc.main.id
}

output "subnet_id" {
  description = "ID du subnet"
  value       = aws_subnet.public.id
}

output "security_group_id" {
  description = "ID du security group"
  value       = aws_security_group.worker.id
}

output "worker_instance_id" {
  description = "ID de l'instance EC2"
  value       = aws_instance.worker.id
}

output "worker_public_ip" {
  description = "IP publique de l'instance EC2"
  value       = aws_instance.worker.public_ip
}

output "worker_private_ip" {
  description = "IP privée de l'instance EC2"
  value       = aws_instance.worker.private_ip
}

output "lambda_function_name" {
  description = "Nom de la fonction Lambda"
  value       = aws_lambda_function.watchdog.function_name
}

output "ssh_command" {
  description = "Commande SSH pour se connecter"
  value       = "ssh -i ~/.ssh/id_rsa ubuntu@${aws_instance.worker.public_ip}"
}
```

**Explication** :

- Affiche les IDs et IPs après `terraform apply`
- Utile pour copier-coller (ex: commande SSH)

---

## Code Lambda : handler.py

Le code Python qui vérifie le laptop et démarre/arrête l'EC2.

**Créer** : `lambda/watchdog/handler.py`

```python
import os
import boto3
import urllib3
import json

# Variables d'environnement (injectées par Terraform)
WORKER_INSTANCE_ID = os.environ['WORKER_INSTANCE_ID']
HEALTHCHECK_URL = os.environ['HEALTHCHECK_URL']

# Client AWS EC2
ec2_client = boto3.client('ec2')

# HTTP client (urllib3 est inclus dans le runtime Lambda, pas requests)
http = urllib3.PoolManager()

def check_laptop_health():
    """Vérifie si le laptop est UP via healthcheck HTTPS (Tailscale Funnel)"""
    try:
        response = http.request('GET', HEALTHCHECK_URL, timeout=10.0)
        return response.status == 200
    except Exception as e:
        print(f"Error checking laptop healthcheck: {e}")
        return False

def get_ec2_state():
    """Récupère l'état actuel de l'instance EC2"""
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
    """
    Point d'entrée Lambda - Logique du watchdog
    
    Règles :
    - Laptop UP + EC2 running -> Stop EC2 (économie)
    - Laptop DOWN + EC2 stopped -> Start EC2 (failover)
    - Sinon -> Ne rien faire
    """
    
    # Vérifier l'état du laptop
    laptop_up = check_laptop_health()
    print(f"Laptop status: {'UP' if laptop_up else 'DOWN'}")
    
    # Vérifier l'état de l'EC2
    ec2_state = get_ec2_state()
    print(f"EC2 state: {ec2_state}")
    
    # Logique de décision
    if laptop_up and ec2_state == 'running':
        stop_ec2()
        action = "Stopped EC2 (laptop is back up)"
    elif not laptop_up and ec2_state == 'stopped':
        start_ec2()
        action = "Started EC2 (laptop is down)"
    elif laptop_up and ec2_state == 'stopped':
        action = "None (normal state - laptop up, EC2 stopped)"
    elif not laptop_up and ec2_state == 'running':
        action = "None (failover active - laptop down, EC2 running)"
    else:
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

**Explication** :

- **check_laptop_health()** : Teste si le laptop répond sur le port 6443 (K3s)
- **get_ec2_state()** : Récupère l'état de l'EC2 (running, stopped, etc.)
- **lambda_handler()** : Logique principale du watchdog

---

## Récupérer les valeurs nécessaires

Avant de déployer, tu dois récupérer 2 informations (plus besoin du token K3s avec Solution 4 !).

### 1. URL Healthcheck Tailscale Funnel

**Sur ton LAPTOP (Arch)** :

```bash
# Vérifier que Funnel est actif
tailscale funnel status

# Output:
# https://laptop-thinkpad.tail1234.ts.net
#   └── http://127.0.0.1:8080
```

**Copie l'URL et ajoute `/health` à la fin** :
- Exemple : `https://laptop-thinkpad.tail1234.ts.net/health`

### 2. Clé d'auth Tailscale

1. Va sur https://login.tailscale.com/admin/settings/keys
2. Clique sur **"Generate auth key"**
3. Coche :
    - [ ] **Reusable** (pour pouvoir recréer l'EC2)
    - [ ] **Ephemeral** (optionnel)
4. Tags : `tag:k8s-worker`
5. Clique **"Generate key"**
6. **Copie la clé** (commence par `tskey-auth-...`)

**[!] Tu ne pourras plus voir cette clé après !**

---

## Créer terraform.tfvars

Ce fichier contient TES valeurs personnelles (secrets).

**Créer** : `infrastructure/terraform.tfvars`

```hcl
# ==================================================================
# TERRAFORM.TFVARS - TES VALEURS PERSONNELLES
# ==================================================================

# URL Healthcheck Tailscale Funnel de ton laptop
healthcheck_url = "https://laptop-thinkpad.tail1234.ts.net/health"  # Remplace par TON URL Funnel

# Clé d'auth Tailscale
tailscale_auth_key = "tskey-auth-kABCDEF123..."  # Remplace par TA clé

# Note : Plus besoin de laptop_tailscale_ip ni k3s_token avec Solution 4 !
```

**[!] IMPORTANT** : Ce fichier contient des secrets, il ne doit **JAMAIS** être commité dans Git !

---

## Créer .gitignore

Pour ne pas commiter les secrets.

**Créer** : `infrastructure/.gitignore`

```
# Terraform
.terraform/
*.tfstate
*.tfstate.backup
.terraform.lock.hcl
terraform.tfvars
*.tfvars
!terraform.tfvars.example

# Lambda
lambda_watchdog.zip

# Secrets
*.pem
*.key
.env
```

---

## Déploiement

Maintenant, on déploie l'infrastructure !

### Étape 1 : Initialiser Terraform

```bash
cd ~/k8s-discord-bot-portfolio/infrastructure

terraform init
```

**Output attendu** :

```
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Installing hashicorp/aws v5.31.0...

Terraform has been successfully initialized!
```

**Ce qui se passe** :

- Télécharge le provider AWS
- Crée le dossier `.terraform/`
- Prêt à utiliser

### Étape 2 : Voir le plan d'exécution

```bash
terraform plan
```

**Output attendu** (exemple) :

```
Terraform will perform the following actions:

  # aws_vpc.main will be created
  + resource "aws_vpc" "main" {
      + cidr_block = "10.0.0.0/16"
      ...
    }

  # aws_instance.worker will be created
  + resource "aws_instance" "worker" {
      + ami           = "ami-0c55b159cbfafe1f0"
      + instance_type = "t3.micro"
      ...
    }

  ... (autres ressources)

Plan: 15 to add, 0 to change, 0 to destroy.
```

**Vérifications** :

- [OK] 15 ressources à créer
- [OK] 0 ressources à détruire
- [OK] Pas d'erreur

### Étape 3 : Créer l'infrastructure

```bash
terraform apply
```

Terraform demande confirmation :

```
Do you want to perform these actions?
  ...
  Enter a value:
```

**Tape `yes` et appuie sur Enter.**

**Output final** (après ~3-4 minutes) :

```
Apply complete! Resources: 15 added, 0 changed, 0 destroyed.

Outputs:

lambda_function_name = "k8s-hybrid-watchdog"
security_group_id = "sg-0123456789abcdef"
ssh_command = "ssh -i ~/.ssh/id_rsa ubuntu@3.250.123.45"
subnet_id = "subnet-0123456789abcdef"
vpc_id = "vpc-0123456789abcdef"
worker_instance_id = "i-0123456789abcdef"
worker_private_ip = "10.0.1.123"
worker_public_ip = "3.250.123.45"
```

**[OK] Infrastructure créée !**

---

## Vérifications

### 1. SSH sur l'EC2

**Attendre 2-3 minutes** que l'EC2 boote et exécute user-data.sh.

```bash
# Utiliser l'output Terraform
ssh -i ~/.ssh/id_rsa ubuntu@$(terraform output -raw worker_public_ip)
```

**Sur l'EC2** :

```bash
# Vérifier Tailscale
tailscale status
# Tu devrais voir ton laptop, ton NAS ET l'EC2

# Vérifier K3s server (pas agent, c'est un control plane standalone)
sudo systemctl status k3s
# Devrait être "active (running)"

# Vérifier le cluster local
sudo kubectl get nodes
# Tu devrais voir l'EC2 en tant que control-plane

# Quitter
exit
```

### 2. Architecture des clusters

**IMPORTANT** : Tu as maintenant **2 clusters K3s complètement séparés** :

1. **Cluster NAS (chez toi)** : tpre-nas en control-plane
2. **Cluster AWS (cloud)** : ip-10-0-1-208 en control-plane standalone

**Sur ton NAS** :

```bash
kubectl get nodes -o wide
# Tu verras uniquement : tpre-nas
```

**Sur ton instance AWS EC2** :

```bash
ssh ubuntu@100.69.6.14  # Via Tailscale
sudo kubectl get nodes -o wide
# Tu verras uniquement : ip-10-0-1-208
```

**[OK] Deux clusters indépendants fonctionnent !**

### 3. Vérifier les logs Lambda

**Attendre 5 minutes** (premier trigger EventBridge).

```bash
# Voir les logs Lambda (remplace k8s-hybrid par ton project_name si différent)
aws logs tail /aws/lambda/k8s-discord-bot-watchdog --follow
```

**Output attendu** :

```
2024-01-15 10:05:00 START RequestId: abc123...
2024-01-15 10:05:01 Laptop status: UP
2024-01-15 10:05:02 EC2 state: running
2024-01-15 10:05:03 Stopping EC2 instance i-0123...
2024-01-15 10:05:04 Action: Stopped EC2 (laptop is back up)
2024-01-15 10:05:05 END RequestId: abc123...
```

**[OK] Lambda fonctionne !**

---

## Commandes utiles

### Voir l'état Terraform

```bash
# Lister toutes les ressources créées
terraform state list

# Voir les détails d'une ressource
terraform state show aws_instance.worker

# Voir tous les outputs
terraform output
```

### Modifier l'infrastructure

```bash
# Modifier variables.tf ou terraform.tfvars
vim terraform.tfvars

# Voir les changements
terraform plan

# Appliquer les changements
terraform apply
```

### Détruire l'infrastructure

```bash
terraform destroy
```

Terraform demande confirmation, tape `yes`.

**[!] Tout sera supprimé définitivement !**

---

## Troubleshooting

### Erreur : "No valid credential sources"

**Problème** : AWS CLI pas configuré.

**Solution** :

```bash
aws configure
# Renseigne tes Access Key ID et Secret Access Key
```

### Erreur : "InvalidKeyPair.NotFound"

**Problème** : Clé SSH n'existe pas.

**Solution** :

```bash
ssh-keygen -t rsa -b 4096 -C "ton-email@example.com"
```

### Lambda ne peut pas contacter le laptop

**Problème** : URL healthcheck incorrecte ou serveur healthcheck non accessible.

**Solution** :

1. Vérifier l'URL healthcheck :

    ```bash
    # Sur laptop
    tailscale funnel status
    # Puis tester :
    curl https://laptop-thinkpad.tail1234.ts.net/health
    # Doit retourner : OK
    ```

2. Vérifier Tailscale :
    
    ```bash
    # Sur laptop
    tailscale ip -4
    ```
    
3. Mettre à jour `terraform.tfvars`
    
4. Recréer l'EC2 :
    
    ```bash
    terraform taint aws_instance.worker
    terraform apply
    ```
    

### Lambda ne démarre/arrête pas l'EC2

**Problème** : Permissions IAM manquantes.

**Solution** :

```bash
# Vérifier que le rôle Lambda a les bonnes permissions
aws iam list-attached-role-policies --role-name k8s-hybrid-lambda-watchdog-role
```

---

## Résumé des coûts

**EC2 t3.micro** :

- Allumé 24/7 : ~€8/mois
- Éteint 23h50/jour (avec Lambda) : ~€0.10/mois

**Lambda** :

- 8,640 exécutions/mois (toutes les 5 min)
- Free tier : 1M exécutions gratuites/mois
- Coût : **€0/mois**

**Total avec Lambda watchdog : ~€0.10/mois** [OK]

---

## Prochaines étapes

[OK] **Infrastructure AWS créée avec Terraform !**

Tu as maintenant :

- [x] VPC configuré
- [x] EC2 worker node
- [x] Tailscale VPN actif
- [x] K3s cluster à 2 nodes
- [x] Lambda watchdog pour économiser

**Suite du guide** :

- Phase 3 : Docker -> - Conteneuriser le bot Discord
- Phase 4 : Kubernetes - Déployer le bot dans K8s
- Phase 5 : Monitoring - Prometheus + Grafana
- Phase 6 : GitOps - ArgoCD

**Félicitations !** [OK]
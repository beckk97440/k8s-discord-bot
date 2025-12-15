# Phase 2 : Infrastructure AWS

[← Phase 1](Part_2_Phase_1_Prérequis.md) | [Phase 3 →](Part_4_Phase_3_Docker.md)

---

## 📚 Vue d'ensemble

Dans cette phase, tu vas créer toute l'infrastructure AWS nécessaire pour le cluster hybride :

- VPC et networking (Subnet, Internet Gateway, Route Table)
- Security Groups (règles de firewall)
- EC2 instance (worker node backup)
- IAM Role (permissions Lambda)
- Lambda function (watchdog)
- EventBridge rule (trigger automatique)

**3 méthodes disponibles** :

1. **Console Web** - Interface graphique (pédagogique)
2. **AWS CLI** - Ligne de commande (scriptable)
3. **Terraform** - Infrastructure as Code (recommandé, production)

---

## 🎯 Quelle méthode choisir ?

### Méthode A : Console Web

[Voir le guide complet - Console Web](Part_3A_Infrastructure_Console.md)

**Quand l'utiliser** :
- ✅ Tu découvres AWS
- ✅ Tu veux comprendre visuellement chaque ressource
- ✅ Environnement de test/learning

**Avantages** :
- Interface visuelle intuitive
- Validation immédiate des champs
- Bon pour comprendre les concepts

**Inconvénients** :
- ❌ Pas reproductible
- ❌ Erreurs manuelles possibles
- ❌ Difficile à documenter
- ❌ Pas adapté pour production

---

### Méthode B : AWS CLI

[Voir le guide complet - AWS CLI](Part_3B_Infrastructure_CLI.md)

**Quand l'utiliser** :
- ✅ Tu es à l'aise avec le terminal
- ✅ Tu veux scripter l'infrastructure
- ✅ Prototypage rapide

**Avantages** :
- Scriptable (peut être automatisé)
- Plus rapide que la console
- Versionnable (script bash)

**Inconvénients** :
- ❌ Moins lisible que Terraform
- ❌ Pas de gestion d'état
- ❌ Difficile à maintenir à long terme

---

### Méthode C : Terraform ⭐ RECOMMANDÉ

[Voir le guide complet - Terraform](Part_3C_Infrastructure_Terraform.md)

**Quand l'utiliser** :
- ✅ Projet professionnel/portfolio
- ✅ Infrastructure reproductible
- ✅ Gestion d'état nécessaire
- ✅ Collaboration en équipe

**Avantages** :
- ✅ Infrastructure as Code (versionné dans Git)
- ✅ État géré automatiquement (tfstate)
- ✅ Plan avant d'appliquer (terraform plan)
- ✅ Reproductible en 2 minutes
- ✅ Standard industrie

**Inconvénients** :
- Nécessite d'apprendre la syntaxe HCL
- Légèrement plus long au début

**💡 C'est cette méthode que tu devrais utiliser pour ton portfolio !**

---

## 📋 Ressources créées (identiques pour les 3 méthodes)

| Ressource | Description | Pourquoi ? |
|-----------|-------------|------------|
| **VPC** | Réseau privé (10.0.0.0/16) | Isolation réseau |
| **Subnet** | Sous-réseau public (10.0.1.0/24) | Pour l'EC2 |
| **Internet Gateway** | Accès Internet | EC2 besoin d'Internet |
| **Route Table** | Routes réseau | Trafic vers Internet |
| **Security Group** | Firewall virtuel | SSH, Tailscale, K3s |
| **EC2** | Serveur t3.micro Ubuntu | Worker node backup |
| **IAM Role** | Permissions Lambda | Contrôler EC2 |
| **Lambda** | Fonction watchdog Python | Failover auto |
| **EventBridge** | Trigger Lambda 5 min | Surveillance continue |

---

## 🚀 Choisis ta méthode et go !

1. **Tu débutes AWS ?** → Commence par [Console Web](Part_3A_Infrastructure_Console.md)
2. **Tu veux scripter ?** → [AWS CLI](Part_3B_Infrastructure_CLI.md)
3. **Production/Portfolio ?** → [Terraform](Part_3C_Infrastructure_Terraform.md) ⭐

**💡 Conseil** : Même si tu choisis Terraform finalement, jette un œil à la version Console Web pour comprendre visuellement ce qui est créé !

---

## ✅ Validation (commune aux 3 méthodes)

Après avoir créé l'infrastructure, tu devrais avoir :

```bash
# Vérifier l'EC2
aws ec2 describe-instances --filters "Name=tag:Name,Values=k8s-worker-node"

# Vérifier la Lambda
aws lambda list-functions --query 'Functions[?FunctionName==`k8s-watchdog`]'

# Vérifier EventBridge
aws events list-rules --name-prefix k8s-watchdog

# Tester la connectivité EC2
ssh ubuntu@<EC2_PUBLIC_IP>
```

---

**Prochaine étape** : [Phase 3 - Conteneurisation Docker](Part_4_Phase_3_Docker.md)

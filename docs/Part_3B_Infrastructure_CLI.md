# 💻 Phase 2-B : Infrastructure AWS - AWS CLI

## 📚 Introduction

Ce guide te montre comment créer ton infrastructure AWS via **AWS CLI** (ligne de commande).

**Pourquoi AWS CLI ?**

- ✅ **Scriptable** : Peut être automatisé dans des scripts bash
- ✅ **Rapide** : Commandes directes, pas de clics
- ✅ **Reproductible** : Les commandes peuvent être sauvegardées
- ✅ **CI/CD** : Peut être intégré dans des pipelines

**⚠️ Important** :

- Méthode pour **scripter** et **automatiser légèrement**
- **Pas recommandé pour production** (utilise Terraform à la place)
- Les concepts AWS sont expliqués en détail dans **Phase 2-A (Console Web)**

---

## 🎯 Ce qu'on va créer

```
Infrastructure AWS (Région eu-west-3 - Paris)
├─ VPC (10.0.0.0/16)
├─ Subnet (10.0.1.0/24)
├─ Internet Gateway
├─ Route Table
├─ Security Group
├─ EC2 Instance (t3.micro, Ubuntu 22.04)
├─ IAM Role
├─ Lambda Function
└─ EventBridge Rule
```

**Temps total** : ~10-15 minutes

---

## ✅ Prérequis

### Installer AWS CLI

**Sur Mac** :

```bash
brew install awscli
```

**Sur Arch Linux** :

```bash
sudo pacman -S aws-cli
```

**Vérifier** :

```bash
aws --version
# aws-cli/2.x.x
```

### Configurer AWS CLI

```bash
aws configure
```

Il va demander :

```
AWS Access Key ID: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name: eu-west-3
Default output format: json
```

**Où trouver les Access Keys ?** Console AWS → IAM → Users → Ton user → Security credentials → Create access key

**Tester** :

```bash
aws sts get-caller-identity
# Doit afficher ton User ID ✅
```

---

## 💡 Astuce : Variables bash

Pour faciliter les commandes, on va stocker les IDs dans des variables :

```bash
# Créer un fichier pour les variables
cat > ~/aws-infra-vars.sh <<'EOF'
#!/bin/bash
# Variables AWS Infrastructure
export AWS_REGION="eu-west-3"
export VPC_ID=""
export SUBNET_ID=""
export IGW_ID=""
export RT_ID=""
export SG_ID=""
export INSTANCE_ID=""
export AMI_ID=""
EOF

# Source le fichier
source ~/aws-infra-vars.sh
```

**Tu mettras à jour les valeurs au fur et à mesure.**

---

## Section 1 : VPC

**📖 Concept** : Voir Phase 2-A Section 1

### Créer le VPC

```bash
# Créer le VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=k8s-hybrid-vpc}]' \
  --query 'Vpc.VpcId' \
  --output text \
  --region $AWS_REGION)

echo "VPC ID: $VPC_ID"
# vpc-0123456789abcdef
```

**📝 Sauvegarder** :

```bash
echo "export VPC_ID=$VPC_ID" >> ~/aws-infra-vars.sh
```

### Activer DNS support

```bash
aws ec2 modify-vpc-attribute \
  --vpc-id $VPC_ID \
  --enable-dns-support \
  --region $AWS_REGION

aws ec2 modify-vpc-attribute \
  --vpc-id $VPC_ID \
  --enable-dns-hostnames \
  --region $AWS_REGION
```

### ✅ Vérification

```bash
aws ec2 describe-vpcs \
  --vpc-ids $VPC_ID \
  --region $AWS_REGION
```

**Temps** : ~20 secondes

---

## Section 2 : Subnet

**📖 Concept** : Voir Phase 2-A Section 2

### Créer le Subnet

```bash
SUBNET_ID=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone ${AWS_REGION}a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=k8s-hybrid-subnet-public}]' \
  --query 'Subnet.SubnetId' \
  --output text \
  --region $AWS_REGION)

echo "Subnet ID: $SUBNET_ID"
```

**📝 Sauvegarder** :

```bash
echo "export SUBNET_ID=$SUBNET_ID" >> ~/aws-infra-vars.sh
```

### Activer Auto-assign Public IP

```bash
aws ec2 modify-subnet-attribute \
  --subnet-id $SUBNET_ID \
  --map-public-ip-on-launch \
  --region $AWS_REGION
```

### ✅ Vérification

```bash
aws ec2 describe-subnets \
  --subnet-ids $SUBNET_ID \
  --query 'Subnets[0].{CIDR:CidrBlock,AvailableIPs:AvailableIpAddressCount,MapPublicIP:MapPublicIpOnLaunch}' \
  --region $AWS_REGION
```

**Temps** : ~15 secondes

---

## Section 3 : Internet Gateway

**📖 Concept** : Voir Phase 2-A Section 3

### Créer l'IGW

```bash
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=k8s-hybrid-igw}]' \
  --query 'InternetGateway.InternetGatewayId' \
  --output text \
  --region $AWS_REGION)

echo "IGW ID: $IGW_ID"
```

**📝 Sauvegarder** :

```bash
echo "export IGW_ID=$IGW_ID" >> ~/aws-infra-vars.sh
```

### Attacher au VPC

```bash
aws ec2 attach-internet-gateway \
  --internet-gateway-id $IGW_ID \
  --vpc-id $VPC_ID \
  --region $AWS_REGION
```

### ✅ Vérification

```bash
aws ec2 describe-internet-gateways \
  --internet-gateway-ids $IGW_ID \
  --query 'InternetGateways[0].Attachments[0].State' \
  --output text \
  --region $AWS_REGION
# available ✅
```

**Temps** : ~10 secondes

---

## Section 4 : Route Table

**📖 Concept** : Voir Phase 2-A Section 4

### Récupérer la Main Route Table

```bash
RT_ID=$(aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=$VPC_ID" "Name=association.main,Values=true" \
  --query 'RouteTables[0].RouteTableId' \
  --output text \
  --region $AWS_REGION)

echo "Route Table ID: $RT_ID"
```

**📝 Sauvegarder** :

```bash
echo "export RT_ID=$RT_ID" >> ~/aws-infra-vars.sh
```

### Tagger la Route Table

```bash
aws ec2 create-tags \
  --resources $RT_ID \
  --tags Key=Name,Value=k8s-hybrid-rt-public \
  --region $AWS_REGION
```

### Ajouter la route vers Internet

```bash
aws ec2 create-route \
  --route-table-id $RT_ID \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID \
  --region $AWS_REGION
```

### Associer le Subnet

```bash
aws ec2 associate-route-table \
  --route-table-id $RT_ID \
  --subnet-id $SUBNET_ID \
  --region $AWS_REGION
```

### ✅ Vérification

```bash
aws ec2 describe-route-tables \
  --route-table-ids $RT_ID \
  --query 'RouteTables[0].Routes[*].{Destination:DestinationCidrBlock,Target:GatewayId}' \
  --region $AWS_REGION
```

**Output attendu** :

```json
[
    {
        "Destination": "10.0.0.0/16",
        "Target": "local"
    },
    {
        "Destination": "0.0.0.0/0",
        "Target": "igw-0123456789abcdef"
    }
]
```

**Temps** : ~20 secondes

---

## Section 5 : Security Group

**📖 Concept** : Voir Phase 2-A Section 5

### Créer le Security Group

```bash
SG_ID=$(aws ec2 create-security-group \
  --group-name k8s-hybrid-worker-sg \
  --description "Security group for K8s worker node" \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=k8s-hybrid-worker-sg}]' \
  --query 'GroupId' \
  --output text \
  --region $AWS_REGION)

echo "Security Group ID: $SG_ID"
```

**📝 Sauvegarder** :

```bash
echo "export SG_ID=$SG_ID" >> ~/aws-infra-vars.sh
```

### Ajouter les règles Inbound

**SSH** :

```bash
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 22 \
  --cidr 0.0.0.0/0 \
  --region $AWS_REGION
```

**Tailscale** :

```bash
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol udp \
  --port 41641 \
  --cidr 0.0.0.0/0 \
  --region $AWS_REGION
```

**K3s API** :

```bash
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 6443 \
  --cidr 10.0.0.0/16 \
  --region $AWS_REGION
```

### ✅ Vérification

```bash
aws ec2 describe-security-groups \
  --group-ids $SG_ID \
  --query 'SecurityGroups[0].IpPermissions[*].{Port:FromPort,Protocol:IpProtocol,Source:IpRanges[0].CidrIp}' \
  --region $AWS_REGION
```

**Temps** : ~20 secondes

---

## Section 6 : EC2 Instance

**📖 Concept** : Voir Phase 2-A Section 6

### Étape 1 : Créer une Key Pair

**Vérifier si tu en as déjà une** :

```bash
aws ec2 describe-key-pairs --region $AWS_REGION
```

**Si pas de key, en créer une** :

```bash
aws ec2 create-key-pair \
  --key-name k8s-hybrid-key \
  --query 'KeyMaterial' \
  --output text \
  --region $AWS_REGION > ~/.ssh/k8s-hybrid-key.pem

chmod 400 ~/.ssh/k8s-hybrid-key.pem
```

### Étape 2 : Récupérer l'AMI Ubuntu 22.04

```bash
AMI_ID=$(aws ec2 describe-images \
  --owners 099720109477 \
  --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*" \
  --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
  --output text \
  --region $AWS_REGION)

echo "AMI ID: $AMI_ID"
```

**📝 Sauvegarder** :

```bash
echo "export AMI_ID=$AMI_ID" >> ~/aws-infra-vars.sh
```

### Étape 3 : Créer le script User Data

```bash
cat > /tmp/user-data.sh <<'EOF'
#!/bin/bash
apt-get update
apt-get upgrade -y
apt-get install -y curl wget vim htop
hostnamectl set-hostname k8s-worker-aws
EOF
```

### Étape 4 : Lancer l'instance

```bash
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t3.micro \
  --key-name k8s-hybrid-key \
  --subnet-id $SUBNET_ID \
  --security-group-ids $SG_ID \
  --associate-public-ip-address \
  --user-data file:///tmp/user-data.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=k8s-hybrid-worker}]' \
  --query 'Instances[0].InstanceId' \
  --output text \
  --region $AWS_REGION)

echo "Instance ID: $INSTANCE_ID"
```

**📝 Sauvegarder** :

```bash
echo "export INSTANCE_ID=$INSTANCE_ID" >> ~/aws-infra-vars.sh
```

### Étape 5 : Attendre que l'instance soit prête

```bash
echo "Waiting for instance to be running..."
aws ec2 wait instance-running \
  --instance-ids $INSTANCE_ID \
  --region $AWS_REGION

echo "Instance is running! Waiting for status checks..."
aws ec2 wait instance-status-ok \
  --instance-ids $INSTANCE_ID \
  --region $AWS_REGION

echo "Instance is ready! ✅"
```

### Étape 6 : Récupérer l'IP publique

```bash
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text \
  --region $AWS_REGION)

echo "Public IP: $PUBLIC_IP"
```

### Étape 7 : Se connecter en SSH

```bash
ssh -i ~/.ssh/k8s-hybrid-key.pem ubuntu@$PUBLIC_IP
```

**Tester** :

```bash
lsb_release -a
# Ubuntu 22.04 ✅

exit
```

### ✅ Vérification

```bash
aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].{State:State.Name,PublicIP:PublicIpAddress,PrivateIP:PrivateIpAddress}' \
  --region $AWS_REGION
```

**Temps** : ~3 minutes

---

## Section 7 : IAM Role pour Lambda

**📖 Concept** : Voir Phase 2-A Section 7

### Créer la Trust Policy

```bash
cat > /tmp/lambda-trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
```

### Créer le Role

```bash
aws iam create-role \
  --role-name lambda-watchdog-role \
  --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
  --description "Role for Lambda watchdog function" \
  --region $AWS_REGION
```

### Attacher les policies

**EC2 Full Access** :

```bash
aws iam attach-role-policy \
  --role-name lambda-watchdog-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2FullAccess
```

**CloudWatch Logs** :

```bash
aws iam attach-role-policy \
  --role-name lambda-watchdog-role \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
```

### ✅ Vérification

```bash
aws iam list-attached-role-policies \
  --role-name lambda-watchdog-role
```

**Temps** : ~30 secondes

---

## Section 8 : Lambda Function

**📖 Concept** : Voir Phase 2-A Section 8

### Étape 1 : Préparer le code

```bash
mkdir -p ~/lambda-watchdog
cd ~/lambda-watchdog

cat > handler.py <<'EOF'
import os
import boto3
import json
import requests

WORKER_INSTANCE_ID = os.environ['WORKER_INSTANCE_ID']
HEALTHCHECK_URL = os.environ['HEALTHCHECK_URL']

ec2_client = boto3.client('ec2')

def check_laptop_health():
    try:
        response = requests.get(HEALTHCHECK_URL, timeout=10, verify=True)
        return response.status_code == 200
    except Exception as e:
        print(f"Error checking laptop: {e}")
        return False

def get_ec2_state():
    response = ec2_client.describe_instances(InstanceIds=[WORKER_INSTANCE_ID])
    state = response['Reservations'][0]['Instances'][0]['State']['Name']
    return state

def start_ec2():
    print(f"Starting EC2 instance {WORKER_INSTANCE_ID}")
    ec2_client.start_instances(InstanceIds=[WORKER_INSTANCE_ID])

def stop_ec2():
    print(f"Stopping EC2 instance {WORKER_INSTANCE_ID}")
    ec2_client.stop_instances(InstanceIds=[WORKER_INSTANCE_ID])

def lambda_handler(event, context):
    laptop_up = check_laptop_health()
    print(f"Laptop status: {'UP' if laptop_up else 'DOWN'}")
    
    ec2_state = get_ec2_state()
    print(f"EC2 state: {ec2_state}")
    
    if laptop_up and ec2_state == 'running':
        stop_ec2()
        action = "Stopped EC2 (laptop is back up)"
    elif not laptop_up and ec2_state == 'stopped':
        start_ec2()
        action = "Started EC2 (laptop is down)"
    elif laptop_up and ec2_state == 'stopped':
        action = "None (normal state)"
    elif not laptop_up and ec2_state == 'running':
        action = "None (failover active)"
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
EOF
```

### Étape 2 : Créer le ZIP

```bash
zip function.zip handler.py
```

### Étape 3 : Récupérer l'ARN du Role

```bash
ROLE_ARN=$(aws iam get-role \
  --role-name lambda-watchdog-role \
  --query 'Role.Arn' \
  --output text)

echo "Role ARN: $ROLE_ARN"
```

### Étape 4 : Créer la fonction Lambda

```bash
aws lambda create-function \
  --function-name k8s-watchdog \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler handler.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 60 \
  --environment "Variables={WORKER_INSTANCE_ID=$INSTANCE_ID,HEALTHCHECK_URL=https://laptop.ts.net/health}" \
  --region $AWS_REGION
```

**⚠️ HEALTHCHECK_URL** : URL factice pour l'instant, tu la changeras après avoir configuré Tailscale Funnel (Phase 7 - Lambda).

### Étape 5 : Tester la fonction

```bash
aws lambda invoke \
  --function-name k8s-watchdog \
  --payload '{}' \
  --region $AWS_REGION \
  /tmp/lambda-response.json

cat /tmp/lambda-response.json
```

### ✅ Vérification

```bash
aws lambda get-function \
  --function-name k8s-watchdog \
  --query 'Configuration.{State:State,Runtime:Runtime,Timeout:Timeout}' \
  --region $AWS_REGION
```

**Temps** : ~2 minutes

---

## Section 9 : EventBridge Rule

**📖 Concept** : Voir Phase 2-A Section 9

### Créer la rule

```bash
aws events put-rule \
  --name k8s-watchdog-trigger \
  --description "Trigger watchdog every 5 minutes" \
  --schedule-expression "rate(5 minutes)" \
  --region $AWS_REGION
```

### Récupérer l'ARN de la Lambda

```bash
LAMBDA_ARN=$(aws lambda get-function \
  --function-name k8s-watchdog \
  --query 'Configuration.FunctionArn' \
  --output text \
  --region $AWS_REGION)

echo "Lambda ARN: $LAMBDA_ARN"
```

### Ajouter la Lambda comme target

```bash
aws events put-targets \
  --rule k8s-watchdog-trigger \
  --targets "Id=1,Arn=$LAMBDA_ARN" \
  --region $AWS_REGION
```

### Donner la permission à EventBridge d'invoquer la Lambda

```bash
aws lambda add-permission \
  --function-name k8s-watchdog \
  --statement-id AllowEventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn $(aws events describe-rule --name k8s-watchdog-trigger --query 'Arn' --output text --region $AWS_REGION) \
  --region $AWS_REGION
```

### ✅ Vérification

```bash
aws events list-targets-by-rule \
  --rule k8s-watchdog-trigger \
  --region $AWS_REGION
```

**Attendre 5 minutes et vérifier les logs** :

```bash
aws logs tail /aws/lambda/k8s-watchdog --follow --region $AWS_REGION
```

**Temps** : ~30 secondes

---

## 🎉 Récapitulatif

✅ **Infrastructure AWS créée avec AWS CLI en ~15 minutes !**

```bash
# Recharger toutes les variables
source ~/aws-infra-vars.sh

# Afficher le résumé
echo "=== Infrastructure Summary ==="
echo "VPC ID: $VPC_ID"
echo "Subnet ID: $SUBNET_ID"
echo "IGW ID: $IGW_ID"
echo "Security Group ID: $SG_ID"
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text --region $AWS_REGION)"
```

---

## 🧹 Nettoyage

**Script complet pour tout supprimer** :

```bash
#!/bin/bash
source ~/aws-infra-vars.sh

echo "Deleting EventBridge rule..."
aws events remove-targets --rule k8s-watchdog-trigger --ids 1 --region $AWS_REGION
aws events delete-rule --name k8s-watchdog-trigger --region $AWS_REGION

echo "Deleting Lambda function..."
aws lambda delete-function --function-name k8s-watchdog --region $AWS_REGION

echo "Deleting IAM role..."
aws iam detach-role-policy --role-name lambda-watchdog-role --policy-arn arn:aws:iam::aws:policy/AmazonEC2FullAccess
aws iam detach-role-policy --role-name lambda-watchdog-role --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess
aws iam delete-role --role-name lambda-watchdog-role

echo "Terminating EC2 instance..."
aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region $AWS_REGION
aws ec2 wait instance-terminated --instance-ids $INSTANCE_ID --region $AWS_REGION

echo "Deleting Security Group..."
aws ec2 delete-security-group --group-id $SG_ID --region $AWS_REGION

echo "Deleting Route..."
aws ec2 delete-route --route-table-id $RT_ID --destination-cidr-block 0.0.0.0/0 --region $AWS_REGION

echo "Detaching and deleting IGW..."
aws ec2 detach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID --region $AWS_REGION
aws ec2 delete-internet-gateway --internet-gateway-id $IGW_ID --region $AWS_REGION

echo "Deleting Subnet..."
aws ec2 delete-subnet --subnet-id $SUBNET_ID --region $AWS_REGION

echo "Deleting VPC..."
aws ec2 delete-vpc --vpc-id $VPC_ID --region $AWS_REGION

echo "✅ All resources deleted!"
```

**Temps** : ~2 minutes

---

## 📊 Comparaison CLI vs Console vs Terraform

|Aspect|Console|CLI|Terraform|
|---|---|---|---|
|**Temps**|45 min|15 min|3 min|
|**Reproductible**|❌|⚠️|✅|
|**Scriptable**|❌|✅|✅|
|**Versionné**|❌|⚠️|✅|
|**Rollback**|❌|❌|✅|
|**Plan preview**|❌|❌|✅|
|**Production**|❌|❌|✅|

**Conclusion** : CLI pour scripter, Terraform pour production ! 🎯

---

## ➡️ Prochaine étape

**Phase 2-C : Terraform** - L'approche production qui automatise tout ça en 1 commande !

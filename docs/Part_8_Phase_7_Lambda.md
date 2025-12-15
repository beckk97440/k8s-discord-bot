# 🤖 Phase 7 : Lambda Watchdog - Failover Automatique

[← Phase 6 - GitOps](Part_7_Phase_6_GitOps.md) | [Phase 8 - Tests →](Part_9_Phase_8_Tests.md)

---

## 📚 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Configuration Tailscale Funnel](#configuration-tailscale-funnel)
3. [Serveur healthcheck sur le laptop](#serveur-healthcheck-sur-le-laptop)
4. [Comprendre Lambda](#comprendre-lambda)
5. [Architecture du Watchdog](#architecture-du-watchdog)
6. [Le code Python expliqué](#le-code-python-expliqu%C3%A9)
7. [Tests locaux](#tests-locaux)
8. [Déploiement sur AWS](#d%C3%A9ploiement-sur-aws)
9. [Monitoring de la Lambda](#monitoring-de-la-lambda)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Vue d'ensemble

### Qu'est-ce que le Watchdog ?

**Watchdog** = Fonction Lambda qui surveille le laptop et gère le failover automatique

**Problème à résoudre** :

```
Laptop éteint (tu fermes le couvercle, panne électrique, etc.)
  ↓
Bot Discord down ❌
  ↓
Tu dois manuellement démarrer l'EC2
```

**Solution : Watchdog automatique** :

```
Lambda s'exécute toutes les 5 minutes (EventBridge)
  ↓
Vérifie healthcheck HTTPS via Tailscale Funnel (public)
  ↓
Laptop OK (200) → EC2 reste arrêté (économie)
Laptop DOWN (timeout/erreur) → EC2 démarre automatiquement
  ↓
EC2 démarre → K3s + ArgoCD redéploient le bot ! ✅
```

### Workflow complet

```
┌─────────────────────────────────────────────────────────┐
│                    WORKFLOW WATCHDOG                     │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  EventBridge (trigger toutes les 5 min)                 │
│         │                                                │
│         ▼                                                │
│  ┌─────────────────────────────────────────┐            │
│  │         LAMBDA WATCHDOG                 │            │
│  │  ─────────────────────────────────────  │            │
│  │                                          │            │
│  │  1. HTTPS GET healthcheck                │            │
│  │     https://laptop.ts.net/health         │            │
│  │     (Tailscale Funnel = public)          │            │
│  │                                          │            │
│  │  2. Check état EC2                      │            │
│  │     (boto3 describe_instances)          │            │
│  │                                          │            │
│  │  3. Décision :                          │            │
│  │                                          │            │
│  │     Laptop UP (200 OK) + EC2 Running    │            │
│  │     → Stop EC2 (économie)               │            │
│  │                                          │            │
│  │     Laptop DOWN (timeout) + EC2 Stopped │            │
│  │     → Start EC2 (failover)              │            │
│  │                                          │            │
│  │     Laptop UP + EC2 Stopped             │            │
│  │     → Rien (état normal)                │            │
│  │                                          │            │
│  │     Laptop DOWN + EC2 Running           │            │
│  │     → Rien (failover actif)             │            │
│  │                                          │            │
│  │  4. Log vers CloudWatch                 │            │
│  └─────────────────────────────────────────┘            │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### États possibles

|Laptop|EC2|Action|Raison|
|---|---|---|---|
|✅ UP (200)|🛑 Stopped|Rien|État normal (économique)|
|✅ UP (200)|✅ Running|**Stop EC2**|Pas besoin de backup|
|❌ DOWN (timeout)|🛑 Stopped|**Start EC2**|Failover nécessaire|
|❌ DOWN (timeout)|✅ Running|Rien|Failover déjà actif|

---

## 🌐 Configuration Tailscale Funnel

### Qu'est-ce que Tailscale Funnel ?

**Tailscale Funnel** = Expose un service local sur Internet via HTTPS

**Différences** :

|Feature|Tailscale (normal)|Tailscale Funnel|
|---|---|---|
|**Visibilité**|Seulement ton réseau Tailscale|Internet public (HTTPS)|
|**URL**|`http://100.64.1.5:8080`|`https://laptop.ts.net`|
|**Certificat**|Aucun|TLS automatique|
|**Accessible par**|Tes devices Tailscale uniquement|N'importe qui (Lambda incl.)|

**Pourquoi Funnel plutôt que ping Tailscale ?**

❌ **Problème avec ping Tailscale** :
- Lambda est dans un VPC AWS (pas dans Tailscale)
- Lambda ne peut pas atteindre l'IP Tailscale privée du laptop
- Il faudrait connecter Lambda à Tailscale (complexe, pas supporté nativement)

✅ **Solution avec Funnel** :
- Funnel expose un endpoint HTTPS public
- Lambda peut faire un simple HTTP GET depuis Internet
- Pas besoin de configuration réseau complexe
- Certificat TLS gratuit et automatique

### Activer Tailscale Funnel sur le laptop

```bash
# Sur le laptop (Arch Linux)

# 1. Mettre à jour Tailscale
sudo tailscale update

# 2. Activer Funnel
tailscale funnel status

# Si pas encore activé :
tailscale funnel --bg 8080

# Ceci expose http://localhost:8080 sur https://LAPTOP-NAME.TAILNET.ts.net
```

**🎓 Explication** :

```bash
tailscale funnel --bg 8080
# --bg : Background (daemon)
# 8080 : Port local à exposer
```

**Résultat** :

```
Available on the internet:

https://laptop-thinkpad.tail1234.ts.net/
  └── http://127.0.0.1:8080

Press Ctrl+C to exit.
```

**📝 Note l'URL !** Ex : `https://laptop-thinkpad.tail1234.ts.net`

### Vérifier l'URL Funnel

```bash
# Lister les funnels actifs
tailscale funnel status

# Output:
# https://laptop-thinkpad.tail1234.ts.net
#   └── http://127.0.0.1:8080
```

**Tester depuis n'importe où** :

```bash
curl https://laptop-thinkpad.tail1234.ts.net
# Devrait retourner une erreur "connection refused" si rien n'écoute sur :8080
# C'est normal ! On va créer le serveur healthcheck maintenant
```

---

## 🏥 Serveur healthcheck sur le laptop

### Créer le script healthcheck

**Créer** : `/home/thomas/healthcheck/server.py`

```python
#!/usr/bin/env python3
"""
Serveur HTTP simple pour healthcheck Tailscale Funnel.

Écoute sur localhost:8080 et répond "OK" si K3s tourne.
"""

import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8080

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Handler HTTP pour le healthcheck."""

    def do_GET(self):
        """Traite les requêtes GET."""
        if self.path == '/health':
            # Vérifier que K3s tourne
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', 'k3s'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.stdout.strip() == 'active':
                    # K3s tourne
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'OK')
                else:
                    # K3s down
                    self.send_response(503)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b'K3s not running')

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f'Error: {e}'.encode())
        else:
            # Route inconnue
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Désactive les logs HTTP (optionnel)."""
        pass

def run_server():
    """Démarre le serveur HTTP."""
    server = HTTPServer(('127.0.0.1', PORT), HealthCheckHandler)
    print(f'Healthcheck server running on http://127.0.0.1:{PORT}')
    print('Exposed via Tailscale Funnel')
    server.serve_forever()

if __name__ == '__main__':
    run_server()
```

**Rendre exécutable** :

```bash
chmod +x /home/thomas/healthcheck/server.py
```

### Créer un service systemd

**Créer** : `/etc/systemd/system/healthcheck.service`

**Note Arch Linux** : Remplace `User=thomas` par ton utilisateur (ex: `tpretat`)

```ini
[Unit]
Description=Healthcheck HTTP server for Tailscale Funnel
After=network.target tailscaled.service k3s.service

[Service]
Type=simple
User=thomas                    # ⚠️ Sur Arch Linux NAS : remplace par ton user (ex: tpretat)
WorkingDirectory=/home/thomas/healthcheck    # ⚠️ Adapter le chemin
ExecStart=/usr/bin/python3 /home/thomas/healthcheck/server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Exemple pour Arch Linux NAS** :

```ini
[Unit]
Description=Healthcheck HTTP server for Tailscale Funnel
After=network.target tailscaled.service k3s.service

[Service]
Type=simple
User=tpretat
WorkingDirectory=/home/tpretat/healthcheck
ExecStart=/usr/bin/python /home/tpretat/healthcheck/server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Activer le service** :

```bash
sudo systemctl daemon-reload
sudo systemctl enable healthcheck
sudo systemctl start healthcheck
```

**Vérifier** :

```bash
sudo systemctl status healthcheck

# Output:
# ● healthcheck.service - Healthcheck HTTP server
#    Active: active (running)

# Tester localement
curl http://127.0.0.1:8080/health
# Output: OK
```

### Tester via Funnel

```bash
# Depuis n'importe où (même ton Mac)
curl https://laptop-thinkpad.tail1234.ts.net/health

# Output: OK ✅
```

**🎉 Parfait ! Le healthcheck est accessible depuis Internet !**

---

## 📖 Comprendre Lambda

### Qu'est-ce qu'AWS Lambda ?

**Lambda** = Serverless compute (exécution de code sans serveur)

**Concept** :

- Tu écris du code (Python, Node.js, etc.)
- Tu l'upload sur AWS
- AWS l'exécute quand déclenché
- Tu paies seulement pour le temps d'exécution

**Analogie** : Location de voiture à l'heure

- Tu n'achètes pas la voiture (serveur)
- Tu la loues quand tu en as besoin
- Tu paies seulement le temps d'utilisation

### Caractéristiques Lambda

|Aspect|Détail|
|---|---|
|**Runtime**|Python 3.11, Node.js, Java, Go, etc.|
|**Timeout**|Max 15 minutes|
|**Memory**|128 MB à 10 GB|
|**Concurrent executions**|1000 par défaut (augmentable)|
|**Pricing**|$0.20 / 1M requests + $0.0000166667 / GB-second|

### Free Tier

**AWS Lambda Free Tier** (permanent) :

- ✅ 1 million de requests/mois
- ✅ 400,000 GB-seconds/mois

**Notre watchdog** :

- Toutes les 5 min = 8,640 exécutions/mois
- Durée : ~2 secondes
- Mémoire : 128 MB
- **Total** : ~17 GB-seconds/mois

**Coût** : $0.00 (largement dans le free tier !)

### Handler Lambda

**Handler** = Fonction point d'entrée

**Format** : `fichier.fonction`

Exemple : `handler.lambda_handler`

- Fichier : `handler.py`
- Fonction : `lambda_handler()`

**Signature Python** :

```python
def lambda_handler(event, context):
    # event : Données du déclencheur
    # context : Métadonnées Lambda

    # Ton code ici

    return {
        'statusCode': 200,
        'body': 'Success'
    }
```

---

## 🏗️ Architecture du Watchdog

### Fichiers

```
lambda/
└── watchdog/
    ├── handler.py          # Code principal
    ├── requirements.txt    # Dépendances
    └── README.md           # Documentation
```

### Dépendances

**requirements.txt** :

```
boto3>=1.26.0
requests>=2.31.0
```

**📖 Modules** :

|Module|Usage|
|---|---|
|`boto3`|SDK AWS pour EC2|
|`requests`|HTTP client pour healthcheck|

---

## 🐍 Le code Python expliqué

### Structure complète

**Créer** : `lambda/watchdog/handler.py`

```python
"""
Lambda Watchdog pour Kubernetes Failover
──────────────────────────────────────────

Surveille le laptop via healthcheck HTTPS et gère le failover vers EC2.

Déclenché par : EventBridge (toutes les 5 minutes)
Actions :
  - Si laptop UP et EC2 running → Stop EC2
  - Si laptop DOWN et EC2 stopped → Start EC2
"""

import os
import boto3
import requests
from datetime import datetime

# ══════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════

# Variables d'environnement (définies dans Terraform)
WORKER_INSTANCE_ID = os.environ['WORKER_INSTANCE_ID']
HEALTHCHECK_URL = os.environ['HEALTHCHECK_URL']

# Configuration du health check
HEALTHCHECK_TIMEOUT = 10  # Timeout en secondes

# Client AWS EC2
ec2_client = boto3.client('ec2')

# ══════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════════════════════

def check_laptop_health():
    """
    Vérifie si le laptop est accessible via healthcheck HTTPS.

    Méthode : GET https://laptop.ts.net/health

    Returns:
        bool: True si le laptop répond 200 OK, False sinon
    """
    try:
        # Requête HTTPS GET
        response = requests.get(
            HEALTHCHECK_URL,
            timeout=HEALTHCHECK_TIMEOUT,
            verify=True  # Vérifier le certificat TLS
        )

        # Status code 200 = OK
        if response.status_code == 200:
            print(f"✅ Laptop is UP - {HEALTHCHECK_URL} returned 200 OK")
            return True
        else:
            print(f"⚠️ Laptop healthcheck returned status {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print(f"⏱️ Laptop healthcheck timed out after {HEALTHCHECK_TIMEOUT}s")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"🔌 Connection error to laptop: {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP request error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error checking laptop: {e}")
        return False


def get_ec2_state():
    """
    Récupère l'état actuel de l'instance EC2 worker.

    Returns:
        str: État de l'instance ('running', 'stopped', 'stopping', etc.)
             ou None si erreur
    """
    try:
        # Décrire l'instance EC2
        response = ec2_client.describe_instances(
            InstanceIds=[WORKER_INSTANCE_ID]
        )

        # Extraire l'état
        state = response['Reservations'][0]['Instances'][0]['State']['Name']

        print(f"📊 EC2 instance {WORKER_INSTANCE_ID} state: {state}")
        return state

    except ec2_client.exceptions.ClientError as e:
        print(f"❌ AWS API error getting EC2 state: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"❌ Unexpected response format: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error getting EC2 state: {e}")
        return None


def start_ec2():
    """
    Démarre l'instance EC2 worker.

    Returns:
        bool: True si succès, False sinon
    """
    try:
        print(f"🚀 Starting EC2 instance {WORKER_INSTANCE_ID}...")

        response = ec2_client.start_instances(
            InstanceIds=[WORKER_INSTANCE_ID]
        )

        # Vérifier la réponse
        if response['StartingInstances']:
            current_state = response['StartingInstances'][0]['CurrentState']['Name']
            print(f"✅ EC2 instance start initiated. Current state: {current_state}")
            return True
        else:
            print(f"⚠️ EC2 instance start response unexpected: {response}")
            return False

    except ec2_client.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"❌ AWS API error starting EC2: {error_code} - {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error starting EC2: {e}")
        return False


def stop_ec2():
    """
    Arrête l'instance EC2 worker.

    Returns:
        bool: True si succès, False sinon
    """
    try:
        print(f"🛑 Stopping EC2 instance {WORKER_INSTANCE_ID}...")

        response = ec2_client.stop_instances(
            InstanceIds=[WORKER_INSTANCE_ID]
        )

        # Vérifier la réponse
        if response['StoppingInstances']:
            current_state = response['StoppingInstances'][0]['CurrentState']['Name']
            print(f"✅ EC2 instance stop initiated. Current state: {current_state}")
            return True
        else:
            print(f"⚠️ EC2 instance stop response unexpected: {response}")
            return False

    except ec2_client.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"❌ AWS API error stopping EC2: {error_code} - {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error stopping EC2: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# HANDLER PRINCIPAL
# ══════════════════════════════════════════════════════════════

def lambda_handler(event, context):
    """
    Point d'entrée Lambda.

    Logique de décision :
      - Laptop UP (200) + EC2 Running → Stop EC2 (économie)
      - Laptop DOWN (timeout) + EC2 Stopped → Start EC2 (failover)
      - Laptop UP + EC2 Stopped → Rien (état normal)
      - Laptop DOWN + EC2 Running → Rien (failover actif)

    Args:
        event (dict): Événement EventBridge
        context (object): Contexte Lambda

    Returns:
        dict: Statut de l'exécution
    """

    # Timestamp du début
    start_time = datetime.utcnow()
    print(f"⏰ Watchdog execution started at {start_time.isoformat()}Z")
    print(f"📋 Event: {event}")

    # ──────────────────────────────────────────────────────────
    # 1. Vérifier l'état du laptop
    # ──────────────────────────────────────────────────────────

    laptop_is_up = check_laptop_health()

    # ──────────────────────────────────────────────────────────
    # 2. Vérifier l'état de l'EC2
    # ──────────────────────────────────────────────────────────

    ec2_state = get_ec2_state()

    if ec2_state is None:
        # Erreur lors de la récupération de l'état
        print("❌ Cannot determine EC2 state, aborting")
        return {
            'statusCode': 500,
            'body': 'Error: Unable to determine EC2 state'
        }

    # ──────────────────────────────────────────────────────────
    # 3. Logique de décision
    # ──────────────────────────────────────────────────────────

    action_taken = None

    # CAS 1 : Laptop UP + EC2 Running
    # → Stop EC2 (pas besoin de backup)
    if laptop_is_up and ec2_state == 'running':
        print("📌 Decision: Laptop is UP and EC2 is RUNNING")
        print("💡 Action: Stopping EC2 to save costs")

        if stop_ec2():
            action_taken = 'stopped_ec2'
        else:
            action_taken = 'stop_ec2_failed'

    # CAS 2 : Laptop DOWN + EC2 Stopped
    # → Start EC2 (failover nécessaire)
    elif not laptop_is_up and ec2_state == 'stopped':
        print("📌 Decision: Laptop is DOWN and EC2 is STOPPED")
        print("💡 Action: Starting EC2 for failover")

        if start_ec2():
            action_taken = 'started_ec2'
        else:
            action_taken = 'start_ec2_failed'

    # CAS 3 : Laptop UP + EC2 Stopped
    # → Rien (état normal)
    elif laptop_is_up and ec2_state == 'stopped':
        print("📌 Decision: Laptop is UP and EC2 is STOPPED")
        print("✅ Action: None (normal state)")
        action_taken = 'none_normal_state'

    # CAS 4 : Laptop DOWN + EC2 Running
    # → Rien (failover déjà actif)
    elif not laptop_is_up and ec2_state == 'running':
        print("📌 Decision: Laptop is DOWN and EC2 is RUNNING")
        print("✅ Action: None (failover already active)")
        action_taken = 'none_failover_active'

    # CAS 5 : États transitoires (pending, stopping, etc.)
    else:
        print(f"⏳ Decision: EC2 is in transitional state '{ec2_state}'")
        print("✅ Action: Waiting for stable state")
        action_taken = 'waiting_transitional_state'

    # ──────────────────────────────────────────────────────────
    # 4. Résumé et retour
    # ──────────────────────────────────────────────────────────

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    result = {
        'timestamp': start_time.isoformat() + 'Z',
        'duration_seconds': duration,
        'laptop_status': 'UP' if laptop_is_up else 'DOWN',
        'ec2_state': ec2_state,
        'action_taken': action_taken
    }

    print(f"📊 Execution summary: {result}")
    print(f"⏱️ Duration: {duration:.2f} seconds")

    return {
        'statusCode': 200,
        'body': result
    }
```

### 🎓 Explication section par section

#### Fonction check_laptop_health()

```python
def check_laptop_health():
    """Vérifie si le laptop est accessible via healthcheck HTTPS."""
    try:
        response = requests.get(
            HEALTHCHECK_URL,
            timeout=HEALTHCHECK_TIMEOUT,
            verify=True
        )

        if response.status_code == 200:
            print(f"✅ Laptop is UP")
            return True
        else:
            print(f"⚠️ Status {response.status_code}")
            return False
```

**🎓 Explication** :

```python
response = requests.get(HEALTHCHECK_URL, timeout=10, verify=True)
# GET https://laptop.ts.net/health
# timeout=10 : Timeout après 10 secondes
# verify=True : Vérifier le certificat TLS (sécurité)
```

**Codes de retour possibles** :

|Code|Signification|Décision|
|---|---|---|
|200|Laptop UP et K3s running|✅ Laptop OK|
|503|Laptop UP mais K3s down|❌ Laptop DOWN|
|Timeout|Laptop éteint ou réseau down|❌ Laptop DOWN|
|Autre erreur|Problème réseau|❌ Laptop DOWN|

---

## 🧪 Tests locaux

### Préparer l'environnement local

```bash
# Créer un virtualenv
cd lambda/watchdog
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install boto3 requests
```

### Créer un script de test

**Créer** : `test_local.py`

```python
"""Script pour tester la Lambda localement."""

import os
from handler import lambda_handler

# Définir les variables d'environnement
os.environ['WORKER_INSTANCE_ID'] = 'i-0123456789abcdef'  # Remplace par ton ID
os.environ['HEALTHCHECK_URL'] = 'https://laptop-thinkpad.tail1234.ts.net/health'

# Créer un event factice
event = {
    "version": "0",
    "id": "test-local",
    "detail-type": "Scheduled Event",
    "source": "aws.events",
    "time": "2025-12-03T15:30:00Z"
}

# Contexte factice
class FakeContext:
    request_id = "test-request-id"

context = FakeContext()

# Exécuter le handler
result = lambda_handler(event, context)

print("\n" + "="*60)
print("RESULT:")
print(result)
print("="*60)
```

### Exécuter le test

```bash
python test_local.py
```

**Output attendu (laptop UP, EC2 stopped)** :

```
⏰ Watchdog execution started at 2025-12-03T15:30:00Z
✅ Laptop is UP - https://laptop.ts.net/health returned 200 OK
📊 EC2 instance i-xxx state: stopped
📌 Decision: Laptop is UP and EC2 is STOPPED
✅ Action: None (normal state)
📊 Execution summary: {'timestamp': '2025-12-03T15:30:00Z', ...}
⏱️ Duration: 0.85 seconds

============================================================
RESULT:
{'statusCode': 200, 'body': {...}}
============================================================
```

---

## 🚀 Déploiement sur AWS

### Via Terraform

**Fichier** : `terraform/aws/lambda.tf`

```hcl
# Archive du code
data "archive_file" "watchdog_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../lambda/watchdog"
  output_path = "${path.module}/watchdog.zip"
}

# Lambda function
resource "aws_lambda_function" "watchdog" {
  filename         = data.archive_file.watchdog_zip.output_path
  function_name    = "k8s-watchdog"
  role            = aws_iam_role.lambda_role.arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.11"
  timeout         = 60
  source_code_hash = data.archive_file.watchdog_zip.output_base64sha256

  environment {
    variables = {
      WORKER_INSTANCE_ID  = aws_instance.k8s_worker.id
      HEALTHCHECK_URL     = var.healthcheck_url  # Ex: https://laptop.ts.net/health
    }
  }
}
```

**Variables Terraform** : Ajouter dans `variables.tf`

```hcl
variable "healthcheck_url" {
  description = "URL du healthcheck Tailscale Funnel"
  type        = string
  # Exemple: https://laptop-thinkpad.tail1234.ts.net/health
}
```

**Déployer** :

```bash
cd terraform/aws

# Plan
terraform plan -var="healthcheck_url=https://laptop-thinkpad.tail1234.ts.net/health"

# Apply
terraform apply -var="healthcheck_url=https://laptop-thinkpad.tail1234.ts.net/health"
```

---

## 📊 Monitoring de la Lambda

### CloudWatch Logs

```bash
# Voir les logs du dernier stream
aws logs tail /aws/lambda/k8s-watchdog --follow
```

**Exemple de logs** :

```
2025-12-03T15:30:00.123Z START RequestId: abc-123
2025-12-03T15:30:00.456Z ⏰ Watchdog execution started
2025-12-03T15:30:00.789Z ✅ Laptop is UP - healthcheck returned 200 OK
2025-12-03T15:30:01.012Z 📊 EC2 instance i-xxx state: stopped
2025-12-03T15:30:01.234Z 📌 Decision: Laptop is UP and EC2 is STOPPED
2025-12-03T15:30:01.456Z ✅ Action: None (normal state)
2025-12-03T15:30:01.678Z ⏱️ Duration: 1.55 seconds
2025-12-03T15:30:01.900Z END RequestId: abc-123
```

---

## 🎉 Félicitations !

Tu as maintenant un **système de failover automatique** :

- ✅ Healthcheck HTTPS via Tailscale Funnel (accessible depuis Lambda)
- ✅ Détection de panne en < 5 minutes
- ✅ Failover automatique vers l'EC2
- ✅ Retour automatique vers le laptop
- ✅ Économie maximale (EC2 arrêté 99% du temps)
- ✅ Haute disponibilité du bot

**Downtime lors d'une panne** : ~5-10 minutes (détection + boot EC2 + redéploiement K3s + ArgoCD)

---

## 📌 Important : ArgoCD sur EC2

**Pour que le failover soit 100% automatique**, tu dois installer ArgoCD sur l'EC2 également (voir [Phase 6 - Configuration pour Failover Automatique](Part_7_Phase_6_GitOps.md#configuration-pour-failover-automatique)).

**Workflow complet lors d'une panne** :

```
1. Laptop s'éteint ❌
   ↓
2. Lambda détecte (< 5 min)
   ↓
3. Lambda démarre EC2
   ↓
4. EC2 boot (2-3 min)
   ↓
5. K3s démarre (systemd)
   ↓
6. ArgoCD démarre sur EC2
   ↓
7. ArgoCD clone le repo Git
   ↓
8. ArgoCD déploie automatiquement le bot
   ↓
9. Bot opérationnel ! ✅
```

**Si ArgoCD n'est pas sur l'EC2** : Tu devras SSH et déployer manuellement avec `kubectl apply` (pas de failover automatique).

**Prochaine étape** : Phase 8 - Tests et validation complète ! ✅

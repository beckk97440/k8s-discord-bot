# ✅ Phase 8 : Tests et Validation Complète

[← Phase 7 - Lambda](Part_8_Phase_7_Lambda.md) | [🎉 Projet terminé !](Part_1_Introduction.md)

---

## 📚 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Checklist de validation](#checklist-de-validation)
3. [Tests infrastructure](#tests-infrastructure)
4. [Tests Kubernetes](#tests-kubernetes)
5. [Tests applicatifs](#tests-applicatifs)
6. [Tests monitoring](#tests-monitoring)
7. [Tests GitOps](#tests-gitops)
8. [Tests failover](#tests-failover)
9. [Tests de charge](#tests-de-charge)
10. [Scénarios de disaster recovery](#sc%C3%A9narios-de-disaster-recovery)
11. [Documentation finale](#documentation-finale)

---

## 🎯 Vue d'ensemble

### Objectif

Valider que **TOUT** fonctionne ensemble :

- ✅ Infrastructure AWS (Terraform)
- ✅ Cluster Kubernetes (laptop + EC2)
- ✅ Application (bot Discord)
- ✅ Monitoring (Prometheus + Grafana)
- ✅ GitOps (ArgoCD)
- ✅ Failover (Lambda Watchdog)

### Approche

```
1. Tests unitaires (chaque composant isolé)
   ↓
2. Tests d'intégration (composants ensemble)
   ↓
3. Tests end-to-end (workflow complet)
   ↓
4. Tests de charge (performance)
   ↓
5. Tests de résilience (pannes)
```

---

## 📋 Checklist de validation

### Infrastructure AWS

- [ ] VPC créé avec CIDR 10.0.0.0/16
- [ ] Subnet public créé
- [ ] Internet Gateway attaché
- [ ] Route table configurée
- [ ] Security Group avec règles correctes
- [ ] EC2 instance créée (t3.micro)
- [ ] IAM roles et policies créés
- [ ] Lambda function déployée
- [ ] EventBridge rule active

### Tailscale

- [ ] Laptop connecté à Tailscale (100.64.1.5)
- [ ] EC2 connecté à Tailscale (100.64.1.x)
- [ ] Ping laptop depuis EC2 fonctionne
- [ ] Ping EC2 depuis laptop fonctionne
- [ ] Mac connecté à Tailscale

### Kubernetes

- [ ] K3s installé sur laptop (control plane + worker)
- [ ] K3s agent installé sur EC2 (worker)
- [ ] 2 nodes visibles : `kubectl get nodes`
- [ ] Tous les nodes Ready
- [ ] kubectl configuré sur Mac

### Application

- [ ] Namespace lol-esports créé
- [ ] SealedSecret créé et déchiffré
- [ ] PVC créé et bound
- [ ] Deployment créé
- [ ] Pod running
- [ ] Bot connecté à Discord
- [ ] Commandes Discord fonctionnent

### Monitoring

- [ ] Namespace monitoring créé
- [ ] Prometheus installé et running
- [ ] Grafana installé et running
- [ ] Node Exporter sur chaque node
- [ ] Kube State Metrics running
- [ ] Dashboards importés
- [ ] Métriques visibles dans Grafana

### GitOps

- [ ] Namespace argocd créé
- [ ] ArgoCD installé et running
- [ ] Application discord-bot créée
- [ ] Sync automatique activé
- [ ] Self-heal activé
- [ ] Prune activé
- [ ] Git repo accessible

### Failover

- [ ] Lambda watchdog déployée
- [ ] EventBridge rule active (5 min)
- [ ] Logs CloudWatch visibles
- [ ] Health check laptop fonctionne
- [ ] Start/Stop EC2 fonctionne

---

## 🏗️ Tests infrastructure

### Test 1 : Vérifier l'infrastructure Terraform

```bash
cd terraform/aws

# Voir l'état
terraform state list

# Devrait lister :
# aws_vpc.k8s_vpc
# aws_subnet.k8s_public_subnet
# aws_internet_gateway.k8s_igw
# aws_route_table.k8s_route_table
# aws_security_group.k8s_sg
# aws_instance.k8s_worker
# aws_iam_role.lambda_role
# aws_iam_policy.lambda_policy
# aws_lambda_function.watchdog
# aws_cloudwatch_event_rule.watchdog_schedule
# etc.
```

**✅ Validation** : Toutes les ressources créées

### Test 2 : Vérifier la connectivité EC2

```bash
# Récupérer l'IP publique
terraform output worker_public_ip

# SSH (via Tailscale de préférence)
ssh ubuntu@$(terraform output -raw worker_public_ip)

# Ou via Tailscale
ssh ubuntu@100.64.1.x  # Remplace par l'IP Tailscale de l'EC2
```

**Dans l'EC2** :

```bash
# Vérifier Tailscale
tailscale status

# Vérifier K3s agent
sudo systemctl status k3s-agent

# Vérifier kubelet
sudo journalctl -u k3s-agent -f
```

**✅ Validation** : SSH fonctionne, services actifs

### Test 3 : Vérifier le réseau Tailscale

```bash
# Depuis le laptop
tailscale ping 100.64.1.x  # IP de l'EC2

# Output attendu :
# pong from ec2-worker (100.64.1.x) via ... in 45ms

# Depuis l'EC2
tailscale ping 100.64.1.5  # IP du laptop

# Output attendu :
# pong from laptop-thinkpad (100.64.1.5) via ... in 10ms
```

**✅ Validation** : Ping bidirectionnel fonctionne

### Test 4 : Vérifier la Lambda

```bash
# Lister les fonctions
aws lambda list-functions --query 'Functions[?FunctionName==`k8s-watchdog`]'

# Invoquer manuellement
aws lambda invoke \
  --function-name k8s-watchdog \
  --payload '{}' \
  response.json

# Voir la réponse
cat response.json

# Voir les logs
aws logs tail /aws/lambda/k8s-watchdog --since 10m
```

**✅ Validation** : Lambda s'exécute sans erreur

---

## ☸️ Tests Kubernetes

### Test 5 : Vérifier le cluster

```bash
# Depuis le Mac (ou laptop)
kubectl get nodes

# Output attendu :
# NAME              STATUS   ROLES                  AGE
# laptop-thinkpad   Ready    control-plane,master   10d
# ip-10-0-1-5       Ready    <none>                 10d

# Voir plus de détails
kubectl get nodes -o wide
```

**✅ Validation** : 2 nodes Ready

### Test 6 : Vérifier les composants système

```bash
# Composants control plane
kubectl get pods -n kube-system

# Devrait montrer :
# coredns-xxx                   Running
# local-path-provisioner-xxx    Running
# metrics-server-xxx            Running
# traefik-xxx (si installé)     Running
```

**✅ Validation** : Tous les pods system Running

### Test 7 : Vérifier les namespaces

```bash
kubectl get namespaces

# Devrait montrer :
# NAME              STATUS
# default           Active
# kube-system       Active
# lol-esports       Active
# monitoring        Active
# argocd            Active
```

**✅ Validation** : Tous les namespaces créés

### Test 8 : Vérifier le storage

```bash
# PVCs
kubectl get pvc --all-namespaces

# Output attendu :
# NAMESPACE      NAME                    STATUS   CAPACITY
# lol-esports    discord-bot-data        Bound    1Gi
# monitoring     prometheus-xxx          Bound    10Gi
# monitoring     grafana-xxx             Bound    5Gi

# PVs
kubectl get pv

# Voir les détails
kubectl describe pvc discord-bot-data -n lol-esports
```

**✅ Validation** : Tous les PVC Bound

### Test 9 : Vérifier les secrets

```bash
# Secrets dans lol-esports
kubectl get secrets -n lol-esports

# Devrait montrer :
# NAME                  TYPE     DATA
# discord-bot-secret    Opaque   2

# Voir les clés (sans les valeurs)
kubectl get secret discord-bot-secret -n lol-esports -o jsonpath='{.data}' | jq 'keys'

# Output : ["DATABASE_URL", "DISCORD_TOKEN"]
```

**✅ Validation** : Secret existe avec les bonnes clés

---

## 🤖 Tests applicatifs

### Test 10 : Vérifier le déploiement du bot

```bash
# Deployment
kubectl get deployment discord-bot -n lol-esports

# Output attendu :
# NAME          READY   UP-TO-DATE   AVAILABLE   AGE
# discord-bot   1/1     1            1           10d

# Pods
kubectl get pods -n lol-esports

# Output attendu :
# NAME                          READY   STATUS    RESTARTS   AGE
# discord-bot-xxx-yyy           1/1     Running   0          5d

# Voir sur quel node
kubectl get pods -n lol-esports -o wide
```

**✅ Validation** : 1/1 pods Running

### Test 11 : Vérifier les logs du bot

```bash
# Logs en temps réel
kubectl logs -f deployment/discord-bot -n lol-esports

# Output attendu :
# <BotUser> has connected to Discord!
# Connected to 1 guilds
```

**✅ Validation** : Bot connecté à Discord

### Test 12 : Tester les commandes Discord

**Dans Discord** :

```
!ping
→ 🏓 Pong! Latency: XXms

!hello
→ Hello @toi! 👋

!info
→ [Embed avec informations du bot]

!matches
→ 🔍 Fetching LoL Esports matches...
→ 📺 Check matches at: https://lolesports.com/schedule
```

**✅ Validation** : Toutes les commandes répondent

### Test 13 : Vérifier la persistence

```bash
# Écrire dans le PVC
kubectl exec deployment/discord-bot -n lol-esports -- \
  sh -c "echo 'Test persistence' > /app/data/test.txt"

# Supprimer le pod (sera recréé)
kubectl delete pod -l app=discord-bot -n lol-esports

# Attendre le nouveau pod
kubectl wait --for=condition=ready pod -l app=discord-bot -n lol-esports --timeout=60s

# Vérifier que le fichier existe toujours
kubectl exec deployment/discord-bot -n lol-esports -- cat /app/data/test.txt

# Output : Test persistence ✅
```

**✅ Validation** : Données persistées après restart

### Test 14 : Vérifier la sécurité (Security Context)

```bash
# Entrer dans le pod
kubectl exec -it deployment/discord-bot -n lol-esports -- /bin/bash

# Vérifier l'utilisateur
whoami
# Output : botuser ✅

id
# Output : uid=1000(botuser) gid=1000(botuser) ✅

# Vérifier que root FS est read-only
touch /test.txt
# Output : touch: cannot touch '/test.txt': Read-only file system ✅

# Mais on peut écrire dans /app/data et /tmp
touch /app/data/test.txt  # ✅
touch /tmp/test.txt       # ✅

exit
```

**✅ Validation** : Security Context appliqué correctement

### Test 15 : Vérifier les resources

```bash
# Utilisation actuelle
kubectl top pod -n lol-esports

# Output :
# NAME                          CPU(cores)   MEMORY(bytes)
# discord-bot-xxx-yyy           45m          120Mi

# Vérifier que c'est dans les limites
kubectl describe pod -l app=discord-bot -n lol-esports | grep -A 5 "Limits:"

# Output :
# Limits:
#   cpu:     200m   ← On est à 45m, OK ✅
#   memory:  256Mi  ← On est à 120Mi, OK ✅
```

**✅ Validation** : Resources dans les limites

---

## 📊 Tests monitoring

### Test 16 : Vérifier Prometheus

```bash
# Port-forward Prometheus
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090 &

# Tester via curl
curl http://localhost:9090/-/healthy

# Output : Prometheus is Healthy. ✅

# Tester une query
curl -s 'http://localhost:9090/api/v1/query?query=up' | jq '.data.result | length'

# Output : Nombre de targets (devrait être > 10)

# Arrêter le port-forward
pkill -f "port-forward.*9090"
```

**✅ Validation** : Prometheus opérationnel

### Test 17 : Vérifier Grafana

```bash
# Port-forward Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80 &

# Ouvrir dans le navigateur
open http://localhost:3000

# Login : admin / admin (ou ton password)
```

**Dans Grafana** :

1. Vérifier la data source Prometheus (vert ✅)
2. Ouvrir un dashboard (ex: "Kubernetes / Compute Resources / Cluster")
3. Vérifier que les graphiques se chargent

**✅ Validation** : Grafana affiche les métriques

### Test 18 : Tester les dashboards personnalisés

**Ouvrir le dashboard "Discord Bot Monitoring"** (créé en Phase 5)

**Vérifier** :

- Panel "CPU Usage" : Affiche la courbe CPU du bot
- Panel "Memory Usage" : Affiche la courbe RAM du bot
- Panel "Restarts" : Affiche 0 (si pas de restart)
- Panel "Nodes Status" : Affiche 2 nodes Ready

**✅ Validation** : Dashboard fonctionne

### Test 19 : Tester une query PromQL

**Dans Grafana → Explore** :

```promql
# CPU du bot
rate(container_cpu_usage_seconds_total{namespace="lol-esports", pod=~"discord-bot.*"}[5m]) * 100

# RAM du bot
container_memory_usage_bytes{namespace="lol-esports", pod=~"discord-bot.*"}

# Nodes Ready
count(kube_node_status_condition{condition="Ready", status="true"})
```

**✅ Validation** : Queries retournent des données

---

## 🔄 Tests GitOps

### Test 20 : Vérifier ArgoCD

```bash
# Port-forward ArgoCD
kubectl port-forward -n argocd svc/argocd-server 8080:443 &

# Ouvrir dans le navigateur
open https://localhost:8080

# Login : admin / [password récupéré]
```

**Dans ArgoCD UI** :

1. Application **discord-bot** visible
2. Status : **Synced** ✅
3. Health : **Healthy** ✅

**✅ Validation** : ArgoCD opérationnel

### Test 21 : Tester le workflow GitOps

**Étape 1 : Modifier un YAML dans Git**

```bash
cd lol-esports-k8s-manifests

# Modifier le deployment (ex: changer l'image ou un label)
vim k8s/apps/discord-bot/deployment.yaml

# Ajouter un label test
metadata:
  labels:
    test: "gitops-validation"

# Commit et push
git add k8s/apps/discord-bot/deployment.yaml
git commit -m "test: Add test label"
git push origin main
```

**Étape 2 : Observer ArgoCD**

```bash
# Attendre < 3 minutes

# Vérifier le status
argocd app get discord-bot

# Devrait montrer :
# Sync Status:  OutOfSync → puis Synced
```

**Étape 3 : Vérifier dans le cluster**

```bash
kubectl get deployment discord-bot -n lol-esports -o yaml | grep "test:"

# Output : test: gitops-validation ✅
```

**✅ Validation** : GitOps fonctionne automatiquement

### Test 22 : Tester le rollback Git

```bash
# Revert le commit
git revert HEAD
git push origin main

# Attendre < 3 minutes

# Vérifier que le label a disparu
kubectl get deployment discord-bot -n lol-esports -o yaml | grep "test:"

# Output : (vide) ✅
```

**✅ Validation** : Rollback Git fonctionne

### Test 23 : Tester self-heal

```bash
# Modifier manuellement le cluster
kubectl scale deployment discord-bot --replicas=3 -n lol-esports

# Vérifier
kubectl get deployment discord-bot -n lol-esports
# READY: 3/3 ⚠️

# Attendre 30 secondes (reconciliation ArgoCD)

# Vérifier à nouveau
kubectl get deployment discord-bot -n lol-esports
# READY: 1/1 ✅ (corrigé automatiquement)
```

**✅ Validation** : Self-heal fonctionne

---

## 🔄 Tests failover

### Test 24 : Tester la détection du laptop UP

```bash
# Vérifier que le laptop est UP
kubectl get nodes

# NAME              STATUS
# laptop-thinkpad   Ready    ✅

# Forcer une exécution de la Lambda
aws lambda invoke \
  --function-name k8s-watchdog \
  --payload '{}' \
  response.json

# Voir les logs
aws logs tail /aws/lambda/k8s-watchdog --since 1m

# Devrait montrer :
# ✅ Laptop 100.64.1.5 is UP
# 📊 EC2 instance xxx state: stopped
# ✅ Action: None (normal state)
```

**✅ Validation** : Laptop détecté UP

### Test 25 : Simuler laptop DOWN

**Étape 1 : Arrêter K3s sur le laptop**

```bash
# Sur le laptop
sudo systemctl stop k3s
```

**Étape 2 : Attendre 5 minutes** (prochain trigger Lambda)

**Étape 3 : Observer les logs Lambda**

```bash
aws logs tail /aws/lambda/k8s-watchdog --follow

# Output attendu :
# ❌ Laptop 100.64.1.5 is DOWN
# 📊 EC2 instance xxx state: stopped
# 📌 Decision: Laptop is DOWN and EC2 is STOPPED
# 💡 Action: Starting EC2 for failover
# 🚀 Starting EC2 instance xxx...
# ✅ EC2 instance start initiated. Current state: pending
```

**Étape 4 : Vérifier l'EC2**

```bash
# Attendre ~1 minute

aws ec2 describe-instances \
  --instance-ids i-xxx \
  --query 'Reservations[0].Instances[0].State.Name'

# Output : running ✅
```

**Étape 5 : Vérifier les nodes Kubernetes**

```bash
kubectl get nodes

# Output :
# NAME              STATUS     ROLES
# laptop-thinkpad   NotReady   control-plane  ← Laptop down
# ip-10-0-1-5       Ready      <none>         ← EC2 up ✅
```

**Étape 6 : Vérifier le pod**

```bash
kubectl get pods -n lol-esports -o wide

# Output :
# NAME                          NODE            STATUS
# discord-bot-xxx-zzz           ip-10-0-1-5     Running  ← Migré sur EC2 ✅
```

**Étape 7 : Vérifier que le bot fonctionne**

Dans Discord :

```
!ping
→ 🏓 Pong! Latency: XXms  ✅ (bot toujours opérationnel)
```

**✅ Validation** : Failover automatique fonctionne !

### Test 26 : Retour à la normale

**Étape 1 : Redémarrer K3s sur le laptop**

```bash
# Sur le laptop
sudo systemctl start k3s
```

**Étape 2 : Attendre que le laptop revienne**

```bash
kubectl get nodes

# Output :
# NAME              STATUS   ROLES
# laptop-thinkpad   Ready    control-plane  ← Laptop back ✅
# ip-10-0-1-5       Ready    <none>
```

**Étape 3 : Attendre 5 minutes** (prochain trigger Lambda)

**Étape 4 : Observer les logs Lambda**

```bash
aws logs tail /aws/lambda/k8s-watchdog --follow

# Output attendu :
# ✅ Laptop 100.64.1.5 is UP
# 📊 EC2 instance xxx state: running
# 📌 Decision: Laptop is UP and EC2 is RUNNING
# 💡 Action: Stopping EC2 to save costs
# 🛑 Stopping EC2 instance xxx...
# ✅ EC2 instance stop initiated. Current state: stopping
```

**Étape 5 : Vérifier l'EC2**

```bash
aws ec2 describe-instances \
  --instance-ids i-xxx \
  --query 'Reservations[0].Instances[0].State.Name'

# Output : stopped ✅
```

**Étape 6 : Vérifier le pod**

```bash
kubectl get pods -n lol-esports -o wide

# Output :
# NAME                          NODE              STATUS
# discord-bot-xxx-aaa           laptop-thinkpad   Running  ← Revenu sur laptop ✅
```

**✅ Validation** : Retour automatique fonctionne !

---

## 🏋️ Tests de charge

### Test 27 : Stress test CPU

```bash
# Installer stress dans le pod
kubectl exec -it deployment/discord-bot -n lol-esports -- bash

# Dans le pod
apt-get update && apt-get install -y stress

# Stresser 1 CPU pendant 60 secondes
stress --cpu 1 --timeout 60s

# Dans un autre terminal, observer
kubectl top pod -n lol-esports --watch
```

**Vérifier dans Grafana** : CPU spike visible dans le dashboard

**✅ Validation** : Métriques remontent correctement

### Test 28 : Stress test mémoire

```bash
# Dans le pod
stress --vm 1 --vm-bytes 100M --timeout 60s

# Observer
kubectl top pod -n lol-esports --watch
```

**Vérifier** : Memory usage monte puis redescend

**✅ Validation** : Memory monitoring fonctionne

### Test 29 : Vérifier les limits

```bash
# Essayer de dépasser la limite mémoire (256Mi)
kubectl exec -it deployment/discord-bot -n lol-esports -- bash

# Dans le pod
stress --vm 1 --vm-bytes 300M --timeout 60s

# Le pod devrait être OOMKilled si > 256Mi
```

**Observer** :

```bash
kubectl get pods -n lol-esports --watch

# Si OOMKilled :
# NAME                          READY   STATUS      RESTARTS
# discord-bot-xxx-yyy           0/1     OOMKilled   0
# discord-bot-xxx-yyy           1/1     Running     1  ← Redémarré automatiquement
```

**✅ Validation** : Limits respectées, auto-restart fonctionne

---

## 🔥 Scénarios de disaster recovery

### Scénario 1 : Perte complète du laptop

**Simulation** :

```bash
# Sur le laptop
sudo shutdown now
```

**Timeline** :

```
T+0min    : Laptop s'éteint
T+5min    : Lambda détecte laptop DOWN
T+5min    : Lambda démarre l'EC2
T+6min    : EC2 running, rejoint le cluster
T+7min    : Pod migré sur EC2
T+7min    : Bot opérationnel sur EC2 ✅
```

**Vérification** :

- Bot toujours accessible sur Discord
- Logs CloudWatch montrent le failover
- Grafana montre le node change

**✅ Validation** : Recovery automatique en < 10 minutes

### Scénario 2 : Corruption du PVC

**Simulation** :

```bash
# Supprimer le PVC
kubectl delete pvc discord-bot-data -n lol-esports

# Le pod crashloop (plus de volume)
kubectl get pods -n lol-esports

# Output :
# NAME                          STATUS
# discord-bot-xxx-yyy           CrashLoopBackOff
```

**Recovery** :

```bash
# Recréer le PVC via ArgoCD
argocd app sync discord-bot

# Ou manuellement
kubectl apply -f k8s/apps/discord-bot/pvc.yaml

# Le deployment recréera le pod automatiquement
kubectl delete pod -l app=discord-bot -n lol-esports
```

**✅ Validation** : Recovery manuel possible

### Scénario 3 : Suppression accidentelle du namespace

**Simulation** :

```bash
# Supprimer le namespace (ATTENTION : destructif)
kubectl delete namespace lol-esports
```

**Recovery** :

```bash
# Via ArgoCD (self-heal)
# ArgoCD détecte que tout a disparu et recrée automatiquement ! ✅

# Ou manuellement
kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f k8s/apps/discord-bot/
```

**✅ Validation** : ArgoCD self-heal protège contre les suppressions

### Scénario 4 : Perte du control plane

**Problème** : Si le laptop (control plane) est down trop longtemps

**Limitations K3s** :

- EC2 est un worker, pas un control plane
- Sans control plane, impossible de créer/modifier des ressources
- Les pods existants continuent de tourner ✅

**Solution long terme** :

- Convertir l'EC2 en control plane aussi (HA)
- Ou utiliser un managed Kubernetes (EKS)

**Pour notre projet** : Acceptable (laptop down rarement > 24h)

---

## 📚 Documentation finale

### Architecture complète

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE COMPLÈTE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    LAPTOP (STANDALONE K3S)               │   │
│  │  ──────────────────────────────────────────────────────  │   │
│  │  • Arch Linux                                            │   │
│  │  • K3s server standalone                                 │   │
│  │  • Discord Bot + Healthcheck HTTP server                 │   │
│  │  • Tailscale Funnel (healthcheck HTTPS public)           │   │
│  │  • Running 24/7 (lid closed)                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                       │
│                           │ Tailscale Funnel HTTPS                │
│                           │                                       │
│  ┌────────────────────────┴──────────────────────────────────┐  │
│  │                                                             │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │      AWS EC2 (STANDALONE K3S BACKUP)                 │ │  │
│  │  │  ──────────────────────────────────────────────────  │ │  │
│  │  │  • Ubuntu 22.04                                      │ │  │
│  │  │  • K3s server standalone                             │ │  │
│  │  │  • ArgoCD (auto-redeploy bot)                        │ │  │
│  │  │  • t3.micro (stopped 99% of time)                    │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  │                                                             │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │          LAMBDA WATCHDOG                             │ │  │
│  │  │  ──────────────────────────────────────────────────  │ │  │
│  │  │  • Python 3.11                                       │ │  │
│  │  │  • Health check laptop (HTTPS via Funnel)            │ │  │
│  │  │  • Start/Stop EC2 (failover)                         │ │  │
│  │  │  • EventBridge trigger (5 min)                       │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  │                                                             │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │            DEUX CLUSTERS K3S INDÉPENDANTS                │   │
│  │  ──────────────────────────────────────────────────────  │   │
│  │                                                            │   │
│  │  Namespace: lol-esports                                   │   │
│  │  ├── Discord Bot (Deployment)                             │   │
│  │  │   ├── PVC (1Gi)                                        │   │
│  │  │   ├── SealedSecret (chiffré)                           │   │
│  │  │   └── Security Context (non-root)                      │   │
│  │  └── ResourceQuota                                        │   │
│  │                                                            │   │
│  │  Namespace: monitoring                                     │   │
│  │  ├── Prometheus (StatefulSet, 10Gi)                       │   │
│  │  ├── Grafana (Deployment, 5Gi)                            │   │
│  │  ├── Node Exporter (DaemonSet)                            │   │
│  │  └── Kube State Metrics (Deployment)                      │   │
│  │                                                            │   │
│  │  Namespace: argocd                                         │   │
│  │  ├── ArgoCD Server                                        │   │
│  │  ├── ArgoCD Repo Server                                   │   │
│  │  ├── ArgoCD Application Controller                        │   │
│  │  └── Application: discord-bot (auto-sync)                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    GIT REPOSITORY                         │   │
│  │  ──────────────────────────────────────────────────────  │   │
│  │  GitHub: lol-esports-k8s-manifests                        │   │
│  │  ├── k8s/base/                                            │   │
│  │  │   ├── namespace.yaml                                   │   │
│  │  │   └── resource-quota.yaml                              │   │
│  │  └── k8s/apps/discord-bot/                                │   │
│  │      ├── sealed-secret.yaml ✅ Commitable                 │   │
│  │      ├── pvc.yaml                                         │   │
│  │      └── deployment.yaml                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                       MAC (GESTION)                       │   │
│  │  ──────────────────────────────────────────────────────  │   │
│  │  • kubectl (contrôle cluster)                             │   │
│  │  • Terraform (infra AWS)                                  │   │
│  │  • Helm (déploiements)                                    │   │
│  │  • Git (GitOps)                                           │   │
│  │  • Port-forward (Grafana, ArgoCD)                         │   │
│  │  • Tailscale (100.64.1.20)                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### Flux de données

```
1. DÉVELOPPEMENT
   Git commit → GitHub → ArgoCD sync → Cluster update

2. MONITORING
   Pods → Prometheus scrape → Grafana visualize

3. FAILOVER
   EventBridge → Lambda check laptop → Start/Stop EC2

4. APPLICATION
   Discord user → Discord API → Bot pod → Response
```

### Technologies utilisées

|Catégorie|Technologies|
|---|---|
|**Infrastructure**|AWS (VPC, EC2, Lambda, EventBridge, CloudWatch), Terraform|
|**Networking**|Tailscale VPN|
|**Kubernetes**|K3s (lightweight K8s), kubectl, Helm|
|**Storage**|PersistentVolumes (local-path provisioner)|
|**Security**|SealedSecrets, Security Context, IAM Roles|
|**Monitoring**|Prometheus, Grafana, Node Exporter, Kube State Metrics|
|**GitOps**|ArgoCD, Git (GitHub)|
|**Application**|Discord Bot (Python), Docker|
|**Automation**|Lambda (Python), boto3|

### Coûts mensuels

|Service|Coût|
|---|---|
|EC2 t3.micro (stopped 99%)|~€0.88/mois (EBS storage)|
|EC2 t3.micro (running 1%)|~€0.02/mois|
|Lambda|€0 (free tier)|
|Data transfer|~€0.01/mois|
|**Total**|**~€0.10/mois** 🎉|

### Compétences démontrées

**Pour le portfolio** :

✅ **Infrastructure as Code** (Terraform)  
✅ **Container orchestration** (Kubernetes/K3s)  
✅ **GitOps** (ArgoCD)  
✅ **Monitoring** (Prometheus/Grafana)  
✅ **Security** (Sealed Secrets, non-root containers, IAM)  
✅ **Serverless** (AWS Lambda)  
✅ **High availability** (Failover automatique)  
✅ **Cost optimization** (EC2 stopped when not needed)  
✅ **Networking** (VPN mesh Tailscale)  
✅ **Python** (Lambda watchdog, Bot Discord)

---

## 📝 Checklist finale

### Avant de considérer le projet terminé

- [ ] Tous les tests de cette phase réussis
- [ ] Documentation complète écrite
- [ ] Diagrammes d'architecture créés
- [ ] README.md dans le repo Git
- [ ] Screenshots des dashboards Grafana
- [ ] Screenshots de l'interface ArgoCD
- [ ] Vidéo démo du failover (optionnel)
- [ ] Présentation du projet préparée (pour entretiens)

### Améliorations futures (optionnel)

- [ ] Convertir EC2 en control plane (HA multi-master)
- [ ] Ajouter un 3ème node (Raspberry Pi)
- [ ] Implémenter Horizontal Pod Autoscaler (HPA)
- [ ] Ajouter un Ingress Controller (pour exposer des services HTTP)
- [ ] Migrer vers un managed K8s (EKS, GKE) pour comparer
- [ ] Ajouter des tests automatisés (CI/CD)
- [ ] Implémenter Vault pour les secrets
- [ ] Ajouter Loki pour les logs agrégés
- [ ] Implémenter Cert-Manager pour les certificats TLS

---

## 🎉 Félicitations !

Tu as créé et validé un **système complet production-ready** :

✅ **Infrastructure** : Terraform, AWS, Tailscale  
✅ **Kubernetes** : Cluster hybrid cloud (laptop + EC2)  
✅ **Application** : Bot Discord containerisé et déployé  
✅ **Monitoring** : Prometheus + Grafana avec dashboards  
✅ **GitOps** : ArgoCD avec auto-sync et self-heal  
✅ **Failover** : Lambda watchdog automatique  
✅ **Tests** : Validés de bout en bout

**Ton projet est un excellent showcase pour :**

- Entretiens DevOps/SRE
- Portfolio GitHub
- Discussions techniques
- Démonstration de compétences multiples

**🚀 Prochaine étape :** Utiliser ce projet dans tes candidatures ! Ce projet démontre une expertise réelle en infrastructure moderne.

---

## 📄 Annexes

### Commandes de dépannage rapide

```bash
# Cluster
kubectl get all --all-namespaces
kubectl get nodes -o wide
kubectl top nodes

# Application
kubectl logs -f deployment/discord-bot -n lol-esports
kubectl describe pod -l app=discord-bot -n lol-esports
kubectl get events -n lol-esports --sort-by='.lastTimestamp'

# Monitoring
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# GitOps
kubectl port-forward -n argocd svc/argocd-server 8080:443
argocd app list
argocd app sync discord-bot

# Lambda
aws lambda invoke --function-name k8s-watchdog --payload '{}' response.json
aws logs tail /aws/lambda/k8s-watchdog --follow

# Infrastructure
terraform state list
terraform plan
terraform output
```

### Ressources utiles

- **Kubernetes** : https://kubernetes.io/docs/
- **K3s** : https://docs.k3s.io/
- **ArgoCD** : https://argo-cd.readthedocs.io/
- **Prometheus** : https://prometheus.io/docs/
- **Grafana** : https://grafana.com/docs/
- **Terraform** : https://www.terraform.io/docs/
- **Tailscale** : https://tailscale.com/kb/
- **AWS Lambda** : https://docs.aws.amazon.com/lambda/

### Template README pour le repo

```markdown
# 🎮 LoL Esports Discord Bot - Hybrid Cloud Kubernetes

Production-grade Discord bot deployment on a hybrid cloud Kubernetes cluster (laptop + AWS EC2) with automatic failover, GitOps, and comprehensive monitoring.

## 🏗️ Architecture

- **Control Plane**: Laptop (Arch Linux, K3s server)
- **Worker Nodes**: Laptop + AWS EC2 (t3.micro)
- **Networking**: Tailscale VPN mesh
- **GitOps**: ArgoCD (auto-sync, self-heal)
- **Monitoring**: Prometheus + Grafana
- **Failover**: AWS Lambda watchdog (5-minute health checks)

## 🚀 Features

- ✅ Infrastructure as Code (Terraform)
- ✅ GitOps deployment (ArgoCD)
- ✅ Automatic failover (laptop → EC2)
- ✅ Cost-optimized (EC2 stopped 99% of time)
- ✅ Production-grade security (Sealed Secrets, non-root containers)
- ✅ Full monitoring stack (Prometheus/Grafana)

## 💰 Cost

~€0.10/month (EC2 storage + minimal compute)

## 📚 Documentation

See [docs/](docs/) for detailed guides:
- [Phase 1-2: Prerequisites & AWS Infrastructure](docs/phase-1-2-infrastructure.md)
- [Phase 3: Docker Containerization](docs/phase-3-docker.md)
- [Phase 4: Kubernetes Deployments](docs/phase-4-kubernetes.md)
- [Phase 5: Monitoring](docs/phase-5-monitoring.md)
- [Phase 6: GitOps](docs/phase-6-gitops.md)
- [Phase 7: Lambda Watchdog](docs/phase-7-lambda.md)
- [Phase 8: Testing & Validation](docs/phase-8-testing.md)

## 🛠️ Tech Stack

Kubernetes, K3s, Terraform, AWS (EC2, Lambda, VPC), Docker, ArgoCD, Prometheus, Grafana, Helm, Tailscale, Python, Discord.py

## 📊 Dashboards

- Grafana: `http://localhost:3000` (port-forward)
- ArgoCD: `https://localhost:8080` (port-forward)
- Prometheus: `http://localhost:9090` (port-forward)

## 🤝 Contributing

This is a portfolio project, but suggestions are welcome via issues!

## 📄 License

MIT
```

---

**🎊 C'est terminé ! Tu as maintenant un guide complet de A à Z avec tous les tests et validations. Bon courage pour la mise en pratique ! 🚀**

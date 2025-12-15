# 📊 Phase 5 : Monitoring avec Prometheus et Grafana

[← Phase 4 - Kubernetes](Part_5_Phase_4_Kubernetes.md) | [Phase 6 - GitOps →](Part_7_Phase_6_GitOps.md)

---

## 📚 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Comprendre Prometheus](#comprendre-prometheus)
3. [Comprendre Grafana](#comprendre-grafana)
4. [Comprendre Helm](#comprendre-helm)
5. [Installation du stack Prometheus](#installation-prometheus)
6. [Accéder à Grafana](#acc%C3%A9der-%C3%A0-grafana)
7. [Créer des dashboards personnalisés](#dashboards-personnalis%C3%A9s)
8. [Queries PromQL essentielles](#queries-promql)
9. [Alerting (optionnel)](#alerting)
10. [Troubleshooting](#troubleshooting)

---

## 🎯 Vue d'ensemble

### Pourquoi du monitoring ?

**Sans monitoring** :

- ❌ Ton bot crash → Tu ne le sais pas
- ❌ CPU à 100% → Tu ne sais pas pourquoi
- ❌ Mémoire qui fuit → Découvert trop tard
- ❌ Laptop down → Tu ne sais pas quand

**Avec monitoring** :

- ✅ Dashboard en temps réel
- ✅ Alertes si problème
- ✅ Historique des métriques
- ✅ Debugging facilité

### Qu'est-ce qu'on va installer ?

**Stack Prometheus complet** (via Helm) :

- 📊 **Prometheus** : Collecte et stocke les métriques
- 📈 **Grafana** : Visualise les métriques (dashboards)
- 🔍 **Node Exporter** : Métriques système (CPU, RAM, disk)
- 📡 **Kube State Metrics** : Métriques Kubernetes (pods, deployments)
- ⚠️ **Alertmanager** : Gestion des alertes (optionnel)

### Architecture du monitoring

```
┌─────────────────────────────────────────────────────────────┐
│                    CLUSTER KUBERNETES                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                     │
│  │ Discord Bot  │      │ Node Exporter│                     │
│  │              │      │ (DaemonSet)  │                     │
│  └──────┬───────┘      └──────┬───────┘                     │
│         │                     │                              │
│         │ Scrape              │ Scrape                       │
│         │ (toutes les 15s)    │ (toutes les 15s)            │
│         ▼                     ▼                              │
│  ┌─────────────────────────────────────┐                    │
│  │         PROMETHEUS                  │                    │
│  │  ─────────────────────────────────  │                    │
│  │  • Collecte métriques               │                    │
│  │  • Stocke time-series               │                    │
│  │  • Évalue les alertes               │                    │
│  │  • Expose API /api/v1/query         │                    │
│  └────────────┬────────────────────────┘                    │
│               │                                              │
│               │ Query API                                    │
│               ▼                                              │
│  ┌─────────────────────────────────────┐                    │
│  │          GRAFANA                    │                    │
│  │  ─────────────────────────────────  │                    │
│  │  • Dashboards interactifs           │                    │
│  │  • Graphiques temps réel            │                    │
│  │  • Alertes visuelles                │                    │
│  │  • Interface web :3000              │                    │
│  └─────────────────────────────────────┘                    │
│                                                               │
└───────────────────────────────────────────────────────────────┘
          │
          │ kubectl port-forward
          â–¼
    ┌─────────────┐
    │  TON MAC    │
    │  localhost  │
    │  :3000      │
    └─────────────┘
```

---

## 📊 Comprendre Prometheus

### Qu'est-ce que Prometheus ?

**Prometheus** = Système de monitoring et alerting open-source

**Créé par** : SoundCloud (2012), maintenant projet CNCF

**Spécialité** : Time-series database (données avec timestamps)

### Concepts clés

#### 1. Métriques (Metrics)

**Métrique** = Mesure d'une valeur au fil du temps

Exemples :

- `cpu_usage` : Utilisation CPU (%)
- `memory_bytes` : Mémoire utilisée (bytes)
- `http_requests_total` : Nombre de requêtes HTTP

**Format** :

```
nom_metrique{label1="valeur1", label2="valeur2"} valeur timestamp
```

Exemple réel :

```
container_memory_usage_bytes{namespace="lol-esports", pod="discord-bot-abc123"} 134217728 1704067200
```

**🎓 Décomposition** :

```
container_memory_usage_bytes     ← Nom de la métrique
{                                ← Labels (filtres)
  namespace="lol-esports",
  pod="discord-bot-abc123"
}
134217728                        ← Valeur (128 MB en bytes)
1704067200                       ← Timestamp Unix
```

#### 2. Labels

**Labels** = Tags pour filtrer et grouper les métriques

```promql
# Métrique sans label
cpu_usage 45

# Métrique avec labels
cpu_usage{instance="node1", job="kubernetes"} 45
cpu_usage{instance="node2", job="kubernetes"} 78
```

**Avantages** :

- Filtrage précis : `cpu_usage{instance="node1"}`
- Agrégation : `sum by (instance) (cpu_usage)`
- Multi-dimensionnel : Plusieurs labels par métrique

#### 3. Types de métriques

|Type|Description|Exemple|
|---|---|---|
|**Counter**|Valeur qui ne fait qu'augmenter|Nombre de requêtes HTTP total|
|**Gauge**|Valeur qui peut monter et descendre|Utilisation CPU actuelle|
|**Histogram**|Distribution de valeurs|Latence des requêtes (buckets)|
|**Summary**|Comme histogram mais calcule percentiles|Latence P50, P95, P99|

**Exemples** :

```promql
# Counter
http_requests_total{method="GET", status="200"} 1547

# Gauge
memory_usage_bytes{pod="discord-bot"} 134217728

# Histogram
http_request_duration_seconds_bucket{le="0.1"} 95
http_request_duration_seconds_bucket{le="0.5"} 120
http_request_duration_seconds_bucket{le="1.0"} 124

# Summary
http_request_duration_seconds{quantile="0.5"} 0.23
http_request_duration_seconds{quantile="0.9"} 0.87
http_request_duration_seconds{quantile="0.99"} 1.2
```

#### 4. Scraping

**Scraping** = Prometheus récupère les métriques en pull (pas push)

```
Prometheus ─────GET /metrics────► Application
           ◄────métriques────────
```

**Pourquoi pull et pas push ?**

|Pull (Prometheus)|Push (alternatives)|
|---|---|
|✅ Contrôle centralisé|❌ Apps doivent connaitre le serveur|
|✅ Service discovery automatique|❌ Config sur chaque app|
|✅ Détection de pannes (target down)|❌ Difficile de détecter les pannes|

**Endpoint `/metrics`** :

Prometheus scrape un endpoint HTTP qui expose les métriques :

```
GET http://discord-bot:8080/metrics

# HELP memory_usage_bytes Current memory usage
# TYPE memory_usage_bytes gauge
memory_usage_bytes{pod="discord-bot"} 134217728

# HELP cpu_usage_percent Current CPU usage
# TYPE cpu_usage_percent gauge
cpu_usage_percent{pod="discord-bot"} 23.5
```

**Notre cas** : On n'expose pas de métriques custom du bot (pour l'instant) Mais Kubernetes expose automatiquement des métriques pour nous !

#### 5. Time-Series Database

**Time-series** = Données indexées par temps

```
timestamp     metric                              value
1704067200    cpu_usage{pod="bot"}               45
1704067215    cpu_usage{pod="bot"}               48
1704067230    cpu_usage{pod="bot"}               52
```

**Prometheus stocke** :

- Par défaut : 15 jours de rétention
- Format : Efficace (compression)
- Queries : Très rapides

---

## 📈 Comprendre Grafana

### Qu'est-ce que Grafana ?

**Grafana** = Plateforme de visualisation et analytics

**Fonctionnalités** :

- 📊 Dashboards interactifs
- 📈 Graphiques multiples (lignes, barres, jauges, etc.)
- 🔍 Exploration des données
- ⚠️ Alertes visuelles
- 👥 Gestion des utilisateurs

### Concepts clés

#### 1. Data Source

**Data Source** = Source de données (Prometheus, InfluxDB, etc.)

Grafana se connecte à Prometheus via son API :

```
Grafana ─────Query PromQL────► Prometheus
        ◄────Données JSON─────
```

#### 2. Dashboard

**Dashboard** = Collection de panels (graphiques)

Exemple de structure :

```
Dashboard: "Cluster Overview"
├── Row: "Nodes"
│   ├── Panel: "CPU Usage"
│   └── Panel: "Memory Usage"
└── Row: "Applications"
    ├── Panel: "Discord Bot CPU"
    └── Panel: "Discord Bot Memory"
```

#### 3. Panel

**Panel** = Un graphique individuel

Types de panels :

- **Graph** : Ligne ou barres
- **Stat** : Valeur unique grande
- **Gauge** : Jauge (0-100%)
- **Table** : Tableau de données
- **Heatmap** : Carte de chaleur

#### 4. Variables

**Variables** = Paramètres dynamiques dans les dashboards

Exemple :

```
Variable: $namespace
Values: ["lol-esports", "kube-system", "monitoring"]

Query: container_memory_usage_bytes{namespace="$namespace"}
```

L'utilisateur peut changer le namespace dans un dropdown !

---

## 🎩 Comprendre Helm

### Qu'est-ce que Helm ?

**Helm** = Package manager pour Kubernetes

**Analogie** :

- **apt/yum** pour Linux
- **npm** pour Node.js
- **pip** pour Python
- **Helm** pour Kubernetes

### Pourquoi Helm ?

**Sans Helm** :

Tu dois créer manuellement 50+ fichiers YAML :

- Deployments pour Prometheus, Grafana, Alertmanager
- Services, ConfigMaps, Secrets
- RBAC (ServiceAccounts, Roles, RoleBindings)
- PVCs pour le storage
- Et tout configurer...

❌ Complexe, long, erreurs fréquentes

**Avec Helm** :

```bash
helm install prometheus prometheus-community/kube-prometheus-stack
```

✅ Tout est créé automatiquement avec les best practices !

### Concepts Helm

#### 1. Chart

**Chart** = Package (comme un .deb ou .rpm)

Structure d'un chart :

```
mon-chart/
├── Chart.yaml          # Métadonnées (nom, version)
├── values.yaml         # Configuration par défaut
├── templates/          # Templates YAML
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
└── charts/             # Dépendances (autres charts)
```

#### 2. Repository

**Repository** = Collection de charts (comme npm registry)

Repositories populaires :

- **stable** : Charts officiels Helm (deprecated)
- **bitnami** : Charts maintenus par Bitnami
- **prometheus-community** : Charts Prometheus
- **grafana** : Charts Grafana

#### 3. Release

**Release** = Instance d'un chart déployé

```bash
# Installer un chart = créer une release
helm install mon-release mon-chart

# Tu peux avoir plusieurs releases du même chart
helm install prometheus-prod prometheus-community/prometheus
helm install prometheus-staging prometheus-community/prometheus
```

#### 4. Values

**Values** = Configuration d'un chart

**values.yaml** (défaut dans le chart) :

```yaml
replicaCount: 1
image:
  repository: nginx
  tag: "1.19"
service:
  type: ClusterIP
  port: 80
```

**Tu peux override** :

```bash
# Via CLI
helm install my-release my-chart --set replicaCount=3

# Via fichier
helm install my-release my-chart -f custom-values.yaml
```

**custom-values.yaml** :

```yaml
replicaCount: 3
service:
  type: LoadBalancer
```

**Résultat** : Merge avec les valeurs par défaut

```yaml
replicaCount: 3           # ← Overridden
image:
  repository: nginx       # ← Défaut
  tag: "1.19"            # ← Défaut
service:
  type: LoadBalancer      # ← Overridden
  port: 80               # ← Défaut
```

#### 5. Templates

**Templates** = YAML avec variables Go template

**Exemple** : `templates/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-deployment
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    spec:
      containers:
      - name: {{ .Chart.Name }}
        image: {{ .Values.image.repository }}:{{ .Values.image.tag }}
```

**Avec values.yaml** :

```yaml
replicaCount: 3
image:
  repository: nginx
  tag: "1.19"
```

**Résultat après templating** :

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-release-deployment
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: my-chart
        image: nginx:1.19
```

**🔍 Variables disponibles** :

|Variable|Description|
|---|---|
|`.Values.*`|Valeurs du values.yaml|
|`.Release.Name`|Nom de la release|
|`.Release.Namespace`|Namespace|
|`.Chart.Name`|Nom du chart|
|`.Chart.Version`|Version du chart|

### Commandes Helm essentielles

```bash
# Ajouter un repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

# Mettre à jour les repos
helm repo update

# Chercher un chart
helm search repo prometheus

# Voir les values par défaut
helm show values prometheus-community/kube-prometheus-stack

# Installer un chart
helm install my-release my-chart

# Lister les releases
helm list

# Upgrader une release
helm upgrade my-release my-chart

# Rollback
helm rollback my-release 1

# Désinstaller
helm uninstall my-release
```

---

## 🚀 Installation du stack Prometheus

### Ajouter le repo Helm

```bash
# Ajouter le repo prometheus-community
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

# Mettre à jour
helm repo update

# Vérifier
helm search repo prometheus
```

**🎓 Output** :

```
NAME                                                    CHART VERSION   APP VERSION
prometheus-community/kube-prometheus-stack              55.5.0          v0.70.0
prometheus-community/prometheus                         25.8.0          v2.48.0
prometheus-community/prometheus-adapter                 4.9.0           v0.11.2
...
```

**On va utiliser** : `kube-prometheus-stack`

**Pourquoi ?** Ce chart inclut TOUT :

- ✅ Prometheus
- ✅ Grafana
- ✅ Alertmanager
- ✅ Node Exporter
- ✅ Kube State Metrics
- ✅ Prometheus Operator

### Voir les values par défaut

```bash
helm show values prometheus-community/kube-prometheus-stack > default-values.yaml
```

**Ce fichier fait 3000+ lignes !** Beaucoup d'options.

### Créer notre fichier de configuration

**Créer** : `prometheus-values.yaml`

```yaml
# ══════════════════════════════════════════════════════════════
# PROMETHEUS CONFIGURATION
# ══════════════════════════════════════════════════════════════

prometheus:
  prometheusSpec:
    # Rétention des données
    retention: 30d
    # Garder 30 jours d'historique
    
    # Storage
    storageSpec:
      volumeClaimTemplate:
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 10Gi
    # PVC de 10Gi pour stocker les métriques
    
    # Resources
    resources:
      requests:
        cpu: 200m
        memory: 512Mi
      limits:
        cpu: 500m
        memory: 1Gi

# ══════════════════════════════════════════════════════════════
# GRAFANA CONFIGURATION
# ══════════════════════════════════════════════════════════════

grafana:
  # Admin password
  adminPassword: "admin"
  # ⚠️ Change this in production!
  
  # Persistence
  persistence:
    enabled: true
    size: 5Gi
  # PVC de 5Gi pour stocker les dashboards
  
  # Resources
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: 200m
      memory: 512Mi
  
  # Pas d'Ingress (on utilise port-forward)
  ingress:
    enabled: false

# ══════════════════════════════════════════════════════════════
# ALERTMANAGER CONFIGURATION (Optionnel)
# ══════════════════════════════════════════════════════════════

alertmanager:
  enabled: true
  alertmanagerSpec:
    storage:
      volumeClaimTemplate:
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 2Gi

# ══════════════════════════════════════════════════════════════
# NODE EXPORTER (Métriques système)
# ══════════════════════════════════════════════════════════════

nodeExporter:
  enabled: true

# ══════════════════════════════════════════════════════════════
# KUBE STATE METRICS (Métriques Kubernetes)
# ══════════════════════════════════════════════════════════════

kubeStateMetrics:
  enabled: true
```

**🎓 Explication détaillée** :

#### Prometheus Config

```yaml
prometheus:
  prometheusSpec:
    retention: 30d
    # Combien de temps garder les données ?
    # 30d = 30 jours
    # Par défaut : 15d
    # Options : 1h, 7d, 90d, etc.
```

**📖 Pourquoi 30 jours ?**

- ✅ Voir les tendances sur un mois
- ✅ Debug des problèmes passés
- ⚠️ Plus = plus de storage nécessaire

```yaml
    storageSpec:
      volumeClaimTemplate:
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 10Gi
```

**📖 Calcul du storage** :

Prometheus stocke environ :

- 1-2 bytes par sample (métrique)
- 1 métrique scrappée toutes les 15s = 5760 samples/jour
- 1000 métriques × 5760 samples × 1.5 bytes ≈ 8.6 MB/jour
- Sur 30 jours : ≈ 260 MB

**Avec overhead** : 10Gi largement suffisant pour un petit cluster !

#### Grafana Config

```yaml
grafana:
  adminPassword: "admin"
  # Mot de passe pour se connecter
  # Username : admin
  # Password : admin
```

**⚠️ Sécurité** :

En production, utilise un mot de passe fort :

```yaml
adminPassword: "MyStr0ngP@ssw0rd!"
```

Ou stocke-le dans un Secret :

```yaml
admin:
  existingSecret: grafana-admin-secret
  userKey: admin-user
  passwordKey: admin-password
```

```yaml
  persistence:
    enabled: true
    size: 5Gi
```

**📖 Pourquoi activer la persistence ?**

Sans persistence :

- ❌ Dashboards perdus si Grafana redémarre
- ❌ Configuration perdue

Avec persistence :

- ✅ Dashboards sauvegardés
- ✅ Configuration gardée

#### Node Exporter

```yaml
nodeExporter:
  enabled: true
```

**Node Exporter** = Agent qui collecte les métriques système

**Déployé en** : DaemonSet (un pod par node)

**Métriques collectées** :

- CPU : `node_cpu_seconds_total`
- RAM : `node_memory_MemTotal_bytes`, `node_memory_MemAvailable_bytes`
- Disk : `node_filesystem_size_bytes`, `node_filesystem_avail_bytes`
- Network : `node_network_receive_bytes_total`, `node_network_transmit_bytes_total`

#### Kube State Metrics

```yaml
kubeStateMetrics:
  enabled: true
```

**Kube State Metrics** = Métriques sur l'état du cluster

**Métriques collectées** :

- Pods : `kube_pod_status_phase`, `kube_pod_container_status_restarts_total`
- Deployments : `kube_deployment_status_replicas`, `kube_deployment_status_replicas_available`
- Nodes : `kube_node_status_condition`

**🔍 Ce qui vient de quoi** :

|Section|Source|
|---|---|
|Structure YAML (prometheus, grafana, etc.)|**Chart kube-prometheus-stack**|
|Options disponibles|**Chart kube-prometheus-stack**|
|Valeurs (30d, 10Gi, admin)|**TON CHOIX**|
|Best practices (persistence, resources)|**Mix chart + ton jugement**|

### Créer le namespace

```bash
kubectl create namespace monitoring
```

### Installer avec Helm

```bash
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --values prometheus-values.yaml
```

**🎓 Que fait cette commande ?**

```bash
helm install prometheus
# Nom de la release : "prometheus"

prometheus-community/kube-prometheus-stack
# Chart à installer : repo/chart

--namespace monitoring
# Dans quel namespace installer

--values prometheus-values.yaml
# Utiliser notre config custom
```

**Output** :

```
NAME: prometheus
LAST DEPLOYED: Wed Dec  3 14:30:00 2025
NAMESPACE: monitoring
STATUS: deployed
REVISION: 1
NOTES:
kube-prometheus-stack has been installed. Check its status by running:
  kubectl --namespace monitoring get pods -l "release=prometheus"
```

**Durée** : 2-3 minutes

### Vérifier l'installation

```bash
# Voir les pods
kubectl get pods -n monitoring

# Output attendu :
# NAME                                                     READY   STATUS    AGE
# prometheus-kube-prometheus-operator-xxx                  1/1     Running   2m
# prometheus-prometheus-kube-prometheus-prometheus-0       2/2     Running   2m
# prometheus-grafana-xxx                                   3/3     Running   2m
# prometheus-kube-state-metrics-xxx                        1/1     Running   2m
# prometheus-prometheus-node-exporter-xxx                  1/1     Running   2m
# alertmanager-prometheus-kube-prometheus-alertmanager-0   2/2     Running   2m
```

**📖 Pods créés** :

|Pod|Rôle|
|---|---|
|`prometheus-operator`|Gère les ressources Prometheus (Operator pattern)|
|`prometheus-prometheus-0`|Prometheus serveur (StatefulSet)|
|`grafana`|Grafana serveur|
|`kube-state-metrics`|Métriques Kubernetes|
|`node-exporter`|Métriques système (DaemonSet, 1 par node)|
|`alertmanager`|Gestion des alertes|

**Attendre que tous soient Running** :

```bash
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana -n monitoring --timeout=300s

# Output:
# pod/prometheus-grafana-xxx condition met
```

### Voir les ressources créées

```bash
# Tous les objets
kubectl get all -n monitoring

# Services
kubectl get svc -n monitoring

# Output:
# NAME                                      TYPE        CLUSTER-IP      PORT(S)
# prometheus-kube-prometheus-prometheus     ClusterIP   10.43.100.1     9090/TCP
# prometheus-grafana                        ClusterIP   10.43.100.2     80/TCP
# prometheus-kube-prometheus-alertmanager   ClusterIP   10.43.100.3     9093/TCP

# PVCs
kubectl get pvc -n monitoring

# Output:
# NAME                                                      STATUS   VOLUME    CAPACITY
# prometheus-prometheus-kube-prometheus-prometheus-db-0     Bound    pvc-xxx   10Gi
# prometheus-grafana                                        Bound    pvc-yyy   5Gi
```

---

## 🌐 Accéder à Grafana

### Port-forward Grafana

```bash
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
```

**🎓 Explication** :

```bash
kubectl port-forward
# Créer un tunnel entre ton Mac et le cluster

-n monitoring
# Dans le namespace monitoring

svc/prometheus-grafana
# Service à cibler

3000:80
# Port local:Port remote
# localhost:3000 → service:80
```

**Output** :

```
Forwarding from 127.0.0.1:3000 -> 3000
Forwarding from [::1]:3000 -> 3000
```

**⚠️ Important** : Garde ce terminal ouvert ! Le port-forward s'arrête si tu fermes le terminal.

### Se connecter

1. Ouvrir le navigateur : **http://localhost:3000**
2. Login :
    - **Username** : `admin`
    - **Password** : `admin` (ou celui que tu as défini)
3. **Bienvenue dans Grafana !**

### Interface Grafana

**Menu gauche** :

```
┌─────────────────┐
│ 🏠 Home         │
│ 📊 Dashboards   │  ← Voir/créer des dashboards
│ 🔍 Explore      │  ← Explorer les métriques
│ ⚠️ Alerting     │  ← Gérer les alertes
│ ⚙️ Configuration│  ← Data sources, plugins
│ 👤 Admin        │  ← Gestion utilisateurs
└─────────────────┘
```

### Vérifier la data source Prometheus

1. Menu gauche → **⚙️ Configuration** → **Data sources**
2. Tu devrais voir **Prometheus** avec un badge vert ✅
3. Cliquer dessus pour voir les détails

**URL de Prometheus** :

```
http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090
```

**📖 Format de l'URL Kubernetes** :

```
http://<service-name>.<namespace>.svc.cluster.local:<port>
```

- `prometheus-kube-prometheus-prometheus` : Nom du service
- `monitoring` : Namespace
- `svc.cluster.local` : Suffixe DNS Kubernetes
- `9090` : Port Prometheus

### Accéder à Prometheus (optionnel)

Si tu veux voir l'interface Prometheus directement :

```bash
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
```

Ouvrir : **http://localhost:9090**

**Interface Prometheus** :

- Graph : Tester des queries PromQL
- Alerts : Voir les alertes actives
- Status : Config, targets, service discovery

---

## 📊 Dashboards pré-installés

### Importer des dashboards

Le chart `kube-prometheus-stack` installe automatiquement des dashboards !

**Voir les dashboards** :

1. Menu gauche → **📊 Dashboards** → **Browse**
2. Tu devrais voir plusieurs dossiers :
    - **General** : Dashboards généraux
    - **Kubernetes** : Dashboards K8s

### Dashboards importants

#### 1. Kubernetes / Compute Resources / Cluster

**Vue d'ensemble du cluster** :

- CPU total utilisé vs disponible
- RAM total utilisé vs disponible
- Nombre de pods par node

#### 2. Kubernetes / Compute Resources / Namespace (Pods)

**Ressources par namespace** :

- Sélectionner `namespace=lol-esports`
- CPU utilisé par pod
- RAM utilisé par pod

#### 3. Node Exporter / Nodes

**Métriques système des nodes** :

- CPU usage par core
- Memory usage
- Disk I/O
- Network traffic

### Importer des dashboards de la communauté

Grafana a une bibliothèque de dashboards : https://grafana.com/grafana/dashboards/

**Dashboards recommandés** :

|Dashboard|ID|Description|
|---|---|---|
|Kubernetes Cluster Monitoring|7249|Vue complète du cluster|
|Node Exporter Full|1860|Métriques détaillées des nodes|
|Kubernetes Pods|6417|Monitoring détaillé des pods|

**Comment importer** :

1. Menu gauche → **📊 Dashboards** → **New** → **Import**
2. Entrer l'ID (ex: `7249`)
3. Cliquer **Load**
4. Sélectionner la data source : **Prometheus**
5. Cliquer **Import**

---

## 🎨 Créer un dashboard personnalisé

### Dashboard pour le bot Discord

**Objectif** : Créer un dashboard qui montre :

- CPU du bot
- RAM du bot
- Nombre de restarts
- État des nodes (laptop vs EC2)

### Étape 1 : Créer le dashboard

1. Menu gauche → **📊 Dashboards** → **New dashboard**
2. Cliquer **Add visualization**
3. Sélectionner **Prometheus** (data source)

### Étape 2 : Panel CPU du bot

**Query** :

```promql
rate(container_cpu_usage_seconds_total{namespace="lol-esports", pod=~"discord-bot.*"}[5m]) * 100
```

**🎓 Explication** :

```promql
container_cpu_usage_seconds_total
# Métrique : Temps CPU utilisé (en secondes)
# Type : Counter (ne fait qu'augmenter)

{namespace="lol-esports", pod=~"discord-bot.*"}
# Filtres (labels) :
#   namespace="lol-esports"  : Seulement notre namespace
#   pod=~"discord-bot.*"     : Regex, pods commençant par "discord-bot"

[5m]
# Range vector : Données des 5 dernières minutes

rate(...[5m])
# Calcule le taux de variation par seconde
# rate() est pour les Counters
# Donne : combien de secondes CPU utilisées par seconde

* 100
# Convertir en pourcentage
# 0.5 secondes/seconde = 50% d'un core
```

**Configuration du panel** :

- **Panel title** : `Discord Bot - CPU Usage`
- **Unit** : `Percent (0-100)`
- **Legend** : `{{pod}}`
- **Graph type** : Time series (ligne)

Cliquer **Apply**

### Étape 3 : Panel RAM du bot

**Query** :

```promql
container_memory_usage_bytes{namespace="lol-esports", pod=~"discord-bot.*"}
```

**Configuration** :

- **Panel title** : `Discord Bot - Memory Usage`
- **Unit** : `bytes(IEC)` (affichera en MB, GB)
- **Legend** : `{{pod}}`

**Ajouter une ligne de seuil** (threshold) :

- Threshold 1 : 128 MB (request)
- Threshold 2 : 256 MB (limit) - en rouge

Cliquer **Apply**

### Étape 4 : Panel Restarts

**Query** :

```promql
kube_pod_container_status_restarts_total{namespace="lol-esports", pod=~"discord-bot.*"}
```

**Configuration** :

- **Panel title** : `Discord Bot - Restarts`
- **Visualization** : **Stat** (grand chiffre)
- **Color** :
    - 0 restarts : Vert
    - 1+ restarts : Orange
    - 5+ restarts : Rouge

Cliquer **Apply**

### Étape 5 : Panel Node Status

**Query** :

```promql
kube_node_status_condition{condition="Ready", status="true"}
```

**Configuration** :

- **Panel title** : `Nodes Status`
- **Visualization** : **Table**
- **Columns** :
    - `node` : Nom du node
    - `Value` : 1 = Ready, 0 = NotReady

Cliquer **Apply**

### Étape 6 : Organiser le dashboard

**Layout recommandé** :

```
┌──────────────────────────────────────────────┐
│          Discord Bot Monitoring               │
├──────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐          │
│  │ CPU Usage    │  │ Memory Usage │          │
│  │ (graph)      │  │ (graph)      │          │
│  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐          │
│  │ Restarts     │  │ Nodes Status │          │
│  │ (stat)       │  │ (table)      │          │
│  └──────────────┘  └──────────────┘          │
└──────────────────────────────────────────────┘
```

**Actions** :

- Drag & drop les panels pour les placer
- Resize en tirant les coins
- Ajouter des **Rows** pour grouper logiquement

### Étape 7 : Sauvegarder

1. Cliquer sur l'icône **💾 Save** (en haut à droite)
2. Nom : `Discord Bot Monitoring`
3. Folder : **General**
4. Cliquer **Save**

---

## 📈 Queries PromQL essentielles

### CPU

```promql
# CPU usage (%)
rate(container_cpu_usage_seconds_total{namespace="lol-esports"}[5m]) * 100

# CPU par pod
sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="lol-esports"}[5m])) * 100

# CPU total du cluster
sum(rate(node_cpu_seconds_total{mode!="idle"}[5m])) * 100
```

### Mémoire

```promql
# RAM usage (bytes)
container_memory_usage_bytes{namespace="lol-esports"}

# RAM en MB
container_memory_usage_bytes{namespace="lol-esports"} / 1024 / 1024

# % de la limite
(container_memory_usage_bytes / container_spec_memory_limit_bytes) * 100
```

### Réseau

```promql
# Bytes received
rate(container_network_receive_bytes_total{namespace="lol-esports"}[5m])

# Bytes transmitted
rate(container_network_transmit_bytes_total{namespace="lol-esports"}[5m])

# Convertir en MB/s
rate(container_network_receive_bytes_total{namespace="lol-esports"}[5m]) / 1024 / 1024
```

### Pods et Restarts

```promql
# Nombre de pods Running
count(kube_pod_status_phase{namespace="lol-esports", phase="Running"})

# Restarts total
sum(kube_pod_container_status_restarts_total{namespace="lol-esports"})

# Pods crashloop
count(kube_pod_container_status_waiting_reason{namespace="lol-esports", reason="CrashLoopBackOff"})
```

### Nodes

```promql
# Nodes Ready
count(kube_node_status_condition{condition="Ready", status="true"})

# Nodes NotReady
count(kube_node_status_condition{condition="Ready", status="false"})

# CPU disponible sur les nodes
sum(node_cpu_seconds_total{mode="idle"})
```

### Disk

```promql
# Espace disque disponible (%)
(node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100

# Espace utilisé par Prometheus
prometheus_tsdb_storage_blocks_bytes
```

---

## ⚠️ Alerting (Optionnel)

### Créer une alerte dans Grafana

**Exemple** : Alerter si le bot utilise > 80% de sa mémoire limite

1. Éditer le panel "Memory Usage"
2. Onglet **Alert**
3. Cliquer **Create alert rule from this panel**

**Configuration** :

```yaml
# Condition
WHEN avg() OF query(A, 5m, now) IS ABOVE 200000000
# 200 MB = 80% de 256 MB (limite)

# Evaluate every
1m
# Évaluer toutes les minutes

# For
5m
# Pendant 5 minutes consécutives
```

**Actions** :

- **Send notification to** : Default
- **Message** : `Discord bot is using over 80% of memory limit!`

Cliquer **Save**

### Alertmanager

Pour des alertes plus avancées, utilise **Alertmanager** :

**Config** : `alertmanager.yaml`

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'cluster']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'discord-webhook'

receivers:
- name: 'discord-webhook'
  webhook_configs:
  - url: 'https://discord.com/api/webhooks/YOUR_WEBHOOK_ID'
    send_resolved: true
```

**Appliquer** :

```bash
kubectl create secret generic alertmanager-config \
  --from-file=alertmanager.yaml \
  -n monitoring

helm upgrade prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring \
  -f prometheus-values.yaml \
  --set alertmanager.config.global.resolve_timeout=5m
```

---

## 🚨 Troubleshooting

### Grafana ne se connecte pas à Prometheus

```bash
# Vérifier que Prometheus tourne
kubectl get pods -n monitoring | grep prometheus

# Tester la connexion depuis Grafana pod
kubectl exec -it -n monitoring deployment/prometheus-grafana -- \
  curl http://prometheus-kube-prometheus-prometheus:9090/-/healthy

# Devrait retourner "Prometheus is Healthy."
```

### Pas de métriques pour le bot

```bash
# Vérifier que le bot tourne
kubectl get pods -n lol-esports

# Vérifier les labels
kubectl get pods -n lol-esports --show-labels

# Dans Prometheus, vérifier les targets
# http://localhost:9090/targets
# Chercher les targets avec namespace="lol-esports"
```

### Dashboards ne chargent pas

```bash
# Vérifier les logs Grafana
kubectl logs -n monitoring deployment/prometheus-grafana

# Redémarrer Grafana
kubectl rollout restart deployment/prometheus-grafana -n monitoring
```

### Storage plein

```bash
# Voir l'utilisation du storage
kubectl exec -n monitoring prometheus-prometheus-kube-prometheus-prometheus-0 -- \
  df -h /prometheus

# Si plein, réduire la rétention
helm upgrade prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring \
  -f prometheus-values.yaml \
  --set prometheus.prometheusSpec.retention=15d
```

---

## 📝 Récapitulatif

### Ce qu'on a installé

✅ **Prometheus** : Collecte et stocke les métriques (30d de rétention, 10Gi)  
✅ **Grafana** : Visualise les métriques (dashboards, 5Gi de storage)  
✅ **Node Exporter** : Métriques système (CPU, RAM, disk)  
✅ **Kube State Metrics** : Métriques Kubernetes (pods, deployments)  
✅ **Alertmanager** : Gestion des alertes

### Architecture complète

```
monitoring namespace
├── Prometheus (StatefulSet)
│   ├── PVC: 10Gi
│   └── Service: :9090
├── Grafana (Deployment)
│   ├── PVC: 5Gi
│   └── Service: :80 (port-forward :3000)
├── Alertmanager (StatefulSet)
│   ├── PVC: 2Gi
│   └── Service: :9093
├── Node Exporter (DaemonSet, 1 pod/node)
└── Kube State Metrics (Deployment)
```

### Dashboards créés

✅ Discord Bot Monitoring (custom)  
✅ Kubernetes Cluster Monitoring (importé)  
✅ Node Exporter Full (importé)

### Queries PromQL maîtrisées

✅ CPU usage  
✅ Memory usage  
✅ Network traffic  
✅ Pod restarts  
✅ Node status

### Commandes essentielles

```bash
# Port-forward Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Port-forward Prometheus
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# Voir les métriques disponibles
kubectl exec -n monitoring prometheus-prometheus-kube-prometheus-prometheus-0 -- \
  wget -qO- http://localhost:9090/api/v1/label/__name__/values

# Redémarrer Grafana
kubectl rollout restart deployment/prometheus-grafana -n monitoring
```

---

## 🎉 Félicitations !

Tu as maintenant un **système de monitoring complet** :

- ✅ Métriques en temps réel
- ✅ Dashboards visuels
- ✅ Historique 30 jours
- ✅ Alertes configurables

**Prochaine étape** : Phase 6 - GitOps avec ArgoCD ! 🔄

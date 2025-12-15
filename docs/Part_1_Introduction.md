# 🚀 Bot Discord sur Kubernetes Hybrid Cloud

## 📚 Qu'est-ce qu'on va construire ?

### Le projet en une phrase

Un bot Discord qui tourne sur Kubernetes (laptop en temps normal, EC2 en failover), avec basculement automatique, monitoring, et gestion GitOps.

### Pourquoi c'est intéressant ?

Ce projet combine **7 technologies** professionnelles :

- **Kubernetes** : Orchestration de containers
- **AWS** : Cloud computing
- **Terraform** : Infrastructure as Code
- **Docker** : Conteneurisation
- **GitOps (ArgoCD)** : Déploiement automatique depuis Git
- **Monitoring (Prometheus/Grafana)** : Observer ce qui se passe
- **Serverless (Lambda)** : Automatisation event-driven

**Coût** : ~€0.10/mois (ultra optimisé !)

---

## 🎯 Architecture : Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                   TON INFRASTRUCTURE                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────┐          ┌────────────────────┐     │
│  │  LAPTOP (chez toi) │          │   AWS EC2 (cloud)  │     │
│  │  ──────────────────│          │  ──────────────────│     │
│  │  • K3s control     │          │  • K3s control     │     │
│  │    plane           │          │    plane (backup)  │     │
│  │  • Bot Discord     │          │  • ArgoCD          │     │
│  │  • Healthcheck     │          │  • Auto-start      │     │
│  │  • Tailscale       │          │  • OFF par défaut  │     │
│  │    Funnel          │          │                    │     │
│  │  • Toujours ON     │          │                    │     │
│  └────────┬───────────┘          └────────────────────┘     │
│           │                                  ▲               │
│           │ https://laptop.ts.net/health     │               │
│           ▼                                  │               │
│  ┌────────────────────────────────────────────┴───────┐     │
│  │              Lambda Watchdog                       │     │
│  │  ────────────────────────────────────────────────  │     │
│  │  • Ping healthcheck via Funnel (public)            │     │
│  │  • Si DOWN → Start EC2                             │     │
│  │  • Si UP + EC2 running → Stop EC2                  │     │
│  │  • Downtime: ~5-10 min                             │     │
│  └────────────────────────────────────────────────────┘     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 🧠 Comment ça marche ?

1. **Temps normal** : Le bot tourne sur ton laptop avec K3s, l'EC2 est éteint
2. **Laptop expose** : Un healthcheck HTTP via Tailscale Funnel (accessible publiquement)
3. **Lambda vérifie** : Toutes les 5 min, ping le healthcheck via HTTPS
4. **Tu éteins le laptop** (ou panne, ou ferme le couvercle)
5. **Lambda détecte** (< 5 min) que le healthcheck ne répond plus
6. **Lambda démarre l'EC2** automatiquement
7. **EC2 démarre** : K3s + ArgoCD redéploient le bot automatiquement (~3-5 min)
8. **Downtime total** : ~5-10 min (détection + boot EC2 + redéploiement)
9. **Tu rallumes le laptop** → Lambda arrête l'EC2 → Bot revient sur laptop

**Résultat** : Haute disponibilité + coûts minimaux !

---

## 📖 Concepts de base à comprendre

### Kubernetes, c'est quoi ?

**Analogie** : Kubernetes = Chef d'orchestre qui gère des musiciens (containers)

Tu lui dis : "Je veux 3 violons, 2 pianos" → Il s'assure qu'il y en a toujours 3 et 2
Si un musicien tombe malade → Il en recrute un autre automatiquement

**Dans notre cas** :

- Tu dis à K8s : "Je veux 1 bot Discord qui tourne"
- K8s s'assure qu'il y a toujours 1 bot qui tourne
- Si le bot crash → K8s le redémarre automatiquement

### K3s vs Kubernetes complet

**K3s** = Kubernetes Light (version allégée)

- **Kubernetes complet** : ~5 GB de RAM, complexe à installer
- **K3s** : <512 MB de RAM, installation en 1 commande

**Pourquoi K3s pour nous ?**

- Laptop = ressources limitées
- On veut quelque chose de simple à gérer
- 100% compatible avec Kubernetes standard

### Terraform, c'est quoi ?

**Analogie** : Terraform = Architecte qui dessine les plans d'un bâtiment

Tu écris un fichier qui décrit ton infrastructure :

```
"Je veux 1 serveur AWS + 1 réseau + 1 fonction Lambda"
```

Terraform crée tout automatiquement !

**Avantages** :

- Reproductible : Tu peux recréer l'infra en 2 min
- Versionné : Tout est dans Git
- Prévisible : `terraform plan` te montre ce qui va changer AVANT de le faire

### Docker, c'est quoi ?

**Analogie** : Docker = Tupperware pour applications

Au lieu d'installer ton bot directement sur le serveur (galère, conflits de versions), tu le mets dans un "container" avec toutes ses dépendances.

**Container** = Application + dépendances + OS minimal → Ça tourne pareil partout (laptop, serveur, cloud)

---

## 🗺️ Plan du projet : 8 phases

### Phase 1 : Prérequis et préparation
- Configuration laptop pour 24/7
- Installation K3s
- Setup Mac pour gestion à distance
- Installation Tailscale VPN

### Phase 2 : Infrastructure AWS
- Création VPC, Subnet, Security Groups
- EC2 standalone backup control plane
- Lambda watchdog (avec healthcheck HTTPS)
- EventBridge trigger (toutes les 5 min)
- **3 méthodes** : Console Web / AWS CLI / Terraform (recommandé)

### Phase 3 : Conteneurisation Docker
- Dockerfile pour le bot Discord
- Build et push sur Docker Hub
- Best practices (multi-stage, security)

### Phase 4 : Déploiements Kubernetes
- Namespace et resource quotas
- Sealed Secrets (secrets sécurisés)
- PersistentVolumeClaim (storage)
- Security Context (non-root)
- Deployment avec health checks

### Phase 5 : Monitoring
- Installation Prometheus (via Helm)
- Configuration Grafana
- Dashboards personnalisés
- Alerting (optionnel)

### Phase 6 : GitOps avec ArgoCD
- Installation ArgoCD
- Configuration repo Git
- Sync automatique
- Self-healing

### Phase 7 : Lambda Watchdog
- Configuration Tailscale Funnel pour healthcheck
- Code Python du watchdog (healthcheck HTTPS)
- Logic de failover (détection + démarrage EC2)
- Déploiement et monitoring CloudWatch

### Phase 8 : Tests et validation
- Tests de failover
- Validation monitoring
- Documentation finale

---

## 💰 Coûts estimés

### Coût mensuel détaillé

| Service | Coût |
|---------|------|
| EC2 t3.micro (stopped 99%) | ~€0.88/mois (EBS storage) |
| EC2 t3.micro (running 1%) | ~€0.02/mois |
| Lambda | €0 (free tier) |
| Data transfer | ~€0.01/mois |
| **Total** | **~€0.10/mois** 🎉 |

### Pourquoi si peu ?

- EC2 éteint la plupart du temps (watchdog intelligent)
- Lambda gratuit (<1M invocations/mois)
- Pas d'ELB, pas d'RDS
- Optimisation maximale

---

## 🎓 Compétences démontrées

Ce projet showcase ces compétences DevOps/SRE :

✅ **Infrastructure as Code** (Terraform)
✅ **Container orchestration** (Kubernetes/K3s)
✅ **GitOps** (ArgoCD)
✅ **Monitoring** (Prometheus/Grafana)
✅ **Security** (Sealed Secrets, non-root containers)
✅ **Serverless** (AWS Lambda)
✅ **High availability** (Failover automatique)
✅ **Cost optimization** (EC2 on-demand intelligent)
✅ **Networking** (VPN mesh Tailscale)
✅ **Python** (Lambda, Bot Discord)

---

## 🚀 Prêt à commencer ?

**Prochaine étape** : [Phase 1 - Prérequis et préparation](Part_2_Phase_1_Prérequis.md)

Tu vas configurer ton laptop, installer K3s, et préparer l'environnement de travail !


# Infrastructure

Cette configuration permet de déployer toute l'infrastructure du bot Discord LoL Esports de manière automatisée et reproductible.

## Architecture

```
┌─────────────────────────────────────────────┐
│              Machine (bare metal)            │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │           k3s (Kubernetes)              │ │
│  │                                         │ │
│  │  ┌──────────────────────────────────┐  │ │
│  │  │         ArgoCD (GitOps)          │  │ │
│  │  └──────────────────────────────────┘  │ │
│  │                                         │ │
│  │  ┌──────────────────────────────────┐  │ │
│  │  │    Sealed Secrets (Security)     │  │ │
│  │  └──────────────────────────────────┘  │ │
│  │                                         │ │
│  │  ┌──────────────────────────────────┐  │ │
│  │  │  Prometheus + Grafana (Monitor)  │  │ │
│  │  └──────────────────────────────────┘  │ │
│  │                                         │ │
│  │  ┌──────────────────────────────────┐  │ │
│  │  │    Discord Bot (Application)     │  │ │
│  │  └──────────────────────────────────┘  │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

## Structure

```
infrastructure/
├── init-k3s.sh           # Script d'installation k3s
└── kubernetes/           # Configuration Terraform
    ├── providers.tf      # Providers (kubernetes, helm, kubectl)
    ├── variables.tf      # Variables configurables
    ├── argocd.tf        # Installation ArgoCD
    ├── sealed-secrets.tf # Installation Sealed Secrets
    ├── monitoring.tf    # Stack Prometheus/Grafana
    ├── discord-bot-app.tf # ArgoCD Application
    └── README.md        # Documentation détaillée
```

## Installation complète (from scratch)

### 1️⃣ Installer k3s

```bash
cd infrastructure
./init-k3s.sh
```

### 2️⃣ Déployer l'infrastructure avec Terraform

```bash
cd kubernetes
terraform init
terraform plan    # Voir ce qui va être créé
terraform apply   # Créer l'infrastructure
```

### 3️⃣ Créer les secrets Discord

```bash
# Récupérer le certificat Sealed Secrets
kubeseal --fetch-cert \
  --controller-name=sealed-secrets-controller \
  --controller-namespace=kube-system \
  > sealed-secrets-cert.pem

# Créer le SealedSecret (remplacer YOUR_TOKEN)
kubectl create secret generic discord-bot-secrets \
  --from-literal=DISCORD_TOKEN=YOUR_TOKEN \
  --namespace=lol-esports \
  --dry-run=client -o yaml | \
kubeseal --cert=sealed-secrets-cert.pem \
  --format=yaml > ../k8s/discord-bot/sealed-secret.yaml

# Commit et push
git add ../k8s/discord-bot/sealed-secret.yaml
git commit -m "Add Discord bot sealed secret"
git push
```

### 4️⃣ Vérifier que tout fonctionne

```bash
# Vérifier les pods
kubectl get pods --all-namespaces

# Vérifier l'application ArgoCD
kubectl get applications -n argocd

# Accéder à ArgoCD UI
kubectl port-forward svc/argocd-server -n argocd 8080:443
# Récupérer le mot de passe admin :
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
```

## Workflow de développement

Après l'installation initiale, le workflow est entièrement automatisé :

```
1. git push (code du bot)
   ↓
2. GitHub Actions (build + push image Docker)
   ↓
3. Update du tag dans k8s/discord-bot/deployment.yaml
   ↓
4. ArgoCD détecte le changement automatiquement
   ↓
5. Déploiement automatique du bot
```

## Disaster Recovery

En cas de panne complète de la machine :

```bash
# 1. Réinstaller k3s
cd infrastructure
./init-k3s.sh

# 2. Redéployer toute l'infrastructure
cd kubernetes
terraform apply

# 3. Recréer les secrets (garder une copie du token Discord !)
# Voir étape 3 ci-dessus
```

⏱️ **Temps de recovery : ~10 minutes**

## Accès aux services

### ArgoCD
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
# User: admin
# Password: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
```

### Grafana
```bash
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# User: admin
# Password: admin
```

### Prometheus
```bash
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
```

## Avantages de cette approche

✅ **Reproductible** : Tout peut être reconstruit en quelques commandes
✅ **Versionné** : L'infrastructure est dans Git
✅ **Documenté** : Le code Terraform est auto-documenté
✅ **Automatisé** : ArgoCD gère les déploiements
✅ **Sécurisé** : Secrets chiffrés avec Sealed Secrets
✅ **Observable** : Prometheus + Grafana pour le monitoring

## Notes importantes

- **k3s** : Installé via script shell (pas géré par Terraform)
- **Terraform** : Gère toute l'infrastructure Kubernetes
- **ArgoCD** : Gère les applications (Discord bot)
- **Secrets** : Ne jamais commiter de secrets en clair
- **State** : Le fichier `terraform.tfstate` doit être sauvegardé

## Commandes utiles

```bash
# Voir l'état de l'infrastructure
terraform show

# Voir les changements avant de les appliquer
terraform plan

# Appliquer des changements
terraform apply

# Détruire toute l'infrastructure (ATTENTION !)
terraform destroy

# Vérifier les pods
kubectl get pods --all-namespaces

# Voir les logs du bot
kubectl logs -n lol-esports -l app=discord-bot -f
```

## Troubleshooting

Voir [kubernetes/README.md](kubernetes/README.md) pour plus de détails sur le troubleshooting.

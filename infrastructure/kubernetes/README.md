# Infrastructure Kubernetes - Terraform

Cette configuration Terraform gère toute l'infrastructure Kubernetes pour le bot Discord LoL Esports.

## Prérequis

1. **k3s doit être installé** sur la machine cible
2. **kubectl** configuré avec accès au cluster
3. **Terraform** >= 1.0 installé

## Ce que Terraform gère

- **ArgoCD** : GitOps pour le déploiement automatique
- **Sealed Secrets** : Gestion sécurisée des secrets
- **Prometheus + Grafana** : Monitoring et observabilité
- **Discord Bot Application** : Configuration ArgoCD pour le bot

## Structure

```
infrastructure/kubernetes/
├── providers.tf           # Configuration des providers
├── variables.tf           # Variables configurables
├── argocd.tf             # Déploiement ArgoCD
├── sealed-secrets.tf     # Déploiement Sealed Secrets
├── monitoring.tf         # Stack Prometheus/Grafana
├── discord-bot-app.tf    # ArgoCD Application pour le bot
└── README.md             # Ce fichier
```

## Installation complète (première fois)

### Étape 1 : Installer k3s

```bash
# Utiliser le script d'initialisation
cd infrastructure
./init-k3s.sh
```

Le script va :
- Installer k3s si pas déjà fait
- Configurer les permissions
- Attendre que k3s soit prêt
- Configurer kubectl

### Étape 2 : Déployer l'infrastructure avec Terraform

```bash
cd infrastructure/kubernetes

# Initialiser Terraform
terraform init

# Voir ce qui va être créé
terraform plan

# Appliquer la configuration
terraform apply
```

### Étape 3 : Créer les secrets Discord

Les secrets ne sont **pas gérés par Terraform** (bonnes pratiques de sécurité).

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
  --format=yaml > k8s/discord-bot/sealed-secret.yaml

# Commit le SealedSecret
git add k8s/discord-bot/sealed-secret.yaml
git commit -m "Add Discord bot sealed secret"
git push
```

## Commandes utiles

### Vérifier l'état de l'infrastructure

```bash
# Voir l'état Terraform
terraform show

# Vérifier les pods
kubectl get pods --all-namespaces

# Vérifier l'application ArgoCD
kubectl get applications -n argocd
```

### Accéder aux services

```bash
# ArgoCD UI (user: admin)
# Récupérer le mot de passe :
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
# Port-forward :
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Grafana (user: admin, password: admin)
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Prometheus
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
```

### Mettre à jour l'infrastructure

```bash
# Modifier les variables dans variables.tf si nécessaire
# Puis appliquer les changements
terraform plan
terraform apply
```

### Détruire l'infrastructure

```bash
# ATTENTION : Cela supprime TOUT (sauf k3s lui-même)
terraform destroy
```

## Variables configurables

Créer un fichier `terraform.tfvars` pour personnaliser :

```hcl
kubeconfig_path         = "~/.kube/config"
argocd_version          = "5.51.6"
sealed_secrets_version  = "2.13.2"
prometheus_version      = "55.5.0"
discord_bot_repo        = "https://github.com/beckk97440/k8s-discord-bot.git"
discord_bot_namespace   = "lol-esports"
```

## Workflow complet (après setup)

1. **Développement** : Modifier le code du bot
2. **Commit** : `git push` (GitHub Actions build + push l'image)
3. **ArgoCD** : Détecte le changement et déploie automatiquement
4. **Monitoring** : Grafana affiche les métriques en temps réel

## Disaster Recovery

En cas de problème majeur :

```bash
# 1. Réinstaller k3s si nécessaire
curl -sfL https://get.k3s.io | sh -

# 2. Recréer toute l'infrastructure
cd infrastructure/kubernetes
terraform apply

# 3. Recréer les secrets (garder une copie du token quelque part !)
# Voir étape 3 ci-dessus
```

## Notes importantes

- **Secrets** : Ne jamais commiter de secrets en clair dans Git
- **State Terraform** : Le fichier `terraform.tfstate` contient l'état de l'infra, à sauvegarder
- **Versions** : Les versions des charts Helm sont fixées dans `variables.tf`
- **k3s** : Terraform ne gère pas l'installation de k3s lui-même

## Troubleshooting

### Erreur "connection refused" lors du `terraform apply`

```bash
# Vérifier que k3s est bien démarré
sudo systemctl status k3s

# Vérifier kubectl
kubectl get nodes
```

### ArgoCD ne démarre pas

```bash
# Vérifier les pods ArgoCD
kubectl get pods -n argocd

# Voir les logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server
```

### L'application Discord bot reste en "Syncing"

```bash
# Vérifier les détails de l'application
kubectl describe application discord-bot -n argocd

# Voir les logs ArgoCD
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller
```

# 📝 Adaptations pour ton setup actuel

## ✅ Ce qui a été modifié

Les documents des **Phases 3 et 4** ont été mis à jour pour partir de ton setup actuel au lieu d'un exemple générique.

---

## 🐳 Phase 3 - Docker

### Changements principaux

1. **Supprimé** : Exemple de bot Discord générique
2. **Ajouté** : Référence à ton bot réel avec scraping LoL Esports + Sheep news
3. **Adapté** : Dockerfile part de ton Dockerfile existant et explique les améliorations
4. **Corrigé** : Bug `ESPORTS_CHANNEL_ID` vs `MATCH_CHANNEL_ID`

### Ton bug à corriger

**Dans `.env`, change** :

```bash
# Avant
ESPORTS_CHANNEL_ID=123456789

# Après
MATCH_CHANNEL_ID=123456789  # ← Match le code dans bot.py
```

**Pourquoi ?**

Dans `bot.py` ligne 12 :

```python
MATCH_CHANNEL_ID = int(os.getenv('MATCH_CHANNEL_ID', '0'))  # ← Cherche MATCH_CHANNEL_ID
```

Mais dans ton `.env` tu avais `ESPORTS_CHANNEL_ID` → Le bot ne trouvait pas la variable !

### Dockerfile amélioré

**Ton ancien Dockerfile** :

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py .
CMD ["python", "-u", "bot.py"]
```

**Améliorations pour Kubernetes** :

- ✅ Ajout utilisateur non-root (`botuser`, UID 1000)
- ✅ Ajout dossier `/app/data` pour PVC
- ✅ Security Context compatible (read-only filesystem)
- ✅ COPY avec `--chown=botuser:botuser`
- ✅ Metadata (LABEL)
- ✅ HEALTHCHECK

**Dockerfile complet dans Phase 3** : Voir section "Améliorer le Dockerfile pour Kubernetes"

---

## ☸️ Phase 4 - Kubernetes

### Changements principaux

1. **Variables d'environnement adaptées** :
    
    - ✅ `DISCORD_TOKEN`
    - ✅ `MATCH_CHANNEL_ID` (pour les matchs)
    - ✅ `NEWS_CHANNEL_ID` (pour les news Sheep)
    - ❌ Supprimé `DATABASE_URL` (pas utilisé dans ton bot)
2. **SealedSecret adapté** avec les 3 variables
    
3. **Deployment adapté** avec les 3 variables
    
4. **Tests adaptés** avec tes vraies commandes Discord
    

### Variables d'environnement

**SealedSecret** (`k8s/apps/discord-bot/sealed-secret.yaml`) :

```yaml
spec:
  encryptedData:
    DISCORD_TOKEN: AgB...  # Chiffré
    MATCH_CHANNEL_ID: AgC...  # Chiffré
    NEWS_CHANNEL_ID: AgD...  # Chiffré
```

**Deployment** (`k8s/apps/discord-bot/deployment.yaml`) :

```yaml
env:
- name: DISCORD_TOKEN
  valueFrom:
    secretKeyRef:
      name: discord-bot-secret
      key: DISCORD_TOKEN
- name: MATCH_CHANNEL_ID
  valueFrom:
    secretKeyRef:
      name: discord-bot-secret
      key: MATCH_CHANNEL_ID
- name: NEWS_CHANNEL_ID
  valueFrom:
    secretKeyRef:
      name: discord-bot-secret
      key: NEWS_CHANNEL_ID
```

### Commandes de test adaptées

**Dans Discord, tes vraies commandes** :

```
!matches      # Derniers résultats + prochains matchs
!today        # Matchs d'aujourd'hui
!league lec   # Matchs d'une league spécifique
!team g2      # Matchs d'une équipe
```

**Notifications automatiques** :

- Matchs dans 1h → Posted dans `MATCH_CHANNEL_ID`
- News Sheep → Posted dans `NEWS_CHANNEL_ID` (toutes les 20min)

---

## 🎯 Workflow de migration

### Étape 1 : Corriger le bug des variables

```bash
cd lol-esports-bot

# Éditer .env
vim .env

# Change ESPORTS_CHANNEL_ID en MATCH_CHANNEL_ID
```

### Étape 2 : Remplacer le Dockerfile

```bash
# Backup de l'ancien
cp Dockerfile Dockerfile.old

# Créer le nouveau Dockerfile
# → Copier depuis Phase 3 section "Dockerfile amélioré"
vim Dockerfile
```

### Étape 3 : Tester localement

```bash
# Build la nouvelle image
docker build -t tonusername/lol-esports-bot:v1.0.0 .

# Test
docker run -d --name lol-bot-test \
  -e DISCORD_TOKEN="$(grep DISCORD_TOKEN .env | cut -d '=' -f2)" \
  -e MATCH_CHANNEL_ID="$(grep MATCH_CHANNEL_ID .env | cut -d '=' -f2)" \
  -e NEWS_CHANNEL_ID="$(grep NEWS_CHANNEL_ID .env | cut -d '=' -f2)" \
  tonusername/lol-esports-bot:v1.0.0

# Voir les logs
docker logs -f lol-bot-test

# Tester sur Discord
# !matches, !today, etc.

# Clean
docker stop lol-bot-test
docker rm lol-bot-test
```

### Étape 4 : Push sur Docker Hub

```bash
# Login
docker login

# Push
docker push tonusername/lol-esports-bot:v1.0.0

# Optionnel : Tag latest
docker tag tonusername/lol-esports-bot:v1.0.0 tonusername/lol-esports-bot:latest
docker push tonusername/lol-esports-bot:latest
```

### Étape 5 : Suivre Phase 1-2 (Infrastructure)

Rien à changer, suivre le guide tel quel.

### Étape 6 : Créer les manifests Kubernetes (Phase 4)

**Créer le SealedSecret** :

```bash
# 1. Créer le secret (ne PAS commiter)
kubectl create secret generic discord-bot-secret \
  --from-literal=DISCORD_TOKEN="ton_token" \
  --from-literal=MATCH_CHANNEL_ID="123456789" \
  --from-literal=NEWS_CHANNEL_ID="987654321" \
  --namespace=lol-esports \
  --dry-run=client -o yaml > discord-bot-secret.yaml

# 2. Sceller
kubeseal --format yaml < discord-bot-secret.yaml > discord-bot-sealed-secret.yaml

# 3. Nettoyer
rm discord-bot-secret.yaml

# 4. Commiter le SealedSecret (chiffré, safe !)
git add discord-bot-sealed-secret.yaml
git commit -m "Add sealed secret"
```

---

## 📊 Comparaison avant/après

### Avant (Docker Compose)

```
lol-esports-bot/
├── bot.py
├── Dockerfile (basique)
├── docker-compose.yml  ← On lance avec ça
├── .env (local)
└── requirements.txt

$ docker-compose up -d
→ Bot tourne sur laptop seulement
→ Aucune redondance
→ Pas de monitoring
→ Pas de GitOps
```

### Après (Kubernetes)

```
lol-esports-k8s-manifests/  ← Nouveau repo Git
├── k8s/
│   ├── base/
│   │   ├── namespace.yaml
│   │   └── resource-quota.yaml
│   └── apps/
│       └── discord-bot/
│           ├── sealed-secret.yaml  ← Secrets chiffrés
│           ├── pvc.yaml
│           └── deployment.yaml

$ git push
→ ArgoCD détecte et déploie automatiquement
→ Bot tourne sur laptop (primary)
→ Failover automatique vers EC2 (si laptop down)
→ Monitoring Prometheus/Grafana
→ GitOps avec historique complet
```

---

## ✅ Checklist de migration

- [ ] Corriger le bug `MATCH_CHANNEL_ID` dans `.env`
- [ ] Remplacer le Dockerfile par la version améliorée
- [ ] Tester localement avec `docker run`
- [ ] Push l'image sur Docker Hub
- [ ] Suivre Phase 1 (K3s sur laptop)
- [ ] Suivre Phase 2 (Infrastructure AWS)
- [ ] Créer le SealedSecret avec les 3 variables
- [ ] Créer le PVC
- [ ] Créer le Deployment
- [ ] Tester les commandes Discord
- [ ] Suivre Phase 5 (Monitoring)
- [ ] Suivre Phase 6 (GitOps)
- [ ] Suivre Phase 7 (Lambda Watchdog)
- [ ] Suivre Phase 8 (Tests complets)

---

## 🎉 Résultat final

Ton bot LoL Esports Discord avec scraping tournera sur :

- ✅ Deux clusters K3s standalone (laptop + AWS EC2 backup)
- ✅ Failover automatique (< 10 min via Lambda + Tailscale Funnel)
- ✅ GitOps (ArgoCD)
- ✅ Monitoring (Prometheus + Grafana)
- ✅ Coût : ~€0.10/mois
- ✅ Production-ready avec Security Context, Sealed Secrets, PVC
- ✅ Portfolio-ready !

**Questions ou blocages pendant la migration ?** N'hésite pas ! 😊

#!/bin/bash
set -e


# SYSTEM UPDATE

apt-get update
apt-get upgrade -y
apt-get install -y curl wget vim htop


# TAILSCALE INSTALLATION

echo "Installing Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh

echo "Starting Tailscale..."
tailscale up --authkey=${tailscale_auth_key} --advertise-tags=tag:k8s-worker

sleep 10


# INSTALLATION OF K3S SERVER (STANDALONE)

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


# INSTALL ARGOCD

echo "Installing ArgoCD..."
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

echo "Waiting for ArgoCD to be ready..."
kubectl wait --for=condition=available --timeout=600s deployment/argocd-server -n argocd
kubectl wait --for=condition=available --timeout=600s deployment/argocd-repo-server -n argocd

echo "ArgoCD is ready!"


# CREATE DISCORD BOT SECRETS

echo "Creating discord-bot namespace and secrets..."
kubectl create namespace lol-esports --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic discord-bot-secret \
  --from-literal=DISCORD_TOKEN="${discord_token}" \
  --from-literal=MATCH_CHANNEL_ID="${match_channel_id}" \
  --from-literal=NEWS_CHANNEL_ID="${news_channel_id}" \
  -n lol-esports \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Secrets created!"


# DEPLOY DISCORD BOT VIA ARGOCD

echo "Deploying discord-bot application..."
kubectl apply -f https://raw.githubusercontent.com/beckk97440/k8s-discord-bot/main/k8s/base/discord-bot-app.yaml

echo "Waiting for discord-bot to sync..."
sleep 30

echo "Setup complete!"
kubectl get pods -n lol-esports
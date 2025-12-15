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

echo "Setup complete!"
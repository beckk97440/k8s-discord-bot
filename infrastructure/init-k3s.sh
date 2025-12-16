#!/bin/bash
set -e

echo "========================================="
echo "Installation de k3s"
echo "========================================="

# Vérifie si k3s est déjà installé
if command -v k3s &> /dev/null; then
    echo "✅ k3s est déjà installé"
    k3s --version
else
    echo "📦 Installation de k3s..."
    curl -sfL https://get.k3s.io | sh -
    echo "✅ k3s installé avec succès"
fi

# Configure les permissions sur le kubeconfig
echo "🔧 Configuration des permissions..."
sudo chmod 644 /etc/rancher/k3s/k3s.yaml

# Vérifie que k3s est bien démarré
echo "🔍 Vérification du statut de k3s..."
sudo systemctl status k3s --no-pager || true

# Configure kubectl pour l'utilisateur courant
echo "⚙️  Configuration de kubectl..."
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
export KUBECONFIG=~/.kube/config

# Ajoute KUBECONFIG au .bashrc si pas déjà présent
if ! grep -q "KUBECONFIG" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# k3s kubeconfig" >> ~/.bashrc
    echo "export KUBECONFIG=~/.kube/config" >> ~/.bashrc
fi

# Attend que k3s soit prêt
echo "⏳ Attente que k3s soit prêt..."
timeout=60
while [ $timeout -gt 0 ]; do
    if kubectl get nodes &> /dev/null; then
        echo "✅ k3s est prêt !"
        kubectl get nodes
        break
    fi
    echo "En attente... ($timeout secondes restantes)"
    sleep 2
    timeout=$((timeout - 2))
done

if [ $timeout -le 0 ]; then
    echo "❌ Timeout : k3s n'est pas prêt après 60 secondes"
    exit 1
fi

echo ""
echo "========================================="
echo "✅ k3s installé et configuré avec succès"
echo "========================================="
echo ""
echo "Prochaines étapes :"
echo "1. cd infrastructure/kubernetes"
echo "2. terraform init"
echo "3. terraform apply"

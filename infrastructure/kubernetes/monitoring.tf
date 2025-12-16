# Namespace pour le monitoring
resource "kubernetes_namespace" "monitoring" {
  metadata {
    name = "monitoring"
  }
}

# Installation de Prometheus + Grafana via Helm
resource "helm_release" "prometheus" {
  name       = "prometheus"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = var.prometheus_version
  namespace  = kubernetes_namespace.monitoring.metadata[0].name

  # Grafana configuration
  set {
    name  = "grafana.enabled"
    value = "true"
  }

  set {
    name  = "grafana.adminPassword"
    value = "admin"
  }

  set {
    name  = "grafana.service.type"
    value = "ClusterIP"
  }

  # Prometheus configuration
  set {
    name  = "prometheus.prometheusSpec.retention"
    value = "7d"
  }

  set {
    name  = "prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.accessModes[0]"
    value = "ReadWriteOnce"
  }

  set {
    name  = "prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage"
    value = "10Gi"
  }

  # Alertmanager configuration
  set {
    name  = "alertmanager.enabled"
    value = "true"
  }

  depends_on = [kubernetes_namespace.monitoring]
}

# Outputs pour accéder aux services
output "grafana_access_command" {
  value       = "kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80"
  description = "Command to access Grafana (admin/admin)"
}

output "prometheus_access_command" {
  value       = "kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090"
  description = "Command to access Prometheus"
}

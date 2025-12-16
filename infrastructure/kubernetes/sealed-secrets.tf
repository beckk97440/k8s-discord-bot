# Installation de Sealed Secrets Controller via Helm
resource "helm_release" "sealed_secrets" {
  name       = "sealed-secrets-controller"
  repository = "https://bitnami-labs.github.io/sealed-secrets"
  chart      = "sealed-secrets"
  version    = var.sealed_secrets_version
  namespace  = "kube-system"

  set {
    name  = "commandArgs[0]"
    value = "--update-status"
  }
}

# Output pour récupérer la clé publique
output "sealed_secrets_cert_command" {
  value       = "kubeseal --fetch-cert --controller-name=sealed-secrets-controller --controller-namespace=kube-system"
  description = "Command to fetch the Sealed Secrets public certificate"
}

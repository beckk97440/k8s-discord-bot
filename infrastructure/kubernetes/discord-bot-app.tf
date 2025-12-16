# Namespace pour le bot Discord
resource "kubernetes_namespace" "discord_bot" {
  metadata {
    name = var.discord_bot_namespace
  }
}

# ArgoCD Application pour le Discord Bot
resource "kubectl_manifest" "discord_bot_app" {
  yaml_body = yamlencode({
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "Application"
    metadata = {
      name      = "discord-bot"
      namespace = "argocd"
    }
    spec = {
      project = "default"
      source = {
        repoURL        = var.discord_bot_repo
        targetRevision = "HEAD"
        path           = "k8s/discord-bot"
      }
      destination = {
        server    = "https://kubernetes.default.svc"
        namespace = var.discord_bot_namespace
      }
      syncPolicy = {
        automated = {
          prune      = true
          selfHeal   = true
          allowEmpty = false
        }
        syncOptions = [
          "CreateNamespace=true",
          "PrunePropagationPolicy=foreground",
          "PruneLast=true"
        ]
      }
    }
  })

  depends_on = [
    helm_release.argocd,
    kubernetes_namespace.discord_bot
  ]
}

output "discord_bot_status_command" {
  value       = "kubectl get applications -n argocd discord-bot"
  description = "Command to check Discord bot ArgoCD application status"
}

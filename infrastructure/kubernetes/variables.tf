variable "kubeconfig_path" {
  description = "Path to kubeconfig file"
  type        = string
  default     = "~/.kube/config"
}

variable "argocd_version" {
  description = "ArgoCD Helm chart version"
  type        = string
  default     = "5.51.6"
}

variable "sealed_secrets_version" {
  description = "Sealed Secrets Helm chart version"
  type        = string
  default     = "2.13.2"
}

variable "prometheus_version" {
  description = "Prometheus Helm chart version"
  type        = string
  default     = "55.5.0"
}

variable "discord_bot_repo" {
  description = "Discord bot Git repository URL"
  type        = string
  default     = "https://github.com/beckk97440/k8s-discord-bot.git"
}

variable "discord_bot_namespace" {
  description = "Namespace for Discord bot"
  type        = string
  default     = "lol-esports"
}

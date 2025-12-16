# League of Legends Esports Discord Bot

A Discord bot that automatically posts League of Legends esports match updates and news, with automated failover between a home NAS and AWS EC2.

## Features

- Posts live match updates from LoL Esports API
- Shares breaking news and announcements
- Automatic failover to AWS when home server is unavailable
- GitOps deployment with ArgoCD
- Multi-architecture Docker images (amd64/arm64)

## Architecture

### Primary Setup (Home NAS)
- **K3s** - Lightweight Kubernetes cluster
- **ArgoCD** - GitOps continuous deployment
- **Tailscale** - Secure networking and healthcheck exposure
- **Sealed Secrets** - Encrypted secrets in Git

### Failover Setup (AWS EC2)
- **Lambda Watchdog** - Monitors healthcheck every 5 minutes
- **EC2 Instance** - Automatically starts when primary is down
- **K3s + ArgoCD** - Same setup as primary for consistency
- **Terraform** - Infrastructure as code

### How Failover Works

1. **Healthcheck Service** runs on NAS, verifies:
   - K3s is running
   - Internet connectivity is available

2. **Lambda Function** checks healthcheck every 5 minutes:
   - If healthy and EC2 running → Stop EC2
   - If unhealthy and EC2 stopped → Start EC2

3. **ArgoCD** on both clusters syncs from the same GitHub repo, ensuring consistent deployments

## Project Structure

```
.
├── app/                    # Discord bot source code
│   └── bot.py             # Main bot logic
├── k8s/                   # Kubernetes manifests
│   ├── discord-bot/       # Bot deployment, PVC, secrets
│   └── base/              # ArgoCD application config
├── infrastructure/        # Terraform + healthcheck
│   ├── ec2.tf            # EC2 instance configuration
│   ├── lambda.tf         # Watchdog function
│   ├── user-data.sh      # EC2 bootstrap script
│   └── healthcheck/      # Healthcheck service for NAS
└── .github/workflows/     # CI/CD pipeline
    └── build-and-deploy.yaml
```

## Deployment Flow

1. **Push code** to `main` branch
2. **GitHub Actions** builds Docker image with git SHA tag
3. **CI/CD updates** Kubernetes manifest with new image tag
4. **ArgoCD detects** change and syncs to active cluster (NAS or EC2)
5. **Kubernetes** pulls new image and restarts bot

## Cost Optimization

With 99% uptime on home NAS:
- **Lambda**: Free tier
- **EventBridge**: Free tier
- **EC2 (stopped)**: ~$0.85/month (EBS storage only)
- **Total**: ~$1/month

## Setup

### Prerequisites
- Docker Hub account
- AWS account with credentials configured
- Tailscale account
- Discord bot token

### Deploy Infrastructure

```bash
cd infrastructure
terraform init
terraform apply
```

### Required Secrets

Create `infrastructure/terraform.tfvars` (gitignored):
```hcl
healthcheck_url    = "https://your-nas.tailscale.net/health"
tailscale_auth_key = "tskey-auth-..."
discord_token      = "your-discord-token"
match_channel_id   = "channel-id"
news_channel_id    = "channel-id"
```

### GitHub Secrets

Configure in repository settings:
- `DOCKER_USERNAME` - Docker Hub username
- `DOCKER_PASSWORD` - Docker Hub password/token

## Monitoring

- **Healthcheck**: `curl https://your-nas.tailscale.net/health`
- **Lambda Logs**: CloudWatch Logs
- **ArgoCD UI**: `kubectl port-forward -n argocd svc/argocd-server 8080:443`
- **Bot Logs**: `kubectl logs -n lol-esports -l app=discord-bot`

## Technologies

- **Kubernetes (K3s)** - Container orchestration
- **ArgoCD** - GitOps deployment
- **Docker** - Containerization
- **Terraform** - Infrastructure as code
- **Tailscale** - Secure networking
- **AWS Lambda** - Serverless monitoring
- **GitHub Actions** - CI/CD
- **Python** - Bot implementation

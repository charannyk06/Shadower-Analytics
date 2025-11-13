# Shadower Analytics - Deployment Guide

This guide covers the deployment process for the Shadower Analytics service across different environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [CI/CD Pipeline](#cicd-pipeline)
- [Infrastructure Setup](#infrastructure-setup)
- [Monitoring](#monitoring)
- [Rollback Procedures](#rollback-procedures)

## Prerequisites

### Required Tools

- Docker 20.10+
- Docker Compose 2.0+
- kubectl 1.25+
- Terraform 1.0+ (for infrastructure)
- AWS CLI (for cloud deployment)
- GitHub CLI (optional)

### Required Access

- GitHub repository access
- Container registry credentials (GitHub Container Registry)
- Kubernetes cluster access (kubeconfig)
- AWS credentials (for infrastructure provisioning)

## Local Development

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/charannyk06/Shadower-Analytics.git
   cd Shadower-Analytics
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

   **⚠️ SECURITY WARNING:**
   - Never commit `.env` files to version control
   - Change all default passwords and secrets before deploying
   - Generate strong JWT secrets: `openssl rand -hex 32`
   - Update `FLOWER_BASIC_AUTH` with secure credentials
   - Keep `terraform.tfvars` and `k8s/secrets.yaml` out of git

3. **Start services with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Flower (Celery monitoring): http://localhost:5555

### Stopping Services

```bash
docker-compose down
```

To also remove volumes:
```bash
docker-compose down -v
```

## Docker Deployment

### Building Images

**Backend:**
```bash
cd backend
docker build -t shadower-analytics-backend:latest .
```

**Frontend:**
```bash
cd frontend
docker build -t shadower-analytics-frontend:latest .
```

### Pushing to Registry

```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Tag images
docker tag shadower-analytics-backend:latest ghcr.io/charannyk06/shadower-analytics-backend:latest
docker tag shadower-analytics-frontend:latest ghcr.io/charannyk06/shadower-analytics-frontend:latest

# Push images
docker push ghcr.io/charannyk06/shadower-analytics-backend:latest
docker push ghcr.io/charannyk06/shadower-analytics-frontend:latest
```

## Kubernetes Deployment

### Initial Setup

1. **Create namespace and resources**
   ```bash
   ./scripts/setup-k8s.sh production
   ```

2. **Configure secrets**
   ```bash
   # Copy example secrets file
   cp k8s/secrets.yaml.example k8s/secrets.yaml

   # Edit secrets with actual values
   vim k8s/secrets.yaml

   # Apply secrets
   kubectl apply -f k8s/secrets.yaml
   ```

### Manual Deployment

```bash
# Apply all Kubernetes resources
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/hpa.yaml
```

### Using Deployment Script

```bash
# Deploy to staging
./scripts/deploy.sh staging v1.0.0

# Deploy to production
./scripts/deploy.sh production v1.0.0
```

### Verify Deployment

```bash
# Check pod status
kubectl get pods -n analytics

# Check deployment status
kubectl get deployments -n analytics

# Check services
kubectl get services -n analytics

# Check ingress
kubectl get ingress -n analytics

# View logs
kubectl logs -f deployment/analytics-backend -n analytics
kubectl logs -f deployment/analytics-frontend -n analytics
```

## CI/CD Pipeline

### GitHub Actions Workflow

The deployment pipeline is automated through GitHub Actions (`.github/workflows/deploy.yml`).

**Workflow Stages:**

1. **Test** - Runs on all pull requests and pushes
   - Backend unit tests
   - Frontend linting and build
   - Code coverage reporting

2. **Security Scan** - Runs after tests
   - Trivy vulnerability scanning
   - SARIF upload to GitHub Security

3. **Build and Push** - Runs on push to main/production
   - Builds Docker images
   - Pushes to GitHub Container Registry
   - Tags with branch name and commit SHA

4. **Deploy to Staging** - Runs on push to main
   - Updates staging Kubernetes deployments
   - Runs smoke tests

5. **Deploy to Production** - Runs on push to production
   - Updates production Kubernetes deployments
   - Verifies deployment
   - Sends notifications

### Triggering Deployments

**To Staging:**
```bash
git push origin main
```

**To Production:**
```bash
git push origin production
```

### Required GitHub Secrets

Configure these secrets in your GitHub repository settings:

- `KUBE_CONFIG_STAGING` - Kubernetes config for staging
- `KUBE_CONFIG_PRODUCTION` - Kubernetes config for production
- `NEXT_PUBLIC_API_URL` - Frontend API URL
- `NEXT_PUBLIC_WS_URL` - Frontend WebSocket URL

## Infrastructure Setup

### Terraform Configuration

1. **Initialize Terraform**
   ```bash
   cd terraform
   terraform init
   ```

2. **Configure variables**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

3. **Plan infrastructure**
   ```bash
   terraform plan
   ```

4. **Apply infrastructure**
   ```bash
   terraform apply
   ```

### Infrastructure Components

- **VPC** - Isolated network for resources
- **RDS PostgreSQL** - Managed database service
- **ElastiCache Redis** - Managed cache service
- **S3 Bucket** - Storage for exports
- **EKS Cluster** - Kubernetes cluster (optional)
- **CloudWatch** - Logging and monitoring

## Monitoring

### Prometheus

Prometheus is configured to scrape metrics from:
- Backend API (`/metrics` endpoint)
- PostgreSQL (via postgres-exporter)
- Redis (via redis-exporter)
- Kubernetes nodes and pods

**Configuration:** `monitoring/prometheus.yml`

### Grafana Dashboards

Import the provided dashboard:
```bash
kubectl apply -f monitoring/grafana-dashboard.json
```

### Alerts

Alert rules are defined in `monitoring/alerts/backend_alerts.yml`.

**Key alerts:**
- High error rate (>5%)
- High response time (>1s)
- High CPU/Memory usage
- Pod not ready
- Database connection issues
- Celery queue backlog

### Viewing Metrics

Access Grafana dashboard:
```bash
kubectl port-forward -n monitoring svc/grafana 3000:80
```

Then open: http://localhost:3000

## Rollback Procedures

### Automatic Rollback

If deployment fails health checks, GitHub Actions will automatically rollback.

### Manual Rollback

**Rollback to previous version:**
```bash
./scripts/rollback.sh production
```

**Rollback to specific revision:**
```bash
# List revisions
kubectl rollout history deployment/analytics-backend -n analytics

# Rollback to specific revision
./scripts/rollback.sh production 3
```

### Emergency Rollback

```bash
# Rollback backend immediately
kubectl rollout undo deployment/analytics-backend -n analytics

# Rollback frontend immediately
kubectl rollout undo deployment/analytics-frontend -n analytics
```

## Environment Configuration

### Development
- Single replica
- Local database
- Debug mode enabled
- Hot reload enabled

### Staging
- 2 replicas
- Managed RDS database
- Production-like configuration
- Auto-scaling enabled

### Production
- 3+ replicas
- Multi-AZ RDS database
- Full monitoring and alerts
- Auto-scaling (2-10 pods)
- High availability

## Health Checks

### Backend Health Endpoint

```bash
curl https://analytics.shadower.ai/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

### Kubernetes Health Checks

- **Liveness Probe:** `/health` - Checked every 30s
- **Readiness Probe:** `/health` - Checked every 10s

## Troubleshooting

### Pod Not Starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n analytics

# Check logs
kubectl logs <pod-name> -n analytics

# Check previous container logs
kubectl logs <pod-name> -n analytics --previous
```

### Database Connection Issues

```bash
# Test database connectivity from pod
kubectl exec -it <backend-pod> -n analytics -- psql $DATABASE_URL

# Check database logs
kubectl logs -n analytics deployment/analytics-backend | grep -i database
```

### High Memory Usage

```bash
# Check memory usage
kubectl top pods -n analytics

# Describe HPA
kubectl describe hpa -n analytics

# Check resource limits
kubectl describe deployment analytics-backend -n analytics
```

## Support

For issues or questions:
- Create an issue in GitHub repository
- Check logs in CloudWatch or Kubernetes
- Review Grafana dashboards for metrics
- Contact the DevOps team

## Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Prometheus Documentation](https://prometheus.io/docs/)

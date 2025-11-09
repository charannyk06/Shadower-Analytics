# Specification: Deployment Configuration

## Overview
Define deployment configuration for analytics service including Docker, Kubernetes, CI/CD, and environment management.

## Technical Requirements

### Docker Configuration

#### Dockerfile - Backend API
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### Dockerfile - Frontend
```dockerfile
# frontend/Dockerfile
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Copy application code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app

# Install serve
RUN npm install -g serve

# Copy built application
COPY --from=builder /app/out ./out

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001
USER nextjs

# Expose port
EXPOSE 3000

# Start application
CMD ["serve", "-s", "out", "-l", "3000"]
```

#### Docker Compose
```yaml
# docker-compose.yml
version: '3.9'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: analytics
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/analytics
      REDIS_URL: redis://redis:6379
      JWT_SECRET: ${JWT_SECRET}
      ENVIRONMENT: ${ENVIRONMENT}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
      NEXT_PUBLIC_WS_URL: ws://backend:8000/ws
    depends_on:
      - backend
    ports:
      - "3000:3000"
    restart: unless-stopped

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A tasks worker -l info
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/analytics
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A tasks beat -l info
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/analytics
      REDIS_URL: redis://redis:6379
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Kubernetes Configuration

#### Deployment - Backend
```yaml
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: analytics-backend
  namespace: analytics
spec:
  replicas: 3
  selector:
    matchLabels:
      app: analytics-backend
  template:
    metadata:
      labels:
        app: analytics-backend
    spec:
      containers:
      - name: backend
        image: shadower/analytics-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: analytics-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: analytics-config
              key: redis-url
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: analytics-secrets
              key: jwt-secret
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: analytics-backend-service
  namespace: analytics
spec:
  selector:
    app: analytics-backend
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

#### Ingress Configuration
```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: analytics-ingress
  namespace: analytics
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/websocket-services: "analytics-backend-service"
spec:
  tls:
  - hosts:
    - analytics.shadower.ai
    secretName: analytics-tls
  rules:
  - host: analytics.shadower.ai
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: analytics-backend-service
            port:
              number: 80
      - path: /ws
        pathType: Prefix
        backend:
          service:
            name: analytics-backend-service
            port:
              number: 80
      - path: /
        pathType: Prefix
        backend:
          service:
            name: analytics-frontend-service
            port:
              number: 80
```

#### Horizontal Pod Autoscaler
```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: analytics-backend-hpa
  namespace: analytics
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: analytics-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### CI/CD Pipeline

#### GitHub Actions Workflow
```yaml
# .github/workflows/deploy.yml
name: Deploy Analytics Service

on:
  push:
    branches: [main, production]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r backend/requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        cd backend
        pytest --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Build and push Backend
      uses: docker/build-push-action@v4
      with:
        context: ./backend
        push: true
        tags: |
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:latest
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:${{ github.sha }}
    
    - name: Build and push Frontend
      uses: docker/build-push-action@v4
      with:
        context: ./frontend
        push: true
        tags: |
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:latest
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:${{ github.sha }}

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/production'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to Kubernetes
      uses: azure/k8s-deploy@v4
      with:
        manifests: |
          k8s/backend-deployment.yaml
          k8s/frontend-deployment.yaml
          k8s/ingress.yaml
        images: |
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:${{ github.sha }}
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:${{ github.sha }}
```

### Environment Configuration

#### Environment Variables
```bash
# .env.example
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=analytics
DB_USER=analytics_user
DB_PASSWORD=secure_password

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Main App Integration
MAIN_APP_API_URL=https://api.shadower.ai
SHARED_JWT_SECRET=shared-secret-between-services

# Email
SENDGRID_API_KEY=your-sendgrid-key
FROM_EMAIL=analytics@shadower.ai

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
NEW_RELIC_LICENSE_KEY=your-new-relic-key

# Feature Flags
ENABLE_PREDICTIVE_ANALYTICS=true
ENABLE_REALTIME_UPDATES=true
ENABLE_EXPORT_FEATURE=true

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_PER_HOUR=5000
```

### Terraform Infrastructure
```hcl
# terraform/main.tf
terraform {
  required_version = ">= 1.0"
  
  backend "s3" {
    bucket = "shadower-terraform-state"
    key    = "analytics/terraform.tfstate"
    region = "us-west-2"
  }
}

provider "aws" {
  region = var.aws_region
}

# RDS Instance for Analytics
resource "aws_db_instance" "analytics" {
  identifier     = "shadower-analytics"
  engine         = "postgres"
  engine_version = "15.3"
  instance_class = "db.t3.medium"
  
  allocated_storage     = 100
  storage_encrypted     = true
  storage_type          = "gp3"
  
  db_name  = "analytics"
  username = var.db_username
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.analytics_db.id]
  db_subnet_group_name   = aws_db_subnet_group.analytics.name
  
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  multi_az               = true
  deletion_protection    = true
  skip_final_snapshot    = false
  
  tags = {
    Name        = "shadower-analytics-db"
    Environment = var.environment
  }
}

# ElastiCache for Redis
resource "aws_elasticache_cluster" "analytics" {
  cluster_id           = "shadower-analytics-cache"
  engine               = "redis"
  node_type            = "cache.t3.medium"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  
  subnet_group_name = aws_elasticache_subnet_group.analytics.name
  security_group_ids = [aws_security_group.analytics_cache.id]
  
  tags = {
    Name        = "shadower-analytics-cache"
    Environment = var.environment
  }
}

# EKS Cluster
resource "aws_eks_cluster" "analytics" {
  name     = "shadower-analytics"
  role_arn = aws_iam_role.eks_cluster.arn
  
  vpc_config {
    subnet_ids = aws_subnet.analytics[*].id
  }
  
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
}

# S3 Bucket for Exports
resource "aws_s3_bucket" "exports" {
  bucket = "shadower-analytics-exports"
  
  tags = {
    Name        = "Analytics Exports"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "exports" {
  bucket = aws_s3_bucket.exports.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "exports" {
  bucket = aws_s3_bucket.exports.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

### Monitoring Setup

#### Prometheus Configuration
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'analytics-backend'
    static_configs:
      - targets: ['analytics-backend:8000']
    metrics_path: '/metrics'
  
  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']
  
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']
  
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

## Deployment Scripts

### Deploy Script
```bash
#!/bin/bash
# scripts/deploy.sh

set -e

ENVIRONMENT=$1
VERSION=$2

if [ -z "$ENVIRONMENT" ] || [ -z "$VERSION" ]; then
    echo "Usage: ./deploy.sh <environment> <version>"
    exit 1
fi

echo "Deploying version $VERSION to $ENVIRONMENT..."

# Build and push images
docker build -t shadower/analytics-backend:$VERSION ./backend
docker build -t shadower/analytics-frontend:$VERSION ./frontend

docker push shadower/analytics-backend:$VERSION
docker push shadower/analytics-frontend:$VERSION

# Update Kubernetes
kubectl set image deployment/analytics-backend \
    backend=shadower/analytics-backend:$VERSION \
    -n analytics

kubectl set image deployment/analytics-frontend \
    frontend=shadower/analytics-frontend:$VERSION \
    -n analytics

# Wait for rollout
kubectl rollout status deployment/analytics-backend -n analytics
kubectl rollout status deployment/analytics-frontend -n analytics

echo "Deployment complete!"
```

## Implementation Priority
1. Docker configuration
2. Local development setup
3. CI/CD pipeline
4. Kubernetes deployment
5. Production monitoring

## Success Metrics
- Deployment success rate > 99%
- Rollback time < 5 minutes
- Zero-downtime deployments
- Auto-scaling response time < 30 seconds
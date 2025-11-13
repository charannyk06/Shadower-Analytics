#!/bin/bash
# Setup script for Kubernetes resources
# Usage: ./setup-k8s.sh <environment>

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check arguments
if [ -z "$1" ]; then
    print_error "Usage: ./setup-k8s.sh <environment>"
    print_error "Example: ./setup-k8s.sh production"
    exit 1
fi

ENVIRONMENT=$1

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    print_error "Environment must be one of: development, staging, production"
    exit 1
fi

print_info "Setting up Kubernetes resources for $ENVIRONMENT environment..."

# Step 1: Create namespace
print_info "Creating namespace..."
kubectl apply -f k8s/namespace.yaml

# Step 2: Create ConfigMap
print_info "Creating ConfigMap..."
kubectl apply -f k8s/configmap.yaml

# Step 3: Create Secrets (prompt user if not exists)
print_info "Checking for secrets..."
if ! kubectl get secret analytics-secrets -n analytics &> /dev/null; then
    print_warning "Secrets not found. Please create secrets manually:"
    print_warning "  1. Copy k8s/secrets.yaml.example to k8s/secrets.yaml"
    print_warning "  2. Update all CHANGE_ME values with actual secrets"
    print_warning "  3. Run: kubectl apply -f k8s/secrets.yaml"
    print_warning ""
    read -p "Have you created the secrets? (yes/no): " SECRETS_READY

    if [ "$SECRETS_READY" != "yes" ]; then
        print_error "Please create secrets before continuing"
        exit 1
    fi
else
    print_info "Secrets already exist"
fi

# Step 4: Deploy backend
print_info "Deploying backend..."
kubectl apply -f k8s/backend-deployment.yaml

# Step 5: Deploy frontend
print_info "Deploying frontend..."
kubectl apply -f k8s/frontend-deployment.yaml

# Step 6: Create Ingress
print_info "Creating Ingress..."
kubectl apply -f k8s/ingress.yaml

# Step 7: Create HPA
print_info "Creating Horizontal Pod Autoscalers..."
kubectl apply -f k8s/hpa.yaml

# Wait for deployments
print_info "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=5m deployment/analytics-backend -n analytics
kubectl wait --for=condition=available --timeout=5m deployment/analytics-frontend -n analytics

# Display status
print_info "\nDeployment status:"
kubectl get deployments -n analytics
kubectl get pods -n analytics
kubectl get services -n analytics
kubectl get ingress -n analytics

print_info "\n✅ Kubernetes setup completed successfully!"

exit 0

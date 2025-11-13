#!/bin/bash
# Deployment script for Shadower Analytics
# Usage: ./deploy.sh <environment> <version>

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
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
if [ -z "$1" ] || [ -z "$2" ]; then
    print_error "Usage: ./deploy.sh <environment> <version>"
    print_error "Example: ./deploy.sh production v1.2.3"
    exit 1
fi

ENVIRONMENT=$1
VERSION=$2

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    print_error "Environment must be one of: development, staging, production"
    exit 1
fi

# Set registry based on environment
REGISTRY="ghcr.io/charannyk06/shadower-analytics"

# Set namespace based on environment
if [ "$ENVIRONMENT" == "production" ]; then
    NAMESPACE="analytics"
elif [ "$ENVIRONMENT" == "staging" ]; then
    NAMESPACE="analytics-staging"
else
    NAMESPACE="analytics-dev"
fi

print_info "Starting deployment to $ENVIRONMENT environment..."
print_info "Version: $VERSION"
print_info "Namespace: $NAMESPACE"

# Step 1: Build Docker images
print_info "Building Docker images..."
docker build -t $REGISTRY-backend:$VERSION ./backend
docker build -t $REGISTRY-frontend:$VERSION ./frontend

# Tag as latest for the environment
docker tag $REGISTRY-backend:$VERSION $REGISTRY-backend:$ENVIRONMENT-latest
docker tag $REGISTRY-frontend:$VERSION $REGISTRY-frontend:$ENVIRONMENT-latest

# Step 2: Push images to registry
print_info "Pushing images to registry..."
docker push $REGISTRY-backend:$VERSION
docker push $REGISTRY-backend:$ENVIRONMENT-latest
docker push $REGISTRY-frontend:$VERSION
docker push $REGISTRY-frontend:$ENVIRONMENT-latest

print_info "Images pushed successfully"

# Step 3: Update Kubernetes deployments
print_info "Updating Kubernetes deployments..."

# Update backend deployment
kubectl set image deployment/analytics-backend \
    backend=$REGISTRY-backend:$VERSION \
    -n $NAMESPACE

# Update frontend deployment
kubectl set image deployment/analytics-frontend \
    frontend=$REGISTRY-frontend:$VERSION \
    -n $NAMESPACE

print_info "Deployment updated, waiting for rollout..."

# Step 4: Wait for rollout to complete
print_info "Waiting for backend rollout..."
kubectl rollout status deployment/analytics-backend -n $NAMESPACE --timeout=10m

print_info "Waiting for frontend rollout..."
kubectl rollout status deployment/analytics-frontend -n $NAMESPACE --timeout=10m

# Step 5: Verify deployment
print_info "Verifying deployment..."

# Check pod status
BACKEND_PODS=$(kubectl get pods -n $NAMESPACE -l app=analytics-backend --field-selector=status.phase=Running --no-headers | wc -l)
FRONTEND_PODS=$(kubectl get pods -n $NAMESPACE -l app=analytics-frontend --field-selector=status.phase=Running --no-headers | wc -l)

print_info "Backend pods running: $BACKEND_PODS"
print_info "Frontend pods running: $FRONTEND_PODS"

if [ "$BACKEND_PODS" -lt 1 ] || [ "$FRONTEND_PODS" -lt 1 ]; then
    print_error "Deployment verification failed - not all pods are running"
    exit 1
fi

# Step 6: Run smoke tests (if environment is not development)
if [ "$ENVIRONMENT" != "development" ]; then
    print_info "Running smoke tests..."

    # Wait a bit for services to stabilize
    sleep 30

    # Get the service URL based on environment
    if [ "$ENVIRONMENT" == "production" ]; then
        SERVICE_URL="https://analytics.shadower.ai"
    else
        SERVICE_URL="https://staging-analytics.shadower.ai"
    fi

    # Check health endpoint
    HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" $SERVICE_URL/health)

    if [ "$HEALTH_STATUS" == "200" ]; then
        print_info "Health check passed"
    else
        print_warning "Health check returned status: $HEALTH_STATUS"
    fi
fi

# Step 7: Create deployment record
print_info "Recording deployment..."
kubectl annotate deployment/analytics-backend \
    kubernetes.io/change-cause="Deployed version $VERSION to $ENVIRONMENT" \
    -n $NAMESPACE --overwrite

kubectl annotate deployment/analytics-frontend \
    kubernetes.io/change-cause="Deployed version $VERSION to $ENVIRONMENT" \
    -n $NAMESPACE --overwrite

print_info "Deployment completed successfully!"
print_info "Version $VERSION is now live in $ENVIRONMENT"

# Display current status
print_info "\nCurrent deployment status:"
kubectl get deployments -n $NAMESPACE
kubectl get pods -n $NAMESPACE

exit 0

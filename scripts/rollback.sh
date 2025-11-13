#!/bin/bash
# Rollback script for Shadower Analytics
# Usage: ./rollback.sh <environment> [revision]

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
if [ -z "$1" ]; then
    print_error "Usage: ./rollback.sh <environment> [revision]"
    print_error "Example: ./rollback.sh production"
    print_error "Example: ./rollback.sh production 3"
    exit 1
fi

ENVIRONMENT=$1
REVISION=${2:-0}  # Default to previous revision (0 means previous)

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
    print_error "Environment must be one of: development, staging, production"
    exit 1
fi

# Set namespace based on environment
if [ "$ENVIRONMENT" == "production" ]; then
    NAMESPACE="analytics"
elif [ "$ENVIRONMENT" == "staging" ]; then
    NAMESPACE="analytics-staging"
else
    NAMESPACE="analytics-dev"
fi

print_warning "⚠️  ROLLBACK INITIATED ⚠️"
print_info "Environment: $ENVIRONMENT"
print_info "Namespace: $NAMESPACE"

# Show current revision history
print_info "\nCurrent revision history for backend:"
kubectl rollout history deployment/analytics-backend -n $NAMESPACE

print_info "\nCurrent revision history for frontend:"
kubectl rollout history deployment/analytics-frontend -n $NAMESPACE

# Confirm rollback in production
if [ "$ENVIRONMENT" == "production" ]; then
    print_warning "\n⚠️  You are about to rollback PRODUCTION deployment ⚠️"
    read -p "Are you sure you want to proceed? (yes/no): " CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        print_info "Rollback cancelled"
        exit 0
    fi
fi

# Perform rollback
print_info "\nPerforming rollback..."

if [ "$REVISION" -eq 0 ]; then
    # Rollback to previous revision
    print_info "Rolling back backend to previous revision..."
    kubectl rollout undo deployment/analytics-backend -n $NAMESPACE

    print_info "Rolling back frontend to previous revision..."
    kubectl rollout undo deployment/analytics-frontend -n $NAMESPACE
else
    # Rollback to specific revision
    print_info "Rolling back backend to revision $REVISION..."
    kubectl rollout undo deployment/analytics-backend --to-revision=$REVISION -n $NAMESPACE

    print_info "Rolling back frontend to revision $REVISION..."
    kubectl rollout undo deployment/analytics-frontend --to-revision=$REVISION -n $NAMESPACE
fi

# Wait for rollback to complete
print_info "\nWaiting for backend rollback to complete..."
kubectl rollout status deployment/analytics-backend -n $NAMESPACE --timeout=5m

print_info "Waiting for frontend rollback to complete..."
kubectl rollout status deployment/analytics-frontend -n $NAMESPACE --timeout=5m

# Verify rollback
print_info "\nVerifying rollback..."

BACKEND_PODS=$(kubectl get pods -n $NAMESPACE -l app=analytics-backend --field-selector=status.phase=Running --no-headers | wc -l)
FRONTEND_PODS=$(kubectl get pods -n $NAMESPACE -l app=analytics-frontend --field-selector=status.phase=Running --no-headers | wc -l)

print_info "Backend pods running: $BACKEND_PODS"
print_info "Frontend pods running: $FRONTEND_PODS"

if [ "$BACKEND_PODS" -lt 1 ] || [ "$FRONTEND_PODS" -lt 1 ]; then
    print_error "Rollback verification failed - not all pods are running"
    exit 1
fi

print_info "\n✅ Rollback completed successfully!"
print_info "\nCurrent deployment status:"
kubectl get deployments -n $NAMESPACE
kubectl get pods -n $NAMESPACE

exit 0

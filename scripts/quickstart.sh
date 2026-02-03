#!/bin/bash

# TalkAI Quick Start Script
# This script helps you quickly get the TalkAI platform running

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    local missing_deps=()
    
    # Check Docker
    if ! command_exists docker; then
        missing_deps+=("Docker")
    else
        print_success "Docker found: $(docker --version | awk '{print $3}' | sed 's/,//')"
    fi
    
    # Check Docker Compose
    if ! command_exists docker-compose; then
        if docker compose version >/dev/null 2>&1; then
            print_success "Docker Compose plugin found: $(docker compose version --short)"
        else
            missing_deps+=("Docker Compose")
        fi
    else
        print_success "Docker Compose found: $(docker-compose --version | awk '{print $3}' | sed 's/,//')"
    fi
    
    # Check Ollama (optional but recommended)
    if command_exists ollama; then
        print_success "Ollama found: $(ollama --version | awk '{print $3}')"
        OLLAMA_LOCAL=true
    else
        print_warning "Ollama not found locally. Will use containerized Ollama or external instance."
        OLLAMA_LOCAL=false
    fi
    
    # Check curl
    if ! command_exists curl; then
        missing_deps+=("curl")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing required dependencies: ${missing_deps[*]}"
        echo ""
        echo "Please install the missing dependencies:"
        echo "  - Docker: https://docs.docker.com/get-docker/"
        echo "  - Docker Compose: https://docs.docker.com/compose/install/"
        echo "  - curl: usually pre-installed or via package manager"
        echo ""
        echo "Optional:"
        echo "  - Ollama: https://ollama.ai/download"
        exit 1
    fi
    
    print_success "All prerequisites satisfied!"
}

# Setup environment file
setup_environment() {
    print_status "Setting up environment..."
    
    ENV_FILE=".env"
    
    if [ -f "$ENV_FILE" ]; then
        print_warning ".env file already exists"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Keeping existing .env file"
            return
        fi
    fi
    
    # Generate random secrets
    JWT_SECRET=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)
    DB_PASSWORD=$(openssl rand -base64 24 2>/dev/null || head -c 24 /dev/urandom | base64)
    ADMIN_PASSWORD=$(openssl rand -base64 16 2>/dev/null || head -c 16 /dev/urandom | base64 | cut -c1-12)
    
    cat > "$ENV_FILE" << EOF
# TalkAI Environment Configuration
# Generated on $(date)

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://talkai:${DB_PASSWORD}@postgres:5432/talkai
DB_PASSWORD=${DB_PASSWORD}
DB_USER=talkai
DB_NAME=talkai

# Redis
REDIS_URL=redis://redis:6379

# JWT Configuration
JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60

# Admin Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=${ADMIN_PASSWORD}

# Ollama Configuration
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_TIMEOUT=120
DEFAULT_MODEL=llama2

# Feature Flags
ENABLE_MOCK_RESPONSES=false
ENABLE_RATE_LIMITING=true
ENABLE_AUDIT_LOG=true
CORS_ORIGINS=*

# Monitoring
METRICS_ENABLED=true
METRICS_PORT=9090
EOF
    
    print_success "Created .env file with secure secrets"
    print_status "Admin credentials:"
    echo "  Username: admin"
    echo "  Password: ${ADMIN_PASSWORD}"
    echo ""
    print_warning "Save these credentials! They won't be shown again."
}

# Start the platform
start_platform() {
    print_status "Starting TalkAI platform..."
    
    # Determine which compose file to use
    if [ -f "docker-compose.yml" ]; then
        COMPOSE_FILE="docker-compose.yml"
    elif [ -f "docker-compose.yaml" ]; then
        COMPOSE_FILE="docker-compose.yaml"
    else
        print_error "No docker-compose file found!"
        exit 1
    fi
    
    # Check if we should use Docker Compose plugin or standalone
    if command_exists docker-compose; then
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi
    
    # Pull latest images
    print_status "Pulling latest images..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" pull
    
    # Start services
    print_status "Starting services (this may take a few minutes)..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 5
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8000/health >/dev/null 2>&1; then
            print_success "API is ready!"
            break
        fi
        
        print_status "Waiting for API... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        print_warning "API might not be ready yet. Check logs with: $COMPOSE_CMD -f $COMPOSE_FILE logs -f api"
    fi
}

# Pull default model in Ollama
setup_ollama() {
    if [ "$OLLAMA_LOCAL" = true ]; then
        print_status "Checking Ollama models..."
        
        if ollama list 2>/dev/null | grep -q "llama2"; then
            print_success "llama2 model already available"
        else
            print_status "Pulling llama2 model (this may take several minutes)..."
            ollama pull llama2
            print_success "llama2 model ready!"
        fi
    else
        print_status "Using containerized Ollama..."
        print_warning "You'll need to pull models manually after startup:"
        echo "  docker exec -it talkai-ollama-1 ollama pull llama2"
    fi
}

# Show access information
show_access_info() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║            TalkAI Platform is Ready!                         ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Access URLs:"
    echo "  🌐 Web Interface:     http://localhost:3000"
    echo "  🔌 API Endpoint:      http://localhost:8000"
    echo "  📚 API Docs:          http://localhost:8000/docs"
    echo "  📊 Metrics:           http://localhost:9090"
    echo ""
    echo "Default Credentials:"
    
    # Read admin credentials from .env
    if [ -f ".env" ]; then
        ADMIN_USER=$(grep "ADMIN_USERNAME=" .env | cut -d'=' -f2)
        ADMIN_PASS=$(grep "ADMIN_PASSWORD=" .env | cut -d'=' -f2)
        echo "  Username: ${ADMIN_USER:-admin}"
        echo "  Password: ${ADMIN_PASS:-admin}"
    else
        echo "  Username: admin"
        echo "  Password: (check your .env file)"
    fi
    echo ""
    echo "Quick Commands:"
    echo "  View logs:          docker-compose logs -f"
    echo "  Stop platform:      docker-compose down"
    echo "  Restart:            docker-compose restart"
    echo "  Health check:       ./scripts/health-check.sh"
    echo ""
    echo "Next Steps:"
    if [ "$OLLAMA_LOCAL" = false ]; then
        echo "  1. Pull an Ollama model: docker exec -it talkai-ollama-1 ollama pull llama2"
    fi
    echo "  2. Log in at http://localhost:3000"
    echo "  3. Start chatting!"
    echo ""
}

# Main execution
main() {
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║          TalkAI Platform - Quick Start                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    
    check_prerequisites
    echo ""
    
    setup_environment
    echo ""
    
    start_platform
    echo ""
    
    setup_ollama
    echo ""
    
    show_access_info
}

# Handle script interruption
trap 'print_error "Setup interrupted"; exit 1' INT TERM

# Run main function
main

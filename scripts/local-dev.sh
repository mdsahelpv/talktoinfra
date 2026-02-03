#!/bin/bash

# TalkAI Platform - Local Development Script
# Hybrid approach: Infrastructure in Docker, services running locally

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_COMPOSE="$PROJECT_ROOT/docker-compose.yml"
ENV_FILE="$PROJECT_ROOT/.env"

# Python/Conda configuration
PYTHON_CMD=""
PYTHON_VERSION=""
USE_CONDA=false
CONDA_CMD=""
SHARED_ENV_NAME="talkai-dev"

# Service configurations
SERVICES=(
    "api-gateway:8000:main:app"
    "ai-router:8001:main:app"
    "action-engine:8002:main:app"
    "policy-engine:8003:main:app"
    "ingestion-service:8004:main:app"
    "audit-service:8005:main:app"
    "agent-service:8006:app.main:app"
    "discovery-service:8007:app.main:app"
)

# Function to print colored output
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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect conda installation
detect_conda() {
    print_status "Checking for conda..."
    
    # Check for conda in common locations
    if command_exists conda; then
        CONDA_CMD="conda"
        USE_CONDA=true
        print_success "Found conda"
        return 0
    fi
    
    # Check common conda installation paths
    if [ -f "$HOME/miniconda3/bin/conda" ]; then
        CONDA_CMD="$HOME/miniconda3/bin/conda"
        USE_CONDA=true
        print_success "Found conda at $CONDA_CMD"
        return 0
    fi
    
    if [ -f "$HOME/anaconda3/bin/conda" ]; then
        CONDA_CMD="$HOME/anaconda3/bin/conda"
        USE_CONDA=true
        print_success "Found conda at $CONDA_CMD"
        return 0
    fi
    
    if [ -f "/opt/conda/bin/conda" ]; then
        CONDA_CMD="/opt/conda/bin/conda"
        USE_CONDA=true
        print_success "Found conda at $CONDA_CMD"
        return 0
    fi
    
    return 1
}

# Function to detect suitable Python version
detect_python() {
    print_status "Detecting Python version..."
    
    # Prefer conda if available
    if detect_conda; then
        print_success "Using conda for environment management"
        return 0
    fi
    
    # Fall back to system Python
    print_status "Conda not found, using system Python..."
    
    # Check for Python 3.12 first (preferred for compatibility)
    if command_exists python3.12; then
        PYTHON_CMD="python3.12"
        PYTHON_VERSION="$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)"
        print_success "Found Python $PYTHON_VERSION"
        return 0
    fi
    
    # Check for Python 3.11
    if command_exists python3.11; then
        PYTHON_CMD="python3.11"
        PYTHON_VERSION="$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)"
        print_success "Found Python $PYTHON_VERSION"
        return 0
    fi
    
    # Check default python3
    if command_exists python3; then
        local version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
        local major=$(echo $version | cut -d'.' -f1)
        local minor=$(echo $version | cut -d'.' -f2)
        
        # Check if it's Python 3.13 or higher
        if [ "$major" -eq 3 ] && [ "$minor" -ge 13 ]; then
            print_warning "Python $version detected - may have compatibility issues with some packages"
            print_warning "Consider installing Python 3.11 or 3.12 for better compatibility"
            PYTHON_CMD="python3"
            PYTHON_VERSION="$version"
            return 0
        elif [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; then
            PYTHON_CMD="python3"
            PYTHON_VERSION="$version"
            print_success "Found Python $PYTHON_VERSION"
            return 0
        else
            print_error "Python 3.11+ required, found $version"
            return 1
        fi
    fi
    
    print_error "Python 3.11+ not found"
    return 1
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    local missing=()
    
    if ! command_exists docker; then
        missing+=("docker")
    fi
    
    if ! command_exists docker-compose; then
        missing+=("docker-compose")
    fi
    
    if ! command_exists npm; then
        missing+=("npm")
    fi
    
    if [ ${#missing[@]} -ne 0 ]; then
        print_error "Missing prerequisites: ${missing[*]}"
        print_error "Please install the missing tools and try again."
        exit 1
    fi
    
    # Check Python separately with version detection
    if ! detect_python; then
        print_error "Python 3.11+ is required. Please install Python 3.11 or 3.12"
        print_error "Ubuntu/Debian: sudo apt install python3.12 python3.12-venv"
        print_error "macOS: brew install python@3.12"
        exit 1
    fi
    
    print_success "All prerequisites found"
}

# Function to setup environment file
setup_environment() {
    print_status "Setting up environment for local development..."
    
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$PROJECT_ROOT/.env.example" ]; then
            cp "$PROJECT_ROOT/.env.example" "$ENV_FILE"
            print_success "Created .env from .env.example"
        else
            print_error "No .env or .env.example file found!"
            exit 1
        fi
    fi
    
    # Create local development .env
    LOCAL_ENV="$PROJECT_ROOT/.env.local"
    
    cat > "$LOCAL_ENV" << EOF
# Local Development Environment
# Generated by local-dev.sh

# Override Docker service names with localhost
DB_HOST=localhost
REDIS_HOST=localhost
QDRANT_HOST=localhost
NATS_URL=nats://localhost:4222

# Keep other settings from main .env
$(grep -v "^DB_HOST=\|^REDIS_HOST=\|^QDRANT_HOST=\|^NATS_URL=" "$ENV_FILE" 2>/dev/null || true)

# Service URLs for local development
API_GATEWAY_URL=http://localhost:8000
AI_ROUTER_URL=http://localhost:8001
ACTION_ENGINE_URL=http://localhost:8002
POLICY_ENGINE_URL=http://localhost:8003
INGESTION_SERVICE_URL=http://localhost:8004
AUDIT_SERVICE_URL=http://localhost:8005
AGENT_SERVICE_URL=http://localhost:8006
DISCOVERY_SERVICE_URL=http://localhost:8007

# Frontend (empty API_URL to use Vite proxy)
VITE_API_URL=
VITE_WS_URL=ws://localhost:8000
EOF
    
    print_success "Created .env.local for local development"
}

# Function to start infrastructure services
start_infrastructure() {
    print_status "Starting infrastructure services (PostgreSQL, Redis, Qdrant, NATS)..."
    
    cd "$PROJECT_ROOT"
    
    # Check if infrastructure is already running
    if docker-compose ps | grep -q "postgres\|redis\|qdrant\|nats"; then
        print_status "Restarting infrastructure services..."
        docker-compose down
        docker-compose up -d postgres redis qdrant nats
    else
        docker-compose up -d postgres redis qdrant nats
    fi
    
    print_status "Waiting for infrastructure to be healthy..."
    sleep 5
    
    # Check health
    local retries=30
    local count=0
    
    while [ $count -lt $retries ]; do
        if docker-compose ps | grep -E "postgres.*healthy|redis.*healthy|qdrant.*healthy" >/dev/null 2>&1; then
            print_success "Infrastructure services are healthy"
            return 0
        fi
        
        count=$((count + 1))
        if [ $count -eq $retries ]; then
            print_error "Infrastructure services failed to become healthy"
            print_error "Check logs with: docker-compose logs"
            exit 1
        fi
        
        echo -n "."
        sleep 2
    done
}

# Function to setup shared Python environment (conda or venv)
setup_venv() {
    if [ "$USE_CONDA" = true ]; then
        # Use shared conda environment
        setup_conda_env
    else
        # Use venv - still per-service for venv since they're already set up
        local service=$1
        local service_dir="$PROJECT_ROOT/services/$service"
        setup_venv_env "$service" "$service_dir"
    fi
}

# Function to setup shared conda environment
setup_conda_env() {
    # Check if shared conda environment exists
    if ! $CONDA_CMD env list | grep -q "^$SHARED_ENV_NAME "; then
        print_status "Creating shared conda environment '$SHARED_ENV_NAME'..."
        $CONDA_CMD create -n "$SHARED_ENV_NAME" python=3.12 -y
        print_success "Created shared conda environment"
    else
        print_status "Shared conda environment '$SHARED_ENV_NAME' already exists"
    fi
    
    # Install dependencies from all services
    print_status "Installing dependencies from all services into shared environment..."
    
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service port module app <<< "$service_config"
        local service_dir="$PROJECT_ROOT/services/$service"
        
        if [ -f "$service_dir/requirements.txt" ]; then
            print_status "Installing deps for $service..."
            $CONDA_CMD run -n "$SHARED_ENV_NAME" pip install -q -r "$service_dir/requirements.txt"
        fi
    done
    
    print_success "All dependencies installed in shared environment"
}

# Function to setup venv environment
setup_venv_env() {
    local service=$1
    local service_dir=$2
    
    # Check if venv exists and has wrong Python version (3.13)
    if [ -d "$service_dir/venv" ]; then
        local venv_python_version=$(cat "$service_dir/venv/pyvenv.cfg" 2>/dev/null | grep "version" | head -1 | cut -d'=' -f2 | tr -d ' ' | cut -d'.' -f1,2)
        if [ "$venv_python_version" = "3.13" ] && [ "$PYTHON_VERSION" != "3.13" ]; then
            print_warning "Found Python 3.13 venv for $service - recreating with Python $PYTHON_VERSION"
            rm -rf "$service_dir/venv"
        fi
    fi
    
    if [ ! -d "$service_dir/venv" ]; then
        print_status "Creating virtual environment for $service (Python $PYTHON_VERSION)..."
        cd "$service_dir"
        $PYTHON_CMD -m venv venv
        print_success "Created venv for $service"
    fi
    
    if [ -f "$service_dir/requirements.txt" ]; then
        print_status "Installing dependencies for $service..."
        cd "$service_dir"
        # Ensure we use the venv's pip, not system pip
        source venv/bin/activate
        # Verify we're using the right Python
        local venv_python=$(which python)
        print_status "Using Python: $venv_python ($(python --version))"
        pip install -q --upgrade pip setuptools wheel
        pip install -q -r requirements.txt
        print_success "Dependencies installed for $service"
    fi
}

# Function to setup all Python services
setup_python_services() {
    print_status "Setting up Python virtual environments..."
    
    if [ "$USE_CONDA" = true ]; then
        # With conda, setup_venv installs all deps at once
        setup_venv ""
    else
        # With venv, need to setup each service individually
        for service_config in "${SERVICES[@]}"; do
            IFS=':' read -r service port module app <<< "$service_config"
            setup_venv "$service"
        done
    fi
    
    print_success "All Python services configured"
}

# Function to check if port is available and kill conflicting processes
ensure_port_available() {
    local port=$1
    local service=$2
    
    # Check if port is in use
    local pids=$(lsof -t -i:$port 2>/dev/null)
    
    if [ -n "$pids" ]; then
        print_status "Port $port is in use by process(es): $pids - killing..."
        kill -9 $pids 2>/dev/null || true
        sleep 1
        
        # Verify port is now free
        local remaining=$(lsof -t -i:$port 2>/dev/null)
        if [ -n "$remaining" ]; then
            print_error "Failed to free port $port. Process(es) still running: $remaining"
            print_error "You may need to kill them manually: kill -9 $remaining"
            return 1
        fi
        print_success "Port $port is now available"
    fi
    
    return 0
}

# Function to start a service in background
start_service() {
    local service=$1
    local port=$2
    local module=$3
    local app=$4
    local service_dir="$PROJECT_ROOT/services/$service"
    local log_file="$PROJECT_ROOT/logs/$service.log"
    
    mkdir -p "$PROJECT_ROOT/logs"
    
    # Ensure port is available before starting
    if ! ensure_port_available "$port" "$service"; then
        return 1
    fi
    
    print_status "Starting $service on port $port..."
    
    cd "$service_dir"
    
    # Export local environment
    export $(grep -v '^#' "$PROJECT_ROOT/.env.local" | xargs)
    
    # Start service based on environment type
    if [ "$USE_CONDA" = true ]; then
        # Use shared conda environment
        nohup $CONDA_CMD run -n "$SHARED_ENV_NAME" uvicorn "$module:$app" --reload --port "$port" --host 0.0.0.0 > "$log_file" 2>&1 &
    else
        # Use venv
        source venv/bin/activate
        nohup uvicorn "$module:$app" --reload --port "$port" --host 0.0.0.0 > "$log_file" 2>&1 &
    fi
    
    local pid=$!
    
    # Store PID
    echo $pid > "$PROJECT_ROOT/logs/$service.pid"
    
    print_success "$service started (PID: $pid, Log: $log_file)"
}

# Function to start all Python services
start_python_services() {
    print_status "Starting all Python services..."
    
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service port module app <<< "$service_config"
        start_service "$service" "$port" "$module" "$app"
        sleep 2  # Small delay between services
    done
    
    print_success "All Python services started"
}

# Function to start frontend
start_frontend() {
    print_status "Starting frontend..."
    
    local frontend_dir="$PROJECT_ROOT/services/frontend"
    
    if [ ! -d "$frontend_dir/node_modules" ]; then
        print_status "Installing frontend dependencies..."
        cd "$frontend_dir"
        npm install
    fi
    
    cd "$frontend_dir"
    
    # Export local environment for frontend
    export $(grep -v '^#' "$PROJECT_ROOT/.env.local" | xargs)
    
    nohup npm run dev > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &
    local pid=$!
    echo $pid > "$PROJECT_ROOT/logs/frontend.pid"
    
    print_success "Frontend started (PID: $pid, Log: logs/frontend.log)"
}

# Function to check service health
check_services() {
    print_status "Checking service health..."
    
    sleep 5
    
    local all_healthy=true
    
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service port module app <<< "$service_config"
        
        if curl -s "http://localhost:$port/health" >/dev/null 2>&1; then
            print_success "$service is healthy (port $port)"
        else
            print_warning "$service may not be ready yet (port $port)"
            all_healthy=false
        fi
    done
    
    if [ "$all_healthy" = true ]; then
        print_success "All services are running!"
    else
        print_warning "Some services are still starting up..."
    fi
}

# Function to display status
display_status() {
    echo
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  TalkAI Platform - Local Development${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo
    echo -e "${BLUE}Infrastructure (Docker):${NC}"
    echo "  - PostgreSQL: localhost:5432"
    echo "  - Redis: localhost:6379"
    echo "  - Qdrant: localhost:6333"
    echo "  - NATS: localhost:4222"
    echo
    echo -e "${BLUE}Services (Local):${NC}"
    
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service port module app <<< "$service_config"
        local pid_file="$PROJECT_ROOT/logs/$service.pid"
        
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if ps -p "$pid" > /dev/null 2>&1; then
                echo -e "  - $service: ${GREEN}http://localhost:$port${NC} (PID: $pid)"
            else
                echo -e "  - $service: ${RED}Not running${NC}"
            fi
        else
            echo -e "  - $service: ${YELLOW}Unknown${NC}"
        fi
    done
    
    echo
    echo -e "  - Frontend: ${GREEN}http://localhost:3000${NC}"
    echo
    echo -e "${BLUE}API Documentation:${NC}"
    echo "  - Swagger UI: http://localhost:8000/docs"
    echo "  - ReDoc: http://localhost:8000/redoc"
    echo
    echo -e "${BLUE}Logs:${NC}"
    echo "  - Service logs: ./logs/"
    echo
    echo -e "${YELLOW}To stop all services, run: ./scripts/local-dev.sh stop${NC}"
    echo
}

# Function to stop all services
stop_services() {
    print_status "Stopping all services..."
    
    # Stop Python services
    for service_config in "${SERVICES[@]}"; do
        IFS=':' read -r service port module app <<< "$service_config"
        local pid_file="$PROJECT_ROOT/logs/$service.pid"
        
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if ps -p "$pid" > /dev/null 2>&1; then
                kill "$pid" 2>/dev/null || true
                print_status "Stopped $service (PID: $pid)"
            fi
            rm -f "$pid_file"
        fi
    done
    
    # Stop frontend
    local frontend_pid_file="$PROJECT_ROOT/logs/frontend.pid"
    if [ -f "$frontend_pid_file" ]; then
        local pid=$(cat "$frontend_pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            kill "$pid" 2>/dev/null || true
            print_status "Stopped frontend (PID: $pid)"
        fi
        rm -f "$frontend_pid_file"
    fi
    
    # Stop infrastructure
    cd "$PROJECT_ROOT"
    docker-compose down
    
    print_success "All services stopped"
}

# Function to show logs
show_logs() {
    local service=$1
    
    if [ -z "$service" ]; then
        print_error "Usage: $0 logs <service-name>"
        echo "Available services:"
        for service_config in "${SERVICES[@]}"; do
            IFS=':' read -r service_name _ _ _ <<< "$service_config"
            echo "  - $service_name"
        done
        echo "  - frontend"
        exit 1
    fi
    
    local log_file="$PROJECT_ROOT/logs/$service.log"
    
    if [ -f "$log_file" ]; then
        tail -f "$log_file"
    else
        print_error "No log file found for $service"
        exit 1
    fi
}

# Function to show help
show_help() {
    cat << EOF
TalkAI Platform - Local Development Script

Usage: $0 [command]

Commands:
    start       Start all services (infrastructure in Docker, apps locally)
    stop        Stop all services
    restart     Restart all services
    status      Show status of all services
    logs        Show logs for a service
    setup       Setup environment and virtual environments only
    help        Show this help message

Examples:
    $0 start                    # Start everything
    $0 logs api-gateway         # Watch api-gateway logs
    $0 stop                     # Stop everything

Services available:
    - api-gateway (port 8000)
    - ai-router (port 8001)
    - action-engine (port 8002)
    - policy-engine (port 8003)
    - ingestion-service (port 8004)
    - audit-service (port 8005)
    - agent-service (port 8006)
    - frontend (port 3000)

Prerequisites:
    - Docker & Docker Compose
    - Conda (recommended) OR Python 3.11/3.12
    - Node.js 20+
    - Ollama running (optional, for AI features)

Notes:
    - The script auto-detects conda and prefers it over venv
    - If conda not found, uses system Python (3.11 or 3.12)
    - Python 3.13 has compatibility issues with some packages
    - Each service gets its own isolated environment

Environment Management:
    - With conda: Single shared environment 'talkai-dev' for all services
    - Without conda: Creates 'venv' directories in each service folder

EOF
}

# Main script logic
case "${1:-start}" in
    start)
        check_prerequisites
        setup_environment
        start_infrastructure
        setup_python_services
        start_python_services
        start_frontend
        sleep 3
        check_services
        display_status
        ;;
    
    stop)
        stop_services
        ;;
    
    restart)
        stop_services
        sleep 2
        $0 start
        ;;
    
    status)
        display_status
        ;;
    
    logs)
        show_logs "$2"
        ;;
    
    setup)
        check_prerequisites
        setup_environment
        setup_python_services
        print_success "Setup complete! Run '$0 start' to begin development."
        ;;
    
    help|--help|-h)
        show_help
        ;;
    
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac

#!/bin/bash

# TalkAI Health Check Script
# Checks the status of all services and displays health information

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
WEB_URL="${WEB_URL:-http://localhost:3000}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
TIMEOUT=5

# Status tracking
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Helper functions
print_header() {
    echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}              TalkAI Platform - Health Check${NC}"
    echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED_CHECKS++))
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((FAILED_CHECKS++))
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED_CHECKS++))
}

# Check HTTP endpoint
check_http() {
    local name=$1
    local url=$2
    local path=$3
    local expected_code=$4
    
    ((TOTAL_CHECKS++))
    
    if curl -s --max-time $TIMEOUT "${url}${path}" -o /dev/null -w "%{http_code}" 2>/dev/null | grep -q "${expected_code}"; then
        print_success "$name is healthy (${url}${path})"
        return 0
    else
        print_error "$name is not responding (${url}${path})"
        return 1
    fi
}

# Check Docker container
check_container() {
    local name=$1
    
    ((TOTAL_CHECKS++))
    
    if docker ps --format "table {{.Names}}" 2>/dev/null | grep -q "${name}"; then
        local status=$(docker inspect --format='{{.State.Status}}' "${name}" 2>/dev/null)
        if [ "$status" = "running" ]; then
            local health=$(docker inspect --format='{{.State.Health.Status}}' "${name}" 2>/dev/null || echo "none")
            if [ "$health" = "none" ] || [ "$health" = "healthy" ]; then
                local uptime=$(docker inspect --format='{{.State.StartedAt}}' "${name}" 2>/dev/null | xargs -I {} date -d {} +%H:%M:%S 2>/dev/null || echo "unknown")
                print_success "$name is running (uptime: $uptime)"
                return 0
            else
                print_warning "$name is running but health check shows: $health"
                return 1
            fi
        else
            print_error "$name status: $status"
            return 1
        fi
    else
        print_error "$name container not found"
        return 1
    fi
}

# Get container version
get_container_version() {
    local name=$1
    local version=$(docker inspect --format='{{.Config.Image}}' "${name}" 2>/dev/null | cut -d':' -f2)
    if [ -z "$version" ] || [ "$version" = "" ]; then
        echo "latest"
    else
        echo "$version"
    fi
}

# Check API health in detail
check_api_health() {
    print_status "Checking API health endpoint..."
    
    local response=$(curl -s --max-time $TIMEOUT "${API_URL}/health" 2>/dev/null)
    
    if [ -n "$response" ]; then
        echo ""
        echo "  API Response:"
        echo "  $response" | sed 's/^/    /'
        echo ""
        
        # Parse JSON if possible
        if command -v jq >/dev/null 2>&1; then
            local status=$(echo "$response" | jq -r '.status' 2>/dev/null || echo "unknown")
            if [ "$status" = "healthy" ]; then
                print_success "API reports healthy status"
            fi
        fi
    fi
}

# Check Ollama models
check_ollama_models() {
    print_status "Checking Ollama models..."
    
    local models=$(curl -s --max-time $TIMEOUT "${OLLAMA_URL}/api/tags" 2>/dev/null)
    
    if [ -n "$models" ]; then
        if command -v jq >/dev/null 2>&1; then
            local model_count=$(echo "$models" | jq '.models | length' 2>/dev/null || echo "0")
            
            if [ "$model_count" -gt 0 ]; then
                print_success "Ollama has $model_count model(s) available"
                echo ""
                echo "  Available models:"
                echo "$models" | jq -r '.models[].name' 2>/dev/null | sed 's/^/    - /'
                echo ""
            else
                print_warning "Ollama is running but no models are downloaded"
                echo ""
                echo "  Run: ollama pull llama2"
                echo ""
            fi
        else
            print_success "Ollama is responding"
        fi
    else
        print_error "Cannot connect to Ollama at ${OLLAMA_URL}"
    fi
}

# Check database connectivity
check_database() {
    print_status "Checking database connectivity..."
    
    # Try to get database status from API
    local db_status=$(curl -s --max-time $TIMEOUT "${API_URL}/health" 2>/dev/null | grep -o '"database":"[^"]*"' | cut -d'"' -f4)
    
    if [ -n "$db_status" ]; then
        if [ "$db_status" = "connected" ] || [ "$db_status" = "ok" ]; then
            print_success "Database is connected"
        else
            print_warning "Database status: $db_status"
        fi
    else
        print_warning "Cannot determine database status from API"
    fi
}

# Display versions
show_versions() {
    echo ""
    echo -e "${CYAN}Service Versions:${NC}"
    echo "─────────────────────────────────────────────────────────────"
    
    # Check Docker containers
    local containers=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -E "(talkai|opsai)" || true)
    
    if [ -n "$containers" ]; then
        while IFS= read -r container; do
            if [ -n "$container" ]; then
                local version=$(get_container_version "$container")
                printf "  %-25s %s\n" "$container:" "$version"
            fi
        done <<< "$containers"
    else
        echo "  No containers found"
    fi
    
    # Check local Ollama version if available
    if command -v ollama >/dev/null 2>&1; then
        local ollama_version=$(ollama --version 2>/dev/null | awk '{print $3}' || echo "unknown")
        printf "  %-25s %s\n" "ollama (local):" "$ollama_version"
    fi
    
    echo ""
}

# Resource usage
show_resources() {
    echo -e "${CYAN}Resource Usage:${NC}"
    echo "─────────────────────────────────────────────────────────────"
    
    if docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | grep -E "(talkai|opsai|NAME)" | head -20; then
        echo ""
    else
        echo "  Cannot retrieve container stats"
        echo ""
    fi
}

# Summary
show_summary() {
    echo -e "${CYAN}Summary:${NC}"
    echo "─────────────────────────────────────────────────────────────"
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        echo -e "  ${GREEN}All systems operational!${NC} ($PASSED_CHECKS/$TOTAL_CHECKS checks passed)"
    elif [ $FAILED_CHECKS -lt $TOTAL_CHECKS ]; then
        echo -e "  ${YELLOW}Some services need attention${NC} ($PASSED_CHECKS/$TOTAL_CHECKS passed, $FAILED_CHECKS failed)"
    else
        echo -e "  ${RED}Critical issues detected!${NC} (0/$TOTAL_CHECKS checks passed)"
    fi
    
    echo ""
    
    # Show troubleshooting tips if there are failures
    if [ $FAILED_CHECKS -gt 0 ]; then
        echo -e "${CYAN}Troubleshooting:${NC}"
        echo "  1. Check logs: docker-compose logs -f"
        echo "  2. Restart services: docker-compose restart"
        echo "  3. Full reset: docker-compose down && docker-compose up -d"
        echo ""
    fi
}

# Main execution
main() {
    print_header
    
    # Check services
    echo -e "${CYAN}Service Status:${NC}"
    echo "─────────────────────────────────────────────────────────────"
    
    # Docker Compose services
    check_container "talkai-api-1" || check_container "opsai-api" || true
    check_container "talkai-web-1" || check_container "opsai-web" || true
    check_container "talkai-postgres-1" || check_container "opsai-postgres" || true
    check_container "talkai-redis-1" || check_container "opsai-redis" || true
    check_container "talkai-ollama-1" || check_container "opsai-ollama" || check_container "ollama" || true
    check_container "talkai-nginx-1" || check_container "opsai-nginx" || true
    
    echo ""
    
    # HTTP endpoints
    echo -e "${CYAN}Endpoint Health:${NC}"
    echo "─────────────────────────────────────────────────────────────"
    
    check_http "API Service" "$API_URL" "/health" "200"
    check_http "Web Frontend" "$WEB_URL" "/" "200"
    check_http "API Docs" "$API_URL" "/docs" "200"
    check_http "Ollama" "$OLLAMA_URL" "/api/tags" "200"
    
    echo ""
    
    # Detailed checks
    check_api_health
    check_database
    check_ollama_models
    
    echo ""
    
    # Version and resource info
    show_versions
    show_resources
    
    # Final summary
    show_summary
}

# Handle arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        --web-url)
            WEB_URL="$2"
            shift 2
            ;;
        --ollama-url)
            OLLAMA_URL="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            echo "TalkAI Health Check Script"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --api-url URL       API endpoint URL (default: http://localhost:8000)"
            echo "  --web-url URL       Web frontend URL (default: http://localhost:3000)"
            echo "  --ollama-url URL    Ollama URL (default: http://localhost:11434)"
            echo "  --timeout SECONDS   Request timeout (default: 5)"
            echo "  -h, --help          Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Run main
main

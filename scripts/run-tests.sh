#!/bin/bash
# Test runner script for TalkAI Platform
# This script runs all tests with real database connections via testcontainers

set -e

echo "====================================="
echo "TalkAI Platform Test Runner"
echo "====================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Parse arguments
RUN_INTEGRATION=false
COVERAGE=false
SPECIFIC_SERVICE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --integration|-i)
            RUN_INTEGRATION=true
            shift
            ;;
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --service|-s)
            SPECIFIC_SERVICE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --integration, -i    Run integration tests with testcontainers"
            echo "  --coverage, -c       Generate coverage report"
            echo "  --service, -s        Run tests for specific service only"
            echo "  --help, -h           Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Function to run tests for a service
run_service_tests() {
    local service=$1
    local service_path="services/$service"
    
    if [ ! -d "$service_path" ]; then
        print_warning "Service directory not found: $service_path"
        return 1
    fi
    
    if [ ! -d "$service_path/tests" ]; then
        print_warning "No tests directory found for $service"
        return 0
    fi
    
    print_status "Running tests for $service..."
    
    cd "$service_path"
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment for $service..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    print_status "Installing dependencies for $service..."
    pip install -q -r requirements.txt
    pip install -q -r ../../requirements-test.txt 2>/dev/null || true
    
    # Run tests
    local pytest_args="-v --tb=short"
    
    if [ "$COVERAGE" = true ]; then
        pytest_args="$pytest_args --cov=app --cov-report=term-missing --cov-report=html:htmlcov"
    fi
    
    if [ "$RUN_INTEGRATION" = false ]; then
        pytest_args="$pytest_args -m 'not integration'"
    fi
    
    print_status "Executing: pytest $pytest_args tests/"
    if ! pytest $pytest_args tests/; then
        print_error "Tests failed for $service"
        deactivate
        cd ../..
        return 1
    fi
    
    deactivate
    cd ../..
    
    print_status "Tests passed for $service"
    return 0
}

# Main execution
FAILED_SERVICES=()

if [ -n "$SPECIFIC_SERVICE" ]; then
    # Run tests for specific service
    if ! run_service_tests "$SPECIFIC_SERVICE"; then
        FAILED_SERVICES+=("$SPECIFIC_SERVICE")
    fi
else
    # Run tests for all services with tests
    for service_dir in services/*/; do
        service=$(basename "$service_dir")
        
        if [ -d "$service_dir/tests" ]; then
            if ! run_service_tests "$service"; then
                FAILED_SERVICES+=("$service")
            fi
        fi
    done
fi

# Summary
echo ""
echo "====================================="
echo "Test Run Summary"
echo "====================================="

if [ ${#FAILED_SERVICES[@]} -eq 0 ]; then
    print_status "All tests passed!"
    exit 0
else
    print_error "Tests failed for the following services:"
    for service in "${FAILED_SERVICES[@]}"; do
        echo "  - $service"
    done
    exit 1
fi

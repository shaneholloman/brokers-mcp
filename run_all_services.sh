#!/bin/bash

# Set error handling
set -e

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to run a service
run_service() {
    local service_name=$1
    local port=$2
    local log_file="logs/${service_name}.log"
    
    echo "Starting ${service_name} on port ${port}"
    
    # Run the service with UV workspace package and redirect output to log file
    FASTMCP_PORT=${port} uv run \
        --package "${service_name}" \
        python "${service_name}/src/server.py" \
        > "${log_file}" 2>&1 &
    
    # Store the PID
    echo $! > "logs/${service_name}.pid"
    echo "${service_name} started with PID $(cat "logs/${service_name}.pid")"
}

# Function to stop services
stop_services() {
    echo "Stopping all services..."
    for service in brokerage_service market_data_service research_service; do
        if [ -f "logs/${service}.pid" ]; then
            pid=$(cat "logs/${service}.pid")
            if kill -0 $pid 2>/dev/null; then
                echo "Stopping ${service} (PID: $pid)"
                kill $pid
                rm "logs/${service}.pid"
            fi
        fi
    done
    echo "All services stopped"
    exit 0
}

# Set up trap for clean shutdown
trap stop_services SIGINT SIGTERM

# Start all services with different ports
run_service "brokerage_service" 8001

run_service "market_data_service" 8002

run_service "research_service" 8003

echo "All services started. Press Ctrl+C to stop all services."
echo "Check logs/ directory for service output."
echo
echo "Services are running on:"
echo "- Brokerage Service: http://localhost:8001"
echo "- Market Data Service: http://localhost:8002"
echo "- Research Service: http://localhost:8003"

# Wait for all background processes
wait

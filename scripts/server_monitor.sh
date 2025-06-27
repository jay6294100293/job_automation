#!/bin/bash

# Server Monitoring Script for Django Job Automation System
# This script collects server metrics and sends them to Django API and n8n

set -e

# =============================================================================
# CONFIGURATION - UPDATE THESE VALUES WITH YOUR DATA
# =============================================================================

# In server_monitor.sh, update these lines:
DJANGO_API_URL="https://ai.jobautomation.me/api/monitoring/metrics/"
N8N_WEBHOOK_URL="https://ai.jobautomation.me/webhook/server-metrics"
API_KEY="MONITORING_API_KEY_WILL_BE_FILLED_BY_DEPLOY_SCRIPT"
LOG_FILE="/var/log/server_monitor.log"

# =============================================================================
# FUNCTIONS - DO NOT CHANGE BELOW THIS LINE
# =============================================================================

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to get CPU usage
get_cpu_usage() {
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//' | sed 's/[^0-9.]//g')
    if [ -z "$cpu_usage" ]; then
        cpu_usage=$(awk '{u=$2+$4; t=$2+$3+$4+$5; if (NR==1){u1=u; t1=t;} else print ($2+$4-u1) * 100 / (t-t1); }' <(grep 'cpu ' /proc/stat; sleep 1; grep 'cpu ' /proc/stat))
    fi
    echo "${cpu_usage:-0}"
}

# Function to get memory usage
get_memory_usage() {
    memory_info=$(free | grep '^Mem:')
    total_mem=$(echo $memory_info | awk '{print $2}')
    used_mem=$(echo $memory_info | awk '{print $3}')
    
    if [ "$total_mem" -gt 0 ]; then
        memory_usage=$(echo "scale=2; $used_mem * 100 / $total_mem" | bc 2>/dev/null || echo "0")
    else
        memory_usage=0
    fi
    echo "$memory_usage"
}

# Function to get disk usage
get_disk_usage() {
    disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    echo "${disk_usage:-0}"
}

# Function to get load average
get_load_average() {
    load_avg=$(uptime | awk -F'load average:' '{print $2}' | xargs)
    echo "$load_avg"
}

# Function to get uptime
get_uptime() {
    uptime_info=$(uptime -p)
    echo "$uptime_info"
}

# Function to get Docker container stats
get_container_stats() {
    if command -v docker &> /dev/null; then
        containers_running=$(docker ps -q | wc -l)
        containers_total=$(docker ps -a -q | wc -l)
    else
        containers_running=0
        containers_total=0
    fi
    echo "$containers_running $containers_total"
}

# Function to send metrics to Django API
send_to_django() {
    local metrics_json="$1"
    
    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "$metrics_json" \
        "$DJANGO_API_URL" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" -eq 201 ]; then
        log_message "✅ Successfully sent metrics to Django API"
        return 0
    else
        log_message "❌ Failed to send metrics to Django API. HTTP Code: $http_code"
        return 1
    fi
}

# Function to send metrics to n8n
send_to_n8n() {
    local metrics_json="$1"
    
    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$metrics_json" \
        "$N8N_WEBHOOK_URL" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" -eq 200 ]; then
        log_message "✅ Successfully sent metrics to n8n"
        return 0
    else
        log_message "❌ Failed to send metrics to n8n. HTTP Code: $http_code"
        return 1
    fi
}

# Main monitoring function
collect_and_send_metrics() {
    log_message "🔍 Starting server metrics collection..."
    
    # Collect metrics
    cpu_usage=$(get_cpu_usage)
    memory_usage=$(get_memory_usage)
    disk_usage=$(get_disk_usage)
    load_average=$(get_load_average)
    uptime_info=$(get_uptime)
    container_stats=$(get_container_stats)
    containers_running=$(echo $container_stats | cut -d' ' -f1)
    containers_total=$(echo $container_stats | cut -d' ' -f2)
    
    # Generate unique event ID
    event_id="metrics_$(date +%s)_$(hostname)"
    timestamp=$(date -Iseconds)
    
    # Create JSON payload
    metrics_json=$(cat <<EOF
{
    "event_id": "$event_id",
    "timestamp": "$timestamp",
    "hostname": "$(hostname)",
    "cpu_usage": $cpu_usage,
    "memory_usage": $memory_usage,
    "disk_usage": $disk_usage,
    "load_average": "$load_average",
    "uptime": "$uptime_info",
    "containers_running": $containers_running,
    "containers_total": $containers_total,
    "collected_at": "$timestamp"
}
EOF
)
    
    log_message "📊 Metrics collected - CPU: ${cpu_usage}%, Memory: ${memory_usage}%, Disk: ${disk_usage}%"
    
    # Send to Django API
    send_to_django "$metrics_json"
    
    # Send to n8n
    send_to_n8n "$metrics_json"
    
    log_message "🏁 Metrics collection completed"
}

# Setup monitoring service
setup_monitoring_service() {
    log_message "🔧 Setting up server monitoring service..."
    
    # Install dependencies
    apt-get update
    apt-get install -y bc curl
    
    # Create systemd service file
    cat > /etc/systemd/system/server-monitor.service << 'EOF'
[Unit]
Description=Server Monitoring for Django Job Automation
After=network.target

[Service]
Type=simple
User=root
ExecStart=/opt/job_automation/scripts/server_monitor.sh --service
Restart=always
RestartSec=300

[Install]
WantedBy=multi-user.target
EOF
    
    # Create systemd timer for periodic execution
    cat > /etc/systemd/system/server-monitor.timer << 'EOF'
[Unit]
Description=Run server monitoring every 5 minutes
Requires=server-monitor.service

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
EOF
    
    # Reload systemd and enable services
    systemctl daemon-reload
    systemctl enable server-monitor.timer
    systemctl start server-monitor.timer
    
    log_message "✅ Server monitoring service setup completed"
}

# Main execution logic
case "${1:-}" in
    --setup)
        setup_monitoring_service
        ;;
    --test)
        collect_and_send_metrics
        ;;
    --service)
        # Run as service (continuous monitoring)
        while true; do
            collect_and_send_metrics
            sleep 300  # Wait 5 minutes
        done
        ;;
    --once)
        collect_and_send_metrics
        ;;
    *)
        echo "Usage: $0 [--setup|--test|--service|--once]"
        echo "  --setup: Setup monitoring as a systemd service"
        echo "  --test:  Test monitoring functionality"
        echo "  --service: Run as a service (used by systemd)"
        echo "  --once:  Run metrics collection once"
        ;;
esac
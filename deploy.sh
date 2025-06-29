#!/bin/bash

# Job Automation Deployment Script
# Run this on your DigitalOcean server to set up the complete system

set -e

echo "🚀 Starting Job Automation System Deployment..."

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
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
#if [[ $EUID -eq 0 ]]; then
#   print_error "This script should not be run as root"
#   exit 1
#fi

# Update system
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
print_status "Installing system dependencies..."
sudo apt install -y \
    curl \
    wget \
    git \
    unzip \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    nginx \
    certbot \
    python3-certbot-nginx

# Install Docker
if ! command -v docker &> /dev/null; then
    print_status "Installing Docker..."
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io
    sudo usermod -aG docker $USER
    print_warning "You need to log out and log back in for Docker permissions to take effect"
else
    print_status "Docker already installed"
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    print_status "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
else
    print_status "Docker Compose already installed"
fi

# Create app directory
print_status "Setting up application directory..."
sudo mkdir -p /opt/job_automation
sudo chown $USER:$USER /opt/job_automation
cd /opt/job_automation

# Clone repository (if not already present)
if [ ! -d ".git" ]; then
    print_status "Cloning repository..."
    git clone https://github.com/$GITHUB_REPOSITORY .
else
    print_status "Repository already exists, pulling latest changes..."
    git pull origin main
fi

# Create necessary directories
print_status "Creating directories..."
mkdir -p nginx/conf.d
mkdir -p certbot/conf
mkdir -p certbot/www
mkdir -p logs
mkdir -p media
mkdir -p staticfiles

# Set up environment file
if [ ! -f ".env" ]; then
    print_status "Setting up environment file..."
    cp .env.example .env
    print_warning "Please edit .env file with your actual credentials"
else
    print_status "Environment file already exists"
fi

# Set up SSL certificate
print_status "Setting up SSL certificate..."
if [ ! -f "/etc/letsencrypt/live/ai.jobautomation.me/fullchain.pem" ]; then
    # First, get certificate
    sudo certbot certonly --webroot \
        --webroot-path=./certbot/www \
        --email mrityunjay.100293@gmail.com \
        --agree-tos \
        --no-eff-email \
        -d ai.jobautomation.me
else
    print_status "SSL certificate already exists"
fi

# Build and start services
print_status "Building Docker images..."
docker-compose build

print_status "Starting services..."
docker-compose up -d

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 30

# Run initial setup
print_status "Running database migrations..."
docker-compose exec -T web python manage.py migrate

print_status "Creating superuser (if needed)..."
docker-compose exec -T web python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created')
else:
    print('Superuser already exists')
EOF

print_status "Collecting static files..."
docker-compose exec -T web python manage.py collectstatic --noinput

print_status "Loading initial data..."
docker-compose exec -T web python manage.py loaddata fixtures/initial_data.json || echo "No fixtures found"

# Set up cron job for certificate renewal
print_status "Setting up certificate auto-renewal..."
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -

# Set up log rotation
print_status "Setting up log rotation..."
sudo tee /etc/logrotate.d/job_automation << EOF
/opt/job_automation/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        docker-compose -f /opt/job_automation/docker-compose.yml restart web
    endscript
}
EOF

# Setup monitoring script
print_status "Setting up monitoring..."
cat > /opt/job_automation/monitor.sh << 'EOF'
#!/bin/bash
# Health monitoring script
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE="/opt/job_automation/logs/monitor.log"

# Check if services are running
if ! docker-compose ps | grep -q "Up"; then
    echo "[$TIMESTAMP] ERROR: Some services are down" >> $LOG_FILE
    docker-compose up -d
fi

# Check disk space
DISK_USAGE=$(df /opt/job_automation | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "[$TIMESTAMP] WARNING: Disk usage is ${DISK_USAGE}%" >> $LOG_FILE
    # Clean up old logs and Docker images
    docker system prune -f
fi

# Check memory usage
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.2f", $3*100/$2}')
if (( $(echo "$MEMORY_USAGE > 90" | bc -l) )); then
    echo "[$TIMESTAMP] WARNING: Memory usage is ${MEMORY_USAGE}%" >> $LOG_FILE
fi

echo "[$TIMESTAMP] Health check completed" >> $LOG_FILE
EOF

chmod +x /opt/job_automation/monitor.sh

# Add monitoring to crontab
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/job_automation/monitor.sh") | crontab -

# Setup backup script
print_status "Setting up backup system..."
cat > /opt/job_automation/backup.sh << 'EOF'
#!/bin/bash
# Database backup script
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_DIR="/opt/job_automation/backups"
mkdir -p $BACKUP_DIR

# Backup database
docker-compose exec -T postgres pg_dump -U django_user job_automation > "$BACKUP_DIR/db_backup_$TIMESTAMP.sql"

# Backup media files
tar -czf "$BACKUP_DIR/media_backup_$TIMESTAMP.tar.gz" media/

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "$(date): Backup completed" >> /opt/job_automation/logs/backup.log
EOF

chmod +x /opt/job_automation/backup.sh

# Add backup to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/job_automation/backup.sh") | crontab -

# Display final status
print_status "Checking service status..."
docker-compose ps

print_status "Testing health endpoint..."
sleep 10
if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
    print_status "✅ Health check passed!"
else
    print_warning "⚠️ Health check failed - services may still be starting"
fi

print_status "🎉 Deployment completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit /opt/job_automation/.env with your API keys"
echo "2. Access your application at: https://ai.jobautomation.me"
echo "3. Access n8n at: https://ai.jobautomation.me/n8n/"
echo "4. Admin panel: https://ai.jobautomation.me/admin/"
echo "5. Monitor logs: docker-compose logs -f"
echo ""
echo "Useful commands:"
echo "- Restart services: docker-compose restart"
echo "- View logs: docker-compose logs [service]"
echo "- Update app: git pull && docker-compose up -d --build"
echo "- Backup: ./backup.sh"
echo ""
print_status "Setup complete! 🚀"

#!/bin/bash

# =============================================================================
# DJANGO JOB AUTOMATION SYSTEM - DIGITAL OCEAN DEPLOYMENT SCRIPT
# =============================================================================

set -e

echo "🚀 Django Job Automation System - Complete Deployment with n8n Monitoring"
echo "=========================================================================="

# =============================================================================
# CONFIGURATION - UPDATE THESE VALUES WITH YOUR DATA
# =============================================================================

PROJECT_NAME="job_automation"
DOMAIN="ai.jobautomation.me"
EMAIL="mrityunjay.100293@gmail.com"
GITHUB_REPO="jay6294100293/job_automation"

# =============================================================================
# SYSTEM VARIABLES - DO NOT CHANGE
# =============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# =============================================================================
# DEPLOYMENT STEPS - DO NOT CHANGE BELOW THIS LINE
# =============================================================================

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Step 1: System Update and Dependencies
print_info "Step 1/10 - Updating system and installing dependencies..."
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    software-properties-common \
    gnupg \
    lsb-release \
    git \
    ufw \
    nginx \
    certbot \
    python3-certbot-nginx \
    bc \
    jq

print_status "System updated successfully!"

# Step 2: Install Docker and Docker Compose
print_info "Step 2/10 - Installing Docker and Docker Compose..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo usermod -aG docker $USER
    print_status "Docker installed successfully!"
else
    print_status "Docker already installed!"
fi

# Step 3: Configure Firewall
print_info "Step 3/10 - Configuring firewall..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 5432  # PostgreSQL external access
sudo ufw allow 6379  # Redis external access
sudo ufw --force enable
print_status "Firewall configured successfully!"

# Step 4: Create project directory
print_info "Step 4/10 - Setting up project directory..."
PROJECT_DIR="/opt/$PROJECT_NAME"
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR
cd $PROJECT_DIR

# Clone repository if specified
if [ ! -z "$GITHUB_REPO" ] && [ "$GITHUB_REPO" != "YOUR_GITHUB_USERNAME/YOUR_REPOSITORY_NAME" ]; then
    if [ ! -d ".git" ]; then
        git clone https://github.com/$GITHUB_REPO.git .
        print_status "Repository cloned successfully!"
    else
        git pull origin main
        print_status "Repository updated successfully!"
    fi
else
    print_warning "Please update GITHUB_REPO in deploy.sh with your actual repository"
    print_warning "Then upload your Django project files to $PROJECT_DIR"
fi

print_status "Project directory setup complete!"

# Step 5: Create necessary directories
print_info "Step 5/10 - Creating application directories..."
mkdir -p {logs,certbot/conf,certbot/www,nginx/conf.d,scripts,n8n_workflows,monitoring}
mkdir -p media/{documents,resumes} staticfiles init-db
chmod +x scripts/*.sh 2>/dev/null || true

# Create monitoring app __init__.py files
touch monitoring/__init__.py
mkdir -p monitoring/migrations
touch monitoring/migrations/__init__.py

print_status "Application directories created!"

# Step 6: Generate secure keys and update environment
print_info "Step 6/10 - Setting up environment configuration..."

# Generate random keys
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())' 2>/dev/null || openssl rand -base64 32)
MONITORING_KEY=$(openssl rand -hex 32)
REDIS_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
DB_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)

# Update .env file if it exists, otherwise create it
if [ -f .env ]; then
    print_status "Updating existing .env file..."
    # Update monitoring API key
    sed -i "s/MONITORING_API_KEY=.*/MONITORING_API_KEY=$MONITORING_KEY/g" .env
    sed -i "s/WILL_BE_GENERATED_BY_DEPLOY_SCRIPT/$MONITORING_KEY/g" .env

    # Update other auto-generated values if they're default
    sed -i "s/CHANGE_THIS_TO_SECURE_PASSWORD/$DB_PASSWORD/g" .env
    sed -i "s/CHANGE_THIS_TO_SECURE_REDIS_PASSWORD/$REDIS_PASSWORD/g" .env
    sed -i "s/CHANGE_THIS_TO_YOUR_ACTUAL_DJANGO_SECRET_KEY/$SECRET_KEY/g" .env
    sed -i "s/CHANGE_THIS_TO_YOUR_DJANGO_SECRET_KEY/$SECRET_KEY/g" .env
else
    print_warning "No .env file found. Please create .env with your configuration!"
fi

# Update server monitoring script with actual API key
if [ -f scripts/server_monitor.sh ]; then
    sed -i "s/MONITORING_API_KEY_WILL_BE_FILLED_BY_DEPLOY_SCRIPT/$MONITORING_KEY/g" scripts/server_monitor.sh
    chmod +x scripts/server_monitor.sh
    print_status "Server monitoring script updated!"
else
    print_warning "Server monitoring script not found at scripts/server_monitor.sh"
fi

print_status "Environment configuration completed!"

# Step 7: Setup SSL certificates
print_info "Step 7/10 - Generating SSL certificates..."
sudo mkdir -p /var/www/certbot

# Stop nginx if running
sudo systemctl stop nginx 2>/dev/null || true

# Generate certificates
sudo certbot certonly --standalone \
    --email $EMAIL \
    -d $DOMAIN \
    --agree-tos \
    --non-interactive || print_warning "SSL certificate generation failed. You can retry later."

print_status "SSL certificate setup completed!"

# Step 8: Create nginx configuration
print_info "Step 8/10 - Setting up Nginx configuration..."

# Create basic nginx config for Django + n8n
sudo mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled

cat > /tmp/nginx_site.conf << EOF
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # Static files
    location /static/ {
        alias /opt/$PROJECT_NAME/staticfiles/;
        expires 30d;
    }

    # Media files
    location /media/ {
        alias /opt/$PROJECT_NAME/media/;
        expires 7d;
    }

    # n8n specific paths
    location ~ ^/(webhook|rest|form)/ {
        proxy_pass http://localhost:5678;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Django application
    location / {
        # Check if it's n8n login page
        if (\$http_user_agent ~* "n8n") {
            proxy_pass http://localhost:5678;
            break;
        }

        # Default to Django
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo cp /tmp/nginx_site.conf /etc/nginx/sites-available/$PROJECT_NAME
sudo ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

print_status "Nginx configuration completed!"

# Step 9: Build and start Docker containers
print_info "Step 9/10 - Building and starting Docker containers..."

# Start the services
if command -v docker compose &> /dev/null; then
    docker compose up -d --build
else
    docker-compose up -d --build
fi

print_status "Docker containers started successfully!"

# Step 10: Setup monitoring and final configuration
print_info "Step 10/10 - Setting up monitoring and final configuration..."

# Setup server monitoring
if [ -f scripts/server_monitor.sh ]; then
    ./scripts/server_monitor.sh --setup
    print_status "Server monitoring setup completed!"
else
    print_warning "Server monitoring script not found. Please add scripts/server_monitor.sh"
fi

# Setup SSL renewal
print_status "Setting up SSL certificate auto-renewal..."
(crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -

# Create backup script
print_status "Creating backup script..."
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_DIR="/opt/job_automation"

mkdir -p $BACKUP_DIR

# Backup database
docker exec job_automation_postgres_1 pg_dump -U n8n n8n > $BACKUP_DIR/database_$DATE.sql 2>/dev/null || echo "Database backup failed"

# Backup media files
tar -czf $BACKUP_DIR/media_$DATE.tar.gz -C $PROJECT_DIR media/ 2>/dev/null || echo "Media backup failed"

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete 2>/dev/null
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete 2>/dev/null

echo "Backup completed: $DATE"
EOF

chmod +x backup.sh

# Add backup to crontab
(crontab -l 2>/dev/null; echo "0 2 * * * $PROJECT_DIR/backup.sh") | crontab -

print_status "Backup system setup completed!"

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 30

# Check service health
print_status "Checking service health..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🎉 DEPLOYMENT COMPLETED SUCCESSFULLY! 🎉"
echo "=========================================="
echo ""
echo "🌐 Your Django application: https://$DOMAIN"
echo "🔧 n8n automation platform: https://$DOMAIN (login with n8n credentials)"
echo "📊 Admin panel: https://$DOMAIN/admin/"
echo "🏥 Health check: https://$DOMAIN/health/"
echo ""
echo "🔑 IMPORTANT CREDENTIALS:"
echo "   - Monitoring API Key: $MONITORING_KEY"
echo "   - Generated DB Password: $DB_PASSWORD"
echo "   - Generated Redis Password: $REDIS_PASSWORD"
echo ""
echo "📋 Next Steps:"
echo "1. Update your .env file with actual API keys (Brevo, Groq, OpenRouter)"
echo "2. Import the n8n workflow from n8n_workflows/monitoring_workflow.json"
echo "3. Configure Discord webhook in the n8n workflow"
echo "4. Update GitHub repository secrets for CI/CD"
echo "5. Test the monitoring system"
echo ""
echo "📁 Important Files:"
echo "   - Project directory: $PROJECT_DIR"
echo "   - Environment file: $PROJECT_DIR/.env"
echo "   - Logs: $PROJECT_DIR/logs/"
echo "   - Backups: /opt/backups/"
echo ""
echo "🔧 Useful Commands:"
echo "   - View logs: docker compose logs -f"
echo "   - Test monitoring: ./scripts/server_monitor.sh --test"
echo "   - Restart services: docker compose restart"
echo "   - Check health: curl https://$DOMAIN/health/"
echo ""
print_status "Django Job Automation System with n8n monitoring is ready!"
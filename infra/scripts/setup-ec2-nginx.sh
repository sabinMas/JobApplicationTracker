#!/bin/bash
# EC2 nginx setup — install and configure SSL reverse proxy
# Run this on EC2 after the main setup-ec2.sh
#
# Usage:
#   ssh ec2-user@<your-ec2-ip>
#   curl -fsSL https://raw.githubusercontent.com/sabinMas/JobApplicationTracker/master/infra/scripts/setup-ec2-nginx.sh | bash

set -e

APP_DIR="/opt/jobtracker"
EC2_PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

echo "=== JobApplicationTracker nginx + SSL Setup ==="
echo "EC2 Public IP: $EC2_PUBLIC_IP"

# ── Install nginx ──────────────────────────────────────────────────────────────
echo "[1/5] Installing nginx..."
if ! command -v nginx &> /dev/null; then
  sudo dnf install -y nginx -q
  sudo systemctl daemon-reload
  echo "  nginx installed."
else
  echo "  nginx already installed."
fi

# ── Generate self-signed SSL certificate ───────────────────────────────────────
echo "[2/5] Setting up SSL certificate..."
CERT_DIR="/etc/nginx/ssl"
CERT_FILE="$CERT_DIR/jobtracker.crt"
KEY_FILE="$CERT_DIR/jobtracker.key"

if [ ! -d "$CERT_DIR" ]; then
  sudo mkdir -p "$CERT_DIR"
fi

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
  echo "  Generating self-signed certificate (valid for 365 days)..."
  sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -subj "/CN=$EC2_PUBLIC_IP/O=JobApplicationTracker/C=US" 2>/dev/null
  sudo chmod 600 "$KEY_FILE"
  echo "  Certificate created: $CERT_FILE"
else
  echo "  SSL certificate already exists."
fi

# ── Create nginx configuration ─────────────────────────────────────────────────
echo "[3/5] Configuring nginx as reverse proxy..."
sudo tee /etc/nginx/conf.d/jobtracker.conf > /dev/null << 'NGINX_CONFIG'
# JobApplicationTracker nginx reverse proxy configuration

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name _;
    return 301 https://$host$request_uri;
}

# HTTPS server block
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name _;

    # SSL configuration
    ssl_certificate /etc/nginx/ssl/jobtracker.crt;
    ssl_certificate_key /etc/nginx/ssl/jobtracker.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Disable direct_slash for cleaner routing
    absolute_redirect off;

    # Proxy to uvicorn backend on :8000
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffer settings for large uploads
        proxy_buffering off;
        proxy_request_buffering off;
        client_max_body_size 100M;
    }

    # Health check endpoint
    location /nginx-health {
        access_log off;
        return 200 "OK";
        add_header Content-Type text/plain;
    }
}
NGINX_CONFIG

echo "  nginx configuration created."

# ── Validate nginx config ──────────────────────────────────────────────────────
echo "[4/5] Validating nginx configuration..."
if sudo nginx -t 2>&1 | grep -q "successful"; then
  echo "  Configuration is valid ✓"
else
  echo "  Configuration validation failed!"
  exit 1
fi

# ── Start/restart nginx ────────────────────────────────────────────────────────
echo "[5/5] Starting nginx..."
sudo systemctl enable nginx
sudo systemctl restart nginx
sleep 2

if sudo systemctl is-active --quiet nginx; then
  echo "  nginx is running ✓"
else
  echo "  Failed to start nginx!"
  sudo journalctl -u nginx -n 20 --no-pager
  exit 1
fi

# ── Final status ───────────────────────────────────────────────────────────────
echo ""
echo "=== Setup Complete ==="
echo ""
echo "✓ nginx is running on HTTPS port 443"
echo "✓ All HTTP traffic redirects to HTTPS"
echo "✓ Requests proxied to uvicorn backend on :8000"
echo ""
echo "Test the setup:"
echo "  curl -k https://$EC2_PUBLIC_IP/api/health"
echo ""
echo "Next steps:"
echo "  1. Update Vercel environment variable: VITE_API_URL=https://$EC2_PUBLIC_IP"
echo "  2. Redeploy frontend from Vercel dashboard"
echo "  3. Verify dashboard loads without errors"
echo ""
echo "SSL Certificate: $CERT_FILE"
echo "  (Self-signed; valid for 365 days)"
echo "  For production, replace with Let's Encrypt or your CA certificate"
echo ""

#!/bin/bash
# EC2 setup script — run this once after launching the instance.
# Tested on Amazon Linux 2023 (t3.small or larger).
#
# Usage:
#   ssh ec2-user@<your-ec2-ip>
#   curl -fsSL https://raw.githubusercontent.com/sabinMas/JobApplicationTracker/master/infra/scripts/setup-ec2.sh | bash

set -e

REPO_URL="https://github.com/sabinMas/JobApplicationTracker.git"
APP_DIR="/opt/jobtracker"
SERVICE_USER="ec2-user"

echo "=== JobApplicationTracker EC2 Setup ==="

# ── System packages ──────────────────────────────────────────────────────────
echo "[1/6] Installing system packages..."
sudo dnf update -y -q
sudo dnf install -y git python3.11 python3.11-pip python3.11-devel gcc

# ── Clone repo ────────────────────────────────────────────────────────────────
echo "[2/6] Cloning repository..."
if [ -d "$APP_DIR" ]; then
  echo "  Directory exists, pulling latest..."
  cd "$APP_DIR" && git pull origin master
else
  sudo git clone "$REPO_URL" "$APP_DIR"
  sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$APP_DIR"
fi

# ── Python virtualenv + dependencies ─────────────────────────────────────────
echo "[3/6] Setting up Python environment..."
cd "$APP_DIR/backend"
python3.11 -m venv venv
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r requirements.txt -q
echo "  Dependencies installed."

# ── .env placeholder ─────────────────────────────────────────────────────────
echo "[4/6] Creating .env file..."
if [ ! -f "$APP_DIR/backend/.env" ]; then
  cp "$APP_DIR/backend/.env.example" "$APP_DIR/backend/.env"
  echo ""
  echo "  *** ACTION REQUIRED ***"
  echo "  Edit $APP_DIR/backend/.env and fill in:"
  echo "    DATABASE_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
  echo "    ALLOWED_ORIGINS (add your EC2 public IP or domain)"
  echo "    BEDROCK_FAST_MODEL, BEDROCK_SMART_MODEL"
  echo ""
else
  echo "  .env already exists, skipping."
fi

# ── Data directory ────────────────────────────────────────────────────────────
mkdir -p "$APP_DIR/data/generated" "$APP_DIR/data/uploads"

# ── systemd service ───────────────────────────────────────────────────────────
echo "[5/6] Installing systemd service..."
sudo tee /etc/systemd/system/jobtracker.service > /dev/null << EOF
[Unit]
Description=JobApplicationTracker FastAPI Backend
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$APP_DIR/backend
ExecStart=$APP_DIR/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
EnvironmentFile=$APP_DIR/backend/.env
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable jobtracker

# ── Deploy script ─────────────────────────────────────────────────────────────
echo "[6/6] Installing deploy script..."
sudo tee /usr/local/bin/deploy-jobtracker > /dev/null << 'EOF'
#!/bin/bash
set -e
APP_DIR="/opt/jobtracker"
echo "Pulling latest code..."
cd "$APP_DIR"
git pull origin master
echo "Installing dependencies..."
./backend/venv/bin/pip install -r backend/requirements.txt -q
echo "Restarting service..."
sudo systemctl restart jobtracker
sleep 2
sudo systemctl status jobtracker --no-pager | head -10
echo "Deploy complete."
EOF
sudo chmod +x /usr/local/bin/deploy-jobtracker

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit your .env:  nano $APP_DIR/backend/.env"
echo "  2. Start the API:   sudo systemctl start jobtracker"
echo "  3. Check status:    sudo systemctl status jobtracker"
echo "  4. View logs:       sudo journalctl -u jobtracker -f"
echo "  5. Future deploys:  deploy-jobtracker"
echo ""
echo "API will be at: http://\$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"

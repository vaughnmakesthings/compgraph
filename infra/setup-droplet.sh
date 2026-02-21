#!/usr/bin/env bash
# setup-droplet.sh — Idempotent provisioning for CompGraph on Ubuntu 24.04
# Run as root on a fresh droplet: ssh compgraph-do 'bash -s' < infra/setup-droplet.sh
set -euo pipefail

REPO_URL="https://github.com/vaughnmakesthings/compgraph.git"
APP_DIR="/opt/compgraph"
SERVICE_USER="compgraph"

echo "=== CompGraph Droplet Setup ==="

# ── 1. System updates + packages ──
echo "[1/10] Installing system packages..."
apt-get update -qq
apt-get install -y -qq git curl build-essential libpq-dev > /dev/null

# ── 2. Swap (1GB, idempotent) ──
if [ ! -f /swapfile ]; then
    echo "[2/10] Creating 1GB swap..."
    fallocate -l 1G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
else
    echo "[2/10] Swap already exists, skipping."
fi

# ── 3. Service user ──
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "[3/10] Creating service user: $SERVICE_USER"
    useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
else
    echo "[3/10] User $SERVICE_USER already exists, skipping."
fi

# ── 4. Install uv ──
if ! command -v uv &>/dev/null; then
    echo "[4/10] Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add to PATH for this script
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "[4/10] uv already installed, skipping."
fi

# ── 5. Clone repo ──
if [ ! -d "$APP_DIR/.git" ]; then
    echo "[5/10] Cloning repository..."
    git clone "$REPO_URL" "$APP_DIR"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"
else
    echo "[5/10] Repository already cloned, skipping."
fi

# ── 6. Install Python 3.13 ──
echo "[6/10] Installing Python 3.13..."
uv python install 3.13

# ── 7. Install dependencies ──
echo "[7/10] Running uv sync..."
cd "$APP_DIR"
# Run as compgraph user for correct venv ownership
sudo -u "$SERVICE_USER" env PATH="$HOME/.local/bin:$PATH" uv sync

# ── 8. Install Caddy ──
if ! command -v caddy &>/dev/null; then
    echo "[8/10] Installing Caddy..."
    apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https > /dev/null
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -qq
    apt-get install -y -qq caddy > /dev/null
else
    echo "[8/10] Caddy already installed, skipping."
fi
cp "$APP_DIR/infra/Caddyfile" /etc/caddy/Caddyfile

# ── 9. Configure journald log rotation ──
echo "[9/10] Configuring journald log rotation..."
mkdir -p /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/compgraph.conf << 'EOF'
[Journal]
SystemMaxUse=500M
MaxRetentionSec=30day
EOF
systemctl restart systemd-journald

# ── 10. Install systemd units ──
echo "[10/10] Installing systemd units..."
cp "$APP_DIR/infra/systemd/compgraph.service" /etc/systemd/system/
cp "$APP_DIR/infra/systemd/compgraph-dashboard.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable compgraph compgraph-dashboard
systemctl enable caddy
systemctl start caddy

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Push .env file: scp .env root@<IP>:/opt/compgraph/.env"
echo "  2. Fix permissions: ssh compgraph-do 'chown compgraph:compgraph /opt/compgraph/.env && chmod 600 /opt/compgraph/.env'"
echo "  3. Start services: ssh compgraph-do 'systemctl start compgraph compgraph-dashboard'"
echo "  4. Verify: curl https://dev.compgraph.io/health"

#!/usr/bin/env bash
# setup-droplet.sh — Idempotent provisioning for CompGraph on Ubuntu 24.04
# Run as root on a fresh droplet: ssh compgraph-do 'bash -s' < infra/setup-droplet.sh
#
# Prerequisites:
#   - Git credentials configured (see step 5 comments)
#   - infra/ files available on main branch or SCP'd separately
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

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
    grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
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

# ── 4. Install uv (system-wide) ──
if [ ! -f /usr/local/bin/uv ]; then
    echo "[4/10] Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    cp "$HOME/.local/bin/uv" /usr/local/bin/uv
    cp "$HOME/.local/bin/uvx" /usr/local/bin/uvx
    chmod 755 /usr/local/bin/uv /usr/local/bin/uvx
else
    echo "[4/10] uv already installed, skipping."
fi

# ── 5. Clone repo ──
# Requires git credentials. Set up beforehand:
#   git config --global credential.helper store
#   echo "https://x-access-token:<TOKEN>@github.com" > /root/.git-credentials
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
sudo -u "$SERVICE_USER" uv sync

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
# Copy Caddyfile (may need SCP if infra/ not yet on main)
if [ -f "$APP_DIR/infra/Caddyfile" ]; then
    cp "$APP_DIR/infra/Caddyfile" /etc/caddy/Caddyfile
else
    echo "  WARNING: $APP_DIR/infra/Caddyfile not found. SCP it to /etc/caddy/Caddyfile manually."
fi

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
# Copy from repo if available, otherwise expect them to be SCP'd
for unit in compgraph.service; do
    if [ -f "$APP_DIR/infra/systemd/$unit" ]; then
        cp "$APP_DIR/infra/systemd/$unit" /etc/systemd/system/
    else
        echo "  WARNING: $APP_DIR/infra/systemd/$unit not found. SCP it to /etc/systemd/system/ manually."
    fi
done
systemctl daemon-reload
systemctl enable compgraph
systemctl enable caddy
systemctl start caddy

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Push .env file: scp .env compgraph-do:/opt/compgraph/.env"
echo "  2. Fix permissions: ssh compgraph-do 'chown compgraph:compgraph /opt/compgraph/.env && chmod 600 /opt/compgraph/.env'"
echo "  3. Start services: ssh compgraph-do 'systemctl start compgraph'"
echo "  4. Verify: curl https://dev.compgraph.io/health"

#!/usr/bin/env bash
# redis-setup.sh — Install and configure Redis on the CompGraph DO droplet
# Run as root: ssh compgraph-do 'bash -s' < infra/redis-setup.sh
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

echo "=== Redis Setup for CompGraph ==="

# ── 1. Install redis-server ──
if ! command -v redis-server &>/dev/null; then
    echo "[1/4] Installing redis-server..."
    apt-get update -qq
    apt-get install -y -qq redis-server > /dev/null
else
    echo "[1/4] redis-server already installed, skipping."
fi

# ── 2. Configure Redis ──
echo "[2/4] Writing /etc/redis/redis.conf..."
cat > /etc/redis/redis.conf << 'EOF'
bind 127.0.0.1
protected-mode yes
port 6379
supervised systemd
daemonize no

maxmemory 256mb
maxmemory-policy allkeys-lru

tcp-backlog 511
timeout 0
tcp-keepalive 300

loglevel notice
logfile /var/log/redis/redis-server.log

databases 16
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis
EOF

# ── 3. Enable and start ──
echo "[3/4] Enabling and starting redis-server..."
systemctl enable redis-server
systemctl restart redis-server

# ── 4. Verify ──
echo "[4/4] Verifying Redis..."
if redis-cli ping | grep -q PONG; then
    echo "Redis is running: $(redis-cli info server | grep redis_version)"
    echo ""
    echo "=== Redis setup complete ==="
    echo "Add to .env: REDIS_URL=redis://127.0.0.1:6379/0"
else
    echo "ERROR: Redis ping failed"
    journalctl -u redis-server -n 20 --no-pager
    exit 1
fi

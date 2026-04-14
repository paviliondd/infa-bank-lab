#!/bin/bash
# setup-containerlab.sh
# Chạy trên VPS 6 (netlab.bank-infra.lab) với quyền root
# Ubuntu 24.04 — không cần KVM

set -euo pipefail

echo "=== Bank Infra Lab — VPS 6 Setup ==="
echo "Host: $(hostname)"
echo "Date: $(date)"

# ── 1. Docker ────────────────────────────────────────────────────
echo ""
echo "[1/4] Installing Docker..."
apt-get update -qq
apt-get install -y curl git vim ufw -qq
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
usermod -aG docker root
echo "✓ Docker $(docker --version)"

# ── 2. Containerlab ──────────────────────────────────────────────
echo ""
echo "[2/4] Installing Containerlab..."
bash -c "$(curl -sL https://get.containerlab.dev)"
echo "✓ Containerlab $(containerlab version | head -1)"

# ── 3. Pull FRRouting image ──────────────────────────────────────
echo ""
echo "[3/4] Pulling FRRouting image (no KVM needed)..."
docker pull frrouting/frr:latest
echo "✓ FRRouting image ready"

# ── 4. Firewall ──────────────────────────────────────────────────
echo ""
echo "[4/4] Configuring firewall..."
ufw allow OpenSSH

# Allow SSH từ VPS 1 (GitLab Runner) vào management network containerlab
# Thay YOUR_VPS1_PRIVATE_IP bằng IP thật của VPS 1
ufw allow from YOUR_VPS1_PRIVATE_IP to any port 22
ufw allow from YOUR_VPS1_PRIVATE_IP to any port 830  # NETCONF

# Containerlab management network
ufw allow in on br-mgmt-net

ufw --force enable
echo "✓ Firewall configured"

# ── 5. Deploy topology ───────────────────────────────────────────
echo ""
echo "[5/5] Deploying network topology..."
mkdir -p /opt/bank-netlab
cp -r /root/containerlab/* /opt/bank-netlab/ 2>/dev/null || true

# Clone từ GitLab nếu repo đã có
# git clone http://gitlab.bank-infra.lab/bank-infra/infra-automation.git /opt/bank-netlab

# Deploy
cd /opt/bank-netlab
containerlab deploy --topo topology.yml --reconfigure

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Topology status:"
containerlab inspect --topo /opt/bank-netlab/topology.yml

echo ""
echo "Management IPs:"
echo "  sw1:     172.20.20.11"
echo "  sw2:     172.20.20.12"
echo "  router1: 172.20.20.13"
echo ""
echo "Test SSH:"
echo "  ssh root@172.20.20.11"

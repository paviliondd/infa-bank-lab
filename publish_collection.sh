#!/bin/bash
# publish_collection.sh - Script mô phỏng CI/CD đẩy Collection tự động

set -e

COLLECTION_DIR="/home/infra-automation/collections/ansible_collections/bank/network"
NEXUS_URL="http://103.110.85.124:8081"
NEXUS_USER="admin"
NEXUS_PASS="Aty9vYLt9pafLtnEttlb1s2MwHcAVCFGGgTsp1ies+U="

echo "==> Đang nện Búa thần: Building Ansible Collection..."
cd "${COLLECTION_DIR}"
ansible-galaxy collection build --force

TARBALL=$(ls -t bank-network-*.tar.gz | head -1)
VERSION=$(echo "${TARBALL}" | grep -oP '\d+\.\d+\.\d+')

echo "==> Đang bế file ${TARBALL} bắn lên trên Nexus..."
curl -s -u "${NEXUS_USER}:${NEXUS_PASS}" \
  --upload-file "${TARBALL}" \
  "${NEXUS_URL}/repository/ansible-collections/bank/network/${TARBALL}"

echo ""
echo "✅ Quá Đỉnh! Đã cất giấu bank.network v${VERSION} lên kho Nexus thành công!"
echo "   Lệnh rước nó về: ansible-galaxy collection install ${NEXUS_URL}/repository/ansible-collections/bank/network/${TARBALL} --force"

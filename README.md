# Bank Infrastructure Lab — infra-automation

## Tổng quan

Monorepo chứa toàn bộ source code cho Bank Infrastructure Lab.
CI/CD pipeline tự động hóa deploy network config, IaC, và platform engineering
theo chuẩn môi trường ngân hàng.

---

## Infrastructure

| VPS | Hostname | Service |
|-----|----------|---------|
| VPS 1 | gitlab.bank-infra.lab | GitLab CE + Runner + Ansible |
| VPS 2 | automation.bank-infra.lab | HashiCorp Vault + Ansible AWX |
| VPS 3 | k8s-master.bank-infra.lab | Kubernetes control-plane |
| VPS 4 | k8s-worker1.bank-infra.lab | Kubernetes worker + Prometheus |
| VPS 5 | k8s-worker2.bank-infra.lab | Kubernetes worker + Nexus |
| VPS 6 | netlab.bank-infra.lab | Containerlab + FRRouting |

---

## Lab Status

| Lab | Tên | Status |
|-----|-----|--------|
| 1.1 | VLAN Config CI/CD Pipeline | ✅ Done |
| 1.2 | Firewall Rule Automation | 🔲 Todo |
| 1.3 | Golden Image Pipeline | 🔲 Todo |
| 1.4 | Backup & DR Automation | 🔲 Todo |
| 2.1 | Terraform Modules | 🔲 Todo |
| 2.2 | Ansible Collection | 🔲 Todo |
| 2.3 | Terraform + Ansible | 🔲 Todo |
| 3.1 | Kubernetes Cluster | 🔲 Todo |
| 3.2 | Jenkins + Vault | 🔲 Todo |
| 3.3 | Prometheus + Grafana | 🔲 Todo |
| 3.4 | Nexus Repository | 🔲 Todo |
| 4.1 | Anomaly Detection AIOps | 🔲 Todo |
| 4.2 | Capacity Planning | 🔲 Todo |
| 5.1 | Capstone Self-Service Portal | 🔲 Todo |

---

## Lab 1.1 — VLAN Config CI/CD Pipeline ✅

### Mục tiêu
Tự động hóa deploy VLAN configuration lên network devices qua GitLab CI pipeline.
Mọi thay đổi config đi qua: code review → lint → validate → staging → production approval.

### Stack
- GitLab CE + Runner (VPS 1)
- Ansible CLI (chạy trên Runner)
- FRRouting containers (VPS 6, không cần KVM)
- Containerlab làm network emulator
- HashiCorp Vault (VPS 2, chuẩn bị cho Lab 3.2)

### Pipeline Flow

```
lint:ansible ──┐
lint:yaml   ──┘── validate:syntax ── validate:dry-run ── deploy:staging ── deploy:production
                                                                        ↘── rollback:staging
```

### VLAN Design

| VLAN | Name | Subnet | Mục đích |
|------|------|--------|----------|
| 10 | MGMT | 192.168.10.0/24 | Management network |
| 20 | INTERNAL | 192.168.20.0/24 | Internal banking apps |
| 30 | DMZ | 192.168.30.0/24 | Internet-facing zone |
| 99 | BLACKHOLE | — | Unused ports |

### Network Topology (Containerlab)

```
         [router1]
        /         \
    [sw1]         [sw2]
172.20.20.11   172.20.20.12
```

### Checkpoints

- [x] Pipeline chạy qua 4 stages không lỗi
- [x] lint:ansible pass
- [x] validate:syntax pass
- [x] validate:dry-run pass
- [x] deploy:staging — Ansible deploy config lên sw1, sw2, router1
- [x] deploy:production — manual approval gate hoạt động
- [x] rollback:staging — manual trigger có sẵn
- [x] Audit log ghi nhận user và timestamp

### Cách chạy thủ công

```bash
# Syntax check
ansible-playbook playbooks/network/vlan-config.yml \
  --inventory inventories/staging/network.yml \
  --syntax-check

# Dry-run
ansible-playbook playbooks/network/vlan-config.yml \
  --inventory inventories/staging/network.yml \
  --check --diff

# Deploy staging
ansible-playbook playbooks/network/vlan-config.yml \
  --inventory inventories/staging/network.yml \
  --diff

# Rollback
ansible-playbook playbooks/network/vlan-rollback.yml \
  --inventory inventories/staging/network.yml \
  -e "rollback_epoch=TIMESTAMP"
```

### ProxyJump SSH Config

Runner trên VPS 1 SSH vào containers trên VPS 6 qua ProxyJump:

```
VPS 1 (gitlab) → VPS 6 (netlab:103.110.85.105) → sw1/sw2/router1 (172.20.20.x)
```

---

## Cấu trúc thư mục

```
infra-automation/
├── .gitlab-ci.yml              # Pipeline chính
├── .ansible-lint               # Lint config
├── ansible.cfg                 # Ansible config
├── README.md
├── collections/
│   └── requirements.yml        # community.general, ansible.posix
├── containerlab/               # Network topology VPS 6
│   ├── topology.yml
│   └── startup-configs/
│       ├── sw1.cfg
│       ├── sw2.cfg
│       └── router1.cfg
├── inventories/
│   └── staging/
│       ├── network.yml
│       └── group_vars/
│           └── network_devices.yml
├── playbooks/
│   └── network/
│       ├── vlan-config.yml
│       └── vlan-rollback.yml
├── roles/
│   └── cisco_vlan/
│       ├── tasks/main.yml
│       ├── handlers/main.yml
│       ├── defaults/main.yml
│       └── templates/
│           ├── vlan.j2
│           └── daemons.j2
└── scripts/
    └── setup-vps6-containerlab.sh
```

---

## Lessons Learned

- GitLab Runner 18.x bị bug `Initializing executor providers` trên Ubuntu 24
  → Fix: dùng binary v17.9.0 trực tiếp
- FRRouting container lock file `/etc/frr/frr.conf` khi Ansible dùng atomic rename
  → Fix: dùng `dd if= of=` hoặc `shell` để ghi trực tiếp
- ProxyJump cần SSH key của gitlab-runner user được add vào cả VPS 6 và containers
- `ANSIBLE_STDOUT_CALLBACK: yaml` conflict với community.general apt version
  → Fix: dùng `default` callback

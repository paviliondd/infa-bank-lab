# Bank Infrastructure Lab — `infra-automation`

> **Monorepo** tự động hóa toàn bộ vòng đời hạ tầng ngân hàng: từ network config, IaC, Kubernetes platform, đến AIOps — theo chuẩn CI/CD pipeline của môi trường tài chính.

---

## Mục lục

- [Tổng quan](#tổng-quan)
- [Kiến trúc hạ tầng](#kiến-trúc-hạ-tầng)
- [Tech Stack](#tech-stack)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [CI/CD Pipeline](#cicd-pipeline)
- [Lab Roadmap](#lab-roadmap)
  - [Lab 1.1 — VLAN Config CI/CD Pipeline](#lab-11--vlan-config-cicd-pipeline-)
  - [Lab 1.2 — Firewall Rule Automation](#lab-12--firewall-rule-automation-)
  - [Lab 1.3 — Golden Image Pipeline](#lab-13--golden-image-pipeline)
  - [Lab 1.4 — Backup & DR Automation](#lab-14--backup--dr-automation-)
  - [Lab 2.1–2.3 — IaC & AWS Terraform](#lab-21--23--iac--aws-terraform-)
  - [Lab 3.1–3.4 — Kubernetes Platform](#lab-31--34--kubernetes-platform-)
  - [Lab 4.1 — AIOps Anomaly Detection](#lab-41--aiops-anomaly-detection-)
  - [Lab 4.2 — Capacity Planning](#lab-42--capacity-planning-)
  - [Lab 5.1 — Capstone Self-Service Portal](#lab-51--capstone-self-service-portal-)
- [Hướng dẫn chạy thủ công](#hướng-dẫn-chạy-thủ-công)
- [Lessons Learned](#lessons-learned)

---

## Tổng quan

Project này xây dựng một **Bank Infrastructure Lab** hoàn chỉnh trên 6 VPS thực tế, mô phỏng môi trường hạ tầng ngân hàng chuẩn doanh nghiệp:

- **Network Automation** — deploy VLAN, firewall rules qua Ansible + GitLab CI
- **Infrastructure as Code** — Terraform modules (AWS VPC, Security Groups, EC2 Golden Image)
- **Kubernetes Platform** — K8s cluster tự quản lý, Jenkins, Vault, Prometheus, Nexus
- **AIOps** — Anomaly detection bằng Isolation Forest + Capacity Planning bằng Prophet
- **Self-Service Portal** — Capstone app cho phép dev tự provision hạ tầng

---

## Kiến trúc hạ tầng

```
┌─────────────────────────────────────────────────────────────────┐
│                     Bank Infrastructure Lab                     │
├─────────┬──────────────────────────────┬────────────────────────┤
│  VPS    │  Hostname                    │  Services              │
├─────────┼──────────────────────────────┼────────────────────────┤
│  VPS 1  │  gitlab.bank-infra.lab       │  GitLab CE + Runner    │
│  VPS 2  │  automation.bank-infra.lab   │  HashiCorp Vault + AWX │
│  VPS 3  │  k8s-master.bank-infra.lab   │  Kubernetes control-   │
│         │                              │  plane                 │
│  VPS 4  │  k8s-worker1.bank-infra.lab  │  K8s worker +          │
│         │                              │  Prometheus            │
│  VPS 5  │  k8s-worker2.bank-infra.lab  │  K8s worker + Nexus    │
│  VPS 6  │  netlab.bank-infra.lab       │  Containerlab + FRR    │
└─────────┴──────────────────────────────┴────────────────────────┘
```

**Network Topology (Containerlab — VPS 6):**

```
            [router1]
           /         \
       [sw1]         [sw2]
  172.20.20.11   172.20.20.12
```

**SSH ProxyJump Flow:**
```
VPS 1 (gitlab-runner) → VPS 6 (netlab) → sw1 / sw2 / router1
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| CI/CD | GitLab CE, GitLab Runner, Jenkins |
| Config Mgmt | Ansible, Ansible AWX, ansible-lint |
| IaC | Terraform (AWS provider) |
| Secret Mgmt | HashiCorp Vault (AppRole auth) |
| Container Orch | Kubernetes (kubeadm), Helm |
| Network Emulation | Containerlab, FRRouting (FRR) |
| Monitoring | Prometheus, Grafana, Alertmanager |
| Artifact Registry | Nexus Repository |
| Security Scanning | tfsec, Trivy, RBAC Audit |
| AIOps | Python, Isolation Forest (scikit-learn), FastAPI |
| Capacity Planning | Prophet (Meta), FastAPI, Prometheus |
| App Runtime | Docker, Kubernetes |

---

## Cấu trúc thư mục

```
infra-automation/
├── .gitlab-ci.yml                  # Pipeline chính (7 stages)
├── .ansible-lint                   # Ansible lint config
├── ansible.cfg                     # Ansible global config
│
├── playbooks/
│   ├── network/
│   │   ├── vlan-config.yml         # Lab 1.1 — deploy VLAN
│   │   └── vlan-rollback.yml       # Lab 1.1 — rollback VLAN
│   ├── firewall/
│   │   ├── firewall-rules.yml      # Lab 1.2 — deploy iptables
│   │   └── firewall-rollback.yml   # Lab 1.2 — rollback firewall
│   └── ci/
│       └── jenkins-setup.yml       # Lab 3.2 — deploy Jenkins
│
├── roles/
│   ├── cisco_vlan/                 # Lab 1.1 — VLAN role (FRR)
│   ├── bank_firewall/              # Lab 1.2 — iptables + Vault
│   ├── vault-docker/               # Lab 3.2 — HashiCorp Vault
│   ├── master/ & worker/           # Lab 3.1 — K8s cluster init
│   ├── nfs-server/ & nfs-client/   # Lab 3.1 — NFS provisioner
│   ├── k8s-ingress/                # Lab 3.1 — Nginx Ingress
│   ├── k8s-cert-manager/           # Lab 3.1 — TLS cert manager
│   ├── k8s-rbac/                   # Lab 3.4 — RBAC audit
│   ├── k8s-banking-app/            # Lab 5.1 — Bank Portal
│   ├── k8s-aiops/                  # Lab 4.1 — AIOps service
│   ├── k8s-capacity-planner/       # Lab 4.2 — Capacity planner
│   └── k8s-capstone/               # Lab 5.1 — Capstone portal
│
├── inventories/staging/
│   ├── network.yml                 # Network devices inventory
│   ├── servers.yml                 # Linux servers inventory
│   └── group_vars/
│       ├── network_devices.yml
│       └── linux_servers.yml
│
├── terraform/
│   ├── modules/
│   │   ├── aws-network/            # VPC, Subnets, Route Tables
│   │   ├── aws-security/           # Security Groups (bank rules)
│   │   └── aws-ec2-golden/         # EC2 từ Golden AMI (Packer)
│   └── environments/staging/       # Staging env tfvars
│
├── collections/
│   ├── requirements.yml
│   └── ansible_collections/bank/network/  # Custom bank.network collection
│       └── roles/vlan_config/      # Multi-vendor VLAN (Cisco/Juniper/Arista)
│
├── containerlab/
│   ├── topology.yml                # Lab network topology
│   └── startup-configs/            # FRR startup configs (sw1, sw2, router1)
│
├── dr_backup/
│   ├── ansible_backup.yml          # Backup network config (scheduled)
│   ├── ansible_dr_restore.yml      # DR restore playbook
│   ├── backup_frr_linux.py         # Python backup script
│   └── backups/                    # Lưu config đã backup
│
├── apps/
│   ├── bank_portal/                # Lab 5.1 — FastAPI + Prometheus metrics
│   ├── aiops/                      # Lab 4.1 — Anomaly detection service
│   └── capacity_planner/           # Lab 4.2 — Capacity forecast service
│
├── monitoring-ansible/             # Lab 3.3 — Prometheus + Grafana setup
│
└── scripts/
    └── setup-vps6-containerlab.sh  # Script khởi tạo VPS 6
```

---

## CI/CD Pipeline

Pipeline gồm **7 stages**, chạy tự động khi push code:

```
lint ──► validate ──► deploy-ci ──► deploy-staging ──► test-connectivity ──► deploy-prod ──► network-dr-schedule
```

| Stage | Jobs | Trigger |
|-------|------|---------|
| `lint` | ansible-lint, yamllint, tfsec, trivy-iac | auto |
| `validate` | syntax-check, dry-run | auto (sau lint) |
| `deploy-ci` | deploy:jenkins | manual |
| `deploy-staging` | vlan-staging, firewall-staging, aiops-staging, capacity-staging | auto / manual |
| `test-connectivity` | firewall-connectivity (SSH, TCP, ICMP, iptables verify) | auto |
| `deploy-prod` | vlan-production, firewall-production | manual (main branch only) |
| `network-dr-schedule` | auto_network_backup | scheduled pipeline |

**Secrets Management:** Vault AppRole inject SSH whitelist IPs vào firewall template tại runtime — không hardcode trong repo.

---

## Lab Roadmap

### Lab 1.1 — VLAN Config CI/CD Pipeline ✅

Tự động hóa deploy VLAN configuration lên network devices qua GitLab CI. Mọi thay đổi đi qua: `code review → lint → dry-run → staging → production approval`.

**VLAN Design:**

| VLAN | Name | Subnet | Mục đích |
|------|------|--------|----------|
| 10 | MGMT | 192.168.10.0/24 | Management network |
| 20 | INTERNAL | 192.168.20.0/24 | Internal banking apps |
| 30 | DMZ | 192.168.30.0/24 | Internet-facing zone |
| 99 | BLACKHOLE | — | Unused ports |

**Checkpoints:**
- [x] Pipeline 4 stages không lỗi
- [x] ansible-lint pass
- [x] validate:dry-run pass
- [x] deploy:staging — Ansible deploy lên sw1, sw2, router1
- [x] deploy:production — manual approval gate
- [x] rollback:staging — manual trigger
- [x] Audit log ghi nhận user + timestamp

---

### Lab 1.2 — Firewall Rule Automation ✅

Tự động hóa deploy iptables rules lên Linux servers qua pipeline. SSH whitelist IPs được fetch từ **HashiCorp Vault** (AppRole auth) tại runtime — không hardcode.

**Flow:** Vault AppRole → fetch SSH IPs → render `iptables.j2` → backup → apply → verify SSH → auto-rollback nếu SSH bị block.

**Connectivity Test Stage:** Sau deploy, pipeline tự động kiểm tra SSH (port 22), HTTP/HTTPS (80/443), ICMP ping, và xác minh iptables rules trên remote host.

---

### Lab 1.3 — Golden Image Pipeline

Packer + Ansible build CIS-hardened Ubuntu 24.04 AMI. Terraform module `aws-ec2-golden` tự động dùng AMI mới nhất khi provision EC2:

```hcl
data "aws_ami" "golden_ami" {
  most_recent = true
  owners      = ["self"]
  filter {
    name   = "name"
    values = ["ubuntu-2404-cis-golden-*", "GoldenImage-Ubuntu2404-CIS*"]
  }
}
```

---

### Lab 1.4 — Backup & DR Automation ✅

Backup tự động network config theo lịch (scheduled pipeline). DR restore bằng một ansible-playbook duy nhất.

```bash
# Chạy backup thủ công
cd dr_backup
ansible-playbook -i ../inventories/staging/network.yml ansible_backup.yml

# DR restore
ansible-playbook -i ../inventories/staging/network.yml ansible_dr_restore.yml \
  -e "restore_epoch=TIMESTAMP"
```

Backup files được lưu tại `dr_backup/backups/<hostname>/frr_latest.conf` và upload lên GitLab artifacts (TTL 7 ngày).

---

### Lab 2.1–2.3 — IaC & AWS Terraform ✅

Ba Terraform modules tái sử dụng theo chuẩn ngân hàng:

| Module | Chức năng |
|--------|-----------|
| `aws-network` | VPC, Public/Private Subnets, Route Tables, Internet Gateway |
| `aws-security` | Security Groups — whitelist SSH IPs, deny all mặc định |
| `aws-ec2-golden` | EC2 instances từ CIS-hardened Golden AMI |

**IaC Security Scanning** tích hợp CI:
- `tfsec` — scan Terraform code mức HIGH severity
- `trivy-iac` — scan toàn bộ IaC files (`.tf`, `.yml`, `.yaml`)

```bash
# Init và apply staging
cd terraform/environments/staging
terraform init
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

**Ansible Collection `bank.network` v1.1.0** — Chuẩn hóa VLAN config cho 3 vendor:

| Platform | Collection Role |
|----------|----------------|
| Cisco IOS | `cisco.ios` |
| Juniper Junos | `junipernetworks.junos` |
| Arista EOS | `arista.eos` |

---

### Lab 3.1–3.4 — Kubernetes Platform ✅

| Lab | Nội dung | Status |
|-----|----------|--------|
| 3.1 | K8s cluster (kubeadm) + NFS + Ingress + cert-manager | ✅ |
| 3.2 | Jenkins + HashiCorp Vault (Docker) | ✅ |
| 3.3 | Prometheus + Grafana + Alertmanager | ✅ |
| 3.4 | Nexus Repository + RBAC Audit | ✅ |

Tất cả components được deploy bằng Ansible playbooks vào K8s cluster 3 nodes (1 master, 2 workers). NFS server trên VPS 3/4 cung cấp PersistentVolume cho Prometheus, Nexus, AIOps models.

---

### Lab 4.1 — AIOps Anomaly Detection ✅

Service phát hiện bất thường hạ tầng theo thời gian thực bằng **Isolation Forest**.

**Architecture:**
```
Prometheus → Collector (scrape metrics) → Model (Isolation Forest) → FastAPI Service
                                                                           ↓
                                                               /predict  /metrics  /health
                                                                           ↓
                                                                    Grafana Dashboard
                                                                    + Alertmanager
```

**Endpoints:**

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/health` | GET | Health check |
| `/predict` | POST | Nhận metric vector, trả về anomaly score |
| `/metrics` | GET | Prometheus scrape endpoint |

**Training Pipeline:** CronJob K8s chạy `train_model.py` định kỳ, tái huấn luyện model từ dữ liệu Prometheus mới. Model được lưu dưới dạng `.pkl` trên PVC.

---

### Lab 4.2 — Capacity Planning ✅

Service dự báo ngưỡng tài nguyên bằng **Meta Prophet** (time-series forecasting).

**Tính năng:**
- Forecast CPU/Memory utilization 30–90 ngày tới
- Tính `days_until_breach` (số ngày trước khi đạt ngưỡng 90%)
- Export Prometheus metric `capacity_days_until_breach` cho Alertmanager
- Grafana SimpleJSON datasource integration

**K8s Resources:** Deployment + CronJob (retrain) + PVC (model storage) + Ingress → `https://capacity.linuxunity.com`

---

### Lab 5.1 — Capstone Self-Service Portal ✅

**Bank Portal** — FastAPI app cho phép developer tự provision hạ tầng qua giao diện web, tích hợp Prometheus metrics để monitor hoạt động:

| Metric | Loại | Mô tả |
|--------|------|-------|
| `bank_requests_total` | Counter | Tổng HTTP requests (method, endpoint, status) |
| `bank_request_latency_seconds` | Histogram | Độ trễ requests |
| `bank_transfer_amount_total` | Counter | Tổng giao dịch (USD) |

Portal deploy lên K8s với Ingress TLS (`cert-manager`), RBAC policies, và audit log.

---

## Hướng dẫn chạy thủ công

### VLAN Config

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

### Firewall

```bash
# Deploy
ansible-playbook playbooks/firewall/firewall-rules.yml \
  --inventory inventories/staging/servers.yml \
  --diff

# Rollback
ansible-playbook playbooks/firewall/firewall-rollback.yml \
  --inventory inventories/staging/servers.yml \
  -e "rollback_epoch=TIMESTAMP"
```

### Ansible Collection

```bash
# Build và publish
./publish_collection.sh

# Install từ Nexus / local
ansible-galaxy collection install collections/ansible_collections/bank/network/bank-network-1.1.0.tar.gz
```

### Containerlab (VPS 6)

```bash
# Khởi tạo môi trường
bash scripts/setup-vps6-containerlab.sh

# Start topology
cd containerlab
containerlab deploy --topo topology.yml

# Destroy
containerlab destroy --topo topology.yml
```

---

## Lessons Learned

| Vấn đề | Root Cause | Fix |
|--------|-----------|-----|
| GitLab Runner lỗi `Initializing executor providers` | Runner 18.x bug trên Ubuntu 24 | Dùng binary v17.9.0 trực tiếp |
| FRR container lock file khi Ansible ghi `frr.conf` | `atomic rename` không hỗ trợ | Dùng `shell: dd if= of=` ghi trực tiếp |
| ProxyJump SSH fail từ Runner | SSH key chưa được add vào cả VPS 6 lẫn containers | Add key cho cả 2 hop |
| `ANSIBLE_STDOUT_CALLBACK: yaml` conflict | Incompatible với `community.general` apt module | Chuyển về `default` callback |
| Vault AppRole token expire giữa pipeline | Token TTL quá ngắn | Tăng TTL + refresh trong `vault.yml` task |

---

## License

MIT — See [LICENSE](LICENSE) for details.

---

*Maintained by Bank Infrastructure Team · [bank-infra/infra-automation](http://gitlab.bank.local/bank-infra/infra-automation)*

# Data block tự động săn lùng Image do Ansible/Packer đúc
data "aws_ami" "golden_ami" {
  most_recent = true
  owners      = ["self"] # AMI do chính account này tạo ra ở Lab 1.3

  filter {
    name   = "name"
    # Mapping đúng pattern tên image sinh ra từ Packer
    values = ["ubuntu-2404-cis-golden-*", "GoldenImage-Ubuntu2404-CIS*"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

resource "aws_instance" "app_server" {
  count                  = var.instance_count
  ami                    = data.aws_ami.golden_ami.id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_ids[count.index % length(var.subnet_ids)]
  vpc_security_group_ids = [var.security_group_id]

  # SSH Key Pair
  key_name = var.key_name

  tags = {
    Name        = "${var.environment}-app-node-${count.index + 1}"
    Environment = var.environment
    ImageOrigin = "Packer-CIS-Hardened"
    ManagedBy   = "Terraform"
  }
}

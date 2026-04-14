resource "aws_security_group" "bank_base_sg" {
  name        = "${var.environment}-bank-base-sg"
  description = "Bank Grade Security Group. Deny all inbound by default."
  vpc_id      = var.vpc_id

  # Allow inbound local VPC traffic
  ingress {
    description = "Allow all inbound traffic within VPC"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
  }

  # Allow specific whitelisted SSH IPs
  dynamic "ingress" {
    for_each = var.whitelist_ssh_ips
    content {
      description = "Allow SSH from Corporate IP"
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = [ingress.value]
    }
  }

  # Allow all outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.environment}-bank-base-sg"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

provider "aws" {
  region = var.aws_region
}

# 1. Triển khai Network Core
module "vpc_network" {
  source              = "../../modules/aws-network"
  environment         = var.environment
  vpc_cidr            = var.vpc_cidr
  public_subnet_cidrs = var.public_subnet_cidrs
  availability_zones  = var.availability_zones
}

# 2. Áp Security Rules cứng của Ngân hàng
module "security_firewall" {
  source            = "../../modules/aws-security"
  environment       = var.environment
  vpc_id            = module.vpc_network.vpc_id
  vpc_cidr          = var.vpc_cidr
  whitelist_ssh_ips = var.whitelist_ssh_ips
}

# 3. Ép khuôn máy ảo ảo dựa theo Golden AMI
module "app_servers" {
  source            = "../../modules/aws-ec2-golden"
  environment       = var.environment
  instance_count    = var.instance_count
  instance_type     = var.instance_type
  key_name          = var.key_name
  
  # Cắm vào Subnet và Security Group vừa tạo
  subnet_ids        = module.vpc_network.public_subnet_ids
  security_group_id = module.security_firewall.security_group_id
}

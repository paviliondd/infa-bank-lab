environment     = "staging"
aws_region      = "ap-southeast-1"

# Network
vpc_cidr            = "10.10.0.0/16"
public_subnet_cidrs = ["10.10.1.0/24", "10.10.2.0/24"]
availability_zones  = ["ap-southeast-1a", "ap-southeast-1b"]

# Thu hẹp tầm quét bảo mật. Điền IP tĩnh Office/Dev-Machine vào đây. Dùng 0.0.0.0/0 TẠM THỜI nếu xài Cloud shell
whitelist_ssh_ips   = ["0.0.0.0/0"] 

# Instances
instance_count = 2
instance_type  = "t3.micro"
key_name       = "vps-aws-key" # Hãy thay đổi bằng tên key có sẵn trên giao diện AWS EC2

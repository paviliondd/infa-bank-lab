variable "environment" {
  description = "Tên phân vùng môi trường (e.g. staging, prod)"
  type        = string
}

variable "vpc_cidr" {
  description = "Dải CIDR cho VPC (vd: 10.0.0.0/16)"
  type        = string
}

variable "public_subnet_cidrs" {
  description = "List CIDRs cho Public Subnets"
  type        = list(string)
}

variable "availability_zones" {
  description = "List các Availability Zones (Vd: ap-southeast-1a, ap-southeast-1b)"
  type        = list(string)
}

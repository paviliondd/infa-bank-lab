variable "aws_region" {
  description = "Region triển khai Cloud"
  type        = string
  default     = "ap-southeast-1"
}

variable "environment" {
  type    = string
  default = "staging"
}

variable "vpc_cidr" {
  type = string
}

variable "public_subnet_cidrs" {
  type = list(string)
}

variable "availability_zones" {
  type = list(string)
}

variable "whitelist_ssh_ips" {
  type = list(string)
}

variable "instance_count" {
  type = number
}

variable "instance_type" {
  type = string
}

variable "key_name" {
  type = string
}

variable "environment" {
  description = "Tên phân vùng môi trường"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID để đính kèm SG"
  type        = string
}

variable "vpc_cidr" {
  description = "Dải IP nội mạng của VPC để trust traffic"
  type        = string
}

variable "whitelist_ssh_ips" {
  description = "Danh sách IP văn phòng được phép kết nối SSH"
  type        = list(string)
  default     = []
}

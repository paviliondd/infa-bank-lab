variable "environment" {
  description = "Tên môi trường triển khai"
  type        = string
}

variable "instance_count" {
  description = "Số lượng máy chủ cần Deploy"
  type        = number
  default     = 1
}

variable "instance_type" {
  description = "Loại EC2 Instance. Khuyến cáo default t3.micro để nằm trong Free Tier"
  type        = string
  default     = "t3.micro"
}

variable "subnet_ids" {
  description = "Danh sách ID subnet (công cộng hoặc riêng tư) để spin-up EC2"
  type        = list(string)
}

variable "security_group_id" {
  description = "Mã định danh SG để giới hạn port"
  type        = string
}

variable "key_name" {
  description = "Tên SSH Key Pair có sẵn trên AWS để mount vào máy ảo"
  type        = string
  default     = ""
}

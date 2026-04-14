output "vpc_id" {
  description = "Mã ID của VPC được tạo"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Danh sách ID của các Public Subnets"
  value       = aws_subnet.public_subnet[*].id
}

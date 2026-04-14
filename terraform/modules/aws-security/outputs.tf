output "security_group_id" {
  description = "ID của Security Group vừa tạo"
  value       = aws_security_group.bank_base_sg.id
}

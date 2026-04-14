output "instance_ids" {
  description = "Danh sách ID các EC2 Insntances"
  value       = aws_instance.app_server[*].id
}

output "instance_public_ips" {
  description = "IP Public của các server sinh ra"
  value       = aws_instance.app_server[*].public_ip
}

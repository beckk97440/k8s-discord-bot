# OUTPUTS

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "subnet_id" {
  description = "SUBNET ID"
  value       = aws_subnet.public.id
}

output "security_group_id" {
  description = "SG ID"
  value       = aws_security_group.worker.id
}

output "worker_instance_id" {
  description = "EC2 INSTANCE ID"
  value       = aws_instance.worker.id
}

output "worker_public_ip" {
  description = "PUBLIC EC2 INSTANCE IP"
  value       = aws_instance.worker.public_ip
}

output "worker_private_ip" {
  description = "PRIVATE EC2 INSTANCE IP"
  value       = aws_instance.worker.private_ip
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.watchdog.function_name
}

output "ssh_command" {
  description = "SSH command to connect to the EC2 instance"
  value       = "ssh -i ~/.ssh/id_ed25519_aws_k8s.pub ubuntu@${aws_instance.worker.public_ip}"
}
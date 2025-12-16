# AMI UBUNTU 22.04

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]  # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}


# SSH KEY PAIR

resource "aws_key_pair" "main" {
  key_name   = "${var.project_name}-key"
  public_key = file("~/.ssh/id_ed25519_aws_k8s.pub")

  tags = {
    Name = "${var.project_name}-key"
  }
}


# EC2 INSTANCE - WORKER NODE

resource "aws_instance" "worker" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.main.key_name
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.worker.id]

  user_data = templatefile("${path.module}/user-data.sh", {
    tailscale_auth_key = var.tailscale_auth_key
    discord_token      = var.discord_token
    match_channel_id   = var.match_channel_id
    news_channel_id    = var.news_channel_id
  })

  # Force recreation when user_data changes
  user_data_replace_on_change = true

  root_block_device {
    volume_type = "gp3"
    volume_size = 8
    encrypted   = true
  }

  tags = {
    Name = "${var.project_name}-worker"
    Role = "k8s-worker"
  }

  instance_initiated_shutdown_behavior = "stop"
}
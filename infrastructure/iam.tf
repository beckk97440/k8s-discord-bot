# IAM ROLE FOR LAMBDA WATCHDOG

resource "aws_iam_role" "lambda_watchdog" {
  name = "${var.project_name}-lambda-watchdog-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = {
    Name = "${var.project_name}-lambda-watchdog-role"
  }
}


# POLICIES - PERMISSIONS EC2

resource "aws_iam_role_policy_attachment" "lambda_ec2" {
  role       = aws_iam_role.lambda_watchdog.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2FullAccess"
}


# POLICIES - PERMISSIONS CLOUDWATCH LOGS

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_watchdog.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}
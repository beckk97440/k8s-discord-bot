# ARCHIVE LAMBDA CODE

data "archive_file" "lambda_watchdog" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/watchdog"
  output_path = "${path.module}/lambda_watchdog.zip"
}


# FUNCTION LAMBDA

resource "aws_lambda_function" "watchdog" {
  filename         = data.archive_file.lambda_watchdog.output_path
  function_name    = "${var.project_name}-watchdog"
  role            = aws_iam_role.lambda_watchdog.arn
  handler         = "handler.lambda_handler"
  runtime         = "python3.11"
  timeout         = 60
  source_code_hash = data.archive_file.lambda_watchdog.output_base64sha256

  environment {
    variables = {
      WORKER_INSTANCE_ID  = aws_instance.worker.id
      HEALTHCHECK_URL = var.healthcheck_url
    }
  }

  tags = {
    Name = "${var.project_name}-watchdog"
  }
}
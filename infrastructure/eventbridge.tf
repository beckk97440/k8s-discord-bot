# EVENTBRIDGE RULE - CRON

resource "aws_cloudwatch_event_rule" "watchdog_trigger" {
  name                = "${var.project_name}-watchdog-trigger"
  description         = "Trigger watchdog every 5 minutes"
  schedule_expression = "rate(5 minutes)"

  tags = {
    Name = "${var.project_name}-watchdog-trigger"
  }
}


# EVENTBRIDGE TARGET - LAMBDA

resource "aws_cloudwatch_event_target" "watchdog" {
  rule      = aws_cloudwatch_event_rule.watchdog_trigger.name
  target_id = "lambda"
  arn       = aws_lambda_function.watchdog.arn
}


# PERMISSION EVENTBRIDGE -> LAMBDA

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.watchdog.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.watchdog_trigger.arn
}
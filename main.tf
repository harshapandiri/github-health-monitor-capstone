terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }

    archive = {
      source = "hashicorp/archive"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

data "aws_iam_role" "lab_role" {
  name = "LabRole"
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/lambda.zip"
}

resource "aws_secretsmanager_secret" "github_api_config" {
  name        = "github-health-monitor/api-config"
  description = "GitHub API token/config for GitHub Project Health Monitor. Value is set outside Terraform."
}

resource "aws_lambda_function" "github_health_monitor" {
  function_name = "github-project-health-monitor"

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  role    = data.aws_iam_role.lab_role.arn
  handler = "handler.lambda_handler"
  runtime = "python3.12"
  timeout = 20

  environment {
    variables = {
      SECRET_NAME = aws_secretsmanager_secret.github_api_config.name
      PROJECT     = "GitHub Project Health Monitor"
    }
  }
}

resource "aws_apigatewayv2_api" "github_health_api" {
  name          = "github-health-monitor-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.github_health_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.github_health_monitor.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "health_route" {
  api_id    = aws_apigatewayv2_api.github_health_api.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.github_health_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "allow_api_gateway" {
  statement_id  = "AllowExecutionFromHttpApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.github_health_monitor.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.github_health_api.execution_arn}/*/*"
}

output "lambda_function_name" {
  value = aws_lambda_function.github_health_monitor.function_name
}

output "lambda_execution_role_arn" {
  value = aws_lambda_function.github_health_monitor.role
}

output "secret_name" {
  value = aws_secretsmanager_secret.github_api_config.name
}

output "health_endpoint_url" {
  value = "${aws_apigatewayv2_stage.default_stage.invoke_url}/health"
}
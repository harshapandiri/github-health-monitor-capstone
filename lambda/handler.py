import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

import boto3


SECRET_NAME = os.environ.get("SECRET_NAME", "github-health-monitor/api-config")
GITHUB_API_BASE = "https://api.github.com"


def get_secret_config():
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=SECRET_NAME)
    return json.loads(response["SecretString"])


def github_get(path, token):
    url = f"{GITHUB_API_BASE}{path}"

    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "github-project-health-monitor",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def lambda_handler(event, context):
    try:
        config = get_secret_config()

        token = config["GITHUB_TOKEN"]
        owner = config["GITHUB_OWNER"]
        repo = config["GITHUB_REPO"]

        repo_info = github_get(f"/repos/{owner}/{repo}", token)
        issues = github_get(f"/repos/{owner}/{repo}/issues?state=open&per_page=100", token)
        commits = github_get(f"/repos/{owner}/{repo}/commits?per_page=5", token)

        try:
            workflow_runs = github_get(f"/repos/{owner}/{repo}/actions/runs?per_page=1", token)
            latest_workflow = workflow_runs.get("workflow_runs", [{}])[0]
            workflow_status = latest_workflow.get("conclusion") or latest_workflow.get("status") or "unknown"
        except Exception:
            workflow_status = "not_available"

        real_open_issues = [
            issue for issue in issues
            if "pull_request" not in issue
        ]

        recent_commit_messages = [
            commit["commit"]["message"].split("\n")[0]
            for commit in commits
        ]

        open_issues_count = len(real_open_issues)
        stars = repo_info.get("stargazers_count", 0)
        forks = repo_info.get("forks_count", 0)

        health_score = 100
        health_score -= min(open_issues_count * 5, 40)

        if workflow_status in ["failure", "cancelled", "timed_out"]:
            health_score -= 25
        elif workflow_status == "not_available":
            health_score -= 5

        health_score = max(0, min(100, health_score))

        if health_score >= 80:
            status = "healthy"
        elif health_score >= 50:
            status = "needs_attention"
        else:
            status = "unhealthy"

        checked_at = datetime.now(timezone.utc).isoformat()

        report = {
            "project": "GitHub Project Health Monitor",
            "repository": f"{owner}/{repo}",
            "health_score": health_score,
            "status": status,
            "open_issues": open_issues_count,
            "stars": stars,
            "forks": forks,
            "recent_commits": recent_commit_messages,
            "latest_workflow_status": workflow_status,
            "last_checked_utc": checked_at,
            "external_api_called": True,
            "secret_read_at_runtime": True
        }

        table_name = os.environ.get("TABLE_NAME")

        if table_name:
            dynamodb = boto3.resource("dynamodb")
            table = dynamodb.Table(table_name)

            table.put_item(
                Item={
                    "repository": report["repository"],
                    "checked_at": report["last_checked_utc"],
                    "health_score": report["health_score"],
                    "status": report["status"],
                    "open_issues": report["open_issues"],
                    "stars": report["stars"],
                    "forks": report["forks"],
                    "external_api_called": True
                }
            )

            report["stored_in_dynamodb"] = True
        else:
            report["stored_in_dynamodb"] = False

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(report)
        }

    except urllib.error.HTTPError as error:
        return {
            "statusCode": error.code,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "error": "GitHub API request failed",
                "status": error.code,
                "details": error.read().decode("utf-8")
            })
        }

    except Exception as error:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "error": "Lambda failed",
                "details": str(error)
            })
        }
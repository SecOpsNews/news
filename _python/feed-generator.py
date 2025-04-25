import os
import requests
import feedgenerator
import pytz
from datetime import datetime, timezone
import config

# GitHub API interaction
def get_github_issues(repo_owner, repo_name, token=None):
    """Fetch open issues from GitHub API"""
    issues = []
    page = 1
    per_page = 100
    max_pages = 10  # Limit to avoid excessive API calls

    while page <= max_pages:
        issues_page = fetch_issues_page(repo_owner, repo_name, token, page, per_page)
        if not issues_page:
            break
        issues.extend(issues_page)

        # Check if we've reached the last page
        if len(issues_page) < per_page:
            break

        page += 1

    print(f"Total issues collected: {len(issues)}")
    return issues

def fetch_issues_page(repo_owner, repo_name, token, page, per_page):
    """Helper function to fetch a single page of issues"""
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    # Add authorization header only if a valid token is provided
    if token and token != "test":
        headers["Authorization"] = f"Bearer {token}"
    elif not token or token == "test":
        print("Warning: No GitHub token provided. Using unauthenticated requests with lower rate limits.")

    params = {
        "state": "open",
        "per_page": per_page,
        "page": page
    }

    try:
        print(f"Fetching page {page}...")
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        page_issues = response.json()
        if not page_issues:
            print("No more issues found.")
            return []

        print(f"Retrieved {len(page_issues)} issues from page {page}")
        return page_issues

    except requests.exceptions.HTTPError as e:
        handle_http_error(e, page)
        return []
    except Exception as e:
        raise ValueError(f"Error fetching issues: {str(e)}")

def handle_http_error(error, page):
    """Handle HTTP errors from GitHub API"""
    if error.response.status_code == 401:
        raise ValueError("GitHub API authentication failed. Please check your token or use a valid token.")
    elif error.response.status_code == 403 and "rate limit exceeded" in str(error.response.text).lower():
        raise ValueError("GitHub API rate limit exceeded. Please wait or use a valid token.")
    elif error.response.status_code == 422:
        # Handle pagination errors gracefully
        print(f"Warning: Pagination issue detected (422 error). Stopping at page {page-1}.")
    else:
        raise ValueError(f"GitHub API error: {str(error)}")

# Date formatting utilities
def format_time_ago(timestamp_str):
    """Convert ISO timestamp to '2 hours ago' format"""
    try:
        # Parse the ISO format timestamp
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))

        # Get current time in UTC
        now = datetime.now(timezone.utc)

        # Calculate the time difference
        diff = now - timestamp
        seconds = diff.total_seconds()

        # Format based on time difference
        return format_seconds_to_time_ago(seconds)
    except Exception as e:
        # Return the original string if there's an error
        print(f"Error formatting date: {e}")
        return timestamp_str

def format_seconds_to_time_ago(seconds):
    """Convert seconds to human-readable time ago format"""
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} {'minute' if minutes == 1 else 'minutes'} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} {'hour' if hours == 1 else 'hours'} ago"
    elif seconds < 604800:  # 7 days
        days = int(seconds / 86400)
        return f"{days} {'day' if days == 1 else 'days'} ago"
    elif seconds < 2592000:  # 30 days
        weeks = int(seconds / 604800)
        return f"{weeks} {'week' if weeks == 1 else 'weeks'} ago"
    elif seconds < 31536000:  # 365 days
        months = int(seconds / 2592000)
        return f"{months} {'month' if months == 1 else 'months'} ago"
    else:
        years = int(seconds / 31536000)
        return f"{years} {'year' if years == 1 else 'years'} ago"

# Content generation and file handling
def create_string(issues, repo_owner, repo_name, output_file):
    """Create content from GitHub issues"""
    string_content = "\n"
    for issue in issues:
        time_ago = format_time_ago(issue['created_at'])
        string_content += f"- {issue['title']} - {time_ago}\n"

    string_content += "\n"
    return string_content

def write_to_file(output_file, string_content):
    """Write content between tags in the output file"""
    with open(output_file, 'r') as f:
        content = f.read()

    start_tag = "<!-- SecOps start -->"
    end_tag = "<!-- SecOps end -->"

    if start_tag not in content or end_tag not in content:
        raise ValueError(f"Error: Tags '{start_tag}' or '{end_tag}' not found in {output_file}.")

    start_index = content.index(start_tag) + len(start_tag)
    end_index = content.index(end_tag)
    new_content = content[:start_index] + "\n" + string_content + "\n" + content[end_index:]

    with open(output_file, 'w') as f:
        f.write(new_content)

# Main program flow
def main():
    # Get environment variables
    token = os.environ.get("GITHUB_TOKEN") or config.GH_TOKEN
    repo_owner = os.environ.get("REPO_OWNER", "SecOpsNews")
    repo_name = os.environ.get("REPO_NAME", "News")
    output_file = os.environ.get("OUTPUT_FILE", "index.md")

    try:
        print(f"Fetching issues for {repo_owner}/{repo_name}...")
        issues = get_github_issues(repo_owner, repo_name, token)
        string_content = create_string(issues, repo_owner, repo_name, output_file)
        write_to_file(output_file, string_content)
        return 0
    except ValueError as e:
        print(f"Error: {str(e)}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    main()
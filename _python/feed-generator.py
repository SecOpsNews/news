import json
import os
import re
import requests
from datetime import datetime, timezone
import config

# Feed labels -> (display name, category). Labels come from the rss_*.yml
# workflows; anything not listed here is shown under its label as "news".
SOURCES = {
    "1Password": ("1Password", "status"),
    "GitHub": ("GitHub", "status"),
    "CloudFlare": ("Cloudflare", "status"),
    "Slack": ("Slack", "status"),
    "Azure": ("Azure", "status"),
    "GCP": ("Google Cloud", "status"),
    "AWS": ("AWS", "status"),
    "CISA": ("CISA", "advisory"),
    "NCSCGuidanceFeed": ("NCSC guidance", "advisory"),
    "NCSCthreats": ("NCSC threat reports", "advisory"),
    "NHSDigital": ("NHS Digital", "advisory"),
    "FullDisclosure": ("Full Disclosure", "advisory"),
    "Bugtraq": ("Bugtraq", "advisory"),
    "MicrosoftSecurityResponseCenter": ("Microsoft MSRC", "advisory"),
    "MicrosoftSecurity": ("Microsoft Security", "advisory"),
    "HIBP": ("Have I Been Pwned", "breach"),
    "DataBreaches": ("DataBreaches.net", "breach"),
    "BrianKrebs": ("Krebs on Security", "blog"),
    "TroyHunt": ("Troy Hunt", "blog"),
    "ScottHelme": ("Scott Helme", "blog"),
    "GrahamCluley": ("Graham Cluley", "blog"),
    "NETRESEC": ("NETRESEC", "blog"),
    "HackerNews": ("The Hacker News", "news"),
    "SecurityWeek": ("SecurityWeek", "news"),
    "BleepingComputer": ("BleepingComputer", "news"),
    "RegisterSec": ("The Register", "news"),
    "RegisterSoftware": ("The Register", "news"),
    "DarkReading": ("Dark Reading", "news"),
    "PoliticCyber": ("Politico", "news"),
    "ITGovernance": ("IT Governance", "news"),
}

# Providers shown in the status strip, in display order.
STATUS_PROVIDERS = ["Cloudflare", "Google Cloud", "AWS", "Azure", "GitHub", "Slack", "1Password"]

# Headline words that mark an item as critical on the dashboard.
CRITICAL = re.compile(r"\b(critical|zero-day|0-day|actively exploited|exploited|ransomware|RCE|CVSS (9|10))\b", re.I)

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

def fetch_stars(repo_owner, repo_name, token, fallback=None):
    """The repository's GitHub star count, or the fallback if the API call fails."""
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token and token != "test":
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.get(f"https://api.github.com/repos/{repo_owner}/{repo_name}", headers=headers, timeout=20)
        response.raise_for_status()
        return response.json().get("stargazers_count", fallback)
    except Exception as e:
        print(f"Warning: couldn't fetch star count: {e}")
        return fallback


def previous_stars(path):
    """The star count from the last run, used if the API call fails."""
    try:
        with open(path) as f:
            return json.load(f).get("stars")
    except (OSError, ValueError):
        return None


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

# Turning issues into items
def parse_issue(issue):
    """Split an rss-issues-action issue into source, title, link and summary."""
    match = re.match(r"\[([^\]]+)\]\s*(.*)", issue["title"])
    label, title = (match.group(1), match.group(2)) if match else ("", issue["title"])
    label = label.replace(" ", "")
    name, category = SOURCES.get(label, (label or "Other", "news"))

    body = issue.get("body") or ""
    links = re.findall(r"<(https?://[^>\s]+)>", body)
    url = links[-1] if links else issue["html_url"]

    text = re.sub(r"<https?://[^>]+>", "", body)
    text = re.sub(r"[*_`#>\\]", "", text)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    # Status pages start each update with a timestamp line; skip those.
    paragraphs = [p for p in paragraphs if not re.fullmatch(r"[A-Z][a-z]{2}\s+\d{1,2}, \d{2}:\d{2} UTC", p)]
    summary = paragraphs[0] if paragraphs else ""
    if len(summary) > 220:
        summary = summary[:217].rsplit(" ", 1)[0] + "…"

    return {
        "source": name,
        "category": category,
        "title": title.strip(),
        "url": url,
        "published": issue["created_at"],
        "summary": summary,
        "critical": bool(CRITICAL.search(title)),
    }


def build_items(issues):
    """Parse, de-duplicate and sort issues, newest first."""
    items, seen = [], set()
    for issue in issues:
        if issue.get("pull_request"):
            continue
        item = parse_issue(issue)
        key = (item["source"], item["title"].lower())
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    items.sort(key=lambda i: i["published"], reverse=True)
    return items


def build_data(items, stars=None, now=None):
    """The dashboard data: items plus the counts and status strip."""
    now = now or datetime.now(timezone.utc)
    day_ago = now.timestamp() - 86400
    recent = [i for i in items if datetime.fromisoformat(i["published"].replace("Z", "+00:00")).timestamp() >= day_ago]
    status_counts = {}
    for i in items:
        if i["category"] == "status":
            status_counts[i["source"]] = status_counts.get(i["source"], 0) + 1
    return {
        "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stars": stars,
        "counts": {
            "last_24h": len(recent),
            "critical": sum(1 for i in items if i["critical"]),
            "advisories": sum(1 for i in items if i["category"] in ("advisory", "breach")),
            "status": sum(status_counts.values()),
        },
        "providers": [{"name": p, "notices": status_counts.get(p, 0)} for p in STATUS_PROVIDERS],
        "items": items,
    }


# Content generation and file handling
def create_string(items):
    """Markdown list for index.md (also used by feed.rss)."""
    string_content = "\n"
    for item in items:
        title = item["title"].replace("[", "(").replace("]", ")")
        string_content += f"- **{item['source']}**: [{title}]({item['url']})\n"
    string_content += "\n"
    return string_content


def write_data(path, data):
    """Write the dashboard data for Jekyll."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

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
    data_file = os.environ.get("DATA_FILE", "_data/news.json")

    try:
        print(f"Fetching issues for {repo_owner}/{repo_name}...")
        issues = get_github_issues(repo_owner, repo_name, token)
        items = build_items(issues)
        stars = fetch_stars(repo_owner, repo_name, token, previous_stars(data_file))
        write_data(data_file, build_data(items, stars))
        write_to_file(output_file, create_string(items))
        return 0
    except ValueError as e:
        print(f"Error: {str(e)}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    main()
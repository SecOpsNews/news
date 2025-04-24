import os
import datetime
import requests
import feedgenerator
import pytz

def get_github_issues(repo_owner, repo_name, token):
    """Fetch open issues from GitHub API"""
    issues = []
    page = 1
    per_page = 100

    while True:
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        params = {
            "state": "open",
            "per_page": per_page,
            "page": page
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        page_issues = response.json()
        if not page_issues:
            break

        issues.extend(page_issues)
        page += 1

        # Check if we've reached the last page
        if len(page_issues) < per_page:
            break

    return issues

def create_rss_feed(issues, repo_owner, repo_name, output_file):
    """Create an RSS feed file from GitHub issues"""
    feed = feedgenerator.Rss201rev2Feed(
        title=f"Open Issues for {repo_owner}/{repo_name}",
        link=f"https://github.com/{repo_owner}/{repo_name}/issues",
        description=f"List of open issues for {repo_owner}/{repo_name}",
        language="en",
    )

    # Current date for the feed
    now = datetime.datetime.now(pytz.utc)

    # Add an entry for today's issues summary
    issue_bullets = "\n".join([
        f"• <a href='{issue['html_url']}'>{issue['title']}</a> "
        f"({', '.join([label['name'] for label in issue['labels']])})"
        for issue in issues
    ])

    feed.add_item(
        title=f"Open Issues Summary - {now.strftime('%Y-%m-%d')}",
        link=f"https://github.com/{repo_owner}/{repo_name}/issues",
        description=f"<ul>{issue_bullets}</ul>",
        pubdate=now,
        unique_id=f"issues-{now.strftime('%Y-%m-%d')}"
    )

    # Write the RSS feed to a file
    with open(output_file, 'w') as fp:
        feed.write(fp, 'utf-8')

def main():
    # Get environment variables
    token = os.environ.get("GITHUB_TOKEN")
    repo_owner = os.environ.get("REPO_OWNER")
    repo_name = os.environ.get("REPO_NAME")
    output_file = os.environ.get("OUTPUT_FILE", "github_issues.xml")

    if not all([token, repo_owner, repo_name]):
        raise ValueError("Missing required environment variables: GITHUB_TOKEN, REPO_OWNER, REPO_NAME")

    print(f"Fetching issues for {repo_owner}/{repo_name}...")
    issues = get_github_issues(repo_owner, repo_name, token)
    print(f"Found {len(issues)} open issues")

    print(f"Creating RSS feed in {output_file}...")
    create_rss_feed(issues, repo_owner, repo_name, output_file)
    print("Done!")

if __name__ == "__main__":
    main()
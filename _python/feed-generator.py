import os
import datetime
import requests
import feedgenerator
import pytz



def get_github_issues(repo_owner, repo_name, token=None):
    """Fetch open issues from GitHub API"""
    issues = []
    page = 1
    per_page = 100
    max_pages = 10  # Limit to avoid excessive API calls

    while page <= max_pages:
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
                break

            issues.extend(page_issues)
            print(f"Retrieved {len(page_issues)} issues from page {page}")

            # Check if we've reached the last page
            if len(page_issues) < per_page:
                break

            page += 1

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise ValueError("GitHub API authentication failed. Please check your token or use a valid token.")
            elif e.response.status_code == 403 and "rate limit exceeded" in str(e.response.text).lower():
                raise ValueError("GitHub API rate limit exceeded. Please wait or use a valid token.")
            elif e.response.status_code == 422:
                # Handle pagination errors gracefully
                print(f"Warning: Pagination issue detected (422 error). Stopping at page {page-1}.")
                break
            else:
                raise ValueError(f"GitHub API error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error fetching issues: {str(e)}")

    print(f"Total issues collected: {len(issues)}")
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

    token = os.environ.get("GITHUB_TOKEN") or GH_TOKEN
    repo_owner = os.environ.get("REPO_OWNER", "SecOpsNews")
    repo_name = os.environ.get("REPO_NAME", "News")
    output_file = os.environ.get("OUTPUT_FILE", "feed.rss")

    try:
        print(f"Fetching issues for {repo_owner}/{repo_name}...")
        issues = get_github_issues(repo_owner, repo_name, token)
        print(f"Found {len(issues)} open issues")

        print(f"Creating RSS feed in {output_file}...")
        create_rss_feed(issues, repo_owner, repo_name, output_file)
        print(f"✅ Done! RSS feed saved to {output_file}")
        return 0
    except ValueError as e:
        print(f"Error: {str(e)}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    main()
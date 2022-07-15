# Reader

A repository to track third party availability and incidents via GitHub Issues.



## Adding a new feed

Add to the relevant action yml file the following code; replacing `SourceName` with the provider as needed, including URL of the RSS/Atom/Json feed + any labels as appropriate

```yaml
SourceName:
    runs-on: ubuntu-latest
    steps:
    - uses: guilhem/rss-issues-action@0.5.2
      continue-on-error: true
      with:
        repo-token: ${{ secrets.GITHUB_TOKEN }}
        feed: "[URL]"
        prefix: "[SourceName]"
        dry-run: "false"
        lastTime: "24h"
        labels: "SourceName, [App, DevOps]" 
```

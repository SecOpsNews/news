# News

A repository to track third party (RSS) feeds from various security sites as GitHub issues. Note this is quite noisy.

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

## All feeds as OPML

Every feed in the `rss_*.yml` workflows is listed in [feeds.opml](https://secops.thechels.uk/feeds.opml), grouped by category, to import into a feed reader. The generator workflow rebuilds it from the workflows, so a new feed is added to it automatically. Run `python _python/opml.py` to rebuild it locally, and `pytest tests` to test it.

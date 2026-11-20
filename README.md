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

## Get it in Slack or Teams

- **Slack:** add Slack's RSS app, then send `/feed subscribe https://secops.thechels.uk/feed.rss` in a channel.
- **Microsoft Teams:** in a channel, open Workflows, choose the template that posts to a channel when an RSS feed is published, and use `https://secops.thechels.uk/feed.rss`.

More ways to follow, including feed readers and OPML, are on [secops.thechels.uk/subscribe](https://secops.thechels.uk/subscribe/).

## All feeds as OPML

Every feed in the `rss_*.yml` workflows is listed in [feeds.opml](https://secops.thechels.uk/feeds.opml), grouped by category, to import into a feed reader. The generator workflow rebuilds it from the workflows, so a new feed is added to it automatically. Run `python _python/opml.py` to rebuild it locally, and `pytest tests` to test it.

## Feed health

The **Feed health** workflow checks every feed in `feeds.opml` each Monday and fails if any is broken (an HTTP error, an HTML page or anything else that isn't a feed). Its run summary lists every feed and its result. Run `python _python/feed_health.py` to check them locally.

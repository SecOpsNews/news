---
layout: page
title: Get SecOpsNews
permalink: /subscribe/
description: "Get the SecOpsNews rundown in Slack, Microsoft Teams or a feed reader, import every source as OPML, or follow each item as a GitHub issue."
---

The rundown is a summary of the dashboard, published each morning and afternoon. Its feed is <https://secops.thechels.uk/feed.rss>, and everything below uses it. There's nothing to install and no account to create with us.

## In Slack

1. Add Slack's **RSS** app to your workspace, if it isn't there already.
2. In the channel you want, send:

   ```text
   /feed subscribe https://secops.thechels.uk/feed.rss
   ```

New rundowns are posted to that channel.

## In Microsoft Teams

1. In the channel you want, open **Workflows**.
2. Choose the template that posts to a channel when an RSS feed is published.
3. Paste `https://secops.thechels.uk/feed.rss` as the feed URL, and save.

## In a feed reader

Add `https://secops.thechels.uk/feed.rss` to any feed reader, such as NetNewsWire, Feedly or Inoreader.

To follow the sources themselves instead, import [all the feeds as OPML](/feeds.opml). That's every source on the dashboard, grouped by category.

## On GitHub

Watch [SecOpsNews/news](https://github.com/SecOpsNews/news) (**Watch** → **All activity**) to get every item as an issue notification. It's noisy.

To watch your own choice of feeds, make a copy of the [feed to issues template](https://github.com/SecOpsNews/template-feed-to-issues).

#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "feedparser",
#     "requests",
#     "tqdm",
#     "beautifulsoup4",
#     "lxml",
# ]
# ///

"""
Generates an HTML feed reader from an OPML file.

Usage:
  python ssrr.py <opml_file> [-o feed.html] [-b blogroll.html]
"""

import logging
import json
import time
from xml.dom.minidom import Document
from concurrent.futures import ThreadPoolExecutor, as_completed

import click
import feedparser
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    filename="output.log",
    level=logging.INFO,
    format="%(message)s",
)


class TqdmUpTo(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def fetch_feed(feed_url):
    """Fetches and parses a single RSS feed."""
    try:
        response = requests.get(feed_url, timeout=10)
        response.raise_for_status()
        log_entry = {
            "timestamp": time.time(),
            "http_code": response.status_code,
            "xml_url": feed_url,
        }
        logging.info(json.dumps(log_entry))
        return feedparser.parse(response.content)
    except requests.RequestException as e:
        log_entry = {
            "timestamp": time.time(),
            "http_code": e.response.status_code if e.response else "N/A",
            "xml_url": feed_url,
            "error": str(e),
        }
        logging.info(json.dumps(log_entry))
        return None


def create_html_doc():
    """Creates a new HTML document with water.css stylesheet."""
    doc = Document()
    html = doc.createElement("html")
    doc.appendChild(html)
    head = doc.createElement("head")
    html.appendChild(head)
    meta = doc.createElement("meta")
    meta.setAttribute("charset", "utf-8")
    head.appendChild(meta)
    title = doc.createElement("title")
    title.appendChild(doc.createTextNode("Feed Reader"))
    head.appendChild(title)
    link = doc.createElement("link")
    link.setAttribute(
        "stylesheet", "https://cdn.jsdelivr.net/npm/water.css@2/out/water.css"
    )
    head.appendChild(link)
    body = doc.createElement("body")
    html.appendChild(body)
    return doc, body


def generate_feed_html(feeds_by_category, output_file):
    """Generates the HTML for the feed reader."""
    doc, body = create_html_doc()
    main_title = doc.createElement("h1")
    main_title.appendChild(doc.createTextNode("Feed Reader"))
    body.appendChild(main_title)

    for category, feeds in feeds_by_category.items():
        category_title = doc.createElement("h2")
        category_title.appendChild(doc.createTextNode(category))
        body.appendChild(category_title)

        for feed_title, feed_url, parsed_feed in feeds:
            if parsed_feed and parsed_feed.entries:
                feed_h3 = doc.createElement("h3")
                feed_h3.appendChild(doc.createTextNode(feed_title))
                body.appendChild(feed_h3)

                ul = doc.createElement("ul")
                body.appendChild(ul)

                for entry in parsed_feed.entries[:3]:
                    if not hasattr(entry, 'link'):
                        continue
                    li = doc.createElement("li")
                    ul.appendChild(li)
                    a = doc.createElement("a")
                    a.setAttribute("href", entry.link)
                    title = getattr(entry, "title", "[No Title]")
                    a.appendChild(doc.createTextNode(title))
                    li.appendChild(a)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(doc.toprettyxml(indent="  "))


def generate_blogroll_html(feeds_by_category, blogroll_file):
    """Generates the HTML for the blogroll."""
    doc, body = create_html_doc()
    main_title = doc.createElement("h1")
    main_title.appendChild(doc.createTextNode("Blogroll"))
    body.appendChild(main_title)

    for category, feeds in feeds_by_category.items():
        category_title = doc.createElement("h2")
        category_title.appendChild(doc.createTextNode(category))
        body.appendChild(category_title)

        ul = doc.createElement("ul")
        body.appendChild(ul)

        for feed_title, feed_url, _ in feeds:
            li = doc.createElement("li")
            ul.appendChild(li)
            a = doc.createElement("a")
            a.setAttribute("href", feed_url)
            a.appendChild(doc.createTextNode(feed_title))
            li.appendChild(a)

    with open(blogroll_file, "w", encoding="utf-8") as f:
        f.write(doc.toprettyxml(indent="  "))


@click.command()
@click.argument("opml_file", type=click.Path(exists=True))
@click.option("-o", "--output", "output_file", default="feed.html", help="Output HTML file for feeds.")
@click.option("-b", "--blogroll", "blogroll_file", help="Output HTML file for the blogroll.")
def main(opml_file, output_file, blogroll_file):
    """
    A server-side RSS reader that takes an OPML file and generates a feed reader as HTML.
    Optionally, it also generates a blogroll as HTML.
    """
    with open(opml_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "xml")

    feeds_by_category = {"Uncategorized": []}
    outlines = soup.find_all("outline", {"xmlUrl": True})

    for outline in outlines:
        category = outline.parent.get("title") or "Uncategorized"
        if category not in feeds_by_category:
            feeds_by_category[category] = []
        feeds_by_category[category].append(
            (outline.get("title"), outline.get("xmlUrl"), None)
        )

    all_feeds = [
        (cat, title, url)
        for cat, feed_list in feeds_by_category.items()
        for title, url, _ in feed_list
    ]

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_feed = {
            executor.submit(fetch_feed, url): (cat, title, url)
            for cat, title, url in all_feeds
        }
        results = {}
        for future in tqdm(
            as_completed(future_to_feed), total=len(all_feeds), desc="Fetching feeds"
        ):
            cat, title, url = future_to_feed[future]
            try:
                parsed_feed = future.result()
                if cat not in results:
                    results[cat] = []
                results[cat].append((title, url, parsed_feed))
            except Exception as exc:
                click.echo(f"Error fetching {url}: {exc}", err=True)

    # Preserve original order
    for category, feeds in feeds_by_category.items():
        if category in results:
            sorted_results = sorted(results[category], key=lambda x: [f[0] for f in feeds].index(x[0]))
            feeds_by_category[category] = sorted_results


    generate_feed_html(feeds_by_category, output_file)
    click.echo(f"Generated feed reader at {output_file}")

    if blogroll_file:
        generate_blogroll_html(feeds_by_category, blogroll_file)
        click.echo(f"Generated blogroll at {blogroll_file}")


if __name__ == "__main__":
    main()

"""
This script implements a server-side RSS reader in Python.

It takes an OPML file as input and generates an HTML feed reader.
The feeds in the HTML output are grouped by category as defined in the OPML file.
Feeds without a category are placed under "Uncategorized".
For each feed, only the top 3 most recent links are included.

The script can also optionally generate a blogroll in HTML format.

The script uses the following libraries:
- click: for command-line interface
- feedparser: for parsing RSS/Atom feeds
- requests: for fetching feed data
- tqdm: for displaying progress bars
- beautifulsoup4: for parsing the OPML file
- xml.dom.minidom: for generating HTML content to avoid raw string manipulation.

Logging is configured to write to 'output.log' in jsonl format,
capturing the timestamp, HTTP status code, and the URL for each feed fetched.

The HTML output is styled using water.css.
"""

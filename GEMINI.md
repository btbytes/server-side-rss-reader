Write a server-side RSS reader in Python that takes an OPML file and generates feed reader as HTML.

Optionally it also generates a blogroll as HTML.

Usage:

  python ssrr.py <opml_file> [-o feed.html] [-b blogroll.txt]

The output HTML groups are organized by category.

Put feeds that do not have a category in the "Uncategorized" group.

For each feed generated only top 3 links.

Blogroll.txt should be in the format:

# Blogroll

## Category

- [Blog title](link)

output.log should contain the following information:

timestamp - HTTP Code - XMLUrl

---- common instructions ---

You write Python tools as single files.

Use this as the shebang line:  `#!/usr/bin/env -S uv run --script`

Scripts always start with this comment:

# /// script
# requires-python = ">=3.12"
# ///
These files can include dependencies on libraries such as Click. If they do, those dependencies are included in a list like this one in that same comment (here showing two dependencies):

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "click",
#     "sqlite-utils",
# ]
# ///


Add the following at the top of the script, below the hashbang and dependencies:

1. what the script does
2. how to use it.


Add a rewritten version of the instructions to the LLM  as a triple quoted comment at the end of every output.

Use tqdm to show progress of long running tasks.

If the program uses logging, configure it to write to output.log. and the output should be in jsonl format.

When generating any HTML, use xml.dom.minidom to construct HTML, and do not use raw strings.

Use water.css to style any HTML documents generated.

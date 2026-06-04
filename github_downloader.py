#!/usr/bin/env python3
"""Download a GitHub subdirectory as a zip file (public repos only)."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import zipfile


def parse_github_url(url):
    """Parse a GitHub URL and return (owner, repo, branch, path).

    Supports:
      https://github.com/owner/repo/tree/branch/path/to/dir
      https://github.com/owner/repo  (downloads repo root, branch = HEAD)
    """
    url = url.rstrip("/")
    prefix = "https://github.com/"
    if not url.startswith(prefix):
        raise ValueError(f"Not a valid GitHub URL: {url}")

    parts = url[len(prefix):].split("/")
    if len(parts) < 2:
        raise ValueError(f"URL must include at least owner and repo: {url}")

    owner = parts[0]
    repo = parts[1]

    if len(parts) > 2 and parts[2] == "tree":
        if len(parts) < 4:
            raise ValueError("URL is missing branch name after /tree/")
        branch = parts[3]
        path = "/".join(parts[4:])
    else:
        branch = "HEAD"
        path = "/".join(parts[2:])

    return owner, repo, branch, path


def fetch_json(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "github-subdir-downloader/1.0"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ValueError(f"Not found (404): {url}") from exc
        if exc.code == 403:
            body = exc.read().decode()
            if "rate limit" in body.lower():
                raise ValueError(
                    "GitHub API rate limit exceeded. "
                    "Wait a few minutes and try again."
                ) from exc
            raise ValueError(f"GitHub API returned 403: {body}") from exc
        raise


def list_files(owner, repo, branch, path, *, _depth=0):
    """Recursively list all file entries under a path via the Contents API."""
    api_url = (
        f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        f"?ref={branch}"
    )
    items = fetch_json(api_url)

    if isinstance(items, dict):
        # Single file returned directly (path pointed to a file, not a dir)
        return [items]

    files = []
    for item in items:
        if item["type"] == "file":
            files.append(item)
        elif item["type"] == "dir":
            files.extend(
                list_files(owner, repo, branch, item["path"], _depth=_depth + 1)
            )
    return files


def build_zip(files, base_path, output_path):
    """Download each file and write it into a zip archive."""
    total = len(files)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, file_info in enumerate(files, 1):
            print(f"  [{idx}/{total}] {file_info['path']}", flush=True)

            req = urllib.request.Request(
                file_info["download_url"],
                headers={"User-Agent": "github-subdir-downloader/1.0"},
            )
            with urllib.request.urlopen(req) as resp:
                content = resp.read()

            # Store with path relative to the requested base
            arc_path = file_info["path"]
            if base_path and arc_path.startswith(base_path):
                arc_path = arc_path[len(base_path):].lstrip("/")

            zf.writestr(arc_path, content)


def main():
    parser = argparse.ArgumentParser(
        description="Download a GitHub subdirectory as a zip file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  %(prog)s https://github.com/owner/repo/tree/main/path/to/subdir
  %(prog)s https://github.com/owner/repo/tree/main/path/to/subdir -o my_output.zip
""",
    )
    parser.add_argument("url", help="GitHub URL of the subdirectory to download")
    parser.add_argument(
        "--output",
        "-o",
        help="Output zip file path (default: <subdir-name>.zip in current directory)",
    )
    args = parser.parse_args()

    try:
        owner, repo, branch, path = parse_github_url(args.url)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Repository : {owner}/{repo}")
    print(f"Branch     : {branch}")
    print(f"Path       : {path or '(root)'}")

    if args.output:
        output_path = args.output
    else:
        dir_name = path.split("/")[-1] if path else repo
        output_path = os.path.join(os.getcwd(), f"{dir_name}.zip")

    print("\nFetching file list from GitHub API...")
    try:
        files = list_files(owner, repo, branch, path)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not files:
        print("No files found at the specified path.")
        sys.exit(1)

    print(f"Found {len(files)} file(s). Downloading into zip...\n")
    try:
        build_zip(files, path, output_path)
    except Exception as exc:
        print(f"Error while building zip: {exc}", file=sys.stderr)
        if os.path.exists(output_path):
            os.remove(output_path)
        sys.exit(1)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"\nDone!  Saved to : {output_path}  ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()

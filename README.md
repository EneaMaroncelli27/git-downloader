# GitHub Subdirectory Downloader

Download a specific folder from a GitHub repository as a zip file, without cloning the whole repo.

## Usage

```
python github_downloader.py <github-url> [-o output.zip]
```

### Examples

```bash
# Download a subfolder
python github_downloader.py https://github.com/owner/repo/tree/main/path/to/folder

# Specify output file name
python github_downloader.py https://github.com/owner/repo/tree/main/src/components -o components.zip

# Download an entire repo
python github_downloader.py https://github.com/owner/repo
```

If you don't specify `-o`, the zip is saved in the current directory named after the folder (e.g. `folder.zip`).

## Requirements

Python 3 — no external dependencies.

## Limitations

- Public repositories only (no authentication)
- Subject to GitHub API rate limits (~60 requests/hour per IP). Large directories with many files may hit this.

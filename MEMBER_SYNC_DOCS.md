# Member Publication Synchronization System

This repository includes an automated system to aggregate research publications from organization members' individual GitHub profiles into the main organization website.

## Overview

The system monitors the GitHub profiles of McPherson Lab members and automatically syncs their research publications from `USERNAME.github.io/publications` to the organization repository at `mcphersonlab.github.io/publications/`.

## Files

- `members.yml` - Configuration file defining active organization members
- `sync_member_posts.py` - Python script that performs the synchronization
- `.github/workflows/sync-member-posts.yml` - GitHub Actions workflow for automation
- `publications/` - Directory containing synced member publications

## How It Works

### Member Configuration

Members are defined in `members.yml` with the following structure:

```yaml
members:
  - username: GitHubUsername
    name: "Full Name"
    role: "Position"
    profile_url: "https://githubusername.github.io"
    publications_path: "/publications"
    active: true
```

### Publication Synchronization

The sync script:

1. Reads the member list from `members.yml`
2. For each active member, checks their GitHub repository at `USERNAME.github.io/publications`
3. Fetches publication directories containing `index.qmd` files and associated images
4. Creates local copies in `publications/` with:
   - Original authorship and metadata preserved
   - Added attribution linking back to the source
   - Prefixed directory name to avoid conflicts (`username-originalname/`)
   - Enhanced frontmatter with source information
   - Associated image files (like `featured.png`, `featured.jpg`) copied alongside

### Automation

The system runs automatically via GitHub Actions:
- **Daily**: Every day at 6 AM UTC
- **On demand**: Can be triggered manually from the GitHub Actions page
- **When updated**: Automatically when `members.yml` is modified

## Manual Usage

You can run the sync script manually:

```bash
# Dry run to see what would be synced
python sync_member_posts.py --dry-run --verbose

# Sync all active members
python sync_member_posts.py --verbose

# Sync a specific member only
python sync_member_posts.py --member JacobKMcPherson --verbose
```

## Adding New Members

To add a new member to the sync system:

1. Ensure they have a GitHub Pages repository at `USERNAME.github.io`
2. Ensure they have a `publications/` directory with publication subdirectories containing `index.qmd` files
3. Add their details to `members.yml`:
   ```yaml
   - username: NewMemberGitHub
     name: "New Member Name"
     role: "Their Role"
     profile_url: "https://newmembergithub.github.io"
     publications_path: "/publications"
     active: true
   ```
4. Commit and push the changes - the sync will run automatically

## Publication Format

Member publications should be organized in directories containing:

- `index.qmd` - The main publication file with YAML frontmatter:

```yaml
---
title: "Publication Title"
author: ["Author Name", "Co-author Name"]
publication: "Journal Name, **Volume**, _Pages_ (Year)"
categories: [research, topic]
image: featured.jpg  # Optional featured image
---

# Publication content here...
```

- `featured.jpg` (or `.png`, `.gif`, `.svg`) - Optional featured image for the publication

## Attribution

All synced publications include automatic attribution to the original author and source, making it clear that the content was originally published on the member's individual site.

## Configuration Options

The `sync_config` section in `members.yml` allows customization:

- `schedule`: When to run automatic sync (cron format)
- `max_posts_per_member`: Maximum publications to sync per member
- `preserve_dates`: Whether to keep original publication dates
- `add_attribution`: Whether to add attribution footers

## Troubleshooting

### Common Issues

1. **Member publications not syncing**: Check that their GitHub Pages repository is public and the publications directory exists
2. **GitHub API limits**: The system uses raw GitHub content fetching as a fallback when API access is limited
3. **Directory conflicts**: Publication directories are prefixed with the member's username to prevent conflicts

### Logs

Check the GitHub Actions workflow logs for detailed information about sync operations. The script provides verbose logging when run with the `--verbose` flag.

### Manual Recovery

If sync fails, you can manually run the script with specific parameters to recover:

```bash
# Re-sync specific member
python sync_member_posts.py --member USERNAME --verbose

# Force a complete re-sync (dry run first)
python sync_member_posts.py --dry-run --verbose
python sync_member_posts.py --verbose
```
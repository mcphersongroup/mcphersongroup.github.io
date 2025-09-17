# Member Post Synchronization System

This repository includes an automated system to aggregate research posts from organization members' individual GitHub profiles into the main organization website.

## Overview

The system monitors the GitHub profiles of McPherson Group members and automatically syncs their research posts from `USERNAME.github.io/research/posts` to the organization repository at `mcphersongroup.github.io/publications`.

## Files

- `members.yml` - Configuration file defining active organization members
- `sync_member_posts.py` - Python script that performs the synchronization
- `.github/workflows/sync-member-posts.yml` - GitHub Actions workflow for automation
- `publications/` - Directory containing synced member posts and publications

## How It Works

### Member Configuration

Members are defined in `members.yml` with the following structure:

```yaml
members:
  - username: GitHubUsername
    name: "Full Name"
    role: "Position"
    profile_url: "https://githubusername.github.io"
    posts_path: "/research/posts"
    active: true
```

### Post Synchronization

The sync script:

1. Reads the member list from `members.yml`
2. For each active member, checks their GitHub repository at `USERNAME.github.io/research/posts`
3. Fetches any `.qmd` (Quarto markdown) files
4. Creates local copies in `publications/` with:
   - Original authorship and metadata preserved
   - Added attribution linking back to the source
   - Prefixed filename to avoid conflicts (`username-originalname.qmd`)
   - Enhanced frontmatter with source information

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
2. Ensure they have a `research/posts/` directory with `.qmd` files
3. Add their details to `members.yml`:
   ```yaml
   - username: NewMemberGitHub
     name: "New Member Name"
     role: "Their Role"
     profile_url: "https://newmembergithub.github.io"
     posts_path: "/research/posts"
     active: true
   ```
4. Commit and push the changes - the sync will run automatically

## Post Format

Member posts should be Quarto markdown files (`.qmd`) with YAML frontmatter:

```yaml
---
title: "Post Title"
author: "Author Name"
date: "2025-01-01"
categories: [research, topic]
---

# Post content here...
```

## Attribution

All synced posts include automatic attribution to the original author and source, making it clear that the content was originally published on the member's individual site.

## Configuration Options

The `sync_config` section in `members.yml` allows customization:

- `schedule`: When to run automatic sync (cron format)
- `max_posts_per_member`: Maximum posts to sync per member
- `preserve_dates`: Whether to keep original publication dates
- `add_attribution`: Whether to add attribution footers

## Troubleshooting

### Common Issues

1. **Member posts not syncing**: Check that their GitHub Pages repository is public and the posts directory exists
2. **GitHub API limits**: The system uses raw GitHub content fetching as a fallback when API access is limited
3. **File conflicts**: Posts are prefixed with the member's username to prevent filename conflicts

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
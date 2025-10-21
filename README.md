# McPherson Lab Website

[![Deploy to GitHub Pages](https://github.com/mcphersonlab/mcphersonlab.github.io/actions/workflows/quarto-publish.yml/badge.svg)](https://github.com/mcphersonlab/mcphersonlab.github.io/actions/workflows/quarto-publish.yml)

This repository contains the source code for the McPherson Lab research website, built with [Quarto](https://quarto.org/) and deployed using GitHub Actions.

## Website Structure

- `index.qmd` - Homepage
- `about.qmd` - About the group
- `research/index.qmd` - Research areas and projects
- `publications/` - Publications 
- `publications/posts/` - Research posts (aggregated from member profiles)
- `people/index.qmd` - Group members and alumni
- `members.yml` - Organization member configuration for post synchronization
- `sync_member_posts.py` - Script for syncing member posts
- `_quarto.yml` - Quarto configuration
- `styles.css` - Custom CSS styling

## Local Development

To work with this website locally:

1. Install [Quarto](https://quarto.org/docs/get-started/)
2. Clone this repository
3. Run `quarto preview` to start a local development server
4. Edit the `.qmd` files to update content
5. Run `quarto render` to build the site

## Deployment

The website is automatically deployed to GitHub Pages using GitHub Actions when changes are pushed to the main branch. The workflow is defined in `.github/workflows/quarto-publish.yml`.

### Member Post Synchronization

The website automatically aggregates research posts from organization members' individual GitHub profiles. This is handled by:

- `.github/workflows/sync-member-posts.yml` - Runs daily to sync new posts
- `sync_member_posts.py` - Python script that performs the synchronization
- `members.yml` - Configuration defining active members

See [MEMBER_SYNC_DOCS.md](MEMBER_SYNC_DOCS.md) for detailed documentation.

## Customization

- Edit `_quarto.yml` to modify site configuration and navigation
- Update content in the `.qmd` files
- Modify `styles.css` for custom styling
- Add new pages by creating additional `.qmd` files and updating the navigation in `_quarto.yml`

## License

MIT License - see [LICENSE](LICENSE) file for details.
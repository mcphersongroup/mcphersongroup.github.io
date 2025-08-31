# McPherson Group Website

[![Deploy to GitHub Pages](https://github.com/mcphersongroup/mcphersongroup.github.io/actions/workflows/quarto-publish.yml/badge.svg)](https://github.com/mcphersongroup/mcphersongroup.github.io/actions/workflows/quarto-publish.yml)

This repository contains the source code for the McPherson Group research website, built with [Quarto](https://quarto.org/) and deployed using GitHub Actions.

## Website Structure

- `index.qmd` - Homepage
- `about.qmd` - About the group
- `research.qmd` - Research areas and projects
- `publications.qmd` - Publications and presentations
- `people.qmd` - Group members and alumni
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

## Customization

- Edit `_quarto.yml` to modify site configuration and navigation
- Update content in the `.qmd` files
- Modify `styles.css` for custom styling
- Add new pages by creating additional `.qmd` files and updating the navigation in `_quarto.yml`

## License

MIT License - see [LICENSE](LICENSE) file for details.
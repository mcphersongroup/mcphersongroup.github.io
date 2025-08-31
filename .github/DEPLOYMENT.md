# Deployment Documentation

## GitHub Actions Workflow

This repository uses GitHub Actions to automatically build and deploy the Quarto website to GitHub Pages.

### Workflow Overview

- **File**: `.github/workflows/quarto-publish.yml`
- **Trigger**: Pushes to `main` branch, Pull Requests to `main`, and manual dispatch
- **Jobs**: 
  - `build`: Renders the Quarto project and uploads artifacts
  - `deploy`: Deploys to GitHub Pages (only on main branch)

### Features

- **Concurrency Control**: Prevents conflicting deployments
- **Environment Protection**: Uses `github-pages` environment for secure deployment
- **Latest Actions**: Uses up-to-date versions of all GitHub Actions
- **Efficient Builds**: Includes TinyTeX caching for faster builds
- **PR Testing**: Builds on PRs to validate changes without deploying

### Manual Deployment

You can manually trigger a deployment by:
1. Going to the Actions tab in GitHub
2. Selecting "Render and Publish" workflow
3. Clicking "Run workflow" button

### Status

The deployment status is shown in the README badge and can be monitored in the Actions tab.
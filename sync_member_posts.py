#!/usr/bin/env python3
"""
Member Publication Synchronization Script

This script fetches research publications from organization members' individual GitHub profiles
and syncs them to the main organization repository.

Usage:
    python sync_member_posts.py [--dry-run] [--member USERNAME]
"""

import os
import sys
import yaml
import requests
import json
import base64
from urllib.parse import urljoin, urlparse
from pathlib import Path
from datetime import datetime
import argparse
import logging
import re
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MemberPostSync:
    def __init__(self, config_path: str = "members.yml", dry_run: bool = False):
        self.config_path = config_path
        self.dry_run = dry_run
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'McPhersonGroup-PostSync/1.0'
        })
        
        # Load configuration
        self.config = self._load_config()
        self.base_publications_dir = Path("publications")
        
    def _load_config(self) -> Dict:
        """Load the members configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded configuration with {len(config.get('members', []))} members")
                return config
        except FileNotFoundError:
            logger.error(f"Configuration file {self.config_path} not found")
            sys.exit(1)
        except yaml.YAMLError as e:
            logger.error(f"Error parsing {self.config_path}: {e}")
            sys.exit(1)
    
    def _get_posts_from_member_site(self, member: Dict) -> List[Dict]:
        """Fetch publications from a member's GitHub profile repository via GitHub API."""
        username = member['username']
        publications_path = member.get('publications_path', '/publications').strip('/')
        
        logger.info(f"Fetching publications for {username} from GitHub API")
        
        posts = []
        try:
            # Use GitHub API to get publications from the member's repository
            repo_name = f"{username}.github.io"
            api_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{publications_path}"
            
            logger.debug(f"API URL: {api_url}")
            response = self._safe_request(api_url)
            
            if response and response.status_code == 200:
                posts = self._parse_posts_from_github_api(response.json(), username, repo_name, publications_path, member)
            elif response:
                logger.warning(f"GitHub API returned status {response.status_code} for {username}/{repo_name}")
                if response.status_code == 404:
                    logger.info(f"Publications directory not found for {username} - this is normal if they don't have publications yet")
                elif response.status_code == 403:
                    logger.warning(f"Access denied to GitHub API. Response: {response.text}")
                    # Try using raw GitHub content instead
                    logger.info("Falling back to raw GitHub content fetch")
                    posts = self._get_posts_via_raw_github(username, publications_path, member)
                else:
                    logger.warning(f"Response: {response.text}")
            else:
                logger.warning(f"Could not fetch posts for {username}")
                # Try fallback even if no response
                logger.info("Trying raw GitHub content fallback")
                posts = self._get_posts_via_raw_github(username, publications_path, member)
                
        except Exception as e:
            logger.error(f"Error fetching publications for {username}: {e}")
            
        logger.info(f"Found {len(posts)} publications for {username}")
        return posts
    
    def _get_posts_via_raw_github(self, username: str, publications_path: str, member: Dict) -> List[Dict]:
        """Alternative method using raw GitHub URLs when API access is limited."""
        publications = []
        
        try:
            repo_name = f"{username}.github.io"
            
            # Try to discover publication directories using known examples
            # For fallback, we'll try known directories that we've seen in the member's repo
            known_directories = ['20250917_test']  # Add more as needed
            
            for dir_name in known_directories:
                try:
                    # Try to fetch index.qmd from this directory
                    index_url = f"https://raw.githubusercontent.com/{username}/{repo_name}/main/{publications_path}/{dir_name}/index.qmd"
                    logger.debug(f"Trying publication URL: {index_url}")
                    
                    response = self._safe_request(index_url)
                    if response and response.status_code == 200:
                        content = response.text
                        
                        # Parse the publication content
                        publication_data = self._parse_qmd_content(content, 'index.qmd', member)
                        if publication_data:
                            publication_data['directory_name'] = dir_name
                            publication_data['source_url'] = f"https://github.com/{username}/{repo_name}/blob/main/{publications_path}/{dir_name}/index.qmd"
                            publication_data['github_path'] = f"{publications_path}/{dir_name}/index.qmd"
                            publication_data['image_files'] = []
                            
                            # Try to find associated image files
                            image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'svg']
                            for ext in image_extensions:
                                img_filename = f"featured.{ext}"
                                img_url = f"https://raw.githubusercontent.com/{username}/{repo_name}/main/{publications_path}/{dir_name}/{img_filename}"
                                
                                # Check if the image exists
                                img_response = self._safe_request(img_url)
                                if img_response and img_response.status_code == 200:
                                    image_info = {
                                        'name': img_filename,
                                        'download_url': img_url,
                                        'github_path': f"{publications_path}/{dir_name}/{img_filename}"
                                    }
                                    publication_data['image_files'].append(image_info)
                                    logger.debug(f"Found image file: {img_filename}")
                                    break  # Only need one featured image
                            
                            publications.append(publication_data)
                            logger.info(f"Successfully fetched publication {dir_name} via raw GitHub")
                    else:
                        logger.debug(f"Could not fetch {dir_name}/index.qmd via raw GitHub (status: {response.status_code if response else 'no response'})")
                        
                except Exception as e:
                    logger.warning(f"Error fetching publication {dir_name} via raw GitHub: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in raw GitHub fallback: {e}")
            
        return publications
    
    def _safe_request(self, url: str) -> Optional[requests.Response]:
        """Make a safe HTTP request with error handling."""
        try:
            response = self.session.get(url, timeout=30)
            return response
        except requests.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
            return None
    
    def _parse_posts_from_github_api(self, api_response: List[Dict], username: str, repo_name: str, publications_path: str, member: Dict) -> List[Dict]:
        """Parse publication directories from GitHub API response."""
        publications = []
        
        logger.info(f"Parsing {len(api_response)} items from {username}'s GitHub repository")
        
        for item in api_response:
            if item['type'] == 'dir' and not item['name'].startswith('_'):
                # This is a publication directory - check if it contains index.qmd
                try:
                    logger.debug(f"Checking publication directory: {item['name']}")
                    subdir_url = item['url']
                    subdir_response = self._safe_request(subdir_url)
                    
                    if subdir_response and subdir_response.status_code == 200:
                        subdir_items = subdir_response.json()
                        
                        # Look for index.qmd in this directory
                        index_qmd = None
                        image_files = []
                        
                        for subitem in subdir_items:
                            if subitem['type'] == 'file':
                                if subitem['name'] == 'index.qmd':
                                    index_qmd = subitem
                                elif subitem['name'].lower().startswith('featured.') and subitem['name'].lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                                    image_files.append(subitem)
                        
                        if index_qmd:
                            # This directory contains a publication - process it
                            publication_data = self._process_publication_directory(
                                item['name'], index_qmd, image_files, username, repo_name, publications_path, member
                            )
                            if publication_data:
                                publications.append(publication_data)
                        else:
                            logger.debug(f"Directory {item['name']} does not contain index.qmd, skipping")
                    else:
                        logger.warning(f"Could not fetch directory contents for {item['name']}")
                        
                except Exception as e:
                    logger.error(f"Error processing directory {item['name']}: {e}")
                    continue
        
        return publications
    
    def _process_publication_directory(self, dir_name: str, index_qmd: Dict, image_files: List[Dict], 
                                     username: str, repo_name: str, publications_path: str, member: Dict) -> Optional[Dict]:
        """Process a publication directory containing index.qmd and associated files."""
        try:
            # Fetch the index.qmd content
            content_response = self._safe_request(index_qmd['url'])
            
            if not content_response or content_response.status_code != 200:
                logger.warning(f"Could not fetch index.qmd for directory {dir_name}")
                return None
                
            content_data = content_response.json()
            content_b64 = content_data.get('content', '')
            content_decoded = base64.b64decode(content_b64).decode('utf-8')
            
            # Parse the publication metadata and content
            publication_data = self._parse_qmd_content(content_decoded, 'index.qmd', member)
            if not publication_data:
                return None
            
            # Add directory-specific information
            publication_data['directory_name'] = dir_name
            publication_data['source_url'] = index_qmd['html_url']
            publication_data['github_path'] = index_qmd['path']
            publication_data['image_files'] = []
            
            # Process associated image files
            for img_file in image_files:
                image_info = {
                    'name': img_file['name'],
                    'download_url': img_file['download_url'],
                    'github_path': img_file['path']
                }
                publication_data['image_files'].append(image_info)
            
            return publication_data
            
        except Exception as e:
            logger.error(f"Error processing publication directory {dir_name}: {e}")
            return None
    
    def _parse_qmd_content(self, content: str, filename: str, member: Dict) -> Optional[Dict]:
        """Parse a Quarto markdown file content."""
        try:
            # Split YAML frontmatter from content
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    yaml_content = parts[1].strip()
                    markdown_content = parts[2].strip()
                    
                    # Parse YAML frontmatter
                    frontmatter = yaml.safe_load(yaml_content)
                    
                    return {
                        'title': frontmatter.get('title', filename.replace('.qmd', '').title()),
                        'author': frontmatter.get('author', member['name']),
                        'date': frontmatter.get('date', datetime.now().isoformat()),
                        'categories': frontmatter.get('categories', []),
                        'content': markdown_content,
                        'filename': filename,
                        'original_frontmatter': frontmatter
                    }
                    
            # If no frontmatter, treat as plain markdown
            return {
                'title': filename.replace('.qmd', '').replace('-', ' ').title(),
                'author': member['name'],
                'date': datetime.now().isoformat(),
                'categories': ['research'],
                'content': content,
                'filename': filename,
                'original_frontmatter': {}
            }
            
        except Exception as e:
            logger.error(f"Error parsing {filename}: {e}")
            return None
    
    def _get_destination_subdir(self, post: Dict, member: Dict) -> str:
        """Determine the destination subdirectory for a post based on member config and post metadata."""
        # Check if member has a custom destination_path
        if 'destination_path' in member:
            return member['destination_path'].strip('/')
        
        # Check if post has a category that maps to a specific subdirectory
        categories = post.get('categories', [])
        sync_config = self.config.get('sync_config', {})
        category_mapping = sync_config.get('category_mapping', {})
        
        for category in categories:
            if category in category_mapping:
                return category_mapping[category].strip('/')
        
        # Check for post type based on frontmatter
        post_type = post.get('original_frontmatter', {}).get('type', 'post')
        type_mapping = sync_config.get('type_mapping', {
            'paper': 'papers',
            'publication': 'papers', 
            'report': 'reports',
            'post': 'posts',
            'blog': 'posts'
        })
        
        if post_type in type_mapping:
            return type_mapping[post_type]
        
        # Default to posts subdirectory for backward compatibility
        return 'posts'
    
    def _create_local_post(self, publication: Dict, member: Dict) -> Tuple[Path, str, List[Tuple[Path, str]]]:
        """Create a local publication directory from fetched publication data."""
        directory_name = publication.get('directory_name', f"publication-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        
        # Create directory path - use the original directory name prefixed with username
        local_dir_name = f"{member['username'].lower()}-{directory_name}"
        destination_dir = self.base_publications_dir / local_dir_name
        
        # Create the index.qmd path
        index_path = destination_dir / 'index.qmd'
        
        # Merge original frontmatter with required fields
        original_fm = publication.get('original_frontmatter', {})
        
        # Create YAML frontmatter for Quarto
        frontmatter = {
            'title': publication.get('title', 'Untitled Publication'),
            'author': publication.get('author', member['name']),
            'date': publication.get('date', datetime.now().isoformat()),
            'categories': publication.get('categories', ['research', 'member-publication'])
        }
        
        # Ensure member-publication category is present
        if 'member-publication' not in frontmatter['categories']:
            frontmatter['categories'].append('member-publication')
        
        # Add source metadata
        frontmatter['source'] = {
            'member': member['name'],
            'username': member['username'],
            'original_url': publication.get('source_url', member['profile_url']),
            'github_path': publication.get('github_path', ''),
            'directory': directory_name
        }
        
        # Preserve additional original frontmatter
        for key, value in original_fm.items():
            if key not in frontmatter and key != 'categories':
                frontmatter[key] = value
                
        # Handle categories merging
        if 'categories' in original_fm:
            original_cats = original_fm['categories'] if isinstance(original_fm['categories'], list) else [original_fm['categories']]
            for cat in original_cats:
                if cat not in frontmatter['categories']:
                    frontmatter['categories'].append(cat)
        
        # Get content
        content = publication.get('content', '')
        
        # Add attribution if configured
        sync_config = self.config.get('sync_config', {})
        if sync_config.get('add_attribution', True):
            attribution = f"\n\n---\n\n*This publication was originally published by [{member['name']}]({member['profile_url']}) and automatically synced to the McPherson Group website.*"
            content += attribution
        
        # Create the full post content
        yaml_header = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
        full_content = f"---\n{yaml_header}---\n\n{content}"
        
        # Prepare image files for download
        image_downloads = []
        for img_info in publication.get('image_files', []):
            img_local_path = destination_dir / img_info['name']
            img_download_url = img_info['download_url']
            image_downloads.append((img_local_path, img_download_url))
        
        return index_path, full_content, image_downloads
    
    def _download_image_file(self, local_path: Path, download_url: str) -> bool:
        """Download an image file from GitHub."""
        try:
            response = self._safe_request(download_url)
            if response and response.status_code == 200:
                # Ensure parent directory exists
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write the image file
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                logger.debug(f"Downloaded image file: {local_path}")
                return True
            else:
                logger.warning(f"Failed to download image from {download_url}")
                return False
        except Exception as e:
            logger.error(f"Error downloading image file {download_url}: {e}")
            return False
    
    def sync_member_posts(self, member_username: Optional[str] = None) -> None:
        """Sync publications for all members or a specific member."""
        members = self.config.get('members', [])
        
        if member_username:
            members = [m for m in members if m['username'] == member_username]
            if not members:
                logger.error(f"Member {member_username} not found in configuration")
                return
        
        # Only sync active members
        active_members = [m for m in members if m.get('active', True)]
        
        logger.info(f"Syncing publications for {len(active_members)} active members")
        
        # Ensure base publications directory exists
        if not self.dry_run:
            self.base_publications_dir.mkdir(parents=True, exist_ok=True)
        
        for member in active_members:
            try:
                self._sync_member_posts(member)
            except Exception as e:
                logger.error(f"Error syncing publications for {member['username']}: {e}")
                continue
    
    def _sync_member_posts(self, member: Dict) -> None:
        """Sync publications for a single member."""
        username = member['username']
        logger.info(f"Syncing publications for {username}")
        
        # Fetch publications from member's site
        publications = self._get_posts_from_member_site(member)
        
        if not publications:
            logger.info(f"No publications found for {username}")
            return
        
        # Limit publications if configured
        max_posts = self.config.get('sync_config', {}).get('max_posts_per_member', 50)
        if len(publications) > max_posts:
            logger.info(f"Limiting to {max_posts} most recent publications for {username}")
            publications = publications[:max_posts]
        
        # Create local publication directories
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        for publication in publications:
            try:
                index_path, content, image_downloads = self._create_local_post(publication, member)
                
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would create/update publication directory: {index_path.parent}")
                    logger.info(f"[DRY RUN] Would create index.qmd: {index_path}")
                    for img_path, img_url in image_downloads:
                        logger.info(f"[DRY RUN] Would download image: {img_path}")
                    logger.debug(f"[DRY RUN] Content preview:\n{content[:200]}...")
                else:
                    # Check if index.qmd already exists
                    if index_path.exists():
                        # Read existing content to compare
                        with open(index_path, 'r', encoding='utf-8') as f:
                            existing_content = f.read()
                        
                        # Simple comparison - you could add more sophisticated comparison
                        if existing_content.strip() == content.strip():
                            logger.debug(f"No changes detected for {index_path}")
                            skipped_count += 1
                            continue
                        else:
                            logger.info(f"Updating existing publication: {index_path.parent}")
                            updated_count += 1
                    else:
                        logger.info(f"Creating new publication: {index_path.parent}")
                        created_count += 1
                    
                    # Ensure destination directory exists
                    index_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write the index.qmd file
                    with open(index_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # Download image files
                    for img_path, img_url in image_downloads:
                        if not self._download_image_file(img_path, img_url):
                            logger.warning(f"Failed to download image: {img_path}")
                        
            except Exception as e:
                logger.error(f"Error processing publication {publication.get('directory_name', 'unknown')}: {e}")
                continue
        
        if not self.dry_run:
            logger.info(f"Sync completed for {username}: {created_count} created, {updated_count} updated, {skipped_count} skipped")

def main():
    parser = argparse.ArgumentParser(description='Sync member publications to organization repository')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without making changes')
    parser.add_argument('--member', type=str, 
                       help='Sync publications for a specific member only')
    parser.add_argument('--config', type=str, default='members.yml',
                       help='Path to members configuration file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize the sync tool
    sync_tool = MemberPostSync(config_path=args.config, dry_run=args.dry_run)
    
    # Run synchronization
    sync_tool.sync_member_posts(member_username=args.member)
    
    if args.dry_run:
        logger.info("Dry run completed. Use --verbose for more details.")
    else:
        logger.info("Publication synchronization completed.")

if __name__ == '__main__':
    main()
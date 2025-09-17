#!/usr/bin/env python3
"""
Member Post Synchronization Script

This script fetches research posts from organization members' individual GitHub profiles
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
        self.posts_dir = Path("publications/posts")
        
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
        """Fetch posts from a member's GitHub profile repository via GitHub API."""
        username = member['username']
        posts_path = member.get('posts_path', '/research/posts').strip('/')
        
        logger.info(f"Fetching posts for {username} from GitHub API")
        
        posts = []
        try:
            # Use GitHub API to get posts from the member's repository
            repo_name = f"{username}.github.io"
            api_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{posts_path}"
            
            logger.debug(f"API URL: {api_url}")
            response = self._safe_request(api_url)
            
            if response and response.status_code == 200:
                posts = self._parse_posts_from_github_api(response.json(), username, repo_name, posts_path, member)
            elif response:
                logger.warning(f"GitHub API returned status {response.status_code} for {username}/{repo_name}")
                if response.status_code == 404:
                    logger.info(f"Posts directory not found for {username} - this is normal if they don't have posts yet")
                elif response.status_code == 403:
                    logger.warning(f"Access denied to GitHub API. Response: {response.text}")
                    # Try using raw GitHub content instead
                    logger.info("Falling back to raw GitHub content fetch")
                    posts = self._get_posts_via_raw_github(username, posts_path, member)
                else:
                    logger.warning(f"Response: {response.text}")
            else:
                logger.warning(f"Could not fetch posts for {username}")
                # Try fallback even if no response
                logger.info("Trying raw GitHub content fallback")
                posts = self._get_posts_via_raw_github(username, posts_path, member)
                
        except Exception as e:
            logger.error(f"Error fetching posts for {username}: {e}")
            
        logger.info(f"Found {len(posts)} posts for {username}")
        return posts
    
    def _get_posts_via_raw_github(self, username: str, posts_path: str, member: Dict) -> List[Dict]:
        """Alternative method using raw GitHub URLs when API access is limited."""
        posts = []
        
        try:
            repo_name = f"{username}.github.io"
            
            # First try to discover posts by checking if we can get the directory listing
            # via the GitHub API, which might work even if individual file access doesn't
            try:
                api_url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{posts_path}"
                response = self._safe_request(api_url)
                if response and response.status_code == 200:
                    # We can get the directory listing via API
                    api_response = response.json()
                    qmd_files = [item['name'] for item in api_response if item['type'] == 'file' and item['name'].endswith('.qmd')]
                    logger.info(f"Discovered {len(qmd_files)} .qmd files via API listing: {qmd_files}")
                else:
                    # Fallback to known files (could be expanded to check common patterns)
                    logger.info("Using fallback file discovery")
                    qmd_files = ['test-post.qmd', 'index.qmd']  # Common post filenames
                    
            except Exception as e:
                logger.warning(f"Error during post discovery: {e}")
                qmd_files = ['test-post.qmd', 'index.qmd']  # Safe fallback
            
            for post_filename in qmd_files:
                try:
                    raw_url = f"https://raw.githubusercontent.com/{username}/{repo_name}/main/{posts_path}/{post_filename}"
                    logger.debug(f"Trying raw URL: {raw_url}")
                    
                    response = self._safe_request(raw_url)
                    if response and response.status_code == 200:
                        content = response.text
                        
                        # Skip files that are not actual posts (like README.md converted to qmd)
                        if post_filename.lower() in ['readme.qmd', 'index.qmd'] and len(content.strip()) < 100:
                            logger.debug(f"Skipping {post_filename} - appears to be a directory index")
                            continue
                            
                        post_data = self._parse_qmd_content(content, post_filename, member)
                        if post_data:
                            post_data['source_url'] = f"https://github.com/{username}/{repo_name}/blob/main/{posts_path}/{post_filename}"
                            post_data['github_path'] = f"{posts_path}/{post_filename}"
                            posts.append(post_data)
                            logger.info(f"Successfully fetched {post_filename} via raw GitHub")
                    else:
                        logger.debug(f"Could not fetch {post_filename} via raw GitHub (status: {response.status_code if response else 'no response'})")
                        
                except Exception as e:
                    logger.warning(f"Error fetching {post_filename} via raw GitHub: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in raw GitHub fallback: {e}")
            
        return posts
    
    def _safe_request(self, url: str) -> Optional[requests.Response]:
        """Make a safe HTTP request with error handling."""
        try:
            response = self.session.get(url, timeout=30)
            return response
        except requests.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
            return None
    
    def _parse_posts_from_github_api(self, api_response: List[Dict], username: str, repo_name: str, posts_path: str, member: Dict) -> List[Dict]:
        """Parse posts from GitHub API response."""
        posts = []
        
        logger.info(f"Parsing {len(api_response)} items from {username}'s GitHub repository")
        
        for item in api_response:
            if item['type'] == 'file' and item['name'].endswith('.qmd'):
                try:
                    # Fetch the actual file content
                    content_url = item['url']
                    content_response = self._safe_request(content_url)
                    
                    if content_response and content_response.status_code == 200:
                        content_data = content_response.json()
                        
                        # Decode the base64 content
                        content_b64 = content_data.get('content', '')
                        content_decoded = base64.b64decode(content_b64).decode('utf-8')
                        
                        # Parse the post metadata and content
                        post_data = self._parse_qmd_content(content_decoded, item['name'], member)
                        if post_data:
                            post_data['source_url'] = item['html_url']
                            post_data['github_path'] = item['path']
                            posts.append(post_data)
                            
                    else:
                        logger.warning(f"Could not fetch content for {item['name']}")
                        
                except Exception as e:
                    logger.error(f"Error processing post {item['name']}: {e}")
                    continue
        
        return posts
    
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
    
    def _create_local_post(self, post: Dict, member: Dict) -> str:
        """Create a local post file from fetched post data."""
        filename = post.get('filename', f"post-{datetime.now().strftime('%Y%m%d%H%M%S')}.qmd")
        
        # Ensure filename has .qmd extension
        if not filename.endswith('.qmd'):
            filename += '.qmd'
            
        # Prefix with member username to avoid conflicts
        local_filename = f"{member['username'].lower()}-{filename}"
        local_path = self.posts_dir / local_filename
        
        # Merge original frontmatter with required fields
        original_fm = post.get('original_frontmatter', {})
        
        # Create YAML frontmatter for Quarto
        frontmatter = {
            'title': post.get('title', 'Untitled Post'),
            'author': post.get('author', member['name']),
            'date': post.get('date', datetime.now().isoformat()),
            'categories': post.get('categories', ['research', 'member-post'])
        }
        
        # Ensure member-post category is present
        if 'member-post' not in frontmatter['categories']:
            frontmatter['categories'].append('member-post')
        
        # Add source metadata
        frontmatter['source'] = {
            'member': member['name'],
            'username': member['username'],
            'original_url': post.get('source_url', member['profile_url']),
            'github_path': post.get('github_path', '')
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
        content = post.get('content', '')
        
        # Add attribution if configured
        sync_config = self.config.get('sync_config', {})
        if sync_config.get('add_attribution', True):
            attribution = f"\n\n---\n\n*This post was originally published by [{member['name']}]({member['profile_url']}) and automatically synced to the McPherson Group website.*"
            content += attribution
        
        # Create the full post content
        yaml_header = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)
        full_content = f"---\n{yaml_header}---\n\n{content}"
        
        return local_path, full_content
    
    def sync_member_posts(self, member_username: Optional[str] = None) -> None:
        """Sync posts for all members or a specific member."""
        members = self.config.get('members', [])
        
        if member_username:
            members = [m for m in members if m['username'] == member_username]
            if not members:
                logger.error(f"Member {member_username} not found in configuration")
                return
        
        # Only sync active members
        active_members = [m for m in members if m.get('active', True)]
        
        logger.info(f"Syncing posts for {len(active_members)} active members")
        
        # Ensure posts directory exists
        if not self.dry_run:
            self.posts_dir.mkdir(parents=True, exist_ok=True)
        
        for member in active_members:
            try:
                self._sync_member_posts(member)
            except Exception as e:
                logger.error(f"Error syncing posts for {member['username']}: {e}")
                continue
    
    def _sync_member_posts(self, member: Dict) -> None:
        """Sync posts for a single member."""
        username = member['username']
        logger.info(f"Syncing posts for {username}")
        
        # Fetch posts from member's site
        posts = self._get_posts_from_member_site(member)
        
        if not posts:
            logger.info(f"No posts found for {username}")
            return
        
        # Limit posts if configured
        max_posts = self.config.get('sync_config', {}).get('max_posts_per_member', 50)
        if len(posts) > max_posts:
            logger.info(f"Limiting to {max_posts} most recent posts for {username}")
            posts = posts[:max_posts]
        
        # Create local post files
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        for post in posts:
            try:
                local_path, content = self._create_local_post(post, member)
                
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would create/update: {local_path}")
                    logger.debug(f"[DRY RUN] Content preview:\n{content[:200]}...")
                else:
                    # Check if file already exists
                    if local_path.exists():
                        # Read existing content to compare
                        with open(local_path, 'r', encoding='utf-8') as f:
                            existing_content = f.read()
                        
                        # Simple comparison - you could add more sophisticated comparison
                        if existing_content.strip() == content.strip():
                            logger.debug(f"No changes detected for {local_path}")
                            skipped_count += 1
                            continue
                        else:
                            logger.info(f"Updating existing post: {local_path}")
                            updated_count += 1
                    else:
                        logger.info(f"Creating new post: {local_path}")
                        created_count += 1
                    
                    # Write the file
                    with open(local_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                        
            except Exception as e:
                logger.error(f"Error processing post {post.get('filename', 'unknown')}: {e}")
                continue
        
        if not self.dry_run:
            logger.info(f"Sync completed for {username}: {created_count} created, {updated_count} updated, {skipped_count} skipped")

def main():
    parser = argparse.ArgumentParser(description='Sync member posts to organization repository')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without making changes')
    parser.add_argument('--member', type=str, 
                       help='Sync posts for a specific member only')
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
        logger.info("Post synchronization completed.")

if __name__ == '__main__':
    main()
"""
Fetcher module for downloading content through proxy.
"""

import logging
import hashlib
from pathlib import Path
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import get_proxy_dict, DOWNLOAD_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentFetcher:
    """Handles fetching content through a proxy."""
    
    def __init__(self):
        self.proxies = get_proxy_dict()
        self.session = self._create_session()
    
    def _create_session(self):
        """Create a requests session with retry logic."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def fetch(self, url, output_filename=None):
        """
        Fetch content from URL through proxy.
        
        Args:
            url: URL to fetch
            output_filename: Optional custom filename for the downloaded file
            
        Returns:
            Path to the downloaded file
        """
        logger.info(f"Fetching content from: {url}")
        
        if self.proxies:
            logger.info(f"Using proxy: {list(self.proxies.values())[0].split('@')[-1]}")
        
        try:
            response = self.session.get(
                url,
                proxies=self.proxies,
                stream=True,
                timeout=300
            )
            response.raise_for_status()
            
            # Generate filename from URL or use provided name
            if not output_filename:
                parsed_url = urlparse(url)
                output_filename = Path(parsed_url.path).name or f"content_{hashlib.md5(url.encode()).hexdigest()[:8]}"
            
            output_path = DOWNLOAD_DIR / output_filename
            
            # Download file in chunks
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Content saved to: {output_path}")
            return output_path
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch content: {e}")
            raise

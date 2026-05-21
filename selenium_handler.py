"""
Selenium handler with optimizations:
- Headless mode support
- Dynamic waits
- Parallel processing capability
- Better error handling
"""
import logging
import time
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import config

logger = logging.getLogger(__name__)


class SeleniumHandler:
    """Handle Selenium operations with optimizations"""
    
    def __init__(self, headless: bool = config.HEADLESS_MODE):
        self.headless = headless
        self.driver = None
        
    def _create_driver(self) -> webdriver.Chrome:
        """Create and configure Chrome WebDriver"""
        options = Options()
        
        if self.headless:
            options.add_argument('--headless=new')
            logger.info("Running in headless mode")
        
        # Performance optimizations
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        
        # Set page load timeout
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(config.PAGE_LOAD_TIMEOUT)
        
        return driver
    
    def start(self) -> None:
        """Initialize the WebDriver"""
        if not self.driver:
            self.driver = self._create_driver()
            logger.info("WebDriver initialized")
    
    def stop(self) -> None:
        """Close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
            finally:
                self.driver = None
    
    def process_link(self, link: str) -> Tuple[str, bool, str]:
        """
        Process a single removal link
        
        Args:
            link: URL to process
            
        Returns:
            Tuple of (link, success, message)
        """
        if not self.driver:
            self.start()
        
        try:
            logger.info(f"Processing: {link}")
            self.driver.get(link)
            
            # Wait for the remove button with dynamic timeout
            wait = WebDriverWait(self.driver, config.ELEMENT_WAIT_TIMEOUT)
            
            try:
                # Look for the Remove button
                remove_button = wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(., 'Remove')]")
                    )
                )
                
                # Click the button
                remove_button.click()
                logger.info(f"✓ Successfully clicked Remove button")
                
                # Brief wait to ensure action completes
                time.sleep(config.POST_CLICK_WAIT)
                
                return (link, True, "Success")
                
            except TimeoutException:
                msg = "Remove button not found (link may be expired or already processed)"
                logger.warning(f"⊘ {msg}")
                return (link, False, msg)
                
        except WebDriverException as e:
            msg = f"WebDriver error: {str(e)[:100]}"
            logger.error(f"✗ {msg}")
            return (link, False, msg)
            
        except Exception as e:
            msg = f"Unexpected error: {str(e)[:100]}"
            logger.error(f"✗ {msg}")
            return (link, False, msg)
    
    def process_links_sequential(self, links: List[str]) -> List[Tuple[str, bool, str]]:
        """
        Process links sequentially
        
        Args:
            links: List of URLs to process
            
        Returns:
            List of (link, success, message) tuples
        """
        results = []
        total = len(links)
        
        logger.info(f"Processing {total} links sequentially")
        
        try:
            self.start()
            
            for idx, link in enumerate(links, 1):
                logger.info(f"[{idx}/{total}] Processing link")
                result = self.process_link(link)
                results.append(result)
                
        finally:
            self.stop()
        
        return results
    
    def _process_link_worker(self, link: str) -> Tuple[str, bool, str]:
        """Worker function for parallel processing"""
        handler = SeleniumHandler(headless=self.headless)
        try:
            handler.start()
            return handler.process_link(link)
        finally:
            handler.stop()
    
    def process_links_parallel(
        self,
        links: List[str],
        max_workers: int = config.MAX_WORKERS
    ) -> List[Tuple[str, bool, str]]:
        """
        Process links in parallel using multiple browser instances
        
        Args:
            links: List of URLs to process
            max_workers: Maximum number of parallel workers
            
        Returns:
            List of (link, success, message) tuples
        """
        results = []
        total = len(links)
        
        logger.info(f"Processing {total} links with {max_workers} parallel workers")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_link = {
                executor.submit(self._process_link_worker, link): link
                for link in links
            }
            
            # Process completed tasks
            completed = 0
            for future in as_completed(future_to_link):
                completed += 1
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Progress: {completed}/{total} completed")
                except Exception as e:
                    link = future_to_link[future]
                    logger.error(f"Worker failed for {link}: {e}")
                    results.append((link, False, f"Worker error: {e}"))
        
        return results
    
    def process_links(self, links: List[str]) -> List[Tuple[str, bool, str]]:
        """
        Process links using configured method (sequential or parallel)
        
        Args:
            links: List of URLs to process
            
        Returns:
            List of (link, success, message) tuples
        """
        if not links:
            logger.warning("No links to process")
            return []
        
        if config.ENABLE_PARALLEL and len(links) > 1:
            return self.process_links_parallel(links, config.MAX_WORKERS)
        else:
            return self.process_links_sequential(links)

# Made with Bob

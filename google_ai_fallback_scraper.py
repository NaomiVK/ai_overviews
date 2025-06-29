import csv
import random
import time
import json
import logging
import os
import re
import requests
from urllib.parse import urljoin, quote_plus
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import threading
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('google_ai_fallback_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GoogleAIFallbackScraper:
    def __init__(self, use_proxy=False, proxy_list=None):
        self.use_proxy = use_proxy
        self.proxy_list = proxy_list or []
        self.current_proxy_index = 0
        self.session_requests = 0
        self.max_requests_per_session = random.randint(10, 20)
        self.ua = UserAgent()
        
        # Initialize session with advanced configuration
        self.session = requests.Session()
        self.setup_session()
        
        # Realistic user agents
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0'
        ]
        
    def setup_session(self):
        """Setup requests session with advanced configuration."""
        # Retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set timeout
        self.session.timeout = 30
        
    def get_realistic_headers(self):
        """Generate highly realistic headers."""
        user_agent = random.choice(self.user_agents)
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': random.choice([
                'en-US,en;q=0.9',
                'en-CA,en;q=0.9,fr;q=0.8',
                'en-GB,en;q=0.9,en-US;q=0.8',
                'en-US,en;q=0.9,es;q=0.8'
            ]),
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        
        # Add referer occasionally
        if random.random() < 0.3:
            headers['Referer'] = random.choice([
                'https://www.google.com/',
                'https://www.google.ca/',
                'https://www.bing.com/',
                'https://duckduckgo.com/'
            ])
        
        return headers
    
    def get_next_proxy(self):
        """Get next proxy from the list."""
        if not self.proxy_list:
            return None
        
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        return proxy
    
    def warm_up_session(self):
        """Warm up the session with realistic requests."""
        logger.info("Warming up session...")
        
        try:
            # Visit Google homepage first
            headers = self.get_realistic_headers()
            
            proxies = None
            if self.use_proxy and self.proxy_list:
                proxy = self.get_next_proxy()
                if proxy:
                    proxies = {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
            
            response = self.session.get('https://www.google.com', headers=headers, proxies=proxies)
            time.sleep(random.uniform(2, 5))
            
            # Visit a few other pages
            warm_up_urls = [
                'https://www.google.com/search?q=weather',
                'https://www.google.com/search?q=news'
            ]
            
            for url in random.sample(warm_up_urls, 1):
                try:
                    headers = self.get_realistic_headers()
                    response = self.session.get(url, headers=headers, proxies=proxies)
                    time.sleep(random.uniform(1, 3))
                except Exception as e:
                    logger.warning(f"Error during warm-up request to {url}: {e}")
            
            logger.info("Session warm-up completed")
            
        except Exception as e:
            logger.error(f"Error during session warm-up: {e}")
    
    def detect_blocking(self, response):
        """Detect if Google is blocking the request."""
        if response.status_code == 429:
            return True, "rate_limit"
        
        if response.status_code in [403, 503]:
            return True, f"http_error_{response.status_code}"
        
        content = response.text.lower()
        blocking_indicators = [
            "captcha", "unusual traffic", "automated queries", "robot",
            "verify you're human", "suspicious activity", "blocked",
            "access denied", "too many requests", "rate limit",
            "security check", "prove you're human", "automated traffic"
        ]
        
        for indicator in blocking_indicators:
            if indicator in content:
                return True, indicator
        
        # Check if we got redirected to a blocking page
        if "sorry.google.com" in response.url:
            return True, "sorry_page_redirect"
        
        return False, None
    
    def search_google(self, search_term, max_retries=3):
        """Search Google using requests and parse for AI overview."""
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Searching Google for: '{search_term}' (Attempt {attempt + 1}/{max_retries})")
                
                # Check if we need to restart session
                self.session_requests += 1
                if self.session_requests >= self.max_requests_per_session:
                    logger.info("Session limit reached, creating new session...")
                    self.session.close()
                    self.session = requests.Session()
                    self.setup_session()
                    self.warm_up_session()
                    self.session_requests = 0
                    self.max_requests_per_session = random.randint(10, 20)
                
                # Prepare search URL
                encoded_term = quote_plus(search_term)
                search_url = f"https://www.google.com/search?q={encoded_term}&hl=en&gl=us"
                
                # Get realistic headers
                headers = self.get_realistic_headers()
                
                # Setup proxy if enabled
                proxies = None
                if self.use_proxy and self.proxy_list:
                    proxy = self.get_next_proxy()
                    if proxy:
                        proxies = {'http': f'http://{proxy}', 'https': f'http://{proxy}'}
                        logger.info(f"Using proxy: {proxy}")
                
                # Add delay before request
                delay = random.uniform(3, 8)
                logger.info(f"Pre-request delay: {delay:.1f} seconds")
                time.sleep(delay)
                
                # Make the search request
                response = self.session.get(
                    search_url, 
                    headers=headers, 
                    proxies=proxies,
                    timeout=30,
                    allow_redirects=True
                )
                
                # Check for blocking
                is_blocked, blocking_type = self.detect_blocking(response)
                if is_blocked:
                    logger.warning(f"Blocking detected: {blocking_type}")
                    
                    if blocking_type == "rate_limit":
                        wait_time = random.uniform(300, 600)  # 5-10 minutes
                        logger.info(f"Rate limit detected. Waiting {wait_time:.1f} seconds...")
                        time.sleep(wait_time)
                        continue
                    else:
                        wait_time = random.uniform(60, 180)  # 1-3 minutes
                        logger.info(f"Waiting {wait_time:.1f} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                
                if response.status_code != 200:
                    logger.warning(f"HTTP {response.status_code} received")
                    continue
                
                # Parse the response
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for AI overview content
                ai_overview_found = self.extract_ai_overview(soup, search_term)
                
                if ai_overview_found:
                    return True, f"AI overview found for '{search_term}'"
                else:
                    return False, f"No AI overview found for '{search_term}'"
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout for '{search_term}' (Attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(30, 60))
                continue
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error for '{search_term}': {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(30, 60))
                continue
                
            except Exception as e:
                logger.error(f"Unexpected error for '{search_term}': {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(30, 60))
                continue
        
        logger.error(f"Failed to search for '{search_term}' after {max_retries} attempts")
        return False, None
    
    def extract_ai_overview(self, soup, search_term):
        """Extract AI overview content from the parsed HTML."""
        
        # AI overview selectors to look for
        ai_selectors = [
            '[data-attrid="wa:/description"]',
            '[data-async-context*="ai_overview"]',
            '.AI-overview',
            '[data-ved*="AI"]',
            '.g-blk',
            '[jsname*="AI"]',
            '.kp-blk',
            '[data-attrid*="description"]',
            '.xpdopen .LGOjhe',
            '.kno-rdesc',
            '.yp',
            '[data-md="50"]',
            '.ULSxyf',
            '.hgKElc',
            '.kno-fb-ctx',
            '.Z0LcW',
            '.IZ6rdc',
            '.ayRjaf',
            '.g-section-with-header',
            '.knowledge-panel',
            '.kp-wholepage'
        ]
        
        ai_overview_content = None
        
        for selector in ai_selectors:
            elements = soup.select(selector)
            if elements:
                ai_overview_content = elements[0]
                logger.info(f"AI overview found using selector: {selector}")
                break
        
        if ai_overview_content:
            # Extract text content
            text_content = ai_overview_content.get_text(strip=True)
            
            # Save the content to a file
            safe_filename = sanitize_filename(search_term)
            content_file = f"ai_content/{safe_filename}_ai_content.txt"
            
            try:
                os.makedirs("ai_content", exist_ok=True)
                with open(content_file, 'w', encoding='utf-8') as f:
                    f.write(f"Search Term: {search_term}\n")
                    f.write(f"AI Overview Content:\n")
                    f.write(text_content)
                    f.write(f"\n\nHTML:\n")
                    f.write(str(ai_overview_content))
                
                logger.info(f"AI overview content saved to: {content_file}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to save AI overview content: {e}")
                return True  # Still found content, just couldn't save
        
        return False

def sanitize_filename(filename):
    """Removes or replaces characters invalid for filenames."""
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    sanitized = sanitized.replace(' ', '_')
    max_len = 200
    if len(sanitized) > max_len:
        sanitized = sanitized[:max_len]
    return sanitized

def read_search_terms_from_csv(file_path):
    """Reads search terms from the first column of a CSV file."""
    search_terms = []
    try:
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row:
                    search_terms.append(row[0])
        return search_terms
    except FileNotFoundError:
        logger.error(f"CSV file not found at {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        return []

def main():
    # Configuration
    csv_file_path = 'search_terms.csv'
    results_csv_path = 'google_ai_fallback_results.csv'
    min_delay = 20   # Longer delays for requests-based approach
    max_delay = 60
    
    # Proxy configuration (optional)
    use_proxy = False  # Set to True to enable proxy rotation
    proxy_list = [
        # Add your proxy list here in format: "ip:port" or "username:password@ip:port"
        # "proxy1.example.com:8080",
        # "proxy2.example.com:8080"
    ]
    
    # Initialize fallback scraper
    scraper = GoogleAIFallbackScraper(use_proxy=use_proxy, proxy_list=proxy_list)
    
    try:
        # Warm up session
        scraper.warm_up_session()
        
        # Read search terms
        search_terms = read_search_terms_from_csv(csv_file_path)
        if not search_terms:
            logger.error("No search terms found. Exiting.")
            return
        
        results = []
        
        for i, term in enumerate(search_terms):
            if not term.strip():
                logger.info("Skipping empty search term.")
                continue
            
            logger.info(f"Processing term {i+1}/{len(search_terms)}: {term}")
            
            # Search with fallback method
            has_ai_overview, result_info = scraper.search_google(term)
            
            # Store results
            results.append({
                "search_term": term,
                "has_ai_overview": has_ai_overview,
                "result_info": result_info
            })
            
            # Extended delay between searches
            delay = random.uniform(min_delay, max_delay)
            logger.info(f"Waiting {delay:.2f} seconds before next search...")
            time.sleep(delay)
            
            # Extended breaks every few searches
            if (i + 1) % 3 == 0:  # More frequent breaks for requests method
                long_break = random.uniform(180, 420)  # 3-7 minutes
                logger.info(f"Taking extended break: {long_break:.1f} seconds...")
                time.sleep(long_break)
    
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Cleanup
        try:
            scraper.session.close()
            logger.info("Session closed.")
        except:
            pass
    
    # Save results
    logger.info("\n--- Fallback Search Analysis Complete ---")
    if results:
        found_count = sum(1 for r in results if r['has_ai_overview'])
        logger.info(f"Total terms searched: {len(results)}")
        logger.info(f"AI overviews found: {found_count}")
        logger.info(f"AI overviews not found: {len(results) - found_count}")
        
        try:
            with open(results_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['search_term', 'has_ai_overview', 'result_info']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for result in results:
                    writer.writerow(result)
            logger.info(f"Results saved to {results_csv_path}")
        except Exception as e:
            logger.error(f"Error writing results to CSV: {e}")
    else:
        logger.info("No results to save.")

if __name__ == "__main__":
    main()
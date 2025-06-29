import csv
import random
import time
import json
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.service import Service
import os
import re
import requests
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('google_ai_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GoogleAIScraper:
    def __init__(self, use_proxy=False, proxy_list=None):
        self.use_proxy = use_proxy
        self.proxy_list = proxy_list or []
        self.current_proxy_index = 0
        self.session_requests = 0
        self.max_requests_per_session = random.randint(15, 25)
        
        # Realistic user agents pool
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
        
        # Realistic screen resolutions
        self.screen_resolutions = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
            (1280, 720), (1600, 900), (1024, 768), (1280, 1024)
        ]
        
        self.driver = None
        
    def get_random_headers(self):
        """Generate randomized headers to avoid detection."""
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': random.choice([
                'en-US,en;q=0.9',
                'en-CA,en;q=0.9,fr;q=0.8',
                'en-GB,en;q=0.9'
            ]),
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
    
    def setup_driver(self):
        """Setup Chrome driver with advanced anti-detection measures."""
        try:
            options = webdriver.ChromeOptions()
            
            # Basic stealth options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Random user agent
            user_agent = random.choice(self.user_agents)
            options.add_argument(f'--user-agent={user_agent}')
            logger.info(f"Using User Agent: {user_agent}")
            
            # Random window size
            width, height = random.choice(self.screen_resolutions)
            options.add_argument(f'--window-size={width},{height}')
            logger.info(f"Window size: {width}x{height}")
            
            # Additional anti-detection arguments
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')  # Faster loading
            options.add_argument('--disable-javascript')  # Can be removed if JS is needed
            options.add_argument('--disable-gpu')
            options.add_argument('--no-first-run')
            options.add_argument('--no-default-browser-check')
            options.add_argument('--disable-default-apps')
            options.add_argument('--disable-popup-blocking')
            options.add_argument('--disable-translate')
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-client-side-phishing-detection')
            options.add_argument('--disable-sync')
            options.add_argument('--disable-features=TranslateUI')
            options.add_argument('--disable-ipc-flooding-protection')
            
            # Proxy setup if enabled
            if self.use_proxy and self.proxy_list:
                proxy = self.get_next_proxy()
                if proxy:
                    options.add_argument(f'--proxy-server={proxy}')
                    logger.info(f"Using proxy: {proxy}")
            
            # Additional preferences to avoid detection
            prefs = {
                "profile.default_content_setting_values": {
                    "notifications": 2,
                    "geolocation": 2,
                    "media_stream": 2,
                },
                "profile.managed_default_content_settings": {
                    "images": 2
                },
                "profile.default_content_settings": {
                    "popups": 0
                }
            }
            options.add_experimental_option("prefs", prefs)
            
            # Initialize driver
            self.driver = webdriver.Chrome(options=options)
            
            # Execute stealth scripts
            self.execute_stealth_scripts()
            
            # Set random viewport
            self.driver.set_window_size(width, height)
            
            logger.info("Chrome driver initialized successfully with stealth configuration")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup driver: {e}")
            return False
    
    def execute_stealth_scripts(self):
        """Execute JavaScript to further hide automation indicators."""
        stealth_scripts = [
            # Remove webdriver property
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
            
            # Override plugins
            """
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            """,
            
            # Override languages
            """
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            """,
            
            # Override permissions
            """
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
            );
            """,
            
            # Override chrome runtime
            """
            if (window.chrome) {
                Object.defineProperty(window.chrome, 'runtime', {
                    get: () => undefined
                });
            }
            """
        ]
        
        for script in stealth_scripts:
            try:
                self.driver.execute_script(script)
            except Exception as e:
                logger.warning(f"Failed to execute stealth script: {e}")
    
    def get_next_proxy(self):
        """Get next proxy from the list."""
        if not self.proxy_list:
            return None
        
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        return proxy
    
    def human_like_typing(self, element, text):
        """Type text with human-like delays and patterns."""
        element.clear()
        
        for char in text:
            element.send_keys(char)
            # Random typing delay between 50-200ms
            time.sleep(random.uniform(0.05, 0.2))
            
            # Occasional longer pauses (thinking)
            if random.random() < 0.1:
                time.sleep(random.uniform(0.5, 1.5))
    
    def random_mouse_movement(self):
        """Perform random mouse movements to simulate human behavior."""
        try:
            actions = ActionChains(self.driver)
            
            # Get window size
            window_size = self.driver.get_window_size()
            max_x = window_size['width']
            max_y = window_size['height']
            
            # Perform 2-5 random movements
            movements = random.randint(2, 5)
            
            for _ in range(movements):
                x = random.randint(0, max_x - 1)
                y = random.randint(0, max_y - 1)
                
                actions.move_by_offset(x - max_x//2, y - max_y//2)
                actions.perform()
                
                time.sleep(random.uniform(0.1, 0.5))
                
                # Reset to center
                actions = ActionChains(self.driver)
                
        except Exception as e:
            logger.warning(f"Random mouse movement failed: {e}")
    
    def detect_captcha_or_blocking(self):
        """Detect if Google is showing CAPTCHA or blocking access."""
        blocking_indicators = [
            "captcha",
            "unusual traffic",
            "automated queries",
            "robot",
            "verify you're human",
            "suspicious activity",
            "blocked",
            "access denied"
        ]
        
        try:
            page_source = self.driver.page_source.lower()
            page_title = self.driver.title.lower()
            
            for indicator in blocking_indicators:
                if indicator in page_source or indicator in page_title:
                    logger.warning(f"Blocking detected: {indicator}")
                    return True, indicator
                    
            # Check for specific CAPTCHA elements
            captcha_selectors = [
                "#captcha",
                ".captcha",
                "[id*='captcha']",
                "[class*='captcha']",
                ".g-recaptcha",
                "#recaptcha"
            ]
            
            for selector in captcha_selectors:
                try:
                    if self.driver.find_element(By.CSS_SELECTOR, selector):
                        logger.warning(f"CAPTCHA element found: {selector}")
                        return True, "captcha_element"
                except NoSuchElementException:
                    continue
                    
            return False, None
            
        except Exception as e:
            logger.error(f"Error detecting blocking: {e}")
            return False, None
    
    def handle_blocking(self, blocking_type):
        """Handle different types of blocking."""
        logger.warning(f"Handling blocking type: {blocking_type}")
        
        if "captcha" in blocking_type.lower():
            logger.info("CAPTCHA detected. Waiting for manual resolution...")
            input("Please solve the CAPTCHA manually and press Enter to continue...")
            return True
        
        # For other types of blocking, wait and retry
        wait_time = random.uniform(60, 180)  # Wait 1-3 minutes
        logger.info(f"Waiting {wait_time:.1f} seconds before retry...")
        time.sleep(wait_time)
        
        return False
    
    def exponential_backoff_delay(self, attempt):
        """Calculate delay using exponential backoff."""
        base_delay = 2
        max_delay = 300  # 5 minutes max
        delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
        return delay

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

def analyze_google_search(scraper, search_term, max_retries=3):
    """Searches Google.ca for a term and screenshots the AI overview if found."""
    wait_time_for_ai_overview = 15  # Define at function level to fix UnboundLocalError
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Searching Google.ca for: '{search_term}' (Attempt {attempt + 1}/{max_retries})")
            
            # Check if we need to restart session
            scraper.session_requests += 1
            if scraper.session_requests >= scraper.max_requests_per_session:
                logger.info("Session limit reached, restarting browser...")
                scraper.driver.quit()
                time.sleep(random.uniform(30, 60))
                if not scraper.setup_driver():
                    return False, None
                scraper.session_requests = 0
                scraper.max_requests_per_session = random.randint(15, 25)
            
            # Navigate to Google with random delay
            time.sleep(random.uniform(2, 5))
            scraper.driver.get("https://www.google.ca")
            
            # Check for blocking immediately after loading
            is_blocked, blocking_type = scraper.detect_captcha_or_blocking()
            if is_blocked:
                if scraper.handle_blocking(blocking_type):
                    continue  # Retry after handling
                else:
                    # If can't handle, wait and retry
                    delay = scraper.exponential_backoff_delay(attempt)
                    logger.info(f"Waiting {delay:.1f} seconds before retry...")
                    time.sleep(delay)
                    continue
            
            # Random mouse movement
            scraper.random_mouse_movement()
            
            # Handle cookie consent
            try:
                cookie_selectors = [
                    "//button[contains(text(), 'Accept')]",
                    "//button[contains(text(), 'I agree')]",
                    "//button[contains(text(), 'OK')]",
                    "//button[contains(text(), 'Accept all')]",
                    "#L2AGLb",  # Google's "I agree" button ID
                    ".QS5gu"   # Another Google consent button class
                ]
                
                for selector in cookie_selectors:
                    try:
                        if selector.startswith("//"):
                            cookie_button = WebDriverWait(scraper.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                        else:
                            cookie_button = WebDriverWait(scraper.driver, 3).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                        cookie_button.click()
                        logger.info("Accepted cookies")
                        time.sleep(random.uniform(1, 3))
                        break
                    except TimeoutException:
                        continue
                        
            except Exception as e:
                logger.info("No cookie consent dialog found or already accepted")
            
            # Find search box with multiple selectors
            search_box_selectors = ["input[name='q']", "textarea[name='q']", "#APjFqb"]
            search_box = None
            
            for selector in search_box_selectors:
                try:
                    search_box = WebDriverWait(scraper.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if not search_box:
                raise TimeoutException("Could not find search box")
            
            # Human-like typing
            scraper.human_like_typing(search_box, search_term)
            
            # Random delay before pressing enter
            time.sleep(random.uniform(0.5, 2))
            search_box.send_keys(Keys.RETURN)
            
            # Wait for search results with longer timeout
            try:
                WebDriverWait(scraper.driver, 15).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.ID, "search")),
                        EC.presence_of_element_located((By.ID, "rso")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-ved]"))
                    )
                )
            except TimeoutException:
                logger.warning("Search results took too long to load")
                continue
            
            # Check for blocking after search
            is_blocked, blocking_type = scraper.detect_captcha_or_blocking()
            if is_blocked:
                if scraper.handle_blocking(blocking_type):
                    continue
                else:
                    delay = scraper.exponential_backoff_delay(attempt)
                    time.sleep(delay)
                    continue
            
            # Wait for AI overview with extended selectors
            logger.info(f"Waiting up to {wait_time_for_ai_overview} seconds for AI overview...")
            
            ai_overview_element = None
            ai_overview_selectors = [
                # Updated selectors for current Google AI overview
                "[data-attrid='wa:/description']",
                "[data-async-context*='ai_overview']",
                ".AI-overview",
                "[data-ved*='AI']",
                ".g-blk",
                "[jsname*='AI']",
                ".kp-blk",
                "[data-attrid*='description']",
                ".xpdopen .LGOjhe",
                ".kno-rdesc",
                ".yp",  # AI overview container
                "[data-md='50']",  # AI overview data attribute
                ".ULSxyf",  # AI overview content
                ".hgKElc",  # AI overview text
                ".kno-fb-ctx",  # Knowledge panel context
                ".Z0LcW",  # Featured snippet
                ".IZ6rdc",  # Rich snippet
                ".ayRjaf"   # AI overview wrapper
            ]
            
            # Try multiple selectors with shorter individual timeouts
            for selector in ai_overview_selectors:
                try:
                    ai_overview_element = WebDriverWait(scraper.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"AI overview found using selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            # If no AI overview found, look for featured snippets
            if not ai_overview_element:
                featured_snippet_selectors = [
                    ".kp-blk",
                    ".g .s",
                    "[data-attrid='wa:/description']",
                    ".xpdopen",
                    ".kno-rdesc",
                    ".LGOjhe",
                    ".Z0LcW",
                    ".IZ6rdc",
                    ".hgKElc"
                ]
                
                for selector in featured_snippet_selectors:
                    try:
                        ai_overview_element = WebDriverWait(scraper.driver, 2).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        logger.info(f"Featured content found using selector: {selector}")
                        break
                    except TimeoutException:
                        continue
            
            if ai_overview_element:
                # Ensure element is visible
                time.sleep(random.uniform(2, 4))
                
                # Scroll to element
                scraper.driver.execute_script("arguments[0].scrollIntoView(true);", ai_overview_element)
                time.sleep(random.uniform(1, 2))
                
                # Take screenshot
                safe_filename_term = sanitize_filename(search_term)
                screenshot_path = f"screenshots_google_ai/{safe_filename_term}_ai_overview.png"
                
                try:
                    ai_overview_element.screenshot(screenshot_path)
                    logger.info(f"Screenshot saved to: {screenshot_path}")
                    return True, screenshot_path
                except Exception as e:
                    logger.error(f"Failed to take screenshot: {e}")
                    return False, None
            else:
                logger.info(f"No AI overview or featured content found for '{search_term}' within {wait_time_for_ai_overview} seconds.")
                return False, None
                
        except TimeoutException:
            logger.warning(f"Timeout occurred for '{search_term}' within {wait_time_for_ai_overview} seconds (Attempt {attempt + 1})")
            if attempt < max_retries - 1:
                delay = scraper.exponential_backoff_delay(attempt)
                logger.info(f"Waiting {delay:.1f} seconds before retry...")
                time.sleep(delay)
            continue
            
        except Exception as e:
            logger.error(f"Error occurred while searching for '{search_term}': {e}")
            if attempt < max_retries - 1:
                delay = scraper.exponential_backoff_delay(attempt)
                time.sleep(delay)
            continue
    
    logger.error(f"Failed to search for '{search_term}' after {max_retries} attempts")
    return False, None

def main():
    # Configuration
    csv_file_path = 'search_terms.csv'
    screenshots_dir = "screenshots_google_ai"
    results_csv_path = 'google_ai_overview_results.csv'
    min_delay = 8   # Increased delays
    max_delay = 20
    
    # Proxy configuration (optional)
    use_proxy = False  # Set to True to enable proxy rotation
    proxy_list = [
        # Add your proxy list here in format: "ip:port" or "username:password@ip:port"
        # "proxy1.example.com:8080",
        # "proxy2.example.com:8080"
    ]
    
    # Initialize scraper
    scraper = GoogleAIScraper(use_proxy=use_proxy, proxy_list=proxy_list)
    
    try:
        # Setup driver
        if not scraper.setup_driver():
            logger.error("Failed to setup driver. Exiting.")
            return
        
        # Read search terms
        search_terms = read_search_terms_from_csv(csv_file_path)
        if not search_terms:
            logger.error("No search terms found. Exiting.")
            return
        
        # Create screenshots directory
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
            logger.info(f"Created directory: {screenshots_dir}")
        
        results = []
        
        for i, term in enumerate(search_terms):
            if not term.strip():
                logger.info("Skipping empty search term.")
                continue
            
            logger.info(f"Processing term {i+1}/{len(search_terms)}: {term}")
            
            # Search with retry logic
            has_ai_overview, screenshot = analyze_google_search(scraper, term)
            
            # Store results
            results.append({
                "search_term": term,
                "has_ai_overview": has_ai_overview,
                "screenshot_path": screenshot
            })
            
            # Longer random delay between searches
            delay = random.uniform(min_delay, max_delay)
            logger.info(f"Waiting {delay:.2f} seconds before next search...")
            time.sleep(delay)
            
            # Occasional longer breaks
            if (i + 1) % 10 == 0:
                long_break = random.uniform(60, 180)
                logger.info(f"Taking a longer break: {long_break:.1f} seconds...")
                time.sleep(long_break)
    
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Cleanup
        if scraper.driver:
            scraper.driver.quit()
            logger.info("Browser closed.")
    
    # Save results
    logger.info("\n--- Search Analysis Complete ---")
    if results:
        found_count = sum(1 for r in results if r['has_ai_overview'])
        logger.info(f"Total terms searched: {len(results)}")
        logger.info(f"AI overviews found: {found_count}")
        logger.info(f"AI overviews not found: {len(results) - found_count}")
        
        try:
            with open(results_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['search_term', 'has_ai_overview', 'screenshot_path']
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
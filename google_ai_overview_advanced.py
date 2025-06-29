import csv
import random
import time
import json
import logging
import os
import re
import requests
from urllib.parse import urljoin
import undetected_chromedriver as uc
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.service import Service
from selenium_stealth import stealth
import threading
import subprocess
import platform

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('google_ai_scraper_advanced.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AdvancedGoogleAIScraper:
    def __init__(self, use_proxy=False, proxy_list=None, use_mobile=False):
        self.use_proxy = use_proxy
        self.proxy_list = proxy_list or []
        self.current_proxy_index = 0
        self.session_requests = 0
        self.max_requests_per_session = random.randint(8, 15)  # Reduced session length
        self.use_mobile = use_mobile
        self.ua = UserAgent()
        
        # Enhanced mobile user agents
        self.mobile_user_agents = [
            'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Mozilla/5.0 (Android 14; Mobile; rv:109.0) Gecko/111.0 Firefox/119.0',
            'Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36'
        ]
        
        # Enhanced desktop user agents with latest versions
        self.desktop_user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0'
        ]
        
        # Realistic screen resolutions
        self.desktop_resolutions = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
            (1280, 720), (1600, 900), (1024, 768), (1280, 1024),
            (2560, 1440), (1920, 1200)
        ]
        
        self.mobile_resolutions = [
            (375, 667), (414, 896), (390, 844), (428, 926),
            (360, 640), (412, 915), (393, 851)
        ]
        
        self.driver = None
        self.session_cookies = []
        
    def get_realistic_headers(self):
        """Generate highly realistic headers."""
        if self.use_mobile:
            user_agent = random.choice(self.mobile_user_agents)
        else:
            user_agent = random.choice(self.desktop_user_agents)
            
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
            'sec-ch-ua-mobile': '?1' if self.use_mobile else '?0',
            'sec-ch-ua-platform': '"Android"' if self.use_mobile else '"Windows"'
        }
        
        return headers
    
    def setup_undetected_driver(self):
        """Setup undetected Chrome driver with advanced anti-detection."""
        try:
            # Advanced Chrome options for maximum stealth
            options = uc.ChromeOptions()
            
            # Essential stealth options
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-extensions')
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
            options.add_argument('--disable-features=TranslateUI,BlinkGenPropertyTrees')
            options.add_argument('--disable-ipc-flooding-protection')
            options.add_argument('--disable-hang-monitor')
            options.add_argument('--disable-prompt-on-repost')
            options.add_argument('--disable-domain-reliability')
            options.add_argument('--disable-component-extensions-with-background-pages')
            options.add_argument('--disable-background-networking')
            
            # Memory and performance optimizations
            options.add_argument('--memory-pressure-off')
            options.add_argument('--max_old_space_size=4096')
            
            # Additional anti-detection measures
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument('--disable-features=VizDisplayCompositor')
            
            # Random window size
            if self.use_mobile:
                width, height = random.choice(self.mobile_resolutions)
                options.add_argument(f'--window-size={width},{height}')
                options.add_argument('--user-agent=' + random.choice(self.mobile_user_agents))
            else:
                width, height = random.choice(self.desktop_resolutions)
                options.add_argument(f'--window-size={width},{height}')
                options.add_argument('--user-agent=' + random.choice(self.desktop_user_agents))
            
            logger.info(f"Window size: {width}x{height}, Mobile: {self.use_mobile}")
            
            # Proxy setup
            if self.use_proxy and self.proxy_list:
                proxy = self.get_next_proxy()
                if proxy:
                    options.add_argument(f'--proxy-server={proxy}')
                    logger.info(f"Using proxy: {proxy}")
            
            # Advanced preferences
            prefs = {
                "profile.default_content_setting_values": {
                    "notifications": 2,
                    "geolocation": 2,
                    "media_stream": 2,
                },
                "profile.managed_default_content_settings": {
                    "images": 1  # Allow images for more realistic behavior
                },
                "profile.default_content_settings": {
                    "popups": 0
                },
                "profile.password_manager_enabled": False,
                "credentials_enable_service": False,
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_setting_values.geolocation": 2
            }
            options.add_experimental_option("prefs", prefs)
            
            # Add arguments instead of experimental options for better compatibility
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-logging')
            options.add_argument('--log-level=3')
            options.add_argument('--disable-extensions')
            
            # Initialize undetected Chrome driver
            self.driver = uc.Chrome(
                options=options,
                version_main=None,  # Auto-detect Chrome version
                driver_executable_path=None,  # Auto-download if needed
                browser_executable_path=None,  # Use system Chrome
                user_data_dir=None,  # Use temporary profile
                headless=False,  # Keep visible for now
                use_subprocess=True,
                debug=False
            )
            
            # Apply selenium-stealth for additional protection
            stealth(self.driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32" if not self.use_mobile else "Linux armv81",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
            )
            
            # Execute advanced stealth scripts
            self.execute_advanced_stealth_scripts()
            
            # Set realistic viewport
            self.driver.set_window_size(width, height)
            
            logger.info("Undetected Chrome driver initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup undetected driver: {e}")
            return False
    
    def execute_advanced_stealth_scripts(self):
        """Execute comprehensive JavaScript stealth scripts."""
        stealth_scripts = [
            # Remove webdriver traces
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """,
            
            # Override plugins with realistic data
            """
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    return [
                        {
                            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: Plugin},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        },
                        {
                            0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format", enabledPlugin: Plugin},
                            description: "Portable Document Format", 
                            filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                            length: 1,
                            name: "Chrome PDF Viewer"
                        }
                    ];
                }
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
            if (window.chrome && window.chrome.runtime) {
                Object.defineProperty(window.chrome.runtime, 'onConnect', {
                    value: undefined,
                    enumerable: false,
                    writable: false,
                    configurable: false
                });
            }
            """,
            
            # Override automation indicators
            """
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """,
            
            # Override screen properties
            """
            Object.defineProperty(screen, 'availTop', {get: () => 0});
            Object.defineProperty(screen, 'availLeft', {get: () => 0});
            """,
            
            # Override connection properties
            """
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    downlink: 10,
                    effectiveType: '4g',
                    rtt: 50,
                    saveData: false
                })
            });
            """,
            
            # Override hardware concurrency
            """
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 4
            });
            """,
            
            # Override device memory
            """
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8
            });
            """
        ]
        
        for script in stealth_scripts:
            try:
                self.driver.execute_script(script)
            except Exception as e:
                logger.warning(f"Failed to execute stealth script: {e}")
    
    def warm_up_session(self):
        """Warm up the browser session with realistic browsing patterns."""
        logger.info("Starting session warm-up...")
        
        try:
            # Visit Google homepage first
            self.driver.get("https://www.google.com")
            time.sleep(random.uniform(3, 6))
            
            # Simulate realistic mouse movements
            self.realistic_mouse_movements()
            
            # Handle cookie consent naturally
            self.handle_cookie_consent()
            
            # Simulate browsing behavior
            self.simulate_browsing_behavior()
            
            # Visit a few other pages to establish session
            other_sites = [
                "https://www.google.com/search?q=weather",
                "https://www.google.com/search?q=news",
                "https://www.google.com/maps"
            ]
            
            for site in random.sample(other_sites, 2):
                try:
                    self.driver.get(site)
                    time.sleep(random.uniform(2, 4))
                    self.realistic_mouse_movements()
                    time.sleep(random.uniform(1, 3))
                except Exception as e:
                    logger.warning(f"Error visiting {site}: {e}")
            
            # Return to Google homepage
            self.driver.get("https://www.google.com")
            time.sleep(random.uniform(2, 4))
            
            logger.info("Session warm-up completed")
            
        except Exception as e:
            logger.error(f"Error during session warm-up: {e}")
    
    def handle_cookie_consent(self):
        """Handle cookie consent in a natural way."""
        try:
            # Wait a bit before looking for consent
            time.sleep(random.uniform(1, 3))
            
            cookie_selectors = [
                "//button[contains(text(), 'Accept')]",
                "//button[contains(text(), 'I agree')]",
                "//button[contains(text(), 'Accept all')]",
                "//button[contains(text(), 'Agree')]",
                "#L2AGLb",  # Google's "I agree" button ID
                ".QS5gu",   # Another Google consent button class
                "[data-ved] button",
                "button[jsname='b3VHJd']"
            ]
            
            for selector in cookie_selectors:
                try:
                    if selector.startswith("//"):
                        element = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        element = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    
                    # Simulate human-like clicking
                    self.human_like_click(element)
                    logger.info("Accepted cookies naturally")
                    time.sleep(random.uniform(1, 3))
                    return True
                    
                except TimeoutException:
                    continue
                    
        except Exception as e:
            logger.info("No cookie consent found or already handled")
        
        return False
    
    def simulate_browsing_behavior(self):
        """Simulate realistic browsing behavior."""
        try:
            # Random scrolling
            for _ in range(random.randint(2, 5)):
                scroll_amount = random.randint(100, 500)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(random.uniform(0.5, 1.5))
            
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(random.uniform(0.5, 1))
            
            # Random mouse movements
            self.realistic_mouse_movements()
            
        except Exception as e:
            logger.warning(f"Error in browsing simulation: {e}")
    
    def realistic_mouse_movements(self):
        """Perform highly realistic mouse movements."""
        try:
            actions = ActionChains(self.driver)
            
            # Get window size
            window_size = self.driver.get_window_size()
            max_x = window_size['width']
            max_y = window_size['height']
            
            # Perform multiple realistic movements
            movements = random.randint(3, 8)
            
            current_x, current_y = max_x // 2, max_y // 2
            
            for _ in range(movements):
                # Calculate next position with some randomness
                target_x = random.randint(50, max_x - 50)
                target_y = random.randint(50, max_y - 50)
                
                # Move in steps to simulate human movement
                steps = random.randint(5, 15)
                for step in range(steps):
                    intermediate_x = current_x + (target_x - current_x) * step / steps
                    intermediate_y = current_y + (target_y - current_y) * step / steps
                    
                    # Add some jitter
                    jitter_x = random.randint(-5, 5)
                    jitter_y = random.randint(-5, 5)
                    
                    actions.move_by_offset(
                        intermediate_x - current_x + jitter_x,
                        intermediate_y - current_y + jitter_y
                    )
                    actions.perform()
                    
                    current_x = intermediate_x + jitter_x
                    current_y = intermediate_y + jitter_y
                    
                    time.sleep(random.uniform(0.01, 0.05))
                    actions = ActionChains(self.driver)
                
                # Pause at destination
                time.sleep(random.uniform(0.1, 0.8))
                
        except Exception as e:
            logger.warning(f"Realistic mouse movement failed: {e}")
    
    def human_like_typing(self, element, text):
        """Type text with highly realistic human patterns."""
        element.clear()
        time.sleep(random.uniform(0.1, 0.3))
        
        for i, char in enumerate(text):
            # Simulate occasional typos and corrections
            if random.random() < 0.05 and i > 0:  # 5% chance of typo
                wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                element.send_keys(wrong_char)
                time.sleep(random.uniform(0.1, 0.3))
                element.send_keys(Keys.BACKSPACE)
                time.sleep(random.uniform(0.1, 0.2))
            
            element.send_keys(char)
            
            # Variable typing speed
            if char == ' ':
                time.sleep(random.uniform(0.1, 0.3))  # Longer pause after space
            else:
                time.sleep(random.uniform(0.05, 0.15))
            
            # Occasional thinking pauses
            if random.random() < 0.08:  # 8% chance
                time.sleep(random.uniform(0.5, 2.0))
    
    def human_like_click(self, element):
        """Perform human-like clicking with slight randomness."""
        try:
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(random.uniform(0.2, 0.5))
            
            # Move to element first
            actions = ActionChains(self.driver)
            actions.move_to_element(element)
            actions.perform()
            time.sleep(random.uniform(0.1, 0.3))
            
            # Click with slight offset for realism
            offset_x = random.randint(-2, 2)
            offset_y = random.randint(-2, 2)
            actions.move_to_element_with_offset(element, offset_x, offset_y)
            actions.click()
            actions.perform()
            
        except Exception as e:
            # Fallback to regular click
            element.click()
    
    def get_next_proxy(self):
        """Get next proxy from the list."""
        if not self.proxy_list:
            return None
        
        proxy = self.proxy_list[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
        return proxy
    
    def detect_blocking_advanced(self):
        """Advanced blocking detection with multiple indicators."""
        blocking_indicators = [
            "captcha", "unusual traffic", "automated queries", "robot",
            "verify you're human", "suspicious activity", "blocked",
            "access denied", "too many requests", "rate limit",
            "security check", "verify your identity", "prove you're human",
            "automated traffic", "bot", "crawler", "scraper"
        ]
        
        try:
            page_source = self.driver.page_source.lower()
            page_title = self.driver.title.lower()
            current_url = self.driver.current_url.lower()
            
            # Check page content
            for indicator in blocking_indicators:
                if indicator in page_source or indicator in page_title:
                    logger.warning(f"Blocking detected in content: {indicator}")
                    return True, indicator
            
            # Check URL for redirects to blocking pages
            blocking_urls = ["sorry.google.com", "accounts.google.com/signin"]
            for url_part in blocking_urls:
                if url_part in current_url:
                    logger.warning(f"Blocking detected in URL: {url_part}")
                    return True, f"url_redirect_{url_part}"
            
            # Check for CAPTCHA elements
            captcha_selectors = [
                "#captcha", ".captcha", "[id*='captcha']", "[class*='captcha']",
                ".g-recaptcha", "#recaptcha", ".recaptcha", "[data-sitekey]",
                "iframe[src*='recaptcha']", ".cf-challenge-form"
            ]
            
            for selector in captcha_selectors:
                try:
                    if self.driver.find_elements(By.CSS_SELECTOR, selector):
                        logger.warning(f"CAPTCHA element found: {selector}")
                        return True, "captcha_element"
                except:
                    continue
            
            # Check for missing search elements (indicates blocking)
            essential_elements = ["input[name='q']", "textarea[name='q']", "#APjFqb"]
            found_search_box = False
            for selector in essential_elements:
                try:
                    if self.driver.find_elements(By.CSS_SELECTOR, selector):
                        found_search_box = True
                        break
                except:
                    continue
            
            if not found_search_box and "google" in current_url:
                logger.warning("Search box not found - possible blocking")
                return True, "missing_search_elements"
                
            return False, None
            
        except Exception as e:
            logger.error(f"Error detecting blocking: {e}")
            return False, None
    
    def handle_blocking_advanced(self, blocking_type):
        """Advanced blocking handling with multiple strategies."""
        logger.warning(f"Handling blocking type: {blocking_type}")
        
        if "captcha" in blocking_type.lower():
            logger.info("CAPTCHA detected. Implementing evasion strategy...")
            
            # Strategy 1: Wait and hope it goes away
            time.sleep(random.uniform(30, 60))
            
            # Strategy 2: Try refreshing
            try:
                self.driver.refresh()
                time.sleep(random.uniform(5, 10))
                
                # Check if blocking is gone
                is_blocked, _ = self.detect_blocking_advanced()
                if not is_blocked:
                    logger.info("Blocking resolved after refresh")
                    return True
            except:
                pass
            
            # Strategy 3: Restart session
            logger.info("Restarting session to bypass blocking...")
            return False
        
        # For other blocking types
        if "rate limit" in blocking_type.lower() or "too many requests" in blocking_type.lower():
            wait_time = random.uniform(300, 600)  # Wait 5-10 minutes
            logger.info(f"Rate limit detected. Waiting {wait_time:.1f} seconds...")
            time.sleep(wait_time)
            return True
        
        # Default strategy: exponential backoff
        wait_time = random.uniform(60, 300)  # Wait 1-5 minutes
        logger.info(f"Waiting {wait_time:.1f} seconds before retry...")
        time.sleep(wait_time)
        
        return False
    
    def restart_session(self):
        """Restart the browser session with new fingerprint."""
        logger.info("Restarting session with new fingerprint...")
        
        try:
            if self.driver:
                self.driver.quit()
                time.sleep(random.uniform(5, 15))
        except:
            pass
        
        # Switch between mobile and desktop randomly
        self.use_mobile = random.choice([True, False])
        
        # Setup new driver
        if self.setup_undetected_driver():
            self.warm_up_session()
            self.session_requests = 0
            self.max_requests_per_session = random.randint(8, 15)
            return True
        
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

def analyze_google_search_advanced(scraper, search_term, max_retries=3):
    """Advanced Google search with comprehensive evasion."""
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Searching Google for: '{search_term}' (Attempt {attempt + 1}/{max_retries})")
            
            # Check if we need to restart session
            scraper.session_requests += 1
            if scraper.session_requests >= scraper.max_requests_per_session:
                logger.info("Session limit reached, restarting...")
                if not scraper.restart_session():
                    continue
            
            # Extended pre-search delay
            pre_search_delay = random.uniform(5, 15)
            logger.info(f"Pre-search delay: {pre_search_delay:.1f} seconds")
            time.sleep(pre_search_delay)
            
            # Navigate to Google with realistic referrer
            if random.choice([True, False]):
                # Sometimes go through google.com first
                scraper.driver.get("https://www.google.com")
                time.sleep(random.uniform(2, 5))
                scraper.realistic_mouse_movements()
            
            # Go to search page
            scraper.driver.get("https://www.google.com/search")
            time.sleep(random.uniform(2, 4))
            
            # Check for blocking immediately
            is_blocked, blocking_type = scraper.detect_blocking_advanced()
            if is_blocked:
                if scraper.handle_blocking_advanced(blocking_type):
                    continue
                else:
                    if not scraper.restart_session():
                        continue
                    continue
            
            # Realistic mouse movements before searching
            scraper.realistic_mouse_movements()
            
            # Find search box with multiple strategies
            search_box_selectors = [
                "input[name='q']", 
                "textarea[name='q']", 
                "#APjFqb",
                "[data-ved] input",
                ".gLFyf"
            ]
            
            search_box = None
            for selector in search_box_selectors:
                try:
                    search_box = WebDriverWait(scraper.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"Found search box with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not search_box:
                logger.warning("Could not find search box")
                continue
            
            # Human-like interaction with search box
            scraper.human_like_click(search_box)
            time.sleep(random.uniform(0.5, 1.5))
            
            # Type search term naturally
            scraper.human_like_typing(search_box, search_term)
            
            # Random delay before submitting
            time.sleep(random.uniform(1, 3))
            
            # Submit search (sometimes use Enter, sometimes click search button)
            if random.choice([True, False]):
                search_box.send_keys(Keys.RETURN)
            else:
                try:
                    search_button = scraper.driver.find_element(By.CSS_SELECTOR, "input[value='Google Search']")
                    scraper.human_like_click(search_button)
                except:
                    search_box.send_keys(Keys.RETURN)
            
            # Wait for results with extended timeout
            try:
                WebDriverWait(scraper.driver, 20).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.ID, "search")),
                        EC.presence_of_element_located((By.ID, "rso")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[data-ved]")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".g"))
                    )
                )
            except TimeoutException:
                logger.warning("Search results took too long to load")
                continue
            
            # Check for blocking after search
            is_blocked, blocking_type = scraper.detect_blocking_advanced()
            if is_blocked:
                if scraper.handle_blocking_advanced(blocking_type):
                    continue
                else:
                    if not scraper.restart_session():
                        continue
                    continue
            
            # Simulate reading results
            time.sleep(random.uniform(2, 5))
            scraper.realistic_mouse_movements()
            
            # Look for AI overview with comprehensive selectors
            logger.info("Looking for AI overview...")
            
            ai_overview_element = None
            ai_overview_selectors = [
                # Latest Google AI overview selectors
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
                ".yp",
                "[data-md='50']",
                ".ULSxyf",
                ".hgKElc", 
                ".kno-fb-ctx",
                ".Z0LcW",
                ".IZ6rdc",
                ".ayRjaf",
                ".g-section-with-header",
                ".knowledge-panel",
                ".kp-wholepage",
                "[data-hveid*='CA']",
                ".g[data-ved*='0ahUKEwi']"
            ]
            
            # Try each selector with patience
            for selector in ai_overview_selectors:
                try:
                    elements = scraper.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        ai_overview_element = elements[0]
                        logger.info(f"AI overview found using selector: {selector}")
                        break
                except:
                    continue
            
            if ai_overview_element:
                # Ensure element is visible and stable
                time.sleep(random.uniform(2, 4))
                
                # Scroll to element naturally
                scraper.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", ai_overview_element)
                time.sleep(random.uniform(2, 3))
                
                # Take screenshot
                safe_filename_term = sanitize_filename(search_term)
                screenshot_path = f"screenshots_google_ai/{safe_filename_term}_ai_overview.png"
                
                try:
                    # Ensure directory exists
                    os.makedirs("screenshots_google_ai", exist_ok=True)
                    
                    ai_overview_element.screenshot(screenshot_path)
                    logger.info(f"Screenshot saved to: {screenshot_path}")
                    return True, screenshot_path
                except Exception as e:
                    logger.error(f"Failed to take screenshot: {e}")
                    return False, None
            else:
                logger.info(f"No AI overview found for '{search_term}'")
                return False, None
                
        except TimeoutException:
            logger.warning(f"Timeout occurred for '{search_term}' (Attempt {attempt + 1})")
            if attempt < max_retries - 1:
                delay = random.uniform(30, 90)
                logger.info(f"Waiting {delay:.1f} seconds before retry...")
                time.sleep(delay)
            continue
            
        except Exception as e:
            logger.error(f"Error occurred while searching for '{search_term}': {e}")
            if attempt < max_retries - 1:
                delay = random.uniform(30, 90)
                time.sleep(delay)
            continue
    
    logger.error(f"Failed to search for '{search_term}' after {max_retries} attempts")
    return False, None

def main():
    # Configuration
    csv_file_path = 'test_search_terms.csv'
    screenshots_dir = "screenshots_google_ai"
    results_csv_path = 'google_ai_overview_results_advanced.csv'
    min_delay = 15   # Increased delays significantly
    max_delay = 45
    
    # Proxy configuration (optional)
    use_proxy = False  # Set to True to enable proxy rotation
    proxy_list = [
        # Add your proxy list here in format: "ip:port" or "username:password@ip:port"
        # "proxy1.example.com:8080",
        # "proxy2.example.com:8080"
    ]
    
    # Initialize advanced scraper
    scraper = AdvancedGoogleAIScraper(use_proxy=use_proxy, proxy_list=proxy_list)
    
    try:
        # Setup undetected driver
        if not scraper.setup_undetected_driver():
            logger.error("Failed to setup undetected driver. Exiting.")
            return
        
        # Warm up session
        scraper.warm_up_session()
        
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
            
            # Search with advanced retry logic
            has_ai_overview, screenshot = analyze_google_search_advanced(scraper, term)
            
            # Store results
            results.append({
                "search_term": term,
                "has_ai_overview": has_ai_overview,
                "screenshot_path": screenshot
            })
            
            # Extended delay between searches
            delay = random.uniform(min_delay, max_delay)
            logger.info(f"Waiting {delay:.2f} seconds before next search...")
            time.sleep(delay)
            
            # Extended breaks every few searches
            if (i + 1) % 5 == 0:
                long_break = random.uniform(120, 300)  # 2-5 minutes
                logger.info(f"Taking extended break: {long_break:.1f} seconds...")
                time.sleep(long_break)
                
                # Occasionally restart session for fresh fingerprint
                if random.random() < 0.3:  # 30% chance
                    logger.info("Restarting session for fresh fingerprint...")
                    scraper.restart_session()
    
    except KeyboardInterrupt:
        logger.info("Script interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Cleanup
        try:
            if scraper.driver:
                scraper.driver.quit()
                logger.info("Browser closed.")
        except:
            pass
    
    # Save results
    logger.info("\n--- Advanced Search Analysis Complete ---")
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

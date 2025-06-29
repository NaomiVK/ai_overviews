#!/usr/bin/env python3
"""
Google AI Overview Detector with advanced rate limit handling
"""

import csv
import time
import random
import json
import urllib.parse
from datetime import datetime
from playwright.sync_api import sync_playwright
from pathlib import Path

class GoogleAIOverviewScraper:
    def __init__(self, csv_file, output_dir="screenshots", delay_range=(10, 20), proxies=None):
        self.csv_file = csv_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.delay_range = delay_range
        self.results = []
        self.proxies = proxies or []
        self.current_proxy_index = 0
        self.rate_limit_count = 0
        self.backoff_time = 30  # Initial backoff time in seconds
        
        if self.proxies:
            print(f"🔐 Proxy configuration loaded: {len(self.proxies)} proxies available")
        else:
            print("⚠️ No proxies configured - running without proxy")
        
        # Extended user agents list
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
        ]

    def get_next_proxy(self, force_rotate=False):
        """Get the next proxy from the list with rotation"""
        if not self.proxies:
            return None
        
        if force_rotate:
            # Force rotation to next proxy
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        
        proxy_config = self.proxies[self.current_proxy_index]
        
        # Parse proxy URL format
        if isinstance(proxy_config, str):
            import re
            match = re.match(r'http://([^:]+):([^@]+)@([^:]+):([^/]+)', proxy_config)
            if match:
                username, password, host, port = match.groups()
                proxy_dict = {
                    'server': f'http://{host}:{port}',
                    'username': username,
                    'password': password
                }
                print(f"  🔐 Using proxy session {self.current_proxy_index + 1}/{len(self.proxies)}")
                return proxy_dict
        return proxy_config

    def setup_browser_context(self, playwright, proxy=None):
        """Setup browser with anti-detection measures"""
        user_agent = random.choice(self.user_agents)
        
        launch_options = {
            'headless': True,  # Run headless to reduce detection
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                # Add more realistic browser args
                '--window-size=1920,1080',
                '--start-maximized',
                '--disable-plugins',
                '--disable-images',
                '--disable-gpu',
                '--disable-dev-tools',
                '--disable-extensions',
                '--no-first-run',
                '--no-default-browser-check',
            ]
        }
        
        if proxy:
            launch_options['proxy'] = proxy
            print(f"  🔐 Using proxy: {proxy['server']}")
        
        browser = playwright.chromium.launch(**launch_options)
        
        # Random viewport to appear more natural
        viewport_options = [
            {'width': 1920, 'height': 1080},
            {'width': 1366, 'height': 768},
            {'width': 1536, 'height': 864},
            {'width': 1440, 'height': 900},
        ]
        
        context = browser.new_context(
            user_agent=user_agent,
            viewport=random.choice(viewport_options),
            locale='en-CA',
            timezone_id='America/Toronto',
            ignore_https_errors=True,
            # Add more realistic headers
            extra_http_headers={
                'Accept-Language': 'en-CA,en-US;q=0.9,en;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            }
        )
        
        # Set timeouts
        context.set_default_navigation_timeout(60000)  # 60 seconds
        context.set_default_timeout(60000)
        
        # Block unnecessary resources
        context.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf}", lambda route: route.abort())
        context.route("**/gtm.js", lambda route: route.abort())
        context.route("**/analytics.js", lambda route: route.abort())
        context.route("**/fbevents.js", lambda route: route.abort())
        context.route("**/*.css", lambda route: route.abort())
        
        # Enhanced stealth
        context.add_init_script("""
            // Overwrite the `navigator.webdriver` property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {
                        0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    }
                ]
            });
            
            // Mock chrome
            window.chrome = {
                runtime: {},
            };
            
            // Mock language
            Object.defineProperty(navigator, 'language', {
                get: () => 'en-CA'
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-CA', 'en-US', 'en']
            });
        """)
        
        return browser, context

    def handle_rate_limit(self):
        """Handle rate limiting with exponential backoff"""
        self.rate_limit_count += 1
        wait_time = min(self.backoff_time * (2 ** (self.rate_limit_count - 1)), 300)  # Max 5 minutes
        
        print(f"\n⚠️ Rate limit detected (429). Count: {self.rate_limit_count}")
        print(f"⏳ Waiting {wait_time} seconds before retrying...")
        
        # Progress indicator
        for i in range(int(wait_time)):
            print(f"\r⏳ Waiting... {wait_time - i} seconds remaining", end='', flush=True)
            time.sleep(1)
        print()  # New line after countdown
        
        return wait_time

    def detect_ai_overview(self, page):
        """Detect AI Overview with improved selectors"""
        print("  🔍 Checking for AI Overview...")
        
        # Wait for content to load
        try:
            page.wait_for_load_state('domcontentloaded', timeout=30000)
            time.sleep(2)  # Additional wait for dynamic content
        except:
            pass
        
        # Comprehensive AI Overview selectors
        ai_overview_selectors = [
            # Direct AI Overview headers
            'h1:has-text("AI Overview")',
            'h2:has-text("AI Overview")',
            'div[class*="AI Overview"]',
            'div[aria-label*="AI Overview"]',
            
            # Known Google AI Overview classes
            'div.YzCcne',
            'h1.VW3apb',
            'div[data-attrid="ai-overview"]',
            
            # Text-based search
            'div:has-text("AI Overview"):not([aria-hidden="true"])',
            
            # Structural patterns
            'div[jscontroller][jsname]:has(h1:has-text("AI Overview"))',
            'div[data-ved]:has(h1:has-text("AI Overview"))',
        ]
        
        for selector in ai_overview_selectors:
            try:
                elements = page.query_selector_all(selector)
                for element in elements:
                    if element and element.is_visible():
                        try:
                            text = element.inner_text()
                            if text and "AI Overview" in text:
                                print(f"  ✅ Found AI Overview using: {selector}")
                                return True, selector, element
                        except:
                            continue
            except:
                continue
        
        # Final check in page content
        try:
            page_content = page.content()
            if "AI Overview" in page_content and "Generated" in page_content:
                print(f"  ⚠️ AI Overview text found in source but not as visible element")
        except:
            pass
        
        print(f"  ❌ No AI Overview found")
        return False, None, None

    def search_and_screenshot(self, search_term, browser, context, retry_count=0):
        """Perform search with retry logic for rate limits"""
        page = context.new_page()
        
        try:
            # Randomize search approach
            if random.random() < 0.3:  # 30% chance to use homepage first
                print(f"  🏠 Using homepage approach for: {search_term}")
                page.goto('https://www.google.ca', wait_until='domcontentloaded', timeout=60000)
                time.sleep(random.uniform(2, 4))
                
                # Find and use search box
                search_box = page.query_selector('input[name="q"], textarea[name="q"]')
                if search_box:
                    search_box.click()
                    time.sleep(random.uniform(0.5, 1.5))
                    search_box.type(search_term, delay=random.randint(50, 150))
                    time.sleep(random.uniform(0.5, 1.5))
                    search_box.press('Enter')
                    page.wait_for_load_state('networkidle', timeout=60000)
            else:
                # Direct search URL
                search_url = f"https://www.google.ca/search?q={urllib.parse.quote_plus(search_term)}&hl=en-CA&gl=ca"
                print(f"  🔍 Direct search for: {search_term}")
                
                response = page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
                
                # Check for rate limiting
                if response and response.status == 429:
                    page.close()
                    
                    if retry_count >= 3:
                        print(f"  ❌ Max retries reached for '{search_term}'")
                        return {
                            'search_term': search_term,
                            'has_ai_overview': False,
                            'timestamp': datetime.now().isoformat(),
                            'error': 'Rate limited after 3 retries'
                        }
                    
                    # Handle rate limit
                    self.handle_rate_limit()
                    
                    # Force proxy rotation
                    if self.proxies:
                        print("  🔄 Rotating to next proxy...")
                        return None  # Signal to rotate proxy
                    
                    # Retry with same context
                    return self.search_and_screenshot(search_term, browser, context, retry_count + 1)
                
                elif not response or response.status >= 400:
                    raise Exception(f"Page load failed with status {response.status if response else 'No response'}")
            
            # Random delay to appear more human
            time.sleep(random.uniform(2, 5))
            
            # Check for AI Overview
            has_ai_overview, selector_used, ai_overview_element = self.detect_ai_overview(page)
            
            result = {
                'search_term': search_term,
                'has_ai_overview': has_ai_overview,
                'selector_used': selector_used,
                'timestamp': datetime.now().isoformat(),
                'screenshot_path': None,
            }
            
            # Screenshot if found
            if has_ai_overview and ai_overview_element:
                screenshot_path = self.output_dir / f"{search_term.replace(' ', '_').replace('/', '_')}_ai_overview.png"
                
                # Re-enable images for screenshot
                page.route("**/*", lambda route: route.continue_())
                time.sleep(3)
                
                page.screenshot(path=str(screenshot_path), full_page=True)
                result['screenshot_path'] = str(screenshot_path)
                print(f"  📸 Screenshot saved")
            
            # Reset rate limit count on success
            if self.rate_limit_count > 0:
                self.rate_limit_count = max(0, self.rate_limit_count - 1)
            
            return result
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            return {
                'search_term': search_term,
                'has_ai_overview': False,
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
        finally:
            page.close()

    def run_analysis(self):
        """Main function with improved error handling"""
        print("🚀 Starting Google AI Overview Analysis with Rate Limit Protection...")
        print(f"⏱️ Using delay range: {self.delay_range[0]}-{self.delay_range[1]} seconds")
        
        # Read search terms
        search_terms = []
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader, None)
                search_terms = [row[0].strip() for row in reader if row]
        except Exception as e:
            print(f"❌ Error reading CSV: {e}")
            return
        
        print(f"📊 Found {len(search_terms)} search terms")
        
        with sync_playwright() as playwright:
            proxy = self.get_next_proxy()
            browser, context = self.setup_browser_context(playwright, proxy)
            
            try:
                for i, term in enumerate(search_terms, 1):
                    print(f"\n{'='*60}")
                    print(f"🔍 Processing {i}/{len(search_terms)}: '{term}'")
                    
                    result = self.search_and_screenshot(term, browser, context)
                    
                    # Check if we need to rotate proxy (None result indicates rate limit)
                    if result is None and self.proxies:
                        context.close()
                        browser.close()
                        proxy = self.get_next_proxy(force_rotate=True)
                        browser, context = self.setup_browser_context(playwright, proxy)
                        # Retry with new proxy
                        result = self.search_and_screenshot(term, browser, context)
                    
                    if result:
                        self.results.append(result)
                    
                    # Delay between searches
                    if i < len(search_terms):
                        delay = random.uniform(self.delay_range[0], self.delay_range[1])
                        print(f"\n⏳ Waiting {delay:.1f} seconds before next search...")
                        time.sleep(delay)
                        
                        # Periodic proxy rotation
                        if i % 3 == 0 and self.proxies:
                            print("\n🔄 Periodic proxy rotation...")
                            context.close()
                            browser.close()
                            proxy = self.get_next_proxy(force_rotate=True)
                            browser, context = self.setup_browser_context(playwright, proxy)
                
            finally:
                context.close()
                browser.close()
        
        self.save_results()
        self.print_summary()

    def save_results(self):
        """Save results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON results
        json_file = f"ai_overview_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Detailed results saved to {json_file}")
        
        # CSV summary
        csv_file = f"ai_overview_summary_{timestamp}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Search Term', 'Has AI Overview', 'Screenshot Path', 'Error', 'Timestamp'])
            
            for result in self.results:
                writer.writerow([
                    result['search_term'],
                    result['has_ai_overview'],
                    result.get('screenshot_path', ''),
                    result.get('error', ''),
                    result['timestamp']
                ])
        print(f"📊 Summary saved to {csv_file}")

    def print_summary(self):
        """Print analysis summary"""
        total = len(self.results)
        with_ai = sum(1 for r in self.results if r['has_ai_overview'])
        errors = sum(1 for r in self.results if 'error' in r)
        
        print(f"\n{'='*60}")
        print(f"📈 ANALYSIS SUMMARY")
        print(f"{'='*60}")
        print(f"Total searches: {total}")
        print(f"With AI Overview: {with_ai}")
        print(f"Errors: {errors}")
        print(f"Success rate: {((total-errors)/total)*100:.1f}%" if total > 0 else "N/A")
        print(f"AI Overview rate: {(with_ai/total)*100:.1f}%" if total > 0 else "N/A")


if __name__ == "__main__":
    # Configuration
    CSV_FILE = "cra_search_terms.csv"
    OUTPUT_DIR = "ai_overview_screenshots"
    DELAY_RANGE = (15, 30)  # Longer delays to avoid rate limits
    
    # Oxylabs Proxy Configuration
    proxy_user = 'customer-naomivk_2kqmu-cc-CA'
    proxy_pass = 'GeorgieDory2147_3'
    proxy_host = 'pr.oxylabs.io'
    proxy_port = '7777'
    
    # Use multiple session-based proxies
    PROXIES = [
        f"http://{proxy_user}-session-{i}:{proxy_pass}@{proxy_host}:{proxy_port}"
        for i in range(1, 6)  # 5 different sessions
    ]
    
    # Run scraper
    scraper = GoogleAIOverviewScraper(
        csv_file=CSV_FILE,
        output_dir=OUTPUT_DIR,
        delay_range=DELAY_RANGE,
        proxies=PROXIES
    )
    
    scraper.run_analysis()
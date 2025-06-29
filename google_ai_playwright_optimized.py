#!/usr/bin/env python3
"""
Optimized Google AI Overview Detector with better proxy handling
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
    def __init__(self, csv_file, output_dir="screenshots", delay_range=(3, 8), proxies=None):
        self.csv_file = csv_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.delay_range = delay_range
        self.results = []
        self.proxies = proxies or []
        self.current_proxy_index = 0
        
        if self.proxies:
            print(f"🔐 Proxy configuration loaded: {len(self.proxies)} proxies available")
        else:
            print("⚠️ No proxies configured - running without proxy")
        
        # User agents to rotate
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

    def get_next_proxy(self):
        """Get the next proxy from the list with rotation"""
        if not self.proxies:
            return None
        
        proxy_config = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        
        # Parse proxy URL format: http://username:password@host:port
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
                print(f"  🔐 Using proxy session {self.current_proxy_index}/{len(self.proxies)}")
                return proxy_dict
        return proxy_config

    def setup_browser_context(self, playwright, proxy=None):
        """Setup browser with optimized settings for proxy usage"""
        user_agent = random.choice(self.user_agents)
        
        launch_options = {
            'headless': False,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                # Optimize for proxy usage
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                # Reduce resource usage
                '--disable-plugins',
                '--disable-images',  # Disable images for faster loading
            ]
        }
        
        if proxy:
            launch_options['proxy'] = proxy
            print(f"  🔐 Using proxy: {proxy['server']}")
        
        browser = playwright.chromium.launch(**launch_options)
        
        context = browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1920, 'height': 1080},
            locale='en-CA',
            timezone_id='America/Toronto',
            ignore_https_errors=True,  # Ignore SSL errors
        )
        
        # Set default navigation timeout
        context.set_default_navigation_timeout(45000)  # 45 seconds
        context.set_default_timeout(45000)  # 45 seconds for all operations
        
        # Block unnecessary resources
        context.route("**/*.{png,jpg,jpeg,gif,svg,ico}", lambda route: route.abort())
        context.route("**/gtm.js", lambda route: route.abort())
        context.route("**/analytics.js", lambda route: route.abort())
        context.route("**/fbevents.js", lambda route: route.abort())
        
        # Add stealth scripts
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        return browser, context

    def detect_ai_overview(self, page):
        """Simplified AI Overview detection"""
        print("  🔍 Checking for AI Overview...")
        
        # Wait for page to stabilize
        page.wait_for_load_state('networkidle', timeout=30000)
        
        # Simple selectors for AI Overview
        ai_overview_selectors = [
            'h1:has-text("AI Overview")',
            'div:has-text("AI Overview")',
            '[aria-label*="AI Overview"]',
        ]
        
        for selector in ai_overview_selectors:
            try:
                elements = page.query_selector_all(selector)
                for element in elements:
                    if element and element.is_visible():
                        text = element.inner_text()
                        if text and "AI Overview" in text:
                            print(f"  ✅ Found AI Overview")
                            return True, selector, element
            except:
                continue
        
        # Check page content as fallback
        try:
            page_content = page.content()
            if "AI Overview" in page_content:
                print(f"  ⚠️ Found AI Overview in content but no visible element")
        except:
            pass
        
        print(f"  ❌ No AI Overview found")
        return False, None, None

    def search_and_screenshot(self, search_term, browser, context):
        """Perform search with optimized loading"""
        page = context.new_page()
        
        try:
            # Direct search URL
            search_url = f"https://www.google.ca/search?q={urllib.parse.quote_plus(search_term)}&hl=en-CA&gl=ca"
            
            print(f"  🌐 Searching for: {search_term}")
            
            # Navigate with network idle wait
            response = page.goto(search_url, wait_until='networkidle', timeout=45000)
            
            if not response or response.status >= 400:
                print(f"  ❌ Failed to load page: Status {response.status if response else 'No response'}")
                raise Exception(f"Page load failed with status {response.status if response else 'No response'}")
            
            # Wait a bit for dynamic content
            time.sleep(3)
            
            # Check for AI Overview
            has_ai_overview, selector_used, ai_overview_element = self.detect_ai_overview(page)
            
            result = {
                'search_term': search_term,
                'has_ai_overview': has_ai_overview,
                'selector_used': selector_used,
                'timestamp': datetime.now().isoformat(),
                'screenshot_path': None,
            }
            
            # Take screenshot if AI overview found
            if has_ai_overview and ai_overview_element:
                screenshot_path = self.output_dir / f"{search_term.replace(' ', '_').replace('/', '_')}_ai_overview.png"
                
                # Enable images temporarily for screenshot
                page.route("**/*", lambda route: route.continue_())
                time.sleep(2)  # Let images load
                
                page.screenshot(path=str(screenshot_path), full_page=True)
                result['screenshot_path'] = str(screenshot_path)
                print(f"  📸 Screenshot saved")
            
            return result
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            return {
                'search_term': search_term,
                'has_ai_overview': False,
                'selector_used': None,
                'timestamp': datetime.now().isoformat(),
                'screenshot_path': None,
                'error': str(e)
            }
        finally:
            page.close()

    def run_analysis(self):
        """Main function to run the analysis"""
        print("🚀 Starting Google AI Overview Analysis...")
        
        # Read search terms
        search_terms = []
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader, None)  # Skip header
                search_terms = [row[0].strip() for row in reader if row]
        except Exception as e:
            print(f"❌ Error reading CSV: {e}")
            return
        
        print(f"📊 Found {len(search_terms)} search terms")
        
        with sync_playwright() as playwright:
            proxy = self.get_next_proxy() if self.proxies else None
            browser, context = self.setup_browser_context(playwright, proxy)
            
            try:
                for i, term in enumerate(search_terms, 1):
                    print(f"\n🔍 Processing {i}/{len(search_terms)}: '{term}'")
                    
                    result = self.search_and_screenshot(term, browser, context)
                    self.results.append(result)
                    
                    # Delay between searches
                    if i < len(search_terms):
                        delay = random.uniform(self.delay_range[0], self.delay_range[1])
                        print(f"⏳ Waiting {delay:.1f} seconds...")
                        time.sleep(delay)
                        
                        # Rotate proxy every 5 searches
                        if i % 5 == 0 and self.proxies:
                            print("🔄 Rotating proxy...")
                            context.close()
                            browser.close()
                            proxy = self.get_next_proxy()
                            browser, context = self.setup_browser_context(playwright, proxy)
                
            finally:
                context.close()
                browser.close()
        
        self.save_results()
        self.print_summary()

    def save_results(self):
        """Save results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON
        json_file = f"ai_overview_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"💾 Results saved to {json_file}")
        
        # Save CSV
        csv_file = f"ai_overview_summary_{timestamp}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Search Term', 'Has AI Overview', 'Screenshot Path', 'Timestamp'])
            
            for result in self.results:
                writer.writerow([
                    result['search_term'],
                    result['has_ai_overview'],
                    result.get('screenshot_path', ''),
                    result['timestamp']
                ])
        print(f"📊 Summary saved to {csv_file}")

    def print_summary(self):
        """Print analysis summary"""
        total = len(self.results)
        with_ai = sum(1 for r in self.results if r['has_ai_overview'])
        
        print(f"\n📈 ANALYSIS SUMMARY")
        print(f"{'='*50}")
        print(f"Total searches: {total}")
        print(f"With AI Overview: {with_ai}")
        print(f"Percentage: {(with_ai/total)*100:.1f}%" if total > 0 else "N/A")


if __name__ == "__main__":
    # Configuration
    CSV_FILE = "cra_search_terms.csv"
    OUTPUT_DIR = "ai_overview_screenshots"
    DELAY_RANGE = (5, 10)  # Longer delays for proxy
    
    # Oxylabs Proxy Configuration
    proxy_user = 'customer-naomivk_2kqmu-cc-CA'
    proxy_pass = 'GeorgieDory2147_3'
    proxy_host = 'pr.oxylabs.io'
    proxy_port = '7777'
    
    # Use session-based proxies
    PROXIES = [
        f"http://{proxy_user}-session-{i}:{proxy_pass}@{proxy_host}:{proxy_port}"
        for i in range(1, 4)  # Use 3 sessions
    ]
    
    # Run scraper
    scraper = GoogleAIOverviewScraper(
        csv_file=CSV_FILE,
        output_dir=OUTPUT_DIR,
        delay_range=DELAY_RANGE,
        proxies=PROXIES
    )
    
    scraper.run_analysis()
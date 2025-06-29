#!/usr/bin/env python3
"""
Google AI Overview Detector - Works with proxies from any country
Forces Canadian search results regardless of proxy location
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
        
        if self.proxies:
            print(f"🔐 Proxy configuration loaded: {len(self.proxies)} proxies available")
            print("🇨🇦 Will force Canadian search results regardless of proxy location")
        else:
            print("⚠️ No proxies configured - running without proxy")
        
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        ]

    def get_next_proxy(self):
        """Get the next proxy from the list"""
        if not self.proxies:
            return None
        
        proxy_config = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        
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
        """Setup browser with Canadian localization"""
        user_agent = random.choice(self.user_agents)
        
        launch_options = {
            'headless': False,  # Changed to False to show browser
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-images',
                '--disable-plugins',
            ]
        }
        
        if proxy:
            launch_options['proxy'] = proxy
        
        browser = playwright.chromium.launch(**launch_options)
        
        # FORCE CANADIAN CONTEXT
        context = browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1920, 'height': 1080},
            locale='en-CA',  # Canadian locale
            timezone_id='America/Toronto',  # Canadian timezone
            geolocation={'longitude': -79.3832, 'latitude': 43.6532},  # Toronto coordinates
            permissions=['geolocation'],
            extra_http_headers={
                'Accept-Language': 'en-CA,en-US;q=0.9,en;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
        )
        
        context.set_default_navigation_timeout(45000)
        context.set_default_timeout(45000)
        
        # Block resources
        context.route("**/*.{png,jpg,jpeg,gif,svg,ico,css}", lambda route: route.abort())
        
        # Anti-detection
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'language', {
                get: () => 'en-CA'
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-CA', 'en-US', 'en']
            });
        """)
        
        return browser, context

    def build_canadian_search_url(self, search_term):
        """Build search URL that forces Canadian results"""
        # Encode the search term
        encoded_term = urllib.parse.quote_plus(search_term)
        
        # Build URL with all Canadian parameters
        # Using google.com (not .ca) to work with any proxy
        base_url = "https://www.google.com/search"
        
        params = {
            'q': search_term,
            'gl': 'ca',  # Geographic location: Canada
            'hl': 'en-CA',  # Host language: Canadian English
            'cr': 'countryCA',  # Country restrict: Canada
            'lr': 'lang_en',  # Language restrict: English
            'pws': '0',  # Disable personalization
            # Optional: Add encoded location (Toronto)
            # 'uule': 'w+CAIQICIGY2FuYWRh'  # Encoded "canada"
        }
        
        param_string = urllib.parse.urlencode(params)
        return f"{base_url}?{param_string}"

    def detect_ai_overview(self, page):
        """Detect AI Overview"""
        print("  🔍 Checking for AI Overview...")
        
        page.wait_for_load_state('domcontentloaded', timeout=30000)
        time.sleep(2)
        
        ai_overview_selectors = [
            'h1:has-text("AI Overview")',
            'div:has-text("AI Overview"):not([aria-hidden="true"])',
            'div.YzCcne',
            'h1.VW3apb',
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
        
        print(f"  ❌ No AI Overview found")
        return False, None, None

    def search_and_screenshot(self, search_term, browser, context):
        """Perform search"""
        page = context.new_page()
        
        try:
            # Build Canadian search URL
            search_url = self.build_canadian_search_url(search_term)
            
            print(f"  🌐 Searching: {search_term}")
            print(f"  🇨🇦 Forcing Canadian results with parameters")
            
            response = page.goto(search_url, wait_until='domcontentloaded', timeout=45000)
            
            if response and response.status == 429:
                print(f"  ⚠️ Rate limited (429)")
                return {
                    'search_term': search_term,
                    'has_ai_overview': False,
                    'timestamp': datetime.now().isoformat(),
                    'error': 'Rate limited'
                }
            
            # Verify we're getting Canadian results (optional)
            try:
                # Check if page mentions Canada or Canadian sites
                page_text = page.content()
                if any(indicator in page_text for indicator in ['.gc.ca', 'Canada.ca', 'Government of Canada']):
                    print(f"  ✅ Confirmed Canadian results")
            except:
                pass
            
            time.sleep(random.uniform(2, 4))
            
            # Check for AI Overview
            has_ai_overview, selector_used, ai_overview_element = self.detect_ai_overview(page)
            
            result = {
                'search_term': search_term,
                'has_ai_overview': has_ai_overview,
                'selector_used': selector_used,
                'timestamp': datetime.now().isoformat(),
                'screenshot_path': None,
            }
            
            if has_ai_overview and ai_overview_element:
                screenshot_path = self.output_dir / f"{search_term.replace(' ', '_').replace('/', '_')}_ai_overview.png"
                page.route("**/*", lambda route: route.continue_())
                time.sleep(2)
                page.screenshot(path=str(screenshot_path), full_page=True)
                result['screenshot_path'] = str(screenshot_path)
                print(f"  📸 Screenshot saved")
            
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
        """Run the analysis"""
        print("🚀 Starting Google AI Overview Analysis")
        print("🌍 Using international proxies with Canadian localization")
        
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
        
        # Random initial delay to avoid patterns
        initial_delay = random.uniform(5, 15)
        print(f"⏳ Initial delay: {initial_delay:.1f} seconds to avoid detection...")
        time.sleep(initial_delay)
        
        with sync_playwright() as playwright:
            proxy = self.get_next_proxy()
            browser, context = self.setup_browser_context(playwright, proxy)
            
            try:
                for i, term in enumerate(search_terms, 1):
                    print(f"\n{'='*50}")
                    print(f"🔍 {i}/{len(search_terms)}: '{term}'")
                    
                    result = self.search_and_screenshot(term, browser, context)
                    self.results.append(result)
                    
                    # Check if we need new proxy due to rate limit
                    if result.get('error') == 'Rate limited' and self.proxies:
                        print("🔄 Rotating proxy due to rate limit...")
                        context.close()
                        browser.close()
                        
                        # Wait before using new proxy
                        wait_time = random.uniform(30, 60)
                        print(f"⏳ Waiting {wait_time:.0f} seconds...")
                        time.sleep(wait_time)
                        
                        proxy = self.get_next_proxy()
                        browser, context = self.setup_browser_context(playwright, proxy)
                    
                    # Delay between searches
                    if i < len(search_terms):
                        delay = random.uniform(self.delay_range[0], self.delay_range[1])
                        print(f"⏳ Waiting {delay:.1f} seconds...")
                        time.sleep(delay)
                        
                        # Rotate proxy every 2 searches for better diversity
                        if i % 2 == 0 and self.proxies:
                            print("🔄 Periodic proxy rotation...")
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
        """Save results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        json_file = f"ai_overview_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to {json_file}")
        
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
        """Print summary"""
        total = len(self.results)
        with_ai = sum(1 for r in self.results if r['has_ai_overview'])
        
        print(f"\n📈 SUMMARY")
        print(f"{'='*30}")
        print(f"Total: {total}")
        print(f"With AI Overview: {with_ai} ({(with_ai/total)*100:.1f}%)" if total > 0 else "N/A")


if __name__ == "__main__":
    CSV_FILE = "cra_search_terms.csv"
    OUTPUT_DIR = "ai_overview_screenshots"
    DELAY_RANGE = (20, 40)  # Increased delays to avoid detection
    
    # Oxylabs Configuration - Can use ANY country
    proxy_user = 'customer-naomivk_2kqmu'  # No -cc-CA needed!
    proxy_pass = 'GeorgieDory2147_3'
    proxy_host = 'pr.oxylabs.io'
    proxy_port = '7777'
    
    # Example configurations:
    
    # Option 1: Random international proxies
    # PROXIES = [
    #     f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
    #     for i in range(5)
    # ]
    
    # Option 2: Specific countries (will still get Canadian results!)
    PROXIES = [
        f"http://{proxy_user}-cc-US:{proxy_pass}@{proxy_host}:{proxy_port}",  # US proxy
        f"http://{proxy_user}-cc-GB:{proxy_pass}@{proxy_host}:{proxy_port}",  # UK proxy
        f"http://{proxy_user}-cc-AU:{proxy_pass}@{proxy_host}:{proxy_port}",  # Australia proxy
        f"http://{proxy_user}-cc-DE:{proxy_pass}@{proxy_host}:{proxy_port}",  # Germany proxy
        f"http://{proxy_user}-cc-FR:{proxy_pass}@{proxy_host}:{proxy_port}",  # France proxy
        f"http://{proxy_user}-cc-JP:{proxy_pass}@{proxy_host}:{proxy_port}",  # Japan proxy
        f"http://{proxy_user}-cc-IT:{proxy_pass}@{proxy_host}:{proxy_port}",  # Italy proxy
        f"http://{proxy_user}-cc-ES:{proxy_pass}@{proxy_host}:{proxy_port}",  # Spain proxy
        f"http://{proxy_user}-cc-NL:{proxy_pass}@{proxy_host}:{proxy_port}",  # Netherlands proxy
        f"http://{proxy_user}-cc-SE:{proxy_pass}@{proxy_host}:{proxy_port}",  # Sweden proxy
        f"http://{proxy_user}-cc-PL:{proxy_pass}@{proxy_host}:{proxy_port}",  # Poland proxy
        f"http://{proxy_user}-cc-BR:{proxy_pass}@{proxy_host}:{proxy_port}",  # Brazil proxy
    ]
    
    scraper = GoogleAIOverviewScraper(
        csv_file=CSV_FILE,
        output_dir=OUTPUT_DIR,
        delay_range=DELAY_RANGE,
        proxies=PROXIES
    )
    
    scraper.run_analysis()
#!/usr/bin/env python3
"""
Google AI Overview Detector for CRA
Uses stealth techniques to avoid bot detection

Proxy Configuration:
- Edit proxy credentials in the __main__ section at the bottom of the file
- Supports Oxylabs residential proxies with session management
- Three proxy modes available: session-based, city-based, or random Canadian IPs
"""

import csv
import time
import random
import json
import base64
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
        
        # Validate proxy configuration
        if self.proxies:
            print(f"🔐 Proxy configuration loaded: {len(self.proxies)} proxies available")
            self._validate_proxies()
        else:
            print("⚠️ No proxies configured - running without proxy")
        
        # User agents to rotate
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
        ]

    def _validate_proxies(self):
        """Validate proxy format and extract proxy types"""
        import re
        proxy_types = set()
        
        for proxy in self.proxies:
            if isinstance(proxy, str):
                match = re.match(r'http://([^:]+):([^@]+)@([^:]+):([^/]+)', proxy)
                if match:
                    username = match.group(1)
                    if '-session-' in username:
                        proxy_types.add('session-based')
                    elif '-city-' in username:
                        proxy_types.add('city-based')
                    else:
                        proxy_types.add('random IP')
                else:
                    print(f"⚠️ Invalid proxy format: {proxy}")
        
        if proxy_types:
            print(f"  ✅ Proxy types: {', '.join(proxy_types)}")

    def get_next_proxy(self):
        """Get the next proxy from the list with rotation"""
        if not self.proxies:
            return None
        
        proxy_config = self.proxies[self.current_proxy_index]
        self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxies)
        
        # Parse proxy URL format: http://username:password@host:port
        if isinstance(proxy_config, str):
            # Extract components from proxy URL
            import re
            match = re.match(r'http://([^:]+):([^@]+)@([^:]+):([^/]+)', proxy_config)
            if match:
                username, password, host, port = match.groups()
                proxy_dict = {
                    'server': f'http://{host}:{port}',
                    'username': username,
                    'password': password
                }
                print(f"  🔐 Proxy rotation: Using session {self.current_proxy_index}/{len(self.proxies)}")
                return proxy_dict
        return proxy_config

    def setup_browser_context(self, playwright, proxy=None):
        """Setup browser with stealth configurations"""
        # Random user agent
        user_agent = random.choice(self.user_agents)
        
        launch_options = {
            'headless': False,  # Set to True for production
            'slow_mo': 1000,  # Add delay between actions
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--start-maximized',
                '--disable-automation',
                '--disable-infobars',
                '--disable-plugins-discovery',
                '--no-first-run',
                '--user-agent=' + random.choice(self.user_agents)
            ]
        }
        
        # Add proxy configuration if provided
        if proxy:
            launch_options['proxy'] = proxy
            # Hide password in log output
            proxy_info = proxy['server']
            if 'username' in proxy:
                # Extract session info from username if present
                username_parts = proxy['username'].split('-')
                if 'session' in proxy['username']:
                    session_info = [part for part in username_parts if 'session' in part]
                    print(f"  🔐 Using proxy: {proxy_info} ({', '.join(session_info)})")
                elif 'city' in proxy['username']:
                    city_info = [part for part in username_parts if 'city' in part]
                    print(f"  🔐 Using proxy: {proxy_info} ({', '.join(city_info)})")
                else:
                    print(f"  🔐 Using proxy: {proxy_info} (random Canadian IP)")
            else:
                print(f"  🔐 Using proxy: {proxy_info}")
        
        browser = playwright.chromium.launch(**launch_options)
        
        context = browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1920, 'height': 1080},
            locale='en-CA',
            timezone_id='America/Toronto',
            geolocation={'longitude': -75.6972, 'latitude': 45.4215},  # Ottawa
            permissions=['geolocation'],
            extra_http_headers={
                'Accept-Language': 'en-CA,en;q=0.9,fr-CA;q=0.8',
                'X-Forwarded-For': '142.116.0.0',  # Canadian IP range
            }
        )
        
        # Add stealth scripts
        context.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-CA', 'en', 'fr-CA'],
            });
        """)
        
        # Set Google preferences cookie to force Canadian domain
        context.add_cookies([{
            'name': 'PREF',
            'value': 'ID=1234567890:FF=0:LD=en-CA:TM=1234567890:C=CA:LM=1234567890:GM=1:SG=2:S=abcdefghij',
            'domain': '.google.ca',
            'path': '/',
            'expires': -1
        }])
        
        return browser, context

    def verify_ai_overview_element(self, page, element):
        """Perform additional verification that this is truly an AI Overview"""
        if not element:
            return False
            
        try:
            # Check if element is visible
            if not element.is_visible():
                return False
                
            # Get the element's text content
            element_text = element.inner_text()
            if not element_text or 'AI Overview' not in element_text:
                return False
                
            # Additional check: Look for AI Overview specific content indicators
            ai_content_indicators = [
                'Learn more',  # Common in AI overviews
                'Sources include',  # Source attribution
                'generated from',  # Generation indicator
            ]
            
            # Check if any typical AI Overview content is present
            has_ai_content = any(indicator.lower() in element_text.lower() for indicator in ai_content_indicators)
            
            # Also accept if it's just the header with minimal content
            is_ai_header = element.query_selector('h1.VW3apb') is not None
            
            return has_ai_content or is_ai_header
            
        except Exception as e:
            print(f"  ⚠️ Error verifying element: {e}")
            return False

    def detect_ai_overview(self, page):
        """Detect if AI Overview is present on the page using the exact wrapper structure"""
        
        print("  🔍 Checking for AI Overview using specific wrapper div...")
        
        # Primary AI Overview container selectors based on your HTML example
        ai_overview_wrapper_selectors = [
            # The main wrapper div that contains the AI Overview
            'div[data-mcpr=""][class="YzCcne"][data-mg-cp="YzCcne"]',
            
            # Alternative selectors for the wrapper
            'div.YzCcne[data-mg-cp="YzCcne"]',
            
            # The h1 "AI Overview" header as indicator
            'h1.VW3apb:has-text("AI Overview")',
            
            # The combination of wrapper + header
            'div[data-mcpr=""] h1.VW3apb',
            
            # Controller div that contains AI Overview content
            'div[jscontroller="EYwa3d"][jsname="dEwkXc"]',
            
            # More specific path from your HTML
            'div.YzCcne div.hdzaWe h1.VW3apb'
        ]
        
        ai_overview_element = None
        selector_used = None
        
        # First, check for the specific wrapper structure
        for selector in ai_overview_wrapper_selectors:
            try:
                elements = page.query_selector_all(selector)
                print(f"  📋 Trying selector: {selector} - Found {len(elements)} elements")
                
                for element in elements:
                    if element and element.is_visible():
                        # Additional verification - check if it contains "AI Overview" text
                        element_text = element.inner_text() if element.inner_text() else ""
                        
                        if "AI Overview" in element_text:
                            # Additional verification using the new method
                            if self.verify_ai_overview_element(page, element):
                                print(f"  ✅ Found and verified AI Overview wrapper")
                                ai_overview_element = element
                                selector_used = selector
                                return True, selector_used, ai_overview_element
                            else:
                                print(f"  ⚠️ Found 'AI Overview' text but failed additional verification")
                        else:
                            print(f"  ⚠️ Found element but no 'AI Overview' text")
                            
            except Exception as e:
                print(f"  ⚠️ Error with selector {selector}: {e}")
                continue
        
        # Fallback: Check for the H1 with "AI Overview" text specifically
        try:
            h1_elements = page.query_selector_all('h1')
            for h1 in h1_elements:
                if h1.is_visible() and h1.inner_text() and "AI Overview" in h1.inner_text():
                    # Try to get the parent wrapper
                    parent = h1.locator('xpath=ancestor::div[@data-mcpr or contains(@class, "YzCcne")]').first
                    if parent:
                        if self.verify_ai_overview_element(page, parent):
                            print(f"  ✅ Found and verified AI Overview via H1 parent fallback")
                            ai_overview_element = parent
                            selector_used = "h1:has-text('AI Overview') -> parent"
                            return True, selector_used, ai_overview_element
                    else:
                        # Check if the H1 itself passes verification
                        if self.verify_ai_overview_element(page, h1):
                            print(f"  ✅ Found and verified AI Overview via H1 fallback")
                            ai_overview_element = h1
                            selector_used = "h1:has-text('AI Overview')"
                            return True, selector_used, ai_overview_element
        except Exception as e:
            print(f"  ⚠️ H1 fallback failed: {e}")
        
        # Final fallback: Text-based search with stricter criteria
        # NOTE: This should NOT return True since we couldn't find a valid element
        try:
            page_content = page.content()
            ai_indicators = ['<h1 class="VW3apb">AI Overview</h1>', 'AI Overview']
            
            for indicator in ai_indicators:
                if indicator in page_content:
                    print(f"  ⚠️ Found AI Overview text in page content, but no valid element structure - NOT counting as valid AI Overview")
                    # Don't return True here - we need a valid element to screenshot
                    break
        except Exception as e:
            print(f"  ⚠️ Text search failed: {e}")
        
        print(f"  ❌ No AI Overview found on this page")
        return False, None, None

    def expand_ai_overview(self, page, ai_overview_element=None):
        """Expand AI Overview content by clicking 'Show more' buttons"""
        expanded_something = False
        
        print("  🔍 Looking for AI Overview expandable content...")
        
        # Strategy 1: Target the specific AI Overview "Show more" button structure
        ai_overview_expand_selectors = [
            # Exact structure from your example
            '[aria-label="Show more AI Overview"][role="button"]',
            '[jsname="rPRdsc"][aria-label*="Show more"]',
            '[aria-label*="Show more AI Overview"]',
            
            # More generic AI Overview expand patterns
            '[aria-expanded="false"][aria-label*="AI Overview"]',
            '[aria-expanded="false"][aria-label*="Show more"]',
            
            # CSS class based targeting
            '.zNsLfb.Jzkafd[role="button"][aria-expanded="false"]',
            '.lACQkd [role="button"][aria-expanded="false"]',
            
            # JSAction based (Google's click handlers)
            '[jsaction*="trigger.OiPALb"][aria-expanded="false"]',
            '[jsaction*="OiPALb"][role="button"]',
            
            # Text content based with proper structure
            '[role="button"]:has-text("Show more")',
            'div[role="button"]:has-text("Show more")'
        ]
        
        print("  🎯 Searching for AI Overview 'Show more' buttons...")
        
        for selector in ai_overview_expand_selectors:
            try:
                buttons = page.query_selector_all(selector)
                print(f"  🔍 Trying selector: {selector} - Found {len(buttons)} elements")
                
                for button in buttons:
                    if button.is_visible():
                        # Get button details for verification
                        aria_label = button.get_attribute('aria-label') or ""
                        button_text = ""
                        try:
                            button_text = button.inner_text().strip()
                        except:
                            pass
                        
                        print(f"  📋 Button details - ARIA: '{aria_label}', Text: '{button_text}'")
                        
                        # Verify this is actually a "Show more" button for AI Overview
                        is_ai_overview_button = (
                            'show more' in aria_label.lower() and 'ai overview' in aria_label.lower()
                        ) or (
                            'show more' in button_text.lower()
                        ) or (
                            aria_label.lower().startswith('show more') and 
                            button.get_attribute('aria-expanded') == 'false'
                        )
                        
                        if is_ai_overview_button:
                            print(f"  🎯 Found AI Overview expand button: '{aria_label or button_text}'")
                            
                            try:
                                # Scroll to button and ensure it's in view
                                button.scroll_into_view_if_needed()
                                time.sleep(random.uniform(0.5, 1))
                                
                                # Highlight the button for debugging (optional)
                                page.evaluate("""(element) => {
                                    element.style.border = '3px solid red';
                                    element.style.backgroundColor = 'yellow';
                                }""", button)
                                time.sleep(0.5)
                                
                                # Click the button
                                button.click()
                                expanded_something = True
                                
                                # Wait for content to expand
                                time.sleep(random.uniform(2, 4))
                                print(f"  ✅ Successfully expanded AI Overview content!")
                                
                                # Remove highlighting
                                page.evaluate("""(element) => {
                                    element.style.border = '';
                                    element.style.backgroundColor = '';
                                }""", button)
                                
                                return expanded_something
                                
                            except Exception as e:
                                print(f"  ⚠️ Failed to click expand button: {e}")
                                continue
                                
            except Exception as e:
                print(f"  ⚠️ Error with selector {selector}: {e}")
                continue
        
        # Strategy 2: If specific selectors fail, try a more general approach
        if not expanded_something:
            print("  🔄 Trying general approach...")
            try:
                # Look for any button containing "Show more" text
                show_more_buttons = page.query_selector_all('*')
                for element in show_more_buttons:
                    try:
                        if element.get_attribute('role') == 'button' or element.tag_name.lower() == 'button':
                            element_text = element.inner_text().strip().lower() if element.inner_text() else ""
                            aria_label = (element.get_attribute('aria-label') or "").lower()
                            
                            if ('show more' in element_text or 'show more' in aria_label) and element.is_visible():
                                print(f"  🎯 Found potential expand button: '{element_text or aria_label}'")
                                
                                # Check if this might be in an AI Overview context
                                parent_content = ""
                                try:
                                    # Get parent elements to check context
                                    parent = element
                                    for _ in range(5):  # Check up to 5 parent levels
                                        parent = parent.locator('xpath=..')
                                        parent_text = parent.inner_text().lower() if parent else ""
                                        if 'ai' in parent_text or 'overview' in parent_text:
                                            parent_content = parent_text
                                            break
                                except:
                                    pass
                                
                                # If we find AI/overview context or if it's one of the few "Show more" buttons
                                if parent_content or element_text == 'show more':
                                    try:
                                        element.scroll_into_view_if_needed()
                                        time.sleep(0.5)
                                        element.click()
                                        expanded_something = True
                                        time.sleep(random.uniform(2, 4))
                                        print(f"  ✅ Successfully expanded content with general approach!")
                                        return expanded_something
                                    except:
                                        continue
                    except:
                        continue
            except Exception as e:
                print(f"  ⚠️ General approach failed: {e}")
        
        if expanded_something:
            print(f"  🎉 Content expansion completed - waiting for DOM updates...")
            time.sleep(random.uniform(2, 4))
        else:
            print(f"  ℹ️ No expandable AI Overview content found")
        
        return expanded_something

    def search_and_screenshot(self, search_term, browser, context):
        """Perform search and take screenshot if AI overview found"""
        page = context.new_page()
        
        try:
            # Method 1: Direct search URL (bypasses search box entirely)
            search_url = f"https://www.google.ca/search?q={urllib.parse.quote_plus(search_term)}&hl=en-CA&gl=ca&cr=countryCA&lr=lang_en"

            
            print(f"  🌐 Navigating to: {search_url}")
            page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for page to fully load
            time.sleep(random.uniform(3, 6))
            
            # Check if we got blocked or redirected
            current_url = page.url
            print(f"  📍 Current URL: {current_url}")
            
            if 'sorry' in current_url.lower() or 'blocked' in current_url.lower():
                print("  ⚠️ Detected blocking, trying alternative method...")
                
                # Method 2: Try going to google.ca first, then search
                page.goto('https://www.google.ca/?gl=ca&hl=en-CA', timeout=30000)
                time.sleep(random.uniform(2, 4))
                
                # Try multiple search box selectors
                search_selectors = ['input[name="q"]', 'textarea[name="q"]', '[role="combobox"]', '#APjFqb']
                search_box = None
                
                for selector in search_selectors:
                    try:
                        search_box = page.wait_for_selector(selector, timeout=5000)
                        print(f"  ✅ Found search box: {selector}")
                        break
                    except:
                        continue
                
                if search_box:
                    # Human-like typing
                    search_box.click()
                    time.sleep(random.uniform(0.5, 1.5))
                    search_box.type(search_term, delay=random.randint(50, 150))
                    time.sleep(random.uniform(0.5, 2))
                    search_box.press('Enter')
                    time.sleep(random.uniform(3, 5))
                else:
                    raise Exception("Could not find search box with any selector")
            
            # Wait for search results to appear - try multiple selectors
            search_result_selectors = [
                '#search',
                '.g',
                '[data-ved]',
                '#main',
                '.s',
                '#rso'
            ]
            
            results_found = False
            for selector in search_result_selectors:
                try:
                    page.wait_for_selector(selector, timeout=10000)
                    results_found = True
                    print(f"  ✅ Search results loaded (found: {selector})")
                    break
                except:
                    continue
            
            if not results_found:
                # Final fallback: check page content
                page_content = page.content()
                if any(indicator in page_content.lower() for indicator in ['results', 'about', 'web']):
                    results_found = True
                    print("  ✅ Search results detected via content analysis")
                else:
                    # Take a debug screenshot to see what's happening
                    debug_path = self.output_dir / f"debug_{search_term.replace(' ', '_')}.png"
                    page.screenshot(path=str(debug_path))
                    print(f"  🐛 Debug screenshot saved: {debug_path}")
                    raise Exception("Could not find search results on page")
            
            # Additional wait for dynamic content
            time.sleep(random.uniform(2, 4))
            
            # Check for AI Overview
            has_ai_overview, selector_used, ai_overview_element = self.detect_ai_overview(page)
            
            result = {
                'search_term': search_term,
                'has_ai_overview': has_ai_overview,
                'selector_used': selector_used,
                'timestamp': datetime.now().isoformat(),
                'screenshot_path': None,
                'content_expanded': False
            }
            
            # If AI overview found, try to expand it before screenshot
            if has_ai_overview and ai_overview_element is not None:
                print(f"  🎯 AI Overview detected for '{search_term}'")
                
                # Double-check: Verify the element still exists and contains AI Overview text
                try:
                    if ai_overview_element.is_visible():
                        element_text = ai_overview_element.inner_text()
                        if element_text and 'AI Overview' in element_text:
                            print(f"  ✅ Verified AI Overview presence")
                            
                            # Try to expand the content
                            content_expanded = self.expand_ai_overview(page, ai_overview_element)
                            result['content_expanded'] = content_expanded
                            
                            # Take screenshot after expansion attempt
                            screenshot_path = self.output_dir / f"{search_term.replace(' ', '_').replace('/', '_')}_ai_overview.png"
                            
                            # Scroll to AI Overview element
                            ai_overview_element.scroll_into_view_if_needed()
                            time.sleep(1)
                            
                            # Take full page screenshot to capture expanded content
                            page.screenshot(path=str(screenshot_path), full_page=True)
                            result['screenshot_path'] = str(screenshot_path)
                            
                            expansion_status = "with expanded content" if content_expanded else "without expansion"
                            print(f"  ✅ AI Overview screenshot saved {expansion_status}")
                        else:
                            print(f"  ⚠️ Element found but doesn't contain 'AI Overview' text - skipping screenshot")
                            result['has_ai_overview'] = False
                    else:
                        print(f"  ⚠️ AI Overview element not visible - skipping screenshot")
                        result['has_ai_overview'] = False
                except Exception as e:
                    print(f"  ⚠️ Error verifying AI Overview element: {e}")
                    result['has_ai_overview'] = False
            else:
                print(f"  ❌ No AI Overview detected for '{search_term}'")
            
            return result
            
        except Exception as e:
            print(f"❌ Error searching '{search_term}': {str(e)}")
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
        print("🚀 Starting Google AI Overview Analysis for CRA...")
        
        # Read search terms from CSV
        search_terms = []
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader, None)  # Skip header if present
                search_terms = [row[0].strip() for row in reader if row]
        except Exception as e:
            print(f"❌ Error reading CSV file: {e}")
            return
        
        print(f"📊 Found {len(search_terms)} search terms to analyze")
        
        with sync_playwright() as playwright:
            # Get initial proxy
            proxy = self.get_next_proxy() if self.proxies else None
            browser, context = self.setup_browser_context(playwright, proxy)
            
            try:
                for i, term in enumerate(search_terms, 1):
                    print(f"\n🔍 Processing {i}/{len(search_terms)}: '{term}'")
                    
                    try:
                        result = self.search_and_screenshot(term, browser, context)
                        self.results.append(result)
                    except Exception as e:
                        print(f"❌ Error during search: {e}")
                        # If proxy error, try rotating to next proxy
                        if self.proxies and "proxy" in str(e).lower():
                            print("🔄 Proxy error detected, rotating to next proxy...")
                            context.close()
                            browser.close()
                            proxy = self.get_next_proxy()
                            browser, context = self.setup_browser_context(playwright, proxy)
                            # Retry the search with new proxy
                            try:
                                result = self.search_and_screenshot(term, browser, context)
                                self.results.append(result)
                            except Exception as retry_e:
                                print(f"❌ Retry failed: {retry_e}")
                                # Add failed result
                                self.results.append({
                                    'search_term': term,
                                    'has_ai_overview': False,
                                    'selector_used': None,
                                    'timestamp': datetime.now().isoformat(),
                                    'screenshot_path': None,
                                    'error': str(retry_e)
                                })
                        else:
                            # Add failed result for non-proxy errors
                            self.results.append({
                                'search_term': term,
                                'has_ai_overview': False,
                                'selector_used': None,
                                'timestamp': datetime.now().isoformat(),
                                'screenshot_path': None,
                                'error': str(e)
                            })
                    
                    # Random delay between searches (important!)
                    if i < len(search_terms):
                        delay = random.uniform(self.delay_range[0], self.delay_range[1])
                        print(f"⏳ Waiting {delay:.1f} seconds before next search...")
                        time.sleep(delay)
                        
                        # Rotate proxy and refresh context periodically
                        rotation_interval = 10 if self.proxies else 20
                        if i % rotation_interval == 0:
                            print("🔄 Refreshing browser context...")
                            if self.proxies:
                                print("🔄 Rotating to next proxy...")
                            context.close()
                            browser.close()
                            
                            # Get next proxy for rotation
                            proxy = self.get_next_proxy() if self.proxies else None
                            browser, context = self.setup_browser_context(playwright, proxy)
                
            finally:
                context.close()
                browser.close()
        
        # Save results
        self.save_results()
        self.print_summary()

    def save_results(self):
        """Save results to JSON and CSV files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed JSON
        json_file = f"cra_ai_overview_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"💾 Detailed results saved to {json_file}")
        
        # Save summary CSV
        csv_file = f"cra_ai_overview_summary_{timestamp}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Search Term', 'Has AI Overview', 'Content Expanded', 'Screenshot Path', 'Selector Used', 'Timestamp'])
            
            for result in self.results:
                writer.writerow([
                    result['search_term'],
                    result['has_ai_overview'],
                    result.get('content_expanded', False),
                    result.get('screenshot_path', ''),
                    result.get('selector_used', ''),
                    result['timestamp']
                ])
        print(f"📊 Summary CSV saved to {csv_file}")

    def print_summary(self):
        """Print analysis summary"""
        total_terms = len(self.results)
        ai_overview_count = sum(1 for r in self.results if r['has_ai_overview'])
        
        print(f"\n📈 ANALYSIS SUMMARY")
        print(f"=" * 50)
        print(f"Total search terms analyzed: {total_terms}")
        print(f"Terms with AI Overview: {ai_overview_count}")
        print(f"Percentage with AI Overview: {(ai_overview_count/total_terms)*100:.1f}%")
        print(f"Screenshots captured: {ai_overview_count}")
        print(f"Screenshots saved in: {self.output_dir}")


if __name__ == "__main__":
    # Configuration
    CSV_FILE = "cra_search_terms.csv"  # Your CSV file with search terms
    OUTPUT_DIR = "ai_overview_screenshots"
    DELAY_RANGE = (4, 8)  # Random delay between searches (seconds)
    
    # Oxylabs Residential Proxy Configuration
    # Your Oxylabs credentials
    proxy_user = 'customer-naomivk_2kqmu-cc-CA'  
    proxy_pass = 'GeorgieDory2147_3'
    proxy_host = 'pr.oxylabs.io'
    proxy_port = '7777'
    
    # Proxy configuration options:
    # Option 1: Use session IDs for sticky sessions (recommended for consistency)
    PROXIES = [
        f"http://{proxy_user}-session-{i}:{proxy_pass}@{proxy_host}:{proxy_port}"
        for i in range(1, 6)  # Creates 5 different sessions
    ]
    
    # Option 2: Use specific Canadian cities (uncomment to use)
    # PROXIES = [
    #     f"http://{proxy_user}-city-toronto:{proxy_pass}@{proxy_host}:{proxy_port}",
    #     f"http://{proxy_user}-city-montreal:{proxy_pass}@{proxy_host}:{proxy_port}",
    #     f"http://{proxy_user}-city-vancouver:{proxy_pass}@{proxy_host}:{proxy_port}",
    #     f"http://{proxy_user}-city-calgary:{proxy_pass}@{proxy_host}:{proxy_port}",
    #     f"http://{proxy_user}-city-ottawa:{proxy_pass}@{proxy_host}:{proxy_port}",
    # ]
    
    # Option 3: Random Canadian residential IPs (uncomment to use)
    # PROXIES = [
    #     f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
    # ]
    
    # Run the scraper
    scraper = GoogleAIOverviewScraper(
        csv_file=CSV_FILE,
        output_dir=OUTPUT_DIR,
        delay_range=DELAY_RANGE,
        proxies=PROXIES
    )
    
    scraper.run_analysis()
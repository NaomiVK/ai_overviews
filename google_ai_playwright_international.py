#!/usr/bin/env python3
import csv
import time
import random
import json
import urllib.parse
import math
import hashlib
import os
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
        self.session_cookies = {}
        
        # Create cookies directory for proxy-specific persistence
        self.cookies_dir = Path("cookies")
        self.cookies_dir.mkdir(exist_ok=True)
        
        if self.proxies:
            print(f"Proxy configuration loaded: {len(self.proxies)} proxies available")
            print("Will force Canadian search results regardless of proxy location")
        else:
            print("WARNING: No proxies configured - running without proxy")
        
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        ]
        
        self.viewports = [
            {'width': 1920, 'height': 1080},
            {'width': 1366, 'height': 768},
            {'width': 1536, 'height': 864},
            {'width': 1440, 'height': 900},
            {'width': 1600, 'height': 900},
            {'width': 1280, 'height': 720},
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
                print(f"  Using proxy session {self.current_proxy_index}/{len(self.proxies)}")
                return proxy_dict
        return proxy_config

    def get_proxy_hash(self, proxy_config):
        """Generate a unique hash for proxy identity to tie cookies to specific proxies"""
        if not proxy_config:
            return "no_proxy"
        
        # Create a consistent hash based on proxy server details
        if isinstance(proxy_config, dict):
            proxy_string = f"{proxy_config.get('server', '')}{proxy_config.get('username', '')}"
        else:
            proxy_string = str(proxy_config)
        
        # Generate SHA256 hash for consistent proxy identity
        proxy_hash = hashlib.sha256(proxy_string.encode()).hexdigest()[:16]
        return proxy_hash

    def load_proxy_cookies(self, context, proxy_hash):
        """Load cookies for this specific proxy identity"""
        try:
            cookie_file = self.cookies_dir / f"{proxy_hash}.json"
            if cookie_file.exists():
                with open(cookie_file, "r") as f:
                    cookies = json.load(f)
                    context.add_cookies(cookies)
                    print(f"  Loaded {len(cookies)} cookies for proxy {proxy_hash[:8]}...")
                    return True
            else:
                print(f"  No existing cookies for proxy {proxy_hash[:8]}...")
                return False
        except Exception as e:
            print(f"  Error loading cookies for proxy {proxy_hash[:8]}...: {e}")
            return False

    def save_proxy_cookies(self, context, proxy_hash):
        """Save cookies for this specific proxy identity"""
        try:
            cookies = context.cookies()
            cookie_file = self.cookies_dir / f"{proxy_hash}.json"
            with open(cookie_file, "w") as f:
                json.dump(cookies, f)
            print(f"  Saved {len(cookies)} cookies for proxy {proxy_hash[:8]}...")
        except Exception as e:
            print(f"  Error saving cookies for proxy {proxy_hash[:8]}...: {e}")

    def setup_browser_context(self, playwright, proxy=None):
        """Setup browser with Canadian localization and randomized fingerprints"""
        user_agent = random.choice(self.user_agents)
        viewport = random.choice(self.viewports)
        
        # Generate proxy hash for cookie persistence
        proxy_hash = self.get_proxy_hash(proxy)
        print(f"  Using proxy identity: {proxy_hash[:8]}...")
        
        # Use Chrome with stealth settings - more reliable than Firefox
        chrome_args = [
            '--disable-blink-features=AutomationControlled',
            '--exclude-switches=enable-automation',
            '--disable-extensions-except=/path/to/extension',
            '--disable-plugins-discovery',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu-sandbox',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-field-trial-config',
            '--disable-back-forward-cache',
            '--disable-ipc-flooding-protection',
            '--disable-features=TranslateUI,BlinkGenPropertyTrees',
            '--disable-component-extensions-with-background-pages',
            '--no-default-browser-check',
            '--disable-default-apps',
            '--disable-breakpad',
            '--disable-component-update',
            '--disable-domain-reliability',
            '--disable-sync',
            '--metrics-recording-only',
            '--no-report-upload',
            '--disable-web-security',
            '--disable-webrtc',
            '--disable-webrtc-encryption',
            f'--window-size={viewport["width"]},{viewport["height"]}',
        ]
        
        launch_options = {
            'headless': False,  # Always use headful browser - much harder to detect
            'slow_mo': random.randint(100, 300),  # Slower human-like delays to all actions
            'args': chrome_args
        }
        
        if proxy:
            launch_options['proxy'] = proxy
        
        # Use Chrome with persistent context for better stealth
        try:
            browser = playwright.chromium.launch(**launch_options)
            print("  Using Chrome with advanced stealth settings")
        except Exception as e:
            print(f"  ERROR launching Chrome: {e}")
            # Fallback with minimal args
            minimal_options = {
                'headless': False,
                'slow_mo': random.randint(100, 300),
                'args': ['--disable-blink-features=AutomationControlled']
            }
            if proxy:
                minimal_options['proxy'] = proxy
            browser = playwright.chromium.launch(**minimal_options)
            print("  Using Chrome with minimal settings (fallback)")
        
        # FORCE CANADIAN CONTEXT with randomized fingerprints
        context = browser.new_context(
            user_agent=user_agent,
            viewport=viewport,
            locale='en-CA',
            timezone_id='America/Toronto',
            geolocation={'longitude': -79.3832, 'latitude': 43.6532},
            permissions=['geolocation'],
            extra_http_headers={
                'Accept-Language': 'en-CA,en-US;q=0.9,en;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'max-age=0',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            }
        )
        
        context.set_default_navigation_timeout(45000)
        context.set_default_timeout(45000)
        
        # Load existing cookies for this proxy identity
        self.load_proxy_cookies(context, proxy_hash)
        
        # Block resources
        context.route("**/*.{png,jpg,jpeg,gif,svg,ico,css}", lambda route: route.abort())
        
        # Apply stealth techniques before any page loads
        context.add_init_script("""
            // Completely hide automation traces
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                enumerable: true,
                configurable: true
            });
            
            // Remove automation properties
            const props = ['__webdriver_evaluate', '__selenium_evaluate', '__webdriver_script_function', '__webdriver_script_func', '__webdriver_script_fn', '__fxdriver_evaluate', '__driver_unwrapped', '__webdriver_unwrapped', '__driver_evaluate', '__selenium_unwrapped', '__fxdriver_unwrapped'];
            props.forEach(prop => delete Object.getPrototypeOf(navigator)[prop]);
            
            // Override Object.getOwnPropertyDescriptor to hide traces
            const originalGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
            Object.getOwnPropertyDescriptor = function(obj, prop) {
                if (prop === 'webdriver') {
                    return undefined;
                }
                return originalGetOwnPropertyDescriptor(obj, prop);
            };
            
            // Spoof chrome object completely
            if (!window.chrome) {
                window.chrome = {};
            }
            
            if (!window.chrome.runtime) {
                window.chrome.runtime = {
                    onConnect: undefined,
                    onMessage: undefined,
                    connect: function() { return {}; },
                    sendMessage: function() { return {}; }
                };
            }
            
            // Mock notification permission
            Object.defineProperty(Notification, 'permission', {
                get: () => 'default'
            });
            
            // Realistic plugin enumeration
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    const plugins = [
                        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: 'Portable Document Format' },
                        { name: 'Native Client', filename: 'internal-nacl-plugin', description: 'Native Client' }
                    ];
                    return Object.assign(plugins, {
                        item: i => plugins[i],
                        namedItem: name => plugins.find(p => p.name === name),
                        refresh: () => {}
                    });
                }
            });
            
            // Spoof iframe contentWindow
            const originalContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
            Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
                get: function() {
                    const win = originalContentWindow.get.call(this);
                    if (win) {
                        try {
                            win.navigator.webdriver = undefined;
                        } catch(e) {}
                    }
                    return win;
                }
            });
        """)
        
        # Advanced fingerprint randomization
        context.add_init_script(f"""
            // Remove webdriver property completely
            Object.defineProperty(navigator, 'webdriver', {{
                get: () => undefined,
                set: () => {{}}
            }});
            
            // Remove all automation indicators
            delete navigator.__webdriver_script_fn;
            delete navigator.__webdriver_evaluate;
            delete navigator.__webdriver_unwrapped;
            delete navigator.__fxdriver_evaluate;
            delete navigator.__fxdriver_unwrapped;
            delete navigator.__driver_evaluate;
            delete navigator.__selenium_evaluate;
            delete navigator.__selenium_unwrapped;
            
            // Remove Chrome automation flags
            if (window.chrome && window.chrome.runtime) {{
                Object.defineProperty(window.chrome.runtime, 'onConnect', {{
                    get: () => undefined
                }});
            }}
            
            // Set Canadian language preferences
            Object.defineProperty(navigator, 'language', {{
                get: () => 'en-CA'
            }});
            Object.defineProperty(navigator, 'languages', {{
                get: () => ['en-CA', 'en-US', 'en']
            }});
            
            // Randomize hardware specs with realistic values
            Object.defineProperty(navigator, 'hardwareConcurrency', {{
                get: () => {random.randint(4, 16)}
            }});
            
            Object.defineProperty(navigator, 'deviceMemory', {{
                get: () => {random.choice([4, 8, 16])}
            }});
            
            // Realistic plugins array
            Object.defineProperty(navigator, 'plugins', {{
                get: () => {{
                    const plugins = [
                        {{name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format'}},
                        {{name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: 'Portable Document Format'}},
                        {{name: 'Native Client', filename: 'internal-nacl-plugin', description: 'Native Client'}}
                    ];
                    return {{
                        length: plugins.length,
                        ...plugins,
                        item: (index) => plugins[index],
                        namedItem: (name) => plugins.find(p => p.name === name)
                    }};
                }}
            }});
            
            // Spoof WebGL renderer with realistic values
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                const renderers = ['Intel(R) UHD Graphics 630', 'NVIDIA GeForce GTX 1060', 'AMD Radeon RX 580'];
                const vendors = ['Intel Inc.', 'NVIDIA Corporation', 'AMD'];
                if (parameter === 37445) return vendors[Math.floor(Math.random() * vendors.length)];
                if (parameter === 37446) return renderers[Math.floor(Math.random() * renderers.length)];
                return getParameter.call(this, parameter);
            }};
            
            // Override screen properties
            Object.defineProperty(screen, 'colorDepth', {{
                get: () => {random.choice([24, 30, 32])}
            }});
            
            // Spoof canvas fingerprinting with slight variations
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {{
                const shift = Math.floor(Math.random() * 3) - 1;
                const context = this.getContext('2d');
                if (context) {{
                    const imageData = context.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {{
                        imageData.data[i] = Math.min(255, Math.max(0, imageData.data[i] + shift));
                    }}
                    context.putImageData(imageData, 0, 0);
                }}
                return originalToDataURL.call(this, type);
            }};
            
            // Mock realistic connection
            Object.defineProperty(navigator, 'connection', {{
                get: () => ({{
                    downlink: {random.uniform(1.5, 10.0)},
                    effectiveType: '4g',
                    rtt: {random.randint(50, 150)}
                }})
            }});
            
            // Mock permissions API
            const originalQuery = navigator.permissions.query;
            navigator.permissions.query = function(permissionDesc) {{
                return Promise.resolve({{
                    state: Math.random() > 0.5 ? 'granted' : 'prompt'
                }});
            }};
            
            // Advanced mouse tracking
            window.mouseX = Math.floor(Math.random() * {viewport['width']});
            window.mouseY = Math.floor(Math.random() * {viewport['height']});
            let mouseMovements = 0;
            let lastMouseMove = Date.now();
            
            document.addEventListener('mousemove', (e) => {{
                window.mouseX = e.clientX;
                window.mouseY = e.clientY;
                mouseMovements++;
                lastMouseMove = Date.now();
            }});
            
            // Simulate realistic performance timing variations
            const originalNow = performance.now;
            performance.now = function() {{
                return originalNow.call(this) + Math.random() * 0.1;
            }};
            
            // Add realistic error handling
            window.addEventListener('error', (e) => {{
                // Suppress some automation-related errors
                if (e.message && e.message.includes('webdriver')) {{
                    e.preventDefault();
                    return false;
                }}
            }});
            
            // Enhanced WebRTC and media device spoofing
            Object.defineProperty(navigator, 'mediaDevices', {{
                get: () => ({{
                    enumerateDevices: () => Promise.resolve([
                        {{deviceId: 'default', kind: 'audioinput', label: 'Default - Microphone'}},
                        {{deviceId: 'default', kind: 'audiooutput', label: 'Default - Speaker'}},
                        {{deviceId: 'camera1', kind: 'videoinput', label: 'Integrated Camera'}}
                    ]),
                    getUserMedia: () => Promise.reject(new Error('Permission denied')),
                    getDisplayMedia: () => Promise.reject(new Error('Permission denied'))
                }})
            }});
            
            // Block WebRTC completely - prevent IP leakage
            Object.defineProperty(window, 'RTCPeerConnection', {{
                get: () => undefined
            }});
            Object.defineProperty(window, 'webkitRTCPeerConnection', {{
                get: () => undefined
            }});
            Object.defineProperty(window, 'mozRTCPeerConnection', {{
                get: () => undefined
            }});
            
            // Block additional WebRTC APIs
            Object.defineProperty(window, 'RTCDataChannel', {{
                get: () => undefined
            }});
            Object.defineProperty(window, 'RTCSessionDescription', {{
                get: () => undefined
            }});
            Object.defineProperty(window, 'RTCIceCandidate', {{
                get: () => undefined
            }});
            
            // Add realistic window focus/blur event listeners
            window.addEventListener('blur', () => {{
                // Simulate user switching away from tab
                console.log('Tab lost focus - user multitasking');
            }});
            window.addEventListener('focus', () => {{
                // Simulate user returning to tab
                console.log('Tab gained focus - user returned');
            }});
            
            // Track focus state for realistic behavior
            window.isTabFocused = true;
            window.addEventListener('blur', () => {{ window.isTabFocused = false; }});
            window.addEventListener('focus', () => {{ window.isTabFocused = true; }});
        """)
        
        # Note: Proxy-specific cookies are already loaded above
        # Old session_cookies system is now replaced with proxy-specific persistence
        
        return browser, context, proxy_hash

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

    def human_mouse_move(self, page, x, y):
        """Simulate human-like mouse movement with curves"""
        current_pos = page.evaluate("() => ({ x: window.mouseX || 0, y: window.mouseY || 0 })")
        start_x, start_y = current_pos.get('x', 0), current_pos.get('y', 0)
        
        # Calculate distance and steps
        distance = math.sqrt((x - start_x)**2 + (y - start_y)**2)
        steps = max(5, int(distance / 10))
        
        # Add random curve to movement
        for i in range(steps):
            progress = i / steps
            # Bezier curve for natural movement
            curve_x = start_x + (x - start_x) * progress + random.uniform(-5, 5) * (1 - progress)
            curve_y = start_y + (y - start_y) * progress + random.uniform(-5, 5) * (1 - progress)
            
            page.mouse.move(curve_x, curve_y)
            time.sleep(random.uniform(0.01, 0.03))
        
        # Final position
        page.mouse.move(x, y)
        page.evaluate(f"window.mouseX = {x}; window.mouseY = {y}")

    def random_scroll(self, page):
        """Perform random scrolling behavior"""
        scroll_actions = [
            lambda: page.mouse.wheel(0, random.randint(100, 300)),  # Scroll down
            lambda: page.mouse.wheel(0, -random.randint(50, 150)),  # Scroll up
            lambda: page.evaluate("window.scrollTo({ top: Math.random() * 500, behavior: 'smooth' })"),
            lambda: page.evaluate("window.scrollBy({ top: 200, behavior: 'smooth' })"),
        ]
        
        # Random number of scroll actions
        for _ in range(random.randint(1, 3)):
            action = random.choice(scroll_actions)
            action()
            time.sleep(random.uniform(0.5, 1.5))

    def simulate_human_clicks(self, page):
        """Simulate random human-like clicks on page elements"""
        try:
            # Get clickable elements (but not critical ones)
            clickable_selectors = [
                'div[role="button"]:not([data-ved])',  # Avoid search result clicks
                'span:not([class*="search"]):not([class*="result"])',
                'div:not([class*="search"]):not([class*="result"]):not([data-ved])',
            ]
            
            for selector in clickable_selectors:
                elements = page.query_selector_all(selector)
                if elements and len(elements) > 0:
                    # Click 1-2 random safe elements
                    safe_elements = [e for e in elements[:10] if e.is_visible()]
                    if safe_elements:
                        element = random.choice(safe_elements)
                        box = element.bounding_box()
                        if box:
                            click_x = box['x'] + box['width'] / 2 + random.uniform(-10, 10)
                            click_y = box['y'] + box['height'] / 2 + random.uniform(-10, 10)
                            
                            self.human_mouse_move(page, click_x, click_y)
                            time.sleep(random.uniform(0.1, 0.3))
                            page.mouse.click(click_x, click_y)
                            time.sleep(random.uniform(0.5, 1.0))
                            break
        except Exception as e:
            pass  # Ignore click simulation errors

    def simulate_typing_behavior(self, page, text):
        """Simulate human typing with random speed and occasional errors"""
        # Try multiple search box selectors
        search_selectors = [
            'input[name="q"]',
            'textarea[name="q"]', 
            'input[title="Search"]',
            'input[aria-label*="Search"]',
            'input[type="text"]',
            '#APjFqb',  # Google's search input ID
        ]
        
        search_box = None
        for selector in search_selectors:
            search_box = page.query_selector(selector)
            if search_box and search_box.is_visible():
                break
        
        if not search_box:
            print("  WARNING: No search box found")
            return False
        
        try:
            # Try multiple click methods to handle intercepting elements
            print("  Focusing on search box...")
            
            # Method 1: Try regular click
            try:
                search_box.click(timeout=10000)
            except:
                # Method 2: Force click to bypass intercepting elements
                try:
                    search_box.click(force=True)
                except:
                    # Method 3: Focus without clicking
                    search_box.focus()
            
            # Wait for search box to be ready
            time.sleep(random.uniform(0.3, 0.8))
            
            # Clear existing text with multiple methods
            try:
                page.keyboard.press('Control+a')
                time.sleep(0.1)
                page.keyboard.press('Delete')
            except:
                # Fallback: clear field directly
                search_box.fill('')
                
        except Exception as e:
            print(f"  WARNING: Search box interaction failed: {e}")
            return False
        
        # Type with human-like behavior
        print(f"  Typing: {text}")
        typed_text = ""
        
        try:
            for i, char in enumerate(text):
                # Random typing speed
                typing_delay = random.uniform(0.05, 0.15)
                
                # Occasional typos (3% chance)
                if random.random() < 0.03 and char.isalpha():
                    # Type wrong character then correct it
                    wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                    try:
                        page.keyboard.type(wrong_char, delay=typing_delay)
                        time.sleep(random.uniform(0.1, 0.3))
                        page.keyboard.press('Backspace')
                        time.sleep(random.uniform(0.05, 0.1))
                    except:
                        pass  # Skip typo if it fails
                
                # Type correct character
                try:
                    page.keyboard.type(char, delay=typing_delay)
                    typed_text += char
                    
                    # Random pauses (10% chance)
                    if random.random() < 0.1:
                        time.sleep(random.uniform(0.2, 0.5))
                        
                except Exception as e:
                    print(f"  WARNING: Typing char '{char}' failed: {e}")
                    # Fallback: use fill method
                    search_box.fill(text)
                    break
            
            print(f"  Successfully typed: {typed_text}")
            return True
            
        except Exception as e:
            print(f"  ERROR: Typing failed: {e}")
            # Ultimate fallback
            try:
                search_box.fill(text)
                print(f"  Fallback: Used fill method")
                return True
            except:
                return False

    def browse_other_pages(self, page):
        """Simulate browsing behavior by visiting other Google pages"""
        other_pages = [
            'https://www.google.com/imghp',  # Images
            'https://news.google.com',       # News
            'https://www.google.com/maps',   # Maps
            'https://www.youtube.com',       # YouTube (Google owned)
            'https://www.google.com/shopping', # Shopping
        ]
        
        if random.random() < 0.4:  # 40% chance to browse other pages
            other_page = random.choice(other_pages)
            print(f"  Browsing {other_page.split('/')[-1]} to appear natural")
            
            try:
                page.goto(other_page, timeout=15000)
                time.sleep(random.uniform(3, 8))  # Longer browsing time
                
                # More realistic browsing behavior
                for _ in range(random.randint(2, 4)):
                    self.random_scroll(page)
                    time.sleep(random.uniform(1, 3))
                    
                    # Sometimes click on elements
                    if random.random() < 0.3:
                        self.simulate_human_clicks(page)
                        time.sleep(random.uniform(1, 2))
                
                # Sometimes do a quick search on the other page
                if random.random() < 0.2 and 'google.com' in other_page:
                    search_terms = ['weather', 'news', 'time', 'calendar']
                    quick_search = random.choice(search_terms)
                    search_box = page.query_selector('input[name="q"], textarea[name="q"]')
                    if search_box:
                        search_box.click()
                        time.sleep(random.uniform(0.5, 1.0))
                        search_box.type(quick_search, delay=random.uniform(0.1, 0.2))
                        time.sleep(random.uniform(1, 2))
                        page.keyboard.press('Enter')
                        time.sleep(random.uniform(2, 4))
                
            except:
                pass  # Ignore navigation errors

    def simulate_alt_tab(self, page):
        """Simulate alt-tabbing out and back in to mimic natural user behavior"""
        try:
            print("  Simulating alt-tab (user multitasking)...")
            
            # Simulate losing focus (alt-tab away)
            page.evaluate("""
                window.dispatchEvent(new Event('blur'));
                document.dispatchEvent(new Event('visibilitychange'));
                Object.defineProperty(document, 'hidden', {value: true, writable: true});
                Object.defineProperty(document, 'visibilityState', {value: 'hidden', writable: true});
            """)
            
            # Stay "away" for realistic time (3-15 seconds)
            away_time = random.uniform(3, 15)
            print(f"  Away from tab for {away_time:.1f} seconds")
            time.sleep(away_time)
            
            # Simulate returning focus (alt-tab back)
            page.evaluate("""
                Object.defineProperty(document, 'hidden', {value: false, writable: true});
                Object.defineProperty(document, 'visibilityState', {value: 'visible', writable: true});
                document.dispatchEvent(new Event('visibilitychange'));
                window.dispatchEvent(new Event('focus'));
            """)
            
            print("  Returned to tab")
            
            # Brief pause as user refocuses
            time.sleep(random.uniform(0.5, 2.0))
            
        except Exception as e:
            print(f"  Alt-tab simulation failed: {e}")

    def save_session_cookies(self, context, proxy_hash=None):
        """Save cookies for session persistence - now uses proxy-specific storage"""
        if proxy_hash:
            self.save_proxy_cookies(context, proxy_hash)
        else:
            # Fallback to old method if no proxy hash provided
            try:
                cookies = context.cookies()
                self.session_cookies = {'cookies': cookies}
                print("  Session cookies saved (legacy method)")
            except:
                pass

    def check_for_captcha_or_blocks(self, page):
        """Check if Google is showing CAPTCHA or blocking page"""
        try:
            current_url = page.url
            
            # Priority check: sorry/index URL (most reliable indicator)
            if current_url.startswith('https://www.google.com/sorry/index'):
                print(f"  🚨 SORRY PAGE URL DETECTED: {current_url}")
                print("  🔄 Will restart with new proxy and retry same search term")
                return 'sorry_page'
            
            # Secondary checks for other sorry URLs
            if 'sorry/index' in current_url or 'sorry.google.com' in current_url:
                print(f"  🚨 SORRY PAGE DETECTED: {current_url}")
                print("  🔄 Will restart with new proxy and retry same search term")
                return 'sorry_page'
            
            # Check for CAPTCHA elements
            captcha_selectors = [
                'form[action*="sorry"]',
                '#captcha-form',
                'input[name="captcha"]',
                '.g-recaptcha',
                '[src*="recaptcha"]'
            ]
            
            for selector in captcha_selectors:
                if page.query_selector(selector):
                    print("  🚨 CAPTCHA FORM DETECTED - Will restart with new proxy")
                    return 'captcha'
            
            # Check for unusual traffic messages
            try:
                page_content = page.content().lower()
                if 'unusual traffic' in page_content or 'automated queries' in page_content:
                    print("  🚨 UNUSUAL TRAFFIC MESSAGE DETECTED - Will restart with new proxy")
                    return 'unusual_traffic'
            except:
                pass
                
            return None
            
        except Exception as e:
            print(f"  DEBUG: Error checking for blocks: {e}")
            return None
    
    def handle_captcha_restart(self, browser, context, playwright):
        """Handle CAPTCHA detection by restarting with new proxy"""
        try:
            print("  🔄 CAPTCHA/BLOCK DETECTED - Restarting session...")
            
            # Close current browser session
            context.close()
            browser.close()
            print("  ✅ Closed blocked session")
            
            # Wait before restarting (avoid immediate retry)
            restart_delay = random.uniform(30, 90)  # 30 seconds to 1.5 minutes
            print(f"  ⏳ Waiting {restart_delay:.1f} seconds before restart...")
            time.sleep(restart_delay)
            
            # Get new proxy
            new_proxy = self.get_next_proxy()
            print(f"  🔄 Switching to new proxy session")
            
            # Create new browser session
            new_browser, new_context, new_proxy_hash = self.setup_browser_context(playwright, new_proxy)
            print("  ✅ New session created successfully")
            
            return new_browser, new_context, new_proxy_hash
            
        except Exception as e:
            print(f"  ❌ Error during restart: {e}")
            raise e

    def detect_ai_overview(self, page):
        """Detect AI Overview with smart DOM waiting"""
        print("  Checking for AI Overview...")
        
        # Smart wait for Google search results to load
        try:
            # Wait for search results container - more reliable than static timeout
            page.wait_for_selector("div.g, #search, #rso", timeout=30000)
            print("  Search results loaded successfully")
        except:
            print("  WARNING: Search results took longer than expected to load")
        
        # Check for blocks/CAPTCHA after page loads
        block_type = self.check_for_captcha_or_blocks(page)
        if block_type:
            return False, f"blocked_{block_type}", None
        
        # Additional wait for dynamic content (AI Overview loads after initial results)
        time.sleep(random.uniform(2, 4))
        
        ai_overview_selectors = [
            'h1:has-text("AI Overview")',
            'div:has-text("AI Overview"):not([aria-hidden="true"])',
            'div.YzCcne',
            'h1.VW3apb',
            # New selectors from provided HTML
            'div[jsname="cUzNTd"]',
            '.Fzsovc',
            '.s7d4ef .f5cPye',
            'div.nk9vdc svg.fWWlmf',  # AI sparkle icon
            'span[data-huuid]',
            'mark.QVRyCf',  # Highlighted information
            '.s7d4ef',  # Main AI Overview container
        ]
        
        for selector in ai_overview_selectors:
            try:
                elements = page.query_selector_all(selector)
                for element in elements:
                    if element and element.is_visible():
                        text = element.inner_text()
                        if text and "AI Overview" in text:
                            print(f"  SUCCESS: Found AI Overview")
                            return True, selector, element
            except:
                continue
        
        print(f"  FAILED: No AI Overview found")
        return False, None, None

    def extract_ai_overview_content(self, page):
        """Extract comprehensive AI Overview content using the selectors you provided"""
        try:
            # Target the main AI Overview container
            ai_container = page.query_selector('.s7d4ef .f5cPye')
            if not ai_container:
                return None
            
            # Extract all text content from data-huuid spans
            text_segments = page.evaluate('''
                Array.from(document.querySelectorAll('span[data-huuid] span'))
                  .map(span => span.textContent.trim())
                  .filter(text => text.length > 0)
            ''')
            
            # Get highlighted information specifically
            highlighted_info = page.evaluate('''
                document.querySelector('mark.QVRyCf')?.textContent
            ''')
            
            return {
                'text_segments': text_segments,
                'highlighted_info': highlighted_info,
                'full_text': ' '.join(text_segments) if text_segments else None
            }
            
        except Exception as e:
            print(f"  WARNING: Error extracting AI Overview content: {e}")
            return None

    def click_show_more_ai_overview(self, page):
        """Click 'Show more' button to expand AI Overview content"""
        show_more_selectors = [
            'div[jsname="rPRdsc"][aria-label="Show more AI Overview"]',  # Most specific and reliable
            '[aria-label="Show more AI Overview"]',  # Aria label fallback
            'div[jsname="rPRdsc"]',                  # Container from your HTML
            'div.lACQkd div[role="button"]',         # Container + role
            '[role="button"][aria-expanded="false"]', # Collapsed state
            'span.clOx1e:has-text("Show more")',     # Text-based
            '[role="button"]:has-text("Show more")', # Role-based
            'div.in7vHe',                            # Inner container
        ]
        
        print(f"  DEBUG: Looking for 'Show more' button...")
        
        for i, selector in enumerate(show_more_selectors):
            try:
                print(f"  DEBUG: Trying selector {i+1}: {selector}")
                elements = page.query_selector_all(selector)
                print(f"  DEBUG: Found {len(elements)} elements with this selector")
                
                for j, element in enumerate(elements):
                    if element and element.is_visible():
                        # Get text content for verification
                        try:
                            text = element.inner_text().lower()
                            aria_label = element.get_attribute('aria-label') or ""
                            print(f"  DEBUG: Element {j+1} text: '{text}', aria-label: '{aria_label}'")
                        except:
                            text = ""
                            aria_label = ""
                        
                        # Check if this looks like a show more button
                        is_show_more = (
                            'show more' in text or 
                            'show more' in aria_label.lower() or
                            (selector == 'div[jsname="rPRdsc"]' and element.get_attribute('aria-label')) or
                            ('more' in text and len(text) < 20)  # Short text with "more"
                        )
                        
                        if is_show_more:
                            print(f"  Found 'Show more' button with selector: {selector}")
                            
                            # Check if element is actually clickable
                            try:
                                box = element.bounding_box()
                                if box:
                                    print(f"  DEBUG: Button position: x={box['x']}, y={box['y']}, width={box['width']}, height={box['height']}")
                                    
                                    # Scroll element into view first
                                    element.scroll_into_view_if_needed()
                                    time.sleep(0.5)
                                    
                                    # Try clicking with different methods
                                    try:
                                        # Method 1: Direct element click
                                        element.click()
                                        print(f"  SUCCESS: Clicked 'Show more' using element.click()")
                                    except:
                                        # Method 2: Force click
                                        element.click(force=True)
                                        print(f"  SUCCESS: Clicked 'Show more' using force click")
                                    
                                    # Wait for content to expand and verify
                                    time.sleep(random.uniform(2, 4))
                                    
                                    # Check if aria-expanded changed
                                    new_aria_expanded = element.get_attribute('aria-expanded')
                                    print(f"  DEBUG: aria-expanded after click: {new_aria_expanded}")
                                    
                                    return True
                                else:
                                    print(f"  DEBUG: No bounding box for element")
                            except Exception as click_error:
                                print(f"  DEBUG: Click error: {click_error}")
                                continue
                
            except Exception as e:
                print(f"  DEBUG: Error with selector {selector}: {e}")
                continue
        
        # Try a more general approach - look for any clickable element with "Show more" text
        try:
            print(f"  DEBUG: Trying general approach...")
            all_clickables = page.query_selector_all('[role="button"], button, a, div[onclick], span[onclick]')
            print(f"  DEBUG: Found {len(all_clickables)} clickable elements")
            
            for element in all_clickables:
                if element and element.is_visible():
                    text = element.inner_text().lower()
                    if 'show more' in text:
                        print(f"  Found 'Show more' via general search: '{text}'")
                        element.click()
                        time.sleep(random.uniform(2, 4))
                        print(f"  SUCCESS: Clicked 'Show more' via general search")
                        return True
        except Exception as e:
            print(f"  DEBUG: Error in general approach: {e}")
        
        print(f"  INFO: No 'Show more' button found - AI Overview may already be fully expanded")
        return False

    def search_and_screenshot(self, search_term, browser, context, proxy_hash=None):
        """Perform search with human-like behavior"""
        page = context.new_page()
        
        try:
            print(f"  Searching: {search_term}")
            print(f"  Forcing Canadian results with parameters")
            
            # Sometimes browse other pages first to appear natural
            self.browse_other_pages(page)
            
            # Start with a more realistic browsing session
            print("  Starting realistic browsing session")
            
            # First visit a non-Google site to establish normal browsing
            normal_sites = [
                'https://www.wikipedia.org',
                'https://www.bbc.com', 
                'https://www.cbc.ca',
                'https://www.reddit.com'
            ]
            
            if random.random() < 0.7:  # 70% chance to visit normal site first
                normal_site = random.choice(normal_sites)
                try:
                    print(f"  Visiting {normal_site} first to establish normal browsing")
                    page.goto(normal_site, timeout=30000)
                    time.sleep(random.uniform(5, 12))
                    
                    # Do some realistic browsing
                    self.random_scroll(page)
                    time.sleep(random.uniform(2, 5))
                    
                    if random.random() < 0.3:
                        self.simulate_human_clicks(page)
                        time.sleep(random.uniform(2, 4))
                        
                except:
                    pass
            
            # Now go to Google homepage
            print("  Loading Google homepage")
            page.goto('https://www.google.com', timeout=30000)
            time.sleep(random.uniform(3, 8))  # Longer pause to read/think
            
            # Simulate human typing in search box
            print("  Typing search query with human behavior")
            typing_success = self.simulate_typing_behavior(page, search_term)
            
            if not typing_success:
                print("  Typing failed - using direct URL approach")
                # Fallback to direct URL if typing fails
                search_url = self.build_canadian_search_url(search_term)
                response = page.goto(search_url, wait_until='domcontentloaded', timeout=45000)
            else:
                # Add search parameters via URL manipulation after typing
                page.evaluate('''
                    const url = new URL(window.location);
                    url.searchParams.set('gl', 'ca');
                    url.searchParams.set('hl', 'en-CA');
                    url.searchParams.set('cr', 'countryCA');
                    url.searchParams.set('lr', 'lang_en');
                    url.searchParams.set('pws', '0');
                ''')
                
                # Press Enter to search
                time.sleep(random.uniform(0.5, 1.5))
                page.keyboard.press('Enter')
                
                # Smart wait for search results instead of static timeout
                try:
                    page.wait_for_selector("div.g, #search, #rso", timeout=45000)
                    print("  Search completed successfully")
                except:
                    print("  WARNING: Search results slow to load")
                
                response = None  # No response object when using keyboard search
            
            if response and response.status == 429:
                print(f"  WARNING: Rate limited (429)")
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
                    print(f"  SUCCESS: Confirmed Canadian results")
            except:
                pass
            
            # Human-like behavior after page loads
            time.sleep(random.uniform(2, 4))
            
            # Simulate natural scrolling and interactions
            print("  Simulating human browsing behavior")
            self.random_scroll(page)
            time.sleep(random.uniform(1, 2))
            
            # Occasional mouse movements and clicks
            if random.random() < 0.4:  # 40% chance
                self.simulate_human_clicks(page)
            
            # More scrolling to view content
            self.random_scroll(page)
            time.sleep(random.uniform(1, 3))
            
            # Check for AI Overview (this also checks for CAPTCHA/blocks)
            has_ai_overview, selector_used, ai_overview_element = self.detect_ai_overview(page)
            
            # Handle detection of blocks/CAPTCHA - return special code to trigger restart
            if selector_used and selector_used.startswith('blocked_'):
                block_type = selector_used.replace('blocked_', '')
                print(f"  BLOCKED: Google detected automation ({block_type})")
                return {
                    'search_term': search_term,
                    'has_ai_overview': False,
                    'selector_used': selector_used,
                    'content_expanded': False,
                    'ai_content': None,
                    'timestamp': datetime.now().isoformat(),
                    'screenshot_path': None,
                    'error': f'Blocked by Google: {block_type}',
                    'restart_needed': True  # Signal for restart
                }
            
            # If AI Overview found, try to expand it by clicking "Show more"
            expanded_content = False
            if has_ai_overview:
                expanded_content = self.click_show_more_ai_overview(page)
                # Additional scroll after expansion to make sure everything is visible
                if expanded_content:
                    self.random_scroll(page)
                    time.sleep(random.uniform(1, 2))
            
            # Extract detailed AI Overview content if found
            ai_content = None
            if has_ai_overview:
                ai_content = self.extract_ai_overview_content(page)
                if ai_content:
                    print(f"  Extracted AI content: {len(ai_content.get('text_segments', []))} segments")
                    if expanded_content:
                        print(f"  Content was expanded using 'Show more' button")
            
            result = {
                'search_term': search_term,
                'has_ai_overview': has_ai_overview,
                'selector_used': selector_used,
                'content_expanded': expanded_content,
                'ai_content': ai_content,
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
            
            # Save session state with proxy-specific cookies
            self.save_session_cookies(context, proxy_hash)
            
            return result
            
        except Exception as e:
            print(f"  FAILED: Error: {str(e)}")
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
        print("Starting Google AI Overview Analysis")
        print("Using international proxies with Canadian localization")
        
        search_terms = []
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader, None)
                search_terms = [row[0].strip() for row in reader if row]
        except Exception as e:
            print(f"FAILED: Error reading CSV: {e}")
            return
        
        print(f"Found {len(search_terms)} search terms")
        
        # Random initial delay to avoid patterns
        initial_delay = random.uniform(15, 45)  # 15-45 seconds initial delay
        print(f"Initial delay: {initial_delay:.1f} seconds to avoid detection...")
        time.sleep(initial_delay)
        
        with sync_playwright() as playwright:
            proxy = self.get_next_proxy()
            browser, context, proxy_hash = self.setup_browser_context(playwright, proxy)
            
            try:
                i = 0
                while i < len(search_terms):
                    term = search_terms[i]
                    search_number = i + 1
                    print(f"\n{'='*50}")
                    print(f"Search {search_number}/{len(search_terms)}: '{term}'")
                    
                    result = self.search_and_screenshot(term, browser, context, proxy_hash)
                    
                    # Check if we need to restart due to CAPTCHA/blocks
                    if result.get('restart_needed'):
                        print(f"\n🚨 CAPTCHA/BLOCK detected for '{term}' - Restarting with new proxy...")
                        try:
                            browser, context, proxy_hash = self.handle_captcha_restart(browser, context, playwright)
                            print(f"  🔄 Will retry search term: '{term}'")
                            # Don't increment i - retry the same search term
                            continue
                        except Exception as e:
                            print(f"Failed to restart session: {e}")
                            break
                    
                    # Success - add result and move to next term
                    self.results.append(result)
                    i += 1  # Only increment when search succeeds or fails without CAPTCHA
                    
                    # Simulate alt-tabbing every few queries (realistic multitasking)
                    if search_number % 3 == 0 and random.random() < 0.6:  # 60% chance every 3rd query
                        temp_page = context.new_page()
                        try:
                            temp_page.goto('https://www.google.com', timeout=10000)
                            self.simulate_alt_tab(temp_page)
                        except:
                            pass
                        finally:
                            temp_page.close()
                    
                    # Check if we need new proxy due to rate limit
                    if result.get('error') == 'Rate limited' and self.proxies:
                        print("Rotating proxy due to rate limit...")
                        context.close()
                        browser.close()
                        
                        # Wait before using new proxy
                        wait_time = random.uniform(30, 60)
                        print(f"Waiting {wait_time:.0f} seconds...")
                        time.sleep(wait_time)
                        
                        proxy = self.get_next_proxy()
                        browser, context, proxy_hash = self.setup_browser_context(playwright, proxy)
                    
                    # Enhanced delay between searches with random activities
                    if search_number < len(search_terms):
                        delay = random.uniform(self.delay_range[0], self.delay_range[1])
                        print(f"Waiting {delay:.1f} seconds...")
                        
                        # Split delay into smaller chunks with random activities
                        chunks = 3
                        chunk_delay = delay / chunks
                        
                        for chunk in range(chunks):
                            time.sleep(chunk_delay)
                            
                            # Random activity during delay
                            if random.random() < 0.3:
                                print("  Simulating idle browsing...")
                                try:
                                    temp_page = context.new_page()
                                    temp_page.goto('https://www.google.com', timeout=10000)
                                    time.sleep(random.uniform(1, 3))
                                    temp_page.close()
                                except:
                                    pass
                        
                        # Rotate proxy more frequently for better diversity
                        if search_number % 1 == 0 and self.proxies:  # Rotate after EVERY search
                            print("Periodic proxy rotation...")
                            context.close()
                            browser.close()
                            proxy = self.get_next_proxy()
                            browser, context, proxy_hash = self.setup_browser_context(playwright, proxy)
                
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
        print(f"\nResults saved to {json_file}")
        
        csv_file = f"ai_overview_summary_{timestamp}.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Search Term', 'Has AI Overview', 'Selector Used', 'Content Expanded', 'AI Content Segments', 'Highlighted Info', 'Screenshot Path', 'Error', 'Timestamp'])
            for result in self.results:
                ai_content = result.get('ai_content', {}) or {}
                writer.writerow([
                    result['search_term'],
                    result['has_ai_overview'],
                    result.get('selector_used', ''),
                    result.get('content_expanded', False),
                    len(ai_content.get('text_segments', [])) if ai_content else 0,
                    ai_content.get('highlighted_info', '') if ai_content else '',
                    result.get('screenshot_path', ''),
                    result.get('error', ''),
                    result['timestamp']
                ])
        print(f"Summary saved to {csv_file}")

    def print_summary(self):
        """Print summary"""
        total = len(self.results)
        with_ai = sum(1 for r in self.results if r['has_ai_overview'])
        
        print(f"\nSUMMARY")
        print(f"{'='*30}")
        print(f"Total: {total}")
        print(f"With AI Overview: {with_ai} ({(with_ai/total)*100:.1f}%)" if total > 0 else "N/A")


if __name__ == "__main__":
    CSV_FILE = "cra_search_terms.csv"
    OUTPUT_DIR = "ai_overview_screenshots"
    DELAY_RANGE = (30, 60)  # Reduced delays - 30 seconds to 1 minute between searches
    
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
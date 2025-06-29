#!/usr/bin/env python3
"""
Detailed proxy test script with better error handling and diagnostics
"""

import re
import json
from playwright.sync_api import sync_playwright, Error
import time

# Oxylabs Residential Proxy Configuration
proxy_user = 'customer-naomivk_2kqmu-cc-CA'  
proxy_pass = 'GeorgieDory2147_3'
proxy_host = 'pr.oxylabs.io'
proxy_port = '7777'

def test_proxy_configurations():
    """Test different proxy configurations"""
    
    # Different proxy configurations to test
    proxy_configs = [
        {
            "name": "Session-based proxy",
            "url": f"http://{proxy_user}-session-test:{proxy_pass}@{proxy_host}:{proxy_port}"
        },
        {
            "name": "City-based proxy (Toronto)",
            "url": f"http://{proxy_user}-city-toronto:{proxy_pass}@{proxy_host}:{proxy_port}"
        },
        {
            "name": "Random Canadian IP",
            "url": f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
        }
    ]
    
    for config in proxy_configs:
        print(f"\n{'='*60}")
        print(f"🧪 Testing: {config['name']}")
        print(f"   URL: {config['url']}")
        test_single_proxy(config['url'])
        time.sleep(2)

def parse_proxy_url(proxy_url):
    """Parse proxy URL into Playwright format"""
    match = re.match(r'http://([^:]+):([^@]+)@([^:]+):([^/]+)', proxy_url)
    if match:
        username, password, host, port = match.groups()
        return {
            'server': f'http://{host}:{port}',
            'username': username,
            'password': password
        }
    return None

def test_single_proxy(proxy_url):
    """Test a single proxy configuration"""
    
    proxy_config = parse_proxy_url(proxy_url)
    if not proxy_config:
        print("❌ Failed to parse proxy URL")
        return
    
    print(f"   Parsed: server={proxy_config['server']}, username={proxy_config['username']}")
    
    with sync_playwright() as p:
        browser = None
        try:
            # Try with different browser options
            print("\n🌐 Launching browser...")
            browser = p.chromium.launch(
                headless=True,  # Use headless for testing
                proxy=proxy_config,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            
            context = browser.new_context(
                ignore_https_errors=True,  # Ignore SSL errors for testing
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            # Enable request/response logging
            page.on("request", lambda request: print(f"   → Request: {request.method} {request.url}"))
            page.on("response", lambda response: print(f"   ← Response: {response.status} {response.url}"))
            
            # Test 1: Basic connectivity test
            print("\n📡 Testing basic connectivity...")
            try:
                response = page.goto('http://httpbin.org/ip', timeout=30000, wait_until='domcontentloaded')
                if response and response.ok:
                    content = page.content()
                    print(f"   ✅ Connected! Status: {response.status}")
                    # Try to parse IP info
                    try:
                        body_text = page.locator('body').inner_text()
                        print(f"   IP Info: {body_text}")
                    except:
                        pass
                else:
                    print(f"   ❌ Failed to connect. Status: {response.status if response else 'No response'}")
            except Error as e:
                print(f"   ❌ Connection error: {e}")
                
            # Test 2: HTTPS test
            print("\n🔒 Testing HTTPS...")
            try:
                response = page.goto('https://httpbin.org/headers', timeout=30000, wait_until='domcontentloaded')
                if response and response.ok:
                    print(f"   ✅ HTTPS works! Status: {response.status}")
                else:
                    print(f"   ❌ HTTPS failed. Status: {response.status if response else 'No response'}")
            except Error as e:
                print(f"   ❌ HTTPS error: {e}")
            
            # Test 3: Check location via ipinfo.io
            print("\n📍 Checking IP location...")
            try:
                response = page.goto('https://ipinfo.io/json', timeout=30000, wait_until='domcontentloaded')
                if response and response.ok:
                    body_text = page.locator('body').inner_text()
                    try:
                        ip_data = json.loads(body_text)
                        print(f"   IP: {ip_data.get('ip', 'Unknown')}")
                        print(f"   Country: {ip_data.get('country', 'Unknown')}")
                        print(f"   City: {ip_data.get('city', 'Unknown')}")
                        print(f"   Region: {ip_data.get('region', 'Unknown')}")
                        
                        if ip_data.get('country') == 'CA':
                            print("   ✅ Canadian IP confirmed!")
                        else:
                            print(f"   ⚠️ Non-Canadian IP: {ip_data.get('country')}")
                    except json.JSONDecodeError:
                        print(f"   ⚠️ Could not parse IP info: {body_text[:100]}...")
                else:
                    print(f"   ❌ Failed to get IP info. Status: {response.status if response else 'No response'}")
            except Error as e:
                print(f"   ❌ IP check error: {e}")
            
            print("\n✅ Proxy test completed")
            
        except Exception as e:
            print(f"\n❌ Browser launch failed: {e}")
            print("   Possible issues:")
            print("   - Invalid proxy credentials")
            print("   - Proxy server is down")
            print("   - Network connectivity issues")
            print("   - Firewall blocking proxy connection")
            
        finally:
            if browser:
                browser.close()

def test_direct_connection():
    """Test without proxy to ensure basic connectivity"""
    print("\n" + "="*60)
    print("🌐 Testing direct connection (no proxy)...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            response = page.goto('https://ipinfo.io/json', timeout=30000)
            if response and response.ok:
                body_text = page.locator('body').inner_text()
                ip_data = json.loads(body_text)
                print(f"✅ Direct connection works!")
                print(f"   Your IP: {ip_data.get('ip')}")
                print(f"   Location: {ip_data.get('city')}, {ip_data.get('country')}")
            else:
                print("❌ Direct connection failed")
        except Exception as e:
            print(f"❌ Direct connection error: {e}")
        
        browser.close()

if __name__ == "__main__":
    print("🔧 Oxylabs Proxy Configuration Test")
    print("="*60)
    
    # First test direct connection
    test_direct_connection()
    
    # Then test proxy configurations
    test_proxy_configurations()
    
    print("\n" + "="*60)
    print("📋 Test Summary:")
    print("If all tests failed with net::ERR_HTTP_RESPONSE_CODE_FAILURE:")
    print("  1. Verify your Oxylabs credentials are correct")
    print("  2. Check if your account is active and has residential proxy access")
    print("  3. Ensure your IP is whitelisted in Oxylabs dashboard")
    print("  4. Try accessing https://pr.oxylabs.io:7777 directly in browser")
    print("  5. Contact Oxylabs support if issues persist")
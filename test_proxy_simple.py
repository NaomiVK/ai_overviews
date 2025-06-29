#!/usr/bin/env python3
"""
Simple proxy test to diagnose Playwright issues
"""

from playwright.sync_api import sync_playwright
import time

# Oxylabs credentials
proxy_user = 'customer-naomivk_2kqmu-cc-CA'
proxy_pass = 'GeorgieDory2147_3'
proxy_host = 'pr.oxylabs.io'
proxy_port = '7777'

def test_basic_proxy():
    """Test basic proxy connectivity with different sites"""
    
    proxy_config = {
        'server': f'http://{proxy_host}:{proxy_port}',
        'username': proxy_user,
        'password': proxy_pass
    }
    
    print(f"🔧 Testing proxy: {proxy_config['server']}")
    print(f"   Username: {proxy_config['username']}")
    
    with sync_playwright() as p:
        print("\n1️⃣ Testing with basic HTTP site...")
        browser = p.chromium.launch(
            headless=False,
            proxy=proxy_config,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        page = browser.new_page()
        
        # Log all network activity
        def log_request(request):
            print(f"→ {request.method} {request.url}")
        
        def log_response(response):
            print(f"← {response.status} {response.url}")
        
        def log_failure(request):
            print(f"❌ Failed: {request.url} - {request.failure}")
        
        page.on("request", log_request)
        page.on("response", log_response)
        page.on("requestfailed", log_failure)
        
        try:
            # Test 1: Simple HTTP site
            print("\n📡 Testing http://httpbin.org/ip")
            response = page.goto('http://httpbin.org/ip', timeout=30000)
            if response:
                print(f"✅ Status: {response.status}")
                print(f"Content: {page.content()[:200]}")
            time.sleep(2)
            
            # Test 2: HTTPS site
            print("\n🔒 Testing https://ipinfo.io/json")
            response = page.goto('https://ipinfo.io/json', timeout=30000)
            if response:
                print(f"✅ Status: {response.status}")
                print(f"Content: {page.content()[:200]}")
            time.sleep(2)
            
            # Test 3: Google.ca without /ncr
            print("\n🔍 Testing https://www.google.ca (without /ncr)")
            response = page.goto('https://www.google.ca', timeout=30000)
            if response:
                print(f"✅ Status: {response.status}")
                print(f"Final URL: {page.url}")
            time.sleep(2)
            
            # Test 4: Google.ca with /ncr
            print("\n🔍 Testing https://www.google.ca/ncr")
            response = page.goto('https://www.google.ca/ncr', timeout=30000)
            if response:
                print(f"✅ Status: {response.status}")
                print(f"Final URL: {page.url}")
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        browser.close()

def test_without_proxy():
    """Test without proxy to compare"""
    print("\n\n2️⃣ Testing WITHOUT proxy for comparison...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            print("\n🌐 Testing https://www.google.ca (no proxy)")
            response = page.goto('https://www.google.ca', timeout=30000)
            if response:
                print(f"✅ Status: {response.status}")
                print(f"Final URL: {page.url}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        browser.close()

def test_alternative_proxy_format():
    """Test with alternative proxy configuration"""
    print("\n\n3️⃣ Testing alternative proxy configuration...")
    
    # Try setting proxy via browser args
    proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                f'--proxy-server={proxy_host}:{proxy_port}',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        # Set auth via context
        context = browser.new_context(
            http_credentials={
                'username': proxy_user,
                'password': proxy_pass
            }
        )
        
        page = context.new_page()
        
        try:
            print(f"\n📡 Testing with args-based proxy config")
            response = page.goto('https://ipinfo.io/json', timeout=30000)
            if response:
                print(f"✅ Status: {response.status}")
                print(f"Content: {page.content()[:200]}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        browser.close()

if __name__ == "__main__":
    print("🧪 Playwright Proxy Diagnostic Test")
    print("="*50)
    
    test_basic_proxy()
    test_without_proxy()
    test_alternative_proxy_format()
    
    print("\n\n📋 Diagnostic Summary:")
    print("If Google loads without proxy but not with proxy:")
    print("  - The proxy might be blocking Google specifically")
    print("  - Try using a different proxy endpoint or configuration")
    print("  - Check if Oxylabs has specific settings for Google access")
    print("\nIf nothing loads with proxy:")
    print("  - Check firewall/network settings")
    print("  - Verify proxy credentials are still valid")
    print("  - Try different Playwright proxy configuration methods")
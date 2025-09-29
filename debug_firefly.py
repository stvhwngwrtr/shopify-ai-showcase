#!/usr/bin/env python3
"""
Firefly API Debug Script
This script helps debug Adobe Firefly API authentication and entitlement issues.
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_firefly_authentication():
    """Test complete Firefly authentication flow."""
    
    print("🔍 Adobe Firefly API Debug Tool")
    print("=" * 50)
    
    # Step 1: Check credentials
    client_id = os.getenv('FIREFLY_CLIENT_ID')
    client_secret = os.getenv('FIREFLY_CLIENT_SECRET')
    
    print(f"1. Checking credentials:")
    print(f"   Client ID: {'✅ Present' if client_id else '❌ Missing'}")
    print(f"   Client Secret: {'✅ Present' if client_secret else '❌ Missing'}")
    
    if not client_id or not client_secret:
        print("\n❌ Missing credentials. Please check your .env file.")
        return False
    
    print(f"   Client ID (partial): {client_id[:8]}...")
    
    # Step 2: Test token generation
    print(f"\n2. Testing token generation:")
    try:
        token_url = 'https://ims-na1.adobelogin.com/ims/token/v3'
        token_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'openid,AdobeID,session,additional_info,read_organizations,firefly_api,ff_apis'
        }
        
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        response = requests.post(token_url, data=token_data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            token_info = response.json()
            print("   ✅ Token generation successful")
            print(f"   Token expires in: {token_info.get('expires_in', 'unknown')} seconds")
            access_token = token_info['access_token']
        else:
            print(f"   ❌ Token generation failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Token generation error: {e}")
        return False
    
    # Step 3: Test Firefly API call
    print(f"\n3. Testing Firefly API access:")
    try:
        firefly_url = 'https://firefly-api.adobe.io/v2/images/generate'
        firefly_headers = {
            'Authorization': f'Bearer {access_token}',
            'X-API-Key': client_id,
            'Content-Type': 'application/json'
        }
        
        test_payload = {
            "prompt": "A simple red apple for API testing",
            "n": 1,
            "size": {"width": 512, "height": 512},
            "style": {"preset": "photo"}
        }
        
        response = requests.post(firefly_url, json=test_payload, headers=firefly_headers, timeout=30)
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Firefly API call successful!")
            result = response.json()
            if result.get('outputs'):
                print(f"   Generated {len(result['outputs'])} image(s)")
                return True
            else:
                print("   ⚠️ No outputs in response")
                
        else:
            print(f"   ❌ Firefly API call failed")
            try:
                error_data = response.json()
                error_code = error_data.get('error_code')
                message = error_data.get('message')
                
                print(f"   Error Code: {error_code}")
                print(f"   Message: {message}")
                
                if error_code == 'user_not_entitled':
                    print(f"\n🔧 SOLUTION:")
                    print(f"   Your Adobe account doesn't have Firefly API entitlements.")
                    print(f"   1. Visit: https://developer.adobe.com/console/home")
                    print(f"   2. Select your project")
                    print(f"   3. Ensure Firefly API is enabled and properly configured")
                    print(f"   4. You may need a paid Adobe Creative Cloud subscription")
                    print(f"   5. Or request access to the Firefly API beta program")
                    
            except:
                print(f"   Raw error: {response.text}")
                
    except Exception as e:
        print(f"   ❌ API call error: {e}")
        
    return False

def test_fallback_mechanism():
    """Test the Shopify image fallback mechanism."""
    print(f"\n4. Testing Shopify image fallback:")
    
    try:
        app_url = 'http://localhost:8080/api/firefly/generate'
        test_data = {
            "prompts": ["A red apple on white background"],
            "products": [
                {
                    "title": "Test Product",
                    "images": ["https://cdn.shopify.com/s/files/1/example.jpg"]
                }
            ]
        }
        
        response = requests.post(app_url, json=test_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                for r in result.get('results', []):
                    if r.get('used_fallback'):
                        print("   ✅ Shopify fallback mechanism working")
                        return True
                    else:
                        print("   ⚠️ Fallback not triggered")
            else:
                print(f"   ❌ App request failed: {result.get('error')}")
        else:
            print(f"   ❌ App not responding: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Fallback test error: {e}")
        
    return False

if __name__ == "__main__":
    print("Starting Firefly API debugging...\n")
    
    # Run authentication test
    auth_success = test_firefly_authentication()
    
    # Test fallback mechanism
    fallback_success = test_fallback_mechanism()
    
    print(f"\n" + "=" * 50)
    print(f"SUMMARY:")
    print(f"Authentication: {'✅ Working' if auth_success else '❌ Failed'}")
    print(f"Fallback: {'✅ Working' if fallback_success else '❌ Failed'}")
    
    if not auth_success and fallback_success:
        print(f"\n💡 RECOMMENDATION:")
        print(f"   Firefly API has entitlement issues, but fallback is working.")
        print(f"   Your app will use Shopify product images when Firefly fails.")
        print(f"   This provides a good user experience while you resolve API access.")

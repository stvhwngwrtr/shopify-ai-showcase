#!/usr/bin/env python3
"""
DALL-E API Debug Script
This script helps debug OpenAI DALL-E API authentication and usage.
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_dalle_authentication():
    """Test complete DALL-E authentication flow."""
    
    print("🔍 OpenAI DALL-E API Debug Tool")
    print("=" * 50)
    
    # Step 1: Check credentials
    api_key = os.getenv('OPENAI_API_KEY')
    
    print(f"1. Checking credentials:")
    print(f"   API Key: {'✅ Present' if api_key else '❌ Missing'}")
    
    if not api_key:
        print("\n❌ Missing API key. Please check your .env file.")
        print("   Get your API key from: https://platform.openai.com/api-keys")
        return False
    
    print(f"   API Key (partial): {api_key[:8]}...")
    
    # Step 2: Test DALL-E API call
    print(f"\n2. Testing DALL-E API access:")
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key)
        
        test_prompt = "A simple red apple for API testing"
        
        print(f"   Testing with prompt: '{test_prompt}'")
        
        response = client.images.generate(
            model="dall-e-3",
            prompt=test_prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        
        if response.data and len(response.data) > 0:
            print("   ✅ DALL-E API call successful!")
            image_data = response.data[0]
            print(f"   Generated image URL: {image_data.url[:50]}...")
            if hasattr(image_data, 'revised_prompt'):
                print(f"   Revised prompt: {image_data.revised_prompt[:100]}...")
            return True
        else:
            print("   ⚠️ No image data in response")
            
    except Exception as e:
        print(f"   ❌ DALL-E API call error: {e}")
        
        # Check for specific error types
        error_str = str(e).lower()
        if 'insufficient_quota' in error_str:
            print(f"\n🔧 SOLUTION:")
            print(f"   Your OpenAI account has insufficient credits.")
            print(f"   1. Visit: https://platform.openai.com/account/billing")
            print(f"   2. Add credits to your account")
            print(f"   3. Ensure you have sufficient balance for DALL-E usage")
        elif 'invalid_api_key' in error_str:
            print(f"\n🔧 SOLUTION:")
            print(f"   Your API key is invalid.")
            print(f"   1. Visit: https://platform.openai.com/api-keys")
            print(f"   2. Generate a new API key")
            print(f"   3. Update your .env file with the new key")
        elif 'rate_limit' in error_str:
            print(f"\n🔧 SOLUTION:")
            print(f"   You've hit the rate limit.")
            print(f"   1. Wait a few minutes before trying again")
            print(f"   2. Consider upgrading your OpenAI plan for higher limits")
        
    return False

def test_fallback_mechanism():
    """Test the Shopify image fallback mechanism."""
    print(f"\n3. Testing Shopify image fallback:")
    
    try:
        app_url = 'http://localhost:8080/api/dalle/generate'
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
    print("Starting DALL-E API debugging...\n")
    
    # Run authentication test
    auth_success = test_dalle_authentication()
    
    # Test fallback mechanism
    fallback_success = test_fallback_mechanism()
    
    print(f"\n" + "=" * 50)
    print(f"SUMMARY:")
    print(f"Authentication: {'✅ Working' if auth_success else '❌ Failed'}")
    print(f"Fallback: {'✅ Working' if fallback_success else '❌ Failed'}")
    
    if not auth_success and fallback_success:
        print(f"\n💡 RECOMMENDATION:")
        print(f"   DALL-E API has issues, but fallback is working.")
        print(f"   Your app will use Shopify product images when DALL-E fails.")
        print(f"   This provides a good user experience while you resolve API access.")

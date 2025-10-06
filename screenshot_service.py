"""Screenshot service for capturing Instagram mockups using Screenshot API."""

import requests
import os
from typing import Dict, Any
import base64
from urllib.parse import urlencode


class ScreenshotService:
    """Service for capturing screenshots of Instagram mockups."""
    
    def __init__(self):
        """Initialize screenshot service."""
        # We'll use a free screenshot service that doesn't require API keys
        # Alternative: Use screenshotone.com, apiflash.com, or screenshot.io
        self.use_external_service = os.getenv('USE_SCREENSHOT_SERVICE', 'false').lower() == 'true'
        self.api_key = os.getenv('SCREENSHOT_API_KEY', '')
        
        if self.use_external_service and self.api_key:
            print("✅ Screenshot service configured")
        else:
            print("⚠️  Screenshot service not configured - will use internal rendering")
    
    def capture_url(self, url: str, width: int = 1080, height: int = 1350) -> Dict[str, Any]:
        """Capture a screenshot of a URL.
        
        Args:
            url: The URL to screenshot
            width: Screenshot width
            height: Screenshot height
            
        Returns:
            Dict with success status and image data
        """
        if not self.use_external_service or not self.api_key:
            return {
                "success": False,
                "error": "Screenshot service not configured. Set USE_SCREENSHOT_SERVICE=true and SCREENSHOT_API_KEY"
            }
        
        try:
            # Using screenshotone.com API (you can swap this for other services)
            api_url = "https://api.screenshotone.com/take"
            
            params = {
                "access_key": self.api_key,
                "url": url,
                "viewport_width": width,
                "viewport_height": height,
                "device_scale_factor": 2,  # Retina quality
                "format": "jpg",
                "image_quality": 90,
                "block_ads": True,
                "block_cookie_banners": True,
                "block_banners_by_heuristics": False,
                "delay": 2,  # Wait 2 seconds for images to load
                "timeout": 30
            }
            
            screenshot_url = f"{api_url}?{urlencode(params)}"
            
            print(f"📸 Capturing screenshot: {url}")
            response = requests.get(screenshot_url, timeout=60)
            response.raise_for_status()
            
            # Convert to base64
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            
            print(f"✅ Screenshot captured: {len(response.content)} bytes")
            
            return {
                "success": True,
                "image_data": image_base64,
                "format": "jpeg",
                "size": len(response.content)
            }
            
        except Exception as e:
            error_msg = f"Screenshot capture failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def capture_html(self, html_content: str, width: int = 1080, height: int = 1350) -> Dict[str, Any]:
        """Capture a screenshot of HTML content.
        
        Args:
            html_content: The HTML content to render and screenshot
            width: Screenshot width
            height: Screenshot height
            
        Returns:
            Dict with success status and image data
        """
        try:
            # For HTML content, we need to use a different approach
            # Option 1: Use screenshotone's HTML capture
            # Option 2: Serve the HTML from an endpoint and screenshot that URL
            
            if not self.use_external_service or not self.api_key:
                return {
                    "success": False,
                    "error": "Screenshot service not configured"
                }
            
            # Using screenshotone.com HTML API
            api_url = "https://api.screenshotone.com/take"
            
            data = {
                "access_key": self.api_key,
                "html": html_content,
                "viewport_width": width,
                "viewport_height": height,
                "device_scale_factor": 2,
                "format": "jpg",
                "image_quality": 90,
                "delay": 1,
                "timeout": 30
            }
            
            print(f"📸 Capturing screenshot from HTML ({len(html_content)} chars)")
            response = requests.post(api_url, json=data, timeout=60)
            response.raise_for_status()
            
            # Convert to base64
            image_base64 = base64.b64encode(response.content).decode('utf-8')
            
            print(f"✅ Screenshot captured from HTML: {len(response.content)} bytes")
            
            return {
                "success": True,
                "image_data": image_base64,
                "format": "jpeg",
                "size": len(response.content)
            }
            
        except Exception as e:
            error_msg = f"HTML screenshot capture failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }


def get_screenshot_service() -> ScreenshotService:
    """Get screenshot service instance."""
    return ScreenshotService()


if __name__ == "__main__":
    # Test the screenshot service
    service = get_screenshot_service()
    
    if service.use_external_service and service.api_key:
        print("✅ Screenshot service is configured and ready")
        print(f"   API Key: {service.api_key[:10]}...")
    else:
        print("❌ Screenshot service is not configured")
        print("   Set these environment variables:")
        print("   - USE_SCREENSHOT_SERVICE=true")
        print("   - SCREENSHOT_API_KEY=your_api_key")


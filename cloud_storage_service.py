import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import Dict, Any, Optional
import os
import io
import base64

class CloudStorageService:
    """Service for uploading images to cloud storage."""
    
    def __init__(self):
        """Initialize cloud storage service."""
        self.cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
        self.api_key = os.getenv('CLOUDINARY_API_KEY')
        self.api_secret = os.getenv('CLOUDINARY_API_SECRET')
        
        if not all([self.cloud_name, self.api_key, self.api_secret]):
            print("⚠️ Warning: Cloudinary credentials not set. Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET environment variables.")
            self.enabled = False
        else:
            # Configure Cloudinary
            cloudinary.config(
                cloud_name=self.cloud_name,
                api_key=self.api_key,
                api_secret=self.api_secret
            )
            self.enabled = True
            print(f"✅ Cloudinary configured for cloud: {self.cloud_name}")
    
    def upload_mockup(self, image_data: str, session_id: str, caption: str = "") -> Dict[str, Any]:
        """Upload Instagram mockup to cloud storage.
        
        Args:
            image_data: Base64 encoded image data
            session_id: Unique session identifier
            caption: Caption text for metadata
            
        Returns:
            Dict with success status and public URL
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Cloud storage not configured"
            }
        
        try:
            print(f"🔄 Starting cloud upload for session: {session_id}")
            
            # Extract base64 data
            if image_data.startswith('data:image'):
                header, encoded = image_data.split(',', 1)
                image_bytes = base64.b64decode(encoded)
                print(f"📊 Extracted base64 data: {len(image_bytes)} bytes")
            else:
                image_bytes = base64.b64decode(image_data)
                print(f"📊 Decoded base64 data: {len(image_bytes)} bytes")
            
            # Create filename
            filename = f"instagram_mockup_{session_id}.jpg"
            print(f"📁 Uploading as: mockups/{filename}")
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                io.BytesIO(image_bytes),
                public_id=f"mockups/{filename}",
                folder="instagram_mockups",
                resource_type="image",
                format="jpg",
                quality="auto",
                fetch_format="auto",
                tags=["instagram", "mockup", "social_media"],
                context={
                    "caption": caption[:500],  # Cloudinary context limit
                    "session_id": session_id
                }
            )
            
            print(f"✅ Upload successful: {result['secure_url']}")
            return {
                "success": True,
                "public_url": result['secure_url'],
                "cloudinary_id": result['public_id'],
                "format": result['format'],
                "bytes": result['bytes']
            }
            
        except Exception as e:
            error_msg = f"Failed to upload mockup to cloud storage: {str(e)}"
            print(f"❌ {error_msg}")
            print(f"🔍 Error type: {type(e).__name__}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def delete_mockup(self, cloudinary_id: str) -> Dict[str, Any]:
        """Delete a mockup from cloud storage.
        
        Args:
            cloudinary_id: Cloudinary public ID
            
        Returns:
            Dict with success status
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Cloud storage not configured"
            }
        
        try:
            result = cloudinary.uploader.destroy(cloudinary_id)
            return {
                "success": result.get('result') == 'ok',
                "result": result.get('result')
            }
        except Exception as e:
            error_msg = f"Failed to delete mockup: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }


def get_cloud_storage_service() -> CloudStorageService:
    """Get cloud storage service instance."""
    return CloudStorageService()


if __name__ == "__main__":
    # Test the cloud storage service
    service = get_cloud_storage_service()
    
    if service.enabled:
        print("✅ Cloud storage service is configured and ready")
    else:
        print("❌ Cloud storage service is not configured")
        print("Set these environment variables:")
        print("- CLOUDINARY_CLOUD_NAME")
        print("- CLOUDINARY_API_KEY") 
        print("- CLOUDINARY_API_SECRET")

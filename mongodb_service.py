import pymongo
from pymongo import MongoClient
from datetime import datetime
import uuid
import os
from typing import Dict, Any, Optional
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import textwrap


class MongoDBService:
    """Service for MongoDB operations related to Instagram posts."""
    
    def __init__(self, connection_string: str, database_name: str = "instagram_posts"):
        """Initialize MongoDB connection.
        
        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database to use
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection = None
    
    def connect(self):
        """Establish connection to MongoDB."""
        try:
            self.client = MongoClient(self.connection_string)
            self.db = self.client[self.database_name]
            self.collection = self.db["posts"]
            print("✅ Connected to MongoDB successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {str(e)}")
            return False
    
    def disconnect(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            print("🔌 Disconnected from MongoDB")
    
    def create_instagram_post_record(self, 
                                   product_id: str,
                                   product_url: str,
                                   asset_urls: list,
                                   product_name: str,
                                   product_category: str,
                                   caption: str = "",
                                   user_name: str = "AI Showcase") -> Dict[str, Any]:
        """Create a new Instagram post record in MongoDB.
        
        Args:
            product_id: Shopify product ID
            product_url: URL to the product page
            asset_urls: List of asset URLs (images)
            product_name: Name of the product
            product_category: Category of the product
            caption: Optional caption text
            user_name: Name of the user posting (default: "AI Showcase")
            
        Returns:
            Dict with success status and record data
        """
        try:
            if self.collection is None:
                if not self.connect():
                    return {
                        "success": False,
                        "error": "Failed to connect to MongoDB"
                    }
            
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Create the record
            record = {
                "session_id": session_id,
                "product_id": product_id,
                "product_url": product_url,
                "asset_created_at": datetime.utcnow(),
                "asset_url": asset_urls,
                "displayed": 0,
                "user_name": user_name,
                "asset_type": "instagram",
                "get_displayed": True,
                "product_name": product_name,
                "product_category": product_category,
                "caption": caption,
                "mockup_type": "instagram_post",
                "has_caption_overlay": bool(caption and caption.strip())
            }
            
            # Insert the record
            result = self.collection.insert_one(record)
            
            if result.inserted_id:
                print(f"✅ Instagram post record created with ID: {result.inserted_id}")
                return {
                    "success": True,
                    "record_id": str(result.inserted_id),
                    "session_id": session_id,
                    "data": record
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to insert record"
                }
                
        except Exception as e:
            error_msg = f"MongoDB operation failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def get_post_by_session_id(self, session_id: str) -> Dict[str, Any]:
        """Retrieve a post record by session ID.
        
        Args:
            session_id: The session ID to search for
            
        Returns:
            Dict with success status and post data
        """
        try:
            if self.collection is None:
                if not self.connect():
                    return {
                        "success": False,
                        "error": "Failed to connect to MongoDB"
                    }
            
            post = self.collection.find_one({"session_id": session_id})
            
            if post:
                # Convert ObjectId to string for JSON serialization
                post["_id"] = str(post["_id"])
                return {
                    "success": True,
                    "data": post
                }
            else:
                return {
                    "success": False,
                    "error": "Post not found"
                }
                
        except Exception as e:
            error_msg = f"MongoDB query failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def update_displayed_count(self, session_id: str, increment: int = 1) -> Dict[str, Any]:
        """Update the displayed count for a post.
        
        Args:
            session_id: The session ID of the post
            increment: Amount to increment the displayed count
            
        Returns:
            Dict with success status
        """
        try:
            if self.collection is None:
                if not self.connect():
                    return {
                        "success": False,
                        "error": "Failed to connect to MongoDB"
                    }
            
            result = self.collection.update_one(
                {"session_id": session_id},
                {"$inc": {"displayed": increment}}
            )
            
            if result.modified_count > 0:
                return {
                    "success": True,
                    "message": f"Updated displayed count for session {session_id}"
                }
            else:
                return {
                    "success": False,
                    "error": "No document was updated"
                }
                
        except Exception as e:
            error_msg = f"MongoDB update failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }


def get_mongodb_service() -> MongoDBService:
    """Get configured MongoDB service instance."""
    connection_string = os.getenv('MONGODB_CONNECTION_STRING', 
                                'mongodb+srv://writer_access:DAz45BC6ADsGattA@neo.95ntiul.mongodb.net/?retryWrites=true&w=majority')
    
    return MongoDBService(connection_string)


def create_instagram_preview_image(image_url: str, caption: str = "", width: int = 1080, height: int = 1350) -> Dict[str, Any]:
    """Create a complete Instagram post mockup with UI elements.
    
    Args:
        image_url: URL of the source image
        caption: Caption text to display
        width: Width of the output image
        height: Height of the output image (taller for full post)
        
    Returns:
        Dict with success status and base64 encoded image data
    """
    try:
        # Download the image
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # Open image with PIL
        image = Image.open(io.BytesIO(response.content))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Create Instagram post dimensions (square image + UI elements below)
        post_width = width
        image_size = width  # Square image
        ui_height = height - image_size
        
        # Create the main post image
        instagram_post = Image.new('RGB', (post_width, height), (255, 255, 255))
        
        # Resize and center the main image
        image.thumbnail((image_size, image_size), Image.Resampling.LANCZOS)
        img_width, img_height = image.size
        x = (image_size - img_width) // 2
        y = (image_size - img_height) // 2
        
        # Paste the image at the top
        instagram_post.paste(image, (x, y))
        
        # Create UI elements below the image
        draw = ImageDraw.Draw(instagram_post)
        
        # Try to load fonts
        try:
            # Try different font paths
            font_paths = [
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
                "/System/Library/Fonts/Arial.ttf",      # macOS alternative
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                "arial.ttf",  # Windows
            ]
            
            header_font = None
            caption_font = None
            
            for font_path in font_paths:
                try:
                    header_font = ImageFont.truetype(font_path, 16)
                    caption_font = ImageFont.truetype(font_path, 14)
                    break
                except:
                    continue
            
            if header_font is None:
                header_font = ImageFont.load_default()
                caption_font = ImageFont.load_default()
                
        except:
            header_font = ImageFont.load_default()
            caption_font = ImageFont.load_default()
        
        # Draw Instagram UI elements
        ui_start_y = image_size
        
        # Header area (profile info)
        header_height = 60
        header_y = ui_start_y + 10
        
        # Profile picture (circle)
        profile_size = 40
        profile_x = 20
        profile_y = header_y + 5
        
        # Draw profile circle (light gray)
        draw.ellipse([profile_x, profile_y, profile_x + profile_size, profile_y + profile_size], 
                    fill=(200, 200, 200), outline=(150, 150, 150))
        
        # Profile name
        profile_name_x = profile_x + profile_size + 15
        profile_name_y = header_y + 15
        draw.text((profile_name_x, profile_name_y), "SuperPossible", fill=(0, 0, 0), font=header_font)
        
        # Sponsored label
        sponsored_y = profile_name_y + 20
        draw.text((profile_name_x, sponsored_y), "Sponsored", fill=(100, 100, 100), font=caption_font)
        
        # Three dots menu
        dots_x = post_width - 30
        dots_y = header_y + 20
        for i in range(3):
            dot_y = dots_y + (i * 5)
            draw.ellipse([dots_x, dot_y, dots_x + 3, dot_y + 3], fill=(100, 100, 100))
        
        # Interaction bar
        interaction_y = ui_start_y + header_height + 20
        
        # Heart icon (red heart)
        heart_x = 20
        heart_y = interaction_y
        draw.ellipse([heart_x, heart_y, heart_x + 20, heart_y + 20], fill=(255, 0, 0))
        
        # Comment icon (speech bubble)
        comment_x = heart_x + 35
        comment_y = interaction_y + 2
        draw.ellipse([comment_x, comment_y, comment_x + 16, comment_y + 16], fill=(0, 0, 0))
        draw.ellipse([comment_x + 2, comment_y + 2, comment_x + 14, comment_y + 14], fill=(255, 255, 255))
        
        # Share icon (paper plane)
        share_x = comment_x + 35
        share_y = interaction_y + 2
        # Simple triangle for paper plane
        draw.polygon([(share_x, share_y), (share_x + 15, share_y + 7), (share_x, share_y + 14)], fill=(0, 0, 0))
        
        # Bookmark icon (right side)
        bookmark_x = post_width - 30
        bookmark_y = interaction_y + 2
        draw.rectangle([bookmark_x, bookmark_y, bookmark_x + 16, bookmark_y + 20], fill=(0, 0, 0))
        draw.rectangle([bookmark_x + 2, bookmark_y + 2, bookmark_x + 14, bookmark_y + 18], fill=(255, 255, 255))
        
        # Likes count
        likes_y = interaction_y + 30
        draw.text((20, likes_y), "4975 likes", fill=(0, 0, 0), font=caption_font)
        
        # Caption area
        caption_y = likes_y + 25
        
        if caption and caption.strip():
            # Wrap caption text
            max_chars_per_line = 60
            wrapped_lines = textwrap.wrap(caption, width=max_chars_per_line)
            
            # Limit to 6 lines maximum
            if len(wrapped_lines) > 6:
                wrapped_lines = wrapped_lines[:6]
                wrapped_lines[-1] = wrapped_lines[-1][:-3] + "..."
            
            # Draw caption lines
            line_height = 18
            for i, line in enumerate(wrapped_lines):
                line_y = caption_y + (i * line_height)
                draw.text((20, line_y), line, fill=(0, 0, 0), font=caption_font)
        
        # Timestamp
        timestamp_y = caption_y + (len(wrapped_lines) if caption else 0) * 18 + 15
        draw.text((20, timestamp_y), "Just now", fill=(150, 150, 150), font=caption_font)
        
        # Convert to base64 for easy storage/transmission
        img_buffer = io.BytesIO()
        instagram_post.save(img_buffer, format='JPEG', quality=85)
        img_buffer.seek(0)
        
        # Encode as base64
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        return {
            "success": True,
            "image_data": img_base64,
            "format": "jpeg",
            "dimensions": f"{post_width}x{height}",
            "has_caption": bool(caption and caption.strip())
        }
        
    except Exception as e:
        error_msg = f"Failed to create Instagram post mockup: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "success": False,
            "error": error_msg
        }


if __name__ == "__main__":
    # Test the MongoDB service
    service = get_mongodb_service()
    
    if service.connect():
        # Test creating a record
        result = service.create_instagram_post_record(
            product_id="12345",
            product_url="https://example.com/product/12345",
            asset_urls=["https://example.com/image.jpg"],
            product_name="Test Product",
            product_category="Test Category",
            comment="Test comment"
        )
        
        if result["success"]:
            print(f"✅ Test record created: {result['record_id']}")
        else:
            print(f"❌ Test failed: {result['error']}")
        
        service.disconnect()
    else:
        print("❌ Failed to connect to MongoDB")

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
    """Create a HIGH-RESOLUTION Instagram post mockup with realistic UI elements.
    
    Args:
        image_url: URL of the source image
        caption: Caption text to display
        width: Width of the output image (default 1080px for high quality)
        height: Height of the output image (default 1350px)
        
    Returns:
        Dict with success status and base64 encoded image data
    """
    try:
        print(f"🎨 Creating high-resolution Instagram mockup ({width}x{height})...")
        
        # Download the image
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # Open image with PIL
        image = Image.open(io.BytesIO(response.content))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # High-resolution Instagram dimensions (3x mobile for quality)
        post_width = width
        post_height = height
        
        # Calculate sections (scaled up 3x for quality)
        header_height = 180  # 3x of 60px
        image_height = 1080  # Square Instagram image (high res)
        ui_height = post_height - header_height - image_height
        
        # Create the main post image with high resolution
        instagram_post = Image.new('RGB', (post_width, post_height), (255, 255, 255))
        
        # Resize and center the main image
        image.thumbnail((image_height, image_height), Image.Resampling.LANCZOS)
        img_width, img_height = image.size
        x = (image_height - img_width) // 2
        y = header_height + (image_height - img_height) // 2
        
        # Paste the image below the header
        instagram_post.paste(image, (x, y))
        
        # Create UI elements
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
            small_font = None
            
            for font_path in font_paths:
                try:
                    # 3x font sizes for high resolution
                    header_font = ImageFont.truetype(font_path, 42)  # 3x of 14
                    caption_font = ImageFont.truetype(font_path, 36)  # 3x of 12
                    small_font = ImageFont.truetype(font_path, 30)   # 3x of 10
                    break
                except:
                    continue
            
            if header_font is None:
                header_font = ImageFont.load_default()
                caption_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
                
        except:
            header_font = ImageFont.load_default()
            caption_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # HEADER SECTION (above image) - Instagram style (3x scaled)
        header_y = 30  # 3x of 10
        
        # Profile picture - Instagram logo style (3x scaled)
        profile_size = 96  # 3x of 32
        profile_x = 36  # 3x of 12
        profile_y = header_y + 42  # 3x of 14
        
        # Draw Instagram-style profile circle (purple with white camera)
        draw.ellipse([profile_x, profile_y, profile_x + profile_size, profile_y + profile_size], 
                    fill=(138, 58, 185), outline=(138, 58, 185))  # Instagram purple
        
        # Add white camera icon in center
        camera_size = 16
        camera_x = profile_x + (profile_size - camera_size) // 2
        camera_y = profile_y + (profile_size - camera_size) // 2
        
        # Camera body (rectangle)
        draw.rectangle([camera_x + 2, camera_y + 4, camera_x + camera_size - 2, camera_y + camera_size - 2], 
                      fill=(255, 255, 255))
        
        # Camera lens (circle)
        lens_size = 8
        lens_x = camera_x + (camera_size - lens_size) // 2
        lens_y = camera_y + 6
        draw.ellipse([lens_x, lens_y, lens_x + lens_size, lens_y + lens_size], 
                    fill=(138, 58, 185))
        
        # Camera flash (small rectangle)
        flash_x = camera_x + camera_size - 6
        flash_y = camera_y + 2
        draw.rectangle([flash_x, flash_y, flash_x + 2, flash_y + 2], fill=(255, 255, 255))
        
        # Profile name - bold styling
        profile_name_x = profile_x + profile_size + 12
        profile_name_y = header_y + 20
        draw.text((profile_name_x, profile_name_y), "SuperPossible", fill=(0, 0, 0), font=header_font)
        
        # Sponsored label - smaller and positioned better
        sponsored_y = profile_name_y + 16
        draw.text((profile_name_x, sponsored_y), "Sponsored", fill=(120, 120, 120), font=small_font)
        
        # Three dots menu - better positioning
        dots_x = post_width - 25
        dots_y = header_y + 25
        for i in range(3):
            dot_y = dots_y + (i * 4)
            draw.ellipse([dots_x, dot_y, dots_x + 2, dot_y + 2], fill=(120, 120, 120))
        
        # INTERACTION BAR (below image)
        interaction_y = header_height + image_height + 12
        
        # Heart icon - outline style (Instagram style)
        heart_x = 12
        heart_y = interaction_y
        heart_size = 24
        # Heart outline (simplified as circle outline)
        draw.ellipse([heart_x, heart_y, heart_x + heart_size, heart_y + heart_size], 
                    fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        
        # Comment icon - outline speech bubble
        comment_x = heart_x + 35
        comment_y = interaction_y + 2
        # Speech bubble outline
        draw.ellipse([comment_x, comment_y, comment_x + 20, comment_y + 20], 
                    fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        # Speech bubble tail outline
        draw.polygon([(comment_x + 8, comment_y + 20), (comment_x + 12, comment_y + 20), (comment_x + 10, comment_y + 25)], 
                    fill=(255, 255, 255), outline=(0, 0, 0))
        
        # Share icon - outline paper plane
        share_x = comment_x + 35
        share_y = interaction_y + 2
        # Paper plane outline
        draw.polygon([(share_x, share_y + 8), (share_x + 20, share_y + 8), (share_x + 10, share_y + 18)], 
                    fill=(255, 255, 255), outline=(0, 0, 0))
        # Paper plane wing outline
        draw.polygon([(share_x + 5, share_y + 8), (share_x + 15, share_y + 8), (share_x + 10, share_y + 3)], 
                    fill=(255, 255, 255), outline=(0, 0, 0))
        
        # Bookmark icon - outline style (right side)
        bookmark_x = post_width - 30
        bookmark_y = interaction_y + 2
        # Bookmark outline
        draw.rectangle([bookmark_x, bookmark_y, bookmark_x + 18, bookmark_y + 20], 
                       fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        # Bookmark notch outline
        draw.polygon([(bookmark_x + 6, bookmark_y + 20), (bookmark_x + 12, bookmark_y + 20), (bookmark_x + 9, bookmark_y + 25)], 
                    fill=(255, 255, 255), outline=(0, 0, 0))
        
        # Likes count - better positioning
        likes_y = interaction_y + 30
        draw.text((12, likes_y), "4,455 likes", fill=(0, 0, 0), font=caption_font)
        
        # Caption area - better spacing
        caption_y = likes_y + 20
        
        if caption and caption.strip():
            # Format caption with bold "SuperPossible" at the start
            formatted_caption = f"SuperPossible {caption}"
            
            # Wrap caption text for mobile
            max_chars_per_line = 45  # Shorter for mobile
            wrapped_lines = textwrap.wrap(formatted_caption, width=max_chars_per_line)
            
            # Limit to 4 lines maximum for mobile
            if len(wrapped_lines) > 4:
                wrapped_lines = wrapped_lines[:4]
                wrapped_lines[-1] = wrapped_lines[-1][:-3] + "..."
            
            # Draw caption lines with better spacing
            line_height = 16
            for i, line in enumerate(wrapped_lines):
                line_y = caption_y + (i * line_height)
                
                # Check if line starts with "SuperPossible" and make it bold
                if line.startswith("SuperPossible"):
                    # Split the line to handle bold "SuperPossible" separately
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        # Draw "SuperPossible" in bold (using header_font)
                        draw.text((12, line_y), parts[0], fill=(0, 0, 0), font=header_font)
                        # Draw the rest of the line
                        if parts[1]:
                            # Get width of "SuperPossible" to position the rest
                            bbox = draw.textbbox((0, 0), parts[0], font=header_font)
                            superpossible_width = bbox[2] - bbox[0]
                            draw.text((12 + superpossible_width + 2, line_y), parts[1], fill=(0, 0, 0), font=caption_font)
                    else:
                        # Just "SuperPossible" on its own line
                        draw.text((12, line_y), line, fill=(0, 0, 0), font=header_font)
                else:
                    # Regular line
                    draw.text((12, line_y), line, fill=(0, 0, 0), font=caption_font)
            
            caption_height = len(wrapped_lines) * line_height
        else:
            caption_height = 0
        
        # Timestamp - better positioning
        timestamp_y = caption_y + caption_height + 8
        draw.text((12, timestamp_y), "Just now", fill=(150, 150, 150), font=small_font)
        
        # Convert to base64 for easy storage/transmission
        img_buffer = io.BytesIO()
        instagram_post.save(img_buffer, format='JPEG', quality=90)
        img_buffer.seek(0)
        
        # Encode as base64
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
        
        return {
            "success": True,
            "image_data": img_base64,
            "format": "jpeg",
            "dimensions": f"{post_width}x{post_height}",
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

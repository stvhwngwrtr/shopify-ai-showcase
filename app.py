from flask import Flask, render_template, jsonify, request, send_from_directory
from shopify_service import get_shopify_service
from mongodb_service import get_mongodb_service, create_instagram_preview_image
from cloud_storage_service import get_cloud_storage_service
from screenshot_service import get_screenshot_service
import json
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time
import threading
import re
import random

# Load environment variables
load_dotenv()

# Ensure required environment variables are set
if not os.getenv('SHOPIFY_SHOP_NAME'):
    print("⚠️ Warning: SHOPIFY_SHOP_NAME not set in environment variables")
if not os.getenv('SHOPIFY_ACCESS_TOKEN'):
    print("⚠️ Warning: SHOPIFY_ACCESS_TOKEN not set in environment variables")
if not os.getenv('OPENAI_API_KEY'):
    print("⚠️ Warning: OPENAI_API_KEY not set in environment variables")
if not os.getenv('INSTAGRAM_ACCESS_TOKEN'):
    print("⚠️ Warning: INSTAGRAM_ACCESS_TOKEN not set in environment variables")
if not os.getenv('MONGODB_CONNECTION_STRING'):
    print("⚠️ Warning: MONGODB_CONNECTION_STRING not set in environment variables")

# OpenAI API key management
def get_openai_api_key():
    """Get OpenAI API key from environment variables."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return {
            "success": False,
            "error": "OpenAI API key not found. Please set OPENAI_API_KEY environment variable."
        }
    return {
        "success": True,
        "api_key": api_key
    }

# Instagram API management
def get_instagram_access_token():
    access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    if not access_token:
        return {
            "success": False,
            "error": "Instagram access token not found. Please set INSTAGRAM_ACCESS_TOKEN environment variable."
        }
    return {
        "success": True,
        "access_token": access_token
    }

def post_to_instagram(image_url, caption):
    """Post an image to Instagram using the Instagram Basic Display API."""
    try:
        # Get Instagram access token
        token_result = get_instagram_access_token()
        if not token_result['success']:
            return {
                'success': False,
                'error': token_result.get('error')
            }
        
        access_token = token_result['access_token']
        
        # Instagram Basic Display API endpoint for creating media
        instagram_url = f"https://graph.instagram.com/v18.0/me/media"
        
        # Prepare the media creation request
        media_data = {
            "image_url": image_url,
            "caption": caption,
            "access_token": access_token
        }
        
        print(f"📱 Posting to Instagram: {caption[:50]}...")
        
        # Create the media container
        response = requests.post(instagram_url, data=media_data, timeout=30)
        
        if response.status_code == 200:
            media_response = response.json()
            media_id = media_response.get('id')
            
            if media_id:
                # Now publish the media
                publish_url = f"https://graph.instagram.com/v18.0/me/media_publish"
                publish_data = {
                    "creation_id": media_id,
                    "access_token": access_token
                }
                
                publish_response = requests.post(publish_url, data=publish_data, timeout=30)
                
                if publish_response.status_code == 200:
                    publish_result = publish_response.json()
                    print(f"✅ Successfully posted to Instagram: {publish_result.get('id')}")
                    return {
                        'success': True,
                        'media_id': publish_result.get('id'),
                        'message': 'Successfully posted to Instagram!'
                    }
                else:
                    error_msg = f"Failed to publish Instagram post: {publish_response.status_code} - {publish_response.text}"
                    print(f"❌ {error_msg}")
                    return {
                        'success': False,
                        'error': error_msg
                    }
            else:
                return {
                    'success': False,
                    'error': 'Failed to create media container - no media ID returned'
                }
        else:
            error_msg = f"Instagram API error: {response.status_code} - {response.text}"
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
            
    except Exception as e:
        error_msg = f"Instagram posting error: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            'success': False,
            'error': error_msg
        }

def validate_and_sanitize_prompt(prompt):
    """
    Validate and sanitize prompts to ensure they're safe for DALL-E API.
    Returns a tuple (is_safe, sanitized_prompt, reason).
    """
    if not prompt or not prompt.strip():
        return False, "", "Empty prompt"
    
    # Convert to lowercase for checking
    prompt_lower = prompt.lower()
    
    # List of potentially unsafe keywords/phrases
    unsafe_keywords = [
        # Violence and weapons
        'weapon', 'gun', 'knife', 'sword', 'violence', 'blood', 'death', 'kill', 'murder',
        'war', 'battle', 'fight', 'attack', 'assault', 'bomb', 'explosive',
        
        # Adult/sexual content
        'nude', 'naked', 'sex', 'sexual', 'porn', 'adult', 'erotic', 'intimate',
        'breast', 'genitals', 'underwear', 'lingerie',
        
        # Drugs and substances
        'drug', 'cocaine', 'heroin', 'marijuana', 'cannabis', 'alcohol', 'beer', 'wine',
        'cigarette', 'smoking', 'tobacco',
        
        # Hate speech and discrimination
        'racist', 'discrimination', 'hate', 'nazi', 'terrorist',
        
        # Medical/health claims
        'medical', 'cure', 'treatment', 'diagnosis', 'medicine', 'prescription',
        
        # Copyrighted characters/brands (common ones)
        'disney', 'marvel', 'superman', 'batman', 'mickey mouse', 'coca cola',
        'nike', 'adidas', 'apple logo', 'google', 'facebook',
        
        # Potentially unsafe scenarios
        'accident', 'crash', 'fire', 'burning', 'dangerous', 'hazard'
    ]
    
    # Check for unsafe keywords
    for keyword in unsafe_keywords:
        if keyword in prompt_lower:
            return False, prompt, f"Contains potentially unsafe keyword: {keyword}"
    
    # Basic sanitization - remove potentially problematic characters and phrases
    sanitized = prompt.strip()
    
    # Remove excessive punctuation that might be used for prompt injection
    sanitized = re.sub(r'[!]{3,}', '!!', sanitized)
    sanitized = re.sub(r'[?]{3,}', '??', sanitized)
    sanitized = re.sub(r'[.]{4,}', '...', sanitized)
    
    # Remove potential prompt injection attempts
    injection_patterns = [
        r'ignore\s+previous\s+instructions',
        r'system\s*:',
        r'assistant\s*:',
        r'human\s*:',
        r'prompt\s*:',
        r'<\s*script\s*>',
        r'javascript\s*:',
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            return False, prompt, f"Contains potential prompt injection: {pattern}"
    
    # Length check - DALL-E has limits
    if len(sanitized) > 1000:
        sanitized = sanitized[:1000].rsplit(' ', 1)[0] + "..."
    
    # Ensure it's a reasonable product-focused prompt
    if len(sanitized.strip()) < 5:
        return False, prompt, "Prompt too short"
    
    return True, sanitized, "Safe"

def make_dalle_api_call(prompt, api_key, size="1024x1024", quality="standard", n=1, reference_image_url=None):
    """Make a DALL-E API call to generate images with optional reference image."""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key)
        
        # If reference image is provided, use image variation or editing
        if reference_image_url:
            # Download the reference image
            import requests
            response = requests.get(reference_image_url, timeout=30)
            response.raise_for_status()
            
            # Create image variation based on reference image
            # Note: DALL-E 3 doesn't support direct image-to-image, but we can use it as inspiration
            enhanced_prompt = f"Create a product showcase image inspired by this reference: {prompt}. Style: professional product photography, clean background, high quality, commercial photography style."
            
            dalle_response = client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size=size,
                quality=quality,
                n=n
            )
        else:
            # Standard text-to-image generation
            dalle_response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                n=n
            )
        
        return {
            'success': True,
            'response': dalle_response,
            'used_reference': bool(reference_image_url)
        }
        
    except Exception as e:
        error_msg = f"DALL-E API error: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            'success': False,
            'error': error_msg
        }

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route('/writer.webp')
def serve_writer_logo():
    """Serve the Writer AI logo WebP file."""
    return send_from_directory('static', 'writer.webp', mimetype='image/webp')

@app.route('/profile-logo.svg')
def serve_profile_logo():
    """Serve the custom profile logo SVG file."""
    return send_from_directory('static', 'profile-logo.svg', mimetype='image/svg+xml')

@app.route('/logo.svg')
def serve_logo():
    """Serve the Writer logo SVG file."""
    return send_from_directory('.', 'logo.svg', mimetype='image/svg+xml')

@app.route('/test-mongodb')
def test_mongodb_page():
    """Serve the MongoDB test page."""
    return send_from_directory('.', 'test_mongodb_frontend.html', mimetype='text/html')

def parse_writer_response(raw_response):
    """Parse the Writer AI response into structured sections."""
    import re
    
    # Initialize result structure
    result = {
        "summary": "",
        "caption": "",
        "image_prompts": [],
        "raw_response": raw_response
    }
    
    # Extract summary
    summary_match = re.search(r'<SUMMARY>(.*?)</SUMMARY>', raw_response, re.DOTALL)
    if summary_match:
        summary_text = summary_match.group(1).strip()
        # Clean up the summary - remove leading dashes and clean formatting
        summary_lines = [line.strip().lstrip('- ') for line in summary_text.split('\n') if line.strip()]
        result["summary"] = summary_lines
    
    # Extract caption
    caption_match = re.search(r'<CAPTION>(.*?)</CAPTION>', raw_response, re.DOTALL)
    if caption_match:
        result["caption"] = caption_match.group(1).strip()
    
    # Extract image prompts
    image_prompts = re.findall(r'<IMAGE_PROMPT>(.*?)</IMAGE_PROMPT>', raw_response, re.DOTALL)
    result["image_prompts"] = [prompt.strip() for prompt in image_prompts]
    
    return result

def parse_targeting_response(raw_response):
    """Parse the Writer AI targeting response into structured sections."""
    import re
    
    # Initialize result structure
    result = {
        "enhanced_description": "",
        "explanation": "",
        "improvements": [],
        "raw_response": raw_response
    }
    
    # Check if it has the NEW_DESCRIPTION format from the Product Description Enhancer
    if "<NEW_DESCRIPTION>" in raw_response:
        # Extract the new description
        new_desc_match = re.search(r'<NEW_DESCRIPTION>(.*?)</NEW_DESCRIPTION>', raw_response, re.DOTALL)
        if new_desc_match:
            result["enhanced_description"] = new_desc_match.group(1).strip()
        
        # Extract the explanation of why it's better
        explanation_match = re.search(r'<EXPLANATION>(.*?)</EXPLANATION>', raw_response, re.DOTALL)
        if explanation_match:
            result["explanation"] = explanation_match.group(1).strip()
        
        # Parse the explanation to extract key improvement points
        if result["explanation"]:
            # Look for numbered points (1., 2., etc.) or bullet points in the explanation
            explanation_lines = result["explanation"].split('\n')
            improvements = []
            current_improvement = ""
            
            for line in explanation_lines:
                line = line.strip()
                # Check if this is a main improvement category
                if re.match(r'^\d+\.\s*\*\*.*?\*\*:', line):
                    # Save previous improvement if exists
                    if current_improvement:
                        improvements.append(current_improvement.strip())
                    # Start new improvement - extract the bold category name
                    category_match = re.search(r'\*\*(.*?)\*\*:', line)
                    if category_match:
                        current_improvement = category_match.group(1).strip()
                elif line.startswith('-') and current_improvement:
                    # Add details to current improvement
                    detail = line.lstrip('- ').strip()
                    if detail:
                        current_improvement += f": {detail}"
            
            # Add the last improvement
            if current_improvement:
                improvements.append(current_improvement.strip())
            
            # If we couldn't parse structured improvements, extract bullet points
            if not improvements:
                for line in explanation_lines:
                    line = line.strip()
                    if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                        improvements.append(line.lstrip('•-* ').strip())
            
            result["improvements"] = improvements
    
    # Check if it has the structured format from Instagram Post Creator (fallback)
    elif "<SUMMARY>" in raw_response and "<CAPTION>" in raw_response:
        # Extract the caption as the enhanced description
        caption_match = re.search(r'<CAPTION>(.*?)</CAPTION>', raw_response, re.DOTALL)
        if caption_match:
            result["enhanced_description"] = caption_match.group(1).strip()
        
        # Extract summary as improvements
        summary_match = re.search(r'<SUMMARY>(.*?)</SUMMARY>', raw_response, re.DOTALL)
        if summary_match:
            summary_text = summary_match.group(1).strip()
            improvements = [line.strip().lstrip('- ') for line in summary_text.split('\n') if line.strip()]
            result["improvements"] = improvements
    
    else:
        # Treat the entire response as enhanced description
        result["enhanced_description"] = raw_response.strip()
        
        # Try to extract bullet points or improvements if they exist
        lines = raw_response.split('\n')
        improvements = []
        for line in lines:
            line = line.strip()
            if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                improvements.append(line.lstrip('•-* ').strip())
        
        if improvements:
            result["improvements"] = improvements
    
    return result

def fetch_shopify_products():
    """Fetch random products from Shopify API."""
    try:
        print(f"DEBUG: SHOPIFY_SHOP_NAME = {os.getenv('SHOPIFY_SHOP_NAME')}")
        print(f"DEBUG: All env vars: SHOPIFY_SHOP_NAME={os.environ.get('SHOPIFY_SHOP_NAME')}")
        
        # Clear any global Shopify state
        import shopify
        shopify.ShopifyResource.clear_session()
        print(f"DEBUG: Cleared Shopify sessions")
        
        service = get_shopify_service()
        print(f"DEBUG: service.shop_name = {service.shop_name}")
        print(f"DEBUG: service.shop_url = {service.shop_url}")
        result = service.list_random_products(count=10)
        service.close()
        
        if result["success"]:
            products = []
            for product in result["products"]:
                # Extract key product information
                product_info = {
                    "id": product.get("id"),
                    "title": product.get("title", "No Title"),
                    "handle": product.get("handle", ""),
                    "description": product.get("body_html", "No description available"),
                    "vendor": product.get("vendor", "Unknown"),
                    "product_type": product.get("product_type", ""),
                    "created_at": product.get("created_at", ""),
                    "updated_at": product.get("updated_at", ""),
                    "status": product.get("status", ""),
                    "images": [img.get("src", "") for img in product.get("images", [])],
                    "variants": []
                }
                
                # Extract variant information
                for variant in product.get("variants", []):
                    variant_info = {
                        "id": variant.get("id"),
                        "title": variant.get("title", ""),
                        "price": variant.get("price", "0.00"),
                        "compare_at_price": variant.get("compare_at_price"),
                        "sku": variant.get("sku", ""),
                        "inventory_quantity": variant.get("inventory_quantity", 0),
                        "available": variant.get("available", False)
                    }
                    product_info["variants"].append(variant_info)
                
                products.append(product_info)
            
            return {
                "success": True,
                "products": products,
                "count": len(products)
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "message": result.get("message", "Failed to fetch products")
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to connect to Shopify API: {str(e)}"
        }

@app.route('/')
def index():
    """Main page displaying Shopify products."""
    result = fetch_shopify_products()
    
    if result["success"]:
        return render_template('index.html', 
                             products=result["products"], 
                             count=result["count"],
                             error_message="",
                             success_message="",
                             my_app={"title": "Writer AI - Shopify Product Showcase"})
    else:
        return render_template('index.html', 
                             products=[], 
                             count=0,
                             error_message=result["message"],
                             success_message="",
                             my_app={"title": "Writer AI - Shopify Product Showcase"})

@app.route('/api/products')
def api_products():
    """API endpoint to get products as JSON."""
    result = fetch_shopify_products()
    return jsonify(result)

@app.route('/api/refresh', methods=['POST'])
def refresh_products():
    """API endpoint to refresh products."""
    result = fetch_shopify_products()
    return jsonify(result)

@app.route('/api/writer', methods=['POST'])
def send_to_writer():
    """Send selected products to Writer AI for processing."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        api_key = data.get('api_key')
        application_id = data.get('application_id')
        products = data.get('products', [])
        target_language = data.get('target_language', 'english')
        target_demographic = data.get('target_demographic', 'general')
        
        if not api_key or not application_id:
            return jsonify({"success": False, "error": "API key and application ID are required"}), 400
        
        if not products:
            return jsonify({"success": False, "error": "No products provided"}), 400
        
        # Make individual calls for each product to get better, focused responses
        writer_url = f"https://api.writer.com/v1/applications/{application_id}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        all_responses = []
        
        for product in products:
            # Prepare individual product details with language and demographic context
            product_details = f"{product.get('title', 'Unknown Product')} from {product.get('vendor', 'Unknown Brand')} for {product.get('price', 'N/A')}"
            
            # Create language and demographic context
            language_context = f"Target Language: {target_language.title()}"
            demographic_context = f"Target Demographic: {target_demographic.replace('-', ' ').title()}"
            
            # Format the request for this specific product
            payload = {
                "inputs": [
                    {
                        "id": "Product Details",
                        "value": [f"{product_details}\n{language_context}\n{demographic_context}"]
                    }
                ]
            }
            
            print(f"DEBUG: Sending payload for product '{product.get('title')}': {payload}")
            
            try:
                response = requests.post(writer_url, headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    raw_response = result.get('suggestion', 'No response received from Writer AI')
                    
                    # Parse the structured response
                    parsed_response = parse_writer_response(raw_response)
                    
                    # Add product info to the response
                    parsed_response['product'] = {
                        'id': product.get('id'),  # Add the product ID
                        'title': product.get('title', 'Unknown Product'),
                        'vendor': product.get('vendor', 'Unknown Brand'),
                        'price': product.get('price', 'N/A'),
                        'stock': product.get('stock', 'N/A')
                    }
                    
                    all_responses.append(parsed_response)
                else:
                    # Handle individual product error
                    error_msg = f"Error for {product.get('title')}: {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail.get('error', error_detail.get('message', 'Unknown error'))}"
                    except:
                        error_msg += f" - {response.text}"
                    
                    all_responses.append({
                        'product': {
                            'id': product.get('id'),  # Add the product ID
                            'title': product.get('title', 'Unknown Product'),
                            'vendor': product.get('vendor', 'Unknown Brand'),
                            'price': product.get('price', 'N/A'),
                            'stock': product.get('stock', 'N/A')
                        },
                        'error': error_msg,
                        'summary': [],
                        'caption': '',
                        'image_prompts': []
                    })
                    
            except requests.exceptions.Timeout:
                all_responses.append({
                    'product': {
                        'title': product.get('title', 'Unknown Product'),
                        'vendor': product.get('vendor', 'Unknown Brand'),
                        'price': product.get('price', 'N/A'),
                        'stock': product.get('stock', 'N/A')
                    },
                    'error': f"Timeout error for {product.get('title')}",
                    'summary': [],
                    'caption': '',
                    'image_prompts': []
                })
            except Exception as e:
                all_responses.append({
                    'product': {
                        'title': product.get('title', 'Unknown Product'),
                        'vendor': product.get('vendor', 'Unknown Brand'),
                        'price': product.get('price', 'N/A'),
                        'stock': product.get('stock', 'N/A')
                    },
                    'error': f"Error for {product.get('title')}: {str(e)}",
                    'summary': [],
                    'caption': '',
                    'image_prompts': []
                })
        
        return jsonify({
            "success": True,
            "responses": all_responses,
            "products_processed": len(products)
        })
            
    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "error": "Writer AI request timed out"
        }), 408
    except requests.exceptions.RequestException as e:
        return jsonify({
            "success": False,
            "error": f"Network error: {str(e)}"
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }), 500

@app.route('/api/target', methods=['POST'])
def target_products():
    """Target selected products using Writer AI for better product descriptions."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        api_key = data.get('api_key')
        application_id = data.get('application_id')
        products = data.get('products', [])
        target_language = data.get('target_language', 'english')
        target_demographic = data.get('target_demographic', 'general')
        
        if not api_key or not application_id:
            return jsonify({"success": False, "error": "API key and application ID are required"}), 400
        
        if not products:
            return jsonify({"success": False, "error": "No products provided"}), 400
        
        # Make individual calls for each product to get enhanced descriptions
        writer_url = f"https://api.writer.com/v1/applications/{application_id}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        all_enhancements = []
        
        # Get the Shopify service to fetch individual products by ID
        service = get_shopify_service()
        
        for product in products:
            # Fetch the specific product by ID from Shopify to get full description
            product_id = str(product.get('id', ''))
            full_product_data = {}
            
            if product_id:
                try:
                    # Fetch the specific product from Shopify
                    result = service.get_product(product_id)
                    if result.get("success") and result.get("product"):
                        shopify_product = result["product"]
                        full_product_data = {
                            "id": shopify_product.get("id"),
                            "title": shopify_product.get("title", "No Title"),
                            "description": shopify_product.get("body_html", "No description available"),
                            "vendor": shopify_product.get("vendor", "Unknown"),
                            "product_type": shopify_product.get("product_type", ""),
                        }
                        print(f"DEBUG: Fetched product ID '{product_id}': '{full_product_data.get('title')}' - Description length: {len(full_product_data.get('description', ''))}")
                    else:
                        print(f"DEBUG: Failed to fetch product ID '{product_id}': {result.get('message', 'Unknown error')}")
                except Exception as e:
                    print(f"DEBUG: Error fetching product ID '{product_id}': {str(e)}")
            
            # Prepare detailed product information with language and demographic context
            product_details = f"""
Product: {product.get('title', 'Unknown Product')}
Brand/Vendor: {product.get('vendor', 'Unknown Brand')}
Price: {product.get('price', 'N/A')}
Stock Status: {product.get('stock', 'N/A')}
Product Type: {full_product_data.get('product_type', 'N/A')}
Target Language: {target_language.title()}
Target Demographic: {target_demographic.replace('-', ' ').title()}
            """.strip()
            
            # Get the full product description from Shopify (body_html)
            current_description = full_product_data.get('description', '').strip()
            if not current_description or current_description == 'No description available':
                current_description = f"Basic product listing for {product.get('title', 'Unknown Product')} from {product.get('vendor', 'Unknown Brand')} priced at {product.get('price', 'N/A')}"
            else:
                # Clean up HTML tags if present in the description
                import re
                current_description = re.sub(r'<[^>]+>', '', current_description)
                current_description = current_description.replace('&nbsp;', ' ').replace('&amp;', '&').strip()
            
            # Format the request for the enhancement agent with both required inputs
            payload = {
                "inputs": [
                    {
                        "id": "Product Details",
                        "value": [product_details]
                    },
                    {
                        "id": "Current Description", 
                        "value": [current_description]
                    }
                ]
            }
            
            print(f"DEBUG: Enhancing product '{product.get('title')}': {payload}")
            
            try:
                response = requests.post(writer_url, headers=headers, json=payload, timeout=60)
                
                if response.status_code == 200:
                    result = response.json()
                    raw_response = result.get('suggestion', 'No targeting received from Writer AI')
                    
                    # Parse the targeting response (it might have structured content)
                    enhancement_data = parse_targeting_response(raw_response)
                    
                    # Add product info to the response
                    enhancement_data['original_product'] = {
                        'id': product.get('id'),  # Add the product ID
                        'title': product.get('title', 'Unknown Product'),
                        'vendor': product.get('vendor', 'Unknown Brand'),
                        'price': product.get('price', 'N/A'),
                        'stock': product.get('stock', 'N/A')
                    }
                    
                    # Add the original description that was sent to the agent
                    enhancement_data['original_description'] = current_description
                    
                    all_enhancements.append(enhancement_data)
                else:
                    # Handle individual product error
                    error_msg = f"Error targeting {product.get('title')}: {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail.get('error', error_detail.get('message', 'Unknown error'))}"
                    except:
                        error_msg += f" - {response.text}"
                    
                    all_enhancements.append({
                        'original_product': {
                            'id': product.get('id'),  # Add the product ID
                            'title': product.get('title', 'Unknown Product'),
                            'vendor': product.get('vendor', 'Unknown Brand'),
                            'price': product.get('price', 'N/A'),
                            'stock': product.get('stock', 'N/A')
                        },
                        'original_description': current_description,
                        'error': error_msg,
                        'enhanced_description': '',
                        'improvements': []
                    })
                    
            except requests.exceptions.Timeout:
                all_enhancements.append({
                    'original_product': {
                        'id': product.get('id'),  # Add the product ID
                        'title': product.get('title', 'Unknown Product'),
                        'vendor': product.get('vendor', 'Unknown Brand'),
                        'price': product.get('price', 'N/A'),
                        'stock': product.get('stock', 'N/A')
                    },
                    'original_description': current_description,
                    'error': f"Timeout error for {product.get('title')}",
                    'enhanced_description': '',
                    'improvements': []
                })
            except Exception as e:
                all_enhancements.append({
                    'original_product': {
                        'id': product.get('id'),  # Add the product ID
                        'title': product.get('title', 'Unknown Product'),
                        'vendor': product.get('vendor', 'Unknown Brand'),
                        'price': product.get('price', 'N/A'),
                        'stock': product.get('stock', 'N/A')
                    },
                    'original_description': current_description,
                    'error': f"Error for {product.get('title')}: {str(e)}",
                    'enhanced_description': '',
                    'improvements': []
                })
        
        # Close the Shopify service connection
        service.close()
        
        return jsonify({
            "success": True,
            "enhancements": all_enhancements,
            "products_processed": len(products)
        })
            
    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "error": "Targeting request timed out"
        }), 408
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }), 500

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "message": "Shopify Product Showcase is running"})

@app.route('/api/dalle/debug', methods=['GET'])
def debug_dalle():
    """Debug endpoint to test DALL-E API authentication."""
    try:
        api_key_result = get_openai_api_key()
        
        if not api_key_result['success']:
            return jsonify({
                "success": False,
                "error": api_key_result.get('error'),
                "api_key_present": False
            })
        
        api_key = api_key_result['api_key']
        
        # Test a simple API call to check authentication
        print("🔍 Testing DALL-E API authentication...")
        test_prompt = "A simple red apple for API testing"
        
        api_result = make_dalle_api_call(test_prompt, api_key, size="1024x1024", quality="standard", n=1)
        
        debug_info = {
            "success": api_result['success'],
            "api_key": api_key[:8] + "...",
            "api_test_result": {
                "success": api_result['success'],
                "error": api_result.get('error')
            }
        }
        
        if api_result['success']:
            debug_info["message"] = "DALL-E API is working correctly"
        else:
            debug_info["solution"] = "Check your OpenAI API key and ensure you have sufficient credits"
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Debug test failed: {str(e)}"
        })

@app.route('/test-writer')
def test_writer():
    """Test Writer AI directly with a simple payload."""
    try:
        api_key = "zHPCT8S8UJh0z7jBPiXHWttThDiX1jZo"
        application_id = "573e34a0-fa17-4295-9126-9990c979f83c"
        
        writer_url = f"https://api.writer.com/v1/applications/{application_id}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": [
                {
                    "id": "Product Details",
                    "value": ["Test product: Smart Watch from TechCorp for $199.99"]
                }
            ]
        }
        
        print(f"TEST: Sending payload: {payload}")
        response = requests.post(writer_url, headers=headers, json=payload, timeout=30)
        print(f"TEST: Response status: {response.status_code}")
        print(f"TEST: Response text: {response.text}")
        
        if response.status_code == 200:
            return jsonify({"success": True, "response": response.json()})
        else:
            return jsonify({"success": False, "error": f"Status: {response.status_code}, Response: {response.text}"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/dalle/status', methods=['GET'])
def get_dalle_status():
    """Check DALL-E API key status."""
    try:
        api_key_result = get_openai_api_key()
        
        if api_key_result['success']:
            print("✅ OpenAI API key is configured")
            return jsonify({
                "success": True,
                "message": "OpenAI API key is configured",
                "api_key": api_key_result['api_key'][:8] + "..."
            })
        else:
            print(f"❌ OpenAI API key not configured: {api_key_result.get('error')}")
            return jsonify(api_key_result)
            
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"💥 {error_msg}")
        return jsonify({"success": False, "error": error_msg})

@app.route('/api/dalle/generate', methods=['POST'])
def generate_dalle_images():
    """Generate images using DALL-E API with fallback to Shopify images."""
    try:
        data = request.get_json() or {}
        api_key = data.get('api_key') or os.getenv('OPENAI_API_KEY')
        prompts = data.get('prompts', [])
        products = data.get('products', [])  # Optional: product data for fallback images
        reference_image_url = data.get('reference_image_url')  # Optional: reference image URL
        
        print(f"🎨 Generate request - API key present: {bool(api_key)}")
        print(f"🎨 Products for fallback: {len(products)} products provided")
        print(f"🎨 Reference image: {reference_image_url or 'None'}")
        
        if not api_key:
            return jsonify({
                "success": False, 
                "error": "API key is required. Provide api_key in request or set OPENAI_API_KEY environment variable."
            })
        
        if not prompts:
            return jsonify({"success": False, "error": "At least one prompt is required"})
        
        results = []
        
        for i, prompt in enumerate(prompts):
            try:
                # Validate and sanitize the prompt first
                is_safe, sanitized_prompt, safety_reason = validate_and_sanitize_prompt(prompt)
                
                if not is_safe:
                    print(f"⚠️ Skipping unsafe prompt: {safety_reason}")
                    results.append({
                        "prompt": prompt,
                        "images": [],
                        "error": f"Prompt rejected for safety: {safety_reason}"
                    })
                    continue
                
                # Use the sanitized prompt for generation
                actual_prompt = sanitized_prompt
                print(f"🔍 Using sanitized prompt: {actual_prompt[:100]}...")
                
                # Generate 1 image for each prompt
                prompt_images = []
                api_error_for_prompt = None
                
                # Make DALL-E API call with optional reference image
                api_result = make_dalle_api_call(actual_prompt, api_key, size="1024x1024", quality="standard", n=1, reference_image_url=reference_image_url)
                
                if api_result['success']:
                    response = api_result['response']
                    
                    if response.data and len(response.data) > 0:
                        image_data = response.data[0]
                        
                        prompt_images.append({
                            "url": image_data.url,
                            "revised_prompt": getattr(image_data, 'revised_prompt', actual_prompt),
                            "prompt": actual_prompt
                        })
                        print(f"✅ Generated image for prompt: {prompt[:50]}...")
                    else:
                        print(f"❌ No image data in DALL-E response")
                else:
                    api_error_for_prompt = api_result.get('error', 'Unknown API error')
                    print(f"DALL-E API error for prompt '{prompt}': {api_error_for_prompt}")
                
                # If DALL-E failed and we have no images, try to use Shopify product images as fallback
                if not prompt_images and products:
                    print(f"🔄 DALL-E failed, using Shopify product images as fallback for prompt: {prompt[:50]}...")
                    
                    # Find a product with images to use as fallback
                    for product in products:
                        product_images = product.get('images', [])
                        if product_images:
                            # Use the first available product image as fallback
                            fallback_image = {
                                "url": product_images[0],
                                "revised_prompt": f"Shopify product image for: {product.get('title', 'Unknown Product')}",
                                "prompt": actual_prompt,
                                "is_fallback": True,
                                "product_title": product.get('title', 'Unknown Product')
                            }
                            prompt_images.append(fallback_image)
                            print(f"✅ Using Shopify image fallback from product: {product.get('title', 'Unknown')}")
                            break
                
                # Determine if fallback was used
                used_fallback = len(prompt_images) > 0 and any(img.get('is_fallback') for img in prompt_images)
                
                # If we have images (either AI or fallback), no error should be shown
                error_message = None
                if not prompt_images:
                    error_message = api_error_for_prompt or f"Failed to generate images for prompt: {prompt}"
                elif used_fallback:
                    # When using fallback, we can optionally include an info message, but not an error
                    error_message = None
                
                results.append({
                    "prompt": prompt,
                    "images": prompt_images,
                    "error": error_message,
                    "used_fallback": used_fallback,
                    "fallback_info": "AI image generation unavailable - using Shopify product image" if used_fallback else None
                })
                
            except Exception as prompt_error:
                # Even in case of exception, try to use Shopify fallback
                fallback_images = []
                if products:
                    print(f"🔄 Exception occurred, trying Shopify fallback for prompt: {prompt[:50]}...")
                    for product in products:
                        product_images = product.get('images', [])
                        if product_images:
                            fallback_image = {
                                "url": product_images[0],
                                "revised_prompt": f"Shopify product image for: {product.get('title', 'Unknown Product')}",
                                "prompt": prompt,
                                "is_fallback": True,
                                "product_title": product.get('title', 'Unknown Product')
                            }
                            fallback_images.append(fallback_image)
                            print(f"✅ Exception fallback using product: {product.get('title', 'Unknown')}")
                            break
                
                results.append({
                    "prompt": prompt,
                    "images": fallback_images,
                    "error": str(prompt_error) if not fallback_images else None,
                    "used_fallback": len(fallback_images) > 0
                })
        
        return jsonify({
            "success": True, 
            "results": results
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/dalle/generate-with-product', methods=['POST'])
def generate_dalle_with_product():
    """Generate DALL-E images using a Shopify product as reference."""
    try:
        data = request.get_json() or {}
        api_key = data.get('api_key') or os.getenv('OPENAI_API_KEY')
        product_id = data.get('product_id')
        prompt = data.get('prompt', '')
        
        if not api_key:
            return jsonify({
                "success": False, 
                "error": "API key is required. Provide api_key in request or set OPENAI_API_KEY environment variable."
            })
        
        if not product_id:
            return jsonify({"success": False, "error": "Product ID is required"})
        
        # Fetch product details from Shopify
        try:
            product_id_int = int(product_id)
        except ValueError:
            return jsonify({"success": False, "error": "Invalid product ID format"})
        
        shopify_service = get_shopify_service()
        product_result = shopify_service.get_product(product_id_int)
        
        if not product_result.get("success"):
            return jsonify({
                "success": False,
                "error": f"Failed to fetch product: {product_result.get('error', 'Unknown error')}"
            })
        
        product_data = product_result["product"]
        product_images = product_data.get("images", [])
        
        if not product_images:
            return jsonify({
                "success": False,
                "error": "Product has no images to use as reference"
            })
        
        # Use the first product image as reference
        first_image = product_images[0]
        # Handle both string URLs and image objects
        if isinstance(first_image, dict):
            reference_image_url = first_image.get('src', first_image.get('url', ''))
        else:
            reference_image_url = first_image
        
        product_name = product_data.get("title", "product")
        
        # Create enhanced prompt if none provided
        if not prompt:
            prompt = f"Professional product photography of {product_name}, clean background, high quality commercial style"
        
        print(f"🎨 Generating with product reference: {product_name}")
        print(f"🎨 Reference image: {reference_image_url}")
        print(f"🎨 Prompt: {prompt}")
        
        # Generate image with reference
        api_result = make_dalle_api_call(prompt, api_key, size="1024x1024", quality="standard", n=1, reference_image_url=reference_image_url)
        
        if api_result['success']:
            response = api_result['response']
            
            if response.data and len(response.data) > 0:
                generated_image = response.data[0]
                
                return jsonify({
                    "success": True,
                    "image_url": generated_image.url,
                    "revised_prompt": generated_image.revised_prompt if hasattr(generated_image, 'revised_prompt') else prompt,
                    "product_data": {
                        "id": product_id,
                        "name": product_data.get("title"),
                        "category": product_data.get("product_type"),
                        "reference_image": reference_image_url
                    },
                    "used_reference": api_result.get('used_reference', False)
                })
            else:
                return jsonify({"success": False, "error": "No images generated"})
        else:
            return jsonify({
                "success": False,
                "error": api_result.get('error', 'DALL-E generation failed')
            })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/instagram/auth-url', methods=['GET'])
def get_instagram_auth_url():
    """Get Instagram authorization URL for OAuth flow."""
    try:
        app_id = os.getenv('INSTAGRAM_APP_ID')
        redirect_uri = f"{request.url_root}api/instagram/callback"
        
        if not app_id:
            return jsonify({
                "success": False,
                "error": "Instagram App ID not configured"
            })
        
        # Instagram Basic Display API OAuth URL
        auth_url = f"https://api.instagram.com/oauth/authorize?client_id={app_id}&redirect_uri={redirect_uri}&scope=user_profile,user_media&response_type=code"
        
        return jsonify({
            "success": True,
            "auth_url": auth_url,
            "message": "Instagram authorization URL generated"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to generate auth URL: {str(e)}"
        })

@app.route('/api/instagram/callback', methods=['GET'])
def instagram_callback():
    """Handle Instagram OAuth callback."""
    try:
        code = request.args.get('code')
        if not code:
            return jsonify({
                "success": False,
                "error": "No authorization code received"
            })
        
        # Exchange code for access token
        app_id = os.getenv('INSTAGRAM_APP_ID')
        app_secret = os.getenv('INSTAGRAM_APP_SECRET')
        redirect_uri = f"{request.url_root}api/instagram/callback"
        
        token_url = "https://api.instagram.com/oauth/access_token"
        token_data = {
            'client_id': app_id,
            'client_secret': app_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
            'code': code
        }
        
        response = requests.post(token_url, data=token_data, timeout=30)
        
        if response.status_code == 200:
            token_response = response.json()
            access_token = token_response.get('access_token')
            
            return jsonify({
                "success": True,
                "access_token": access_token,
                "message": "Instagram authorization successful! You can now post to Instagram."
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Failed to exchange code for token: {response.text}"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Callback error: {str(e)}"
        })

@app.route('/api/instagram/post', methods=['POST'])
def post_to_instagram_endpoint():
    """Post an image to Instagram."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        image_url = data.get('image_url')
        caption = data.get('caption', '')
        
        if not image_url:
            return jsonify({"success": False, "error": "Image URL is required"}), 400
        
        # Post to Instagram
        result = post_to_instagram(image_url, caption)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Instagram posting error: {str(e)}"
        }), 500

@app.route('/api/instagram/record', methods=['POST'])
def record_instagram_post():
    """Record an Instagram post to MongoDB with product data."""
    try:
        data = request.get_json()
        
        # Debug logging
        print(f"🔍 Received data: {data}")
        print(f"🔍 Data type: {type(data)}")
        
        if not data:
            print("❌ No data provided")
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        # Extract required data
        product_id = data.get('product_id')
        image_url = data.get('image_url')
        caption = data.get('caption', '')
        comment = data.get('comment', '')
        mockup_image_data = data.get('mockup_image_data')  # Frontend-captured mockup
        
        print(f"🔍 Extracted - product_id: {product_id}, image_url: {image_url}")
        print(f"🔍 Extracted - caption: {caption}, comment: {comment}")
        print(f"🔍 Extracted - mockup_image_data: {'Present' if mockup_image_data else 'Not provided'}")
        
        if not product_id:
            print("❌ Product ID is missing")
            return jsonify({"success": False, "error": "Product ID is required"}), 400
        
        if not image_url:
            print("❌ Image URL is missing")
            return jsonify({"success": False, "error": "Image URL is required"}), 400
        
        # Get MongoDB service
        mongodb_service = get_mongodb_service()
        
        # Get Shopify service to fetch product details
        shopify_service = get_shopify_service()
        
        try:
            # Convert product_id to integer (Shopify expects integer IDs)
            try:
                product_id_int = int(product_id)
            except (ValueError, TypeError) as e:
                print(f"❌ Invalid product ID format: {product_id}")
                return jsonify({
                    "success": False,
                    "error": f"Invalid product ID format: {product_id}"
                }), 400
            
            # Fetch product details from Shopify
            product_result = shopify_service.get_product(product_id_int)
            
            if not product_result.get("success"):
                return jsonify({
                    "success": False,
                    "error": f"Failed to fetch product details: {product_result.get('error', 'Unknown error')}"
                }), 400
            
            product_data = product_result["product"]
            
            # Extract product information
            product_name = product_data.get("title", "Unknown Product")
            product_category = product_data.get("product_type", "General")
            product_url = f"https://{os.getenv('SHOPIFY_SHOP_NAME', 'shop')}.myshopify.com/products/{product_data.get('handle', '')}"
            
            # Try screenshot service first (if configured)
            screenshot_service = get_screenshot_service()
            screenshot_result = None
            
            if screenshot_service.use_external_service and screenshot_service.api_key:
                print("📸 Attempting screenshot capture via HTML...")
                
                # URL encode the image URL for the proxy endpoint
                encoded_image_url = requests.utils.quote(image_url, safe='')
                
                # Convert DALL-E image to data URL for reliable screenshot capture
                try:
                    print("🔄 Converting DALL-E image to data URL...")
                    data_url_response = requests.post('http://localhost:8080/api/image-to-dataurl', 
                                                    json={'image_url': image_url}, 
                                                    timeout=30)
                    if data_url_response.status_code == 200:
                        data_url_data = data_url_response.json()
                        if data_url_data.get('success'):
                            screenshot_image_url = data_url_data['data_url']
                            print(f"✅ Converted to data URL: {len(screenshot_image_url)} chars")
                        else:
                            print("⚠️ Data URL conversion failed, using direct URL")
                            screenshot_image_url = image_url
                    else:
                        print("⚠️ Data URL conversion failed, using direct URL")
                        screenshot_image_url = image_url
                except Exception as e:
                    print(f"⚠️ Data URL conversion error: {e}, using direct URL")
                    screenshot_image_url = image_url
                
                # Generate the HTML for the Instagram preview
                likes = str(random.randint(500, 5000))
                
                # Read the profile logo SVG content to embed it directly
                profile_logo_svg = '''<svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .teal-shape { fill: #20B2AA; }
    </style>
  </defs>
  <!-- Top bean/comma shape (curved downwards and to the right) -->
  <path class="teal-shape" d="M20 12 C16 8, 8 12, 8 20 C8 28, 12 32, 20 36 C28 40, 36 40, 44 36 C48 34, 50 30, 50 26 C50 22, 48 18, 44 16 C40 14, 36 14, 32 16 C28 14, 24 14, 20 16 C18 14, 16 12, 20 12 Z"/>
  
  <!-- Bottom bean/comma shape (curved upwards and to the left) -->
  <path class="teal-shape" d="M44 52 C48 56, 56 52, 56 44 C56 36, 52 32, 44 28 C36 24, 28 24, 20 28 C16 30, 14 34, 14 38 C14 42, 16 46, 20 48 C24 50, 28 50, 32 48 C36 50, 40 50, 44 48 C46 50, 48 52, 44 52 Z"/>
</svg>'''
                
                preview_html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #fafafa;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }}
        .instagram-post {{
            width: 480px;
            background: white;
            border: 1px solid #dbdbdb;
            border-radius: 8px;
            overflow: hidden;
        }}
        .post-header {{
            display: flex;
            align-items: center;
            padding: 14px 16px;
            border-bottom: 1px solid #efefef;
        }}
        .profile-pic {{
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 12px;
            overflow: hidden;
        }}
        .profile-pic svg {{
            width: 100%;
            height: 100%;
        }}
        .username {{
            font-weight: 600;
            font-size: 14px;
            color: #262626;
            flex: 1;
        }}
        .username span {{
            display: block;
            font-weight: 400;
            font-size: 12px;
            color: #8e8e8e;
            margin-top: 2px;
        }}
        .post-image {{
            width: 100%;
            display: block;
            background: #f0f0f0;
        }}
        .post-actions {{
            display: flex;
            padding: 8px 16px;
            gap: 16px;
        }}
        .action-btn {{
            background: none;
            border: none;
            cursor: pointer;
            padding: 8px 0;
        }}
        .action-btn svg {{
            width: 24px;
            height: 24px;
            stroke: #262626;
            fill: none;
            stroke-width: 2;
        }}
        .post-likes {{
            padding: 0 16px 8px;
            font-weight: 600;
            font-size: 14px;
            color: #262626;
        }}
        .post-caption {{
            padding: 0 16px 16px;
            font-size: 14px;
            color: #262626;
            line-height: 18px;
        }}
        .post-caption .username {{
            font-weight: 600;
            margin-right: 8px;
            display: inline-block;
        }}
        .post-time {{
            padding: 0 16px 16px;
            font-size: 10px;
            color: #8e8e8e;
            text-transform: uppercase;
        }}
    </style>
</head>
<body>
    <div class="instagram-post">
        <div class="post-header">
            <div class="profile-pic">
                {profile_logo_svg}
            </div>
            <div class="username">
                SuperPossible
            </div>
            <button class="action-btn">
                <svg viewBox="0 0 24 24"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>
            </button>
        </div>
        <img src="{screenshot_image_url}" class="post-image" alt="{product_name}" crossorigin="anonymous">
        <div class="post-actions">
            <button class="action-btn">
                <svg viewBox="0 0 24 24"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
            </button>
            <button class="action-btn">
                <svg viewBox="0 0 24 24"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
            </button>
            <button class="action-btn">
                <svg viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
            <button class="action-btn" style="margin-left: auto;">
                <svg viewBox="0 0 24 24"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
            </button>
        </div>
        <div class="post-likes">{likes} likes</div>
        <div class="post-caption">
            <span class="username">SuperPossible</span> {caption}
        </div>
        <div class="post-time">Just now</div>
    </div>
    <script>
        // Ensure image is loaded before screenshot
        document.addEventListener('DOMContentLoaded', function() {{
            const img = document.querySelector('.post-image');
            if (img) {{
                // Force image to load
                img.style.display = 'block';
                img.style.visibility = 'visible';
                
                img.onload = function() {{
                    console.log('Image loaded successfully');
                    // Add a small delay to ensure rendering is complete
                    setTimeout(() => {{
                        console.log('Image rendering complete');
                    }}, 1000);
                }};
                img.onerror = function() {{
                    console.log('Image failed to load');
                }};
                
                // Trigger load if already cached
                if (img.complete) {{
                    img.onload();
                }}
            }}
        }});
    </script>
</body>
</html>'''
                
                # Capture screenshot from HTML
                screenshot_result = screenshot_service.capture_html(preview_html, width=480, height=700)
                
                if screenshot_result and screenshot_result.get("success"):
                    print("✅ Screenshot captured successfully from HTML")
                    mockup_image_data = screenshot_result['image_data']
                else:
                    print(f"⚠️  Screenshot service failed: {screenshot_result.get('error')}")
            
            # Use frontend-captured mockup if available, or screenshot if captured
            if mockup_image_data:
                print("📱 Using captured Instagram mockup")
                # Extract base64 data from data URL
                if mockup_image_data.startswith('data:image'):
                    base64_data = mockup_image_data.split(',', 1)[1]
                else:
                    base64_data = mockup_image_data
                
                # Upload frontend mockup to cloud storage
                cloud_storage = get_cloud_storage_service()
                upload_result = cloud_storage.upload_mockup(
                    base64_data, 
                    str(product_id), 
                    caption
                )
                
                if upload_result["success"]:
                    asset_urls = [upload_result['public_url']]
                    print(f"✅ Uploaded frontend-captured mockup: {upload_result['public_url']}")
                    mockup_result = {"success": True, "format": "jpeg"}
                else:
                    # Fallback to base64 data URL if cloud upload fails
                    asset_urls = [mockup_image_data]
                    print(f"⚠️ Cloud upload failed, using base64 fallback: {upload_result.get('error')}")
                    mockup_result = {"success": True, "format": "jpeg"}
            else:
                print("🎨 Generating new Instagram mockup (fallback)")
                # Create Instagram post mockup with caption overlay (fallback)
                mockup_result = create_instagram_preview_image(image_url, caption)
                
                if mockup_result["success"]:
                    # Upload mockup to cloud storage
                    cloud_storage = get_cloud_storage_service()
                    upload_result = cloud_storage.upload_mockup(
                        mockup_result['image_data'], 
                        str(product_id), 
                        caption
                    )
                    
                    if upload_result["success"]:
                        asset_urls = [upload_result['public_url']]
                        print(f"✅ Created and uploaded Instagram mockup: {upload_result['public_url']}")
                    else:
                        # Fallback to base64 data URL if cloud upload fails
                        mockup_data_url = f"data:image/{mockup_result['format']};base64,{mockup_result['image_data']}"
                        asset_urls = [mockup_data_url]
                        print(f"⚠️ Cloud upload failed, using base64 fallback: {upload_result.get('error')}")
                else:
                    # Fallback to original image URL
                    asset_urls = [image_url]
                    print(f"⚠️ Failed to create mockup: {mockup_result.get('error')}")
            
            # Create MongoDB record
            record_result = mongodb_service.create_instagram_post_record(
                product_id=str(product_id),
                product_url=product_url,
                asset_urls=asset_urls,
                product_name=product_name,
                product_category=product_category,
                caption=caption,
                user_name="AI Showcase"
            )
            
            if record_result["success"]:
                print(f"✅ Instagram post recorded successfully: {record_result['session_id']}")
                response_data = {
                    "success": True,
                    "message": "Instagram post recorded successfully",
                    "session_id": record_result["session_id"],
                    "record_id": record_result["record_id"],
                    "asset_url": asset_urls[0] if asset_urls else None,
                    "mockup_created": mockup_result["success"] if mockup_result else False,
                    "product_data": {
                        "name": product_name,
                        "category": product_category,
                        "url": product_url
                    }
                }
                
                # Add cloud storage info if available
                if mockup_result["success"] and 'upload_result' in locals():
                    response_data["cloud_storage"] = {
                        "uploaded": upload_result["success"],
                        "public_url": upload_result.get("public_url"),
                        "cloudinary_id": upload_result.get("cloudinary_id")
                    }
                
                return jsonify(response_data)
            else:
                return jsonify({
                    "success": False,
                    "error": f"Failed to record Instagram post: {record_result.get('error')}"
                }), 500
                
        finally:
            # Clean up services
            shopify_service.close()
            mongodb_service.disconnect()
        
    except Exception as e:
        error_msg = f"Instagram recording error: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@app.route('/api/instagram-preview/<session_id>')
def instagram_preview(session_id):
    """Serve a standalone Instagram preview HTML for screenshot capture."""
    try:
        # Get parameters from query string
        image_url = request.args.get('image_url', '')
        caption = request.args.get('caption', '')
        product_name = request.args.get('product_name', 'Product')
        likes = request.args.get('likes', str(random.randint(500, 5000)))
        
        if not image_url:
            return "Image URL required", 400
        
        # URL encode the image URL for the proxy endpoint
        encoded_image_url = requests.utils.quote(image_url, safe='')
        
        # Embed the profile logo SVG directly
        profile_logo_svg = '''<svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .teal-shape { fill: #20B2AA; }
    </style>
  </defs>
  <!-- Top bean/comma shape (curved downwards and to the right) -->
  <path class="teal-shape" d="M20 12 C16 8, 8 12, 8 20 C8 28, 12 32, 20 36 C28 40, 36 40, 44 36 C48 34, 50 30, 50 26 C50 22, 48 18, 44 16 C40 14, 36 14, 32 16 C28 14, 24 14, 20 16 C18 14, 16 12, 20 12 Z"/>
  
  <!-- Bottom bean/comma shape (curved upwards and to the left) -->
  <path class="teal-shape" d="M44 52 C48 56, 56 52, 56 44 C56 36, 52 32, 44 28 C36 24, 28 24, 20 28 C16 30, 14 34, 14 38 C14 42, 16 46, 20 48 C24 50, 28 50, 32 48 C36 50, 40 50, 44 48 C46 50, 48 52, 44 52 Z"/>
</svg>'''
        
        # Create a standalone Instagram mockup HTML
        html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #fafafa;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }}
        .instagram-post {{
            width: 480px;
            background: white;
            border: 1px solid #dbdbdb;
            border-radius: 8px;
            overflow: hidden;
        }}
        .post-header {{
            display: flex;
            align-items: center;
            padding: 14px 16px;
            border-bottom: 1px solid #efefef;
        }}
        .profile-pic {{
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: white;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 12px;
            overflow: hidden;
        }}
        .profile-pic svg {{
            width: 100%;
            height: 100%;
        }}
        .username {{
            font-weight: 600;
            font-size: 14px;
            color: #262626;
            flex: 1;
        }}
        .username span {{
            display: block;
            font-weight: 400;
            font-size: 12px;
            color: #8e8e8e;
            margin-top: 2px;
        }}
        .post-image {{
            width: 100%;
            display: block;
            background: #f0f0f0;
        }}
        .post-actions {{
            display: flex;
            padding: 8px 16px;
            gap: 16px;
        }}
        .action-btn {{
            background: none;
            border: none;
            cursor: pointer;
            padding: 8px 0;
        }}
        .action-btn svg {{
            width: 24px;
            height: 24px;
            stroke: #262626;
            fill: none;
            stroke-width: 2;
        }}
        .post-likes {{
            padding: 0 16px 8px;
            font-weight: 600;
            font-size: 14px;
            color: #262626;
        }}
        .post-caption {{
            padding: 0 16px 16px;
            font-size: 14px;
            color: #262626;
            line-height: 18px;
        }}
        .post-caption .username {{
            font-weight: 600;
            margin-right: 8px;
            display: inline-block;
        }}
        .post-time {{
            padding: 0 16px 16px;
            font-size: 10px;
            color: #8e8e8e;
            text-transform: uppercase;
        }}
    </style>
</head>
<body>
    <div class="instagram-post">
        <div class="post-header">
            <div class="profile-pic">
                {profile_logo_svg}
            </div>
            <div class="username">
                SuperPossible
            </div>
            <button class="action-btn">
                <svg viewBox="0 0 24 24"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>
            </button>
        </div>
        <img src="/api/proxy-image?url={encoded_image_url}" class="post-image" alt="{product_name}" crossorigin="anonymous">
        <div class="post-actions">
            <button class="action-btn">
                <svg viewBox="0 0 24 24"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
            </button>
            <button class="action-btn">
                <svg viewBox="0 0 24 24"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
            </button>
            <button class="action-btn">
                <svg viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
            <button class="action-btn" style="margin-left: auto;">
                <svg viewBox="0 0 24 24"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
            </button>
        </div>
        <div class="post-likes">{likes} likes</div>
        <div class="post-caption">
            <span class="username">SuperPossible</span> {caption}
        </div>
        <div class="post-time">Just now</div>
    </div>
</body>
</html>
        '''
        
        return html, 200, {'Content-Type': 'text/html'}
        
    except Exception as e:
        print(f"❌ Error generating preview: {e}")
        return str(e), 500

@app.route('/api/image-to-dataurl', methods=['POST'])
def image_to_dataurl():
    """Convert an image URL to a data URL for reliable screenshot capture."""
    try:
        data = request.get_json()
        image_url = data.get('image_url')
        
        if not image_url:
            return jsonify({'error': 'image_url is required'}), 400
        
        # Fetch the image
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # Convert to base64 data URL
        import base64
        from urllib.parse import urlparse
        
        # Determine content type
        content_type = response.headers.get('content-type', 'image/png')
        
        # Create data URL
        image_base64 = base64.b64encode(response.content).decode('utf-8')
        data_url = f"data:{content_type};base64,{image_base64}"
        
        return jsonify({
            'success': True,
            'data_url': data_url,
            'size': len(response.content)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/proxy-image', methods=['GET'])
def proxy_image():
    """Proxy external images to avoid CORS issues in html2canvas."""
    try:
        image_url = request.args.get('url')
        
        if not image_url:
            return jsonify({"success": False, "error": "URL parameter required"}), 400
        
        # Download the image
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        
        # Return the image with appropriate headers
        from flask import Response
        return Response(
            response.content,
            mimetype=response.headers.get('content-type', 'image/png'),
            headers={
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'public, max-age=3600'
            }
        )
        
    except Exception as e:
        print(f"❌ Image proxy error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Starting Shopify Product Showcase on port {port}")
    print(f"🌐 Access the app at: http://localhost:{port}")
    print(f"🧪 MongoDB test page: http://localhost:{port}/test-mongodb")
    print(f"📊 Health check: http://localhost:{port}/health")
    print(f"🛍️  API endpoint: http://localhost:{port}/api/products")
    print(f"✨ Writer AI endpoint: http://localhost:{port}/api/writer")
    print(f"🎨 DALL-E image generation: http://localhost:{port}/api/dalle/generate")
    print(f"🔍 DALL-E debug: http://localhost:{port}/api/dalle/debug")
    print(f"📱 Instagram auth: http://localhost:{port}/api/instagram/auth-url")
    print(f"📱 Instagram post: http://localhost:{port}/api/instagram/post")
    print(f"📱 Instagram record: http://localhost:{port}/api/instagram/record")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

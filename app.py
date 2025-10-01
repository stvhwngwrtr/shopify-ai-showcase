from flask import Flask, render_template, jsonify, request, send_from_directory
from shopify_service import get_shopify_service
import json
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time
import threading
import re

# Load environment variables
load_dotenv()

# Ensure required environment variables are set
if not os.getenv('SHOPIFY_SHOP_NAME'):
    print("⚠️ Warning: SHOPIFY_SHOP_NAME not set in environment variables")
if not os.getenv('SHOPIFY_ACCESS_TOKEN'):
    print("⚠️ Warning: SHOPIFY_ACCESS_TOKEN not set in environment variables")
if not os.getenv('OPENAI_API_KEY'):
    print("⚠️ Warning: OPENAI_API_KEY not set in environment variables")

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

def make_dalle_api_call(prompt, api_key, size="1024x1024", quality="standard", n=1):
    """Make a DALL-E API call to generate images."""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key)
        
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality=quality,
            n=n
        )
        
        return {
            'success': True,
            'response': response
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

@app.route('/logo.svg')
def serve_logo():
    """Serve the Writer logo SVG file."""
    return send_from_directory('.', 'logo.svg', mimetype='image/svg+xml')

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
        
        print(f"🎨 Generate request - API key present: {bool(api_key)}")
        print(f"🎨 Products for fallback: {len(products)} products provided")
        
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
                
                # Make DALL-E API call
                api_result = make_dalle_api_call(actual_prompt, api_key, size="1024x1024", quality="standard", n=1)
                
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Starting Shopify Product Showcase on port {port}")
    print(f"🌐 Access the app at: http://localhost:{port}")
    print(f"📊 Health check: http://localhost:{port}/health")
    print(f"🛍️  API endpoint: http://localhost:{port}/api/products")
    print(f"✨ Writer AI endpoint: http://localhost:{port}/api/writer")
    print(f"🎨 DALL-E image generation: http://localhost:{port}/api/dalle/generate")
    print(f"🔍 DALL-E debug: http://localhost:{port}/api/dalle/debug")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

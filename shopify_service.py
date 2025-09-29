import shopify
import os
import random
from typing import Optional, Dict, Any, List


class ShopifyService:
    """Simple service for Shopify Admin API operations."""
    
    def __init__(self, shop_name: str, access_token: str, api_version: str = "2023-10"):
        """Initialize with Shopify credentials.
        
        Args:
            shop_name: Your Shopify shop name (without .myshopify.com)
            access_token: Your Shopify access token
            api_version: API version to use
        """
        self.shop_name = shop_name
        self.access_token = access_token
        self.api_version = api_version
        self.shop_url = f"{shop_name}.myshopify.com"
        self._session: Optional[shopify.Session] = None
    
    def _get_session(self) -> shopify.Session:
        """Get or create Shopify session."""
        if not self._session:
            # Clear any existing sessions first
            shopify.ShopifyResource.clear_session()
            print(f"DEBUG: Creating session with shop_url='{self.shop_url}', api_version='{self.api_version}'")
            self._session = shopify.Session(self.shop_url, self.api_version, self.access_token)
            shopify.ShopifyResource.activate_session(self._session)
            print(f"DEBUG: Session activated, site={shopify.ShopifyResource.site}")
        return self._session
    
    def get_product(self, product_id: int) -> Dict[str, Any]:
        """Get a product by ID.
        
        Args:
            product_id: Shopify product ID
            
        Returns:
            Dict with product data or error message
        """
        session = self._get_session()
        
        try:
            product = shopify.Product.find(product_id)
            return {
                "success": True,
                "product": product.to_dict()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to fetch product {product_id}"
            }
    
    def list_products(self, limit: int = 50) -> Dict[str, Any]:
        """List products from the store.
        
        Args:
            limit: Maximum number of products to return
            
        Returns:
            Dict with products list or error message
        """
        session = self._get_session()
        
        try:
            products = shopify.Product.find(limit=limit)
            return {
                "success": True,
                "products": [product.to_dict() for product in products],
                "count": len(products)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to fetch products: {str(e)}"
            }
    
    def list_random_products(self, count: int = 10, max_fetch: int = 100) -> Dict[str, Any]:
        """List random products from the store.
        
        Args:
            count: Number of random products to return
            max_fetch: Maximum number of products to fetch for random selection
            
        Returns:
            Dict with random products list or error message
        """
        session = self._get_session()
        
        try:
            # First, get the total count of products
            all_products = shopify.Product.find(limit=250)  # Shopify's max limit
            total_products = len(all_products)
            
            if total_products == 0:
                return {
                    "success": True,
                    "products": [],
                    "count": 0
                }
            
            # If we have fewer products than requested, return all
            if total_products <= count:
                return {
                    "success": True,
                    "products": [product.to_dict() for product in all_products],
                    "count": total_products
                }
            
            # Randomly select the requested number of products
            selected_products = random.sample(all_products, min(count, total_products))
            
            return {
                "success": True,
                "products": [product.to_dict() for product in selected_products],
                "count": len(selected_products)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to fetch random products: {str(e)}"
            }
    
    def close(self):
        """Clear Shopify session (call when done)."""
        if self._session:
            shopify.ShopifyResource.clear_session()
            self._session = None


# Simple usage example:

def get_shopify_service():
    """Get configured Shopify service instance."""
    # Clear any existing Shopify sessions first
    try:
        import shopify
        shopify.ShopifyResource.clear_session()
    except:
        pass
    
    # Get credentials from environment variables
    shop_name = os.getenv('SHOPIFY_SHOP_NAME')
    access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
    
    if not shop_name or not access_token:
        raise ValueError("SHOPIFY_SHOP_NAME and SHOPIFY_ACCESS_TOKEN environment variables are required")
    
    print(f"DEBUG: Creating service with shop_name='{shop_name}', token='{access_token[:10]}...'")
    
    return ShopifyService(shop_name=shop_name, access_token=access_token)


def main():
    # Initialize service with your credentials
    service = get_shopify_service()
    
    # List products
    products = service.list_products(limit=10)
    if products["success"]:
        print(f"📦 Found {products['count']} products")
        for product in products["products"][:3]:  # Show first 3
            print(f"  - {product['title']} (${product['variants'][0]['price'] if product['variants'] else 'N/A'})")
    else:
        print(f"❌ Error: {products['message']}")
    
    # Clean up when done (optional but recommended)
    service.close()

if __name__ == "__main__":
    main()

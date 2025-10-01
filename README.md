# 🛍️ Shopify Product Showcase with AI

A powerful Flask web application that integrates with Shopify API to showcase products with AI-powered content generation using Writer AI and OpenAI DALL-E.

![Python](https://img.shields.io/badge/python-v3.9+-blue.svg)
![Flask](https://img.shields.io/badge/flask-v2.3+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 🌟 Overview

Transform your Shopify store into an AI-powered marketing machine! This application fetches products from your Shopify store and uses advanced AI to generate compelling marketing content, social media posts, and stunning product images.

## Features

- 🛍️ **Shopify Integration**: Fetches products directly from your Shopify store
- 🤖 **Writer AI Integration**: Generate marketing content, captions, and Instagram posts
- 🎨 **OpenAI DALL-E Integration**: AI-powered image generation for products
- 📝 **Product Enhancement**: Improve product descriptions with AI targeting
- 🌍 **Multi-language Support**: Target different languages and demographics
- 🔄 **Real-time Refresh**: Update product data on demand
- 🐳 **Docker Ready**: Containerized for easy deployment
- ☁️ **Cloud Deployable**: Ready for Railway, Render, Heroku, and more

## Quick Start

### Prerequisites

- Python 3.9+
- Shopify store with API access
- Writer AI API account (optional)
- OpenAI API account (optional)
- Docker (optional, for containerized deployment)

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/shopify-ai-showcase.git
cd shopify-ai-showcase
```

### 2. Configure Shopify API

Copy the environment template and update with your credentials:

```bash
cp env.example .env
```

Edit `.env` with your Shopify details:

```bash
SHOPIFY_SHOP_NAME=your_shop_name
SHOPIFY_ACCESS_TOKEN=your_access_token
```

### 3. Test Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python3 app.py
```

### 4. Deploy with Docker

```bash
# Quick deployment
./deploy.sh

# Or manually
docker-compose up -d
```

The app will be available at `http://localhost:8080`

## Shopify API Setup

### Getting Your Credentials

1. **Go to your Shopify Admin** → Apps → Manage private apps
2. **Create a new private app** with these permissions:
   - `read_products`
   - `read_inventory`
3. **Copy your credentials**:
   - Shop name (without .myshopify.com)
   - Access token

### API Permissions Required

- `read_products` - To fetch product data
- `read_inventory` - To get stock levels

## Deployment Options

### Docker (Recommended)

```bash
# Build and run
docker build -t shopify-showcase .
docker run -p 8080:8080 -e SHOPIFY_SHOP_NAME=your_shop -e SHOPIFY_ACCESS_TOKEN=your_token shopify-showcase
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Cloud Deployment

#### Railway
1. Connect your GitHub repository
2. Set environment variables in Railway dashboard
3. Deploy automatically

#### Render
1. Create new Web Service
2. Connect repository
3. Set environment variables
4. Deploy

#### Heroku
```bash
# Install Heroku CLI
heroku create your-app-name
heroku config:set SHOPIFY_SHOP_NAME=your_shop
heroku config:set SHOPIFY_ACCESS_TOKEN=your_token
git push heroku main
```

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard with product showcase |
| `/api/products` | GET | Fetch Shopify products as JSON |
| `/api/writer` | POST | Generate marketing content with Writer AI |
| `/api/target` | POST | Enhance product descriptions |
| `/api/dalle/generate` | POST | Generate product images with OpenAI DALL-E |
| `/api/dalle/debug` | GET | Test DALL-E API authentication |
| `/health` | GET | Health check endpoint |

## 🤖 AI Features

### Writer AI Integration
- **Content Generation**: Create Instagram posts, captions, and marketing copy
- **Product Enhancement**: Improve product descriptions with AI targeting
- **Multi-language Support**: Generate content in different languages
- **Demographic Targeting**: Tailor content for specific audiences

### OpenAI DALL-E Integration
- **Image Generation**: Create stunning product images from text prompts
- **Automatic Fallback**: Uses Shopify product images when AI generation fails
- **Batch Processing**: Generate multiple images simultaneously
- **Safety Filtering**: Built-in prompt validation and sanitization

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `SHOPIFY_SHOP_NAME` | Your Shopify shop name | ✅ | `superpossible` |
| `SHOPIFY_ACCESS_TOKEN` | Your Shopify access token | ✅ | (required) |
| `SHOPIFY_API_VERSION` | API version to use | ❌ | `2023-10` |
| `OPENAI_API_KEY` | OpenAI API Key for DALL-E | ❌ | (optional) |
| `DEBUG` | Enable debug mode | ❌ | `False` |
| `PORT` | Application port | ❌ | `8080` |

### Product Data Structure

The app fetches and displays:

- **Basic Info**: Title, description, vendor, product type
- **Pricing**: Price, compare-at-price
- **Inventory**: Stock levels, availability
- **Media**: Product images
- **Variants**: Size, color, and other options

## API Endpoints

The app uses the Shopify Admin API:

- `GET /admin/api/2024-07/products.json?limit=10` - Fetch products
- `GET /admin/api/2024-07/products/{id}.json` - Get specific product

## Troubleshooting

### Common Issues

1. **"Failed to connect to Shopify API"**
   - Check your credentials
   - Verify API permissions
   - Ensure shop name is correct

2. **"No products found"**
   - Check if your store has products
   - Verify API permissions include `read_products`

3. **Docker build fails**
   - Check Docker is running
   - Verify all files are present

### Debug Mode

Enable debug logging:

```bash
export DEBUG=1
python3 main.py
```

## Development

### Project Structure

```
hello-world/
├── app.py                 # Main Flask application with AI integrations
├── shopify_service.py     # Shopify API integration service
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
├── env.example           # Environment variables template
├── logo.svg              # Application logo
├── static/
│   └── favicon.png       # Web favicon
└── templates/
    └── index.html        # HTML template
```

### Adding Features

1. **New Product Fields**: Update `fetch_shopify_products()` in `app.py`
2. **UI Changes**: Modify the Flask templates in `templates/`
3. **API Endpoints**: Add new routes to `app.py` or methods to `shopify_service.py`
4. **AI Features**: Extend Writer AI or DALL-E integrations in `app.py`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

- **Writer Framework**: https://dev.writer.com/framework
- **Shopify API**: https://shopify.dev/docs/admin-api
- **Issues**: Create an issue in this repository

---

Built with ❤️ using Writer Framework and Shopify API

# 🚀 Deploy to Render - Step by Step Guide

This guide will help you deploy your Shopify AI Showcase webapp to Render.com for public access.

## Prerequisites

Before you begin, make sure you have:

1. **A GitHub account** (required for Render deployment)
2. **Your Shopify credentials**:
   - Shop name (without .myshopify.com)
   - Access token with `read_products` and `read_inventory` permissions
3. **Optional AI service credentials**:
   - Writer AI API key and application ID
   - OpenAI API key for DALL-E image generation
   - Instagram Business account with API access

## Step 1: Push Your Code to GitHub

If you haven't already, push your code to a GitHub repository:

```bash
# Initialize git repository (if not already done)
git init
git add .
git commit -m "Initial commit - Shopify AI Showcase"

# Create a new repository on GitHub, then:
git remote add origin https://github.com/yourusername/your-repo-name.git
git branch -M main
git push -u origin main
```

## Step 2: Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up with your GitHub account
3. Authorize Render to access your repositories

## Step 3: Deploy Your Web Service

1. **Click "New +" → "Web Service"**
2. **Connect your GitHub repository**
   - Select your repository from the list
   - Choose the `main` branch
3. **Configure your service**:
   - **Name**: `shopify-ai-showcase` (or your preferred name)
   - **Runtime**: `Docker` (automatically detected from Dockerfile)
   - **Region**: Choose closest to your users
   - **Branch**: `main`
   - **Dockerfile Path**: `./Dockerfile` (should be auto-detected)

## Step 4: Set Environment Variables

In the Render dashboard, scroll down to "Environment Variables" and add:

### Required Variables
```
SHOPIFY_SHOP_NAME=your_actual_shop_name
SHOPIFY_ACCESS_TOKEN=your_actual_access_token
```

### Optional Variables (for AI features)
```
OPENAI_API_KEY=your_openai_api_key
INSTAGRAM_APP_ID=your_instagram_app_id
INSTAGRAM_APP_SECRET=your_instagram_app_secret
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token
```

### System Variables (usually defaults are fine)
```
PORT=8080
DEBUG=false
SHOPIFY_API_VERSION=2023-10
```

## Step 5: Deploy

1. **Click "Create Web Service"**
2. Render will automatically:
   - Build your Docker container
   - Deploy to their infrastructure
   - Provide you with a public URL

The deployment process typically takes 3-5 minutes.

## Step 6: Verify Deployment

Once deployed, you'll get a URL like: `https://your-service-name.onrender.com`

Test these endpoints:
- **Main app**: `https://your-service-name.onrender.com/`
- **Health check**: `https://your-service-name.onrender.com/health`
- **API**: `https://your-service-name.onrender.com/api/products`

## Environment Variables Reference

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `SHOPIFY_SHOP_NAME` | Your shop name without .myshopify.com | ✅ | `my-awesome-store` |
| `SHOPIFY_ACCESS_TOKEN` | Shopify Admin API access token | ✅ | `shpat_xxxxx` |
| `SHOPIFY_API_VERSION` | Shopify API version | ❌ | `2023-10` |
| `OPENAI_API_KEY` | OpenAI API key for DALL-E | ❌ | `sk-xxxxx` |
| `INSTAGRAM_APP_ID` | Instagram App ID | ❌ | `123456789` |
| `INSTAGRAM_APP_SECRET` | Instagram App Secret | ❌ | `abcdef123456` |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram Access Token | ❌ | `IGQVJ...` |
| `DEBUG` | Enable debug mode | ❌ | `false` |
| `PORT` | Application port | ❌ | `8080` |

## Troubleshooting

### Common Issues

1. **Build Fails**
   - Check that all files are committed to GitHub
   - Verify Dockerfile syntax
   - Check requirements.txt for valid packages

2. **App Starts but Shows Errors**
   - Verify environment variables are set correctly
   - Check logs in Render dashboard
   - Test Shopify credentials locally first

3. **Shopify Connection Issues**
   - Verify shop name (no .myshopify.com suffix)
   - Check access token permissions
   - Ensure token hasn't expired

### Viewing Logs

In your Render dashboard:
1. Go to your service
2. Click on "Logs" tab
3. View real-time application logs

### Updating Your Deployment

To update your app:
1. Push changes to your GitHub repository
2. Render will automatically redeploy
3. Or manually trigger deployment in Render dashboard

## Free Tier Limitations

Render's free tier includes:
- ✅ 750 hours/month (enough for always-on)
- ✅ Custom domains
- ✅ Automatic SSL
- ❌ May spin down after 15 minutes of inactivity
- ❌ Cold start delays (30-60 seconds)

For production use, consider upgrading to a paid plan for:
- No spin-down
- Faster performance
- More resources

## Custom Domain (Optional)

To use your own domain:
1. In Render dashboard, go to your service
2. Click "Settings" → "Custom Domains"
3. Add your domain
4. Update your DNS records as instructed

## Security Best Practices

1. **Never commit secrets** to your repository
2. **Use environment variables** for all sensitive data
3. **Regularly rotate** API tokens
4. **Monitor logs** for suspicious activity
5. **Keep dependencies updated**

## Next Steps

Once deployed, you can:
- Share your public URL with others
- Set up monitoring and alerts
- Configure custom domains
- Scale up for production traffic
- Add CI/CD workflows

## Support

- **Render Docs**: https://render.com/docs
- **Shopify API**: https://shopify.dev/docs
- **This App**: Check GitHub issues or create new ones

---

🎉 **Congratulations!** Your Shopify AI Showcase is now live on the internet!


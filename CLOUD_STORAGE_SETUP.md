# Cloud Storage Setup Guide

## Overview
The Instagram mockup system now supports uploading images to cloud storage for public URLs instead of storing large base64 data in MongoDB.

## Supported Cloud Providers

### 1. Cloudinary (Recommended - Easiest Setup)
**Pros**: Developer-friendly, automatic optimization, free tier
**Cons**: Slightly more expensive at scale

**Setup Steps**:
1. Sign up at [cloudinary.com](https://cloudinary.com)
2. Get your credentials from the dashboard
3. Add to `.env` file:
   ```
   CLOUDINARY_CLOUD_NAME=your_cloud_name
   CLOUDINARY_API_KEY=your_api_key
   CLOUDINARY_API_SECRET=your_api_secret
   ```

**Free Tier**: 25GB storage, 25GB bandwidth/month

### 2. AWS S3 (Most Popular)
**Pros**: Industry standard, very reliable, extensive ecosystem
**Cons**: More complex setup, requires AWS account

**Setup Steps**:
1. Create AWS account
2. Create S3 bucket with public read access
3. Create IAM user with S3 permissions
4. Install boto3: `pip install boto3`
5. Add to `.env`:
   ```
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_S3_BUCKET=your_bucket_name
   AWS_REGION=us-east-1
   ```

### 3. Google Cloud Storage
**Pros**: Good integration with Google services, competitive pricing
**Cons**: Requires Google Cloud account

**Setup Steps**:
1. Create Google Cloud account
2. Enable Cloud Storage API
3. Create bucket with public access
4. Create service account with Storage Admin role
5. Install google-cloud-storage: `pip install google-cloud-storage`

### 4. Cloudflare R2 (Cheapest)
**Pros**: S3-compatible, no egress fees, very cheap
**Cons**: Newer service, less ecosystem

**Setup Steps**:
1. Create Cloudflare account
2. Enable R2 service
3. Create bucket
4. Generate API token
5. Use S3-compatible configuration

## Implementation Status

✅ **Cloudinary**: Fully implemented and ready to use
🔄 **AWS S3**: Can be implemented (requires boto3 integration)
🔄 **Google Cloud**: Can be implemented (requires gcs integration)
🔄 **Cloudflare R2**: Can be implemented (S3-compatible)

## Current Behavior

### With Cloud Storage Configured:
- Creates Instagram mockup with caption overlay
- Uploads to cloud storage (Cloudinary)
- Stores public URL in MongoDB
- Returns public URL in API response

### Without Cloud Storage:
- Creates Instagram mockup with caption overlay
- Falls back to base64 data URL
- Stores base64 in MongoDB
- Returns base64 data URL in API response

## API Response Examples

### With Cloud Storage:
```json
{
  "success": true,
  "asset_url": "https://res.cloudinary.com/your-cloud/image/upload/v1/mockups/instagram_mockup_9156912087296.jpg",
  "cloud_storage": {
    "uploaded": true,
    "public_url": "https://res.cloudinary.com/your-cloud/image/upload/v1/mockups/instagram_mockup_9156912087296.jpg",
    "cloudinary_id": "mockups/instagram_mockup_9156912087296"
  }
}
```

### Without Cloud Storage (Fallback):
```json
{
  "success": true,
  "asset_url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAUDBAQEAwUEBAQFBQUGBwwIBwcHBw8LCwkMEQ8SEhEPERETFhwXExQaFRERGCEYGh0dHx8fExciJCIeJBweHx7/2wBDAQUFBQcGBw4ICA4eFBEUHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh7/wAARCAQ4BDgDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSE...",
  "cloud_storage": {
    "uploaded": false,
    "error": "Cloud storage not configured"
  }
}
```

## Next Steps

1. **Choose a cloud provider** based on your needs
2. **Set up credentials** in your `.env` file
3. **Test the integration** using the test script
4. **Monitor usage** and costs
5. **Consider implementing** additional providers if needed

## Cost Comparison (Approximate)

| Provider | Storage (per GB/month) | Bandwidth (per GB) | Free Tier |
|----------|----------------------|-------------------|-----------|
| Cloudinary | $0.10 | $0.10 | 25GB storage + 25GB bandwidth |
| AWS S3 | $0.023 | $0.09 | 5GB storage + 1GB bandwidth |
| Google Cloud | $0.020 | $0.12 | 5GB storage + 1GB bandwidth |
| Cloudflare R2 | $0.015 | $0.00* | 10GB storage + unlimited bandwidth |

*First 10GB bandwidth free per month

# Cloudflare R2 Setup for Card Assets

This document explains how card assets are integrated with Cloudflare R2 and how to configure different environments.

## Overview

Card artwork is served from Cloudflare R2 (object storage) via the public URL: `https://assets.drawtwo.com`

Example card URL structure:
```
https://assets.drawtwo.com/titles/{title_slug}/cards/{card_slug}.webp
```

For the "Archetype" title, the "Zap" card would be at:
```
https://assets.drawtwo.com/titles/archetype/cards/zap.webp
```

## Architecture

The backend generates card art URLs dynamically based on configuration:
- **Production**: Uses Cloudflare R2 public URL
- **Local Dev**: Can use R2 URLs (read-only) OR fallback to local media files
- **Frontend**: Receives complete URLs from backend API (no frontend config needed)

## Environment Configuration

### Production Setup

1. Copy `production.env.template` to `production.env`
2. Fill in your Cloudflare R2 credentials:

```bash
# Public URL (not secret)
CARD_ASSETS_BASE_URL=https://assets.drawtwo.com

# R2 API credentials (secret - for uploading assets)
R2_ACCOUNT_ID=your_cloudflare_account_id
R2_ACCESS_KEY_ID=your_r2_access_key_id
R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
R2_BUCKET_NAME=drawtwo-assets
```

3. Run with production config:
```bash
docker compose -f docker-compose.production.yml --env-file production.env up
```

### Local Development Setup

You have 3 options for local development:

#### Option 1: Use R2 for Reading (Recommended for Testing)
Best for testing the production asset pipeline without uploading.

1. Copy `local.env.template` to `.env`
2. Set only the public URL:
```bash
CARD_ASSETS_BASE_URL=https://assets.drawtwo.com
# Leave R2 credentials empty - read-only mode
```

3. Run normally:
```bash
docker compose up
```

The app will fetch card images from R2 but won't be able to upload.

#### Option 2: Use R2 with Write Access
If you need to test uploading assets locally (requires your own R2 credentials).

1. Copy `local.env.template` to `.env`
2. Fill in all R2 credentials (use your personal R2 account)
3. Run normally

⚠️ **Important**: Never commit `.env` files with real credentials!

#### Option 3: Local Files Only (No R2)
If you don't need card images or want to develop offline.

1. Don't create a `.env` file (or leave `CARD_ASSETS_BASE_URL` empty)
2. Place card images in: `backend/media/titles/{title_slug}/cards/{card_slug}.webp`
3. Run normally

The app will serve images from local media folder.

## How It Works

### Backend
- **Settings**: `backend/config/settings/base.py` reads R2 config from environment
- **URL Generation**: `backend/apps/core/card_assets.py` generates URLs based on config
- **Serialization**: `backend/apps/core/serializers.py` includes `art_url` in card data

### Frontend
- Receives complete URLs from backend API
- No R2 configuration needed
- Images load via standard `<img>` tags with backend-provided URLs

## Security

✅ **Safe to commit:**
- `production.env.template`
- `local.env.template`
- Public asset URLs

❌ **Never commit:**
- `production.env`
- `.env`
- `.env.local`
- Any file with R2 API credentials

All sensitive files are in `.gitignore`.

## Testing the Integration

1. Start your local environment
2. Navigate to a title with cards (e.g., `/titles/archetype`)
3. Check browser DevTools Network tab
4. Verify card images load from:
   - R2: `https://assets.drawtwo.com/...` (if configured)
   - Local: `http://localhost:8000/media/...` (if R2 not configured)

## Uploading Assets to R2

(To be implemented: Upload scripts/management commands)

For now, assets are uploaded manually to R2 bucket with the structure:
```
drawtwo-assets/
  titles/
    archetype/
      cards/
        zap.webp
        fireball.webp
        ...
      card_back.webp
    another-title/
      cards/
        ...
```

## Troubleshooting

**Images not loading?**
- Check `CARD_ASSETS_BASE_URL` in your environment config
- Verify R2 bucket has public read access
- Check browser console for CORS errors

**Want to switch from R2 to local files?**
- Remove or comment out `CARD_ASSETS_BASE_URL` in your `.env`
- Restart the backend

**Production not using R2?**
- Verify `production.env` has `CARD_ASSETS_BASE_URL` set
- Check Docker container can read environment variables
- Look for Django startup logs

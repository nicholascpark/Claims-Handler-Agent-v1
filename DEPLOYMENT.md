# Deployment Guide for Render

This guide will help you deploy your IntactBot FNOL Agent to Render.

## Prerequisites

1. A Render account (sign up at [render.com](https://render.com))
2. Your Azure OpenAI credentials
3. This repository pushed to GitHub/GitLab

## Deployment Steps

### 1. Connect Your Repository

1. Go to your Render dashboard
2. Click "New +" and select "Blueprint"
3. Connect your GitHub/GitLab repository
4. Render will automatically detect the `render.yaml` file

### 2. Set Environment Variables

In the Render dashboard, you'll need to set these environment variables for the **backend service**:

#### Required Variables
```
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2025-01-01-preview
AZURE_DEPLOYMENT_NAME=gpt-4o-quick
AZURE_STT_DEPLOYMENT_NAME=whisper
AZURE_TTS_DEPLOYMENT_NAME=tts
```

#### Optional Variables
```
OPENAI_API_KEY=your_openai_api_key_here
TEMPERATURE=0.1
MAX_TOKENS=1000
ENABLE_LLM_CACHING=true
ENABLE_PAYLOAD_CACHING=true
```

### 3. Deploy

1. After connecting your repo and setting environment variables, click "Apply"
2. Render will build and deploy both services:
   - **Backend**: Python API service
   - **Frontend**: Static React site

### 4. Service URLs

After deployment, you'll get URLs like:
- Backend: `https://intactbot-backend-xxx.onrender.com`
- Frontend: `https://intactbot-frontend-xxx.onrender.com`

The frontend will automatically be configured to use the backend URL.

## Manual Deployment (Alternative)

If you prefer to deploy services individually:

### Backend Service

1. Create a new "Web Service" in Render
2. Connect your repository
3. Set these build settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python backend.py`
   - **Environment**: `Python 3`
4. Add the environment variables listed above

### Frontend Service

1. Create a new "Static Site" in Render
2. Connect your repository
3. Set these build settings:
   - **Build Command**: `cd frontend && npm ci && npm run build`
   - **Publish Directory**: `frontend/build`
   - **Environment Variables**: 
     - `REACT_APP_API_URL`: Set to your backend service URL

## Testing Your Deployment

1. Visit your frontend URL
2. The app should load and connect to the backend
3. Test the chat functionality
4. Check the `/health` endpoint on your backend URL

## Troubleshooting

### Common Issues

1. **CORS Errors**: Make sure your frontend URL is properly configured in the backend CORS settings
2. **Environment Variables**: Double-check all required variables are set
3. **Build Failures**: Check the build logs in Render dashboard

### Health Check

Visit `https://your-backend-url.onrender.com/health` to verify the backend is running.

## Updating Your Deployment

1. Push changes to your repository
2. Render will automatically rebuild and redeploy
3. For environment variable changes, update them in the Render dashboard

## Cost Optimization

- Both services are configured to use the "Starter" plan
- Consider upgrading to "Standard" plan for production use
- The backend will sleep after 15 minutes of inactivity on the free tier

## Security Notes

- Never commit API keys to your repository
- Use Render's environment variable system for sensitive data
- Consider restricting CORS origins for production use 
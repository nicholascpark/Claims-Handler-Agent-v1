#!/bin/bash
# Start script for FNOL Voice Agent Frontend

echo "🚀 Starting FNOL Voice Agent Frontend..."

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Check if logo exists
if [ ! -f "public/intactbot_logo.png" ]; then
    echo "⚠️  Warning: intactbot_logo.png not found in public directory"
    echo "Please copy the logo to frontend/public/intactbot_logo.png"
fi

# Start development server
echo "✅ Starting development server on http://localhost:3000"
npm run dev

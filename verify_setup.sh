#!/bin/bash
# Verification script for FNOL Voice Agent setup

echo "🔍 FNOL Voice Agent - Setup Verification"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track issues
ISSUES=0

# Function to check file exists
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 ${RED}(missing)${NC}"
        ISSUES=$((ISSUES + 1))
        return 1
    fi
}

# Function to check directory exists
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        return 0
    else
        echo -e "${RED}✗${NC} $1/ ${RED}(missing)${NC}"
        ISSUES=$((ISSUES + 1))
        return 1
    fi
}

# Function to check command exists
check_command() {
    if command -v "$1" &> /dev/null; then
        VERSION=$($1 --version 2>&1 | head -1)
        echo -e "${GREEN}✓${NC} $1 - $VERSION"
        return 0
    else
        echo -e "${RED}✗${NC} $1 ${RED}(not found)${NC}"
        ISSUES=$((ISSUES + 1))
        return 1
    fi
}

echo "📋 Checking Prerequisites..."
echo "─────────────────────────────"
check_command python3
check_command node
check_command npm
echo ""

echo "📁 Checking Backend Structure..."
echo "─────────────────────────────"
check_dir "backend"
check_file "backend/server.py"
check_file "backend/requirements.txt"
check_file "backend/Dockerfile"
check_file "backend/README.md"
check_file "backend/start.sh"
echo ""

echo "📁 Checking Frontend Structure..."
echo "─────────────────────────────"
check_dir "frontend"
check_dir "frontend/src"
check_dir "frontend/src/components"
check_dir "frontend/src/hooks"
check_dir "frontend/public"
check_file "frontend/package.json"
check_file "frontend/vite.config.js"
check_file "frontend/tailwind.config.js"
check_file "frontend/src/App.jsx"
check_file "frontend/src/main.jsx"
check_file "frontend/src/hooks/useVoiceAgent.js"
check_file "frontend/public/intactbot_logo.png"
check_file "frontend/public/audio-processor-worklet.js"
check_file "frontend/public/audio-playback-worklet.js"
echo ""

echo "📁 Checking voice_langgraph (existing)..."
echo "─────────────────────────────"
check_dir "voice_langgraph"
check_file "voice_langgraph/voice_agent.py"
check_file "voice_langgraph/graph_builder.py"
check_file "voice_langgraph/nodes.py"
check_file "voice_langgraph/schema.py"
echo ""

echo "📄 Checking Documentation..."
echo "─────────────────────────────"
check_file "QUICKSTART.md"
check_file "SETUP_GUIDE.md"
check_file "TESTING_GUIDE.md"
check_file "DEPLOYMENT_PRODUCTION.md"
check_file "APPLICATION_SUMMARY.md"
check_file "PROJECT_README.md"
check_file "README_FULLSTACK.md"
echo ""

echo "⚙️  Checking Configuration..."
echo "─────────────────────────────"
if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} .env file exists"
    
    # Check for required variables
    if grep -q "AZURE_OPENAI_ENDPOINT" .env && grep -q "AZURE_OPENAI_API_KEY" .env; then
        echo -e "${GREEN}✓${NC} Required Azure OpenAI variables present"
    else
        echo -e "${YELLOW}⚠${NC} .env exists but may be missing required variables"
        echo "  Required: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY"
        ISSUES=$((ISSUES + 1))
    fi
else
    echo -e "${YELLOW}⚠${NC} .env file not found (copy from .env.example)"
    ISSUES=$((ISSUES + 1))
fi

if [ -f ".env.example" ]; then
    echo -e "${GREEN}✓${NC} .env.example template available"
else
    echo -e "${YELLOW}⚠${NC} .env.example not found"
fi
echo ""

echo "🔧 Checking Startup Scripts..."
echo "─────────────────────────────"
check_file "start_all.sh"
check_file "start_all.bat"
check_file "docker-compose.yml"
echo ""

echo "📦 Summary"
echo "=========================================="
if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Setup looks good.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Configure .env if not already done"
    echo "  2. Run: ./start_all.sh"
    echo "  3. Open: http://localhost:3000"
    echo "  4. Click 'Call Agent' and start talking!"
    exit 0
else
    echo -e "${RED}❌ Found $ISSUES issue(s)${NC}"
    echo ""
    echo "Please resolve the issues above before starting the application."
    echo "See SETUP_GUIDE.md for detailed instructions."
    exit 1
fi

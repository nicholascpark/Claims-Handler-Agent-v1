#!/bin/bash
# Start script for Claims Handler Voice Agent Backend

echo "🚀 Starting Claims Handler Voice Agent Backend..."

# Check if we're in the backend directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Please run this script from the backend directory"
    echo "   cd backend && ./start.sh"
    exit 1
fi

# Check if .env exists in parent directory
if [ ! -f "../.env" ]; then
    echo "⚠️  Warning: .env file not found in project root"
    if [ -f "../.env.example" ]; then
        echo "📝 Copying .env.example to .env..."
        cp ../.env.example ../.env
        echo "📝 Please edit .env with your Azure OpenAI credentials before continuing."
        exit 1
    else
        echo "❌ Error: No .env.example found. Please create .env manually."
        exit 1
    fi
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv || python -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Verify activation
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Error: Failed to activate virtual environment"
    exit 1
fi

echo "✅ Virtual environment activated: $VIRTUAL_ENV"

# Install/upgrade dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r ../requirements.txt

# Verify FastAPI is installed
python -c "import fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Error: FastAPI not installed correctly"
    echo "   Try: pip install -r ../requirements.txt"
    exit 1
fi

# Start server
echo ""
echo "✅ Starting server on http://localhost:8000"
echo "   Press Ctrl+C to stop"
echo ""
python main.py


#!/bin/bash
# Master start script for FNOL Voice Agent
# Starts both backend and frontend in separate terminal sessions

echo "🚀 FNOL Voice Agent - Starting All Services"
echo "============================================"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found in project root"
    echo "Please create .env file with Azure OpenAI credentials"
    echo "See SETUP_GUIDE.md for details"
    exit 1
fi

echo "✅ Environment file found"

# Function to start service in new terminal
start_service() {
    local service_name=$1
    local service_dir=$2
    local start_script=$3
    
    echo "Starting $service_name..."
    
    # Detect OS and open appropriate terminal
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        osascript -e "tell app \"Terminal\" to do script \"cd $(pwd)/$service_dir && ./$start_script\""
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v gnome-terminal &> /dev/null; then
            gnome-terminal -- bash -c "cd $(pwd)/$service_dir && ./$start_script; exec bash"
        elif command -v xterm &> /dev/null; then
            xterm -e "cd $(pwd)/$service_dir && ./$start_script; exec bash" &
        else
            echo "⚠️  No terminal emulator found. Please start manually:"
            echo "   cd $service_dir && ./$start_script"
        fi
    else
        echo "⚠️  OS not recognized. Please start manually:"
        echo "   cd $service_dir && ./$start_script"
    fi
}

# Start backend
start_service "Backend" "backend" "start.sh"
sleep 2

# Start frontend
start_service "Frontend" "frontend" "start.sh"

echo ""
echo "✅ Services starting..."
echo ""
echo "📍 Backend:  http://localhost:8000"
echo "📍 Frontend: http://localhost:3000"
echo ""
echo "⏳ Wait for both services to initialize, then open http://localhost:3000"
echo ""
echo "To stop services:"
echo "  - Close the terminal windows"
echo "  - Or press Ctrl+C in each terminal"
echo ""

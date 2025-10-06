# 🚨 Immediate Fix: ModuleNotFoundError

## Problem
```
ModuleNotFoundError: No module named 'fastapi'
```

## Solution

The backend needs to run in a **virtual environment** with dependencies installed.

### Quick Fix (Easiest)

**Windows**:
```bash
cd backend
start.bat
```

**Linux/Mac**:
```bash
cd backend
chmod +x start.sh
./start.sh
```

This script will:
1. ✅ Create virtual environment (if needed)
2. ✅ Activate it automatically
3. ✅ Install all dependencies
4. ✅ Start the server

### Manual Fix

If the script doesn't work, do it manually:

**Windows**:
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Start server
python main.py
```

**Linux/Mac**:
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start server
python main.py
```

### Verify It's Working

Your terminal prompt should show `(venv)`:
```
(venv) C:\...\backend> python main.py
```

You should see:
```
🚀 Starting Claims Handler Voice Agent Backend...
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Why This Happens

Python projects use **virtual environments** to:
- Isolate dependencies per project
- Avoid conflicts between packages
- Ensure reproducible installs

Without activating the venv, Python can't find the installed packages (like `fastapi`).

## Next Steps

Once backend is running:

1. Open new terminal for frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

2. Open browser to: http://localhost:5173

## Still Having Issues?

See [backend/TROUBLESHOOTING.md](backend/TROUBLESHOOTING.md) for detailed solutions.

## Complete Reset

If nothing works, start fresh:

```bash
# Clean up
cd backend
rm -rf venv
rm -rf __pycache__

# Recreate everything
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

# Test
python -c "import fastapi; print('✅ FastAPI installed')"

# Start
python main.py
```

---

**TIP**: Always use the startup scripts (`start.sh` / `start.bat`) - they handle everything automatically!



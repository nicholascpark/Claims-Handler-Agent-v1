# Backend Troubleshooting Guide

## Common Issues and Solutions

### 1. ModuleNotFoundError: No module named 'fastapi'

**Problem**: 
```
ModuleNotFoundError: No module named 'fastapi'
```

**Cause**: Running Python without activating the virtual environment first.

**Solution**:

**Option A - Use the startup script (Recommended)**:
```bash
# From the backend directory
cd backend
./start.sh       # Linux/Mac
start.bat        # Windows
```

**Option B - Manual activation**:

Linux/Mac:
```bash
cd backend
source venv/bin/activate
python main.py
```

Windows:
```bash
cd backend
venv\Scripts\activate.bat
python main.py
```

Windows PowerShell:
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python main.py
```

**Option C - Create venv if it doesn't exist**:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate.bat on Windows
pip install -r requirements.txt
python main.py
```

### 2. Virtual Environment Not Activating

**Symptoms**:
- Prompt doesn't change to show `(venv)`
- `which python` shows system Python, not venv Python

**Solution**:

1. **Check Python version**:
   ```bash
   python --version  # Should be 3.9+
   ```

2. **Try python3**:
   ```bash
   python3 -m venv venv
   ```

3. **PowerShell execution policy** (Windows):
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

4. **Recreate venv**:
   ```bash
   rm -rf venv  # or rmdir /s venv on Windows
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

### 3. Azure OpenAI Authentication Error

**Error**:
```
Invalid API key or endpoint
```

**Solution**:

1. **Check .env file exists**:
   ```bash
   ls ../.env  # Should exist in project root
   ```

2. **Verify credentials**:
   ```bash
   cat ../.env | grep AZURE_OPENAI
   ```

3. **Required variables**:
   ```env
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_API_KEY=your-key-here
   AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o
   AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME=gpt-4o-realtime-preview
   ```

4. **Test credentials**:
   ```python
   # In Python REPL
   import os
   from dotenv import load_dotenv
   load_dotenv('../.env')
   print(os.getenv('AZURE_OPENAI_ENDPOINT'))
   print(os.getenv('AZURE_OPENAI_API_KEY')[:10] + '...')
   ```

### 4. Port Already in Use

**Error**:
```
OSError: [Errno 48] Address already in use
```

**Solution**:

1. **Find process using port 8000**:
   
   Linux/Mac:
   ```bash
   lsof -i :8000
   kill -9 <PID>
   ```
   
   Windows:
   ```cmd
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   ```

2. **Use different port**:
   ```bash
   PORT=8001 python main.py
   ```

### 5. WebSocket Connection Fails

**Symptoms**:
- Frontend can't connect
- "Connection refused" errors

**Checklist**:

1. **Backend is running**:
   ```bash
   curl http://localhost:8000/health
   ```
   
2. **Check logs** for errors in backend terminal

3. **Test WebSocket**:
   ```bash
   npm install -g wscat
   wscat -c ws://localhost:8000/ws/voice
   ```

4. **Check firewall** isn't blocking port 8000

### 6. Slow Startup / Dependency Installation

**Solution**:

1. **Use pip cache**:
   ```bash
   pip install --cache-dir ~/.cache/pip -r requirements.txt
   ```

2. **Upgrade pip first**:
   ```bash
   pip install --upgrade pip setuptools wheel
   ```

3. **Install in batches** if out of memory:
   ```bash
   pip install fastapi uvicorn
   pip install langchain langgraph
   pip install -r requirements.txt
   ```

### 7. Import Error from voice_langgraph

**Error**:
```
ModuleNotFoundError: No module named 'voice_langgraph'
```

**Solution**:

1. **Check directory structure**:
   ```bash
   ls -la ../voice_langgraph/  # Should exist
   ```

2. **Verify __init__.py exists**:
   ```bash
   ls ../voice_langgraph/__init__.py
   ```

3. **Python path is correct** (session_manager.py adds parent dir):
   ```python
   sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
   ```

### 8. Realtime API Connection Issues

**Symptoms**:
- Sessions start but no audio
- WebSocket disconnects immediately

**Solution**:

1. **Check deployment name**:
   - Must be a Realtime API deployment
   - Format: `gpt-4o-realtime-preview`

2. **Verify API version**:
   ```env
   AZURE_OPENAI_REALTIME_API_VERSION=2024-10-01-preview
   ```

3. **Check network** allows WebSocket connections

4. **Test Realtime API directly** (from voice_langgraph):
   ```bash
   cd ..
   python run_voice_agent.py
   ```

## Verification Steps

### Check Virtual Environment

```bash
# Should show venv path
echo $VIRTUAL_ENV  # Linux/Mac
echo %VIRTUAL_ENV%  # Windows

# Should show venv Python
which python  # Linux/Mac
where python  # Windows

# Should list installed packages
pip list | grep fastapi
```

### Check Dependencies

```bash
# All should succeed
python -c "import fastapi"
python -c "import uvicorn"
python -c "import langchain"
python -c "import langgraph"
python -c "import trustcall"
python -c "import aiohttp"
```

### Check Environment Variables

```bash
# In Python
python << EOF
import os
from dotenv import load_dotenv
load_dotenv('../.env')

required = [
    'AZURE_OPENAI_ENDPOINT',
    'AZURE_OPENAI_API_KEY',
    'AZURE_OPENAI_CHAT_DEPLOYMENT_NAME',
    'AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME',
]

for var in required:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: {value[:20]}...")
    else:
        print(f"❌ {var}: NOT SET")
EOF
```

## Still Having Issues?

1. **Check backend logs** - Look for stack traces in terminal
2. **Enable debug logging** - Edit `main.py`:
   ```python
   logging.basicConfig(level=logging.DEBUG)
   ```
3. **Test standalone agent** - Verify voice_langgraph works:
   ```bash
   cd ..
   python run_voice_agent.py
   ```
4. **Review documentation**:
   - [backend/README.md](README.md)
   - [../INTEGRATION_GUIDE.md](../INTEGRATION_GUIDE.md)
   - [../QUICK_START.md](../QUICK_START.md)

## Quick Reset

If all else fails, start fresh:

```bash
# From project root
cd backend

# Clean up
rm -rf venv
rm -rf __pycache__
rm -rf *.pyc

# Recreate
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate.bat
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Verify
python -c "import fastapi; print('FastAPI OK')"

# Start
python main.py
```



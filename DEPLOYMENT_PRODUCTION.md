# FNOL Voice Agent - Production Deployment Guide

Comprehensive guide for deploying the FNOL Voice Agent to production environments.

## 📋 Pre-Deployment Checklist

### Infrastructure
- [ ] Production Azure OpenAI resource provisioned
- [ ] Realtime API deployment created (gpt-4o-realtime-preview)
- [ ] Chat API deployment created (gpt-4)
- [ ] Server infrastructure ready (VM, container platform, etc.)
- [ ] SSL certificates obtained
- [ ] Domain names configured
- [ ] Firewall rules configured

### Configuration
- [ ] Production .env file created
- [ ] All required environment variables set
- [ ] Sensitive data secured (API keys, secrets)
- [ ] CORS origins configured
- [ ] WebSocket timeout settings tuned
- [ ] Logging configured
- [ ] Monitoring enabled

### Testing
- [ ] All test scenarios pass
- [ ] Load testing completed
- [ ] Security testing completed
- [ ] UAT sign-off received
- [ ] Performance benchmarks met

## 🚀 Deployment Options

### Option 1: Docker Compose (Recommended)

**Pros:**
- Easy orchestration
- Consistent environments
- Simple rollback
- Isolated services

**Steps:**

1. **Prepare Environment**
```bash
# Create production .env
cp .env.example .env
# Edit with production values
nano .env
```

2. **Build Images**
```bash
# Build both services
docker-compose build

# Or build individually
docker-compose build backend
docker-compose build frontend
```

3. **Start Services**
```bash
# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

4. **Configure Reverse Proxy**

Example Nginx configuration:
```nginx
# /etc/nginx/sites-available/fnol-voice-agent

upstream backend {
    server localhost:8000;
}

upstream frontend {
    server localhost:3000;
}

server {
    listen 80;
    server_name fnol.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name fnol.yourdomain.com;

    ssl_certificate /etc/ssl/certs/fnol.crt;
    ssl_certificate_key /etc/ssl/private/fnol.key;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```

5. **Enable and Test**
```bash
sudo ln -s /etc/nginx/sites-available/fnol-voice-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

### Option 2: Kubernetes

**Pros:**
- High availability
- Auto-scaling
- Rolling updates
- Cloud-native

**Deployment Files:**

`k8s/backend-deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fnol-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fnol-backend
  template:
    metadata:
      labels:
        app: fnol-backend
    spec:
      containers:
      - name: backend
        image: your-registry/fnol-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: AZURE_OPENAI_ENDPOINT
          valueFrom:
            secretKeyRef:
              name: azure-credentials
              key: endpoint
        - name: AZURE_OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: azure-credentials
              key: api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: fnol-backend
spec:
  selector:
    app: fnol-backend
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: ClusterIP
```

`k8s/frontend-deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fnol-frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: fnol-frontend
  template:
    metadata:
      labels:
        app: fnol-frontend
    spec:
      containers:
      - name: frontend
        image: your-registry/fnol-frontend:latest
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: fnol-frontend
spec:
  selector:
    app: fnol-frontend
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
  type: ClusterIP
```

`k8s/ingress.yaml`:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fnol-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - fnol.yourdomain.com
    secretName: fnol-tls
  rules:
  - host: fnol.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: fnol-frontend
            port:
              number: 80
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: fnol-backend
            port:
              number: 8000
      - path: /ws
        pathType: Prefix
        backend:
          service:
            name: fnol-backend
            port:
              number: 8000
```

**Deploy:**
```bash
# Create namespace
kubectl create namespace fnol

# Create secrets
kubectl create secret generic azure-credentials \
  --from-literal=endpoint=$AZURE_OPENAI_ENDPOINT \
  --from-literal=api-key=$AZURE_OPENAI_API_KEY \
  -n fnol

# Deploy
kubectl apply -f k8s/ -n fnol

# Check status
kubectl get pods -n fnol
kubectl get services -n fnol
kubectl get ingress -n fnol
```

---

### Option 3: Traditional Server

**Backend:**
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3.11 python3-pip portaudio19-dev

# Create service user
sudo useradd -r -s /bin/false fnolbackend

# Install application
sudo mkdir -p /opt/fnol-backend
sudo cp -r backend/* /opt/fnol-backend/
cd /opt/fnol-backend

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create systemd service
sudo nano /etc/systemd/system/fnol-backend.service
```

```ini
[Unit]
Description=FNOL Voice Agent Backend
After=network.target

[Service]
Type=simple
User=fnolbackend
WorkingDirectory=/opt/fnol-backend
Environment="PATH=/opt/fnol-backend/venv/bin"
EnvironmentFile=/opt/fnol-backend/.env
ExecStart=/opt/fnol-backend/venv/bin/gunicorn server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable fnol-backend
sudo systemctl start fnol-backend
sudo systemctl status fnol-backend
```

**Frontend:**
```bash
# Build frontend
cd frontend
npm install
npm run build

# Serve with Nginx
sudo cp -r dist/* /var/www/fnol-frontend/
sudo chown -R www-data:www-data /var/www/fnol-frontend

# Nginx config created above
sudo systemctl reload nginx
```

---

## 🔒 Security Hardening

### Backend Security

1. **Environment Variables**
```bash
# Use secrets management (not .env files)
# AWS: AWS Secrets Manager
# Azure: Azure Key Vault
# HashiCorp: Vault
```

2. **CORS Configuration**
```python
# In server.py, restrict origins:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://fnol.yourdomain.com"],  # Specific domain
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

3. **Rate Limiting**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.websocket("/ws/voice")
@limiter.limit("10/minute")
async def websocket_voice_endpoint(websocket: WebSocket):
    ...
```

### Frontend Security

1. **Content Security Policy**
```html
<!-- In index.html -->
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; 
               connect-src 'self' wss://api.yourdomain.com; 
               img-src 'self' data:; 
               style-src 'self' 'unsafe-inline';">
```

2. **Environment Variables**
```bash
# Never commit .env to git
# Use build-time variables for production
VITE_WS_URL=wss://api.yourdomain.com/ws/voice
```

---

## 📊 Monitoring and Alerting

### Health Checks

```bash
# Backend health
curl https://api.yourdomain.com/health

# Should return 200 with:
{
  "status": "healthy",
  "services": {
    "langgraph": "available",
    "voice_settings": "configured"
  }
}
```

### Logging

**Structured Logging:**
```python
import structlog

logger = structlog.get_logger()
logger.info("session_started", session_id=session_id, user_id=user_id)
```

**Log Aggregation:**
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Splunk
- DataDog
- Azure Monitor

### Alerts

Set up alerts for:
- Backend service down
- High error rate (>5%)
- WebSocket connection failures
- Azure OpenAI API errors
- High latency (>5s response time)

---

## 🔄 CI/CD Pipeline

### Example GitHub Actions

`.github/workflows/deploy.yml`:
```yaml
name: Deploy FNOL Voice Agent

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Test Backend
        run: |
          cd backend
          pip install -r requirements.txt
          python -m pytest
      - name: Test Frontend
        run: |
          cd frontend
          npm install
          npm run lint
          npm run build

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and Push Docker Images
        run: |
          docker build -t registry.yourdomain.com/fnol-backend:${{ github.sha }} -f backend/Dockerfile .
          docker build -t registry.yourdomain.com/fnol-frontend:${{ github.sha }} -f frontend/Dockerfile ./frontend
          docker push registry.yourdomain.com/fnol-backend:${{ github.sha }}
          docker push registry.yourdomain.com/fnol-frontend:${{ github.sha }}
      - name: Deploy to Production
        run: |
          # Deploy to your infrastructure
          # e.g., kubectl set image deployment/fnol-backend ...
```

---

## 📈 Scaling

### Horizontal Scaling

**Backend:**
- Run multiple instances behind load balancer
- Use Redis for shared session state
- Enable sticky sessions for WebSocket

**Frontend:**
- Serve from CDN
- Use multiple edge locations
- Enable caching for static assets

### Vertical Scaling

**Backend:**
- Increase CPU/memory for containers
- Optimize LangGraph workflow
- Cache extraction results

**Frontend:**
- Code splitting
- Lazy loading
- Asset optimization

---

## 🔧 Maintenance

### Regular Tasks

**Daily:**
- Monitor error logs
- Check health endpoints
- Review performance metrics

**Weekly:**
- Review and rotate logs
- Update dependencies (security patches)
- Backup configuration

**Monthly:**
- Capacity planning review
- Security audit
- Performance optimization

### Updating the Application

```bash
# Pull latest code
git pull origin main

# Backend update
cd backend
docker-compose build backend
docker-compose up -d backend

# Frontend update
cd frontend
npm run build
docker-compose build frontend
docker-compose up -d frontend

# Verify
curl https://api.yourdomain.com/health
```

---

## 🆘 Disaster Recovery

### Backup Strategy

**What to Backup:**
- Environment configurations
- SSL certificates
- Session data (if persisted)
- Application logs

**Backup Frequency:**
- Configuration: Daily
- Logs: Continuous streaming to log aggregator

### Recovery Procedures

**Backend Failure:**
```bash
# 1. Check logs
docker-compose logs backend

# 2. Restart service
docker-compose restart backend

# 3. If persists, rollback
docker-compose down
git checkout <previous-working-commit>
docker-compose up -d
```

**Complete Outage:**
```bash
# 1. Restore from backup
# 2. Rebuild containers
docker-compose build
# 3. Deploy
docker-compose up -d
# 4. Verify health
curl https://api.yourdomain.com/health
```

---

## 📊 Performance Tuning

### Backend Optimization

```python
# server.py - Production settings

# Increase workers for Gunicorn
# workers = (2 * CPU_CORES) + 1
uvicorn.run(
    app,
    host="0.0.0.0",
    port=8000,
    workers=8,  # Adjust based on CPU
    log_level="warning",  # Reduce logging overhead
    access_log=False  # Disable if using separate logging
)
```

### Frontend Optimization

```javascript
// vite.config.js - Production optimizations

export default defineConfig({
  build: {
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,  // Remove console.log in production
      },
    },
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
        },
      },
    },
  },
})
```

### Database/Cache Layer (Future Enhancement)

```python
# Add Redis for session persistence
import aioredis

redis = await aioredis.create_redis_pool('redis://localhost')

# Store session data
await redis.setex(
    f"session:{session_id}",
    3600,  # 1 hour TTL
    json.dumps(session_data)
)
```

---

## 🔍 Troubleshooting Production Issues

### High CPU Usage

**Causes:**
- Too many concurrent sessions
- Inefficient LangGraph workflow
- Memory leaks

**Solutions:**
- Scale horizontally
- Optimize extraction triggers
- Profile and fix memory leaks

### High Latency

**Causes:**
- Azure OpenAI API throttling
- Network latency
- Large message payloads

**Solutions:**
- Request rate limit increase from Azure
- Use regional endpoints
- Compress WebSocket messages

### WebSocket Disconnections

**Causes:**
- Proxy timeout
- Network instability
- Server overload

**Solutions:**
- Increase proxy timeout (nginx: `proxy_read_timeout`)
- Implement heartbeat/ping
- Add auto-reconnection logic

---

## 📞 Support and Escalation

### Monitoring Alerts

Configure alerts for:
- Service down (PagerDuty, Opsgenie)
- Error rate >5% (Slack, email)
- Latency >5s (Datadog, New Relic)
- Failed deployments (GitHub, GitLab)

### On-Call Procedures

1. **Receive Alert**
2. **Check Health Dashboard**
3. **Review Recent Deployments**
4. **Check Application Logs**
5. **Verify Azure OpenAI Status**
6. **Escalate if Needed**

### Rollback Procedure

```bash
# 1. Stop current deployment
docker-compose down

# 2. Checkout previous version
git log --oneline  # Find last working commit
git checkout <commit-hash>

# 3. Rebuild and deploy
docker-compose build
docker-compose up -d

# 4. Verify
curl https://api.yourdomain.com/health

# 5. Notify team
# Send notification of rollback
```

---

## 📝 Compliance and Audit

### Data Privacy
- PII (Personally Identifiable Information) handling
- GDPR compliance (if applicable)
- Data retention policies
- Encryption at rest and in transit

### Audit Logging
- User sessions
- Data access
- Configuration changes
- Security events

### Documentation
- System architecture diagram
- Data flow diagrams
- Security assessment
- Disaster recovery plan

---

## ✅ Post-Deployment Validation

After deployment, verify:

1. **Smoke Test**
   ```bash
   # Health check
   curl https://api.yourdomain.com/health
   
   # Frontend loads
   curl https://fnol.yourdomain.com
   ```

2. **End-to-End Test**
   - Open application
   - Start voice session
   - Complete sample claim
   - Verify submission

3. **Performance Test**
   - Measure latency
   - Check resource usage
   - Verify concurrent users

4. **Security Test**
   - SSL certificate valid
   - CORS working correctly
   - No exposed secrets
   - Rate limiting active

---

## 🎓 Training and Documentation

### User Training
- Create user guide
- Record demo videos
- Conduct training sessions
- Provide support documentation

### Developer Documentation
- Architecture overview
- API documentation
- Deployment procedures
- Troubleshooting guide

---

**Last Updated**: September 30, 2025  
**Maintained By**: Intact Financial Corporation DevOps Team

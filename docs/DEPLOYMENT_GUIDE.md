# TradePulse IQ Server Deployment Guide

## 🌐 Server Information

### Production Server Details
- **Provider**: DigitalOcean Droplet
- **IP Address**: `138.68.245.159`
- **OS**: Ubuntu 24.04 LTS
- **SSH User**: `root`
- **Deployment Path**: `/srv/trad`

### Database Configuration
- **Host**: `localhost` (on server)
- **Port**: `5432`
- **Database**: `trad`
- **User**: `traduser`
- **Password**: `TRAD123!`
- **Technology**: PostgreSQL 16 with pgvector extension

## 🚀 Deployment Commands

### Standard Deployment
```bash
# Deploy enhanced TradePulse IQ backend
cd /workspaces/Trad
SERVER=138.68.245.159 SSH_USER=root DEST=/srv/trad ./ops/scripts/deploy_to_server.sh
```

### Alternative Deployment (with explicit parameters)
```bash
# If you need to specify different parameters
SERVER=138.68.245.159 \
SSH_USER=root \
DEST=/srv/trad \
./ops/scripts/deploy_to_server.sh
```

## 🔍 Health Check & Verification

### Post-Deployment Health Check
```bash
# Run health check after deployment
./ops/scripts/health_check.sh

# Check API endpoints remotely
curl http://138.68.245.159:8000/health
curl http://138.68.245.159:8000/docs
```

### SSH Access for Manual Checks
```bash
# SSH into server for manual verification
ssh root@138.68.245.159

# Check service status on server
sudo systemctl status trad.service
sudo systemctl status dashboard.service

# Check logs
sudo journalctl -u trad.service -f
sudo journalctl -u dashboard.service -f

# Check API is responding
curl http://localhost:8000/health
```

## 📊 Deployed Services

### systemd Services
1. **trad.service** - Main trading bot
   - **Path**: `/etc/systemd/system/trad.service`
   - **Executable**: `/srv/trad/.venv/bin/python3 /srv/trad/main.py`
   - **Logs**: `sudo journalctl -u trad.service -f`

2. **dashboard.service** - TradePulse IQ FastAPI Backend
   - **Path**: `/etc/systemd/system/dashboard.service`
   - **Executable**: `/srv/trad/.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000`
   - **Port**: `8000`
   - **Logs**: `sudo journalctl -u dashboard.service -f`

### API Endpoints (Port 8000)
- **Health Check**: `http://138.68.245.159:8000/health`
- **API Documentation**: `http://138.68.245.159:8000/docs`
- **Portfolio API**: `http://138.68.245.159:8000/api/portfolio/summary`
- **Trades API**: `http://138.68.245.159:8000/api/trades/active`
- **Patterns API**: `http://138.68.245.159:8000/api/patterns/strategy-performance`
- **Training API**: `http://138.68.245.159:8000/api/training/system-status`
- **Analytics API**: `http://138.68.245.159:8000/api/analytics/market-overview`
- **Exchanges API**: `http://138.68.245.159:8000/api/exchanges/connections`

## 📁 Server File Structure

```
/srv/trad/                          # Main deployment directory
├── api/                            # Enhanced FastAPI backend (30+ endpoints)
│   ├── main.py                     # FastAPI application entry point
│   ├── portfolio.py                # Portfolio management API
│   ├── trades.py                   # Trade management API
│   ├── patterns.py                 # Strategy patterns API
│   ├── training.py                 # ML training API
│   ├── analytics.py                # Analytics API
│   └── exchanges.py                # Exchange management API
├── core/                           # Core trading system
│   ├── execution_core.py           # Enhanced execution with OCO
│   ├── data_handler.py             # Market data management
│   └── event_system.py             # Event-driven architecture
├── ml/                             # Multi-dimensional training
│   ├── trained_assets_manager.py   # Enhanced training system
│   └── multi_dimensional_trainer.py
├── strategies/                     # A+ Trading strategies
│   ├── htf_sweep.py               # HTF Sweep strategy
│   ├── volume_breakout.py         # Volume breakout strategy
│   └── divergence_capitulation.py # Divergence capitulation
├── policy/                         # Trading policies
├── config/                         # Configuration files
│   ├── trad.env                   # Environment variables
│   └── aplus.env                  # A+ specific config
├── sql/                           # Database schemas
├── ops/                           # Operations scripts
└── .venv/                         # Python virtual environment
```

## 🔧 Troubleshooting

### Common Issues

1. **Service Not Starting**
   ```bash
   # Check service status
   sudo systemctl status dashboard.service
   
   # Restart services
   sudo systemctl restart dashboard.service
   sudo systemctl restart trad.service
   ```

2. **API Not Responding**
   ```bash
   # Check if port 8000 is listening
   sudo netstat -tlnp | grep 8000
   
   # Check service logs
   sudo journalctl -u dashboard.service -f
   ```

3. **Database Connection Issues**
   ```bash
   # Test database connection
   psql -h localhost -U traduser -d trad
   
   # Check if PostgreSQL is running
   sudo systemctl status postgresql
   ```

4. **Permission Issues**
   ```bash
   # Fix ownership if needed
   sudo chown -R root:root /srv/trad
   
   # Check environment file permissions
   sudo ls -la /etc/trad/trad.env
   ```

### Log Locations
- **Trading Bot**: `sudo journalctl -u trad.service -f`
- **Dashboard API**: `sudo journalctl -u dashboard.service -f`
- **System Logs**: `/var/log/syslog`
- **Application Logs**: `/var/log/trad-dashboard.log`

## 🔄 Deployment Process Overview

1. **Repository Sync**: Code synced via rsync to `/srv/trad`
2. **Environment Setup**: Config files copied to `/etc/trad/`
3. **Dependencies**: Python packages installed in `/srv/trad/.venv`
4. **Database Init**: SQL schemas applied to PostgreSQL
5. **Service Registration**: systemd services installed and started
6. **Verification**: Health checks and API endpoint testing

## 🔐 Security & Access

### Environment Files
- **Main Config**: `/etc/trad/trad.env`
- **Database Password**: `TRAD123!`
- **Dashboard Credentials**: `admin / trad`

### Network Access
- **SSH**: Port 22 (standard)
- **API**: Port 8000 (HTTP)
- **Database**: Port 5432 (local only)

## 📈 Enhanced Features Deployed

### Multi-Dimensional Training System
- ✅ TrainedAssetsManager with regime awareness
- ✅ Strategy-specific parameter optimization
- ✅ Cross-timeframe analysis

### Enhanced API Backend
- ✅ 30+ REST API endpoints
- ✅ Real-time portfolio management
- ✅ Advanced analytics and reporting
- ✅ Exchange connection management
- ✅ Strategy performance tracking

### A+ Trading Strategies
- ✅ HTF Sweep (1h→5m liquidity sweep)
- ✅ Volume Breakout (ATR-based consolidation)
- ✅ Divergence Capitulation (trend context + divergence)

---

## 🎯 Quick Reference

**Deploy Command**: `SERVER=138.68.245.159 SSH_USER=root DEST=/srv/trad ./ops/scripts/deploy_to_server.sh`

**Health Check**: `curl http://138.68.245.159:8000/health`

**SSH Access**: `ssh root@138.68.245.159`

**API Docs**: `http://138.68.245.159:8000/docs`

---

*Last Updated: October 22, 2025*
*Enhanced TradePulse IQ Deployment Guide*
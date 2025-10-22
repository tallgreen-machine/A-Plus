# TradePulse IQ Documentation

This directory contains comprehensive documentation for the TradePulse IQ trading platform.

## 📖 Documentation Index

### Core Documentation
- **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** - Complete production deployment guide
- **[PRODUCTION_STATUS.md](./PRODUCTION_STATUS.md)** - Current production system status and health
- **[dashboard_technical_spec.md](./dashboard_technical_spec.md)** - Technical specifications for the dashboard

### Development & Enhancement Documentation
- **[BACKEND_ENHANCEMENT_SUMMARY.md](./BACKEND_ENHANCEMENT_SUMMARY.md)** - Summary of backend API enhancements and new features
- **[CLEANUP_SUMMARY.md](./CLEANUP_SUMMARY.md)** - Project organization and file cleanup documentation
- **[SERVER_CONNECTION.md](./SERVER_CONNECTION.md)** - Server connection and configuration details

## 🚀 Quick Links

### Production System
- **Live Dashboard**: http://138.68.245.159:8000
- **API Documentation**: http://138.68.245.159:8000/docs
- **Server SSH**: `ssh root@138.68.245.159`

### Key Commands
```bash
# Deploy to production
SERVER=138.68.245.159 SSH_USER=root DEST=/srv/trad ./ops/scripts/deploy_to_server.sh

# Check server status
./ops/scripts/server_info.sh

# Health check
curl http://138.68.245.159:8000/health
```

## 📋 Documentation Standards

All documentation follows these standards:
- **Markdown format** with clear section headers
- **Production-ready examples** with actual server details
- **Complete command references** with working examples
- **Status tracking** with timestamps and verification steps

---

*For the main project overview, see [../README.md](../README.md)*
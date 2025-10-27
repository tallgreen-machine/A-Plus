# Market Data Quick Reference

**Status:** ✅ All Systems Ready for Training  
**Updated:** October 27, 2025

## 📊 At a Glance

| Metric | Value |
|--------|-------|
| **Total Records** | 18,755,054 |
| **Growth** | +10.1M (+117%) |
| **Exchanges** | 6 active |
| **Symbols** | 8 cryptocurrencies |
| **Coverage** | 541 days (May 2024 - Oct 2025) |
| **Status** | ✅ Training Ready |

## ✅ Training-Ready Symbols

All 8 symbols ready for immediate training:

1. **ETH/USDT** - 3.83M records (6 exchanges) ⭐ EXCELLENT
2. **BTC/USDT** - 3.81M records (6 exchanges) ⭐ EXCELLENT
3. **SOL/USDT** - 2.63M records (4 exchanges) ⭐ EXCELLENT
4. **ADA/USDT** - 2.39M records (3 exchanges) ⭐ EXCELLENT
5. **AVAX/USDT** - 2.37M records (3 exchanges) ⭐ EXCELLENT
6. **DOT/USDT** - 2.26M records (3 exchanges) ⭐ EXCELLENT
7. **BNB/USDT** - 1.00M records (2 exchanges) ⭐ EXCELLENT
8. **MATIC/USDT** - 464K records (1 exchange) ✓ GOOD

## 🚀 Quick Commands

### Check Data Status
```bash
# From dev container
bash /workspaces/Trad/ops/scripts/monitor_backfills.sh

# From server
source /etc/trad/trad.env
PGPASSWORD="$DB_PASSWORD" psql -h localhost -U $DB_USER -d $DB_NAME -c \
  "SELECT COUNT(*) FROM market_data;"
```

### Get Symbol Breakdown
```bash
ssh -A root@138.68.245.159 "source /etc/trad/trad.env && \
  PGPASSWORD=\"\$DB_PASSWORD\" psql -h localhost -U \$DB_USER -d \$DB_NAME -c \
  \"SELECT symbol, COUNT(*) as records FROM market_data GROUP BY symbol ORDER BY records DESC;\""
```

## 📈 Recommended Training Order

1. **Start Here:** BTC/USDT, ETH/USDT, SOL/USDT (highest quality)
2. **Next:** ADA/USDT, AVAX/USDT, DOT/USDT (strong altcoins)
3. **Later:** BNB/USDT, MATIC/USDT (lower volume)

## 📚 Full Documentation

See [MARKET_DATA_INVENTORY.md](./MARKET_DATA_INVENTORY.md) for complete details.

---

**Ready to start training?** All systems go! 🎯

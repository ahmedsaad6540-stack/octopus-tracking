# OCTOPUS V3.1 – First Click Audit Report
Date: 2026-06-25
Version: 3.1 – schema v2

```
[1/3] Click → /r  ✓ click_id=… latency 0ms
[2/3] Conversion → /postback/impact  ✓ $25.5
[3/3] ROI → /roi  ✓ sales=1 revenue=$25.5 cr=100%
✅ PIPELINE STATUS: PASS
```

- Click Integrity: ip_hash / ua_hash / bot_flag / duplicate_flag / risk_score ✅
- subid passthrough: ✅
- Postback Impact / Digistore24: ✅
- FX normalization USD/EUR/SAR/EGP/AED: ✅
- ROI: views / clicks_real / sales / revenue_usd / conversion_rate / ctr / epc / rpvm ✅
- Event immutability – append-only triggers ✅

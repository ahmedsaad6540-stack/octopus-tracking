# OCTOPUS V3.1 – Profit Twin – Video → Click → Conversion → Revenue

**Self-driving affiliate profit tracker for TikTok / Reels / Shorts.**

Pipeline: `Video → Click → Conversion → Revenue → ROI`

Last Audit: ✅ **PASS – Click → Conversion → Revenue $25.50**

---

## Quick start – local

```bash
cd octopus_v3/backend
pip install -r requirements_tracking.txt
uvicorn tracking_server:app --reload --port 8000
# in another terminal:
python test_runner.py
# ✅ PIPELINE STATUS: PASS
```

Dashboard: open `octopus_v3/app/index.html` → click "شغل Test Runner"

API: `http://localhost:8000/roi`

---

## Supabase setup

1. supabase.com → New Project
2. SQL Editor → paste `supabase/schema_tracking_v2.sql` → Run
3. Copy keys to `backend/.env`:
```
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJ...
IP_HASH_SALT=random_long_string
UA_HASH_SALT=random_long_string_2
```

Tables: `products, videos, clicks, conversions`
View: `v_video_roi`

20 products seeded.

---

## Deploy – Railway

See `DEPLOY_RAILWAY.md`

---

## Test

```bash
python test_runner.py
```
```
[1/3] Click → /r  ✓
[2/3] Conversion → /postback/impact  ✓ $25.5
[3/3] ROI → /roi  ✓
✅ PIPELINE STATUS: PASS
```

MIT – 2026

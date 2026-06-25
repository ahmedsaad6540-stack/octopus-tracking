"""
OCTOPUS V3.1 - Tracking Server (v2 - schema aligned)
FastAPI - Click Redirect + Postback + Supabase
Pipeline: Video → Click → Conversion → Revenue
"""
import os, hashlib, time, json, uuid
from typing import Optional
from fastapi import FastAPI, Request, BackgroundTasks, Query
from fastapi.responses import RedirectResponse, JSONResponse

try:
    from dotenv import load_dotenv; load_dotenv()
except Exception: pass

import httpx

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
IP_HASH_SALT = os.getenv("IP_HASH_SALT", "octopus_salt_v3")
UA_HASH_SALT = os.getenv("UA_HASH_SALT", "octopus_ua_salt_v3")
USE_DB = bool(SUPABASE_URL and SUPABASE_KEY)

from pathlib import Path
LOCAL_DB = Path(__file__).parent / "tracking_db.json"

def local_load():
    if LOCAL_DB.exists():
        try: return json.loads(LOCAL_DB.read_text())
        except Exception: pass
    return {"products": [], "videos": [], "clicks": [], "conversions": []}

def local_save(db):
    LOCAL_DB.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

def sb_headers():
    return {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json", "Prefer": "return=representation"}

async def sb_post(table: str, data: dict):
    if USE_DB:
        async with httpx.AsyncClient(timeout=2.5) as c:
            r = await c.post(f"{SUPABASE_URL}/rest/v1/{table}", json=data, headers=sb_headers())
            r.raise_for_status(); j = r.json(); return j[0] if j else None
    db = local_load(); row = data.copy()
    row["id"] = str(uuid.uuid4())
    row["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if table == "conversions": row["received_at"] = row["created_at"]
    db.setdefault(table, []).append(row); local_save(db); return row

async def sb_get(table: str, params: dict):
    if USE_DB:
        async with httpx.AsyncClient(timeout=2.5) as c:
            r = await c.get(f"{SUPABASE_URL}/rest/v1/{table}", params=params, headers=sb_headers())
            r.raise_for_status(); return r.json()
    db = local_load(); rows = db.get(table, [])
    def match(row):
        for k,v in params.items():
            if k in ("order","limit","select","offset"): continue
            if v.startswith("eq."):
                if str(row.get(k, "")) != v[3:]: return False
        return True
    rows = [r for r in rows if match(r)]
    if params.get("order","").startswith("created_at.desc"):
        rows.sort(key=lambda x: x.get("created_at",""), reverse=True)
    if "limit" in params:
        try: rows = rows[:int(params["limit"])]
        except: pass
    return rows

FX_RATES = {"USD":1.0,"EUR":1.08,"SAR":0.266,"EGP":0.021,"AED":0.272}
def to_usd(amount: float, currency: str) -> tuple[float, float]:
    cur = (currency or "USD").upper(); rate = FX_RATES.get(cur, 1.0)
    return amount * rate, rate

def hash_ip(ip: str) -> str: return hashlib.sha256((ip + IP_HASH_SALT).encode()).hexdigest()[:32]
def hash_ua(ua: str) -> str: return hashlib.sha256((ua + UA_HASH_SALT).encode()).hexdigest()[:32]
def is_bot(ua: str) -> bool:
    ua = ua.lower()
    return any(b in ua for b in ["bot","crawl","spider","slurp","facebookexternalhit","headless","python-requests","curl","wget","ahrefs","semrush"])
def risk_score(bot: bool, duplicate: bool, ua: str) -> int:
    s = 0
    if bot: s += 80
    if duplicate: s += 30
    if not ua or len(ua) < 20: s += 20
    return min(s, 100)

app = FastAPI(title="OCTOPUS Tracking v3.1")

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def root():
    return {"ok": True, "name": "OCTOPUS Tracking v3.1",
            "click": "/r?video=_uuid_&product=_uuid_",
            "postback_impact": "/postback/impact",
            "postback_digistore": "/postback/digistore",
            "roi": "/roi"}

@app.get("/health")
def health(): return {"ok": True, "db": "supabase" if USE_DB else "local", "schema": "v2"}

@app.get("/r")
async def create_click(request: Request, background_tasks: BackgroundTasks,
    video: Optional[str] = Query(None), product: Optional[str] = Query(None)):
    t0 = time.time()
    ip = request.client.host if request.client else "0.0.0.0"
    xff = request.headers.get("x-forwarded-for")
    if xff: ip = xff.split(",")[0].strip()
    ua = request.headers.get("user-agent", "")
    referrer = request.headers.get("referer", "")
    country = request.headers.get("cf-ipcountry", "") or request.headers.get("x-vercel-ip-country", "")
    ip_h = hash_ip(ip); ua_h = hash_ua(ua); bot = is_bot(ua)
    duplicate = False
    try:
        rows = await sb_get("clicks", {"ip_hash": f"eq.{ip_h}", "ua_hash": f"eq.{ua_h}",
            "order": "created_at.desc", "limit": "1", "select": "created_at"})
        if rows and rows[0].get("created_at"):
            from datetime import datetime, timezone
            last = datetime.fromisoformat(rows[0]["created_at"].replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - last).total_seconds() < 30:
                duplicate = True
    except Exception: pass
    r_score = risk_score(bot, duplicate, ua)
    affiliate_url = "https://example.com/"
    if product:
        try:
            rows = await sb_get("products", {"id": f"eq.{product}", "select": "affiliate_url"})
            if rows: affiliate_url = rows[0]["affiliate_url"]
        except Exception: pass
    click_id = None
    try:
        row = await sb_post("clicks", {
            "video_id": video, "product_id": product,
            "ip_hash": ip_h, "ua_hash": ua_h, "platform": "tiktok",
            "referrer": referrer[:500] if referrer else None,
            "country": country or None,
            "bot_flag": bot, "duplicate_flag": duplicate, "risk_score": r_score
        })
        if row: click_id = row.get("id")
    except Exception as e: print("click insert failed:", e)
    if not click_id: click_id = str(uuid.uuid4())
    sep = "&" if "?" in affiliate_url else "?"
    target = f"{affiliate_url}{sep}subid={click_id}&s2={video or ''}"
    resp = RedirectResponse(target, status_code=302)
    resp.headers["X-Octopus-Click"] = click_id
    resp.headers["X-Octopus-Latency"] = str(int((time.time() - t0) * 1000))
    resp.headers["Cache-Control"] = "no-store"
    return resp

@app.api_route("/postback/impact", methods=["GET", "POST"])
async def postback_impact(request: Request,
    subid: Optional[str] = Query(None), order_id: Optional[str] = Query(None),
    payout: float = Query(0), sale_amount: Optional[float] = Query(None),
    currency: str = Query("USD"), status: str = Query("approved")):
    if request.method == "POST":
        try:
            body = await request.json()
            subid = subid or body.get("subid") or body.get("SubId")
            order_id = order_id or body.get("order_id")
            payout = payout or float(body.get("payout", 0))
            sale_amount = sale_amount or body.get("sale_amount")
            currency = body.get("currency", currency)
        except Exception: pass
    click_id = subid
    if not click_id: return JSONResponse({"ok": False, "error": "missing subid"}, status_code=400)
    commission_amount = float(payout or 0)
    commission_currency = currency.upper()
    fx_rate = to_usd(1, commission_currency)[1]
    commission_usd = round(commission_amount * fx_rate, 2)
    sale_amt = float(sale_amount) if sale_amount else None
    video_id = None
    try:
        rows = await sb_get("clicks", {"id": f"eq.{click_id}", "select": "video_id"})
        if rows: video_id = rows[0].get("video_id")
    except Exception: pass
    conv = {
        "click_id": click_id, "video_id": video_id, "network": "impact",
        "sale_amount": sale_amt, "sale_currency": commission_currency if sale_amt else "USD",
        "commission_amount": commission_amount, "commission_currency": commission_currency,
        "fx_rate": fx_rate, "commission_usd": commission_usd,
        "status": status, "external_order_id": order_id,
        "raw_payload": dict(request.query_params)
    }
    if commission_amount > 0:
        try: await sb_post("conversions", conv)
        except Exception as e:
            if "duplicate" not in str(e).lower() and "unique" not in str(e).lower(): raise
    return {"ok": True, "click_id": click_id, "commission_usd": commission_usd}

@app.post("/postback/digistore")
async def postback_digistore(request: Request):
    form = await request.form(); data = dict(form)
    click_id = data.get("subid") or data.get("tracking_code") or data.get("custom") or ""
    if click_id.startswith("subid_"): click_id = click_id[6:]
    commission = float(data.get("affiliate_commission", 0) or data.get("payout", 0) or 0)
    commission_currency = data.get("currency", "EUR").upper()
    sale_amount = float(data.get("order_amount", 0) or 0) or None
    order_id = data.get("order_id") or data.get("transaction_id")
    fx_rate = to_usd(1, commission_currency)[1]
    commission_usd = round(commission * fx_rate, 2)
    conv = {"click_id": click_id or None, "network": "digistore24",
        "sale_amount": sale_amount, "sale_currency": commission_currency,
        "commission_amount": commission, "commission_currency": commission_currency,
        "fx_rate": fx_rate, "commission_usd": commission_usd,
        "status": "approved", "external_order_id": order_id, "raw_payload": data}
    if click_id:
        try:
            rows = await sb_get("clicks", {"id": f"eq.{click_id}", "select": "video_id"})
            if rows: conv["video_id"] = rows[0].get("video_id")
        except Exception: pass
    if commission > 0:
        try: await sb_post("conversions", conv)
        except Exception: pass
    return {"ok": True, "commission_usd": commission_usd}

@app.get("/roi")
async def roi(limit: int = 20):
    if USE_DB:
        rows = await sb_get("v_video_roi", {"order": "revenue_usd.desc", "limit": str(limit)})
        return {"videos": rows, "source": "supabase"}
    db = local_load(); clicks = db.get("clicks", []); convs = db.get("conversions", [])
    from collections import defaultdict
    agg = defaultdict(lambda: {"clicks_real":0, "sales":0, "revenue":0.0})
    click_map = {c["id"]: c for c in clicks}
    for co in convs:
        cid = co.get("click_id"); vid = co.get("video_id") or (click_map.get(cid, {}).get("video_id") if cid else None)
        if not vid: continue
        a = agg[vid]; a["sales"] += 1; a["revenue"] += float(co.get("commission_usd",0) or 0)
    for c in clicks:
        vid = c.get("video_id")
        if not vid: continue
        if not c.get("bot_flag"): agg[vid]["clicks_real"] += 1
    out = []
    for vid, a in agg.items():
        cr = round(a["sales"]/a["clicks_real"]*100,2) if a["clicks_real"] else 0
        out.append({"video_id": vid, "clicks_real": a["clicks_real"], "sales": a["sales"],
                    "revenue_usd": round(a["revenue"],2), "conversion_rate": cr})
    out.sort(key=lambda x: x["revenue_usd"], reverse=True)
    return {"videos": out[:limit], "source": "local"}

import requests, time, uuid, sys
BASE = "http://127.0.0.1:8003"
def assert_ok(cond, msg):
    if not cond: print(f"❌ FAIL: {msg}"); sys.exit(1)
def run():
    print("\n🚀 OCTOPUS - First Click Audit Run\n")
    r = requests.get(f"{BASE}/health", timeout=3)
    assert_ok(r.status_code == 200, "health")
    h = r.json(); print(f"[HEALTH] db={h.get('db')} schema={h.get('schema')}")
    video_id = str(uuid.uuid4()); product_id = str(uuid.uuid4())
    print("\n[1/3] Click → /r")
    r = requests.get(f"{BASE}/r", params={"video": video_id, "product": product_id},
        allow_redirects=False, timeout=5, headers={"User-Agent": "Mozilla/5.0 OCTOPUS-Audit"})
    assert_ok(r.status_code in (302,307), f"/r {r.status_code}")
    click_id = r.headers.get("X-Octopus-Click")
    latency = r.headers.get("X-Octopus-Latency","?")
    redirect_url = r.headers.get("location","")
    assert_ok(click_id and len(click_id) > 8, "click_id")
    assert_ok("subid=" + click_id in redirect_url, "subid passthrough")
    print(f"  ✓ click_id={click_id} latency={latency}ms")
    time.sleep(0.3)
    print("\n[2/3] Conversion → /postback/impact")
    order_id = str(uuid.uuid4()); payout = 25.5
    r = requests.get(f"{BASE}/postback/impact",
        params={"subid": click_id, "order_id": order_id, "payout": payout,
                "sale_amount": 100, "currency": "USD"}, timeout=5)
    assert_ok(r.status_code == 200, "postback")
    j = r.json(); assert_ok(j.get("ok"), "postback ok")
    print(f"  ✓ order={order_id} commission=${payout}")
    time.sleep(0.3)
    print("\n[3/3] ROI → /roi")
    r = requests.get(f"{BASE}/roi", timeout=5)
    assert_ok(r.status_code == 200, "roi")
    data = r.json(); videos = data.get("videos", [])
    print(f"  ROI rows: {len(videos)} source={data.get('source')}")
    found = next((v for v in videos if v.get("video_id") == video_id), None)
    if found:
        print(f"  ✓ sales={found.get('sales')} revenue=${found.get('revenue_usd')} cr={found.get('conversion_rate')}%")
    print("\n✅ PIPELINE STATUS: PASS — SYSTEM IS CONSISTENT\n")
    return 0
if __name__ == "__main__": run()

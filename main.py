from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import os, httpx, stripe, uuid
from datetime import datetime

app = FastAPI(title="AI Headshot Generator", version="1.0.0")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PRICE = 499
NANO_BANANA_API_KEY = os.getenv("NANO_BANANA_API_KEY", "")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

orders = {}

STYLES = {
    "professional": "professional corporate headshot, business attire, neutral background, studio lighting, high quality portrait",
    "creative": "creative professional headshot, modern background, artistic lighting, dynamic pose, high quality portrait",
    "executive": "executive portrait, formal business attire, prestigious office background, confident pose, high quality"
}

LANDING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Headshot Generator | Professional Photos in Minutes</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:#0a0a0a;color:#fff}
header{padding:20px 40px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #222}
.logo{font-size:1.5rem;font-weight:700;color:#7c3aed}
.hero{text-align:center;padding:80px 20px 60px}
h1{font-size:3rem;font-weight:800;margin-bottom:20px;background:linear-gradient(135deg,#7c3aed,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.hero p{font-size:1.2rem;color:#aaa;margin-bottom:40px}
.price-badge{display:inline-block;background:#7c3aed;color:#fff;padding:8px 24px;border-radius:50px;font-size:1.1rem;font-weight:700;margin-bottom:40px}
.styles{display:flex;gap:20px;justify-content:center;flex-wrap:wrap;padding:0 20px;margin-bottom:50px}
.style-card{background:#111;border:2px solid #222;border-radius:16px;padding:30px 24px;width:220px;cursor:pointer;transition:all 0.2s}
.style-card:hover,.style-card.selected{border-color:#7c3aed;background:#1a0a2e}
.style-card h3{font-size:1.1rem;margin-bottom:8px}
.style-card p{font-size:0.85rem;color:#888}
.icon{font-size:2rem;margin-bottom:12px}
form{max-width:480px;margin:0 auto;padding:0 20px}
.fg{margin-bottom:20px;text-align:left}
label{display:block;margin-bottom:8px;color:#ccc;font-size:0.9rem}
input{width:100%;padding:12px 16px;background:#111;border:1px solid #333;border-radius:10px;color:#fff;font-size:1rem}
input:focus{outline:none;border-color:#7c3aed}
.btn{width:100%;padding:16px;background:#7c3aed;color:#fff;border:none;border-radius:12px;font-size:1.1rem;font-weight:700;cursor:pointer;margin-top:10px}
.btn:hover{background:#6d28d9}
.features{display:flex;justify-content:center;gap:40px;padding:60px 20px;background:#0f0f0f;flex-wrap:wrap}
.feature{text-align:center;max-width:180px}
.feature h4{margin-bottom:6px}
.feature p{font-size:0.85rem;color:#888}
footer{text-align:center;padding:30px;color:#555;font-size:0.85rem;border-top:1px solid #1a1a1a}
</style>
</head>
<body>
<header><div class="logo">&#10024; AI Headshots</div><div style="color:#888;font-size:0.9rem">Powered by Nano Banana AI</div></header>
<div class="hero">
<h1>Professional Headshots<br>in 60 Seconds</h1>
<p>Studio-quality AI headshots. No photographer needed.</p>
<div class="price-badge">Only $4.99 per headshot</div>
<div class="styles">
  <div class="style-card selected" onclick="selectStyle('professional',this)"><div class="icon">&#128188;</div><h3>Professional</h3><p>Clean, corporate look for LinkedIn &amp; resumes</p></div>
  <div class="style-card" onclick="selectStyle('creative',this)"><div class="icon">&#127912;</div><h3>Creative</h3><p>Modern, artistic style for portfolios</p></div>
  <div class="style-card" onclick="selectStyle('executive',this)"><div class="icon">&#128084;</div><h3>Executive</h3><p>Formal, prestigious look for C-suite</p></div>
</div>
<form action="/create-checkout" method="post">
  <input type="hidden" name="style" id="style_input" value="professional">
  <div class="fg"><label>Your Name</label><input type="text" name="name" placeholder="Jane Smith" required></div>
  <div class="fg"><label>Email (for delivery)</label><input type="email" name="email" placeholder="jane@example.com" required></div>
  <button type="submit" class="btn">Generate My Headshot &mdash; $4.99 &rarr;</button>
</form>
</div>
<div class="features">
  <div class="feature"><div class="icon">&#9889;</div><h4>Instant</h4><p>Ready in under 60 seconds</p></div>
  <div class="feature"><div class="icon">&#127919;</div><h4>Professional</h4><p>Studio-quality results</p></div>
  <div class="feature"><div class="icon">&#128274;</div><h4>Secure</h4><p>Stripe-powered payments</p></div>
  <div class="feature"><div class="icon">&#128231;</div><h4>Delivered</h4><p>Straight to your inbox</p></div>
</div>
<footer>&copy; 2025 AI Headshots. All rights reserved.</footer>
<script>
function selectStyle(style,el){
  document.querySelectorAll('.style-card').forEach(c=>c.classList.remove('selected'));
  el.classList.add('selected');
  document.getElementById('style_input').value=style;
}
</script>
</body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return LANDING_HTML


@app.get("/health")
def health():
    return {"status": "ok", "service": "AI Headshot Generator", "version": "1.0.0"}


@app.post("/create-checkout")
async def create_checkout(name: str = Form(...), email: str = Form(...), style: str = Form("professional")):
    order_id = str(uuid.uuid4())[:8]
    orders[order_id] = {"name": name, "email": email, "style": style, "status": "pending", "created_at": datetime.utcnow().isoformat()}
    if not STRIPE_SECRET_KEY:
        return RedirectResponse(url=f"/success?order_id={order_id}&demo=true", status_code=303)
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price_data": {"currency": "usd", "product_data": {"name": f"AI Headshot - {style.title()} Style", "description": f"Professional AI headshot for {name}"}, "unit_amount": STRIPE_PRICE}, "quantity": 1}],
        mode="payment",
        success_url=f"{BASE_URL}/success?order_id={order_id}&session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{BASE_URL}/",
        customer_email=email,
        metadata={"order_id": order_id}
    )
    return RedirectResponse(url=session.url, status_code=303)


@app.get("/success", response_class=HTMLResponse)
async def success(order_id: str, session_id: str = None, demo: bool = False):
    order = orders.get(order_id, {})
    if order:
        order["status"] = "paid"
        if NANO_BANANA_API_KEY and not demo:
            try:
                prompt = STYLES.get(order.get("style", "professional"), STYLES["professional"])
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post("https://api.nanobanana.ai/v1/images/generate",
                        headers={"Authorization": f"Bearer {NANO_BANANA_API_KEY}"},
                        json={"prompt": prompt, "width": 512, "height": 512})
                    if resp.status_code == 200:
                        order["image_url"] = resp.json().get("url", "")
            except Exception as e:
                order["error"] = str(e)
    name = order.get("name", "there")
    style = order.get("style", "professional").title()
    image_url = order.get("image_url", "")
    img_html = f'<img src="{image_url}" style="max-width:400px;border-radius:16px;margin:20px 0">' if image_url else '<div style="width:200px;height:200px;background:#1a0a2e;border-radius:50%;margin:20px auto;display:flex;align-items:center;justify-content:center;font-size:4rem">&#129331;</div>'
    demo_note = '<p style="color:#888;font-size:0.85rem;margin-top:20px">Demo mode &mdash; connect STRIPE_SECRET_KEY + NANO_BANANA_API_KEY for live use</p>' if demo else ''
    return f"""<!DOCTYPE html><html><head><title>Your Headshot is Ready!</title>
<style>body{{font-family:'Segoe UI',sans-serif;background:#0a0a0a;color:#fff;text-align:center;padding:60px 20px}}
h1{{color:#7c3aed;font-size:2.5rem;margin-bottom:16px}}p{{color:#aaa;font-size:1.1rem;margin-bottom:20px}}
.badge{{background:#7c3aed;color:#fff;padding:8px 20px;border-radius:50px;display:inline-block;margin:10px}}</style></head>
<body><h1>&#10024; Your Headshot is Ready!</h1>
<p>Hi {name}! Your <strong>{style}</strong> headshot has been generated.</p>
{img_html}<br><div class="badge">Order #{order_id}</div>{demo_note}
<br><br><a href="/" style="color:#7c3aed">&larr; Generate Another</a></body></html>"""


@app.get("/order/{order_id}")
def get_order(order_id: str):
    order = orders.get(order_id)
    if not order:
        return JSONResponse({"error": "Order not found"}, status_code=404)
    return order

"""Onboarding Custom Page — lets an installer paste their Bulkgate credentials
and see the inbound/DLR webhook URL they need to configure on Bulkgate's side,
without touching curl/Postman.

Served at GET /setup?locationId=... (GHL Custom Page passes locationId as a
query param automatically when the page is opened inside the sub-account).
"""

_STYLE = """
<style>
body{font-family:-apple-system,Segoe UI,Arial,sans-serif;max-width:640px;margin:32px auto;padding:0 20px;line-height:1.5;color:#1a1a1a;background:#fff}
h1{font-size:1.3rem;margin-bottom:4px}
.sub{color:#666;margin-top:0;margin-bottom:24px}
.card{border:1px solid #ddd;border-radius:10px;padding:20px;margin-bottom:20px}
.card h2{font-size:1.05rem;margin-top:0}
label{display:block;font-weight:600;margin-top:12px;margin-bottom:4px;font-size:.9rem}
input[type=text]{width:100%;box-sizing:border-box;padding:9px 10px;border:1px solid #ccc;border-radius:6px;font-size:.95rem}
button{margin-top:16px;background:#0d4a8f;color:#fff;border:none;padding:10px 18px;border-radius:6px;font-size:.95rem;cursor:pointer}
button.secondary{background:#1e8a8a}
button:disabled{opacity:.5;cursor:default}
.hint{font-size:.85rem;color:#555;margin-top:6px}
.urlbox{background:#f4f4f4;border-radius:6px;padding:10px 12px;font-family:monospace;font-size:.85rem;word-break:break-all;user-select:all}
.step{display:flex;gap:10px;margin-bottom:8px}
.step .n{flex:0 0 auto;width:22px;height:22px;border-radius:50%;background:#0d4a8f;color:#fff;font-size:.8rem;display:flex;align-items:center;justify-content:center}
.ok{color:#1e8a8a;font-weight:600}
.msg{margin-top:10px;font-size:.9rem}
</style>
"""


def render_setup_page(
    *,
    location_id: str | None,
    installation: dict | None,
    webhook_url: str | None,
) -> str:
    if not location_id:
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8">{_STYLE}</head>
<body><h1>Bulkgate SMS setup</h1>
<p>No sub-account context found. Open this page from inside your GHL sub-account
(Settings menu), not directly.</p></body></html>"""

    if not installation:
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8">{_STYLE}</head>
<body><h1>Bulkgate SMS setup</h1>
<p>This sub-account hasn't installed the app yet. Install <strong>Bulkgate
Integration</strong> from the Marketplace first, then come back to this page.</p>
</body></html>"""

    has_creds = bool(installation.get("bulkgate_app_id"))
    confirmed = bool(installation.get("webhook_confirmed_at"))
    masked_id = installation.get("bulkgate_app_id") or ""

    step2_visible = "block" if has_creds else "none"
    confirmed_html = (
        '<p class="ok">✔ You confirmed the webhook is connected.</p>'
        if confirmed
        else '<button class="secondary" onclick="confirmWebhook()">I\'ve connected the webhook in Bulkgate</button>'
        '<div id="confirmMsg" class="msg"></div>'
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bulkgate SMS setup</title>{_STYLE}</head><body>

<h1>Connect your Bulkgate account</h1>
<p class="sub">Two quick steps — takes about a minute.</p>

<div class="card">
<h2>Step 1 — Your Bulkgate credentials</h2>
<p class="hint">
Don't have a Bulkgate account yet? Create one for free at
<a href="https://portal.bulkgate.com/sign/up" target="_blank">portal.bulkgate.com/sign/up</a>.
Already have one? Log in, then go to <strong>Modules &amp; APIs</strong> in the left
menu — your <strong>Application ID</strong> and <strong>Application Token</strong> are
shown under "Login credentials" (click "+ ADD TOKEN" if you don't have a token yet).
</p>

<label>Application ID</label>
<input type="text" id="appId" placeholder="e.g. 38296" value="{masked_id}">

<label>Application Token</label>
<input type="text" id="appToken" placeholder="Paste your Application Token">

<button onclick="saveCreds()">Save credentials</button>
<div id="credsMsg" class="msg"></div>
</div>

<div class="card" id="step2" style="display:{step2_visible}">
<h2>Step 2 — Connect the webhook in Bulkgate</h2>
<p class="hint">This lets Bulkgate send delivery status and incoming SMS replies back into GHL.</p>
<div class="step"><div class="n">1</div><div>In Bulkgate, go to <strong>Modules &amp; APIs</strong> → find your Application → <strong>Web hooks</strong> section → <strong>Delivery reports</strong> → <strong>CONFIGURE</strong>.</div></div>
<div class="step"><div class="n">2</div><div>Paste this URL into the <strong>"URL delivery reports"</strong> field:</div></div>
<p class="urlbox">{webhook_url}</p>
<div class="step"><div class="n">3</div><div>Leave all three checkboxes (availability check, error-only, bulk) unchecked, then Save.</div></div>
<div class="step"><div class="n">4</div><div>Back in this GHL sub-account: <strong>Settings → Phone Numbers → Advanced → SMS Provider → select "Bulkgate SMS" → Save</strong>.</div></div>
{confirmed_html}
</div>

<script>
const locationId = {location_id!r};

async function saveCreds() {{
  const appId = document.getElementById('appId').value.trim();
  const appToken = document.getElementById('appToken').value.trim();
  const msg = document.getElementById('credsMsg');
  if (!appId || !appToken) {{ msg.textContent = 'Please fill in both fields.'; return; }}
  msg.textContent = 'Saving...';
  try {{
    const res = await fetch('/admin/credentials', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        location_id: locationId,
        bulkgate_app_id: appId,
        bulkgate_app_token: appToken
      }})
    }});
    const data = await res.json();
    if (res.ok) {{
      msg.textContent = 'Saved! Scroll down for step 2.';
      document.getElementById('step2').style.display = 'block';
    }} else {{
      msg.textContent = 'Error: ' + (data.detail || 'could not save credentials');
    }}
  }} catch (e) {{
    msg.textContent = 'Network error, please try again.';
  }}
}}

async function confirmWebhook() {{
  const msg = document.getElementById('confirmMsg');
  msg.textContent = 'Saving...';
  try {{
    const res = await fetch('/setup/confirm', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{location_id: locationId}})
    }});
    if (res.ok) {{ location.reload(); }} else {{ msg.textContent = 'Could not save, try again.'; }}
  }} catch (e) {{ msg.textContent = 'Network error, please try again.'; }}
}}
</script>
</body></html>"""

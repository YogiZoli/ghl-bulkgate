"""Onboarding Custom Page — the installer's guided, one-page setup.

Served at GET /setup?locationId=... (GHL Custom Page passes locationId as a
query param automatically when the page is opened inside the sub-account).

Design goal (Zoltan's brief): the friendliest possible flow. The user only ever
has to (1) paste two values FROM Bulkgate into this page, and (2) copy ONE URL
FROM this page into Bulkgate. Every value that must move between systems has a
one-click copy button; every place they need to go has a real clickable link.
No curl, no manual typing of long strings.
"""

_STYLE = """
<style>
:root{
  --brand:#0d4a8f; --brand-2:#1466c2; --accent:#12b3a6; --ink:#1a2230;
  --muted:#5b6472; --line:#e3e8ef; --bg:#f5f7fa; --ok:#0f9d78; --okbg:#e7f7f0;
}
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
  margin:0;background:var(--bg);color:var(--ink);line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:660px;margin:0 auto;padding:28px 18px 64px}
.hero{background:linear-gradient(135deg,var(--brand),var(--brand-2));color:#fff;
  border-radius:16px;padding:26px 26px 22px;box-shadow:0 10px 30px rgba(13,74,143,.18)}
.hero h1{margin:0 0 6px;font-size:1.5rem;letter-spacing:-.02em}
.hero p{margin:0;opacity:.92;font-size:.98rem}
.prog{display:flex;gap:8px;margin-top:18px}
.prog .dot{flex:1;height:6px;border-radius:6px;background:rgba(255,255,255,.28)}
.prog .dot.on{background:#fff}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:22px;
  margin-top:18px;box-shadow:0 1px 3px rgba(16,34,64,.04)}
.card.locked{opacity:.55;pointer-events:none;filter:grayscale(.2)}
.chead{display:flex;align-items:center;gap:12px;margin-bottom:6px}
.badge{flex:0 0 auto;width:30px;height:30px;border-radius:50%;background:var(--brand);
  color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center;font-size:.95rem}
.chead h2{margin:0;font-size:1.12rem}
.card .lead{color:var(--muted);font-size:.92rem;margin:2px 0 16px 42px}
.field{margin:0 0 14px 42px}
label{display:block;font-weight:600;margin-bottom:5px;font-size:.9rem}
input[type=text]{width:100%;padding:11px 12px;border:1.5px solid #cdd5df;border-radius:9px;
  font-size:1rem;transition:border-color .15s,box-shadow .15s}
input[type=text]:focus{outline:none;border-color:var(--brand-2);box-shadow:0 0 0 3px rgba(20,102,194,.15)}
.help{font-size:.85rem;color:var(--muted);margin:5px 0 0}
.help a{color:var(--brand-2);font-weight:600}
.btn{appearance:none;border:none;cursor:pointer;font-size:.98rem;font-weight:600;
  border-radius:9px;padding:12px 20px;transition:transform .05s,background .15s}
.btn:active{transform:translateY(1px)}
.btn-primary{background:var(--brand);color:#fff}
.btn-primary:hover{background:var(--brand-2)}
.btn-ghost{background:#eef2f7;color:var(--brand)}
.btn:disabled{opacity:.5;cursor:default}
.rowbtn{margin:2px 0 0 42px}
.step{display:flex;gap:12px;margin:0 0 14px 42px}
.step .n{flex:0 0 auto;width:24px;height:24px;border-radius:50%;background:#eef2f7;
  color:var(--brand);font-weight:700;font-size:.82rem;display:flex;align-items:center;justify-content:center}
.step .t{flex:1;font-size:.94rem}
.copyrow{display:flex;align-items:stretch;gap:8px;margin:6px 0 0 42px}
.copyrow .val{flex:1;min-width:0;background:#f2f5f9;border:1.5px dashed #c7d0dc;border-radius:9px;
  padding:11px 12px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.82rem;
  word-break:break-all;color:#243}
.copybtn{flex:0 0 auto;display:flex;align-items:center;gap:6px;background:var(--brand);color:#fff;
  border:none;border-radius:9px;padding:0 15px;font-weight:600;font-size:.86rem;cursor:pointer;transition:background .15s}
.copybtn:hover{background:var(--brand-2)}
.copybtn.done{background:var(--ok)}
.copybtn svg{width:15px;height:15px}
.linkbtn{display:inline-flex;align-items:center;gap:8px;text-decoration:none;background:#eef2f7;
  color:var(--brand);font-weight:600;font-size:.92rem;border-radius:9px;padding:11px 16px;margin:2px 0 0 42px}
.linkbtn:hover{background:#e3ebf5}
.linkbtn svg{width:15px;height:15px}
.msg{margin:12px 0 0 42px;font-size:.9rem;min-height:1.1em}
.msg.err{color:#c0392b}
.msg.ok{color:var(--ok);font-weight:600}
.done-banner{display:flex;align-items:center;gap:10px;background:var(--okbg);border:1px solid #b8e6d4;
  color:var(--ok);border-radius:11px;padding:14px 16px;margin:2px 0 0 42px;font-weight:600}
.done-banner svg{width:20px;height:20px;flex:0 0 auto}
.notice{max-width:660px;margin:24px auto 0;text-align:center;color:var(--muted);font-size:.85rem}
.gk{margin:0 0 0 42px}
.gk p{margin:0 0 10px;font-size:.9rem;padding:11px 14px;border-radius:10px}
.gk p:last-child{margin-bottom:0}
.gk-ok{background:var(--okbg);border:1px solid #b8e6d4;color:#1a4a3a}
.gk-no{background:#fff4f0;border:1px solid #f3d3c7;color:#7a3b2a}
</style>
"""

_COPY_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" '
    'height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>'
)
_CHECK_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" '
    'stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>'
)
_EXT_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6"/>'
    '<path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>'
)


def _shell(inner: str) -> str:
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        f"<title>Bulkgate SMS setup</title>{_STYLE}</head><body><div class=\"wrap\">"
        f"{inner}</div></body></html>"
    )


def render_setup_page(
    *,
    location_id: str | None,
    installation: dict | None,
    webhook_url: str | None,
) -> str:
    if not location_id:
        return _shell(
            '<div class="hero"><h1>Bulkgate SMS setup</h1>'
            "<p>Open this page from inside your GHL sub-account (left menu → "
            "<strong>Bulkgate Setup</strong>), not directly.</p></div>"
        )

    if not installation:
        return _shell(
            '<div class="hero"><h1>Bulkgate SMS setup</h1>'
            "<p>This sub-account hasn't installed the app yet. Install "
            "<strong>Bulkgate Integration</strong> from the Marketplace first, "
            "then reopen this page.</p></div>"
        )

    has_creds = bool(installation.get("bulkgate_app_id"))
    confirmed = bool(installation.get("webhook_confirmed_at"))
    app_id = installation.get("bulkgate_app_id") or ""
    url = webhook_url or ""

    step2_class = "" if has_creds else "locked"
    d1 = "on" if True else ""
    d2 = "on" if has_creds else ""
    d3 = "on" if confirmed else ""

    if confirmed:
        step2_tail = (
            f'<div class="done-banner">{_CHECK_SVG}'
            "<span>All set — Bulkgate SMS is connected and ready to use.</span></div>"
        )
    else:
        step2_tail = (
            '<button class="btn btn-primary" style="margin-left:42px;margin-top:4px" '
            'onclick="confirmWebhook()">I\'ve pasted the URL &amp; selected the provider</button>'
            '<div id="confirmMsg" class="msg"></div>'
        )

    body = f"""
<div class="hero">
  <h1>Connect Bulkgate SMS</h1>
  <p>Two short steps and your GoHighLevel sends &amp; receives SMS through your own Bulkgate account.</p>
  <div class="prog"><div class="dot {d1}"></div><div class="dot {d2}"></div><div class="dot {d3}"></div></div>
</div>

<div class="card">
  <div class="chead"><div class="badge">1</div><h2>Paste your Bulkgate keys</h2></div>
  <p class="lead">Copy these two values from Bulkgate and paste them here.</p>
  <p class="help" style="margin-left:42px">
    No Bulkgate account yet? <a href="https://portal.bulkgate.com/sign/up" target="_blank" rel="noopener">Create a free one →</a><br>
    Already have one? <a href="https://portal.bulkgate.com/application/" target="_blank" rel="noopener">Open Modules &amp; APIs →</a>
    — your <strong>Application ID</strong> and <strong>Application Token</strong> are under
    “Login credentials” (click <strong>+ ADD TOKEN</strong> if you don't have a token yet).
  </p>

  <div class="field">
    <label for="appId">Application ID</label>
    <input type="text" id="appId" placeholder="Your 5-digit number, e.g. 12345" value="{app_id}" autocomplete="off">
  </div>
  <div class="field">
    <label for="appToken">Application Token</label>
    <input type="text" id="appToken" placeholder="Long code of letters &amp; numbers" autocomplete="off">
  </div>
  <div class="rowbtn"><button class="btn btn-primary" onclick="saveCreds()">Save &amp; continue</button></div>
  <div id="credsMsg" class="msg"></div>
</div>

<div class="card {step2_class}" id="step2">
  <div class="chead"><div class="badge">2</div><h2>Connect the webhook in Bulkgate</h2></div>
  <p class="lead">This lets Bulkgate push delivery reports and incoming replies back into GHL.</p>

  <div class="step"><div class="n">1</div><div class="t">Copy your personal webhook URL:</div></div>
  <div class="copyrow">
    <div class="val" id="hookUrl">{url}</div>
    <button class="copybtn" id="hookCopy" onclick="copyUrl()">{_COPY_SVG}<span>Copy</span></button>
  </div>

  <div class="step" style="margin-top:16px"><div class="n">2</div><div class="t">
    Open Bulkgate, go to <strong>Modules &amp; APIs → your Application → Web hooks →
    Delivery reports → CONFIGURE</strong>, and paste the URL into the
    <strong>“URL delivery reports”</strong> field (Ctrl/Cmd+V), then Save.
  </div></div>
  <a class="linkbtn" href="https://portal.bulkgate.com/application/" target="_blank" rel="noopener">{_EXT_SVG}Open Bulkgate webhooks</a>

  <div class="step" style="margin-top:16px"><div class="n">3</div><div class="t">
    Back in this GHL sub-account: <strong>Settings → Phone Numbers → Advanced →
    SMS Provider → select “Bulkgate SMS” → Save</strong>.
  </div></div>

  {step2_tail}
</div>

<div class="card">
  <div class="chead"><div class="badge" style="background:var(--accent)">i</div><h2>Good to know</h2></div>
  <p class="lead">What this app does today — and what it doesn't (yet).</p>
  <div class="gk">
    <p class="gk-ok"><strong>&#10003; Supported now:</strong> Two-way <strong>SMS</strong> — send messages, receive replies, and get delivery reports right inside your GHL conversations. Messages are sent from the phone number Bulkgate assigns to your account.</p>
    <p class="gk-no"><strong>Not supported yet:</strong> Viber, WhatsApp, RCS, MMS / picture messages, and custom Sender IDs (showing your own brand name or number as the sender).</p>
  </div>
</div>

<p class="notice">Your keys are encrypted before they're stored, and are permanently deleted the moment you uninstall the app.</p>

<script>
const locationId = {location_id!r};

function flash(el, cls, text) {{ el.className = 'msg ' + cls; el.textContent = text; }}

async function saveCreds() {{
  const appId = document.getElementById('appId').value.trim();
  const appToken = document.getElementById('appToken').value.trim();
  const msg = document.getElementById('credsMsg');
  if (!appId || !appToken) {{ flash(msg, 'err', 'Please fill in both fields.'); return; }}
  flash(msg, '', 'Saving…');
  try {{
    const res = await fetch('/admin/credentials', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{location_id: locationId, bulkgate_app_id: appId, bulkgate_app_token: appToken}})
    }});
    const data = await res.json().catch(() => ({{}}));
    if (res.ok) {{
      flash(msg, 'ok', '✓ Saved. Now finish step 2 below.');
      const s2 = document.getElementById('step2');
      s2.classList.remove('locked');
      s2.scrollIntoView({{behavior: 'smooth', block: 'start'}});
    }} else {{
      flash(msg, 'err', 'Error: ' + (data.detail || 'could not save credentials'));
    }}
  }} catch (e) {{ flash(msg, 'err', 'Network error, please try again.'); }}
}}

async function copyUrl() {{
  const url = document.getElementById('hookUrl').textContent.trim();
  const btn = document.getElementById('hookCopy');
  try {{
    await navigator.clipboard.writeText(url);
  }} catch (e) {{
    const r = document.createRange(); r.selectNode(document.getElementById('hookUrl'));
    const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
    try {{ document.execCommand('copy'); }} catch (_) {{}} sel.removeAllRanges();
  }}
  btn.classList.add('done');
  btn.innerHTML = {_CHECK_SVG!r} + '<span>Copied!</span>';
  setTimeout(() => {{ btn.classList.remove('done'); btn.innerHTML = {_COPY_SVG!r} + '<span>Copy</span>'; }}, 2200);
}}

async function confirmWebhook() {{
  const msg = document.getElementById('confirmMsg');
  flash(msg, '', 'Saving…');
  try {{
    const res = await fetch('/setup/confirm', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{location_id: locationId}})
    }});
    if (res.ok) {{ location.reload(); }} else {{ flash(msg, 'err', 'Could not save, try again.'); }}
  }} catch (e) {{ flash(msg, 'err', 'Network error, please try again.'); }}
}}
</script>
"""
    return _shell(body)

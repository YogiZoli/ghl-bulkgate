# ghl-bulkgate

**Public GoHighLevel Marketplace app** that registers as an **SMS Conversation
Provider** and bridges GHL ⇄ **Bulkgate**:

- **Outbound:** SMS sent from GHL → delivered over the Bulkgate network (cheap, with a Hungarian sender name).
- **Inbound:** replies + delivery reports (DLR) flow back into the GHL Unified Inbox / message status.

> Standalone codebase. Shares **nothing** with the Billingo/Számlázz connector —
> separate repo, separate OAuth, separate Railway service, separate lifecycle.
> Repo: `github.com/YogiZoli/ghl-bulkgate`

---

## Architecture

```
OUTBOUND
  GHL (user sends SMS)
    └─ POST  Delivery URL  ─►  /ghl/outbound
          ├─ resolve location → Bulkgate app_id+token (encrypted, per install)
          ├─ normalize number (+36 / 0036 / 0630 / … → 3630…)
          ├─ Bulkgate send (gSystem sender by default, country=hu, unicode=false)
          ├─ store messageId ⇄ Bulkgate smsID  (DLR routing + idempotency)
          └─ update GHL message status ("pending" until DLR), return 200 fast

INBOUND / DLR
  Bulkgate  ─►  GET/POST  /bulkgate/inbound/{webhook_token}
          ├─ status 1  → GHL status "delivered"
          ├─ status 3  → GHL status "failed"
          ├─ status 2/13 → buffered/seen (logged, no GHL change)
          └─ status 10 → incoming SMS: opt-out check → upsert contact →
                          add inbound message to GHL Inbox
```

Each installation gets a **unique inbound webhook token** so DLR/incoming
callbacks resolve to the correct tenant — critical because every installer uses
their own Bulkgate account and configures their own callback URL.

## Tech stack

Python 3.12 · FastAPI · SQLite (MVP) · Railway · Fernet-encrypted credential
store · `tzdata` in requirements.

## Project layout

```
app/
  main.py            FastAPI: /health, /oauth/callback, /ghl/outbound,
                     /bulkgate/inbound/{token}, /admin/credentials
  services.py        outbound + inbound/DLR business logic (unit-tested)
  bulkgate_client.py Bulkgate Advanced Transactional v2 send + response parsing
  ghl_client.py      GHL OAuth, inbound message, message-status, contact upsert
  store.py           SQLite: installs, message map, opt-outs, idempotency
  phone.py           HU → E.164 normalization
  sms_text.py        GSM-7 vs UCS-2 detection + segment counting
  optout.py          STOP / LEIRATKOZÁS keyword handling
  crypto.py          Fernet encrypt/decrypt
  config.py          env-driven settings
tests/               fixture-based tests, no network (50 tests)
```

## Verified API facts (checked against official docs at build time)

**Bulkgate — Advanced Transactional v2**
`POST https://portal.bulkgate.com/api/2.0/advanced/transactional` (JSON).
Auth in body: `application_id` + `application_token`. Key fields: `number`
(international, no `+`), `text`, `country` (ISO alpha-2, e.g. `hu`), and the SMS
channel object `channel.sms.{sender_id, sender_id_value?, unicode}`.
Success → `data.response[].message_id`/`status`/`number`;
error → top-level `{type, code, error}`.

⚠️ **Field lessons (VoxFlow live tests + Bulkgate support ticket HZL-CTQKD-699):**

- **Hungary does NOT support text sender IDs (`gText`)** — the API replies
  `"accepted": 1` and the carrier silently drops the SMS. Default sender is
  therefore **`gSystem`**. Only configure `gText` per install for countries
  that support it, with a Bulkgate-whitelisted name (max 11 chars,
  alphanumeric, no spaces).
- **Bulkgate "accepted" ≠ delivered.** We report `pending` to GHL on accept
  and only set `delivered`/`failed` from the DLR callback.
- **Unicode cost protection:** Hungarian `ő`/`ű` force UCS-2 (70 chars/segment
  → 2-3× cost). Default `UNICODE_MODE=never` keeps `unicode:false` so Bulkgate
  transliterates accents (`ő`→`o`) at GSM-7 pricing. Set `auto` for real UCS-2.
- **Endpoint:** default is `/advanced/promotional` — the field-proven VoxFlow
  path, available on every account. `/advanced/transactional` requires the
  Transactional module enabled on the installer's Bulkgate account.
  Configurable via `BULKGATE_API_URL`.
DLR/incoming are delivered to your callback **via GET query params**: `status`
(1 delivered · 2 buffered · 3 not_delivered · 10 incoming · 13 seen), `smsID`,
`to`, `price`, and for status 10 also `from` + `message`.

**GoHighLevel — Custom Conversation Provider**
Scopes: `conversations/message.write` (outbound webhook + add inbound + update
status), `conversations.write`, `conversations.readonly`, `contacts.write`,
`contacts.readonly`, `conversations/message.readonly`.
Outbound webhook payload: `contactId, locationId, messageId, type, message,
phone, userId, attachments`.
Inbound: `POST /conversations/messages/inbound` (`type:"SMS"`, `contactId`).
Status: `PUT /conversations/messages/{messageId}/status` — only the conversation
provider's own marketplace app token may update status.

### ⚠️ One correction vs. the original build brief
The brief said to tick **“Is this a Custom Conversation Provider.”** Per GHL's
docs that checkbox creates an *additional* channel and **requires**
`conversationProviderId` on inbound. But the brief's activation step
(*Settings → Phone Numbers → Advanced → SMS Provider → select → Save*) is the
**“Replace default SMS provider”** model, where you **do NOT** tick the box and
`conversationProviderId` is **not required**.

This app supports **both**: `conversationProviderId` is optional and configurable
(`GHL_CONVERSATION_PROVIDER_ID` env, or per-install in the DB). For the
replace-default model, leave it blank and **don't** tick the box.

---

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in GHL creds + FERNET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # FERNET_KEY
uvicorn app.main:app --reload --port 8080
pytest                        # 47 tests, no network
```

## Deploy to Railway

1. Push this repo to `github.com/YogiZoli/ghl-bulkgate`.
2. Railway → **New Project → Deploy from GitHub** → select the repo.
3. Set service **Variables** (from `.env.example`): `GHL_CLIENT_ID`,
   `GHL_CLIENT_SECRET`, `GHL_REDIRECT_URI`, `FERNET_KEY`, and optionally
   `DEFAULT_SENDER_ID_VALUE`, `GHL_CONVERSATION_PROVIDER_ID`.
4. (Recommended) attach a **persistent volume** and point `DATABASE_PATH` at it
   so the SQLite store survives redeploys.
5. Railway gives you a public HTTPS URL — this is your **Delivery URL base** and
   **OAuth redirect** host. Healthcheck path is `/health`.

## Marketplace setup (the long pole — start early)

1. Create a **Public** Marketplace app at <https://marketplace.gohighlevel.com>.
2. **Auth**: add the scopes listed above, set redirect
   `https://<railway-host>/oauth/callback`, save client id/secret into Railway.
3. **Conversation Provider** module: Name, Type = **SMS**, Delivery URL =
   `https://<railway-host>/ghl/outbound`. (Replace-default model → leave the
   custom-provider checkbox **unticked**.)
4. **Submit for review** → GHL approval (this is the multi-day step a private app
   wouldn't have).

## Per-install setup (each sub-account)

1. Install the app → OAuth redirect stores tokens; the success page shows the
   installation's unique **inbound webhook URL**.
2. Provide the location's Bulkgate **Application ID + token** (e.g. via the
   `POST /admin/credentials` setup endpoint — secure this behind real auth/a
   Custom Page before production).
3. In Bulkgate, set that **inbound webhook URL** as the incoming/DLR callback.
4. In the sub-account: **Settings → Phone Numbers → Advanced Settings → SMS
   Provider → select this provider → Save**.

## Definition of done

A published app a sub-account installs and enables as its SMS provider; GHL SMS
go out via Bulkgate with a Hungarian sender name; delivery status returns to GHL;
inbound SMS land on the right contact in the Unified Inbox; `STOP`/`LEIRATKOZÁS`
opt-out works; every webhook returns 200 quickly. (Code is done with
fixture tests; live test + marketplace approval are external dependencies.)

## Edge cases handled

- **Opt-out:** `STOP`/`STOPP`/`LEIRATKOZÁS`/`UNSUBSCRIBE`/… flags the contact;
  further outbound to that number is blocked and marked *failed*.
  `START`/`FELIRATKOZÁS` re-subscribes. Plain conversational words
  (`NEM`/`IGEN`/`YES`) are deliberately NOT keywords — a "Nem" reply in a
  two-way conversation must not unsubscribe anyone.
- **Number normalization:** `+3630…`, `0036…`, `0630…`, bare `30…` → `3630…`;
  invalid numbers are logged and reported as *failed* (never 5xx to GHL).
- **Delivery failure:** Bulkgate `status=3` → GHL *failed* (never silent).
- **Idempotency:** duplicate GHL `messageId` and repeated Bulkgate DLRs are
  de-duped (stable SHA-256 digests, not process-salted `hash()`).
- **Unicode/long SMS:** `UNICODE_MODE=never` (default) keeps GSM-7 pricing via
  Bulkgate transliteration; `auto` detects UCS-2 for real accents. Segment
  counting included.
- **Multi-tenant:** Bulkgate keys + tokens stored per-install, encrypted, never
  mixed across locations.
```

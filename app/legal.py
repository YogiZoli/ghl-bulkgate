"""Static Privacy Policy & Terms of Service HTML for the Bulkgate Integration app.

Standalone content — deliberately NOT shared with or linked to the
CommentClient (C2C) privacy/terms pages, per Zoltan's instruction to avoid
any cross-reference between the two separate Marketplace apps.
"""

_STYLE = """
<style>
body{font-family:-apple-system,Segoe UI,Arial,sans-serif;max-width:780px;margin:40px auto;padding:0 20px;line-height:1.55;color:#1a1a1a}
h1{font-size:1.6rem}h2{font-size:1.15rem;margin-top:2em;border-bottom:1px solid #ddd;padding-bottom:.3em}
table{border-collapse:collapse;width:100%;margin:1em 0}
td,th{border:1px solid #ccc;padding:6px 10px;text-align:left;vertical-align:top}
footer{margin-top:3em;font-size:.85em;color:#666}
</style>
"""

PRIVACY_HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Privacy Policy – Bulkgate Integration</title>{_STYLE}</head><body>
<h1>Bulkgate Integration</h1>
<p><strong>Privacy Policy</strong><br>
Effective date: 3 July 2026 | Last updated: 3 July 2026</p>

<h2>1. Introduction</h2>
<p>Welcome to Bulkgate Integration (the "Service"), a GoHighLevel Marketplace
application. We are committed to protecting your personal data in compliance
with the UK GDPR, the EU GDPR (2016/679), and applicable data-protection
legislation. This Privacy Policy explains what data we collect, why we
collect it, how we protect it, and what rights you have.</p>
</body></html>"""

_PRIVACY_BODY_2 = """
<h2>2. Data Controller</h2>
<table>
<tr><td>Company name</td><td>Mindful Momentum Ltd</td></tr>
<tr><td>Registered address</td><td>Hova House, 1 Hova Villas, Brighton &amp; Hove, BN3 3DH, United Kingdom</td></tr>
<tr><td>Company number</td><td>14864005</td></tr>
<tr><td>UTR</td><td>61309 15915</td></tr>
<tr><td>Support email</td><td>ghladmins@gmail.com</td></tr>
<tr><td>Hungarian business address</td><td>Weiner Leó utca 4., 1066 Budapest, Hungary</td></tr>
<tr><td>Hungarian phone</td><td>+36 20 515 1514</td></tr>
</table>

<h2>3. What is Bulkgate Integration?</h2>
<p>Bulkgate Integration is a GoHighLevel Marketplace application that acts as
an SMS Conversation Provider: it delivers outbound SMS messages sent from a
subscriber's GoHighLevel (GHL) sub-account through the subscriber's own
Bulkgate account, and returns inbound SMS replies and delivery status reports
back into the GHL Unified Inbox. Each subscriber connects and pays for their
own Bulkgate account directly (pay-as-you-go); the Service does not process
or resell SMS credit.</p>

<h2>4. Data Processors</h2>
<table>
<tr><th>Processor</th><th>Role</th><th>Location</th></tr>
<tr><td>HighLevel Inc. (GoHighLevel)</td><td>CRM, Conversations/Unified Inbox</td><td>USA</td></tr>
<tr><td>TOPefekt s.r.o. (Bulkgate)</td><td>SMS delivery, using the subscriber's own Bulkgate account</td><td>EU</td></tr>
<tr><td>Railway Corp.</td><td>Application hosting</td><td>USA</td></tr>
</table>
<p>All sub-processors are bound by GDPR-compatible Data Processing Agreements.
Transfers to the USA are covered by Standard Contractual Clauses (SCCs)
and/or the EU–US Data Privacy Framework.</p>
"""

_PRIVACY_BODY_3 = """
<h2>5. Personal Data We Process</h2>
<ul>
<li><strong>SMS message data:</strong> recipient/sender phone numbers, message
text content, delivery timestamps and status — passed through between GHL
and Bulkgate.</li>
<li><strong>GoHighLevel contact data:</strong> contact name, phone number, and
conversation history relevant to the SMS thread, as stored in the
subscriber's GHL sub-account.</li>
<li><strong>Subscriber account data:</strong> GHL location ID, OAuth
access/refresh tokens (Fernet-encrypted at rest), Bulkgate Application ID and
token (Fernet-encrypted at rest, provided by the subscriber).</li>
<li><strong>Technical data:</strong> IP addresses, API request logs, error
logs — retained for security and debugging.</li>
</ul>

<h2>6. Legal Basis and Purpose</h2>
<table>
<tr><th>Purpose</th><th>Legal basis (GDPR Art. 6)</th></tr>
<tr><td>Delivering SMS via the subscriber's Bulkgate account</td><td>Contract performance — Art. 6(1)(b)</td></tr>
<tr><td>OAuth authentication and token management</td><td>Contract performance — Art. 6(1)(b)</td></tr>
<tr><td>Security, fraud prevention, debugging</td><td>Legitimate interest — Art. 6(1)(f)</td></tr>
<tr><td>Legal and regulatory compliance</td><td>Legal obligation — Art. 6(1)(c)</td></tr>
</table>

<h2>7. Retention Periods</h2>
<ul>
<li><strong>Active installation:</strong> data is retained for the duration of the active GHL installation.</li>
<li><strong>Post-uninstall:</strong> account data and encrypted credentials are deleted within 90 days of uninstall.</li>
<li><strong>Security / audit logs:</strong> up to 12 months.</li>
<li><strong>OAuth &amp; Bulkgate tokens:</strong> deleted immediately upon uninstall or revocation.</li>
</ul>
"""

_PRIVACY_BODY_4 = """
<h2>8. Your Rights</h2>
<p>Under the UK GDPR and EU GDPR you have the right to access, rectify,
erase, restrict, port, and object to the processing of your data, and to
withdraw consent where processing is based on consent. To exercise any of
these rights, contact us at ghladmins@gmail.com. We will respond within
30 days.</p>

<h2>9. Cookies</h2>
<p>The Bulkgate Integration web application uses strictly necessary session
cookies for OAuth state verification only. No marketing or analytics cookies
are set by the Service itself.</p>

<h2>10. Security</h2>
<ul>
<li>TLS encryption on all data in transit.</li>
<li>OAuth and Bulkgate API tokens encrypted at rest using Fernet symmetric encryption.</li>
<li>Access controls: only authorised personnel and automated systems access production data.</li>
<li>Data breach notification within 72 hours of discovery where required by law.</li>
</ul>

<h2>11. Children's Privacy</h2>
<p>The Service is not directed at individuals under the age of 16. We do not
knowingly collect personal data from children.</p>

<h2>12. Supervisory Authority</h2>
<p>If you believe our data processing violates applicable law, you may lodge
a complaint with the UK Information Commissioner's Office (ico.org.uk), the
Hungarian NAIH (naih.hu), or your local Data Protection Authority.</p>

<h2>13. Changes to This Policy</h2>
<p>We may update this Privacy Policy from time to time. Material changes
will be communicated via a notice on this page at least 15 days before
taking effect.</p>

<h2>14. Contact</h2>
<p><strong>Mindful Momentum Ltd</strong><br>
Email: ghladmins@gmail.com<br>
Hungarian phone: +36 20 515 1514<br>
Address: Hova House, 1 Hova Villas, Brighton &amp; Hove, BN3 3DH, United Kingdom</p>
<footer>© 2026 Bulkgate Integration / Mindful Momentum Ltd. All rights reserved.</footer>
</body></html>
"""

PRIVACY_HTML = PRIVACY_HTML.replace(
    "</body></html>",
    _PRIVACY_BODY_2 + _PRIVACY_BODY_3 + _PRIVACY_BODY_4,
)

TERMS_HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Terms of Service – Bulkgate Integration</title>{_STYLE}</head><body>
<h1>Bulkgate Integration</h1>
<p><strong>Terms of Service</strong><br>
Effective date: 3 July 2026 | Last updated: 3 July 2026</p>

<h2>1. Provider Details</h2>
<table>
<tr><td>Company name</td><td>Mindful Momentum Ltd</td></tr>
<tr><td>Registered address</td><td>Hova House, 1 Hova Villas, Brighton &amp; Hove, BN3 3DH, United Kingdom</td></tr>
<tr><td>Company number</td><td>14864005</td></tr>
<tr><td>UTR</td><td>61309 15915</td></tr>
<tr><td>Support email</td><td>ghladmins@gmail.com</td></tr>
<tr><td>Hungarian business address</td><td>Weiner Leó utca 4., 1066 Budapest, Hungary</td></tr>
<tr><td>Brand name</td><td>Bulkgate Integration</td></tr>
</table>

<h2>2. Scope and Acceptance</h2>
<p>These Terms of Service ("Terms") govern access to and use of the Bulkgate
Integration application ("Service") operated by Mindful Momentum Ltd
("Provider", "we", "us"). By installing the Service from the GoHighLevel
Marketplace or otherwise using it, you ("User", "Subscriber") accept these
Terms in full. If you do not agree, do not install or use the Service.</p>
"""

_TERMS_BODY_2 = """
<h2>3. Description of the Service</h2>
<p>Bulkgate Integration is a GoHighLevel Marketplace application that:</p>
<ul>
<li>Registers as an SMS Conversation Provider inside a GHL sub-account.</li>
<li>Delivers outbound SMS sent from GHL through the Subscriber's own Bulkgate account.</li>
<li>Returns inbound SMS replies and delivery status reports into the GHL Unified Inbox.</li>
</ul>
<p>The Service is built on and integrated with GoHighLevel (HighLevel Inc.)
and Bulkgate (TOPefekt s.r.o.) as third-party platforms.</p>

<h2>4. Account, Installation and Your Own Bulkgate Account</h2>
<p>To use the Service you must have an active GoHighLevel sub-account, install
the Service via the official GoHighLevel Marketplace, and authorise it via
OAuth 2.0. <strong>You must also hold your own active Bulkgate account and
provide your own Bulkgate Application ID and token.</strong> The Provider
does not supply, resell, or subsidise Bulkgate SMS credit — all SMS usage is
billed directly by Bulkgate to your own Bulkgate account, entirely separate
from and in addition to any fee for the Service itself.</p>

<h2>5. Fees and Billing</h2>
<p>Any fee for the Service itself is billed through the GoHighLevel
Marketplace billing system, as shown in the Marketplace listing. SMS usage
costs are billed separately and directly by Bulkgate to the Subscriber's own
Bulkgate account and are entirely outside the Provider's control or
billing.</p>
"""

_TERMS_BODY_3 = """
<h2>6. User Obligations</h2>
<ul>
<li>Provide accurate information when setting up the Service.</li>
<li>Comply with the GoHighLevel Terms of Service and Bulkgate's own terms.</li>
<li>Not use the Service for spam, phishing, harassment, or any unlawful purpose.</li>
<li>Not reverse-engineer, copy, resell, or redistribute the Service.</li>
<li>Keep API credentials and OAuth tokens confidential.</li>
<li>Obtain any consents required under applicable law (e.g. GDPR, TCPA) before sending SMS to a contact.</li>
</ul>

<h2>7. Provider Rights and Obligations</h2>
<p>The Provider will deliver the Service with reasonable skill and care,
respond to support requests within 2 business days, and handle personal data
in accordance with the <a href="/privacy">Privacy Policy</a>. The Provider
reserves the right to modify or update the Service, suspend or terminate
access for breach of these Terms, and amend these Terms with prior notice.</p>

<h2>8. Intellectual Property</h2>
<p>The Bulkgate Integration brand, application code, and all related
materials are the exclusive intellectual property of Mindful Momentum Ltd.
You are granted a limited, non-exclusive, non-transferable licence to use
the Service for your own business purposes during the active installation
period.</p>
"""

_TERMS_BODY_4 = """
<h2>9. Cancellation</h2>
<p>You may uninstall the Service at any time from your GHL sub-account. Upon
uninstall, encrypted credentials and access tokens are deleted within 90
days as described in the Privacy Policy. Cancelling the Service has no
effect on your separate Bulkgate account or its balance.</p>

<h2>10. Limitation of Liability</h2>
<p>To the fullest extent permitted by law, the Provider is not liable for
temporary unavailability of the Service (including GoHighLevel or Bulkgate
outages), for the accuracy or delivery of messages sent via Bulkgate, or for
any consequential, indirect, or incidental loss arising from use of the
Service. The Provider's total aggregate liability shall not exceed the fees
paid to the Provider (excluding Bulkgate SMS costs) in the 12 months
preceding the claim. Nothing in these Terms excludes liability for fraud,
death or personal injury caused by negligence, or any liability that cannot
be excluded by law.</p>

<h2>11. Force Majeure</h2>
<p>The Provider is not liable for delays or failures caused by events
outside its reasonable control, including outages of GoHighLevel, Bulkgate,
Railway, or general internet infrastructure failures.</p>

<h2>12. Data Protection</h2>
<p>Personal data processing is governed by the <a href="/privacy">Privacy
Policy</a>, which forms an integral part of these Terms.</p>
"""

_TERMS_BODY_5 = """
<h2>13. Changes to These Terms</h2>
<p>We may update these Terms at any time. For material changes, we will
notify Subscribers via a notice on this page at least 15 days before the new
Terms take effect.</p>

<h2>14. Governing Law and Jurisdiction</h2>
<p>These Terms are governed by the laws of England and Wales. Any disputes
shall be subject to the exclusive jurisdiction of the courts of England and
Wales, except where mandatory consumer-protection laws in your country of
residence provide otherwise. EU online dispute resolution:
ec.europa.eu/consumers/odr</p>

<h2>15. Severability</h2>
<p>If any provision of these Terms is found to be invalid or unenforceable,
the remaining provisions continue in full force and effect.</p>

<h2>16. Contact</h2>
<p><strong>Mindful Momentum Ltd</strong><br>
Email: ghladmins@gmail.com<br>
Address: Hova House, 1 Hova Villas, Brighton &amp; Hove, BN3 3DH, United Kingdom</p>
<footer>© 2026 Bulkgate Integration / Mindful Momentum Ltd. All rights reserved.</footer>
</body></html>
"""

TERMS_HTML = TERMS_HTML.replace(
    "</body></html>",
    _TERMS_BODY_2 + _TERMS_BODY_3 + _TERMS_BODY_4 + _TERMS_BODY_5,
)


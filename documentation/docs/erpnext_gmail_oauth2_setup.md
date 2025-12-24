# Gmail API Transport Layer with OAuth2 - Technical Documentation

**Project:** Leofresh ERPNext  
**Component:** Email Queue Override  
**Implementation Date:** November 2025  
**Author:** Peter Kamau  
**Tags:** #gmail-api #oauth2 #connected-app #email-transport #erpnext

---

## Executive Summary

This document covers the complete implementation of Gmail API as an email transport layer for ERPNext, replacing traditional SMTP with OAuth2-authenticated Gmail API. The implementation uses ERPNext's Connected App system for automatic token management, eliminating the need for manual service account credentials and providing production-ready automatic token refresh.

**Key Achievement:** Migration from file-based service account credentials to ERPNext's Connected App OAuth2 system with automatic token lifecycle management.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Connected App Setup](#connected-app-setup)
4. [Implementation Details](#implementation-details)
5. [Token Management](#token-management)
6. [Email Flow](#email-flow)
7. [Troubleshooting](#troubleshooting)
8. [Production Deployment](#production-deployment)
9. [Code Reference](#code-reference)

---

## Architecture Overview

### Before (Service Account)

```
Email Queue → Service Account JSON File → Manual Token Refresh → Gmail API
```

**Limitations:**

- Manual credential file management
- No automatic token refresh
- Security concerns with credential files
- Complex deployment process

### After (Connected App OAuth2)

```
Email Queue → Email Account → Connected App → Token Cache → Gmail API
                                    ↓
                            Auto Token Refresh
```

**Benefits:**

- ✅ Automatic token refresh handled by Frappe
- ✅ Secure encrypted token storage in Token Cache
- ✅ Built-in OAuth consent flow
- ✅ No manual credential file management
- ✅ Production-ready high-traffic support
- ✅ Centralized OAuth management

---

## Prerequisites

### 1. Google Cloud Console Setup

1. **Create OAuth2 Credentials:**

   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create/select project
   - Enable Gmail API
   - Create OAuth 2.0 Client ID (Web Application)
   - Add authorized redirect URIs: `https://your-domain.com/api/method/frappe.integrations.oauth2.authorize_access`

2. **Configure OAuth Consent Screen:**
   - User type: Internal (for organization) or External
   - Scopes: `https://www.googleapis.com/auth/gmail.send`
   - Test users (if External): Add authorized email addresses

### 2. Python Dependencies

```bash
# Install required packages
bench pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### 3. ERPNext Configuration

- ERPNext version: 13.0 or higher
- Frappe Framework with Connected App support
- Email Account DocType access

---

## Connected App Setup

### Step 1: Create Connected App

Navigate to **Setup → Integrations → Connected App** and create new:

```
Connected App Name: Gmail Email Sending
Provider Name: Google
Authorization URI: https://accounts.google.com/o/oauth2/v2/auth
Token URI: https://oauth2.googleapis.com/token
Revoke Token URI: https://oauth2.googleapis.com/revoke
Client ID: [Your Google OAuth Client ID]
Client Secret: [Your Google OAuth Client Secret]
```

### Step 2: Configure Scopes

Add the following scope:

```
Scope: https://www.googleapis.com/auth/gmail.send
```

### Step 3: Critical Query Parameters ⚠️

Add these query parameters (REQUIRED for token refresh):

| Parameter     | Value     | Purpose                                                  |
| ------------- | --------- | -------------------------------------------------------- |
| `access_type` | `offline` | Required to receive refresh_token                        |
| `prompt`      | `consent` | Forces consent screen to ensure refresh_token on re-auth |

**Why These Matter:**

- Without `access_type=offline`, Google will NOT return a refresh_token
- Without `prompt=consent`, re-authorization may not return a new refresh_token
- Missing refresh_token = token refresh failure after 1 hour

### Step 4: Create Email Account

Navigate to **Setup → Email → Email Account** and configure:

```
Email ID: leofreshapp@gmail.com
Enable Outgoing: ✓
Default Outgoing: ✓
Auth Method: OAuth
Connected App: Gmail Email Sending
Connected User: [Your ERPNext user email]
```

**Important:** Leave SMTP fields empty (server, port, password) - they're not used with OAuth.

### Step 5: Authorize OAuth

1. Save the Email Account
2. Click "Connect" button in Connected App field
3. Complete Google OAuth consent flow
4. Grant "Send email on your behalf" permission
5. Verify Token Cache is created

---

## Implementation Details

### File Structure

```
apps/leofresh/leofresh/
├── overrides/
│   ├── email_queue.py          # Gmail API transport layer (PRIMARY)
│   └── email_account.py        # SMTP validation bypass
├── hooks.py                     # DocType override registration
└── docs/
    └── erpnext_gmail_transport_layer_with_oauth.md
```

### Core Components

#### 1. Email Queue Override (`email_queue.py`)

**Class:** `APIEmailQueue(EmailQueue)`

**Key Methods:**

- `get_email_provider()` - Detects gmail_connected_app or gmail_legacy
- `get_email_account_with_connected_app()` - Finds Email Account with OAuth
- `validate()` - Skips SMTP validation for API providers
- `after_insert()` - Auto-triggers background/immediate send
- `send()` - Main override with duplicate prevention
- `get_gmail_service()` - **CRITICAL** - Token management and Gmail API initialization
- `send_via_gmail_api()` - Gmail API send with error handling
- `get_final_mime_message()` - MIME rebuilding with attachments

#### 2. Email Account Override (`email_account.py`)

**Class:** `APIEmailAccount(EmailAccount)`

**Purpose:** Bypass SMTP validation when using OAuth

```python
def validate_smtp_conn(self):
    if self._should_skip_smtp_validation():
        frappe.logger().debug(f"Skipping SMTP validation for OAuth: {self.name}")
        return
    return super(APIEmailAccount, self).validate_smtp_conn()
```

#### 3. Hooks Registration (`hooks.py`)

```python
override_doctype_class = {
    "Email Queue": "leofresh.overrides.email_queue.APIEmailQueue",
    "Email Account": "leofresh.overrides.email_account.APIEmailAccount"
}

boot_session = [
    "leofresh.hooks.override_email_queue_class",
    "leofresh.hooks.override_email_account_class"
]
```

---

## Token Management

### Token Lifecycle

```
Initial Authorization → Access Token (1 hour) + Refresh Token (permanent)
                             ↓
                    Token expires after 1 hour
                             ↓
                    get_active_token() checks expiry
                             ↓
                    Auto-refresh using refresh_token
                             ↓
                    Update Token Cache with new access_token
```

### Token Cache Structure

**DocType:** Token Cache

| Field           | Description                         |
| --------------- | ----------------------------------- |
| `connected_app` | Reference to Connected App          |
| `user`          | ERPNext user email                  |
| `access_token`  | Current access token (encrypted)    |
| `refresh_token` | Permanent refresh token (encrypted) |
| `expires_in`    | Token validity in seconds (3600)    |
| `success`       | Authorization success flag          |

### Automatic Token Refresh

The `get_gmail_service()` method handles token refresh automatically:

```python
def get_gmail_service(self) -> Any:
    """Initialize Gmail API service with automatic token refresh"""
    email_account = self.get_email_account_with_connected_app()
    connected_app = frappe.get_doc("Connected App", email_account.connected_app)

    # Auto-refreshes if expired
    token_cache = connected_app.get_active_token(email_account.connected_user)

    if token_cache.is_expired():
        frappe.logger().info("Token expired, refreshing...")
        token_cache = connected_app.get_active_token(email_account.connected_user)

    token_data = token_cache.get_json()
    credentials = Credentials(
        token=token_data.get('access_token'),
        refresh_token=token_data.get('refresh_token'),
        token_uri=connected_app.token_uri,
        client_id=connected_app.client_id,
        client_secret=connected_app.get_password("client_secret"),
        scopes=['https://www.googleapis.com/auth/gmail.send']
    )

    return build('gmail', 'v1', credentials=credentials)
```

### Token Updater Callback

When Google SDK refreshes tokens internally, the callback updates Token Cache:

```python
def token_updater(token_data):
    """Callback when Google SDK auto-refreshes token"""
    frappe.logger().info("🔄 Token auto-refreshed by Google SDK")
    token_cache.update_data(token_data)
    frappe.logger().info("✓ Token Cache updated")
```

---

## Email Flow

### Complete Send Process

```
1. Email Queue Created (via frappe.sendmail)
        ↓
2. after_insert() hook triggered
        ↓
3. get_email_provider() detects gmail_connected_app
        ↓
4. Status set to "Sending" (prevents duplicates)
        ↓
5. Background job enqueued: send_email_via_gmail()
        ↓
6. get_gmail_service() called
        ↓
7. Connected App → Token Cache → Credentials
        ↓
8. Token validity checked (auto-refresh if expired)
        ↓
9. Gmail API service initialized
        ↓
10. get_final_mime_message() builds clean MIME
        ↓
11. Attachments processed (print formats, files)
        ↓
12. Gmail API send (users().messages().send())
        ↓
13. Update recipient status (Sent/Error)
        ↓
14. Aggregate Email Queue status
```

### Duplicate Prevention

Two-layer protection:

1. **Status Check:** Skip if already "Sent" or "Sending"
2. **Atomic Update:** Set status="Sending" immediately in `after_insert()`

```python
def after_insert(self):
    if provider and not self.send_after and self.status == "Not Sent":
        # Immediately set to Sending to prevent duplicate jobs
        self.db_set("status", "Sending", commit=True)

        # Enqueue background job
        frappe.enqueue(
            method='leofresh.overrides.email_queue.send_email_via_gmail',
            queue='short',
            email_queue_name=self.name
        )
```

---

## Troubleshooting

### Issue 1: Missing refresh_token Error

**Error Message:**

```
oauthlib.oauth2.rfc6749.errors.InvalidClientIdError:
Missing required parameter: refresh_token
```

**Root Cause:** Token Cache lacks refresh_token because Connected App missing `access_type=offline`

**Solution:**

1. **Verify Connected App Query Parameters:**

   ```
   Go to Connected App → Query Parameters table
   Ensure: access_type = offline
   Ensure: prompt = consent
   ```

2. **Revoke Existing Authorization:**

   - Visit https://myaccount.google.com/permissions
   - Find "Gmail Email Sending" app
   - Click "Remove Access"

3. **Re-authorize:**

   - Open Email Account in ERPNext
   - Click "Connect" in Connected App field
   - Complete OAuth consent flow
   - Grant permissions

4. **Verify Token Cache:**

   ```python
   # In bench console
   frappe.init(site='your-site')
   frappe.connect()

   token_cache = frappe.get_doc("Token Cache", "Gmail Email Sending-user@example.com")
   print("Has refresh_token:", bool(token_cache.get_password("refresh_token")))
   print("Expires in:", token_cache.get_expires_in())
   ```

### Issue 2: Token Refresh Still Failing

**Diagnostic Steps:**

```python
# Check Connected App configuration
app = frappe.get_doc("Connected App", "Gmail Email Sending")
print("Token URI:", app.token_uri)
print("Client ID:", app.client_id)
print("Query Params:", [(p.key, p.value) for p in app.query_parameters])

# Check Token Cache contents
tc = frappe.get_doc("Token Cache", "Gmail Email Sending-user@example.com")
print("Success:", tc.success)
print("Expires in:", tc.get_expires_in())
print("Has access_token:", bool(tc.get_password("access_token")))
print("Has refresh_token:", bool(tc.get_password("refresh_token")))
```

### Issue 3: Duplicate Emails Sent

**Cause:** Race condition between scheduler and background jobs

**Solution:** Already implemented via status checks + atomic updates

**Verify:**

```sql
-- Check Email Queue status transitions
SELECT name, status, creation, modified
FROM `tabEmail Queue`
WHERE name = 'EMAIL-QUEUE-XXXX'
ORDER BY modified DESC;
```

### Issue 4: Attachments Not Appearing

**Diagnostic:**

1. Check logs for attachment processing:

   ```bash
   tail -f logs/frappe.log | grep -i "attachment"
   ```

2. Verify print format configuration:

   ```python
   # Print format test
   frappe.attach_print(
       doctype='Sales Invoice',
       name='SINV-00001',
       print_format='Standard'
   )
   ```

3. Check file paths:
   ```python
   # File path resolution test
   file_url = '/private/files/document.pdf'
   path = frappe.get_site_path('private', 'files', 'document.pdf')
   print("Exists:", os.path.exists(path))
   ```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Google Cloud Console OAuth credentials created
- [ ] Gmail API enabled in Google Cloud project
- [ ] Authorized redirect URIs configured
- [ ] Python dependencies installed (`google-auth`, etc.)
- [ ] Connected App created with correct query parameters
- [ ] Email Account created and linked to Connected App
- [ ] OAuth authorization completed successfully
- [ ] Token Cache contains refresh_token
- [ ] Test email sent successfully
- [ ] Logs verified for successful send

### Deployment Steps

1. **Install Dependencies:**

   ```bash
   cd /path/to/frappe-bench
   bench pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
   ```

2. **Migrate Custom App:**

   ```bash
   bench --site your-site migrate
   bench --site your-site clear-cache
   bench restart
   ```

3. **Create Connected App** (via ERPNext UI)

4. **Authorize OAuth** (via Email Account)

5. **Test Send:**

   ```python
   frappe.sendmail(
       recipients=['test@example.com'],
       sender='leofreshapp@gmail.com',
       subject='Production Test',
       message='<p>Testing Gmail API OAuth2</p>',
       now=True
   )
   ```

6. **Monitor Logs:**
   ```bash
   tail -f logs/frappe.log | grep -E "Gmail|OAuth|Token"
   ```

### Post-Deployment Monitoring

**Log Messages to Watch:**

✅ Success indicators:

```
🔐 Using Connected App: Gmail Email Sending
✓ Token valid, expires in 3599 seconds
✅ Gmail API service initialized with Connected App
✓ Sent via Gmail API - Message ID: 18c1234567890abcd
```

⚠️ Warning indicators:

```
Token expired, refreshing...
🔄 Token auto-refreshed by Google SDK
```

❌ Error indicators:

```
Missing required parameter: refresh_token
OAuth token not found
Failed to refresh OAuth token
```

### Optional: Token Health Monitor

Create a scheduled job to monitor token health:

```python
# In hooks.py
scheduler_events = {
    "hourly": [
        "leofresh.tasks.check_token_health"
    ]
}

# In tasks.py
def check_token_health():
    """Monitor OAuth token expiry and alert if needed"""
    from datetime import timedelta

    # Get all Token Caches for Gmail
    token_caches = frappe.get_all(
        "Token Cache",
        filters={"connected_app": "Gmail Email Sending"},
        fields=["name", "user", "modified"]
    )

    for tc_name in token_caches:
        tc = frappe.get_doc("Token Cache", tc_name.name)

        if not tc.get_password("refresh_token"):
            frappe.log_error(
                title=f"Missing Refresh Token: {tc_name.user}",
                message="Token Cache lacks refresh_token. Re-authorization required."
            )

        expires_in = tc.get_expires_in()
        if expires_in and expires_in < 300:  # Less than 5 minutes
            frappe.logger().warning(f"Token expiring soon for {tc_name.user}: {expires_in}s")
```

---

## Code Reference

### Complete get_gmail_service() Implementation

```python
def get_gmail_service(self) -> Any:
    """
    Initialize Gmail API service using Connected App OAuth tokens

    This method uses ERPNext's Connected App system for automatic
    token management and refresh. It replaces the legacy file-based
    service account approach.

    Returns:
        Gmail API service object

    Raises:
        frappe.ValidationError: If OAuth token not found or expired
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        # Get Email Account with Connected App
        email_account = self.get_email_account_with_connected_app()

        if email_account:
            frappe.logger().info(f"🔐 Using Connected App: {email_account.connected_app}")

            # Get Connected App document
            connected_app = frappe.get_doc("Connected App", email_account.connected_app)

            # Get active token (auto-refreshes if expired)
            token_cache = connected_app.get_active_token(
                email_account.connected_user or frappe.session.user
            )

            if not token_cache:
                frappe.throw(_(
                    "OAuth token not found for Email Account '{0}'. "
                    "Please authorize the Connected App '{1}' first."
                ).format(email_account.name, connected_app.name))

            # Check if token is expired and refresh if needed
            if token_cache.is_expired():
                frappe.logger().info("Token expired, refreshing...")
                token_cache = connected_app.get_active_token(email_account.connected_user)

                if not token_cache or token_cache.is_expired():
                    frappe.throw(_(
                        "Failed to refresh OAuth token for Email Account '{0}'. "
                        "Please re-authorize the Connected App."
                    ).format(email_account.name))

            # Get token data
            token_data = token_cache.get_json()
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')

            if not access_token:
                frappe.throw(_("Access token not found in Token Cache"))

            frappe.logger().info(
                f"✓ Token valid, expires in {token_data.get('expires_in')} seconds"
            )

            # Build credentials for Gmail API
            SCOPES = ['https://www.googleapis.com/auth/gmail.send']

            credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri=connected_app.token_uri,
                client_id=connected_app.client_id,
                client_secret=connected_app.get_password("client_secret"),
                scopes=SCOPES
            )

            # Token updater callback
            def token_updater(token_data):
                """Callback to update Token Cache when token is refreshed"""
                try:
                    frappe.logger().info("🔄 Token auto-refreshed by Google SDK")
                    token_cache.update_data(token_data)
                    frappe.logger().info("✓ Token Cache updated successfully")
                except Exception as e:
                    frappe.logger().error(f"Failed to update Token Cache: {str(e)}")
                    frappe.log_error(
                        title="Token Cache Update Failed",
                        message=f"Error: {str(e)}\n{frappe.get_traceback()}"
                    )

            # Check if token needs immediate refresh
            if not credentials.valid:
                if credentials.expired and credentials.refresh_token:
                    frappe.logger().info("Token invalid, refreshing via Google SDK...")
                    credentials.refresh(Request())

                    # Update Token Cache with new token
                    token_updater({
                        'access_token': credentials.token,
                        'refresh_token': credentials.refresh_token,
                        'expires_in': 3600,
                        'token_type': 'Bearer'
                    })

            # Build Gmail service
            service = build('gmail', 'v1', credentials=credentials)
            frappe.logger().info("✅ Gmail API service initialized with Connected App")
            return service

        # Fallback to legacy method if no Connected App found
        frappe.throw(_(
            "Gmail API not configured. Please setup an Email Account "
            "with Connected App for OAuth2 authentication."
        ))

    except Exception as e:
        frappe.log_error(
            title="Gmail API Initialization Error",
            message=f"Error: {str(e)}\n\nTraceback: {frappe.get_traceback()}"
        )
        raise
```

### Email Send Example

```python
# Simple email
frappe.sendmail(
    recipients=['customer@example.com'],
    sender='leofreshapp@gmail.com',
    subject='Order Confirmation',
    message='<h1>Thank you for your order!</h1>',
    now=True  # Send immediately
)

# With attachment
frappe.sendmail(
    recipients=['customer@example.com'],
    sender='leofreshapp@gmail.com',
    subject='Invoice SINV-00001',
    message='<p>Please find your invoice attached.</p>',
    attachments=[{
        'fname': 'Invoice-SINV-00001.pdf',
        'fcontent': pdf_content
    }],
    now=True
)

# With print format
frappe.sendmail(
    recipients=['customer@example.com'],
    sender='leofreshapp@gmail.com',
    subject='Delivery Note DN-00001',
    message='<p>Your order has been shipped.</p>',
    print_format='Standard',
    doc=frappe.get_doc('Delivery Note', 'DN-00001'),
    now=True
)
```

---

## Key Takeaways

1. **Connected App is Production-Ready:** ERPNext's Connected App system provides enterprise-grade OAuth token management with automatic refresh.

2. **Query Parameters are Critical:** Always set `access_type=offline` and `prompt=consent` in Connected App to ensure refresh_token is returned.

3. **Token Lifecycle is Automatic:** Once properly configured, tokens refresh automatically without manual intervention.

4. **Security Best Practices:** Tokens are encrypted in Token Cache, credentials never stored in code or config files.

5. **Migration Path:** Legacy service account implementations can coexist with Connected App during migration period.

6. **Monitoring is Essential:** Log messages provide clear indicators of OAuth health and token refresh success.

7. **Re-authorization May Be Needed:** If refresh_token is missing, revoke and re-authorize through Google account settings.

---

## Additional Resources

- [ERPNext Connected App Documentation](https://frappeframework.com/docs/user/en/guides/integration/oauth2)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Gmail API Reference](https://developers.google.com/gmail/api/reference/rest)
- [Frappe Email Queue Source](https://github.com/frappe/frappe/blob/develop/frappe/email/doctype/email_queue/email_queue.py)

---

**Document Version:** 1.0  
**Last Updated:** November 26, 2025  
**Maintained By:** Leofresh Development Team

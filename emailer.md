# Complete Gmail API Email Integration for ERPNext

## What You Get

✅ **Gmail API** replaces SMTP for all email sending
✅ **ERPNext email interface** remains completely unchanged
✅ **Proper domain URLs** in all emails (signup, reset, attachments)
✅ **Attachment support** works automatically
✅ **Email Queue** tracking and retry logic intact
✅ **Easy configuration** via site_config.json

---

## Installation Steps (Complete)

### 1. Install Google API Libraries

```bash
cd /home/frappe/frappe-bench
bench pip install google-auth google-auth-oauthlib google-api-python-client
```

### 2. Create Custom App

```bash
bench new-app custom_app
# Follow prompts with your details
```

### 3. Create File Structure

```bash
cd apps/custom_app/custom_app
mkdir -p overrides templates/emails www
touch overrides/__init__.py
```

Your structure should be:
```
apps/custom_app/custom_app/
├── __init__.py
├── hooks.py
├── overrides/
│   ├── __init__.py
│   ├── email_queue.py
│   └── user_signup.py
├── templates/
│   └── emails/
│       └── signup_email.html
└── www/
    ├── verify-email.py
    └── verify-email.html
```

### 4. Add Files

Copy these files from the artifacts above:

1. **overrides/email_queue.py** - Gmail API Override for ERPNext Email Queue
2. **__init__.py** - App Initialization
3. **hooks.py** - Simple Gmail API Integration
4. **overrides/__init__.py** - Empty file (makes it a package)

### 5. Configure ERPNext Domain

**Option A: Via UI (Recommended)**
1. Go to System Settings
2. Set "Site URL" to: `https://yourdomain.com`
3. Save

**Option B: Via site_config.json**

```bash
nano /home/frappe/frappe-bench/sites/your-site/site_config.json
```

Add:
```json
{
  "db_name": "your_db",
  "db_password": "your_password",

  "use_gmail_api": true,
  "gmail_credentials_path": "/home/frappe/frappe-bench/sites/your-site/private/service-account.json",
  "gmail_delegated_email": "noreply@yourdomain.com",

  "host_name": "https://yourdomain.com",
  "site_url": "https://yourdomain.com"
}
```

### 6. Add Google Credentials

```bash
# Place your service account JSON
sudo cp service-account.json /home/frappe/frappe-bench/sites/your-site/private/

# Set permissions
sudo chown frappe:frappe /home/frappe/frappe-bench/sites/your-site/private/service-account.json
sudo chmod 600 /home/frappe/frappe-bench/sites/your-site/private/service-account.json
```

### 7. Install App

```bash
cd /home/frappe/frappe-bench
bench --site your-site install-app custom_app
bench restart
bench --site your-site clear-cache
```

---

## Configuration Summary

### Required in site_config.json:

```json
{
  "use_gmail_api": true,
  "gmail_credentials_path": "/full/path/to/service-account.json",
  "gmail_delegated_email": "sender@yourdomain.com",
  "host_name": "https://yourdomain.com",
  "site_url": "https://yourdomain.com"
}
```

### Required in System Settings (via UI):

- **Site URL**: `https://yourdomain.com`

---

## What Gets Fixed Automatically

### 1. Email Sending
- ✅ All emails sent via Gmail API
- ✅ SMTP not used (but Email Accounts can stay for documentation)
- ✅ Email Queue works normally
- ✅ Retry logic preserved

### 2. URLs in Emails
- ✅ Image URLs become: `https://yourdomain.com/files/image.png`
- ✅ Link URLs become: `https://yourdomain.com/app/Sales%20Order/SO-00001`
- ✅ Attachment URLs work correctly
- ✅ Button links use proper domain

### 3. User Signup/Reset Emails
- ✅ Verification links use proper domain
- ✅ Password reset links work correctly
- ✅ Welcome emails have correct login URL
- ✅ All embedded images/logos display properly

---

## Testing Your Setup

### Test 1: Basic Email Send

```bash
bench --site your-site console
```

```python
import frappe

# Send test email
frappe.sendmail(
    recipients=['test@example.com'],
    subject='Test Gmail API Integration',
    message='<p>This email was sent via Gmail API!</p><p>All URLs should be correct.</p>',
    delayed=False
)

# Check if sent
frappe.db.sql("""
    SELECT name, status, message_id, error
    FROM `tabEmail Queue`
    ORDER BY creation DESC
    LIMIT 1
""", as_dict=1)
```

### Test 2: Email with Attachment

1. Go to any document (e.g., Sales Order)
2. Click **Menu** > **Email**
3. Add recipient
4. Click **Attach Document Print**
5. Send

**Expected:**
- Email sends via Gmail API
- PDF attachment is included
- All links in email work

### Test 3: Check URLs in Email

Send an email and check the HTML source - all URLs should be absolute:

```html
<!-- GOOD: Absolute URLs -->
<img src="https://yourdomain.com/files/logo.png">
<a href="https://yourdomain.com/app/Item/ITEM-001">View Item</a>

<!-- BAD: Relative URLs (if you see these, URLs aren't fixed) -->
<img src="/files/logo.png">
<a href="/app/Item/ITEM-001">View Item</a>
```

### Test 4: User Signup Flow

If you implemented the custom signup:

```bash
# Test signup
curl -X POST https://yourdomain.com/api/method/custom_app.custom_app.overrides.user_signup.custom_signup \
  -H "Content-Type: application/json" \
  -d '{"email":"newuser@example.com","full_name":"New User"}'
```

**Expected:**
- User receives email
- Verification link uses: `https://yourdomain.com/verify-email?key=...`
- Clicking link verifies account
- Welcome email has login link: `https://yourdomain.com/login`

---

## Common URL Issues & Fixes

### Issue 1: URLs Still Show localhost or Wrong Domain

**Check:**
```bash
bench --site your-site console
```
```python
from frappe.utils import get_url, get_site_url
print("Site URL:", get_url())
print("Config:", frappe.get_site_config().get('host_name'))
```

**Fix:**
1. Update System Settings > Site URL
2. Update site_config.json with correct host_name
3. Clear cache: `bench --site your-site clear-cache`
4. Restart: `bench restart`

### Issue 2: Attachment Links Don't Work

**Check file permissions:**
```bash
ls -la /home/frappe/frappe-bench/sites/your-site/public/files
ls -la /home/frappe/frappe-bench/sites/your-site/private/files
```

**Fix:**
```bash
cd /home/frappe/frappe-bench
sudo chown -R frappe:frappe sites/your-site/public/files
sudo chown -R frappe:frappe sites/your-site/private/files
sudo chmod -R 755 sites/your-site/public/files
```

### Issue 3: Images in Email Don't Display

**Causes:**
- Using relative URLs
- Files not publicly accessible
- CORS issues

**Fix:**
1. Ensure URL fixing is working (check `fix_email_content_urls` function)
2. Move images to public folder
3. Or use external CDN for email images

---

## Advanced: Custom Email Templates

### Create Custom Template with Proper URLs

**File:** `custom_app/custom_app/templates/emails/sales_order_confirmation.html`

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
        }
        .header {
            background: #007bff;
            color: white;
            padding: 20px;
            text-align: center;
        }
        .content { padding: 20px; }
        .button {
            display: inline-block;
            padding: 12px 24px;
            background: #28a745;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            margin: 20px 0;
        }
        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 12px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="header">
        <!-- Logo with proper URL -->
        {% if company_logo %}
        <img src="{{ frappe.utils.get_url() }}{{ company_logo }}"
             alt="Logo"
             style="max-height: 50px;">
        {% endif %}
        <h2>Order Confirmation</h2>
    </div>

    <div class="content">
        <p>Dear {{ customer_name }},</p>

        <p>Thank you for your order! We're processing it now.</p>

        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr style="background: #f8f9fa;">
                <th style="padding: 10px; text-align: left;">Order Number</th>
                <td style="padding: 10px;">{{ order_name }}</td>
            </tr>
            <tr>
                <th style="padding: 10px; text-align: left;">Order Date</th>
                <td style="padding: 10px;">{{ order_date }}</td>
            </tr>
            <tr style="background: #f8f9fa;">
                <th style="padding: 10px; text-align: left;">Total Amount</th>
                <td style="padding: 10px;">{{ currency }} {{ grand_total }}</td>
            </tr>
        </table>

        <!-- Button with proper URL -->
        <a href="{{ frappe.utils.get_url() }}/app/sales-order/{{ order_name }}"
           class="button">
            View Order Details
        </a>

        <p>You can track your order anytime by visiting:</p>
        <p><a href="{{ frappe.utils.get_url() }}/app/sales-order/{{ order_name }}">
            {{ frappe.utils.get_url() }}/app/sales-order/{{ order_name }}
        </a></p>
    </div>

    <div class="footer">
        <p>{{ frappe.defaults.get_defaults().company }}<br>
        {{ frappe.utils.get_url() }}</p>

        <p>Questions? Reply to this email or contact us at {{ support_email }}</p>
    </div>
</body>
</html>
```

### Use Custom Template in Code

```python
import frappe
from frappe.utils import get_url

def send_order_confirmation(order_name):
    """
    Send custom order confirmation email
    """
    order = frappe.get_doc('Sales Order', order_name)

    # Get company logo path
    company = frappe.get_doc('Company', order.company)
    company_logo = company.company_logo if hasattr(company, 'company_logo') else None

    # Render template with context
    message = frappe.render_template(
        'custom_app/templates/emails/sales_order_confirmation.html',
        {
            'customer_name': order.customer_name,
            'order_name': order.name,
            'order_date': order.transaction_date,
            'currency': order.currency,
            'grand_total': order.grand_total,
            'company_logo': company_logo,
            'support_email': frappe.get_site_config().get('support_email', 'support@example.com')
        }
    )

    # Send email
    frappe.sendmail(
        recipients=order.contact_email,
        subject=f'Order Confirmation - {order.name}',
        message=message,
        reference_doctype='Sales Order',
        reference_name=order.name,
        delayed=False
    )
```

---

## Monitoring & Troubleshooting

### Check Email Queue Status

```python
# In bench console
import frappe

# Get email statistics
stats = frappe.db.sql("""
    SELECT
        status,
        COUNT(*) as count,
        DATE(creation) as date
    FROM `tabEmail Queue`
    WHERE creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    GROUP BY status, DATE(creation)
    ORDER BY date DESC, status
""", as_dict=1)

for stat in stats:
    print(f"{stat.date} - {stat.status}: {stat.count}")
```

### Check Recent Failures

```python
# Get failed emails
failed = frappe.db.sql("""
    SELECT name, sender, subject, error, creation
    FROM `tabEmail Queue`
    WHERE status = 'Error'
    ORDER BY creation DESC
    LIMIT 10
""", as_dict=1)

for email in failed:
    print(f"\n{email.name}")
    print(f"Subject: {email.subject}")
    print(f"Error: {email.error}")
```

### View Gmail API Usage

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Go to "APIs & Services" > "Dashboard"
4. Click on "Gmail API"
5. View quota usage and request statistics

### Enable Detailed Logging

Add to site_config.json:
```json
{
  "developer_mode": 1,
  "logging": 2
}
```

Then check logs:
```bash
tail -f /home/frappe/frappe-bench/logs/bench.log
```

---

## Security Best Practices

### 1. Protect Credentials

```bash
# Correct permissions
chmod 600 /path/to/service-account.json
chown frappe:frappe /path/to/service-account.json

# Add to .gitignore
echo "*.json" >> .gitignore
echo "site_config.json" >> .gitignore
```

### 2. Use Environment Variables (Production)

Instead of hardcoding paths in site_config.json:

```python
# In email_queue.py, modify get_gmail_service():
import os

credentials_path = os.getenv('GMAIL_CREDENTIALS_PATH') or \
                   frappe.get_site_config().get('gmail_credentials_path')
```

Then set environment variable:
```bash
export GMAIL_CREDENTIALS_PATH="/secure/path/to/service-account.json"
```

### 3. Rotate Credentials Regularly

- Create new service account every 6-12 months
- Delete old service accounts after migration
- Update credentials_path in config

### 4. Monitor for Abuse

```python
# Check for unusual sending patterns
unusual = frappe.db.sql("""
    SELECT
        sender,
        COUNT(*) as count,
        DATE(creation) as date
    FROM `tabEmail Queue`
    WHERE creation >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
    GROUP BY sender, DATE(creation)
    HAVING count > 100
""", as_dict=1)

if unusual:
    # Alert admin
    print("Unusual email activity detected!")
```

---

## Performance Tips

### 1. Batch Email Processing

ERPNext processes emails in batches. To optimize:

```json
// In site_config.json
{
  "email_queue_batch_size": 50,
  "email_retry_limit": 3
}
```

### 2. Use Delayed Sending for Bulk

```python
# For bulk emails, use delayed=True
frappe.sendmail(
    recipients=recipient_list,
    subject='Newsletter',
    message=content,
    delayed=True  # Queues instead of sending immediately
)
```

### 3. Monitor Gmail API Quotas

Gmail API limits:
- **User rate limit**: 250 messages/second
- **Daily sending limit**: Depends on account type
  - Regular Gmail: 500/day
  - Google Workspace: 2000/day (or custom limit)

To avoid hitting limits:
```python
# Add rate limiting in site_config.json
{
  "mail_queue_delay": 0.2  # 200ms delay between emails
}
```

---

## Migration from SMTP

### Step-by-Step Migration

1. **Test in Dev/Staging First**
   ```bash
   # Clone production to staging
   bench --site staging.example.com restore /path/to/production/backup
   ```

2. **Enable Gmail API in Staging**
   - Update site_config.json
   - Test all email scenarios

3. **Monitor for Issues**
   - Check Email Queue for failures
   - Verify URLs in received emails
   - Test attachments

4. **Deploy to Production**
   ```bash
   # Update production site_config.json
   bench --site production.example.com clear-cache
   bench restart
   ```

5. **Keep SMTP Config as Backup**
   - Don't delete Email Account records
   - Can quickly revert if needed

### Rollback Plan

If issues occur:

```json
// Set in site_config.json
{
  "use_gmail_api": false
}
```

```bash
bench --site your-site clear-cache
bench restart
```

Emails will immediately go back to SMTP.

---

## FAQ

**Q: Can I use this with multiple sending domains?**
A: Yes, configure separate service accounts with domain-wide delegation for each domain, or use `gmail_delegated_email` to specify the sender.

**Q: What about email tracking (open rates, click rates)?**
A: Gmail API doesn't provide built-in tracking. You'd need to:
- Add tracking pixels to HTML emails
- Use URL shorteners with tracking
- Integrate third-party email tracking service

**Q: Can I still use Email Account doctype?**
A: Yes, Email Account records can remain for documentation/reference. They're just not used for sending when Gmail API is enabled.

**Q: Does this work with ERPNext's Newsletter feature?**
A: Yes! Newsletter uses the Email Queue system, so it automatically uses Gmail API.

**Q: What about email replies?**
A: This solution only handles *sending*. For receiving emails, you still need to configure Email Account with IMAP/POP3.

**Q: Can I send from multiple email addresses?**
A: Yes, if using domain-wide delegation. Set `gmail_delegated_email` dynamically or create multiple service accounts.

---

## Summary

You now have:

✅ Gmail API integrated with ERPNext
✅ All URLs fixed to use proper domain
✅ Email Queue working normally
✅ Attachments supported
✅ User signup/reset with correct links
✅ Easy configuration and rollback
✅ Production-ready security

Everything works through ERPNext's standard interface - users won't notice any difference except more reliable email delivery!

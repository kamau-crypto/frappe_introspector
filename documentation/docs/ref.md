# Gmail API for ERPNext - Quick Reference Card

## 🚀 One-Time Setup

```bash
# 1. Install libraries
bench pip install google-auth google-auth-oauthlib google-api-python-client

# 2. Create app
bench new-app custom_app

# 3. Create structure
cd apps/custom_app/custom_app
mkdir overrides && touch overrides/__init__.py

# 4. Add files (from artifacts)
# - overrides/email_queue.py
# - __init__.py
# - hooks.py

# 5. Install app
bench --site yoursite install-app custom_app
```

## ⚙️ Configuration Files

### site_config.json
```json
{
  "use_gmail_api": true,
  "gmail_credentials_path": "/path/to/service-account.json",
  "gmail_delegated_email": "noreply@yourdomain.com",
  "host_name": "https://yourdomain.com",
  "site_url": "https://yourdomain.com"
}
```

### System Settings (UI)
- **Site URL**: `https://yourdomain.com`

## 🔧 Essential Commands

```bash
# Restart after changes
bench restart

# Clear cache
bench --site yoursite clear-cache

# Check email queue
bench --site yoursite console
>>> frappe.db.sql("SELECT name, status, error FROM `tabEmail Queue` ORDER BY creation DESC LIMIT 10", as_dict=1)

# Send test email
>>> frappe.sendmail(recipients=['test@example.com'], subject='Test', message='Testing', delayed=False)

# Process queue manually
>>> from frappe.email.queue import flush
>>> flush()
```

## ✅ Verification Checklist

- [ ] Gmail API enabled in Google Cloud
- [ ] Service account JSON downloaded
- [ ] Credentials file has correct permissions (600)
- [ ] site_config.json updated
- [ ] System Settings > Site URL configured
- [ ] App installed and bench restarted
- [ ] Test email sent successfully
- [ ] URLs in email are absolute (https://yourdomain.com/...)
- [ ] Attachments work

## 🐛 Quick Troubleshooting

| Problem | Check | Fix |
|---------|-------|-----|
| Emails not sending | use_gmail_api in config | Set to `true` |
| Wrong URLs | Site URL in System Settings | Update to `https://yourdomain.com` |
| Permission denied | File permissions | `chmod 600 service-account.json` |
| Import error | Google libraries installed | `bench pip install google-*` |
| API not enabled | Google Cloud Console | Enable Gmail API |

## 📝 Quick Tests

```python
# Test 1: Check configuration
from frappe.utils import get_url
print(get_url())  # Should be: https://yourdomain.com

# Test 2: Check Gmail API loaded
from frappe.email.doctype.email_queue.email_queue import EmailQueue
print(EmailQueue.__name__)  # Should be: GmailAPIEmailQueue

# Test 3: Send test email
frappe.sendmail(
    recipients=['you@example.com'],
    subject='Gmail API Test',
    message='<h1>Success!</h1><p>Gmail API is working.</p>',
    delayed=False
)

# Test 4: Check last email
frappe.db.get_value('Email Queue',
    {'name': ['like', '%']},
    ['name', 'status', 'message_id'],
    order_by='creation desc')
```

## 🔐 Security Checklist

- [ ] Credentials file not in Git
- [ ] File permissions set to 600
- [ ] Domain-wide delegation configured (if needed)
- [ ] Environment variables used in production
- [ ] Credentials rotated every 6-12 months
- [ ] Gmail API quotas monitored

## 🎯 Key Files Location

```
frappe-bench/
├── apps/custom_app/custom_app/
│   ├── __init__.py
│   ├── hooks.py
│   └── overrides/
│       ├── __init__.py
│       └── email_queue.py
└── sites/yoursite/
    ├── site_config.json
    └── private/
        └── service-account.json
```

## 📊 Monitoring Commands

```python
# Email statistics (last 7 days)
frappe.db.sql("""
    SELECT status, COUNT(*)
    FROM `tabEmail Queue`
    WHERE creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)
    GROUP BY status
""")

# Recent failures
frappe.db.sql("""
    SELECT name, subject, error
    FROM `tabEmail Queue`
    WHERE status='Error'
    ORDER BY creation DESC
    LIMIT 5
""", as_dict=1)

# Today's sending volume
frappe.db.sql("""
    SELECT COUNT(*) as count
    FROM `tabEmail Queue`
    WHERE DATE(creation) = CURDATE()
""")[0][0]
```

## 🔄 Enable/Disable

### Disable Gmail API (revert to SMTP)
```json
{"use_gmail_api": false}
```
```bash
bench --site yoursite clear-cache && bench restart
```

### Re-enable Gmail API
```json
{"use_gmail_api": true}
```
```bash
bench --site yoursite clear-cache && bench restart
```

## 📞 Support

**Google Cloud Issues**: Check [Google Cloud Console](https://console.cloud.google.com/)
**ERPNext Email Queue**: Check Email Queue doctype in ERPNext
**Logs**: `tail -f logs/bench.log`
**Error Log**: Check Error Log doctype in ERPNext

---

## 💡 Remember

- URLs automatically fixed to absolute paths
- All ERPNext email features work unchanged
- Users don't see any difference
- Easy rollback with one config change
- Gmail API = better deliverability + security

**It just works!** 🎉

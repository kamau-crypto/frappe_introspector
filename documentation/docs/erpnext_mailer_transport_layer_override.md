# Gmail API Email Transport Layer for Frappe/ERPNext

## Overview

This document describes the improved override for Frappe's Email Queue to use the Gmail API (with OAuth2) for sending emails, bypassing traditional SMTP. This approach is designed to overcome SMTP restrictions, provide robust OAuth2 token handling, and fully support Frappe's advanced email features (templates, print formats, attachments, etc.).

---

## Key Features

- **Gmail API Integration**: Uses Google's official API and OAuth2 for secure, modern email delivery.
- **Immediate Sending**: Emails are sent as soon as they are queued, improving responsiveness.
- **Duplicate Prevention**: Status checks and atomic updates prevent race conditions and duplicate sends.
- **Full Frappe Compatibility**: Supports all Frappe features, including:
  - Email templates and HTML formatting
  - Print format PDF attachments
  - File attachments and inline images
  - Custom headers, footers, unsubscribe links, and tracking pixels
- **Background Job Handling**: Uses Frappe's background job system for reliable, non-blocking delivery.
- **Robust Error Handling**: Logs errors and updates status for transparency and debugging.
- **OAuth2 Token Refresh**: Handles token refresh automatically for uninterrupted service.

---

## Issues Addressed

- **SMTP Restrictions**: Bypasses SMTP, avoiding issues with blocked ports, rate limits, or legacy authentication.
- **Race Conditions**: Prevents duplicate emails by updating status to "Sending" before background job execution.
- **Attachment Handling**: Ensures print formats and file attachments are included and correctly encoded.
- **MIME Cleanliness**: Rebuilds MIME messages to remove SMTP artifacts, ensuring compatibility with Gmail API.
- **Immediate Feedback**: Emails are sent instantly after being queued, improving user experience.

---

## Core Functions and Their Roles

### 1. `send_email_via_gmail(email_queue_name)`
- **Purpose**: Background job to send a queued email via Gmail API.
- **Logic**:
  - Loads the `Email Queue` document.
  - Checks if the email is already sent or sending.
  - Calls the `send()` method with `force_send=True`.
  - Logs completion or errors.

---

### 2. `APIEmailQueue` (Class)
- **Purpose**: Overrides Frappe's `EmailQueue` to use Gmail API.
- **Key Methods**:
  - `get_email_provider()`: Detects if Gmail API is configured.
  - `validate()`: Skips SMTP validation if Gmail API is used.
  - `after_insert()`: Immediately enqueues the background job for sending if Gmail API is active.
  - `send()`: Main override; updates status, sends via Gmail API, and handles errors.
  - `update_status_after_send()`: Updates the queue status based on recipient delivery.
  - `get_gmail_service()`: Initializes the Gmail API client with OAuth2 credentials.
  - `send_via_gmail_api()`: Sends the email to a recipient using the Gmail API.
  - `get_final_mime_message()`: Rebuilds a clean MIME message for Gmail API, including all attachments and content.

---

## Sample Test Use Case

Below is a sample test function from `api.py` that demonstrates sending an email with a print format PDF attachment using the Gmail API transport:

```python
@frappe.whitelist(allow_guest=True)
def send_tester_mail():
    """
    Test email sending via Gmail API
    UPDATED: Proper subject and clear HTML content
    """
    try:
        # Send with clear subject and HTML
        frappe.sendmail(
            recipients=['kamaupeter343@gmail.com'],
            sender='leofreshapp@gmail.com',
            subject='Test Email With Invoice Attachment',  # ✅ Clear subject
            message="""
                <h2>Hello from Gmail API!</h2>
                <p>This email demonstrates:</p>
                <ul>
                    <li>HTML content rendering</li>
                    <li>Print format PDF attachment</li>
                    <li>Clean MIME structure</li>
                </ul>
                <p><strong>Please check the attachment!</strong></p>
            """,
            attachments=[{
                "print_format_attachment": 1,
                "doctype": "Sales Invoice",
                "name": "ACC-SINV-2025-00032",
                "print_format": "Sales Invoice Print",  # Or None for default
                "lang": "en",
                "print_letterhead": True
            }],
            now=True  # Send immediately
        )
        
        frappe.logger().info("✓ Email queued and sent via Gmail API")
        
        # Check email queue status
        emails = frappe.db.sql("""
            SELECT name, status, sender, error, message
            FROM `tabEmail Queue` 
            ORDER BY creation DESC 
            LIMIT 1
        """, as_dict=1)
        
        return {
            "success_key": 1,
            "message": "Email sent successfully",
            "emails": emails
        }
    except Exception as e:
        frappe.logger().error(f"Email send error: {str(e)}")
        return {
            "success_key": 0,
            "message": f"Failed: {str(e)}"
        }
```

---

## How to Test

1. **Configure Gmail API Credentials**  
   - Place your OAuth2 credentials (service account or OAuth client) in your site config or as a JSON file.
   - Set `use_gmail_api` and/or `gmail_credentials_path` in your `site_config.json`.

2. **Deploy the Override**  
   - Ensure the override class and background job function are present in `leofresh/overrides/email_queue.py`.
   - Register the override in your app's hooks.

3. **Send a Test Email**  
   - Call the `send_tester_mail` endpoint (e.g., via REST API or Frappe Desk).
   - Check the logs and the recipient's inbox for delivery.
   - Inspect the `Email Queue` doctype for status and error messages.

---

## Future Improvements

- **Batch Sending**: Optimize for bulk email campaigns with batching and rate limiting.
- **Advanced Error Handling**: Retry logic for transient Gmail API errors.
- **OAuth2 User Consent**: Support for delegated sending on behalf of users (not just service accounts).
- **Delivery Tracking**: Integrate Gmail API message IDs with Frappe's email tracking.
- **Admin Dashboard**: UI for monitoring Gmail API quota, errors, and delivery stats.
- **Multi-Provider Support**: Extend the override to support other APIs (SendGrid, Brevo, etc.) with similar logic.

---

## References

- [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python)
- [Frappe Email Queue Documentation](https://frappeframework.com/docs/v13/user/en/email)
- [OAuth2 for Google APIs](https://developers.google.com/identity/protocols/oauth2)

---

## Example: Minimal Site Config for Gmail API

```json
{
  "use_gmail_api": true,
  "gmail_credentials_path": "/path/to/service-account.json"
}
```

---

## Summary

This override provides a robust, modern, and extensible way to send emails from Frappe/ERPNext using the Gmail API. It is designed for reliability, full feature support, and ease of future extension.

Store this document alongside your codebase for reference and as a foundation for future improvements.

---

"""
Gmail API Transport Layer for Frappe Email Queue
"""

import base64
import email
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import frappe
from frappe import _
from frappe.email.doctype.email_queue.email_queue import EmailQueue


# ============ MODULE-LEVEL FUNCTION ============
def send_email_via_gmail(email_queue_name):
    """Background job to send email via Gmail API"""
    try:
        frappe.logger().info(f"📨 Background: {email_queue_name}")
        email_queue = frappe.get_doc("Email Queue", email_queue_name)

        if email_queue.status in ["Sent", "Sending"]:
            frappe.logger().info(f"Already {email_queue.status}, skipping")
            return

        email_queue.send(force_send=True)
        frappe.logger().info(f"✓ Complete: {email_queue_name}")
    except Exception as e:
        frappe.log_error(
            title=f"Gmail Background Send Failed",
            message=f"Queue: {email_queue_name}\nError: {str(e)}\n{frappe.get_traceback()}",
        )


# ============ CLASS ============
class APIEmailQueue(EmailQueue):
    """
    Gmail API Email Queue - Transport Layer Override

    Strategy: Let Frappe build the complete email (MIME, formatting, attachments)
    then intercept at send time and use Gmail API instead of SMTP.

    This preserves ALL Frappe features:
    - Email templates and styling
    - Print format PDFs
    - File attachments
    - Inline images
    - Headers and footers
    - Unsubscribe links
    - Email tracking
    """

    def get_email_provider(self) -> Optional[str]:
        """Check if Gmail API is configured"""
        config: Dict[str, Any] = frappe.get_site_config()

        if config.get("use_gmail_api") or config.get("gmail_credentials_path"):
            return "gmail"

        return None

    def validate(self) -> None:
        """Skip Email Account validation when using Gmail API"""
        provider = self.get_email_provider()

        if provider:
            if not self.sender:
                config = frappe.get_site_config()
                self.sender = (
                    config.get("gmail_delegated_email")
                    or config.get("default_sender_email")
                    or frappe.session.user
                    or "noreply@example.com"
                )

            if not self.recipients:
                frappe.throw(_("Recipients are required"))

            frappe.logger().debug(
                f"Using {provider.upper()} API - skipping SMTP validation"
            )
            return

        super(APIEmailQueue, self).validate()

    def after_insert(self):
        """
        Auto-trigger immediate send for Gmail API emails
        Runs after Email Queue document is created
        """
        provider = self.get_email_provider()

        if provider == "gmail":
            # Check if should send immediately (not scheduled for later)
            if not self.send_after and self.status == "Not Sent":
                frappe.logger().info(
                    f"🚀 Auto-triggering immediate Gmail API send: {self.name}"
                )

                # Option 1: Send synchronously (blocks until sent)
                if frappe.flags.in_test or frappe.conf.get("gmail_send_sync"):
                    try:
                        self.send(force_send=True)
                    except Exception as e:
                        frappe.logger().error(f"Immediate send failed: {str(e)}")

                # Option 2: Send asynchronously (recommended for production)
                else:
                    frappe.enqueue(
                        method="leofresh.overrides.email_queue.send_email_via_gmail",
                        queue="short",
                        timeout=300,
                        is_async=True,
                        now=False,
                        job_name=f"gmail_send_{self.name}",
                        at_front=True,  # Priority processing
                        email_queue_name=self.name,
                    )
        else:
            # Call parent's after_insert for SMTP
            if hasattr(super(APIEmailQueue, self), "after_insert"):
                super(APIEmailQueue, self).after_insert()

    def send(
        self, smtp_server_instance=None, frappe_mail_client=None, force_send=False
    ):
        """
        Override send() to bypass SMTP server initialization when using Gmail API
        """
        provider = self.get_email_provider()

        if provider == "gmail":
            # Use Gmail API - bypass SMTP completely
            if not self.can_send_now() and not force_send:
                frappe.logger().debug(
                    f"Email queue {self.name} cannot send now, skipping"
                )
                return

            frappe.logger().info(
                f"📧 Sending via Gmail API: {self.name} to {len(self.recipients)} recipient(s)"
            )

            # Update status to "Sending" to prevent duplicate sends
            self.update_status(status="Sending", commit=True)

            try:
                # Reload document to ensure all fields are loaded
                self.reload()

                sent_to_at_least_one = False

                # Send to each recipient
                for recipient in self.recipients:
                    if recipient.is_mail_sent():
                        frappe.logger().debug(
                            f"Skipping already sent: {recipient.recipient}"
                        )
                        continue

                    try:
                        success = self.send_via_gmail_api(recipient.recipient)

                        if success:
                            recipient.db_set("status", "Sent", commit=True)
                            sent_to_at_least_one = True
                            frappe.logger().info(f"✓ Sent to: {recipient.recipient}")
                        else:
                            recipient.db_set("status", "Error", commit=True)
                            frappe.logger().error(
                                f"✗ Failed to send to: {recipient.recipient}"
                            )

                    except Exception as e:
                        recipient.db_set("status", "Error", commit=True)
                        frappe.log_error(
                            title=f"Gmail API Send Error - {recipient.recipient}",
                            message=f"Error: {str(e)}\n\nTraceback: {frappe.get_traceback()}",
                        )

                # Update final queue status
                self.update_status_after_send()
                frappe.logger().info(f"✓ Email queue {self.name} processing complete")

            except Exception as e:
                # If any error occurs during the entire process
                status = "Partially Sent" if sent_to_at_least_one else "Error"
                self.update_status(status=status, error=str(e), commit=True)
                frappe.log_error(
                    title="Gmail API Send Error - Queue",
                    message=f"Queue: {self.name}\nError: {str(e)}\n\nTraceback: {frappe.get_traceback()}",
                )

            return

        # Use default SMTP
        return super(APIEmailQueue, self).send(
            smtp_server_instance, frappe_mail_client, force_send
        )

    def update_status_after_send(self):
        """Update Email Queue status based on recipient statuses"""
        # Reload to get latest recipient statuses
        self.reload()

        sent = sum(1 for r in self.recipients if r.status == "Sent")
        total = len(self.recipients)

        if sent == total:
            self.db_set("status", "Sent")
        elif sent > 0:
            self.db_set("status", "Partially Sent")
        else:
            self.db_set("status", "Error")

    # ==================== GMAIL API TRANSPORT ====================

    def get_gmail_service(self) -> Any:
        """Initialize Gmail API service with OAuth2"""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            config = frappe.get_site_config()
            credentials_path = config.get("gmail_credentials_path")
            credentials = None

            if credentials_path and os.path.exists(credentials_path):
                with open(credentials_path, "r") as f:
                    creds_data = json.load(f)

                if "private_key" in creds_data:
                    # Service Account
                    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
                    credentials = service_account.Credentials.from_service_account_file(
                        credentials_path, scopes=SCOPES
                    )

                    delegated_email = config.get("gmail_delegated_email")
                    if delegated_email:
                        credentials = credentials.with_subject(delegated_email)

                elif "client_id" in creds_data and "refresh_token" in creds_data:
                    # OAuth2 User Credentials
                    SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

                    credentials = Credentials(
                        token=creds_data.get("token"),
                        refresh_token=creds_data.get("refresh_token"),
                        token_uri=creds_data.get("token_uri"),
                        client_id=creds_data.get("client_id"),
                        client_secret=creds_data.get("client_secret"),
                        scopes=SCOPES,
                    )

                    if not credentials.valid:
                        if credentials.expired and credentials.refresh_token:
                            credentials.refresh(Request())

                            creds_data["token"] = credentials.token
                            if credentials.expiry:
                                creds_data["expiry"] = credentials.expiry.isoformat()

                            with open(credentials_path, "w") as f:
                                json.dump(creds_data, f, indent="\t")

            return build("gmail", "v1", credentials=credentials)

        except Exception as e:
            frappe.log_error(
                title="Gmail API Initialization Error",
                message=f"Error: {str(e)}\n\nTraceback: {frappe.get_traceback()}",
            )
            raise

    def send_via_gmail_api(
        self, recipient: str, formatted: Optional[str] = None
    ) -> bool:
        """Send via Gmail API using Frappe's pre-built MIME message"""
        try:
            from googleapiclient.errors import HttpError

            frappe.logger().info(f"=== Gmail API Send ===")
            frappe.logger().info(f"To: {recipient}")

            # Get Gmail API service
            service = self.get_gmail_service()

            # CRITICAL: Get Frappe's complete MIME message
            mime_message = self.get_final_mime_message(recipient, formatted)

            # Remove

            # Send via Gmail API
            sent_message = (
                service.users()
                .messages()
                .send(userId="me", body=mime_message)
                .execute()
            )

            message_id = sent_message.get("id")
            if message_id:
                self.message_id = message_id
                self.db_set("message_id", message_id)

            frappe.logger().info(f"✓ Sent via Gmail API - Message ID: {message_id}")
            return True

        except HttpError as error:  # type: ignore
            error_message = (
                f"Gmail API HTTP Error: {error.status_code} - {error.reason}"
            )
            frappe.log_error(
                title=f"Gmail API Send Error",
                message=f"{error_message}\n\nRecipient: {recipient}\n\nDetails: {str(error)}",
            )
            return False

        except Exception as e:
            frappe.log_error(
                title=f"Gmail API Error",
                message=f"Error: {str(e)}\n\nRecipient: {recipient}\n\nTraceback: {frappe.get_traceback()}",
            )
            return False

    def get_final_mime_message(
        self, recipient: str, formatted: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Parse Frappe's MIME message and rebuild clean email for Gmail API

        Extracts headers, HTML content (prioritized), plain text, and attachments
        from the raw MIME message and builds a clean message without SMTP artifacts.

        Args:
            recipient: Email recipient address
            formatted: Optional pre-formatted HTML content

        Returns:
            Dictionary with 'raw' key containing base64-encoded MIME message
        """
        try:
            # Initialize defaults
            sender = getattr(self, "sender", None) or frappe.session.user
            subject = getattr(self, "subject", None) or "(No Subject)"
            reply_to = getattr(self, "reply_to", None)
            html_content = None
            plain_content = None
            attachments = []

            # Parse MIME message if no pre-formatted content provided
            if not formatted:
                # Get the raw message from queue (contains full MIME structure)
                raw_message = getattr(self, "message", None) or ""

                if raw_message:
                    # Parse MIME message into email object
                    parsed_msg = email.message_from_string(raw_message)

                    # Extract headers from parsed message (these are the actual sent values)
                    subject = parsed_msg.get("Subject", subject)
                    sender = parsed_msg.get("From", sender)
                    reply_to = parsed_msg.get("Reply-To", reply_to)
                    date = parsed_msg.get("Date")

                    frappe.logger().debug(
                        f"Parsed MIME headers - Subject: {subject}, From: {sender}, Reply-To: {reply_to}"
                    )

                    # Walk through MIME parts to extract content and attachments
                    for part in parsed_msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition", ""))

                        # Skip multipart containers
                        if part.get_content_maintype() == "multipart":
                            continue

                        # Handle file attachments (has Content-Disposition: attachment)
                        if "attachment" in content_disposition:
                            filename = part.get_filename()
                            if filename:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    attachments.append(
                                        {"fname": filename, "fcontent": payload}
                                    )
                                    frappe.logger().debug(
                                        f"Found MIME attachment: {filename}"
                                    )
                            continue

                        # Extract HTML content (PRIORITY)
                        if content_type == "text/html":
                            payload = part.get_payload(decode=True)
                            if payload:
                                charset = part.get_content_charset() or "utf-8"
                                html = (
                                    payload.decode(charset, errors="replace")
                                    if isinstance(payload, bytes)
                                    else payload
                                )
                                # Prioritize: only override if this HTML is longer/better
                                if not html_content or len(html) > len(html_content):
                                    html_content = html

                        # Extract plain text (FALLBACK)
                        elif content_type == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                charset = part.get_content_charset() or "utf-8"
                                text = (
                                    payload.decode(charset, errors="replace")
                                    if isinstance(payload, bytes)
                                    else payload
                                )
                                # Only set if not already set
                                if not plain_content:
                                    plain_content = text

                    frappe.logger().debug(
                        f"Extracted - HTML: {bool(html_content)}, Plain: {bool(plain_content)}, MIME Attachments: {len(attachments)}"
                    )

            else:
                # Use pre-formatted content
                html_content = formatted

            # Process Frappe's attachments field - handles print formats and file attachments
            if hasattr(self, "attachments") and self.attachments:
                try:
                    attachments_list = (
                        json.loads(self.attachments)
                        if isinstance(self.attachments, str)
                        else self.attachments
                    )
                    existing_filenames = {att["fname"] for att in attachments}

                    for att in attachments_list:
                        # Handle print format attachments (PDFs generated from documents)
                        if att.get("print_format_attachment") == 1:
                            frappe.logger().debug(
                                f"Processing print format attachment: {att}"
                            )

                            # Remove the flag before passing to frappe.attach_print
                            att_copy = att.copy()
                            att_copy.pop("print_format_attachment", None)

                            # Use Frappe's internal function to generate print format PDF/HTML
                            try:
                                print_format_file = frappe.attach_print(**att_copy)

                                # Avoid duplicates
                                if print_format_file["fname"] not in existing_filenames:
                                    attachments.append(
                                        {
                                            "fname": print_format_file["fname"],
                                            "fcontent": print_format_file["fcontent"],
                                        }
                                    )
                                    existing_filenames.add(print_format_file["fname"])
                                    frappe.logger().info(
                                        f"Added print format attachment: {print_format_file['fname']}"
                                    )
                            except Exception as e:
                                frappe.logger().error(
                                    f"Failed to generate print format: {str(e)}"
                                )

                        # Handle regular file attachments
                        elif att.get("file_url") or att.get("fid"):
                            file_url = (
                                att.get("file_url")
                                if isinstance(att, dict)
                                else getattr(att, "file_url", None)
                            )
                            file_id = (
                                att.get("fid")
                                if isinstance(att, dict)
                                else getattr(att, "fid", None)
                            )

                            # Try to get file from File doctype if fid is provided
                            if file_id:
                                try:
                                    file_doc = frappe.get_doc("File", {"name": file_id})
                                    filename = file_doc.file_name
                                    fcontent = file_doc.get_content()

                                    if filename not in existing_filenames:
                                        attachments.append(
                                            {"fname": filename, "fcontent": fcontent}
                                        )
                                        existing_filenames.add(filename)
                                        frappe.logger().debug(
                                            f"Added file attachment (by fid): {filename}"
                                        )
                                    continue
                                except Exception as e:
                                    frappe.logger().warning(
                                        f"Could not load file by fid {file_id}: {str(e)}"
                                    )

                            # Try to resolve file path from URL
                            if file_url:
                                file_path = self._resolve_file_path(file_url)
                                if file_path and os.path.exists(file_path):
                                    filename = os.path.basename(file_path)
                                    # Avoid duplicates
                                    if filename not in existing_filenames:
                                        with open(file_path, "rb") as f:
                                            attachments.append(
                                                {
                                                    "fname": filename,
                                                    "fcontent": f.read(),
                                                }
                                            )
                                            existing_filenames.add(filename)
                                            frappe.logger().debug(
                                                f"Added file attachment (by path): {filename}"
                                            )
                except Exception as e:
                    frappe.logger().warning(
                        f"Could not load Frappe attachments: {str(e)}\n{frappe.get_traceback()}"
                    )

            # Determine final HTML content (prioritize HTML over plain text)
            final_html = None
            if html_content:
                final_html = html_content
            elif plain_content:
                # Wrap plain text in HTML for consistent rendering
                final_html = f"<html><body><pre style='font-family: sans-serif; white-space: pre-wrap;'>{plain_content}</pre></body></html>"
            elif formatted:
                # Ensure formatted content is HTML
                if not formatted.strip().startswith("<"):
                    final_html = f"<html><body>{formatted}</body></html>"
                else:
                    final_html = formatted
            else:
                # Fallback
                final_html = "<html><body><p>No content</p></body></html>"

            # Build clean MIME message for Gmail API
            mime_message = MIMEMultipart()

            # Set headers (clean, no SMTP artifacts)
            mime_message["To"] = recipient
            mime_message["Subject"] = subject
            mime_message["From"] = sender

            if reply_to:
                mime_message["Reply-To"] = reply_to

            # Attach HTML body
            msg_body = MIMEText(str(final_html), "html", "utf-8")
            mime_message.attach(msg_body)

            # Attach all files
            for att in attachments:
                try:
                    from email.mime.application import MIMEApplication

                    file_part = MIMEApplication(att["fcontent"], name=att["fname"])
                    file_part["Content-Disposition"] = (
                        f'attachment; filename="{att["fname"]}"'
                    )
                    mime_message.attach(file_part)
                except Exception as e:
                    frappe.logger().warning(
                        f"Could not attach file {att.get('fname')}: {str(e)}"
                    )

            # Encode for Gmail API
            raw_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()

            frappe.logger().info(
                f"MIME rebuilt - HTML: {bool(html_content)}, Attachments: {len(attachments)}, Size: {len(raw_message)} chars"
            )

            return {"raw": raw_message}

        except Exception as e:
            frappe.logger().error(
                f"Error building MIME: {str(e)}\n{frappe.get_traceback()}"
            )
            raise

    def _resolve_file_path(self, file_url: str) -> Optional[str]:
        """Resolve file URL to filesystem path"""
        try:
            if file_url.startswith("/private/files/"):
                return frappe.get_site_path(
                    "private", "files", file_url.replace("/private/files/", "")
                )
            elif file_url.startswith("/files/"):
                return frappe.get_site_path(
                    "public", "files", file_url.replace("/files/", "")
                )
            else:
                # Cases when the name of the file is provided along
                file_doc = frappe.get_doc("File", file_url)
                return file_doc.get("file_url").__getattribute__("file_path")
        except:
            return None

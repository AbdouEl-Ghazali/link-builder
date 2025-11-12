#!/usr/bin/env python3
"""
Automatic email sending script for link-building outreach.

Sends emails via SMTP for messages in outreach_messages_validated.json.
Uses environment variables for SMTP configuration.
"""

import json
import csv
import os
import smtplib
import socket
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Set

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Load .env file from project root
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data"
MESSAGES_FILE = DATA_DIR / "outreach_messages_validated.json"
LOG_FILE = DATA_DIR / "outreach_log.csv"

# SMTP Configuration (from environment variables)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER)
# SENDER_NAME defaults to BUSINESS_NAME if not set, otherwise uses SMTP_FROM_NAME
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "")
SENDER_NAME = os.getenv("SENDER_NAME") or os.getenv("SMTP_FROM_NAME") or BUSINESS_NAME or "Your Business"
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

# Domain validation timeout (seconds)
DOMAIN_CHECK_TIMEOUT = 5


def extract_domain_from_email(email: str) -> Optional[str]:
    """Extract domain from email address."""
    if not email or "@" not in email:
        return None
    return email.split("@")[1].lower().strip()


def validate_domain(domain: str) -> Tuple[bool, str]:
    """
    Validate that a domain exists and has MX records.
    
    Returns:
        (is_valid: bool, error_message: str)
    """
    if not domain:
        return False, "No domain provided"
    
    # Basic domain format validation
    domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    if not re.match(domain_pattern, domain):
        return False, f"Invalid domain format: {domain}"
    
    try:
        # Try to resolve the domain
        socket.gethostbyname(domain)
        
        # Try to get MX records (optional but more thorough)
        try:
            import dns.resolver
            mx_records = dns.resolver.resolve(domain, 'MX', lifetime=DOMAIN_CHECK_TIMEOUT)
            if not list(mx_records):
                return False, f"Domain {domain} has no MX records"
        except ImportError:
            # dnspython not installed, skip MX check
            pass
        except Exception:
            # MX check failed, but domain resolves, so continue
            pass
        
        return True, ""
    except socket.gaierror as e:
        return False, f"Domain {domain} not found (DNS resolution failed)"
    except Exception as e:
        return False, f"Domain validation error for {domain}: {str(e)}"


def get_already_contacted() -> Dict[Tuple[str, str], str]:
    """
    Read outreach_log.csv and return a dict of already contacted sites/contacts.
    
    Returns:
        Dict mapping (site, contact) tuple to status string
        Only includes entries with status "sent" or "opened"
    """
    already_contacted: Dict[Tuple[str, str], str] = {}
    
    if not LOG_FILE.exists():
        return already_contacted
    
    try:
        with open(LOG_FILE, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                site = row.get("site", "").strip()
                contact = row.get("contact", "").strip()
                status = row.get("status", "").strip().lower()
                
                # Check if this contact was already successfully sent or opened
                if status in ("sent", "opened") and site and contact:
                    # Use site+contact as key to track duplicates
                    key = (site.lower(), contact.lower())
                    already_contacted[key] = status
    except Exception as e:
        print(f"Warning: Could not read outreach log: {e}")
    
    return already_contacted


def log_submission(site: str, contact: str, status: str, notes: str):
    """Log a submission attempt to the CSV log file."""
    timestamp = datetime.now().isoformat()
    
    # Ensure log file exists with headers
    file_exists = LOG_FILE.exists()
    
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "site", "contact", "status", "notes"])
        writer.writerow([timestamp, site, contact, status, notes])


def send_email(
    to_email: str,
    subject: str,
    message: str,
    from_email: str = SMTP_FROM_EMAIL,
    from_name: str = SMTP_FROM_NAME,
    validate_domain_first: bool = True
) -> Tuple[bool, str]:
    """
    Send an email via SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        message: Email body
        from_email: Sender email address
        from_name: Sender name
        validate_domain_first: If True, validate domain before attempting to send
    
    Returns:
        (success: bool, error_message: str)
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        return False, "SMTP credentials not configured (SMTP_USER and SMTP_PASSWORD required)"
    
    if not to_email:
        return False, "No recipient email address provided"
    
    # Validate email format
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, to_email):
        return False, f"Invalid email address format: {to_email}"
    
    # Validate domain before sending
    if validate_domain_first:
        domain = extract_domain_from_email(to_email)
        if domain:
            is_valid, domain_error = validate_domain(domain)
            if not is_valid:
                return False, f"Domain validation failed: {domain_error}"
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        
        # Add message body
        msg.attach(MIMEText(message, "plain"))
        
        # Connect to SMTP server
        if SMTP_USE_TLS:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        
        # Login and send
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True, "Email sent successfully"
    
    except smtplib.SMTPAuthenticationError as e:
        return False, f"SMTP authentication failed: {str(e)}"
    except smtplib.SMTPRecipientsRefused as e:
        # Check if error indicates domain not found
        error_str = str(e).lower()
        if "couldn't be found" in error_str or "domain" in error_str and "not found" in error_str:
            domain = extract_domain_from_email(to_email)
            return False, f"Domain not found: {domain} (Address not found - domain couldn't be found)"
        return False, f"Recipient refused: {str(e)}"
    except smtplib.SMTPDataError as e:
        error_str = str(e).lower()
        if "couldn't be found" in error_str or "domain" in error_str:
            domain = extract_domain_from_email(to_email)
            return False, f"Domain not found: {domain} (Address not found - domain couldn't be found)"
        return False, f"SMTP data error: {str(e)}"
    except smtplib.SMTPException as e:
        error_str = str(e).lower()
        # Check for domain-related errors in the exception message
        if "couldn't be found" in error_str or ("domain" in error_str and "not found" in error_str):
            domain = extract_domain_from_email(to_email)
            return False, f"Domain not found: {domain} (Address not found - domain couldn't be found)"
        return False, f"SMTP error: {str(e)}"
    except Exception as e:
        error_str = str(e).lower()
        # Check for domain-related errors
        if "couldn't be found" in error_str or ("domain" in error_str and "not found" in error_str):
            domain = extract_domain_from_email(to_email)
            return False, f"Domain not found: {domain} (Address not found - domain couldn't be found)"
        return False, f"Error sending email: {str(e)}"


def process_messages():
    """Process all messages in outreach_messages_validated.json and send emails."""
    if not MESSAGES_FILE.exists():
        print(f"Error: {MESSAGES_FILE} not found")
        return
    
    with open(MESSAGES_FILE, "r") as f:
        messages = json.load(f)
    
    if not messages:
        print("No messages found in outreach_messages_validated.json")
        return
    
    print(f"Processing {len(messages)} messages...")
    
    # Load already contacted list to avoid duplicates
    already_contacted = get_already_contacted()
    if already_contacted:
        print(f"Found {len(already_contacted)} previously contacted sites/contacts - will skip duplicates")
    
    # Check SMTP configuration
    if not SMTP_USER or not SMTP_PASSWORD:
        print("\n⚠️  Warning: SMTP credentials not configured.")
        print("Set the following environment variables:")
        print("  - SMTP_HOST (default: smtp.gmail.com)")
        print("  - SMTP_PORT (default: 587)")
        print("  - SMTP_USER (your email)")
        print("  - SMTP_PASSWORD (your email password or app password)")
        print("  - SMTP_FROM_EMAIL (default: SMTP_USER)")
        print("  - SMTP_FROM_NAME or SENDER_NAME (default: BUSINESS_NAME or 'Your Business')")
        print("  - SMTP_USE_TLS (default: true)")
        print("\nSkipping email sending. Only contact forms will be processed.")
        return
    
    sent_count = 0
    failed_count = 0
    skipped_count = 0
    already_sent_count = 0
    
    for msg_data in messages:
        site = msg_data.get("site", "Unknown")
        to_email = msg_data.get("to")
        contact_form_url = msg_data.get("contact_form_url")
        subject = msg_data.get("subject", "")
        message = msg_data.get("message", "")
        
        # Check if already contacted (by email or contact form)
        if to_email:
            key = (site.lower(), to_email.lower())
            if key in already_contacted:
                status = already_contacted[key]
                print(f"Skipping {site} ({to_email}) - already {status}")
                already_sent_count += 1
                continue
        elif contact_form_url:
            # Check by contact form URL
            key = (site.lower(), contact_form_url.lower())
            if key in already_contacted:
                status = already_contacted[key]
                print(f"Skipping {site} ({contact_form_url}) - already {status}")
                already_sent_count += 1
                continue
        
        # Skip if no email address
        if not to_email:
            if contact_form_url:
                log_submission(
                    site,
                    contact_form_url,
                    "skipped",
                    "No email address, contact form URL available"
                )
                skipped_count += 1
            else:
                log_submission(
                    site,
                    "N/A",
                    "skipped",
                    "No email address or contact form URL"
                )
                skipped_count += 1
            continue
        
        # Validate domain first (quick check before attempting SMTP)
        domain = extract_domain_from_email(to_email)
        if domain:
            print(f"\nValidating domain for {site} ({to_email})...")
            is_valid, domain_error = validate_domain(domain)
            if not is_valid:
                log_submission(site, to_email, "failed", f"Domain validation failed: {domain_error}")
                print(f"  ✗ Domain validation failed: {domain_error}")
                failed_count += 1
                # If contact form available, note it as fallback
                if contact_form_url:
                    print(f"  ℹ Contact form available as fallback: {contact_form_url}")
                continue
        
        # Try to send email
        print(f"Sending email to {site} ({to_email})...")
        success, error_msg = send_email(to_email, subject, message, validate_domain_first=False)
        
        if success:
            log_submission(site, to_email, "sent", "Email sent successfully via SMTP")
            print(f"  ✓ Email sent successfully")
            sent_count += 1
        else:
            # Check if it's a domain error and suggest contact form fallback
            is_domain_error = "domain" in error_msg.lower() or "couldn't be found" in error_msg.lower()
            log_submission(site, to_email, "failed", error_msg)
            print(f"  ✗ Failed: {error_msg}")
            if is_domain_error and contact_form_url:
                print(f"  ℹ Contact form available as fallback: {contact_form_url}")
            failed_count += 1
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Sent: {sent_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Already sent (skipped): {already_sent_count}")
    print(f"  Total: {len(messages)}")
    print(f"{'='*60}")


def main():
    """Main entry point."""
    process_messages()


if __name__ == "__main__":
    main()


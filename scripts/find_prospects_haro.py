#!/usr/bin/env python3
"""
HARO (Help a Reporter Out) prospect finder.

Connects to email via IMAP, searches for HARO emails, and extracts relevant requests.
Uses the same email credentials as the submitter (SMTP_USER and SMTP_PASSWORD).
"""

import json
import os
import sys
import imaplib
import email
import re
from email.header import decode_header
from email.utils import parsedate_to_datetime
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from html import unescape

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
HARO_REQUESTS_FILE = DATA_DIR / "haro_requests.json"
PROSPECTS_FILE = DATA_DIR / "prospects.json"
CONTENT_SUMMARIES_FILE = DATA_DIR / "content_summaries.json"
HARO_EMAILS_MD_FILE = DATA_DIR / "haro_emails.md"

# Email Configuration (from environment variables - same as submitter)
IMAP_HOST = os.getenv("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
EMAIL_USER = os.getenv("SMTP_USER", "")
EMAIL_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# Business Configuration
TARGET_DOMAIN = os.getenv("TARGET_DOMAIN", "your-domain.com")

# HARO email patterns (common HARO sender addresses)
HARO_SENDER_PATTERNS = [
    "helpareporter",
    "haro",
    "help a reporter",
    "qwoted",
    "sourcebottle",
    "journorequests",
]


def decode_mime_words(s):
    """Decode MIME encoded words in email headers."""
    if not s:
        return ""
    decoded_parts = decode_header(s)
    decoded_str = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            try:
                decoded_str += part.decode(encoding or 'utf-8')
            except (UnicodeDecodeError, LookupError):
                decoded_str += part.decode('utf-8', errors='ignore')
        else:
            decoded_str += part
    return decoded_str


def extract_text_from_email(msg) -> str:
    """Extract plain text from email message."""
    text_content = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            
            # Skip attachments
            if "attachment" in content_disposition:
                continue
            
            # Get text content
            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        text_content += payload.decode(charset, errors='ignore')
                except Exception as e:
                    print(f"  Warning: Could not decode text part: {e}")
            elif content_type == "text/html":
                # Fallback to HTML if no plain text
                if not text_content:
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            html_content = payload.decode(charset, errors='ignore')
                            # Simple HTML tag removal
                            text_content = re.sub(r'<[^>]+>', ' ', html_content)
                            text_content = unescape(text_content)
                    except Exception as e:
                        print(f"  Warning: Could not decode HTML part: {e}")
    else:
        # Not multipart, get payload directly
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                text_content = payload.decode(charset, errors='ignore')
        except Exception as e:
            print(f"  Warning: Could not decode message: {e}")
    
    return text_content


def is_haro_email(sender: str, subject: str) -> bool:
    """Check if an email is from HARO."""
    sender_lower = sender.lower()
    subject_lower = subject.lower()
    
    for pattern in HARO_SENDER_PATTERNS:
        if pattern in sender_lower or pattern in subject_lower:
            return True
    
    return False


def extract_keywords_from_content() -> List[str]:
    """
    Extract unique keywords from your content summaries.
    
    Reads data/content_summaries.json and collects all unique topics/keywords.
    
    Returns:
        List of unique keywords/topics
    """
    if not CONTENT_SUMMARIES_FILE.exists():
        print(f"Warning: {CONTENT_SUMMARIES_FILE} not found. No keywords extracted.", file=sys.stderr)
        return []
    
    try:
        with open(CONTENT_SUMMARIES_FILE, "r") as f:
            content_summaries = json.load(f)
        
        keywords = set()
        for entry in content_summaries:
            topics = entry.get("topics", [])
            for topic in topics:
                # Add the topic as-is, and also split multi-word topics
                keywords.add(topic.lower())
                # Split by spaces and add individual words
                words = topic.lower().split()
                keywords.update(words)
        
        return sorted(list(keywords))
    
    except Exception as e:
        print(f"Warning: Could not extract keywords from content summaries: {e}", file=sys.stderr)
        return []


def extract_prospect_from_query(query_text: str, matched_keywords: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """
    Extract prospect information from a HARO query.
    
    HARO queries typically contain:
    - Reporter/journalist name
    - Publication/outlet name
    - Email address
    - Publication URL (sometimes)
    - The query itself
    
    Args:
        query_text: The full text of the HARO query
        matched_keywords: Optional list of keywords that matched (for reference)
    
    Returns:
        Prospect dict matching prospects.json structure, or None if insufficient info
    """
    if matched_keywords is None:
        matched_keywords = []
    # Extract email address
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_matches = re.findall(email_pattern, query_text)
    contact_email = email_matches[0] if email_matches else None
    
    # Extract URLs
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;:!?]'
    url_matches = re.findall(url_pattern, query_text)
    homepage_url = url_matches[0] if url_matches else None
    
    # Try to extract reporter/publication name
    # Common patterns: "Reporter Name, Publication Name" or "Publication Name - Reporter Name"
    lines = query_text.split('\n')
    site_name = None
    reporter_name = None
    
    # Look for patterns like "Name, Publication" or "Publication - Name"
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        if not line:
            continue
        
        # Pattern: "Reporter Name, Publication Name"
        match = re.match(r'^([^,]+),\s*(.+)$', line)
        if match:
            reporter_name = match.group(1).strip()
            site_name = match.group(2).strip()
            break
        
        # Pattern: "Publication - Reporter Name"
        match = re.match(r'^(.+?)\s*[-–—]\s*(.+)$', line)
        if match:
            site_name = match.group(1).strip()
            reporter_name = match.group(2).strip()
            break
        
        # Pattern: "Reporter Name at Publication"
        match = re.search(r'(.+?)\s+at\s+(.+)', line, re.IGNORECASE)
        if match:
            reporter_name = match.group(1).strip()
            site_name = match.group(2).strip()
            break
    
    # If we found a publication name, use it; otherwise try to construct from email domain
    if not site_name:
        if contact_email:
            # Try to extract domain and make a reasonable site name
            domain = contact_email.split('@')[1] if '@' in contact_email else None
            if domain:
                # Remove common email prefixes
                domain = domain.replace('mail.', '').replace('email.', '')
                site_name = domain.split('.')[0].title() + " Publication"
        else:
            # Last resort: use a generic name
            site_name = "HARO Request Publication"
    
    # If we have at least an email or URL, create a prospect
    if contact_email or homepage_url:
        # Create relevance description from query
        query_preview = query_text[:200].replace('\n', ' ').strip()
        if matched_keywords:
            relevance = f"HARO request: {query_preview}... (Keywords: {', '.join(matched_keywords[:5])})"
        else:
            relevance = f"HARO request: {query_preview}..."
        
        prospect = {
            "site_name": site_name,
            "homepage_url": homepage_url or f"https://{contact_email.split('@')[1]}" if contact_email else None,
            "contact_email": contact_email,
            "contact_form_url": None,
            "relevance": relevance,
            "found_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        return prospect
    
    return None


def connect_to_email() -> Optional[imaplib.IMAP4_SSL]:
    """Connect to email server via IMAP."""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("Error: Email credentials not configured.", file=sys.stderr)
        print("Set SMTP_USER and SMTP_PASSWORD environment variables (same as submitter)", file=sys.stderr)
        return None
    
    try:
        print(f"Connecting to {IMAP_HOST}:{IMAP_PORT}...", file=sys.stderr)
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(EMAIL_USER, EMAIL_PASSWORD)
        print("✓ Connected successfully", file=sys.stderr)
        return mail
    except imaplib.IMAP4.error as e:
        print(f"Error: IMAP authentication failed: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error connecting to email: {e}", file=sys.stderr)
        return None


def search_haro_emails(mail: imaplib.IMAP4_SSL, days_back: int = 30, since_date: Optional[datetime] = None) -> List[str]:
    """
    Search for HARO emails in the inbox.
    
    Args:
        mail: IMAP connection
        days_back: Number of days to search back (used if since_date is None)
        since_date: Optional datetime to search for emails after this date
    
    Returns:
        List of email IDs
    """
    try:
        mail.select("INBOX")
        
        # Use since_date if provided, otherwise use days_back
        if since_date:
            # IMAP SINCE is inclusive, so add 1 day to get emails AFTER the latest date
            from datetime import timedelta
            date_after = since_date + timedelta(days=1)
            # Format date for IMAP search (format: DD-MMM-YYYY)
            date_since = date_after.strftime("%d-%b-%Y")
            print(f"Searching for emails since {date_since} (after latest email date {since_date.strftime('%Y-%m-%d')})...", file=sys.stderr)
        else:
            # Search for emails from last N days
            from datetime import timedelta
            date_since = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            print(f"Searching for emails since {date_since}...", file=sys.stderr)
        
        search_criteria = f'(SINCE {date_since})'
        status, messages = mail.search(None, search_criteria)
        
        if status != "OK":
            print(f"Error searching emails: {status}", file=sys.stderr)
            return []
        
        email_ids = messages[0].split()
        print(f"Found {len(email_ids)} emails to check", file=sys.stderr)
        
        haro_email_ids = []
        
        for email_id in email_ids:
            try:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    continue
                
                msg = email.message_from_bytes(msg_data[0][1])
                sender = decode_mime_words(msg.get("From", ""))
                subject = decode_mime_words(msg.get("Subject", ""))
                
                if is_haro_email(sender, subject):
                    haro_email_ids.append(email_id.decode())
                    print(f"  Found HARO email: {subject[:60]}...", file=sys.stderr)
            
            except Exception as e:
                print(f"  Warning: Error processing email {email_id}: {e}", file=sys.stderr)
                continue
        
        return haro_email_ids
    
    except Exception as e:
        print(f"Error searching for HARO emails: {e}", file=sys.stderr)
        return []


def process_haro_email(mail: imaplib.IMAP4_SSL, email_id: str) -> Optional[Dict[str, Any]]:
    """Process a single HARO email and return the entire email content."""
    try:
        status, msg_data = mail.fetch(email_id.encode(), "(RFC822)")
        if status != "OK":
            return None
        
        msg = email.message_from_bytes(msg_data[0][1])
        sender = decode_mime_words(msg.get("From", ""))
        subject = decode_mime_words(msg.get("Subject", ""))
        date_str = msg.get("Date", "")
        
        # Extract email body
        email_body = extract_text_from_email(msg)
        
        if not email_body:
            return None
        
        # Return entire email (not extracting queries)
        email_data = {
            "email_id": email_id,
            "email_date": date_str,
            "email_subject": subject,
            "email_sender": sender,
            "email_body": email_body,
            "found_date": datetime.now().isoformat()
        }
        
        return email_data
    
    except Exception as e:
        print(f"  Error processing email {email_id}: {e}", file=sys.stderr)
        return None


def load_existing_requests() -> List[Dict[str, Any]]:
    """Load existing HARO requests from file."""
    if not HARO_REQUESTS_FILE.exists():
        return []
    
    try:
        with open(HARO_REQUESTS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load existing requests: {e}")
        return []


def save_requests(requests: List[Dict[str, Any]]):
    """Save HARO requests to JSON file."""
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(HARO_REQUESTS_FILE, "w") as f:
        json.dump(requests, f, indent=2)
    
    print(f"\n✓ Saved {len(requests)} requests to {HARO_REQUESTS_FILE}")


def load_existing_prospects() -> List[Dict[str, Any]]:
    """Load existing prospects from file."""
    if not PROSPECTS_FILE.exists():
        return []
    
    try:
        with open(PROSPECTS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load existing prospects: {e}")
        return []


def save_prospects(prospects: List[Dict[str, Any]]):
    """Save prospects to JSON file."""
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(PROSPECTS_FILE, "w") as f:
        json.dump(prospects, f, indent=2)
    
    print(f"\n✓ Saved {len(prospects)} prospects to {PROSPECTS_FILE}")


def is_duplicate_prospect(new_prospect: Dict[str, Any], existing_prospects: List[Dict[str, Any]]) -> bool:
    """Check if a prospect already exists (by email or URL)."""
    new_email = new_prospect.get("contact_email", "").lower() if new_prospect.get("contact_email") else None
    new_url = new_prospect.get("homepage_url", "").lower() if new_prospect.get("homepage_url") else None
    
    for existing in existing_prospects:
        existing_email = existing.get("contact_email", "").lower() if existing.get("contact_email") else None
        existing_url = existing.get("homepage_url", "").lower() if existing.get("homepage_url") else None
        
        # Check by email
        if new_email and existing_email and new_email == existing_email:
            return True
        
        # Check by URL
        if new_url and existing_url and new_url == existing_url:
            return True
    
    return False


def get_latest_email_date_from_markdown() -> Optional[datetime]:
    """
    Parse the latest email date from existing haro_emails.md markdown file.
    
    Returns:
        Latest email date as datetime object, or None if file doesn't exist or has no dates
    """
    if not HARO_EMAILS_MD_FILE.exists():
        return None
    
    try:
        with open(HARO_EMAILS_MD_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Find all date lines matching **Date:** pattern
        date_pattern = r'\*\*Date:\*\*\s*(.+)'
        date_matches = re.findall(date_pattern, content)
        
        if not date_matches:
            return None
        
        latest_date = None
        for date_str in date_matches:
            date_str = date_str.strip()
            if not date_str or date_str == "N/A":
                continue
            
            try:
                # Parse email date string (e.g., "Mon, 10 Nov 2025 17:11:44 +0000")
                parsed_date = parsedate_to_datetime(date_str)
                if latest_date is None or parsed_date > latest_date:
                    latest_date = parsed_date
            except (ValueError, TypeError) as e:
                # Skip invalid date strings
                continue
        
        return latest_date
    
    except Exception as e:
        print(f"Warning: Could not parse latest email date from markdown: {e}", file=sys.stderr)
        return None


def get_existing_email_ids_from_markdown() -> set:
    """
    Extract all email IDs from existing haro_emails.md markdown file.
    
    Returns:
        Set of email IDs found in the markdown file
    """
    if not HARO_EMAILS_MD_FILE.exists():
        return set()
    
    try:
        with open(HARO_EMAILS_MD_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Extract email IDs from the markdown (they're stored in process_haro_email but not in markdown)
        # Since email_id is not in the markdown format, we'll need to track by date+subject
        # For now, return empty set - we'll rely on haro_requests.json for duplicate checking
        # and date-based filtering for incremental fetching
        return set()
    
    except Exception as e:
        print(f"Warning: Could not extract email IDs from markdown: {e}", file=sys.stderr)
        return set()


def format_email_for_display(email_data: Dict[str, Any], index: int, total: int) -> str:
    """Format an entire email for human-readable display (markdown format)."""
    lines = []
    lines.append(f"## Email {index + 1} of {total}")
    lines.append("")
    lines.append(f"**Subject:** {email_data.get('email_subject', 'N/A')}")
    lines.append(f"**Date:** {email_data.get('email_date', 'N/A')}")
    lines.append(f"**From:** {email_data.get('email_sender', 'N/A')}")
    lines.append("")
    lines.append("**Email Body:**")
    lines.append("")
    # Format email body as a code block for better readability
    lines.append("```")
    lines.append(email_data.get('email_body', ''))
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def append_emails_to_markdown(new_emails: List[Dict[str, Any]]) -> bool:
    """
    Append new emails to existing markdown file with proper numbering.
    
    Args:
        new_emails: List of email data dictionaries to append
    
    Returns:
        True if successful, False otherwise
    """
    if not new_emails:
        return False
    
    try:
        # Read existing markdown file
        existing_content = ""
        current_total = 0
        
        if HARO_EMAILS_MD_FILE.exists():
            with open(HARO_EMAILS_MD_FILE, "r", encoding="utf-8") as f:
                existing_content = f.read()
            
            # Extract current total count from existing file
            total_match = re.search(r'\*\*Total Emails:\*\*\s*(\d+)', existing_content)
            if total_match:
                current_total = int(total_match.group(1))
        
        # Find where to insert new emails (after the last email)
        # Look for the last "---" separator that marks the end of an email
        insert_position = len(existing_content)
        
        # If file exists and has content, find the last email separator
        if existing_content:
            # Find the last occurrence of "---" separator
            # Pattern is "\n---\n" between emails
            last_separator = existing_content.rfind("\n---\n")
            if last_separator != -1:
                # Insert after the last separator and its trailing newline
                insert_position = last_separator + len("\n---\n")
            elif existing_content.rstrip().endswith("---"):
                # File ends with "---", find it and insert after
                last_separator = existing_content.rfind("---")
                if last_separator != -1:
                    insert_position = last_separator + len("---")
                    # Skip any trailing whitespace/newlines
                    while insert_position < len(existing_content) and existing_content[insert_position] in ['\n', '\r', ' ']:
                        insert_position += 1
                    # Ensure we have at least one newline before new content
                    if insert_position == 0 or existing_content[insert_position-1] != '\n':
                        # Will add newline when joining
                        pass
        
        # Build new email content
        new_email_lines = []
        for i, email_data in enumerate(new_emails):
            # Number emails starting from current_total + 1
            formatted = format_email_for_display(email_data, current_total + i, current_total + len(new_emails))
            new_email_lines.append(formatted)
        
        # Update total count in header
        new_total = current_total + len(new_emails)
        
        # Reconstruct the file
        if not existing_content:
            # Create new file
            markdown_lines = []
            markdown_lines.append("# HARO Emails")
            markdown_lines.append("")
            markdown_lines.append(f"**Total Emails:** {new_total}")
            markdown_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            markdown_lines.append("")
            markdown_lines.append("---")
            markdown_lines.append("")
            markdown_lines.extend(new_email_lines)
            final_content = "\n".join(markdown_lines)
        else:
            # Update existing file
            # Update total count in header
            updated_content = re.sub(
                r'\*\*Total Emails:\*\*\s*\d+',
                f'**Total Emails:** {new_total}',
                existing_content,
                count=1
            )
            # Update generated timestamp
            updated_content = re.sub(
                r'\*\*Generated:\*\*\s*[^\n]+',
                f'**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                updated_content,
                count=1
            )
            # Insert new emails at the appropriate position
            final_content = (
                updated_content[:insert_position] +
                "\n".join(new_email_lines) +
                updated_content[insert_position:]
            )
        
        # Write updated content
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(HARO_EMAILS_MD_FILE, "w", encoding="utf-8") as f:
            f.write(final_content)
        
        return True
    
    except Exception as e:
        print(f"Error appending emails to markdown: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point - fetches HARO emails and outputs as markdown file."""
    # Check if output file already exists and get latest email date
    latest_date = None
    is_incremental = False
    
    if HARO_EMAILS_MD_FILE.exists():
        print(f"Output file {HARO_EMAILS_MD_FILE} exists. Checking for new emails after latest date...", file=sys.stderr)
        latest_date = get_latest_email_date_from_markdown()
        if latest_date:
            is_incremental = True
            print(f"Found latest email date: {latest_date.strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
        else:
            print(f"Warning: Could not parse latest email date. Will search last 30 days.", file=sys.stderr)
    
    # Extract keywords from content summaries (for reference, displayed in stderr)
    keywords = extract_keywords_from_content()
    if keywords:
        domain_display = TARGET_DOMAIN if TARGET_DOMAIN != "your-domain.com" else "your content"
        print(f"\nExtracted {len(keywords)} keywords from {domain_display} content:", file=sys.stderr)
        print("Keywords:", ", ".join(keywords[:20]), file=sys.stderr)
        if len(keywords) > 20:
            print(f"... and {len(keywords) - 20} more", file=sys.stderr)
        print("", file=sys.stderr)
    
    # Connect to email
    mail = connect_to_email()
    if not mail:
        return
    
    try:
        # Search for HARO emails (with date filter if incremental)
        if is_incremental and latest_date:
            haro_email_ids = search_haro_emails(mail, since_date=latest_date)
        else:
            haro_email_ids = search_haro_emails(mail, days_back=30)
        
        if not haro_email_ids:
            if is_incremental:
                print("\nNo new HARO emails found after latest date.", file=sys.stderr)
            else:
                print("\nNo HARO emails found.", file=sys.stderr)
                # Create empty markdown file only if it doesn't exist
                if not HARO_EMAILS_MD_FILE.exists():
                    DATA_DIR.mkdir(parents=True, exist_ok=True)
                    with open(HARO_EMAILS_MD_FILE, "w") as f:
                        f.write("# HARO Emails\n\nNo HARO emails found.\n")
                    print(f"Created empty output file: {HARO_EMAILS_MD_FILE}", file=sys.stderr)
            return
        
        # Load existing requests to avoid duplicates
        existing_requests = load_existing_requests()
        existing_email_ids = {req.get("email_id") for req in existing_requests if req.get("email_id")}
        
        all_emails = []
        
        # Process each HARO email
        for email_id in haro_email_ids:
            if email_id in existing_email_ids:
                continue  # Skip already processed emails
            
            email_data = process_haro_email(mail, email_id)
            if email_data:
                all_emails.append(email_data)
        
        if not all_emails:
            if is_incremental:
                print("\nNo new HARO emails found after latest date.", file=sys.stderr)
            else:
                print("\nNo new HARO emails found.", file=sys.stderr)
                # Create empty markdown file only if it doesn't exist
                if not HARO_EMAILS_MD_FILE.exists():
                    DATA_DIR.mkdir(parents=True, exist_ok=True)
                    with open(HARO_EMAILS_MD_FILE, "w") as f:
                        f.write("# HARO Emails\n\nNo new HARO emails found.\n")
                    print(f"Created empty output file: {HARO_EMAILS_MD_FILE}", file=sys.stderr)
            return
        
        # Append or create markdown file
        if is_incremental:
            # Append to existing file
            if append_emails_to_markdown(all_emails):
                print(f"\n✓ Appended {len(all_emails)} new emails to {HARO_EMAILS_MD_FILE}", file=sys.stderr)
                print(f"✓ File ready for review", file=sys.stderr)
            else:
                print(f"\n✗ Error appending emails to markdown file", file=sys.stderr)
        else:
            # Create new file
            markdown_lines = []
            markdown_lines.append("# HARO Emails")
            markdown_lines.append("")
            markdown_lines.append(f"**Total Emails:** {len(all_emails)}")
            markdown_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            markdown_lines.append("")
            markdown_lines.append("---")
            markdown_lines.append("")
            
            for i, email_data in enumerate(all_emails):
                formatted = format_email_for_display(email_data, i, len(all_emails))
                markdown_lines.append(formatted)
            
            # Write markdown to file
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(HARO_EMAILS_MD_FILE, "w") as f:
                f.write("\n".join(markdown_lines))
            
            print(f"\n✓ Saved {len(all_emails)} emails to {HARO_EMAILS_MD_FILE}", file=sys.stderr)
            print(f"✓ File ready for review", file=sys.stderr)
    
    finally:
        try:
            mail.logout()
        except:
            pass


if __name__ == "__main__":
    main()


# Link Builder - Automated Backlink Generation

## TLDR

**Automated backlink builder** that utilizes Cursor agents to find backlink opportunities, generates personalized outreach messages, and **automatically sends emails** to get backlinks. 

**Quick workflow**: Run `/find-prospects` and/or `/find-prospects-haro` → `/content-mapper` → `/outreach-writer` → `/submitter` in Cursor. Configure SMTP in `.env` for automatic sending, or copy-paste messages manually. All results tracked in `data/outreach_log.csv`.

---

An automated link-building workflow that discovers prospects, generates personalized outreach messages, and **automatically sends backlink requests** via email or contact forms. Get backlinks to your website with minimal manual effort.

## What This Does

This tool automates the entire backlink building process:

1. **Finds Prospects** - Discovers websites that accept guest posts, link to resources, or have broken links (via Google search or HARO emails)
2. **Maps Your Content** - Analyzes your blog to understand your topics and expertise
3. **Generates Outreach** - Creates personalized outreach messages matching your content to relevant opportunities
4. **Automatically Submits** - **Sends emails automatically via SMTP** and fills contact forms via browser
5. **Tracks Results** - Logs all submissions so you can track which sites you've contacted

## Quick Start: Generate Backlinks Automatically

### Step 1: Initial Setup

1. **Copy the environment template:**
   ```bash
   cp env.template .env
   ```

2. **Configure your settings** (use the interactive setup script):
   ```bash
   ./setup_env.sh
   ```
   
   Or manually edit `.env` with:
   - Your domain and business name
   - Your blog URL
   - SMTP email credentials (only needed if you want automatic email sending - see [Submission Options](#submission-options) below)

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Step 2: Run the Automated Workflow

Execute these Cursor commands in sequence (each step builds on the previous):

#### Option A: Google Search Method (Recommended for most users)

```bash
# 1. Find prospects via Google search
/find-prospects

# 2. Map your blog content
/content-mapper

# 3. Generate personalized outreach messages
/outreach-writer

# 4. Automatically send emails and submit forms
/submitter
```

#### Option B: HARO Method (For journalists/reporters)

Note: Your email must be recieving HARO requests for this to work.

```bash
# 1. Find HARO prospects from your email
/find-prospects-haro

# 2. Map your blog content (if not done already)
/content-mapper

# 3. Generate personalized outreach messages
/outreach-writer

# 4. Automatically send emails and submit forms
/submitter
```

#### Option C: Mix and Match (Combine both methods)

You can combine both methods to maximize your prospects:

```bash
# 1. Find prospects via Google search
/find-prospects

# 2. Find HARO prospects from your email (optional)
/find-prospects-haro

# 3. Map your blog content
/content-mapper

# 4. Generate personalized outreach messages (combines all prospects)
/outreach-writer

# 5. Automatically send emails and submit forms
/submitter
```

**Note**: Running both `/find-prospects` and `/find-prospects-haro` will combine all prospects into a single list. The `/outreach-writer` command will then match all prospects with your content.

### Step 3: Review Results

Check your results in the `data/` directory:
- `outreach_log.csv` - See which sites you've contacted and their status
- `prospects.json` - All discovered link opportunities
- `outreach_messages.json` - Generated outreach messages

## Submission Options

### Option 1: Automatic Submission (Recommended)

The `/submitter` command automatically:

1. **Sends emails via SMTP** - Reads `data/outreach_messages_validated.json` and sends personalized emails to all prospects
2. **Validates domains** - Checks email domains before sending to avoid bounces
3. **Skips duplicates** - Automatically skips sites you've already contacted
4. **Fills contact forms** - Uses browser automation to fill and submit contact forms
5. **Logs everything** - Records all attempts in `data/outreach_log.csv` with status (sent, failed, skipped)

**No manual work required** - just run `/submitter` and it handles all email sending automatically!

**Requires**: SMTP email configuration (see [Email Configuration](#email-configuration-required-for-automatic-sending) section)

### Option 2: Manual Submission (No Email Setup Required)

If you prefer to send emails manually or don't want to configure SMTP:

1. **Generate messages** - Run steps 1-3 (`/find-prospects` or `/find-prospects-haro`, `/content-mapper`, `/outreach-writer`)
2. **Review messages** - Open `data/outreach_messages.json` or `data/outreach_messages_validated.json`
3. **Copy and paste** - Manually copy each message and send via your email client
4. **Track manually** - Update `data/outreach_log.csv` with your submissions

**Benefits**:
- No email configuration needed
- Full control over when and how you send
- Can personalize messages further before sending
- Works with any email client (Gmail, Outlook, etc.)

**Note**: Even with manual submission, the tool still generates personalized messages and matches prospects to your content automatically. You just handle the actual sending yourself.

## Detailed Setup Instructions

### Email Configuration (Required for Automatic Sending Only)

**Skip this section if you plan to send emails manually** (copy-paste method). You only need email configuration if you want the tool to send emails automatically.

To enable automatic email sending, you need SMTP credentials:

1. **Use the interactive setup script (easiest):**
   ```bash
   ./setup_env.sh
   ```
   This will prompt you for all required settings.

2. **Or manually configure `.env`:**
   ```bash
   cp env.template .env
   # Edit .env with your settings
   ```

   Required settings:
   ```bash
   # Business Info
   TARGET_DOMAIN=your-domain.com
   BUSINESS_NAME=Your Business Name
   BLOG_URL=https://your-domain.com/blog
   
   # SMTP (for automatic email sending)
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   SMTP_FROM_EMAIL=your-email@gmail.com
   SMTP_FROM_NAME=Your Business Team
   SMTP_USE_TLS=true
   ```

3. **For Gmail users** - Generate an App Password:
   - Visit https://myaccount.google.com/apppasswords
   - Generate a new app password for "Mail"
   - Use this 16-character password (not your regular password) for `SMTP_PASSWORD`

### Other Email Providers

- **Outlook**: `SMTP_HOST=smtp-mail.outlook.com`, `SMTP_PORT=587`
- **Yahoo**: `SMTP_HOST=smtp.mail.yahoo.com`, `SMTP_PORT=587`
- **Custom**: Check with your email provider for SMTP settings

## Workflow Details

### Method 1: Google Search (`/find-prospects`)

Finds link opportunities by searching Google for:
- Guest post opportunities ("write for us" + your keywords)
- Resource pages that link to external content
- Broken link building opportunities

**How it works:**
1. Extracts keywords from your website and blog
2. Searches Google with targeted queries
3. Identifies sites that accept guest posts or link to resources
4. Extracts contact information (email or contact form)
5. Saves prospects to `data/prospects.json`

### Method 2: HARO (`/find-prospects-haro`)

Finds journalists and reporters looking for sources via HARO emails.

**How it works:**
1. Connects to your email via IMAP (uses same credentials as SMTP)
2. Searches for HARO emails in your inbox (last 30 days)
3. Extracts relevant queries based on your content topics
4. Creates prospects from journalist requests
5. Saves to `data/prospects.json` and `data/haro_requests.json`

**Note**: You need to be subscribed to HARO (or similar services like Qwoted, SourceBottle) for this to work.

### Content Mapping (`/content-mapper`)

Analyzes your blog to understand your expertise:
- Visits your blog URL
- Extracts post titles, summaries, and topics
- Creates a content map for matching with prospects
- Saves to `data/content_summaries.json`

### Outreach Generation (`/outreach-writer`)

Creates personalized outreach messages:
- Matches prospects to relevant blog posts
- Generates personalized messages (not generic templates)
- Includes specific content recommendations
- Saves to `data/outreach_messages.json` and `data/outreach_messages_validated.json`

### Automatic Submission (`/submitter`)

**This is where the magic happens** - automatically sends your backlink requests:

1. **Automatic Email Sending:**
   - Reads `data/outreach_messages_validated.json`
   - Validates email domains before sending
   - Sends personalized emails via SMTP
   - Skips duplicates (checks `outreach_log.csv`)
   - Logs all results

2. **Contact Form Submission:**
   - For sites with contact forms (no email)
   - Uses browser automation to fill and submit forms
   - Handles form validation and submission

3. **Tracking:**
   - All attempts logged to `data/outreach_log.csv`
   - Status: `sent`, `failed`, `skipped`, `opened`
   - Includes timestamps and notes

## Output Files

All results are saved in the `data/` directory:

- `prospects.json` - All discovered link opportunities
- `content_summaries.json` - Your blog posts with topics
- `outreach_messages.json` - Generated outreach messages
- `outreach_messages_validated.json` - Validated messages ready to send
- `outreach_log.csv` - **Submission tracking** (who you contacted, when, status)
- `haro_requests.json` - HARO queries found (if using HARO method)
- `haro_emails.md` - Formatted HARO queries for review

## Utility Scripts

- `scripts/send_emails.py` - Standalone email sending script (also used by `/submitter`)
- `scripts/track_links.py` - Check which sites have linked back to you
- `scripts/find_prospects_haro.py` - Fetch HARO emails from your inbox
- `scripts/log_activity.py` - Track workflow activities

## Requirements

- **Python 3.7+** (for utility scripts)
- **Cursor IDE** (for running commands)
- **Python packages** (install with `pip install -r requirements.txt`):
  - `requests` - For HTTP requests
  - `beautifulsoup4` - For HTML parsing
  - `lxml` - HTML parser backend
  - `python-dotenv` - For loading `.env` files (optional but recommended)

**Note**: The email sending script uses Python's built-in `smtplib`, so no additional packages are needed for email functionality.

## Tips & Best Practices

### Running the Workflow

1. **Run steps in order** - Each command builds on the previous one's output
2. **Review before submitting** - Check `outreach_messages.json` before running `/submitter`
3. **Start small** - Test with a few prospects first to ensure everything works
4. **Monitor your email** - Check your sent folder to verify emails are being sent correctly

### Avoiding Spam

- **Personalize messages** - The tool generates personalized messages, but review them
- **Respect rate limits** - Don't send hundreds of emails at once
- **Follow up appropriately** - Wait for responses before following up
- **Check spam folders** - Some emails may end up in spam

### Tracking Success

- **Monitor `outreach_log.csv`** - See which sites you've contacted
- **Use `track_links.py`** - Check which sites have linked back to you
- **Update status manually** - Mark successful links in the log as "opened" or "linked"

### Re-running the Workflow

- **Prospects accumulate** - Running `/find-prospects` multiple times adds to existing prospects
- **Duplicates are skipped** - The system automatically skips sites you've already contacted
- **Content mapping updates** - Re-run `/content-mapper` if you publish new blog posts
- **HARO updates** - Delete `data/haro_emails.md` to re-fetch HARO emails

## Troubleshooting

### Emails Not Sending

- **Check SMTP credentials** - Verify your email and app password are correct
- **Check domain validation** - Invalid domains are skipped automatically
- **Check spam folder** - Some emails may be filtered
- **Review `outreach_log.csv`** - See error messages for failed sends

### No Prospects Found

- **Expand keywords** - The tool extracts keywords from your site, but you can manually add more
- **Try different search terms** - Adjust the search queries in `/find-prospects`
- **Check HARO subscription** - Make sure you're receiving HARO emails if using that method

### Contact Forms Not Submitting

- **Some forms require manual submission** - Browser automation may not work for all forms
- **Check form structure** - Complex forms may need manual handling
- **Use email as fallback** - If a site has both email and form, email is preferred

## Cursor Commands Reference

- `/find-prospects` - Find prospects via Google search
- `/find-prospects-haro` - Find prospects from HARO emails
- `/content-mapper` - Map your blog content
- `/outreach-writer` - Generate outreach messages
- `/submitter` - Automatically send emails and submit forms


# Link Builder Workflow

An automated link-building workflow using Cursor commands to discover prospects, map content, generate outreach messages, and track submissions.

## Quick Start

Run the complete workflow using the WorkflowOrchestrator command:
```
/WorkflowOrchestrator
```

Or run individual steps:
- `/ProspectFinder` - Find link-building prospects
- `/ContentMapper` - Map blog content
- `/OutreachWriter` - Generate outreach messages
- `/Submitter` - Submit and log outreach attempts

## What It Does

The workflow executes 4 steps automatically:

1. **ProspectFinder** - Searches for fashion blogs that accept guest posts
2. **ContentMapper** - Maps your blog content from build-a-dress.com
3. **OutreachWriter** - Generates personalized outreach messages
4. **Submitter** - Logs all submission attempts

## Output Files

All results are saved in the `data/` directory:

- `prospects.json` - Found link-building opportunities
- `content_summaries.json` - Your blog posts mapped
- `outreach_messages.json` - Generated outreach messages
- `outreach_log.csv` - Submission tracking log

## Cursor Commands

The `.cursor/commands/` directory contains Cursor command files for agent execution:
- `workflow-orchestrator.md` - Main orchestrator that runs all steps
- `find-prospects.md` - Prospect discovery
- `content-mapper.md` - Content mapping
- `outreach-writer.md` - Message generation
- `submitter.md` - Submission logging

## Utility Scripts

- `scripts/track_links.py` - Check which sites have linked back to you
- `scripts/log_activity.py` - Track workflow activities
- `scripts/send_emails.py` - Automatically send outreach emails via SMTP

## Automatic Email Sending

The Submitter command now supports automatic email sending via SMTP. To enable this:

1. **Set up SMTP credentials** - You have three options:

   **Option A: Use the setup script (recommended)**
   ```bash
   ./setup_env.sh
   ```
   This interactive script will prompt you for your SMTP settings and create a `.env` file.

   **Option B: Create .env file manually**
   ```bash
   cp env.template .env
   # Then edit .env and fill in your values
   ```

   **Option C: Set environment variables directly**
   ```bash
   export SMTP_HOST=smtp.gmail.com
   export SMTP_PORT=587
   export SMTP_USER=your-email@gmail.com
   export SMTP_PASSWORD=your-app-password
   export SMTP_FROM_EMAIL=your-email@gmail.com
   export SMTP_FROM_NAME="Build-a-Dress Team"
   export SMTP_USE_TLS=true
   ```

   **Note**: If you use a `.env` file, the script will automatically load it (requires `python-dotenv` package).

2. **For Gmail users**: You'll need to generate an "App Password":
   - Go to https://myaccount.google.com/apppasswords
   - Generate a new app password for "Mail"
   - Use this app password (not your regular password) for `SMTP_PASSWORD`

3. **Run the email script**:
   ```bash
   python scripts/send_emails.py
   ```

   Or let the Submitter command handle it automatically when you run `/Submitter`.

The script will:
- Read messages from `data/outreach_messages.json`
- Send emails automatically via SMTP for all messages with email addresses
- Log results to `data/outreach_log.csv`
- Skip messages that only have contact forms (those are handled via browser)

## Requirements

The Cursor commands use built-in browser tools and don't require Python dependencies. The utility scripts require:
- Python 3.7+
- requests
- beautifulsoup4
- lxml

Install with: `pip install -r requirements.txt`

**Note**: The email sending script uses Python's built-in `smtplib`, so no additional packages are needed for email functionality.


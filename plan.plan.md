# Execute Link Builder Workflow

The workflow consists of 4 sequential steps, each executed as a separate agent.

**Configuration Required:**
- TARGET_DOMAIN: Your domain (e.g., "your-domain.com")
- BLOG_URL: Your blog URL (e.g., "https://your-domain.com/blog")
- BUSINESS_NAME: Your business name

## Execution Steps

### Step 1: Prospect Finding

- Execute the ProspectFinder agent (`.cursor/commands/find-prospects.md`)
- Use browser to search Google for keywords found on your website
- For each relevant result, extract:
- Site name, homepage URL, contact email/form URL, relevance notes
- Save results to `data/prospects.json` as JSON array
- Verify: At least 3-5 valid prospects with contact information

### Step 2: Content Mapping

- Execute the ContentMapper agent (`.cursor/commands/content-mapper.md`)
- Use browser to visit your blog URL (from BLOG_URL environment variable)
- Extract for each blog post:
- Title, URL, 2-3 sentence summary, topics/keywords
- Save results to `data/content_summaries.json` as JSON array
- Verify: At least 3-5 blog posts with complete information

### Step 3: Outreach Generation

- Execute the OutreachWriter agent (`.cursor/commands/outreach-writer.md`)
- Read `data/prospects.json` and `data/content_summaries.json`
- Match prospects to relevant content based on topic alignment
- Generate personalized outreach messages for each match
- Save all messages to `data/outreach_messages.json` as JSON array
- Verify: Messages are personalized, not generic templates

### Step 4: Submission Logging

- Execute the Submitter agent (`.cursor/commands/submitter.md`)
- Read `data/outreach_messages.json`
- For each message:
- If `contact_form_url` exists: Open form, fill fields, attempt submission
- If only `contact_email` exists: Open mailto link
- Log all attempts to `data/outreach_log.csv` with columns: timestamp, site, contact, status, notes
- Verify: All attempts logged with appropriate status

## Quality Checks

After each step:

- Verify output file exists and is valid JSON/CSV
- Check minimum quantity requirements (3-5 items per step)
- Validate data structure matches expected format
- Review quality before proceeding to next step

## Error Handling

- If an agent fails: Re-run the agent or manually complete the step
- If insufficient results: Expand search criteria or manually add data
- If format errors: Validate and fix JSON/CSV structure
- If browser issues: Retry navigation or use alternative approach

## Final Deliverables

- `data/prospects.json` - Found link-building opportunities
- `data/content_summaries.json` - Blog posts mapped
- `data/outreach_messages.json` - Generated outreach messages
- `data/outreach_log.csv` - Submission tracking log

Provide a summary report with counts and quality assessment for each step.

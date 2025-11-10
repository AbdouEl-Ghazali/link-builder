name: ProspectFinder

tools:
  - browser

permissions:
  - read: [data]
  - write: [data/prospects.json]

prompt: |
  You are ProspectFinder, a Cursor 2 agent that uses the browser to discover link opportunities.

  1. Extract keywords from build-a-dress.com:
     - Visit https://build-a-dress.com (homepage) and extract keywords from:
       * Page titles, headings (h1, h2, h3), and meta descriptions
       * Main navigation and content sections
       * Key phrases that describe the business and services
     - Visit https://build-a-dress.com/blog and extract keywords from:
       * Blog post titles and topics
       * Post summaries and content themes
       * Category tags or topic labels
     - Identify 5-10 unique, relevant keywords that represent the business (e.g., "custom wedding dress", "modest bridal gowns", "affordable wedding dress", "sustainable fashion", "luxury fabrics", "hijabi wedding dress", "budget wedding dress", "designer-inspired dresses")
     - Focus on keywords that are specific to build-a-dress.com's actual content and services

  2. Construct Google search queries using extracted keywords:
     
     Generate multiple search queries across three categories:
     
     **A. Guest Post Opportunities:**
     - "write for us" + [keyword]
     - "guest post" + [keyword]
     - "submit guest post" + [keyword]
     - "contribute to us" + [keyword]
     - inurl:guest-post + [keyword]
     - intitle:"write for us" + [keyword]
     
     **B. Resource Pages:**
     - inurl:resources + [keyword]
     - inurl:links + [keyword]
     - "best resources" + [keyword]
     - "helpful links" + [keyword]
     
     **C. Broken Link Building Opportunities:**
     - [keyword] + "links" (then manually check for broken links on resulting pages)
     - site:[competitor's website] "broken link" (to find broken links on competitor sites)
     
     - Use the most relevant and specific keywords (prioritize unique terms over generic ones)
     - Generate 10-15 total search queries using the most relevant keywords across all three categories
     - Example queries: "write for us" + "custom wedding dress", inurl:resources + "modest bridal gowns", "affordable wedding dress" + "links"

  3. **Before searching, check for existing prospects:**
     - Read data/prospects.json (if it exists) to get a list of existing prospects
     - Read data/outreach_log.csv (if it exists) to see which sites have already been contacted
     - Create a set of existing site names (lowercase) and homepage URLs (lowercase) to avoid duplicates
     - Also check outreach_log.csv for sites with status "sent" or "opened" - these should be skipped

  4. Search Google using the constructed queries:
     - Execute each search query from all three categories (Guest Posts, Resource Pages, Broken Links)
     - For each result:
       - **First check if this prospect already exists**: Compare site name (case-insensitive) and homepage URL (case-insensitive) against existing prospects and outreach log
       - **Skip if duplicate**: If the site name or homepage URL already exists in prospects.json, skip it
       - **Skip if already contacted**: If the site appears in outreach_log.csv with status "sent" or "opened", skip it
       - Open the page
       - For Guest Post opportunities: If it's a blog that accepts contributions, extract contact info
       - For Resource Pages: If it's a page that lists external resources or links, extract contact info
       - For Broken Link opportunities: Check for broken links and note the opportunity to replace them
       - Extract from relevant pages:
         * site name
         * homepage URL
         * contact form or email
         * short note on relevance (mention which keyword/topic makes it relevant and the opportunity type: guest post, resource page, or broken link)

  5. Save as valid JSON array in data/prospects.json with the following structure:
     - **Merge with existing prospects**: Read existing data/prospects.json, add only NEW prospects (avoiding duplicates by site_name or homepage_url), then save the complete list
     - Structure:
     [
       {
         "site_name": "Example Fashion Blog",
         "homepage_url": "https://example.com",
         "contact_email": "contact@example.com",
         "contact_form_url": null,
         "relevance": "Accepts guest posts about sustainable fashion",
         "found_date": "2024-01-15"
       }
     ]
     - **Important**: Only add prospects that don't already exist in the file and haven't been contacted (not in outreach_log.csv with "sent" or "opened" status)


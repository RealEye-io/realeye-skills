# Benchmark summary

150 SaaS landing pages, first screen only (desktop 1440×900, mobile 390×844): 100 top SaaS, 25 average SaaS, 25 poorly made SaaS. Captured 2026-11-13 (first 25 top-SaaS pages) and 2026-11-16 (the rest). Values = predicted attention share, CAS (composite) at 3 s, % of the screenshot. Full data (all AOIs, Speed/Reach/Hold, 3/6/10 s, texts, boxes) in `data/benchmark.json`.

The goal when optimising a page is not rank 1 on every element. It is: no blind spots, each element inside the typical range of top pages built the same way, and a similar attention spread. Only the top-SaaS group is the yardstick; the average and poorly made groups are context. Reports recompute all numbers without the target page.

## Groups and how pages were chosen

- **Top SaaS (`saas`, reference pool):** 100 of the biggest / best-known SaaS companies (large public companies and category leaders). Chosen for size and brand, not for proven conversion. Pages that blocked capture (bot walls) or showed chat/promo popups over the hero were skipped.
- **Average SaaS (`average`):** 25 mid-size, lesser-known SaaS companies sampled across categories (project management, time tracking, invoicing, scheduling, live chat, help desk, CRM, e-mail marketing), not chosen for design quality.
- **Poorly made SaaS (`poor`):** 25 pages picked in a manual audit of 67 small or legacy SaaS vendors. A page qualified when its first screen failed at least one written criterion: no clear headline or a headline that is not a value proposition; no visible sign-up CTA in the first screen; cluttered or text-wall hero; small or low-contrast text; a notice, carousel or form in place of a message; dated layout with weak hierarchy. This is one reviewer's judgement, not a published ranking, and some pages are borderline. The reason for each page is listed below.
- RealEye and other eye-tracking / attention / UX-research tools are deliberately not in the bundled benchmark.

## Approaches

- **Message-led** (`message`): the text carries the screen: message block gets at least 2x the hero visual's attention (or there is no hero visual).
- **Balanced (message + visual)** (`balanced`): message and hero visual share the screen: neither gets 2x the other.
- **Visual-led** (`visual`): the product/visual carries the screen: hero visual gets at least 2x the message block's attention.

## Desktop: reference ranges by approach (top-SaaS pages; p25–p75, median in brackets, pages having the element)

- **Message-led** (27): Airtable, Asana, GitHub, Intercom, Mailchimp, Shopify, Stripe, Zendesk, Workday, Snowflake, Docusign, Cloudflare, 1Password, Typeform, Ahrefs, Buffer, PagerDuty, GitLab, Apollo, ZoomInfo, PandaDoc, Cal.com, Help Scout, Auth0, Grafana, Replit, Paddle
- **Balanced (message + visual)** (36): Calendly, Canva, HubSpot, Linear, monday.com, Notion, Slack, Twilio, Okta, Wix, Box, Gusto, Pipedrive, Freshworks, Zoho, Klaviyo, SurveyMonkey, Sentry, Netlify, Brevo, ActiveCampaign, Gong, Attio, Brex, Plaid, Trello, Todoist, Lucid, RingCentral, Bitwarden, Elastic, New Relic, Descript, Retool, Make, Dialpad
- **Visual-led** (37): Atlassian, ClickUp, Datadog, Dropbox, Figma, Miro, Vercel, Webflow, Zapier, Zoom, MongoDB, Squarespace, Rippling, Deel, Grammarly, Postman, Supabase, DigitalOcean, Outreach, Clay, Ramp, Expensify, Square, Basecamp, Evernote, Framer, Amplitude, Mixpanel, PostHog, Unbounce, Snyk, Databricks, ElevenLabs, Cursor, n8n, Optimizely, CrowdStrike

| Element | Message-led (27) | Balanced (message + visual) (36) | Visual-led (37) | Average SaaS, all approaches (median) | Poorly made SaaS (median) |
|---|---|---|---|---|---|
| Message block | 18.4–29.5 [21.7] (27/27) | 15.7–27.4 [20.2] (36/36) | 8.7–14.9 [13.1] (37/37) | 17.5 (25/25) | 10.7 (25/25) |
| Headline | 13.9–25.2 [19.9] (27/27) | 11.0–21.1 [14.6] (36/36) | 6.4–11.4 [8.4] (37/37) | 12.8 (25/25) | 8.5 (25/25) |
| Subhead | 3.1–5.2 [4.6] (24/27) | 3.6–6.0 [4.6] (36/36) | 2.2–4.6 [3.7] (31/37) | 5.5 (22/25) | 4.0 (17/25) |
| Action block | 2.1–4.4 [2.6] (27/27) | 1.4–2.6 [1.9] (35/36) | 1.4–2.5 [2.0] (34/37) | 2.1 (25/25) | 1.9 (25/25) |
| Primary CTA | 0.9–1.8 [1.3] (25/27) | 0.8–1.5 [1.0] (35/36) | 0.7–1.5 [1.2] (33/37) | 1.4 (25/25) | 1.2 (24/25) |
| Secondary CTA | 1.0–1.6 [1.2] (12/27) | 0.7–1.3 [1.0] (24/36) | 0.6–1.2 [1.0] (20/37) | 1.3 (14/25) | 0.9 (9/25) |
| Hero visual | 4.1–8.4 [7.5] (7/27) | 19.4–31.0 [25.2] (36/36) | 29.5–47.6 [36.9] (37/37) | 24.7 (23/25) | 31.9 (20/25) |
| Trust strip | 3.3–4.9 [4.2] (8/27) | 2.0–3.6 [3.2] (10/36) | 2.7–4.2 [3.0] (4/37) | 2.3 (7/25) | 6.3 (5/25) |
| Nav CTA | 0.2–0.3 [0.2] (23/27) | 0.2–0.3 [0.2] (33/36) | 0.1–0.3 [0.2] (30/37) | 0.2 (24/25) | 0.2 (19/25) |

Mean attention spread %:

| Group | Message (eyebrow + headline + subhead) | Action (hero CTAs + form) | Hero visual | Trust / proof | Header + announcement | Background / unassigned |
|---|---|---|---|---|---|---|
| Top SaaS, Message-led | 24.1 | 3.6 | 1.8 | 1.3 | 8.1 | 61.0 |
| Top SaaS, Balanced (message + visual) | 20.8 | 2.0 | 26.3 | 1.0 | 7.5 | 42.4 |
| Top SaaS, Visual-led | 12.2 | 2.0 | 41.2 | 0.4 | 7.5 | 36.7 |
| Average SaaS | 18.4 | 2.7 | 24.8 | 1.2 | 7.3 | 45.6 |
| Poorly made SaaS | 13.6 | 2.8 | 22.7 | 1.5 | 6.9 | 52.5 |

## Mobile: reference ranges by approach (top-SaaS pages; p25–p75, median in brackets, pages having the element)

- **Message-led** (58): Airtable, Calendly, Canva, ClickUp, Dropbox, GitHub, HubSpot, Intercom, Mailchimp, Notion, Shopify, Stripe, Vercel, Webflow, Zendesk, Workday, Snowflake, Docusign, Twilio, Cloudflare, Squarespace, Box, Rippling, Deel, Grammarly, 1Password, Typeform, Pipedrive, Freshworks, Ahrefs, Buffer, SurveyMonkey, PagerDuty, GitLab, Postman, Supabase, Brevo, Apollo, ZoomInfo, Expensify, Trello, Todoist, Mixpanel, PostHog, PandaDoc, Cal.com, RingCentral, Help Scout, Auth0, Bitwarden, New Relic, Grafana, Descript, ElevenLabs, Replit, Make, Paddle, CrowdStrike
- **Balanced (message + visual)** (29): Atlassian, Datadog, Linear, monday.com, Slack, Zapier, Okta, Wix, Gusto, Zoho, Klaviyo, Sentry, Netlify, ActiveCampaign, Gong, Outreach, Clay, Attio, Ramp, Brex, Plaid, Lucid, Framer, Amplitude, Unbounce, Snyk, Elastic, Databricks, n8n
- **Visual-led** (13): Asana, Figma, Miro, Zoom, MongoDB, DigitalOcean, Square, Basecamp, Evernote, Cursor, Retool, Optimizely, Dialpad

| Element | Message-led (58) | Balanced (message + visual) (29) | Visual-led (13) | Average SaaS, all approaches (median) | Poorly made SaaS (median) |
|---|---|---|---|---|---|
| Message block | 21.5–39.7 [29.0] (58/58) | 20.8–29.2 [25.1] (29/29) | 8.2–20.6 [14.7] (13/13) | 27.7 (25/25) | 24.0 (25/25) |
| Headline | 12.4–23.1 [18.4] (58/58) | 12.2–16.5 [13.6] (29/29) | 5.4–14.7 [9.2] (13/13) | 16.2 (25/25) | 14.2 (25/25) |
| Subhead | 7.3–15.1 [10.9] (54/58) | 7.1–12.9 [9.5] (28/29) | 5.2–10.0 [5.8] (8/13) | 13.1 (22/25) | 14.7 (17/25) |
| Action block | 4.9–13.8 [7.0] (58/58) | 4.6–9.6 [6.2] (27/29) | 2.6–5.6 [4.1] (12/13) | 6.4 (24/25) | 6.6 (21/25) |
| Primary CTA | 3.4–6.4 [5.1] (55/58) | 2.7–5.4 [3.1] (27/29) | 2.0–3.6 [2.5] (12/13) | 4.7 (24/25) | 4.5 (20/25) |
| Secondary CTA | 2.7–6.2 [4.6] (29/58) | 1.9–4.3 [2.6] (16/29) | 1.3–2.6 [2.0] (6/13) | 4.3 (14/25) | 4.7 (6/25) |
| Hero visual | 5.6–11.8 [7.8] (17/58) | 19.3–30.5 [26.6] (29/29) | 35.9–61.9 [47.4] (13/13) | 18.5 (20/25) | 21.0 (16/25) |
| Trust strip | 4.6–8.6 [6.3] (7/58) | few pages (2/29) | 3.2–6.3 [4.3] (3/13) | 7.9 (3/25) | 9.8 (4/25) |
| Nav CTA | 0.8–1.3 [0.9] (25/58) | 0.6–0.9 [0.6] (11/29) | 0.8–1.2 [0.9] (4/13) | 1.1 (11/25) | 0.5 (5/25) |

Mean attention spread %:

| Group | Message (eyebrow + headline + subhead) | Action (hero CTAs + form) | Hero visual | Trust / proof | Header + announcement | Background / unassigned |
|---|---|---|---|---|---|---|
| Top SaaS, Message-led | 30.4 | 9.3 | 2.6 | 1.0 | 7.7 | 49.2 |
| Top SaaS, Balanced (message + visual) | 25.1 | 7.4 | 25.4 | 0.8 | 6.8 | 34.5 |
| Top SaaS, Visual-led | 14.9 | 4.1 | 46.7 | 1.0 | 7.6 | 25.7 |
| Average SaaS | 28.6 | 8.0 | 14.0 | 1.2 | 6.9 | 41.3 |
| Poorly made SaaS | 25.9 | 7.4 | 15.5 | 1.6 | 4.4 | 45.2 |

## What separates the groups (medians)

- **Desktop, message:** poorly made pages give the headline 8.5% and the message block 10.7% of predicted attention, against 13.1% and 17.5% for top SaaS (12.8% and 17.5% for average). Headline font: 45.0 px vs 64.0 px (average 60.0 px).
- **Desktop, unassigned background:** 56.5% on poorly made pages vs 47.1% on top SaaS: more attention lands on nothing in particular.
- **CTAs do not separate the groups:** action block 2.1% (top), 2.1% (average), 1.9% (poor) on desktop. A CTA share in range is necessary, not a sign of a good page.
- **Average vs top:** medians are close on almost every element; top pages show a wider spread of deliberate choices (very message-led or very visual-led), average pages cluster in the balanced middle.
- **Mobile:** the three groups are much closer to each other than on desktop; attention spread alone separates page quality poorly on a phone.
- Groups of 25 are small and the poor group is one reviewer's selection, so treat these as indications.

## Average SaaS pages

- Acuity Scheduling (https://acuityscheduling.com)
- Bonsai (https://hellobonsai.com)
- Capsule CRM (https://capsulecrm.com)
- Clockify (https://clockify.me)
- Close (https://close.com)
- Copper (https://copper.com)
- Crisp (https://crisp.chat)
- Dubsado (https://dubsado.com)
- Gorgias (https://gorgias.com)
- Groove (https://groovehq.com)
- HappyFox (https://happyfox.com)
- Harvest (https://getharvest.com)
- HoneyBook (https://honeybook.com)
- Keap (https://keap.com)
- LiveAgent (https://liveagent.com)
- LiveChat (https://livechat.com)
- Moosend (https://moosend.com)
- Nifty (https://niftypm.com)
- Omnisend (https://omnisend.com)
- Paymo (https://paymoapp.com)
- SimplyBook.me (https://simplybook.me)
- Teamwork (https://teamwork.com)
- Tidio (https://tidio.com)
- Wave (https://waveapps.com)
- Wrike (https://wrike.com)

## Poorly made SaaS pages and why each was picked

- Agile CRM (https://agilecrm.com): small headline, dated layout, screenshot dominates
- Apptivo (https://apptivo.com): cluttered: menu list, badges and small headline compete
- Axosoft (https://axosoft.com): low-contrast headline, single ghost button
- Bubbl.us (https://bubbl.us): dated; headline is a rotating fragment, visual clutter
- Commence (https://commence.com): dated layout, greyed-out visual, weak CTA contrast
- Dovico (https://dovico.com): headline over a busy photo, tiny CTAs
- Easy Projects (Birdview) (https://easyprojects.net): rebrand notice as hero; no product CTA
- eSurveysPro (https://esurveyspro.com): login form is the hero; cluttered, no single message
- Formsite (https://formsite.com): dated design; small headline squeezed beside a busy illustration
- FreeConferenceCall (https://freeconferencecall.com): sign-up form floats over decoration, headline pushed aside
- HESK (https://hesk.com): dated design; headline repeats the product name, small text
- iContact (https://icontact.com): small headline; two competing offer boxes
- KashFlow (https://kashflow.com): rotating news carousel instead of a value proposition; no sign-up CTA in the hero
- Kintone (https://kintone.com): loud colour blocks and clutter around the message
- LimeSurvey (https://limesurvey.org): small headline; tab strip and screenshot compete, CTA below the visual
- osTicket (https://osticket.com): announcement banner dominates; headline small and low, tiny CTAs
- Planio (https://plan.io): dated, dense hero with small text
- Project Insight (https://projectinsight.com): hero cropped inside a box, ghost buttons, empty lower half
- ProofHub (https://proofhub.com): dense hero text with mixed bold, underline and highlight; small CTA
- Salesboom (https://salesboom.com): text over a busy photo background, weak hierarchy
- Sendy (https://sendy.co): wall of small text; primary CTA far from the headline
- SuiteCRM (https://suitecrm.com): low-contrast text on a gradient, CTAs detached from the message
- VerticalResponse (https://verticalresponse.com): dated; small headline over a loud background
- Vision Helpdesk (https://visionhelpdesk.com): generic headline, low-contrast small text, CTAs far below the message
- Wufoo (https://wufoo.com): dated; small text, video thumbnail as visual

## Desktop: all pages

| Page | Group | Approach | Headline (H1 text) | px | H1 % | Subhead % | Primary CTA % | All CTAs % | Visual % | Trust % |
|---|---|---|---|---|---|---|---|---|---|---|
| 1Password | saas | message | Secure access for every human and AI agent | 88 | 33.3 | 5.1 | 1.2 | 2.2 | 7.5 | – |
| ActiveCampaign | saas | balanced | Run the marketing you never had time for | 66 | 16.0 | 4.6 | 0.9 | 3.7 | 41.1 | – |
| Ahrefs | saas | message | Make your business discoverable—in search, AI, and beyond | 92 | 29.0 | 9.7 | 2.5 | 4.8 | 5.2 | – |
| Airtable | saas | message | All your teams, all their workflows—connected in one workspace | 40 | 12.0 | 5.0 | 2.2 | 3.4 | – | – |
| Amplitude | saas | visual | A new era for product teams | 72 | 11.7 | – | 0.7 | 1.2 | 26.1 | – |
| Apollo | saas | message | Grow revenue with one connected GTM system | 72 | 17.9 | 3.7 | 0.8 | 3.9 | – | – |
| Asana | saas | message | The OS for human-agent teams | 102 | 22.9 | 3.0 | 0.6 | 3.6 | – | – |
| Atlassian | saas | visual | Discover the power of knowing | 64 | 7.6 | 7.9 | 2.1 | 2.1 | 43.9 | – |
| Attio | saas | balanced | Welcome to agentic revenue. | 64 | 8.5 | 3.8 | 0.8 | 1.6 | 23.3 | – |
| Auth0 | saas | message | Convert, protect, & personalize every journey | 64 | 15.2 | 7.9 | 1.3 | 2.5 | – | 3.6 |
| Basecamp | saas | visual | Manage any project, coordinate every team. Master your company with Ba | 50 | 15.7 | 3.3 | – | – | 45.6 | – |
| Bitwarden | saas | balanced | Secure every login for people, agents, and machines | 60 | 14.9 | 9.9 | 1.5 | 2.7 | 21.0 | – |
| Box | saas | balanced | Campaigns + AI | 80 | 10.7 | 8.6 | 1.5 | 2.7 | 17.0 | – |
| Brevo | saas | balanced | Turn Every Email SMS Order Interaction into a Lifetime Customer | 40 | 8.7 | 4.3 | 1.0 | 2.6 | 19.8 | 3.7 |
| Brex | saas | balanced | Finance built for speed and control. | 72 | 13.4 | 2.8 | 0.6 | 2.3 | 30.9 | – |
| Buffer | saas | message | Your social media workspace | 76 | 16.0 | 5.3 | 1.8 | 8.5 | – | 3.3 |
| Cal.com | saas | message | Where people Intro call 30m 2:00 PM 2:00 PM Booked 12:30 AM 12:30 PM f | 80 | 22.6 | 1.9 | 3.2 | 5.5 | 8.8 | – |
| Calendly | saas | balanced | All the work around meetings, handled. | 72 | 16.2 | 5.0 | 1.8 | 3.5 | 16.7 | – |
| Canva | saas | balanced | What will you design today? | 80 | 11.2 | 4.6 | 2.1 | 2.1 | 31.5 | – |
| Clay | saas | visual | Build systems to grow revenue | 88 | 11.5 | 2.2 | 0.6 | 1.0 | 60.4 | – |
| ClickUp | saas | visual | One Workspace built to think and work | 60 | 8.1 | 5.3 | 1.5 | 2.7 | 33.6 | – |
| Cloudflare | saas | message | Everything we learned from powering 20% of the Internet—yours by defau | 56 | 17.3 | 3.9 | 1.7 | 1.7 | – | – |
| CrowdStrike | saas | visual | Start free trial | 16 | 17.7 | 7.1 | 0.6 | 0.6 | 83.2 | – |
| Cursor | saas | visual | Cursor is your coding agent for building ambitious software. | 26 | 2.0 | – | 1.3 | 2.4 | 64.5 | – |
| Databricks | saas | visual | One database for AI, apps and agents | 56 | 8.4 | 4.6 | 0.7 | 1.3 | 29.5 | 2.9 |
| Datadog | saas | visual | AI-Powered Observability and Security | 68 | 9.4 | 4.4 | 2.2 | 4.0 | 60.7 | – |
| Deel | saas | visual | Hire, manage, pay, & equip anyone, anywhere. | 60 | 12.9 | 0.9 | 1.5 | 1.5 | 38.4 | – |
| Descript | saas | balanced | AI-editing for every kind of video | 88 | 24.2 | 5.6 | 1.9 | 1.9 | 27.0 | – |
| Dialpad | saas | balanced | The AI platform for customer experience | 48 | 7.9 | 5.0 | 0.4 | 0.7 | 10.2 | 3.4 |
| DigitalOcean | saas | visual | AI-Native Cloud | 48 | 4.0 | 1.9 | 1.0 | 2.3 | 28.8 | 7.1 |
| Docusign | saas | message | Everything you need to agree | 80 | 11.6 | 1.8 | 0.9 | 6.5 | – | 4.8 |
| Dropbox | saas | visual | Store, share, and get more done with a smarter Dropbox | 40 | 9.6 | 7.0 | 1.6 | 1.6 | 43.2 | – |
| Elastic | saas | balanced | Elasticsearch: The search database for AI | 64 | 18.1 | 3.2 | 0.7 | 1.6 | 17.9 | 6.9 |
| ElevenLabs | saas | visual | Bringing technology to life | 48 | 3.9 | 3.8 | 0.6 | 1.5 | 20.3 | – |
| Evernote | saas | visual | Your second brain | 72 | 6.2 | 5.0 | 2.8 | 2.8 | 42.8 | – |
| Expensify | saas | visual | The easiest way to do your expenses | 52 | 6.6 | 1.7 | 1.4 | 4.9 | 26.3 | – |
| Figma | saas | visual | The full-stack creative canvas | 56 | 5.8 | – | 1.3 | 1.3 | 46.1 | – |
| Framer | saas | visual | Framer is the pro website builder with a world-class design agent | 54 | 12.2 | 2.2 | 0.4 | 1.0 | 46.5 | – |
| Freshworks | saas | balanced | Turn operational complexity into coordinated action | 72 | 21.7 | 8.6 | 0.5 | 1.0 | 30.6 | 3.3 |
| GitHub | saas | message | Software still starts with you | 56 | 9.8 | – | 1.6 | 8.7 | – | – |
| GitLab | saas | message | Speed you can trust, all the way to production | 96 | 30.1 | 2.7 | 2.3 | 2.3 | – | – |
| Gong | saas | balanced | REVENUE AI BUILT TO CLOSE DEALS FASTER, PREDICT PIPELINE RISK, AUTOMAT | 60 | 14.3 | 3.9 | 0.9 | 1.3 | 30.7 | 1.5 |
| Grafana | saas | message | AI for observability. Observability for AI. One platform for both. | 60 | 19.9 | 1.8 | 1.6 | 5.0 | – | 6.8 |
| Grammarly | saas | visual | Think big. We’ll take care of the details. | 46 | 4.8 | 2.3 | 2.9 | 5.3 | 30.3 | – |
| Gusto | saas | balanced | Hire, pay, and grow like a pro. | 110 | 23.8 | 4.2 | 1.2 | 2.3 | 45.3 | – |
| Help Scout | saas | message | Where support teams turn conversations into resolutions intelligence r | 89 | 38.0 | 3.5 | 0.9 | 1.4 | – | – |
| HubSpot | saas | balanced | HubSpot: The Customer Relationship Harness | 65 | 18.3 | 7.3 | 1.9 | 3.6 | 15.4 | – |
| Intercom | saas | message | A complete system for AI and human customer service | 80 | 27.6 | 5.7 | 0.8 | 1.4 | 2.9 | – |
| Klaviyo | saas | balanced | Your AI marketing agent, always a step ahead | 80 | 23.9 | 2.9 | 0.8 | 2.6 | 22.1 | – |
| Linear | saas | balanced | The product development system for teams and agents | 64 | 20.7 | 1.6 | – | – | 33.2 | – |
| Lucid | saas | balanced | Transform your business with AI | 64 | 13.9 | 5.6 | 1.6 | 1.6 | 32.6 | – |
| Mailchimp | saas | message | Turn ideas into emails & SMS that connect | 64 | 13.8 | 4.9 | 2.4 | 2.4 | – | – |
| Make | saas | balanced | Build and manage AI agents and automations in one visual landscape | 60 | 21.0 | 6.5 | 0.9 | 1.9 | 14.8 | – |
| Miro | saas | visual | Human collaboration at the speed of AI | 56 | 10.6 | 4.3 | – | – | 65.8 | – |
| Mixpanel | saas | visual | Build like your customers are right beside you | 48 | 10.2 | 3.7 | 0.7 | 1.7 | 35.8 | – |
| monday.com | saas | balanced | The AI workspace for people and agents | 56 | 8.7 | 5.3 | 0.9 | 0.9 | 22.4 | 8.8 |
| MongoDB | saas | visual | EVERY SCALE. EVERY AGENT. ONE PLATFORM | 86 | 9.5 | – | 1.2 | 1.8 | 28.4 | – |
| n8n | saas | visual | Build the agent. Understand its workflow. | 64 | 12.4 | 4.4 | 1.0 | 2.0 | 34.7 | – |
| Netlify | saas | balanced | Push your ideas to the web | 64 | 9.1 | 2.9 | 0.5 | 1.1 | 23.1 | 3.1 |
| New Relic | saas | balanced | OBSERVABILITY THAT PREDICTS | 132 | 22.5 | 5.0 | 0.8 | 1.4 | 30.3 | – |
| Notion | saas | balanced | Where teams and agents Think together. | 96 | 28.3 | 2.9 | 1.1 | 2.1 | 48.0 | – |
| Okta | saas | balanced | Bring agents out of the shadows | 64 | 11.2 | 4.4 | 1.4 | 2.4 | 17.7 | – |
| Optimizely | saas | visual | You're free to grow | 117 | 17.4 | 3.2 | 0.8 | 0.8 | 47.6 | – |
| Outreach | saas | visual | Stop buying software. Start hiring AI agents. | 48 | 9.0 | 6.0 | 1.2 | 2.5 | 52.0 | – |
| Paddle | saas | message | Sell globally. Grow without the complexity. | 64 | 14.1 | 7.1 | 1.7 | 2.6 | – | 3.3 |
| PagerDuty | saas | message | Watch Paige work. Watch Detect. Resolve. Work. | 16 | 20.0 | – | 1.7 | 1.7 | – | – |
| PandaDoc | saas | message | Growing your business starts with your agreements | 70 | 23.8 | 4.9 | 2.3 | 2.3 | 8.1 | 4.8 |
| Pipedrive | saas | balanced | The easy and effective CRM for closing deals | 52 | 8.5 | 5.2 | 0.6 | 1.4 | 24.9 | – |
| Plaid | saas | balanced | Turn data into revolutionary financial products | 76 | 22.8 | 6.0 | 1.3 | 2.7 | 45.8 | 1.1 |
| PostHog | saas | visual | Your product's context layer | 36 | 2.3 | 4.6 | 1.2 | 1.9 | 29.5 | – |
| Postman | saas | visual | API context_ engineering for your agents | 63 | 8.0 | 2.7 | – | 2.5 | 27.2 | – |
| Ramp | saas | visual | Time is money. Save both. | 64 | 5.3 | 1.7 | 1.2 | 3.9 | 35.8 | – |
| Replit | saas | message | What will you build? | 64 | 6.6 | 1.6 | – | 10.5 | – | – |
| Retool | saas | balanced | Secure your vibe-coded apps | 72 | 8.3 | 0.8 | 0.9 | 2.2 | 16.8 | – |
| RingCentral | saas | balanced | The Agentic Voice AI platform to drive customer outcomes | 60 | 12.2 | 4.7 | 0.4 | 1.1 | 25.4 | 2.1 |
| Rippling | saas | visual | Manage your entire workforce on one system | 48 | 6.8 | 4.0 | 1.0 | 4.2 | 33.2 | – |
| Sentry | saas | balanced | Code breaks, fix it faster | 88 | 14.9 | 7.1 | 0.9 | 1.7 | 27.3 | – |
| Shopify | saas | message | Be the next AI all-star | 96 | 14.8 | 3.1 | 0.6 | 0.6 | – | – |
| Slack | saas | balanced | All your people and AI agents working together | 64 | 16.9 | 2.1 | 1.8 | 3.9 | 30.2 | 2.0 |
| Snowflake | saas | message | The Agentic Enterprise Runs on Snowflake | 80 | 22.3 | 4.8 | 0.9 | 1.9 | 13.8 | – |
| Snyk | saas | visual | Every AI App You Build | 104 | 10.0 | 7.0 | – | – | 44.0 | – |
| Square | saas | visual | Local legend or global icon. Make it big on your block. | 81 | 22.5 | – | 1.0 | 2.1 | 95.4 | 3.2 |
| Squarespace | saas | visual | A website makes it real | 64 | 8.1 | 0.6 | 1.9 | 1.9 | 29.3 | – |
| Stripe | saas | message | Financial infrastructure to grow your revenue. Accept payments, offer  | 48 | 29.7 | – | 0.9 | 2.4 | – | 2.5 |
| Supabase | saas | visual | Build in a weekend Scale to millions | 46 | 7.3 | 2.3 | 0.9 | 2.0 | 31.4 | – |
| SurveyMonkey | saas | balanced | Humans still matter. Listen to them. | 92 | 23.5 | 4.3 | 1.7 | 1.7 | 29.2 | – |
| Todoist | saas | balanced | The task system you’ll actually stick with | 55 | 13.9 | 7.9 | 1.9 | 1.9 | 20.3 | – |
| Trello | saas | balanced | Capture, organize, and tackle your to-dos from anywhere. | 48 | 14.3 | 4.1 | 1.2 | 3.7 | 32.6 | – |
| Twilio | saas | balanced | The platform for conversations in the AI era | 56 | 13.5 | 6.3 | 0.5 | 1.1 | 18.5 | – |
| Typeform | saas | message | Your favorite forms. Now with AI automation. | 80 | 20.8 | 5.6 | 1.3 | 1.3 | 3.0 | – |
| Unbounce | saas | visual | Three ways to build. Zero reasons to wait. | 52 | 6.1 | 4.1 | 2.1 | 2.1 | 50.7 | – |
| Vercel | saas | visual | Agentic Infrastructure | 64 | 6.4 | – | 0.3 | 0.8 | 52.8 | 2.2 |
| Webflow | saas | visual | Build for what’s next | 80 | 7.7 | 2.2 | 0.6 | 0.6 | 30.0 | – |
| Wix | saas | balanced | Create your future on the leading website builder | 82 | 25.8 | 1.8 | 1.7 | 1.7 | 32.5 | – |
| Workday | saas | message | AI that gets work done right. | 68 | 13.3 | 4.9 | – | 3.9 | – | – |
| Zapier | saas | visual | Welcome to automation in the agentic era | 56 | 11.4 | 2.0 | 1.2 | 2.9 | 28.7 | – |
| Zendesk | saas | message | Build for better outcomes | 68 | 10.0 | 3.3 | 0.8 | 3.3 | – | – |
| Zoho | saas | balanced | Your life's work, powered by our life's work | 44 | 8.7 | 6.6 | 1.3 | 1.3 | 19.8 | – |
| Zoom | saas | visual | Find out what's possible when work connects | 54 | 10.1 | 2.0 | 1.2 | 2.2 | 36.9 | – |
| ZoomInfo | saas | message | The best GTM data. Orchestrated anywhere. Paid for once. | 72 | 26.6 | 4.3 | 0.7 | 3.6 | – | 5.3 |
| Acuity Scheduling | average | balanced | Scheduling software to power exceptional client experiences | 40 | 9.0 | 4.5 | 2.3 | 4.2 | 23.6 | – |
| Bonsai | average | balanced | The unified platform for service businesses | 56 | 11.0 | 3.6 | 2.0 | 2.0 | 14.2 | – |
| Capsule CRM | average | balanced | Simple to start. Built for growth. | 64 | 8.7 | 5.4 | 0.4 | 0.4 | 18.7 | 2.3 |
| Clockify | average | balanced | The most popular time tracker for teams | 45 | 13.1 | 6.7 | 2.7 | 2.7 | 23.1 | – |
| Close | average | visual | The CRM that sells with you | 60 | 6.5 | 6.9 | 1.4 | 8.9 | 42.7 | – |
| Copper | average | balanced | The CRM that helps you be there for your clients, every step of the wa | 60 | 20.1 | – | 1.6 | 2.1 | 36.4 | – |
| Crisp | average | balanced | Augment your customer experience. AI made to support your team & custo | 48 | 13.5 | – | 2.9 | 2.9 | 22.2 | – |
| Dubsado | average | balanced | Book clients, send contracts and get paid | 70 | 12.8 | 6.8 | 2.5 | 4.8 | 36.5 | – |
| Gorgias | average | visual | Deliver the best customer experience | 64 | 9.7 | 2.0 | 0.2 | 0.4 | 25.8 | – |
| Groove | average | balanced | AI customer support that actually resolves tickets | 60 | 15.0 | 7.2 | 1.1 | 1.9 | 26.4 | – |
| HappyFox | average | visual | Agentic help desk for demanding support workloads. Support customers a | 40 | 10.1 | – | 0.5 | 1.3 | 60.6 | – |
| Harvest | average | balanced | Turn hours into estimates | 70 | 13.8 | 3.7 | 1.6 | 4.5 | 24.7 | 8.0 |
| HoneyBook | average | balanced | Manage every client, project, and payment all in one place. | 64 | 14.9 | 6.5 | 2.0 | 2.0 | 12.1 | – |
| Keap | average | visual | Put Your Business Growth on Autopilot | 40 | 4.9 | 5.1 | 1.3 | 2.8 | 33.8 | – |
| LiveAgent | average | visual | Help desk and live chat with AI agents | 60 | 8.0 | 5.9 | 0.3 | 0.8 | 32.4 | 0.7 |
| LiveChat | average | message | Live chat software that grows sales | 128 | 34.4 | 6.5 | 1.8 | 1.8 | 17.9 | – |
| Moosend | average | balanced | Send, Convert, Repeat: Delight your audience in every email​ | 44 | 9.6 | 5.6 | 0.8 | 0.8 | 27.3 | – |
| Nifty | average | message | The Work Built Around Visibility | 62 | 12.7 | 4.1 | 2.1 | 4.3 | – | 7.4 |
| Omnisend | average | visual | Email & SMS marketing | 80 | 13.8 | 2.4 | 0.6 | 1.8 | 33.7 | 1.1 |
| Paymo | average | balanced | Small Businesses. Big Results. | 56 | 11.4 | 7.3 | 0.9 | 4.6 | 36.3 | – |
| SimplyBook.me | average | balanced | Online Booking System for all service based industries | 50 | 13.8 | 4.4 | 1.5 | 3.0 | 21.0 | – |
| Teamwork | average | balanced | Most tools track work. We make it profitable. | 58 | 12.4 | 6.4 | 2.8 | 6.7 | 13.6 | – |
| Tidio | average | message | What did your last 100 conversations earn you? | 72 | 27.8 | 3.8 | 1.2 | 2.1 | – | 1.8 |
| Wave | average | balanced | Clear books. Conﬁdent decisions. | 72 | 15.1 | 6.6 | 0.8 | 0.8 | 20.4 | – |
| Wrike | average | balanced | Deliver work, powered by humans and agents | 64 | 15.4 | 3.7 | 0.9 | 0.9 | 15.5 | 3.8 |
| Agile CRM | poor | visual | Sell & Market Like the Fortune 500 | 36 | 3.0 | 1.2 | 0.9 | 4.1 | 49.2 | – |
| Apptivo | poor | visual | Accelerate your business Growth. | 42 | 3.4 | 1.1 | 0.8 | 1.9 | 15.5 | 8.2 |
| Axosoft | poor | visual | Axosoft is the Scrum software for agile teams | 38 | 3.7 | 2.8 | 2.5 | 2.5 | 34.6 | – |
| Bubbl.us | poor | visual | create a family tree. | 28 | 2.5 | – | 5.8 | 5.8 | 38.6 | 4.0 |
| Commence | poor | visual | Some CRM’s Manage Sales Ours Gets You Sales! | 36 | 6.0 | 3.2 | 1.1 | 1.9 | 19.3 | – |
| Dovico | poor | visual | People helping people grow | 80 | 14.4 | – | 1.4 | 2.4 | 61.3 | 6.0 |
| Easy Projects (Birdview) | poor | balanced | Easy Projects is now Birdview PSA | 50 | 7.1 | 9.0 | 0.4 | 0.4 | 8.8 | 6.6 |
| eSurveysPro | poor | visual | New User? | 30 | 0.4 | – | – | 3.3 | 42.4 | – |
| Formsite | poor | visual | Easily create professional online forms, surveys and workflows! | 38 | 6.9 | – | 0.9 | 0.9 | 40.6 | – |
| FreeConferenceCall | poor | message | Free, High-Quality Conference Call Services | 48 | 11.2 | 5.8 | 1.8 | 12.3 | – | – |
| HESK | poor | visual | Help Desk Software Hesk | 32 | 1.5 | 2.3 | 1.4 | 1.4 | 16.9 | – |
| iContact | poor | visual | Easy email marketing software for your small business | 40 | 8.8 | – | 1.8 | 1.8 | 25.9 | – |
| KashFlow | poor | message | Online Accounting Software Made Simple | 46 | 11.6 | 16.3 | 0.5 | 0.5 | – | – |
| Kintone | poor | balanced | All your team's workflows & AI in one place with Kintone | 66 | 17.9 | 3.1 | 0.9 | 3.3 | 34.5 | 6.3 |
| LimeSurvey | poor | visual | Free online survey tool Create professional surveys 🇩🇪 HOSTED IN GERMA | 24 | 10.7 | – | 1.2 | 1.2 | 40.1 | – |
| osTicket | poor | balanced | Get The World’s Most Popular Customer Support Software | 48 | 11.2 | 5.7 | 0.8 | 0.8 | 8.7 | – |
| Planio | poor | visual | Engineer Project Success | 43 | 5.1 | 4.7 | 1.6 | 5.1 | 34.2 | – |
| Project Insight | poor | message | Connect your data. Trust your reports. | 54 | 11.0 | 11.0 | 2.0 | 3.5 | – | – |
| ProofHub | poor | balanced | The one place for all your projects, teams and communications | 80 | 20.6 | 11.8 | 1.6 | 1.6 | 29.6 | – |
| Salesboom | poor | message | Blast your business off with easy to use Cloud CRM Software. Fully Cus | 45 | 17.1 | – | 2.2 | 3.0 | – | – |
| Sendy | poor | visual | Send Newsletters Without SaaS Lock‑In | 60 | 6.8 | 2.8 | 0.4 | 1.0 | 34.3 | – |
| SuiteCRM | poor | message | Whatever your goal, SuiteCRM offers comprehensive insights that will h | 55 | 30.0 | – | 1.0 | 1.9 | 3.7 | – |
| VerticalResponse | poor | balanced | Easy email marketing to communicate with your customers | 40 | 8.5 | 4.0 | 1.5 | 4.9 | 17.2 | – |
| Vision Helpdesk | poor | message | Customer Service Software | 60 | 5.7 | 1.7 | 1.0 | 1.9 | – | – |
| Wufoo | poor | message | Easy-to-Use Online Form Builder For Every Organization | 52 | 17.9 | 7.9 | 1.2 | 2.2 | 12.9 | – |

## Mobile: all pages

| Page | Group | Approach | Headline (H1 text) | px | H1 % | Subhead % | Primary CTA % | All CTAs % | Visual % | Trust % |
|---|---|---|---|---|---|---|---|---|---|---|
| 1Password | saas | message | Secure access for every human and AI agent | 48 | 32.5 | 9.1 | 4.5 | 9.0 | 6.3 | – |
| ActiveCampaign | saas | balanced | Run the marketing you never had time for | 40 | 13.3 | 13.8 | 2.9 | 8.9 | 31.9 | – |
| Ahrefs | saas | message | Make your business discoverable—in search, AI, and beyond | 48 | 30.5 | 17.1 | 6.6 | 12.8 | – | – |
| Airtable | saas | message | All your teams, all their workflows—connected in one workspace | 32 | 18.6 | 8.6 | 7.0 | 15.1 | – | – |
| Amplitude | saas | balanced | A new era for product teams | 44 | 12.8 | 10.4 | 2.2 | 4.4 | 15.3 | – |
| Apollo | saas | message | Grow revenue with one connected GTM system | 44 | 22.6 | 8.2 | 5.6 | 16.9 | – | – |
| Asana | saas | visual | The OS for human-agent teams | 48 | 14.7 | 5.9 | 2.1 | 9.0 | 70.5 | – |
| Atlassian | saas | balanced | Discover the power of knowing | 44 | 12.4 | 16.9 | 4.1 | 4.1 | 30.8 | – |
| Attio | saas | balanced | Welcome to agentic revenue. | 40 | 12.2 | 7.1 | 4.2 | 15.0 | 22.9 | – |
| Auth0 | saas | message | Convert, protect, & personalize every journey | 44 | 21.8 | 21.6 | 2.3 | 5.2 | – | 4.8 |
| Basecamp | saas | visual | Manage any project, coordinate every team. Master your company with Ba | 28 | 15.5 | 4.9 | – | – | 47.9 | – |
| Bitwarden | saas | message | Secure every login for people, agents, and machines | 32 | 15.1 | 25.9 | 3.1 | 5.4 | – | – |
| Box | saas | message | Content + AI | 48 | 7.0 | 11.1 | 5.1 | 9.7 | 3.1 | – |
| Brevo | saas | message | Turn Every Email SMS Order Interaction into a Lifetime Customer | 28 | 17.2 | 18.8 | 8.0 | 16.7 | 7.9 | – |
| Brex | saas | balanced | Finance built for speed and control. | 36 | 10.2 | 6.5 | 1.0 | 6.0 | 31.2 | 12.7 |
| Buffer | saas | message | Your social media workspace | 40 | 12.2 | 7.1 | 7.7 | 23.2 | 2.0 | 10.6 |
| Cal.com | saas | message | Where people Intro call 30m 2:30 PM 2:30 PM Booked 12:30 AM 12:30 PM f | 42 | 21.4 | 4.0 | 8.0 | 14.8 | 7.8 | – |
| Calendly | saas | message | All the work around meetings, handled. | 40 | 15.9 | 12.7 | 5.2 | 11.7 | – | 3.5 |
| Canva | saas | message | What will you design today? | 45 | 17.4 | 4.8 | 4.3 | 4.3 | 4.9 | – |
| Clay | saas | balanced | Build systems to grow revenue | 42 | 12.8 | 9.9 | 2.6 | 4.6 | 22.4 | – |
| ClickUp | saas | message | One Workspace built to think and work | 34 | 11.3 | 6.6 | 5.5 | 5.5 | – | 4.4 |
| Cloudflare | saas | message | Everything we learned from powering 20% of the Internet—yours by defau | 40 | 26.4 | 16.2 | 7.1 | 7.1 | – | – |
| CrowdStrike | saas | message | Virtual Event | 16 | 18.7 | 11.6 | 1.6 | 1.6 | – | – |
| Cursor | saas | visual | Cursor is your coding agent for building ambitious software. | 24 | 7.5 | – | 2.7 | 2.7 | 61.9 | – |
| Databricks | saas | balanced | One database for AI, apps and agents | 44 | 20.7 | 6.9 | 2.9 | 4.4 | 29.7 | – |
| Datadog | saas | balanced | AI-Powered Observability and Security | 38 | 16.2 | 6.5 | 4.8 | 9.7 | 23.8 | – |
| Deel | saas | message | Hire, manage, pay, & equip anyone, anywhere. | 38 | 17.6 | 3.0 | 4.9 | 4.9 | – | – |
| Descript | saas | message | AI-editing for every kind of video | 48 | 22.6 | 17.0 | 4.2 | 4.2 | 16.7 | – |
| Dialpad | saas | visual | The AI platform for customer experience | 32 | 12.5 | 9.8 | 1.4 | 2.3 | 47.4 | – |
| DigitalOcean | saas | visual | AI-Native Cloud | 28 | 2.7 | 5.7 | 4.9 | 10.3 | 30.9 | 8.3 |
| Docusign | saas | message | Everything you need to agree | 58 | 22.7 | 6.5 | 3.2 | 14.1 | – | – |
| Dropbox | saas | message | Store, share, and get more done with a smarter Dropbox | 36 | 22.3 | 19.9 | 6.6 | 6.6 | – | – |
| Elastic | saas | balanced | Elasticsearch: The search database for AI | 32 | 17.5 | 7.1 | 3.0 | 7.2 | 18.2 | – |
| ElevenLabs | saas | message | Bringing technology to life | 36 | 7.6 | 14.6 | 1.6 | 4.8 | 6.6 | – |
| Evernote | saas | visual | Your second brain | 36 | 4.2 | 10.9 | 6.0 | 6.0 | 35.9 | – |
| Expensify | saas | message | The easiest way to do your expenses | 36 | 10.4 | – | 4.3 | 15.5 | – | – |
| Figma | saas | visual | The full-stack creative canvas | 36 | 8.2 | – | 4.1 | 4.1 | 57.9 | – |
| Framer | saas | balanced | Framer is the pro website builder with a world-class design agent | 36 | 16.4 | 8.9 | 1.5 | 1.5 | 27.3 | – |
| Freshworks | saas | message | Turn operational complexity into coordinated action | 48 | 41.7 | 11.5 | 2.1 | 2.1 | – | – |
| GitHub | saas | message | Software still starts with you | 36 | 13.1 | – | 5.1 | 25.3 | – | – |
| GitLab | saas | message | Speed you can trust, all the way to production | 48 | 26.9 | 8.0 | 6.9 | 6.9 | – | – |
| Gong | saas | balanced | REVENUE AI BUILT TO CLOSE DEALS FASTER, PREDICT PIPELINE RISK, AUTOMAT | 36 | 11.1 | 14.8 | 7.5 | 9.0 | 33.7 | – |
| Grafana | saas | message | AI for observability. Observability for AI. One platform for both. | 48 | 44.7 | 4.1 | 3.8 | 7.0 | – | – |
| Grammarly | saas | message | Think big. We’ll take care of the details. | 30 | 7.5 | 8.7 | 7.4 | 16.5 | – | – |
| Gusto | saas | balanced | Hire, pay, and grow like a pro. | 52 | 13.4 | 11.5 | 5.8 | 12.0 | 26.6 | – |
| Help Scout | saas | message | Where support teams turn conversations into resolutions intelligence r | 45 | 27.1 | 16.3 | 7.3 | 12.1 | – | – |
| HubSpot | saas | message | HubSpot: The Customer Relationship Harness | 40 | 19.3 | 33.2 | 5.2 | 10.5 | – | – |
| Intercom | saas | message | A complete system for AI and human customer service | 40 | 18.8 | 6.3 | 2.8 | 4.6 | – | – |
| Klaviyo | saas | balanced | Your AI marketing agent, always a step ahead | 40 | 17.8 | 12.2 | 1.5 | 5.6 | 17.7 | – |
| Linear | saas | balanced | The product development system for teams and agents | 38 | 29.4 | 7.5 | – | – | 32.5 | – |
| Lucid | saas | balanced | Transform your business with AI | 32 | 7.5 | 9.6 | 3.2 | 3.2 | 21.0 | – |
| Mailchimp | saas | message | Turn ideas into emails & SMS that connect | 36 | 14.1 | 7.2 | 5.4 | 5.4 | – | – |
| Make | saas | message | Build and manage AI agents and automations in one visual landscape | 42 | 32.2 | 17.8 | 5.1 | 10.1 | – | – |
| Miro | saas | visual | Human collaboration at the speed of AI | 32 | 1.8 | 2.6 | 1.1 | 1.1 | 22.1 | – |
| Mixpanel | saas | message | Build faster, with direction | 36 | 11.9 | 14.9 | 2.5 | 5.2 | – | – |
| monday.com | saas | balanced | People and agents working as one team | 33 | 10.9 | 6.4 | 6.4 | 21.0 | 18.7 | – |
| MongoDB | saas | visual | EVERY SCALE. EVERY AGENT. ONE PLATFORM | 33 | 5.4 | – | 3.0 | 4.1 | 36.2 | – |
| n8n | saas | balanced | Build the agent. Understand its workflow. | 48 | 20.4 | 9.4 | 2.7 | 5.2 | 29.1 | – |
| Netlify | saas | balanced | Push your ideas to the web | 41 | 11.2 | 10.2 | 2.4 | 4.6 | 12.3 | – |
| New Relic | saas | message | OBSERVABILITY THAT PREDICTS | 60 | 16.7 | 14.8 | 7.2 | 12.9 | 10.2 | – |
| Notion | saas | message | Where teams and agents Think together. | 42 | 18.3 | 7.0 | 5.3 | 10.1 | – | 9.0 |
| Okta | saas | balanced | Bring agents out of the shadows | 32 | 12.8 | 5.9 | 3.1 | 6.2 | 29.6 | – |
| Optimizely | saas | visual | You're free to grow | 70 | 20.5 | 14.5 | 2.1 | 2.1 | 83.8 | – |
| Outreach | saas | balanced | Stop buying software. Start hiring AI agents. | 40 | 22.6 | 14.8 | 4.8 | 9.4 | 57.3 | – |
| Paddle | saas | message | Sell globally. Grow without the complexity. | 56 | 27.0 | 10.2 | 2.9 | 4.4 | – | 8.2 |
| PagerDuty | saas | message | Watch Paige work. Watch Detect. Resolve. Work. | 16 | 28.1 | – | 5.0 | 5.0 | – | – |
| PandaDoc | saas | message | Growing your business starts with your agreements | 36 | 23.3 | 9.2 | 6.8 | 6.8 | 5.6 | 6.3 |
| Pipedrive | saas | message | The easy and effective CRM for closing deals | 32 | 8.1 | 15.4 | 3.6 | 5.5 | – | – |
| Plaid | saas | balanced | Turn data into revolutionary financial products | 32 | 16.5 | 8.3 | 2.7 | 5.5 | 32.5 | 8.3 |
| PostHog | saas | message | Your product's context layer | 30 | 8.4 | 10.8 | 5.2 | 10.4 | – | – |
| Postman | saas | message | API context_ engineering for your agents | 58 | 29.5 | 8.2 | – | 7.8 | – | – |
| Ramp | saas | balanced | Time is money. Save both. | 40 | 10.6 | 6.9 | 6.1 | 20.2 | 28.5 | – |
| Replit | saas | message | What will you build? | 32 | 5.3 | 3.9 | – | 15.2 | – | – |
| Retool | saas | visual | Secure your vibe-coded apps | 40 | 10.2 | – | 1.7 | 3.4 | 28.0 | 2.0 |
| RingCentral | saas | message | The Agentic Voice AI platform to drive customer outcomes | 39 | 29.5 | 12.0 | 1.9 | 4.0 | 13.6 | – |
| Rippling | saas | message | Manage your entire workforce on one system | 36 | 15.7 | 10.6 | 5.1 | 16.2 | – | – |
| Sentry | saas | balanced | Code breaks, fix it faster | 50 | 13.8 | 12.7 | 2.8 | 4.5 | 17.7 | – |
| Shopify | saas | message | Be the next AI all-star | 56 | 14.2 | 5.5 | 6.3 | 20.3 | – | – |
| Slack | saas | balanced | All your people and AI agents working together | 32 | 13.7 | 7.2 | 9.1 | 18.6 | 10.5 | – |
| Snowflake | saas | message | The Agentic Enterprise Runs on Snowflake | 46 | 18.4 | 15.2 | 3.5 | 6.7 | 10.9 | – |
| Snyk | saas | balanced | Unleash AI Innovators — Securely | 40 | 14.6 | 17.0 | – | – | 30.5 | – |
| Square | saas | visual | Local legend or global icon. Make it big on your block. | 56 | 39.2 | – | 2.3 | 5.0 | 97.1 | 4.3 |
| Squarespace | saas | message | A website makes it real | 42 | 11.0 | 1.6 | 3.8 | 3.8 | – | – |
| Stripe | saas | message | Financial infrastructure to grow your revenue. | 34 | 9.6 | – | 8.0 | 15.7 | – | – |
| Supabase | saas | message | Build in a weekend Scale to millions | 34 | 8.2 | 10.7 | 2.7 | 5.0 | – | – |
| SurveyMonkey | saas | message | Humans still matter. Listen to them. | 60 | 30.3 | 14.6 | 3.5 | 3.5 | 16.0 | – |
| Todoist | saas | message | The task system you’ll actually stick with | 37 | 17.2 | 19.4 | 4.2 | 4.2 | 13.4 | – |
| Trello | saas | message | Capture, organize, and tackle your to-dos from anywhere. | 32 | 19.8 | 9.0 | 6.1 | 6.1 | 4.6 | – |
| Twilio | saas | message | The platform for conversations in the AI era | 34 | 13.6 | 20.9 | 2.4 | 3.6 | 6.6 | – |
| Typeform | saas | message | Your favorite forms. Now with AI automation. | 48 | 28.9 | 12.6 | 2.5 | 2.5 | – | – |
| Unbounce | saas | balanced | Three ways to build. Zero reasons to wait. | 32 | 10.9 | 19.1 | 6.3 | 6.3 | 23.3 | – |
| Vercel | saas | message | Agentic Infrastructure | 48 | 18.6 | 4.3 | 5.8 | 10.3 | – | – |
| Webflow | saas | message | Build for what’s next | 46 | 10.7 | 10.9 | 2.8 | 2.8 | – | – |
| Wix | saas | balanced | Create your future on the leading website builder | 41 | 19.8 | 5.7 | 5.0 | 9.9 | 19.3 | – |
| Workday | saas | message | AI that gets work done right. | 32 | 8.8 | 12.7 | – | 4.2 | – | – |
| Zapier | saas | balanced | Welcome to automation in the agentic era | 40 | 13.6 | – | 3.1 | 3.1 | 20.1 | – |
| Zendesk | saas | message | Build for better outcomes | 43 | 14.8 | 14.8 | 3.9 | 15.5 | 11.8 | – |
| Zoho | saas | balanced | Your life's work, powered by our life's work | 32 | 14.1 | 16.1 | 6.2 | 6.2 | 29.8 | – |
| Zoom | saas | visual | Find out what's possible when work connects | 34 | 9.2 | 5.3 | 3.4 | 5.5 | 39.1 | – |
| ZoomInfo | saas | message | The AI platform for go‑to‑market teams | 48 | 21.8 | 7.4 | 6.5 | 20.2 | – | – |
| Acuity Scheduling | average | balanced | Scheduling software to power exceptional client experiences | 32 | 14.8 | 10.5 | 6.5 | 12.4 | 17.6 | – |
| Bonsai | average | message | The unified platform for service businesses | 40 | 18.4 | 8.2 | 3.9 | 3.9 | 3.3 | – |
| Capsule CRM | average | balanced | Simple to start. Built for growth. | 40 | 11.7 | 21.9 | 2.6 | 2.6 | 27.3 | – |
| Clockify | average | balanced | The most popular time tracker for teams | 28 | 8.8 | 9.1 | 5.6 | 5.6 | 22.6 | – |
| Close | average | balanced | The CRM that sells with you | 38 | 10.8 | 10.2 | 2.7 | 18.0 | 19.3 | – |
| Copper | average | balanced | The CRM that helps you be there for your clients, every step of the wa | 36 | 25.2 | – | 2.6 | 3.8 | 22.3 | – |
| Crisp | average | balanced | Augment your customer experience. AI made to support your team & custo | 30 | 22.9 | – | – | – | 14.0 | – |
| Dubsado | average | message | Book clients, send contracts and get paid | 47 | 19.2 | 13.9 | 4.3 | 8.2 | 15.2 | – |
| Gorgias | average | balanced | Deliver the best customer experience | 32 | 10.7 | 9.5 | 1.8 | 3.7 | 31.0 | – |
| Groove | average | balanced | AI customer support that actually resolves tickets | 36 | 16.8 | 15.8 | 3.1 | 5.4 | 23.6 | – |
| HappyFox | average | message | Agentic help desk for demanding support workloads. Support customers a | 36 | 37.5 | – | 5.3 | 9.7 | 18.8 | – |
| Harvest | average | message | Turn hours into estimates | 48 | 17.2 | 9.7 | 6.4 | 21.1 | 11.4 | – |
| HoneyBook | average | balanced | Manage every client, project, and payment all in one place. | 36 | 16.7 | 11.2 | 3.8 | 3.8 | 18.8 | – |
| Keap | average | balanced | Put Your Business Growth on Autopilot | 26 | 6.3 | 13.6 | 9.4 | 14.5 | 17.1 | – |
| LiveAgent | average | message | Help desk and live chat with AI agents | 48 | 17.1 | 15.3 | 1.6 | 3.4 | – | 6.1 |
| LiveChat | average | balanced | Live chat software for your team and AI | 40 | 16.2 | 19.9 | 7.2 | 7.2 | 18.3 | – |
| Moosend | average | message | Send, Convert, Repeat: Delight your audience in every email​ | 36 | 28.4 | 16.4 | 3.4 | 3.4 | – | – |
| Nifty | average | message | The Work Built Around Visibility | 32 | 9.2 | 14.3 | 5.1 | 9.9 | – | 8.1 |
| Omnisend | average | balanced | Email & SMS marketing | 40 | 15.7 | 7.6 | 6.3 | 10.5 | 18.7 | 7.9 |
| Paymo | average | message | Small Businesses. Big Results. | 35 | 12.5 | 19.0 | 7.4 | 15.8 | 5.5 | – |
| SimplyBook.me | average | message | Online Booking System for all service based industries | 26 | 14.3 | 11.2 | 5.7 | 11.4 | 10.2 | – |
| Teamwork | average | message | Most tools track work. We make it profitable. | 34 | 14.4 | 13.9 | 7.2 | 12.9 | – | – |
| Tidio | average | message | What did your last 100 conversations earn you? | 32 | 20.6 | 13.0 | 2.9 | 5.1 | – | – |
| Wave | average | balanced | Clear books. Conﬁdent decisions. | 34 | 8.9 | 13.1 | 2.8 | 2.8 | 19.2 | – |
| Wrike | average | balanced | Deliver work, powered by humans and agents | 40 | 21.0 | 10.1 | 5.0 | 5.0 | 15.9 | – |
| Agile CRM | poor | balanced | Sell & Market Like the Fortune 500 | 36 | 12.3 | 7.3 | 5.7 | 16.6 | 18.9 | 6.1 |
| Apptivo | poor | visual | Accelerate your business Growth. | 24 | 7.0 | 2.9 | 1.8 | 3.9 | 27.5 | 15.0 |
| Axosoft | poor | message | Axosoft is the Scrum software for agile teams | 38 | 16.4 | 7.6 | 9.8 | 9.8 | 11.0 | – |
| Bubbl.us | poor | visual | With Bubbl.us you can create a family tree. create a family tree. | 32 | 9.9 | – | 4.9 | 4.9 | 34.0 | 2.1 |
| Commence | poor | message | Some CRM’s Manage Sales Ours Gets You Sales! | 26 | 12.0 | 8.3 | – | – | – | – |
| Dovico | poor | visual | People helping people grow | 38 | 7.8 | – | 3.5 | 6.5 | 51.2 | 13.4 |
| Easy Projects (Birdview) | poor | message | Easy Projects is now Birdview PSA | 34 | 9.9 | 21.9 | 1.1 | 1.1 | – | – |
| eSurveysPro | poor | balanced | New User? | 30 | 2.4 | – | – | 11.9 | 4.2 | – |
| Formsite | poor | balanced | Easily create professional online forms, surveys and workflows! | 31 | 22.2 | – | 6.6 | 6.6 | 42.4 | – |
| FreeConferenceCall | poor | message | Free, High-Quality Conference Call Services | 32 | 14.1 | 14.8 | 2.6 | 26.7 | – | – |
| HESK | poor | visual | Help Desk Software Hesk | 22 | 2.9 | 4.6 | 2.9 | 2.9 | 29.1 | – |
| iContact | poor | message | Easy email marketing software for your small business | 40 | 26.1 | – | 4.4 | 4.4 | – | – |
| KashFlow | poor | message | Payments. Faster than everyone. | 56 | 45.3 | 21.9 | – | – | – | – |
| Kintone | poor | balanced | All your team's workflows & AI in one place with Kintone | 42 | 24.1 | 7.9 | 1.5 | 6.0 | 29.5 | – |
| LimeSurvey | poor | balanced | Free online survey tool Create professional surveys 🇩🇪 HOSTED IN GERMA | 20 | 14.2 | – | 4.7 | 4.7 | 22.6 | – |
| osTicket | poor | balanced | Get The World’s Most Popular Customer Support Software | 30 | 17.7 | 14.7 | 2.6 | 2.6 | 17.2 | – |
| Planio | poor | message | Engineer Project Success | 43 | 13.2 | 19.1 | 5.8 | 18.2 | 10.0 | – |
| Project Insight | poor | message | Connect your data. Trust your reports. | 34 | 15.2 | 30.6 | 3.7 | 9.6 | – | – |
| ProofHub | poor | message | The one place for all your projects, teams and communications | 44 | 23.0 | 34.4 | 4.1 | 4.1 | 2.0 | – |
| Salesboom | poor | message | Blast your business off with easy to use Cloud CRM Software. Fully Cus | 28 | 15.6 | – | 5.2 | 8.9 | – | – |
| Sendy | poor | balanced | Send Newsletters Without SaaS Lock‑In | 45 | 20.2 | 7.7 | – | – | 14.7 | – |
| SuiteCRM | poor | visual | Watch & Discover | 36 | 16.5 | – | 5.6 | 11.4 | 53.7 | – |
| VerticalResponse | poor | balanced | Easy email marketing to communicate with your customers | 25 | 11.5 | 18.0 | 6.0 | 12.1 | 19.3 | – |
| Vision Helpdesk | poor | message | Customer Service Software | 36 | 8.3 | 7.8 | – | – | – | – |
| Wufoo | poor | message | Easy-to-Use Online Form Builder For Every Organization | 40 | 19.8 | 27.8 | 5.4 | 11.1 | – | – |

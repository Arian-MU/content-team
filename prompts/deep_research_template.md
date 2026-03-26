# ChatGPT Deep Research Prompt Template

Use this template every time you start a Deep Research session in ChatGPT.
Copy the block below, replace `[TOPIC]` with your actual topic, and paste it
into the ChatGPT Deep Research prompt box.

---

## Prompt to paste into ChatGPT

```
Research the following topic in depth:

TOPIC: [TOPIC]

Produce a structured markdown report using EXACTLY the section headings and
format shown below. Do not add extra top-level headings or change the heading
names — the report will be machine-parsed, so consistency matters.

---

# [TOPIC]

## Executive Summary
2–3 sentence overview of the key finding or narrative.

## Key Insights
A numbered list of the most important insights (aim for 5–8 points).
Each point should be a **bold title** followed by 1–2 sentences of explanation.

1. **Insight title**: Explanation.
2. **Insight title**: Explanation.
...

## Background & Context
2–4 paragraphs covering the relevant history, definition, or framing of the
topic. Include relevant statistics and data where available.

## Current Landscape / Trends
2–4 paragraphs describing the current state of the topic, emerging trends,
and notable examples or case studies.

## Marketing & Strategic Implications
(Tailor to the topic.) 2–3 paragraphs focused on what practitioners, marketers,
or business leaders should know and do with this information.

## Conclusion
1–2 paragraphs summarising the overall takeaway and any recommended next steps
or questions worth exploring.

## References
List every source you consulted. Format EACH entry as a bullet point — one
source per bullet — using this exact structure:

- Author/Organisation (Year). Title of article or page. URL: https://...
- Author/Organisation (Year). Title of article or page. URL: https://...

Rules for the References section:
• Every entry MUST include a full https:// URL on the same line.
• Do NOT use footnote markers like 【14†...】 — write out the URL directly.
• Do NOT use "citeturn" or any internal citation notation.
• If a source has no retrievable URL, write "URL: unavailable".
• Aim for at least 8 references.

---

Return only the report in the format above. Do not add commentary outside
the headings.
```

---

## Why this template exists

The report you get back is uploaded into the ContentTeam Knowledge Base
("Upload Research Report" section). The system automatically:

| What the system reads | Where it looks in the report |
|---|---|
| **Topic / title** | The `# Heading` on line 1 |
| **Reference URLs** | Every `https://` URL found in the `## References` section |
| **Citation strings** | Each bullet point inside the `## References` section |

If the report follows this template exactly:
- Zero parsing errors — title, URLs, and citations are all extracted cleanly.
- No missed references — every source is captured as a citation.
- No skipped ingestion — the content flows correctly into ChromaDB and SQLite.

---

## Checklist before uploading the report

- [ ] First line is `# [Your topic]` (no extra text before it)
- [ ] `## References` section is present and uses bullet points
- [ ] Each bullet point contains a full `https://` URL
- [ ] No `【N†...】` footnote markers remain in the body text
  (if they do, the system will strip them automatically, but cleaner is better)
- [ ] File saved as `.md` or `.txt`

---

## Example reference entry (correct format)

```
- LinkedIn (2024). LinkedIn Workforce Report: Skills on the Rise. URL: https://business.linkedin.com/talent-solutions/workforce-report
- McKinsey & Company (2023). The State of AI in 2023. URL: https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai-in-2023
```

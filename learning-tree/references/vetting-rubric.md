# Vetting rubric: choosing resources

Goal per skill node: one primary video, one primary article, and up to three alternatives that serve different needs. Quality and honesty beat quantity.

## Hard rules

1. **Every URL must come from a search result or a page you fetched in this session.** Never write a link from memory; models invent plausible URLs.
2. **Open the page** (fetch it) before recommending it, so the title, creator and length you record are real.
3. **Run `scripts/check_links.py`** on the tree before delivering. For YouTube it also returns the real video title: make sure it matches what you wrote. If you cannot run it, tell the person the links are unverified.
4. **If you cannot find something good, say so** and list fewer resources. Do not pad.

## Choosing the primary pair

Score candidates against the node's stated outcome ("You'll be able to...").

| Check | Prefer |
|---|---|
| Fit | Teaches exactly this node's outcome at the person's level, not a whole course. |
| Recency | Fast-moving fields (software, tools, AI): published or updated within roughly 2-3 years, or explicitly versioned. Stable fields (math, fundamentals): age matters little. |
| Credibility | Official docs, university courses, maintainers, practitioners with a track record, reputable educators. |
| Method | Shows or demonstrates, includes exercises or worked examples. |
| Length | Fits the node's `est_hours`; a 6-hour video does not belong in a 3-hour node. |
| Access | Free, no login wall, stable URL. Note any paywall. |

## Choosing alternatives

Alternatives exist for the person who dislikes the primary. Each should differ from the primary along **one axis** and say so in its "pick this if" line:

- shorter / quicker overview
- deeper or more advanced
- different format (text instead of video, interactive instead of passive)
- different style (slower, more visual, more blunt)
- project-based instead of explanatory

If two candidates are basically the same, keep the better one and drop the other.

## Source tiers

Prefer the highest tier that has something good for the node. Search each tier before moving down.

1. **Tier 1: authoritative.** Official documentation, university courses and lecture notes, maintainers, and organisations that publish the material they teach.
2. **Tier 2: reputable community.** Established educators and channels with a track record, well-known engineering blogs, and curated "awesome" lists.
3. **Tier 3: last resort.** Forum threads, Q&A answers, and social media posts (Facebook, X, Reddit and similar). Use one only if tiers 1 and 2 have nothing usable for this node. Say so in the resource's "why" line (e.g. "only source found: community forum thread"), never use it as an alternative just to fill the list, and tell the person the node is thinly covered.

A tier is a starting point, not a verdict. A tier-1 page can be outdated, and a tier-2 page can be wrong, so the checks in "Choosing the primary pair" still apply.

## Red flags

- Undated or clearly outdated for the tool version in use
- SEO listicles, affiliate-driven "best X" pages, content farms
- Clickbait titles, promises of mastery in minutes
- A vendor selling a product dressed as a tutorial (acceptable only when the vendor's own docs are the subject)
- Paywalled content presented as free (note paywalls that exist, such as some Medium posts)
- Videos that are mostly talking-head with no demonstration, for hands-on skills
- Source you cannot identify the author of
- Social media posts and forum answers presented as authoritative, especially undated ones

## Niche topics

When mainstream sources are thin: look for curated "awesome" lists on GitHub, university syllabi and lecture notes, conference talks, official docs, community wikis and well-regarded books' companion sites. Prefer one solid primary and no alternatives over weak filler. State plainly that the topic is thinly covered.

## What to record per resource

Format icon (🎥 / 📄), title as shown on the page, creator or site, approximate length (only if confirmed), and a short reason in the person's terms ("clear diagrams", "includes a live conflict").

# Sources and search strategy

Contents: search order · known sources · query patterns · attribution

Availability, pricing and URLs change. Treat this list as a starting map, and confirm every page by fetching it (see `vetting-rubric.md`). Last spot-checked against current sources on 2026-10-13: Google Skills, Coursera/edX access, free-for.dev. The rest was not re-verified.

## Search order

1. **Find the shape of the topic.** Look for an existing roadmap or syllabus and use it to draft gears. Check roadmap.sh for a matching roadmap, then university syllabi.
2. **Find resources per node.** Prefer the known sources below, searched with the web search tool and a `site:` filter where useful.
3. **Go wide only when needed.** For niche topics, search awesome-lists, talks, papers' companion material and community wikis.
4. **Verify.** Fetch, then `check_links.py`.

The "known sources" step is a set of targeted searches, not a crawler. Web search results vary run to run, so verification matters more than the search itself.

## Known sources

Use only the rows that fit the topic. None of them may fit, and that is fine: fall back to an open search and judge the results with the tiers in `vetting-rubric.md`. Never check every row for its own sake.

| Source | Good for | Search hint |
|---|---|---|
| roadmap.sh | Gear structure for developer and IT topics | Find the roadmap page for the topic; use its node list as a skeleton. Attribute it; do not copy its text. |
| Official documentation | Authoritative primary articles for tools and languages | `<tool> getting started`, `<tool> tutorial site:<official domain>` |
| MIT OpenCourseWare (ocw.mit.edu) | University lectures, notes, problem sets | `<topic> site:ocw.mit.edu` |
| OpenLearn (open.edu/openlearn) | Free Open University units across many subjects | `<topic> site:open.edu/openlearn` |
| Other university sites | Syllabi, lecture notes | `<topic> syllabus site:.edu`, `<topic> lecture notes` |
| freeCodeCamp, Khan Academy, The Odin Project, CS50 | Beginner programming, web, math, CS | Search the topic with the site name |
| Company-run free learning (IBM SkillsBuild, Microsoft Learn, Google Skills, AWS Skill Builder) | Vendor tools and certifications | Search the product plus the platform name; note that training content is mostly free; certification exams and some labs or practice tests may cost money. Say “free” only for what the page you opened shows as free. Google Skills is the 2025 merger of Google Cloud Skills Boost, Grow with Google, DeepMind and Google for Education training, so older pages may say "Cloud Skills Boost"; some labs use monthly credits |
| free-for.dev (github.com/ripienaar/free-for-dev) | Mostly developer-tool free tiers; its "Education and Career Development" section is short and developer-focused (freeCodeCamp, The Odin Project, Full Stack Open and similar) | Fetch the list and read that section; do not expect it to cover non-technical subjects |
| GitHub awesome lists | Niche topics, curated links | `awesome <topic> github` |
| YouTube | Lectures, walkthroughs, full courses | `<topic> <node title> tutorial`; prefer playlists and courses from recognized educators; check upload date and length |
| Blogs (dev.to, personal and engineering blogs) | Focused articles | Prefer these over paywalled platforms; note if a post is behind a paywall |
| Coursera / edX | Structured university courses | Free access varies by course and has been narrowing: edX audit access is free but time-limited and excludes graded work; Coursera has moved some courses to first-module previews. Say "free" only if the enrollment page you opened shows it |

## Query patterns

- Roadmap: `<topic> learning roadmap`, `<topic> roadmap beginner to advanced`
- Syllabus: `<topic> course syllabus`, `<topic> syllabus site:.edu`
- Node resource: `<node title> tutorial`, `<node title> explained`, `<node title> exercises`
- Video: `<node title> <topic> course playlist`
- Niche: `awesome <topic>`, `<topic> reading list`, `<topic> wiki`

Start with 1-3 words, then narrow. Run a separate search per node rather than one query for everything.

## Attribution and respect

- Link to resources; do not copy their text into node files.
- When a gear structure is based on a roadmap or syllabus, say which one in `overview.md` or in your message to the person.
- Do not scrape sites that forbid it. Prefer official APIs and feeds where they exist.

---
title: "Lessons — Directory Index"
purpose: "Lessons learned from real incidents, debugging sessions, and production issues"
type: directory-index
aspect: knower
neural:
  activation: 0.38
  stage: growing
  synapse_in: 0
  synapse_out: 5
---

# Lessons

**Purpose:** Capture hard-won knowledge from mistakes, debugging sessions, and production incidents. Each lesson documents what went wrong, why, and how to prevent recurrence.

**Put here when:** Something unexpected happens during development or production that others should know about. Includes root cause and prevention guidance.

**Naming:** `lesson-NN-descriptive-slug.md` or date-prefixed `YYYY-MM-DD-slug.md`

**Required frontmatter:**
- `title` — Lesson title (descriptive of the problem)
- `date` — Date learned (YYYY-MM-DD)
- `severity` — One of: `HIGH`, `MEDIUM`, `LOW`
- `tags` — Array of tags (`[lesson, topic-area]`)

**Template:** No

**Current count:** 47 notes (23 HIGH severity)

**Key notes (HIGH severity):**
- [[lesson-04-surgery-lesson]] — Surgical code changes: modify only what is required
- [[lesson-21-runtime-json-pollution]] — Debug output corrupts JSON parsing in pipelines
- [[lesson-18-mock-live-services-in-tests]] — Never call real APIs from unit test suite

**Related MOC:** [[MOC-compound-engineering]], [[MOC-platform-infrastructure]]

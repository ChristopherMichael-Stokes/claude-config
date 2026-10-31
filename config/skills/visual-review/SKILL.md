---
name: visual-review
description: >-
  Standards for the artifact page that ends work judged by eye (images, fits, meshes, maps,
  plots): before/after panels, overlays, blink toggle, subject selection and a how-to-read note.
  Use when building or reviewing such a page, and when checking renders, plots or screenshots
  during the work.
---

# Visual review page

Publish the page as an artifact, with metrics beside the views, never instead of them.

- Before and after on the same subjects, same crop, same scale, with an overlay that makes the
  question checkable (the reference outline over the image) and a blink toggle for A against B.
- Subjects chosen by a rule fixed before fitting, spread across the cases, never by how good
  they look. Worst cases shown beside typical ones.
- Spread across places or conditions (one per compass direction, say), with sites that failed
  listed as failed.
- A short "how to read this" at the top: what each panel is, the one question to answer, known
  artefacts.

## Checking renders during the work

A `research-mid` subagent reads the images, not the main thread: an image read in the main thread
is resent every turn after. Its brief names the image paths and the criterion each is judged
against, and asks for a per-image verdict (pass/fail, what is wrong, where in the image). The main
thread reads an image itself only when a verdict is ambiguous or contradicts the metrics.

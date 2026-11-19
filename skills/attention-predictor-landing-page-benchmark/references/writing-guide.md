# Writing the analysis (narrative.json)

`scripts/narrate.py` writes a complete, data-driven draft. Rewrite it in your own words when you can; the rules below are what makes the analysis useful. Every number must come from `facts.md` or `analysis.json`. A full hand-written example is in `templates/narrative.example.json`.

## Fields

`title`, `goal`, `verdict`, `top_actions[]`, `approach_notes[]`, `target_notes[]`, `benchmark_notes[]`, `patterns[]` (optional), `competitor_takeaways` (only when a competitor group is set), `change_verdict` and `change_notes[]` (only when a previous version is compared, see workflow step 4b), `mobile_notes[]`, `guidelines[]` (each: `title`, `tag`, `points[]`, `target`, `evidence`), `scorecard[]` (each: `metric`, `today_d`, `target_d`, `today_m`, `target_m`), `limits[]`. Simple HTML (`<b>`) is allowed in strings.

## Rules

- **goal:** one or two sentences: the approach used, whether the owner chose it or it was assumed from the page today, and the reference group size. The report prints the general goal statement itself.
- **verdict:** lead with the range check, not with ranks. Is any key element a blind spot or missing; what is below range; what is in range; what is above range and whether that is by design. 3–5 sentences, both devices.
- **Order of work:** blind spots and missing key elements → key elements below range → supporting elements below range → spread corrections. Elements in range get "keep". Never recommend raising an element that is already in or above range because some other page scores higher.
- **Budget:** attention is a fixed budget. Every "raise X" says where the attention comes from - an above-range element that is not what the approach puts first, an oversized optional element, or unassigned background - and confirms the donor stays inside its own range.
- **Diagnose each weak element:** too small (low area, normal attention per area) or unattractive (normal area, low attention per area)? Losing attention from 3 s to 10 s? Which element takes it?
- **Targets are the reference range** (p25–p75 of top pages built the same way), e.g. "primary CTA 0.7–1.8%". Never "rank 1" or "beat Stripe". For an element above range the target is a floor ("stay ≥ 0.7%").
- **approach_notes:** why the approach fits (message : visual ratio), what the spread comparison shows, and what would change under the alternatives - so the owner can decide knowingly. If facts.md says WEAK FIT, choosing a clear approach is the first recommendation.
- **guidelines:** each one is a concrete spec (px sizes, word counts, labels, order, placement, fill/colour), 2–3 copy directions where copy is the problem, the target range, where the attention comes from, and evidence (value, range, status, pages in the group). Tag with device and status (`blind spot`, `missing`, `below range`, `do not change`, `process`). Always include a "keep what is in range" guideline and a validation step (re-score the variant with this skill, then a live A/B test).
- **Context:** ranks against all pages and the average / poorly made medians may be mentioned, clearly as context. Re-check every superlative against the data.
- **Language:** "predicted attention", never "users looked at". Say "indicative" when an element is present on only a few reference pages, and do not call an optional element a problem.

## Hand-over message

State the approach used (and that it was assumed, if so), the blind spots, what is already in range, and where the files are.

# Choosing useful AOIs when the design has none

An AOI (Area of Interest) is a region of the image whose attention is measured separately. If the study item has no AOIs saved, there is nothing to report on: the agent must define them. This guide says how, so the AOIs answer the questions the brand team actually has.

AOIs defined here are **proposed**: they are measured read-only (the dashboard's statistics endpoint accepts any shape; nothing is saved in RealEye) and the report says so. Never save or edit AOIs in the user's RealEye study unless the user explicitly asks; the report's study blueprint gives the coordinates so they can be drawn in the AOI editor.

## 1. Check first

1. Read the item's AOIs: `/api/item/<ITEM_ID>/aoi/get/?tryToFix=1` (the shapes script prints them). An empty list means the design has none.
2. If some AOIs exist, keep them and only add the missing important ones, named in the same style. If the user's brief names elements, they come first.
3. If you compare designs, define AOIs for **all designs together**: the same elements, the same names, in the same order, so the numbers can be compared.

## 2. Start from the decision, not from the picture

Write down, in one line each, the decision the brand team has to make, what the designer wants viewers to notice, and the hypotheses to test (the report's hypotheses section). Then choose the elements those questions depend on:

| Element | Why it matters | Typical AOI |
|---|---|---|
| Brand name / logo | Without it nothing builds the brand | each place it appears (logo, pack label, banner) as separate AOIs |
| Product / pack shot | What is being sold | the pack, and the label if it carries the name |
| Headline / claim / tagline | The message | the text block, tight to the text |
| Offer, price, promotion | Drives action | the offer block |
| Call to action (button, URL, QR) | The next step | the button or line |
| Human face / eyes | Strong attractor; can pull attention from the brand | the face (add the eyes only for a gaze-cue question) |
| Key visual / hero image | The scene or product in use | the main image area |
| Competing or decorative elements | Possible distractors | only if a hypothesis is about them |
| Legal / small print | Only if it must be read | usually skip |

Aim for **3 to 8 AOIs**. Fewer than 3 cannot show a hierarchy; more than 8 is unreadable and the small ones are noisy. Start with the must-not-miss elements and stop when each remaining candidate would not change a decision.

## 3. Shape and size rules

- **Name by what it covers** ("Brand name (banner)", not "Region 4"). Avoid colons in names (they break difference tokens). Give each AOI a `role` (what it is) and a `why` (the question it answers).
- **Tight, with a little margin.** Draw the outline around the element with about 1–2% of the image as margin, because webcam eye tracking is imprecise. Do not include large empty background.
- **Not too small.** Keep each side at least about 6% of the image width or height (`scripts/check_aois.py` warns). For tiny elements, enlarge the AOI to include its surroundings or merge it with its neighbour and say so in the name ("Pack label area").
- **Not too big.** An AOI covering more than about half the image shows nothing. Split it.
- **No accidental overlaps.** Overlaps are fine when one element is deliberately inside another (a logo on a pack): say so in the `role`. Otherwise separate them. Large AOIs score higher simply because they are larger; mention it when sizes differ a lot.
- **Polygons for odd shapes**, rectangles for the rest. A rectangle is four points; the time range starts at 0.5 s like the dashboard's own.
- **Text blocks:** one AOI per headline or line group, not per word, unless a hypothesis is about a specific word.

## 4. Find the coordinates

1. Open the clean stimulus image (it is saved for the report) with the image viewer and note where each chosen element sits. Estimate the outline as points in percent of the image width and height, origin top-left (x to the right, y down).
2. Write `aois.json` (see `scripts/check_aois.py`), run `python scripts/check_aois.py aois.json -i stimulus.jpg -o preview.png`, and **look at the preview**: every outline must sit on the element it is named after. Fix and repeat until it does.
3. Measure the AOIs with `scripts/dashboard_vai_collect.js` using `CONFIG.customAois` (points in percent). Check the numbers make sense: an AOI with near-zero Reach is probably misplaced or too small.
4. **Look at the heatmap against the outlines.** Any strong warm area outside all AOIs is an element you missed or an unexpected attractor: add an AOI for it, re-measure, and mention it in the findings. Any AOI over a cold area is either a real blind spot or misplaced: check the outline first.
5. Put the result in the report JSON: `variants[].aois` (name, role, why, color, shape in %), `variants[].aoi_source: "proposed"`, and `image_px`. The report then marks the AOIs as proposed and the blueprint tells the reader to draw them in RealEye.

## 5. Say what you did

State in the report that the AOIs were proposed from the image and the design's purpose, how you chose them, and that the same measurement on other AOIs would give other numbers. Offer to add them to the study only if the user asks. Suggest in *How to improve the study* any AOIs you left out (finer parts of the pack, the eyes, a call to action that is not yet in the design).

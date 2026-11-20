# Neuromarketing image report

Use this skill to turn *measured* RealEye eye tracking into a decision brief for a brand or creative team. It covers tested ads, packaging, and other static images, with shot-level guidance for video ads. Gaze identifies what was looked at and what to retest; the planned post-view or behavioral outcome decides between versions. The skill does not run Attention Predictor or pick a winner from a heatmap.

## Install

```bash
npx skills add RealEye-io/realeye-skills --skill neuromarketing-image-report
```

In Claude Code, add the `RealEye-io/realeye-skills` marketplace and install `neuromarketing-image-report@realeye-skills`. You can also copy this folder into your agent's skills directory. The supplied-file workflow needs no API token or setup script.

## Use

1. Open the tested item's **Heatmap** in RealEye. Provide the tested creative and download **AOI Overall Stats** with the chosen filters. For images, the **AOI VAI Report** PDF is another starting point. Add a matching heatmap or shot-level evidence and any participant-level or quality exports needed. For variant selection also provide **Survey Results** or the relevant choice/field results with the variant assignment and scoring rules. [Export help](https://www.realeye.io/support/data-export-csv-files).
2. If you have an item link, the agent can inspect it only with authorized access. Otherwise attach the exports directly, keeping participant names and external IDs out of the files you share if they are not needed.
3. Tell the agent the decision, the audience and placement, and whether the study used free viewing or a task. Include the exposure duration and any variant or audience segment you want compared.

Example request:

> Use neuromarketing-image-report on the attached ad and RealEye exports. We're deciding whether to keep this layout or move the benefit claim. Our audience was grocery shoppers, viewing freely for 5 seconds on desktop. Tell the brand manager what to preserve, what to change, and how to test the change without hurting brand visibility. Put the metrics and study details in an appendix.

The default output is a self-contained, professional HTML report (one file, charts and images embedded, dark mode, print to PDF) built with the bundled `scripts/build_report.py` (Python 3, no dependencies). It analyses only Average-or-better quality viewers, covers each design separately (AOI overlay with viewing-order markers, heatmap, viewing ratio, TTFF, VAI with Reach/Speed/Hold, gender and age cuts, the embedded dashboard AOI VAI report), compares designs head to head with charts and intervals, and ends with prioritised actions, a retest plan, and an evidence appendix. See [the HTML report guide](references/html-report.md). See the [fictional worked examples](references/worked-example.md), the [interpretation guide](references/interpretation.md), and the [RealEye Neuromarketing Report Methodology](<references/RealEye Neuromarketing Report Methodology.md>) for the evidence and study protocol. No participant or customer study data is bundled.

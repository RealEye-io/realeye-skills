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

The output is a self-contained, professional HTML report (one file, images embedded, dark mode, print to PDF) built with the bundled `scripts/build_report.py` (Python 3, no dependencies). It states that the test ran on the RealEye platform with webcam eye tracking, opens with the overall findings and conclusions, then explains how to read VAI and goes into depth: the viewing order, each design, and VAI with its Reach, Speed and Hold for every gender, age and gender × age audience in the first 3, 5 and 10 seconds, with a heatmap for each. Only viewers with data quality Average or better are analysed, and only VAI and its components are used (no raw metrics such as time to first fixation). Every report is built from a bundled template, styled after the RealEye dashboard's AOI VAI report, and must look like the bundled example (`assets/example/example-report.html`), and every table and heatmap links to the same view in the RealEye dashboard. The agent collects the data with the browser following [the browser playbook](references/browser-data-collection.md). The intro presents the tested images with their AOIs outlined and links to the dashboard, every mention of a design shows its thumbnail on hover, every metric name (VAI, Reach, Speed, Hold, AOI) has a tooltip definition, the report states when the study was created, when the data was collected, the RealEye version and who took part (gender, age, device), presents data as tables and charts, and ends with a copy-paste prompt and a collapsed data pack (markdown with CSV tables, copy and download buttons) that let an AI assistant use all the data and answer follow-up questions, and the viewing order is visualised overall and for every audience. See [the HTML report guide](references/html-report.md). See the [fictional worked examples](references/worked-example.md), the [interpretation guide](references/interpretation.md), and the [RealEye Neuromarketing Report Methodology](<references/RealEye Neuromarketing Report Methodology.md>) for the evidence and study protocol. The bundled example uses aggregated results from a RealEye demo study (no participant-level data, placeholder study ids).

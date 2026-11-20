# Accessibility (Google Lighthouse)

The report script produces pages that score **100** in Google Lighthouse's accessibility category on desktop and mobile, with details opened and all tabs shown. Keep it that way.

## What the script already does

- **Contrast:** every text colour is at least 4.5:1 on its background (WCAG AA). Muted text is `#5c5c5c`, soft text `#6b6b6b`, link and accent text `#b53d1b`; white text only sits on dark enough chips (design colours `#c2410c`, `#2563c4`, `#1b7d42`, `#ae3ec9`; tag colours are dark). The bright brand orange `#fc7753` is only used for bars, borders and the logo (dark text on it).
- **Structure:** one `h1`, headings never skip a level for assistive technology (`aria-level` keeps the visual style), tables have header cells (first column cells that name a row are `th scope="row"`), the page has a language, a title and a viewport.
- **Names:** images, SVG charts and heatmaps have `role="img"` and a label, text areas have `aria-label`, icon buttons have `aria-label`, design chips inside links are not buttons.
- **Keyboard:** design chips, tooltips terms, menu entries and the mark-up tool work with the keyboard and show focus.

## Run Lighthouse

Lighthouse does not accept `file://` URLs, so serve the report over localhost.

```powershell
mkdir lh; cd lh; npm init -y; npm install lighthouse          # once, in a scratch folder
python -m http.server 8765 --bind 127.0.0.1                    # in the folder with report.html, second terminal
$env:CHROME_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
node node_modules/lighthouse/cli/index.js http://127.0.0.1:8765/report.html --only-categories=accessibility --preset=desktop --output=json --output-path=lh.json --chrome-flags="--headless=new"
```

Run it again without `--preset=desktop` for mobile. Lighthouse only tests what is visible, so also run it on a copy where every `<details>` is `<details open>` and the audience tab panes are shown (`.wtabs .wpane{display:block!important}`), because they hide content by default. Read the failed audits from `lh.json` (`audits.<id>.details.items[].node`). Stop the local server afterwards.

## When you change the design

Do not add colours that fail 4.5:1, text smaller than the existing sizes in lighter greys, nested interactive elements, or images without a label. `scripts/audit_report.py` checks the colour tokens and chip colours; Lighthouse checks the rest.

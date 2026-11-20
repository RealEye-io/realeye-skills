# Printing and saving as PDF

The report is meant to be printed or saved as a PDF (the *Print / Save as PDF* button, or Ctrl+P). The script's print layout (the `@media print` and `@page` rules in `build_report.py`) does this:

- A4 page with small margins; backgrounds, colours and images are forced to print (`print-color-adjust: exact`), because the heatmaps, design images, charts, badges and pills are CSS backgrounds that browsers drop when *Background graphics* is off.
- Wide tables shrink and wrap instead of being clipped; stage images and heatmaps are limited in size so a tall design does not fill a page.
- All audience tabs (first 3, 5 and 10 s) are shown, and the collapsed dashboard AOI VAI report copies are opened for printing and closed again afterwards (`beforeprint` / `afterprint`).
- Cards, findings, table rows and figures are kept together; headings stay with their content.
- The menu, the mark-up tool, buttons, the AI prompt and the data pack are hidden; the closing section says they are in the interactive version. Links print as plain text.

## Check it

Render the report to PDF with headless Edge or Chrome and look at the pages:

```powershell
& "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --headless=new --user-data-dir=$env:TEMP\pdfprof --virtual-time-budget=8000 --no-pdf-header-footer --print-to-pdf=report.pdf "file:///C:/path/report.html"
```

Then convert pages to images (for example with PyMuPDF: `pymupdf.open("report.pdf")[i].get_pixmap(matrix=pymupdf.Matrix(0.75, 0.75))`) and make a contact sheet of every page. Look for: missing images, clipped tables or charts, text cut at the right edge, large blank gaps, overlapping blocks. The example prints to about 65 A4 pages.

Do not add styling in a report that breaks this; change the script instead and re-check.

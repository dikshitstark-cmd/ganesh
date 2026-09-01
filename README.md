# Ganesh Utsav Receipt Management System

A complete, self-contained Flask web app for generating and tracking
donation receipts for a Ganesh Utsav committee — bilingual (Telugu +
English), pixel-perfect A4 print layout, payment tracking (Paid /
Partial / Unpaid), UPI QR codes, bulk generation from Excel, and
Excel/CSV export.

---

## 1. Tech Stack

| Layer     | Choice |
|-----------|--------|
| Backend   | Python 3 + Flask |
| Database  | SQLite (single file, `receipts.db`, zero setup) |
| Frontend  | Plain HTML + CSS + a little vanilla JS (no build step) |
| PDF       | Browser print (`window.print`) for single receipts, **WeasyPrint** for bulk PDF generation (no wkhtmltopdf) |
| Excel     | `openpyxl` (read/write) |
| QR Codes  | `qrcode` (rendered as inline base64 — no extra static files) |

---

## 2. Project Structure

```
ganesh_utsav/
├── app.py                     # Flask app & all routes
├── db.py                      # SQLite schema + data access layer
├── utils.py                   # amount-in-words, QR code, WhatsApp link helpers
├── generate_placeholders.py   # creates placeholder header/watermark images
├── requirements.txt
├── sample_receipts.xlsx       # sample file for bulk upload
├── receipts.db                # created automatically on first run
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── new_receipt.html
│   ├── bulk_upload.html
│   ├── receipt.html           # the printable A4 receipt page
│   ├── _receipt_body.html     # reusable receipt markup (used twice per page)
│   └── error.html
├── static/
│   ├── css/style.css          # dashboard/forms UI
│   ├── css/receipt.css        # pixel-perfect A4 print styling
│   ├── js/dashboard.js
│   └── images/                # ganesh_left.png, ganesh_right.png, watermark.png
├── uploads/                   # bulk-upload Excel files land here
└── generated/                 # generated ZIPs of bulk receipts land here
```

---

## 3. Setup

### 3.1 Python dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3.2 Telugu font for PDF generation (important)

The browser already renders Telugu correctly via Google Fonts
(Noto Sans Telugu), so single-receipt printing works out of the box
with no setup.

For **bulk PDF generation** (WeasyPrint, running outside a browser),
install the Noto Sans Telugu font at the OS level so WeasyPrint can
find it through fontconfig:

```bash
# Debian/Ubuntu
sudo apt-get install -y fonts-noto-core

# Fedora
sudo dnf install -y google-noto-sans-telugu-fonts

# macOS (Homebrew)
brew install --cask font-noto-sans-telugu
```

> **Why not just let WeasyPrint download the Google webfont?**
> Some WeasyPrint + fontTools version combinations crash
> (`ValueError: expected 0 <= int <= 122`) when subsetting Google's
> *variable* Noto Sans Telugu webfont. The bulk-PDF route in this app
> deliberately renders against the **locally installed static font**
> instead (see `render_receipt_html(..., for_pdf=True)` in `app.py`),
> which sidesteps the bug entirely and was verified to render Telugu
> correctly. If WeasyPrint isn't installed at all, bulk generation
> automatically falls back to a ZIP of printable HTML files instead of
> failing.

### 3.3 Generate placeholder images (one-time)

Real Ganesh artwork isn't included in this deliverable. Run this once
to generate simple placeholder header/watermark images so the receipt
always renders something instead of a broken image icon:

```bash
python generate_placeholders.py
```

To use real artwork later, just replace these three files with your
own images of the same name (any size — CSS scales them):
`static/images/ganesh_left.png`, `ganesh_right.png`, `watermark.png`.

### 3.4 Run

```bash
python app.py
```

Open **http://127.0.0.1:5000** — you'll land on the Dashboard.
The SQLite database (`receipts.db`) and its tables are created
automatically on first run.

For verbose debug tracebacks during development:
`FLASK_DEBUG=1 python app.py` (the reloader is intentionally kept
off — see the comment in `app.py` for why).

---

## 4. Using the App

### Create a single receipt
Dashboard → **+ New Receipt** → fill in Name, Address, Amount, Mode,
and Payment Status (Paid in full / Partial / Unpaid). Receipt number
is assigned automatically (`GU/2026/0001`, persistent counter, never
reused even if you delete rows).

### View / Print / Save as PDF
Dashboard → **View / Print** opens the receipt in a new tab. Click
**🖨 Print / Save as PDF** — the browser's print dialog lets you print
on paper or "Save as PDF". The page is laid out for A4 with two
copies stacked on one sheet (**Customer Copy** on top, **Office
Copy** below, separated by a cut line) — a bonus feature so you can
literally cut the page in half after printing.

### Update a payment
Dashboard → **Update Payment** on any non-Paid row opens a small
modal: either **Mark Fully Paid** in one click, or type a specific
paid amount for a partial payment. The due amount and status badge
recalculate automatically.

### Search & filter
The search box matches name or receipt number; the status dropdown
filters by Paid / Partial / Unpaid.

### Export
Dashboard → **Export Excel** / **Export CSV** downloads every
receipt with all payment columns.

### Bulk generate
Navbar → **Bulk Generate** → upload an Excel file with columns
`Name | Address | Amount | Mode` (see `sample_receipts.xlsx`, or
download a fresh copy from the page itself). Every valid row becomes
a new receipt with status **Unpaid**, and you get a ZIP of individual
PDFs (or HTML files if WeasyPrint isn't available) to download.
Rows with missing/invalid data are skipped and listed on screen.

### WhatsApp
Dashboard → **WhatsApp** next to a receipt opens `wa.me` with a
pre-filled thank-you message and a link to the receipt — only if a
phone number was entered when the receipt was created. **The phone
number is never printed on the receipt itself**, exactly as
required; it's stored purely for this feature.

### UPI QR code
Every receipt with a due amount > 0 shows a scannable UPI QR code.
Set your real UPI ID by editing the `settings` table (or just change
the default in `db.py` → `init_db()` before first run):

```python
defaults = {
    "upi_id": "your-real-id@upi",
    "org_name_en": "Your Committee Name",
    "org_name_te": "మీ కమిటీ పేరు",
}
```

---

## 5. Error Handling Built In

- **Bulk upload**: rejects non-`.xlsx/.xls` files, missing required
  columns, empty files, and skips (with a listed reason) any row
  missing a name/address/amount or with a non-numeric/zero amount.
- **New receipt form**: validates required fields, numeric amounts,
  and that paid amount never exceeds the total; errors are shown
  inline without losing what you typed.
- **404 / 413 / 500**: friendly error page instead of a raw
  traceback; upload size is capped at 10 MB.
- **PDF generation failures** (bulk): if WeasyPrint isn't installed,
  or a specific receipt fails to render as PDF, the app automatically
  falls back to HTML for that file rather than aborting the whole
  batch.

---

## 6. Notes on Design Choices

- **No wkhtmltopdf**: single receipts use the browser's native
  print-to-PDF (perfect Unicode/Telugu rendering, zero server load).
  Bulk receipts use WeasyPrint, a pure-Python PDF engine — no browser
  binary or Chromium install required.
- **QR codes are inline** (base64 data URI) — nothing written to
  disk, nothing to clean up.
- **Receipt numbering** uses a persistent counter row in SQLite, not
  `MAX(id)+1`, so it survives deletions and restarts.
- **Amount in words** uses the Indian numbering system (Lakh/Crore),
  not the Western Million/Billion grouping — implemented from
  scratch in `utils.py`, no extra dependency.

---

## 7. Production Deployment Notes

This ships with Flask's built-in dev server for simplicity. For real
deployment:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Also: change `app.secret_key` in `app.py` to a long random value,
and put SQLite on a persistent volume if deploying on ephemeral
infrastructure (e.g. containers).
"# ganesh" 

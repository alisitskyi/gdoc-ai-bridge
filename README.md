# gdoc-ai-bridge 🚀

> **Universal Google Docs & Google Sheets CLI for AI Coding Assistants**  
> Enables Claude Code, Cursor, Cline, Roo Code, Antigravity, and developers to seamlessly read, edit, and comment on Google Docs & Sheets across any workspace.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Google Cloud: Ready](https://img.shields.io/badge/Google%20Cloud-OAuth%202.0-orange.svg)](https://console.cloud.google.com/)

---

## 💡 Why This Exists

When working with AI coding assistants (like **Claude Code**, **Cline**, **Cursor**, or **Copilot**) in VS Code, AI often needs to read technical specifications, update product requirements documents (PRD), or edit tracking tables in Google Docs & Sheets.

Existing approaches usually fail:
1. **Google Apps Script Webhooks:** Blocked by Google with *"This app is blocked"* due to unverified sensitive scopes.
2. **Per-project secret sprawl:** Copying API keys and scripts into every git repository risks committing secrets and forces repeated re-authentications.
3. **Accidental overwrites:** Direct API edits have no "preview" and can ruin existing formatting or text.

### The Solution: `gdoc-ai-bridge`
- 🌐 **Global Single Sign-On:** Authenticate **once** into `~/.gdoc/` $\rightarrow$ every project, terminal, and AI assistant on your machine inherits access automatically.
- 🛡️ **Safety-First Auto Backups:** Every destructive action (`replace`, `append`, `sheet-update`) automatically creates a timestamped clone (`[Backup] ...`) in Google Drive before modifying the original.
- ⚡ **Universal CLI (`gdoc` / `gsheet`):** Simple, fast command-line interface designed to be invoked directly by AI agents or human developers.
- 📊 **Docs + Sheets + Comments:** Complete coverage for reading content, updating tables, managing comment threads, and replying to team discussions.

---

## 🚀 Quickstart (Installation)

### On Windows (PowerShell)
```powershell
# 1. Clone repository
git clone https://github.com/alisitskyi/gdoc-ai-bridge.git
cd gdoc-ai-bridge

# 2. Run automated installer
.\install.ps1

# 3. Copy your Google Cloud credentials.json to ~/.gdoc/
# (See Google Cloud setup below)

# 4. Authenticate once
gdoc auth
```

### On macOS / Linux
```bash
# 1. Clone repository
git clone https://github.com/alisitskyi/gdoc-ai-bridge.git
cd gdoc-ai-bridge

# 2. Run automated installer
chmod +x install.sh
./install.sh

# 3. Authenticate once
gdoc auth
```

### Or via pip
```bash
pip install -e .
gdoc auth
```

---

## 🔑 One-Time Google Cloud Setup (2 minutes)

1. Open [Google Cloud Console](https://console.cloud.google.com/projectcreate) and create a project (e.g. `gdoc-automation`).
2. Enable the required APIs:
   - [Enable Google Docs API](https://console.cloud.google.com/apis/library/docs.googleapis.com)
   - [Enable Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)
   - [Enable Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com)
3. Configure [OAuth Consent Screen](https://console.cloud.google.com/apis/credentials/consent):
   - User Type: **External**
   - Fill in App Name & Support Email.
   - Under **Audience / Test users**, add your Google email account.
4. Create Credentials:
   - Go to [Credentials](https://console.cloud.google.com/apis/credentials) $\rightarrow$ **+ CREATE CREDENTIALS** $\rightarrow$ **OAuth client ID**.
   - Application Type: **Desktop app**.
   - Click **Create**, then click **DOWNLOAD JSON**.
5. Save the downloaded JSON file as:
   - **Windows:** `C:\Users\<username>\.gdoc\credentials.json`
   - **macOS/Linux:** `~/.gdoc/credentials.json`
6. Run `gdoc auth` in any terminal to log in via browser once.

---

## 📖 CLI Usage Reference

You can pass either the **full URL** or just the **document/sheet ID**.

### 📄 Google Docs

```bash
# Check status
gdoc status

# Read entire document text:
gdoc read "https://docs.google.com/document/d/<ID>/edit"

# Save document text to a local file:
gdoc read "<URL>" --save-to ./notes/doc_content.txt

# Find and replace text (automatically creates backup in Google Drive first):
gdoc replace "<URL>" --find "old text" --replace "new text"

# Append text to the end of the document:
gdoc append "<URL>" --text "New section or paragraph to add"

# Insert text at specific character index:
gdoc insert "<URL>" --index 10 --text "Inserted header"

# View all comments and discussions:
gdoc comments "<URL>"

# Reply to a comment thread:
gdoc reply "<URL>" --comment-id "<COMMENT_ID>" --text "Fixed according to review"

# Create a manual backup snapshot:
gdoc backup "<URL>"
```

### 📊 Google Sheets

```bash
# View spreadsheet title, tab names, and dimensions:
gdoc sheet-info "https://docs.google.com/spreadsheets/d/<ID>/edit"

# Read table (formatted text table):
gdoc sheet-read "<URL>"

# Read specific tab or range:
gdoc sheet-read "<URL>" --range "Sheet1!A1:D20"

# Output as JSON (perfect for AI processing):
gdoc sheet-read "<URL>" --json

# Output as CSV:
gdoc sheet-read "<URL>" --csv

# Update cell(s):
gdoc sheet-update "<URL>" --range "Sheet1!B2" --values "Updated Status"
gdoc sheet-update "<URL>" --range "Sheet1!A2:B2" --values '[["Value A", "Value B"]]'

# Append a row to the table:
gdoc sheet-append "<URL>" --values "Product A, 199.99, Active"
```

---

## 🤖 Connecting to AI Assistants

### Claude Code
Add to your project's `CLAUDE.md` or `.claude/settings.json`:
```json
{
  "allowedTools": [
    "Bash(gdoc *)",
    "PowerShell(gdoc *)",
    "Bash(gsheet *)",
    "PowerShell(gsheet *)"
  ]
}
```

### Cursor IDE
Copy [`templates/.cursorrules`](templates/.cursorrules) into your project root. Cursor will automatically use `gdoc` whenever you ask it about Google Docs.

### Cline / Roo Code
Copy [`templates/.clinerules`](templates/.clinerules) into your project root.

---

## 🛡️ Security & Privacy

- **No Third-Party Servers:** All requests go directly from your local machine to Google Cloud official endpoints via HTTPS.
- **Tokens are Local:** Your credentials and OAuth tokens are stored exclusively in your local `~/.gdoc/` folder, never uploaded anywhere.
- **Git Protected:** `.gitignore` includes strict rules preventing credentials and tokens from ever being committed.

---

## 📄 License

MIT License. Free to use, modify, and distribute. See [LICENSE](LICENSE) for details.

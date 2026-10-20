# Claude Code Guide for Google Docs & Google Sheets

You have access to a global command-line utility `gdoc` (and `gsheet`) to read and edit Google Docs and Google Sheets directly from the terminal.

## Core Principles
1. **Never ask for passwords or API keys in chat.** Global authentication is already configured in `~/.gdoc/`.
2. **Backups are automatic.** Every modifying command (`replace`, `append`, `insert`, `sheet-update`, `sheet-append`) automatically creates a timestamped clone of the file in Google Drive before modifying it.
3. **URL or Bare ID.** You can pass either the full Google URL or just the ID string.

## Google Docs Commands
- **Read entire document:**
  ```bash
  gdoc read "<DOC_URL_OR_ID>"
  ```
- **Replace text (exact match across document):**
  ```bash
  gdoc replace "<DOC_URL_OR_ID>" --find "<OLD_TEXT>" --replace "<NEW_TEXT>"
  ```
- **Append new paragraph to the end:**
  ```bash
  gdoc append "<DOC_URL_OR_ID>" --text "<TEXT_TO_APPEND>"
  ```
- **List comments and discussion threads:**
  ```bash
  gdoc comments "<DOC_URL_OR_ID>"
  ```
- **Reply to a comment thread:**
  ```bash
  gdoc reply "<DOC_URL_OR_ID>" --comment-id "<COMMENT_ID>" --text "<REPLY_TEXT>"
  ```

## Google Sheets Commands
- **Inspect sheet tabs and dimensions:**
  ```bash
  gdoc sheet-info "<SHEET_URL_OR_ID>"
  ```
- **Read table values (formatted text or JSON):**
  ```bash
  gdoc sheet-read "<SHEET_URL_OR_ID>" --range "Sheet1!A1:D20"
  gdoc sheet-read "<SHEET_URL_OR_ID>" --json
  gdoc sheet-read "<SHEET_URL_OR_ID>" --csv
  ```
- **Update specific cells:**
  ```bash
  gdoc sheet-update "<SHEET_URL_OR_ID>" --range "Sheet1!B2" --values "New Value"
  gdoc sheet-update "<SHEET_URL_OR_ID>" --range "Sheet1!A2:B2" --values '[["Col1", "Col2"]]'
  ```
- **Append a row to the end:**
  ```bash
  gdoc sheet-append "<SHEET_URL_OR_ID>" --values "Value1, Value2, Value3"
  ```

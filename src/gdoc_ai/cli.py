#!/usr/bin/env python3
"""
Global Google Docs & Sheets CLI Tool (gdoc / gsheet)
Enables any AI assistant or developer in VS Code across all projects to:
- Authenticate once globally with multiple account profiles (--profile)
- Read & edit Google Docs (search/replace, append, insert, comments)
- Read & edit Google Sheets (read ranges, update cells, append rows, list sheets)
- Create backups automatically before editing
"""

import os
import re
import sys
import csv
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

GLOBAL_DIR = Path.home() / '.gdoc'
GLOBAL_CREDS = GLOBAL_DIR / 'credentials.json'
GLOBAL_TOKEN = GLOBAL_DIR / 'token.json'


def find_credentials_file() -> Path:
    """Find credentials.json in global ~/.gdoc or local .secrets/ directory."""
    if GLOBAL_CREDS.exists():
        return GLOBAL_CREDS
    local_creds = Path.cwd() / '.secrets' / 'credentials.json'
    if local_creds.exists():
        return local_creds
    return GLOBAL_CREDS


def find_token_file(profile: str = "default") -> Path:
    """Find token file for specific profile."""
    if profile and profile != "default":
        return GLOBAL_DIR / f"token_{profile}.json"
    if GLOBAL_TOKEN.exists():
        return GLOBAL_TOKEN
    local_token = Path.cwd() / '.secrets' / 'token.json'
    if local_token.exists():
        return local_token
    return GLOBAL_TOKEN


def extract_id(id_or_url: str) -> str:
    """Extract document/spreadsheet ID from raw ID or Google URL."""
    if not id_or_url:
        raise ValueError("ID or URL cannot be empty.")
    match = re.search(r'/(?:document|spreadsheets)/d/([a-zA-Z0-9_-]+)', id_or_url)
    if match:
        return match.group(1)
    match_general = re.search(r'/d/([a-zA-Z0-9_-]+)', id_or_url)
    if match_general:
        return match_general.group(1)
    return id_or_url.strip()


def get_credentials(profile: str = "default") -> Any:
    """Authenticate via OAuth Desktop App or Service Account."""
    GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
    creds_file = find_credentials_file()
    token_file = find_token_file(profile)

    if not creds_file.exists():
        print(f"\n[ERROR] Credentials file not found!", file=sys.stderr)
        print(f"Looked in:\n  1. {GLOBAL_CREDS}\n  2. {Path.cwd() / '.secrets' / 'credentials.json'}", file=sys.stderr)
        print("\nPlease save your downloaded Google Cloud OAuth JSON as:", file=sys.stderr)
        print(f"  {GLOBAL_CREDS}\n", file=sys.stderr)
        sys.exit(1)

    try:
        with open(creds_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[!] Error parsing {creds_file}: {e}", file=sys.stderr)
        sys.exit(1)

    if data.get('type') == 'service_account':
        return service_account.Credentials.from_service_account_file(
            str(creds_file),
            scopes=SCOPES
        )

    creds = None
    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print(f"[*] Refreshing expired token (profile: {profile})...", file=sys.stderr)
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            print(f"[*] Launching browser for Google login (profile: {profile})...", file=sys.stderr)
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, 'w', encoding='utf-8') as f:
            f.write(creds.to_json())
        print(f"[+] Token for profile '{profile}' saved to {token_file}", file=sys.stderr)

    return creds


def get_services(profile: str = "default"):
    """Return Docs, Drive, and Sheets API service clients."""
    creds = get_credentials(profile)
    docs = build('docs', 'v1', credentials=creds)
    drive = build('drive', 'v3', credentials=creds)
    sheets = build('sheets', 'v4', credentials=creds)
    return docs, drive, sheets


def create_backup(file_id: str, prefix: str = "[Backup]", profile: str = "default") -> Dict[str, str]:
    """Create a backup copy in Google Drive."""
    file_id = extract_id(file_id)
    _, drive, _ = get_services(profile)

    try:
        meta = drive.files().get(fileId=file_id, fields="name").execute()
        orig_name = meta.get("name", "Document")
    except Exception:
        orig_name = "Document"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    backup_name = f"{prefix} {orig_name} ({timestamp})"

    try:
        copied = drive.files().copy(
            fileId=file_id,
            body={'name': backup_name},
            fields="id, name, webViewLink"
        ).execute()
        print(f"[Backup Created] Name: {copied.get('name')}", file=sys.stderr)
        print(f"                 ID:   {copied.get('id')}", file=sys.stderr)
        print(f"                 URL:  {copied.get('webViewLink')}", file=sys.stderr)
        return copied
    except Exception as e:
        print(f"[!] Warning: Backup could not be created: {e}", file=sys.stderr)
        return {}


# ==================== GOOGLE DOCS FUNCTIONS ====================

def parse_structural_elements(elements: List[Dict[str, Any]]) -> str:
    """Extract plain text from Docs structure."""
    out = []
    for elem in elements:
        if 'paragraph' in elem:
            for p in elem['paragraph'].get('elements', []):
                t = p.get('textRun', {}).get('content', '')
                if t:
                    out.append(t)
        elif 'table' in elem:
            for row in elem['table'].get('tableRows', []):
                cells = []
                for cell in row.get('tableCells', []):
                    cells.append(parse_structural_elements(cell.get('content', [])).strip())
                out.append(" | ".join(cells) + "\n")
    return "".join(out)


def cmd_read(args):
    prof = getattr(args, 'profile', 'default')
    doc_id = extract_id(args.id_or_url)
    docs, _, _ = get_services(prof)
    doc = docs.documents().get(documentId=doc_id).execute()
    title = doc.get('title', 'Untitled')
    content = doc.get('body', {}).get('content', [])
    text = parse_structural_elements(content)

    if args.save_to:
        p = Path(args.save_to)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        print(f"[+] Saved {title} to {p.resolve()}", file=sys.stderr)
    else:
        sys.stdout.write(text)


def cmd_replace(args):
    prof = getattr(args, 'profile', 'default')
    doc_id = extract_id(args.id_or_url)
    if not args.no_backup:
        create_backup(doc_id, profile=prof)

    docs, _, _ = get_services(prof)
    requests = [{
        'replaceAllText': {
            'containsText': {
                'text': args.find,
                'matchCase': not args.ignore_case
            },
            'replaceText': args.replace
        }
    }]
    res = docs.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
    replies = res.get('replies', [])
    count = 0
    if replies and 'replaceAllText' in replies[0]:
        count = replies[0]['replaceAllText'].get('occurrencesChanged', 0)
    print(f"[+] Replaced {count} occurrence(s) of '{args.find}' -> '{args.replace}'")


def cmd_append(args):
    prof = getattr(args, 'profile', 'default')
    doc_id = extract_id(args.id_or_url)
    if not args.no_backup:
        create_backup(doc_id, profile=prof)

    docs, _, _ = get_services(prof)
    doc = docs.documents().get(documentId=doc_id).execute()
    body_content = doc.get('body', {}).get('content', [])
    end_idx = body_content[-1].get('endIndex', 1) - 1 if body_content else 1
    if end_idx < 1:
        end_idx = 1

    requests = [{
        'insertText': {
            'location': {'index': end_idx},
            'text': args.text
        }
    }]
    docs.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
    print(f"[+] Appended text to end of document (index {end_idx})")


def cmd_insert(args):
    prof = getattr(args, 'profile', 'default')
    doc_id = extract_id(args.id_or_url)
    if not args.no_backup:
        create_backup(doc_id, profile=prof)

    docs, _, _ = get_services(prof)
    requests = [{
        'insertText': {
            'location': {'index': args.index},
            'text': args.text
        }
    }]
    docs.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
    print(f"[+] Inserted text at index {args.index}")


def cmd_comments(args):
    prof = getattr(args, 'profile', 'default')
    doc_id = extract_id(args.id_or_url)
    _, drive, _ = get_services(prof)
    resp = drive.comments().list(
        fileId=doc_id,
        fields="comments(id,author(displayName),content,createdTime,resolved,replies(id,author(displayName),content,createdTime))"
    ).execute()

    comments = resp.get('comments', [])
    print(f"=== Comments ({len(comments)}) ===")
    for idx, c in enumerate(comments, 1):
        status = "[RESOLVED]" if c.get('resolved') else "[OPEN]"
        author = c.get('author', {}).get('displayName', 'User')
        cid = c.get('id', '')
        print(f"\n{idx}. {status} [ID: {cid}] {author}: {c.get('content', '')}")
        for r in c.get('replies', []):
            ra = r.get('author', {}).get('displayName', 'User')
            print(f"     -> {ra}: {r.get('content', '')}")


def cmd_reply(args):
    prof = getattr(args, 'profile', 'default')
    doc_id = extract_id(args.id_or_url)
    _, drive, _ = get_services(prof)
    drive.replies().create(
        fileId=doc_id,
        commentId=args.comment_id,
        body={'content': args.text},
        fields="id,content"
    ).execute()
    print(f"[+] Replied to comment {args.comment_id}: {args.text}")


# ==================== GOOGLE SHEETS FUNCTIONS ====================

def cmd_sheet_info(args):
    prof = getattr(args, 'profile', 'default')
    sheet_id = extract_id(args.id_or_url)
    _, _, sheets = get_services(prof)
    res = sheets.spreadsheets().get(spreadsheetId=sheet_id).execute()
    title = res.get('properties', {}).get('title', 'Untitled')
    print(f"=== Spreadsheet: {title} (ID: {sheet_id}) ===")
    print("Tabs / Sheets:")
    for s in res.get('sheets', []):
        props = s.get('properties', {})
        stitle = props.get('title', '')
        grid = props.get('gridProperties', {})
        rows = grid.get('rowCount', 0)
        cols = grid.get('columnCount', 0)
        print(f"  - '{stitle}' (Rows: {rows}, Columns: {cols})")


def cmd_sheet_read(args):
    prof = getattr(args, 'profile', 'default')
    sheet_id = extract_id(args.id_or_url)
    _, _, sheets = get_services(prof)

    range_name = args.range
    if not range_name:
        meta = sheets.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets_list = meta.get('sheets', [])
        if sheets_list:
            range_name = sheets_list[0]['properties']['title']
        else:
            range_name = 'Sheet1'

    res = sheets.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=range_name
    ).execute()

    rows = res.get('values', [])
    if not rows:
        print("[!] No data found in the specified range.", file=sys.stderr)
        return

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    elif args.csv:
        writer = csv.writer(sys.stdout)
        for row in rows:
            writer.writerow(row)
    else:
        max_cols = max(len(r) for r in rows) if rows else 0
        col_widths = [0] * max_cols
        for row in rows:
            for idx, cell in enumerate(row):
                col_widths[idx] = max(col_widths[idx], len(str(cell)))

        for row in rows:
            padded = [str(cell).ljust(col_widths[idx]) for idx, cell in enumerate(row)]
            print(" | ".join(padded))


def cmd_sheet_append(args):
    prof = getattr(args, 'profile', 'default')
    sheet_id = extract_id(args.id_or_url)
    if not args.no_backup:
        create_backup(sheet_id, profile=prof)

    _, _, sheets = get_services(prof)
    try:
        val_data = json.loads(args.values)
        if not isinstance(val_data, list):
            val_data = [[val_data]]
        elif val_data and not isinstance(val_data[0], list):
            val_data = [val_data]
    except json.JSONDecodeError:
        val_data = [[v.strip() for v in args.values.split(",")]]

    range_target = args.range or "Sheet1!A1"
    body = {'values': val_data}
    res = sheets.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=range_target,
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

    updated_range = res.get('updates', {}).get('updatedRange', '')
    updated_rows = res.get('updates', {}).get('updatedRows', 0)
    print(f"[+] Appended {updated_rows} row(s) at range {updated_range}")


def cmd_sheet_update(args):
    prof = getattr(args, 'profile', 'default')
    sheet_id = extract_id(args.id_or_url)
    if not args.no_backup:
        create_backup(sheet_id, profile=prof)

    _, _, sheets = get_services(prof)
    try:
        val_data = json.loads(args.values)
        if not isinstance(val_data, list):
            val_data = [[val_data]]
        elif val_data and not isinstance(val_data[0], list):
            val_data = [val_data]
    except json.JSONDecodeError:
        val_data = [[v.strip() for v in args.values.split(",")]]

    body = {'values': val_data}
    res = sheets.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=args.range,
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

    cells = res.get('updatedCells', 0)
    print(f"[+] Updated {cells} cell(s) in range {args.range}")


def col_to_idx(col: str) -> int:
    res = 0
    for c in col.upper():
        res = res * 26 + (ord(c) - ord('A') + 1)
    return res - 1


def parse_a1_notation(a1_str: str) -> dict:
    s = a1_str.strip()
    sheet_name = None
    if '!' in s:
        parts = s.split('!', 1)
        sheet_name = parts[0].strip("'\"")
        cells = parts[1].strip()
    else:
        cells = s

    if ':' in cells:
        start_cell, end_cell = cells.split(':', 1)
    else:
        start_cell = cells
        end_cell = None

    m_start = re.match(r'^([A-Za-z]+)(\d+)$', start_cell)
    if not m_start:
        raise ValueError(f"Invalid start cell in A1 notation: {start_cell}")

    start_col = col_to_idx(m_start.group(1))
    start_row = int(m_start.group(2)) - 1

    if end_cell:
        m_end = re.match(r'^([A-Za-z]+)(\d+)$', end_cell)
        if not m_end:
            raise ValueError(f"Invalid end cell in A1 notation: {end_cell}")
        end_col = col_to_idx(m_end.group(1)) + 1
        end_row = int(m_end.group(2))
    else:
        end_col = start_col + 1
        end_row = start_row + 1

    return {
        'sheet_name': sheet_name,
        'start_row': start_row,
        'end_row': end_row,
        'start_col': start_col,
        'end_col': end_col
    }


def cmd_sheet_create(args):
    prof = getattr(args, 'profile', 'default')
    _, drive, sheets = get_services(prof)

    body = {
        'properties': {
            'title': args.title
        }
    }
    res = sheets.spreadsheets().create(body=body, fields='spreadsheetId,spreadsheetUrl').execute()
    sheet_id = res.get('spreadsheetId')
    url = res.get('spreadsheetUrl')

    if getattr(args, 'folder_id', None):
        drive.files().update(
            fileId=sheet_id,
            addParents=args.folder_id,
            fields='id, parents'
        ).execute()

    print(f"[+] Created Google Spreadsheet successfully!")
    print(f"Spreadsheet ID:  {sheet_id}")
    print(f"Spreadsheet URL: {url}")


def cmd_sheet_add_tab(args):
    prof = getattr(args, 'profile', 'default')
    sheet_id = extract_id(args.id_or_url)
    if not getattr(args, 'no_backup', False):
        create_backup(sheet_id, profile=prof)

    _, _, sheets = get_services(prof)
    req = {
        'requests': [{
            'addSheet': {
                'properties': {
                    'title': args.title
                }
            }
        }]
    }
    res = sheets.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=req).execute()
    added = res.get('replies', [{}])[0].get('addSheet', {}).get('properties', {})
    print(f"[+] Added new tab '{added.get('title')}' (Sheet ID: {added.get('sheetId')})")


def cmd_sheet_chart(args):
    prof = getattr(args, 'profile', 'default')
    sheet_id = extract_id(args.id_or_url)
    if not getattr(args, 'no_backup', False):
        create_backup(sheet_id, profile=prof)

    _, _, sheets = get_services(prof)

    meta = sheets.spreadsheets().get(spreadsheetId=sheet_id, fields="sheets(properties(sheetId,title))").execute()
    sheets_list = meta.get('sheets', [])
    sheet_map = {s['properties']['title']: s['properties']['sheetId'] for s in sheets_list}
    first_sheet_id = sheets_list[0]['properties']['sheetId'] if sheets_list else 0

    parsed = parse_a1_notation(args.range)
    if parsed['sheet_name']:
        target_sheet_id = sheet_map.get(parsed['sheet_name'], first_sheet_id)
    else:
        target_sheet_id = first_sheet_id

    chart_type = args.type.upper() if args.type else "COLUMN"
    title = args.title or f"{chart_type.capitalize()} Chart"

    # Anchor placement
    if args.anchor:
        parsed_anchor = parse_a1_notation(args.anchor)
        if parsed_anchor['sheet_name']:
            anchor_sheet_id = sheet_map.get(parsed_anchor['sheet_name'], target_sheet_id)
        else:
            anchor_sheet_id = target_sheet_id
        anchor_row = parsed_anchor['start_row']
        anchor_col = parsed_anchor['start_col']
    else:
        anchor_sheet_id = target_sheet_id
        anchor_row = parsed['start_row']
        anchor_col = parsed['end_col'] + 1

    width = args.width or 600
    height = args.height or 370

    position = {
        'overlayPosition': {
            'anchorCell': {
                'sheetId': anchor_sheet_id,
                'rowIndex': anchor_row,
                'columnIndex': anchor_col
            },
            'widthPixels': width,
            'heightPixels': height
        }
    }

    if chart_type == "PIE":
        spec = {
            'title': title,
            'pieChart': {
                'legendPosition': 'RIGHT_LEGEND',
                'domain': {
                    'sourceRange': {
                        'sources': [{
                            'sheetId': target_sheet_id,
                            'startRowIndex': parsed['start_row'],
                            'endRowIndex': parsed['end_row'],
                            'startColumnIndex': parsed['start_col'],
                            'endColumnIndex': parsed['start_col'] + 1
                        }]
                    }
                },
                'series': {
                    'sourceRange': {
                        'sources': [{
                            'sheetId': target_sheet_id,
                            'startRowIndex': parsed['start_row'],
                            'endRowIndex': parsed['end_row'],
                            'startColumnIndex': parsed['start_col'] + 1,
                            'endColumnIndex': parsed['start_col'] + 2
                        }]
                    }
                },
                'threeDimensional': False
            }
        }
    else:
        if parsed['end_col'] - parsed['start_col'] == 1:
            domains = []
            series = [{
                'series': {
                    'sourceRange': {
                        'sources': [{
                            'sheetId': target_sheet_id,
                            'startRowIndex': parsed['start_row'],
                            'endRowIndex': parsed['end_row'],
                            'startColumnIndex': parsed['start_col'],
                            'endColumnIndex': parsed['end_col']
                        }]
                    }
                },
                'targetAxis': 'LEFT_AXIS'
            }]
        else:
            domains = [{
                'domain': {
                    'sourceRange': {
                        'sources': [{
                            'sheetId': target_sheet_id,
                            'startRowIndex': parsed['start_row'],
                            'endRowIndex': parsed['end_row'],
                            'startColumnIndex': parsed['start_col'],
                            'endColumnIndex': parsed['start_col'] + 1
                        }]
                    }
                }
            }]
            series = []
            for col_idx in range(parsed['start_col'] + 1, parsed['end_col']):
                series.append({
                    'series': {
                        'sourceRange': {
                            'sources': [{
                                'sheetId': target_sheet_id,
                                'startRowIndex': parsed['start_row'],
                                'endRowIndex': parsed['end_row'],
                                'startColumnIndex': col_idx,
                                'endColumnIndex': col_idx + 1
                            }]
                        }
                    },
                    'targetAxis': 'LEFT_AXIS'
                })

        axis = []
        if getattr(args, 'x_title', None):
            axis.append({'position': 'BOTTOM_AXIS', 'title': args.x_title})
        if getattr(args, 'y_title', None):
            axis.append({'position': 'LEFT_AXIS', 'title': args.y_title})

        spec = {
            'title': title,
            'basicChart': {
                'chartType': chart_type,
                'legendPosition': 'BOTTOM_LEGEND',
                'axis': axis,
                'domains': domains,
                'series': series,
                'headerCount': 1
            }
        }

    req = {
        'requests': [{
            'addChart': {
                'chart': {
                    'spec': spec,
                    'position': position
                }
            }
        }]
    }

    res = sheets.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=req).execute()
    new_chart = res.get('replies', [{}])[0].get('addChart', {}).get('chart', {})
    chart_id = new_chart.get('chartId', '<generated>')
    print(f"[+] Chart '{title}' ({chart_type}) added successfully! (Chart ID: {chart_id})")


def cmd_status(args):
    prof = getattr(args, 'profile', 'default')
    creds_file = find_credentials_file()
    token_file = find_token_file(prof)
    print(f"=== Google Docs & Sheets Status (Profile: '{prof}') ===")
    print(f"Credentials location: {creds_file} (Exists: {creds_file.exists()})")
    print(f"Token location:       {token_file} (Exists: {token_file.exists()})")
    if not creds_file.exists():
        print("[-] Status: Please put credentials.json in ~/.gdoc/credentials.json")
    elif not token_file.exists():
        print(f"[!] Status: credentials.json present! Run 'gdoc auth --profile {prof}' to authorize.")
    else:
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
            if creds and creds.valid:
                print(f"[+] Status: Authentication is VALID and READY for profile '{prof}'!")
            elif creds and creds.expired and creds.refresh_token:
                print(f"[*] Status: Token for profile '{prof}' expired, will refresh automatically.")
            else:
                print(f"[!] Status: Token invalid, please run 'gdoc auth --profile {prof}'.")
        except Exception as e:
            print(f"[-] Status: Error verifying token: {e}")


def main():
    # Common parent parser with --profile
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--profile", default=argparse.SUPPRESS, help="Google account profile (e.g. 'work', 'personal')")

    parser = argparse.ArgumentParser(
        prog="gdoc",
        description="Global Google Docs & Sheets CLI for AI assistants and developers.",
        parents=[common_parser]
    )
    sub = parser.add_subparsers(dest="subcommand", help="Command to run")

    # Common
    sub.add_parser("auth", help="Run one-time OAuth authentication", parents=[common_parser])
    sub.add_parser("status", help="Check credentials and authentication status", parents=[common_parser])

    p_back = sub.add_parser("backup", help="Create a backup copy in Google Drive", parents=[common_parser])
    p_back.add_argument("id_or_url", help="Google Doc or Sheet URL/ID")
    p_back.add_argument("--prefix", default="[Backup]", help="Backup title prefix")

    # Docs
    p_read = sub.add_parser("read", help="Read Google Doc content", parents=[common_parser])
    p_read.add_argument("id_or_url", help="Google Doc URL or Document ID")
    p_read.add_argument("--save-to", help="Path to save document text")

    p_rep = sub.add_parser("replace", help="Find and replace text in Google Doc", parents=[common_parser])
    p_rep.add_argument("id_or_url", help="Google Doc URL or Document ID")
    p_rep.add_argument("--find", required=True, help="Text to search for")
    p_rep.add_argument("--replace", required=True, help="Replacement text")
    p_rep.add_argument("--ignore-case", action="store_true", help="Case-insensitive search")
    p_rep.add_argument("--no-backup", action="store_true", help="Skip backup creation")

    p_app = sub.add_parser("append", help="Append text to end of Google Doc", parents=[common_parser])
    p_app.add_argument("id_or_url", help="Google Doc URL or Document ID")
    p_app.add_argument("--text", required=True, help="Text to append")
    p_app.add_argument("--no-backup", action="store_true", help="Skip backup creation")

    p_ins = sub.add_parser("insert", help="Insert text at specific character index", parents=[common_parser])
    p_ins.add_argument("id_or_url", help="Google Doc URL or Document ID")
    p_ins.add_argument("--text", required=True, help="Text to insert")
    p_ins.add_argument("--index", type=int, default=1, help="Index position")
    p_ins.add_argument("--no-backup", action="store_true", help="Skip backup creation")

    p_com = sub.add_parser("comments", help="List comments in Google Doc", parents=[common_parser])
    p_com.add_argument("id_or_url", help="Google Doc URL or Document ID")

    p_repcom = sub.add_parser("reply", help="Reply to a comment", parents=[common_parser])
    p_repcom.add_argument("id_or_url", help="Google Doc URL or Document ID")
    p_repcom.add_argument("--comment-id", required=True, help="Comment ID")
    p_repcom.add_argument("--text", required=True, help="Reply text")

    # Sheets
    p_sinfo = sub.add_parser("sheet-info", help="Get spreadsheet metadata and tab list", parents=[common_parser])
    p_sinfo.add_argument("id_or_url", help="Google Sheet URL or Spreadsheet ID")

    p_sread = sub.add_parser("sheet-read", help="Read values from Google Sheet", parents=[common_parser])
    p_sread.add_argument("id_or_url", help="Google Sheet URL or Spreadsheet ID")
    p_sread.add_argument("--range", help="Sheet range (e.g. 'Sheet1!A1:D20' or 'TabName')")
    p_sread.add_argument("--csv", action="store_true", help="Output in CSV format")
    p_sread.add_argument("--json", action="store_true", help="Output in JSON format")

    p_supdate = sub.add_parser("sheet-update", help="Update cells in Google Sheet", parents=[common_parser])
    p_supdate.add_argument("id_or_url", help="Google Sheet URL or Spreadsheet ID")
    p_supdate.add_argument("--range", required=True, help="Target cell/range (e.g. 'Sheet1!A2')")
    p_supdate.add_argument("--values", required=True, help="JSON array of values (e.g. '[[\"A\", \"B\"]]') or comma-separated")
    p_supdate.add_argument("--no-backup", action="store_true", help="Skip backup creation")

    p_sapp = sub.add_parser("sheet-append", help="Append row(s) to Google Sheet", parents=[common_parser])
    p_sapp.add_argument("id_or_url", help="Google Sheet URL or Spreadsheet ID")
    p_sapp.add_argument("--values", required=True, help="JSON array of values or comma-separated")
    p_sapp.add_argument("--range", help="Target sheet/range (default 'Sheet1!A1')")
    p_sapp.add_argument("--no-backup", action="store_true", help="Skip backup creation")

    # Sheet create
    p_screate = sub.add_parser("sheet-create", help="Create a new Google Spreadsheet", parents=[common_parser])
    p_screate.add_argument("--title", required=True, help="Title of the new spreadsheet")
    p_screate.add_argument("--folder-id", help="Optional Google Drive folder ID to place the spreadsheet in")

    # Sheet add tab
    p_saddtab = sub.add_parser("sheet-add-tab", help="Add a new tab/sheet to an existing spreadsheet", parents=[common_parser])
    p_saddtab.add_argument("id_or_url", help="Google Sheet URL or Spreadsheet ID")
    p_saddtab.add_argument("--title", required=True, help="Title of the new tab")
    p_saddtab.add_argument("--no-backup", action="store_true", help="Skip backup creation")

    # Sheet chart
    p_schart = sub.add_parser("sheet-chart", help="Add a chart to a Google Sheet", parents=[common_parser])
    p_schart.add_argument("id_or_url", help="Google Sheet URL or Spreadsheet ID")
    p_schart.add_argument("--range", required=True, help="Data range in A1 notation (e.g. 'Sheet1!A1:C10')")
    p_schart.add_argument("--type", choices=["COLUMN", "BAR", "LINE", "AREA", "PIE", "SCATTER", "COMBO"], default="COLUMN", help="Chart type (default: COLUMN)")
    p_schart.add_argument("--title", help="Chart title")
    p_schart.add_argument("--anchor", help="Top-left cell where the chart will float (e.g. 'E2' or 'Sheet1!E2')")
    p_schart.add_argument("--x-title", help="Title for the X-axis (horizontal)")
    p_schart.add_argument("--y-title", help="Title for the Y-axis (vertical)")
    p_schart.add_argument("--width", type=int, default=600, help="Chart width in pixels (default: 600)")
    p_schart.add_argument("--height", type=int, default=370, help="Chart height in pixels (default: 370)")
    p_schart.add_argument("--no-backup", action="store_true", help="Skip backup creation")

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    try:
        prof = getattr(args, 'profile', 'default')
        if args.subcommand == "auth":
            get_credentials(prof)
            print(f"[+] Authentication successful for profile '{prof}'!")
        elif args.subcommand == "status":
            cmd_status(args)
        elif args.subcommand == "backup":
            create_backup(args.id_or_url, args.prefix, profile=prof)
        elif args.subcommand == "read":
            cmd_read(args)
        elif args.subcommand == "replace":
            cmd_replace(args)
        elif args.subcommand == "append":
            cmd_append(args)
        elif args.subcommand == "insert":
            cmd_insert(args)
        elif args.subcommand == "comments":
            cmd_comments(args)
        elif args.subcommand == "reply":
            cmd_reply(args)
        elif args.subcommand == "sheet-info":
            cmd_sheet_info(args)
        elif args.subcommand == "sheet-read":
            cmd_sheet_read(args)
        elif args.subcommand == "sheet-update":
            cmd_sheet_update(args)
        elif args.subcommand == "sheet-append":
            cmd_sheet_append(args)
        elif args.subcommand == "sheet-create":
            cmd_sheet_create(args)
        elif args.subcommand == "sheet-add-tab":
            cmd_sheet_add_tab(args)
        elif args.subcommand == "sheet-chart":
            cmd_sheet_chart(args)
    except HttpError as e:
        print(f"[!] Google API Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[!] Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

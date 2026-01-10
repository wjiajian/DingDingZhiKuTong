# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DingDingZhiKuTong is a DingTalk knowledge base synchronization toolkit for enterprise AI assistant knowledge base file synchronization. It performs incremental one-way sync between DingTalk knowledge bases and local NAS storage.

## Architecture

This project uses a three-stage workflow:

1. **API Data Fetching** (`get_KB_FILE_URL.py`)
   - Fetches DingTalk API access token (via `getToken.py`)
   - Recursively traverses the knowledge base file tree (supports subfolder filtering)
   - Scans local NAS file tree
   - Compares file trees and generates differential list
   - Outputs: `kb_tree.json` (complete structure) + `urls_to_download.txt` (files to download)

2. **Manual Download** (RPA implementation)
   - User downloads files from URLs in `urls_to_download.txt`
   - Files must be organized in a source directory matching the knowledge base structure

3. **File Synchronization** (`compare_move_file.py`)
   - Reads `kb_tree.json` as the authoritative source
   - **Cleanup Phase**: Deletes files and empty directories in NAS that don't exist in `kb_tree.json`
   - **Move Phase**: Moves new files from source directory to correct NAS locations
   - Supports both dry-run mode (preview) and live execution

## Key Dependencies

Install DingTalk SDK dependencies:
```bash
pip install alibabacloud_dingtalk alibabacloud_tea_openapi alibabacloud_tea_util
```

## Configuration

All configuration is done via global variables in the Python files:

**In `get_KB_FILE_URL.py`:**
- `ACCESS_TOKEN` - DingTalk API access token (from `getToken.py`)
- `OPERATOR_ID` - Operator's unionId
- `WORKSPACE_NAME` - Full name of target knowledge base
- `NAS_ROOT_PATH` - Local target folder path
- `USE_SYNC_FILTER` - Enable/disable subfolder path filtering
- `SYNC_FILTERS` - List of subfolder paths to sync (when filtering enabled)

**In `compare_move_file.py`:**
- `KB_TREE_JSON` - Path to `kb_tree.json` from step 1
- `SOURCE_DIR` - Directory with newly downloaded files
- `DEST_DIR` - Final NAS target directory
- `dry_run` parameter - Set `True` for preview, `False` for execution

## File Extension Mapping

The tool automatically converts DingTalk proprietary extensions to standard Office formats:
- `.adoc` → `.docx`
- `.axls` → `.xlsx`
- `.appt` → `.pptx`
- `.atxt` → `.txt`
- `.apdf` → `.pdf`

## Important Notes

- Always run `compare_move_file.py` in dry-run mode first to preview operations
- The `kb_tree.json` file is the single source of truth for synchronization
- This is a one-way sync: DingTalk → Local (changes are never pushed back)
- The manual download step (step 2) is designed for RPA automation
- File trees use dictionaries for folders and lists for children

## Related Project

For processing Excel-linked document attachments, see [LinkContentAI](https://github.com/wjiajian/LinkContentAI).

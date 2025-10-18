import os
import base64
import mimetypes
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

TMP_DIR = Path("/tmp/llm_attachments")
TMP_DIR.mkdir(parents=True, exist_ok=True)

def decode_attachments(attachments):
    """
    attachments: list of {name, url: data:<mime>;base64,<b64>}
    Saves files into /tmp/llm_attachments/<name>
    Returns list of dicts: {"name": name, "path": "/tmp/..", "mime": mime, "size": n}
    """
    saved = []
    for att in attachments or []:
        name = att.get("name") or "attachment"
        url = att.get("url", "")
        if not url.startswith("data:"):
            continue
        try:
            header, b64data = url.split(",", 1)
            mime = header.split(";")[0].replace("data:", "")
            data = base64.b64decode(b64data)
            path = TMP_DIR / name
            with open(path, "wb") as f:
                f.write(data)
            saved.append({
                "name": name,
                "path": str(path),
                "mime": mime,
                "size": len(data)
            })
        except Exception as e:
            print("Failed to decode attachment", name, e)
    return saved

def summarize_attachment_meta(saved):
    """
    saved is list from decode_attachments.
    Returns a short human-readable summary string for the prompt.
    """
    summaries = []
    for s in saved:
        nm = s["name"]
        p = s["path"]
        mime = s.get("mime", "")
        try:
            if mime.startswith("text") or nm.endswith((".md", ".txt", ".json", ".csv")):
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    if nm.endswith(".csv"):
                        lines = [next(f).strip() for _ in range(3)]
                        preview = "\\n".join(lines)
                    else:
                        data = f.read(1000)
                        preview = data.replace("\n", "\\n")[:1000]
                summaries.append(f"- {nm} ({mime}): preview: {preview}")
            else:
                summaries.append(f"- {nm} ({mime}): {s['size']} bytes")
        except Exception as e:
            summaries.append(f"- {nm} ({mime}): (could not read preview: {e})")
    return "\\n".join(summaries)

def _strip_code_block(text: str) -> str:
    """
    If text is inside triple-backticks, return inner contents. Otherwise return text as-is.
    """
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            return parts[1].strip()
    return text.strip()

def generate_readme_fallback(brief: str, checks=None, attachments_meta=None, round_num=1):
    checks_text = "\\n".join(checks or [])
    att_text = attachments_meta or ""
    return f"""# Auto-generated README (Round {round_num})

**Project brief:** {brief}

**Attachments:**
{att_text}

**Checks to meet:**
{checks_text}

## Setup
1. Open `index.html` in a browser.
2. No build steps required.

## Notes
This README was generated as a fallback (OpenAI did not return an explicit README).
"""

def generate_app_code(brief: str, attachments=None, checks=None, round_num=1, prev_readme=None):
    """
    Generate or revise an app using the OpenAI Responses API.
    - round_num=1: build from scratch
    - round_num=2: refactor based on new brief and previous README/code
    """
    saved = decode_attachments(attachments or [])
    attachments_meta = summarize_attachment_meta(saved)

    context_note = ""
    if round_num == 2 and prev_readme:
        context_note = f"\n### Previous README.md:\n{prev_readme}\n\nRevise and enhance this project according to the new brief below.\n"

    user_prompt = f"""
You are a professional web developer assistant.

### Round
{round_num}

### Task
{brief}

{context_note}

### Attachments (if any)
{attachments_meta}

### Evaluation checks
{checks or []}

### Output format rules:
1. Produce a complete single-file web application that satisfies the brief requirements.
2. Output must contain **exactly two parts**:
   - First part: Complete index.html code (including DOCTYPE, html, head, body tags)
   - Second part: README.md content (starts after a line containing exactly: ---README.md---)
3. The index.html must be a SINGLE FILE containing:
   - All HTML structure
   - All CSS styles (inline in <style> tags or inline styles)
   - All JavaScript logic (inline in <script> tags)
   - Complete functionality to fulfill the brief requirements
4. README.md must include:
   - Overview of the application
   - Setup instructions (just open index.html in browser)
   - Usage instructions
   - If Round 2, describe improvements made from previous version.
5. Do not include any commentary outside the HTML code or README content.
6. The index.html must be completely self-contained - no external dependencies except CDN links if specifically requested.
7. Use the separator line "---README.md---" exactly as shown to separate the two parts.
"""

    try:
        import requests
        token = OPENAI_API_KEY
        if not token:
            raise RuntimeError("OPENAI_API_KEY is not set in environment")

        url = "https://aipipe.org/openrouter/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-nano"),
            "messages": [
                {"role": "system", "content": "You are a helpful coding assistant that outputs runnable web apps."},
                {"role": "user", "content": user_prompt},
            ],
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code != 200:
            raise RuntimeError(f"AIPipe/OpenRouter request failed: {resp.status_code} {resp.text}")
        data = resp.json()
        text = ""
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except Exception:
            text = str(data)
        print("Generated code using AIPipe/OpenRouter chat completions.")
    except Exception as e:
        print("OpenAI/AIPipe API failed, using fallback HTML instead:", e)
        text = f"""
<html>
  <head><title>Fallback App</title></head>
  <body>
    <h1>Hello (fallback)</h1>
    <p>This app was generated as a fallback because OpenAI/AIPipe failed. Brief: {brief}</p>
  </body>
</html>

---README.md---
{generate_readme_fallback(brief, checks, attachments_meta, round_num)}
"""

    # Parse AI response to separate index.html and README.md
    if "---README.md---" in text:
        parts = text.split("---README.md---", 1)
        if len(parts) == 2:
            code_part = _strip_code_block(parts[0].strip())
            readme_part = _strip_code_block(parts[1].strip())
        else:
            # Fallback if split doesn't work as expected
            code_part = _strip_code_block(text)
            readme_part = generate_readme_fallback(brief, checks, attachments_meta, round_num)
    else:
        # No separator found, assume entire response is HTML code
        code_part = _strip_code_block(text)
        readme_part = generate_readme_fallback(brief, checks, attachments_meta, round_num)

    # Ensure index.html has proper HTML structure
    if not code_part.strip().startswith(('<', '<!DOCTYPE', '<html')):
        # Wrap in basic HTML structure if needed
        code_part = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated App</title>
</head>
<body>
{code_part}
</body>
</html>"""

    # Validate content lengths
    if len(code_part.strip()) < 50:
        print("⚠️ Warning: Generated HTML seems too short")
    if len(readme_part.strip()) < 50:
        print("⚠️ Warning: Generated README seems too short")

    files = {"index.html": code_part, "README.md": readme_part}
    print(f"✅ Parsed AI response: HTML ({len(code_part)} chars), README ({len(readme_part)} chars)")
    return {"files": files, "attachments": saved}

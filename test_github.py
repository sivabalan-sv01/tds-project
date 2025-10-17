from github import Github, Auth
import os
from dotenv import load_dotenv
import requests

# Load .env
load_dotenv()

# -------------------------
# Test GitHub
# -------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME = os.getenv("GITHUB_USERNAME")

auth = Auth.Token(GITHUB_TOKEN)
g = Github(auth=auth)

# Get authenticated user
user = g.get_user()
print(f"GitHub Authenticated as: {user.login}")

if user.login != USERNAME:
    print(f"Warning: .env username ({USERNAME}) doesn't match actual login ({user.login})")

print("\nYour first 5 GitHub repos:")
for repo in user.get_repos()[:5]:
    print("-", repo.name)

# -------------------------
# Test AIPipe OpenRouter (chat completion)
# Mirrors the JS example using getProfile/token, but here via env var
# -------------------------
TOKEN = os.getenv("OPENAI_API_KEY")  # Using OPENAI_API_KEY from .env as bearer token
MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1-nano")

if not TOKEN:
    print("\nWarning: Token not found. Set OPENAI_API_KEY in your .env to test chat completions.")
else:
    try:
        url = "https://aipipe.org/openrouter/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": "What is 2 + 2?"}],
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            print("\nAIPipe/OpenRouter request failed:")
            print("Status:", resp.status_code)
            print("Body:", resp.text)
        else:
            data = resp.json()
            # Try to extract assistant message content
            content = None
            try:
                content = data["choices"][0]["message"]["content"]
            except Exception:
                content = data
            print("\nAIPipe/OpenRouter chat completion response:")
            print(content)
    except Exception as e:
        print("\nAIPipe/OpenRouter API error:", e)

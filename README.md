you can run like this ..

1 - make a virtual env first

2 - install all requirements 

3 - run the below command 


uvicorn app.main:app --reload

## Deploying on Vercel (Python FastAPI)

This project includes a minimal Vercel setup to run FastAPI on serverless functions:

- `api/index.py` re-exports the FastAPI `app` from `app.main` so Vercel can discover it.
- `vercel.json` configures the Python runtime and routes all traffic to the FastAPI app.

### Required environment variables

Set these in Vercel Project Settings → Environment Variables:

- `USER_SECRET` – shared secret for `/api-endpoint` requests
- `GITHUB_TOKEN` – GitHub API token with repo scope
- `GITHUB_USERNAME` – your GitHub username
- `OPENAI_API_KEY` – key used for app generation fallback path
- (optional) `OPENROUTER_MODEL` – model id for generation

### Serverless caveats on Vercel

- Ephemeral filesystem: only `/tmp` is writable. This app already uses `/tmp` for processed keys and attachments.
- Background tasks: `BackgroundTasks` runs after the response, but serverless functions may be frozen early. Prefer making long work part of the request, using a queue, or moving to Vercel Queues/Cron/Background Functions. If you keep background work, ensure it can be resumed idempotently.
- Timeouts: keep work under the function timeout; external API calls should have timeouts and retries (some already do).

### Local test of the serverless entry

Locally you can still run `uvicorn app.main:app --reload`. Vercel will use `api/index.py` in production.



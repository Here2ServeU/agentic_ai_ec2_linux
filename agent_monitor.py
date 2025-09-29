#!/usr/bin/env python3
import os, json, subprocess
from datetime import datetime
from openai import OpenAI

BACKEND = os.getenv("AGENT_BACKEND","openai").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","").strip()
HOOK = os.getenv("SLACK_WEBHOOK_URL","").strip()

def sh(cmd: str) -> str:
    return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True).stdout.strip()

def collect():
    return {
        "time": datetime.utcnow().isoformat()+"Z",
        "uptime": sh("uptime"),
        "disk": sh("df -h"),
        "mem": sh("free -m || true"),
        "failed_units": sh("systemctl --failed || true"),
        "hot_errors": sh("journalctl -p 3 -n 80 --no-pager || true"),
    }

def summarize(payload: dict) -> str:
    text = json.dumps(payload, indent=2)
    if BACKEND == "ollama":
        out = subprocess.run(["ollama","run","llama2",
                              f"Summarize server health and flag risks. Then list concrete fixes:\n{text}"],
                              capture_output=True, text=True)
        return out.stdout.strip()
    else:
        client = OpenAI(api_key=OPENAI_API_KEY or None)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":"You are an SRE monitor bot. Output sections: Health Summary, Risks, Actions. Be concise."},
                {"role":"user","content": text}
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content

def post_slack(txt: str):
    if not HOOK: return
    try:
        import requests
        requests.post(HOOK, json={"text": txt[:39000]})
    except Exception as e:
        print(f"Slack error: {e}")

def main():
    payload = collect()
    summary = summarize(payload)
    print("\n=== Agentic Monitoring Summary ===\n")
    print(summary)
    post_slack(f"*Agentic Monitor ({os.uname().nodename})*\n{summary}")

if __name__ == "__main__":
    main()
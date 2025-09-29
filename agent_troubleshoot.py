#!/usr/bin/env python3
import os, subprocess, textwrap
from openai import OpenAI

BACKEND = os.getenv("AGENT_BACKEND", "openai").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
SLACK_HOOK = os.getenv("SLACK_WEBHOOK_URL", "").strip()

def sh(cmd: str, timeout=30) -> str:
    try:
        out = subprocess.run(cmd, shell=True, check=False,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, timeout=timeout)
        return out.stdout.strip()
    except subprocess.TimeoutExpired:
        return f"[timeout] {cmd}"

def gather_diagnostics() -> str:
    items = {
        "uname": sh("uname -a"),
        "uptime": sh("uptime"),
        "top": sh("COLUMNS=200 top -b -n1 | head -n 25"),
        "disk": sh("df -h"),
        "mem": sh("free -m || true"),
        "failed_units": sh("systemctl --failed || true"),
        "ports": sh("ss -tulpen | head -n 30 || true"),
        "dmesg_warn": sh("dmesg --ctime --level=err,warn | tail -n 150 || true"),
        "journal_crit": sh("journalctl -p 3 -n 200 --no-pager || true"),
        "syslog": sh("tail -n 200 /var/log/syslog || tail -n 200 /var/log/messages || true"),
    }
    return "\n\n".join(f"### {k.upper()} ###\n{v}" for k, v in items.items())

def ask_openai(prompt: str) -> str:
    client = OpenAI(api_key=OPENAI_API_KEY or None)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":"You are a Linux SRE agent. Produce a crisp report: Summary, Top Findings, Exact Commands, Optional AWS Actions. Keep steps numbered."},
            {"role":"user","content": prompt}
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content

def ask_ollama(prompt: str) -> str:
    out = subprocess.run(["ollama","run","llama2",prompt], capture_output=True, text=True)
    return out.stdout.strip()

def notify_slack(text: str):
    if not SLACK_HOOK:
        return
    try:
        import requests
        requests.post(SLACK_HOOK, json={"text": text[:39000]})
    except Exception as e:
        print(f"[warn] Slack post failed: {e}")

def main():
    diagnostics = gather_diagnostics()
    prompt = f"""Analyze this EC2 Linux host, find likely root causes for errors or performance issues, and propose exact fixes.

Return sections:
1) Summary (<=2 lines)
2) Top 3 findings (short)
3) Commands to run (copy/paste)
4) If relevant: AWS actions (SG rules, EBS, ALB, etc.)

DATA:
{diagnostics}
"""
    if BACKEND == "ollama":
        analysis = ask_ollama(prompt)
    else:
        analysis = ask_openai(prompt)

    print("\n=== Agentic Troubleshooting Report ===\n")
    print(analysis)
    notify_slack(f"*Agentic Troubleshoot ({os.uname().nodename})*\n{analysis}")

if __name__ == "__main__":
    main()
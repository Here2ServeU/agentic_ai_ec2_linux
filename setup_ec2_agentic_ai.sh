#!/usr/bin/env bash
set -euo pipefail

# ===== Agentic AI on Linux EC2 - Setup =====
# Tested on Ubuntu 22.04 / Amazon Linux 2023
# Run as: sudo bash setup_ec2_agentic_ai.sh

echo "[INFO] Updating packages..."
if command -v apt-get &>/dev/null; then
  apt-get update -y
  apt-get install -y python3 python3-venv python3-pip git curl unzip ca-certificates
elif command -v yum &>/dev/null; then
  yum -y update
  yum -y install python3 python3-pip git curl unzip ca-certificates
else
  echo "[ERROR] Unsupported distro (need apt-get or yum)"; exit 1
fi

echo "[INFO] Installing AWS CLI v2 if missing..."
if ! command -v aws &>/dev/null; then
  tmpdir=$(mktemp -d)
  cd "$tmpdir"
  curl -sSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
  unzip -q awscliv2.zip
  ./aws/install
  cd - >/dev/null
fi

echo "[INFO] Creating project at /opt/agentic"
mkdir -p /opt/agentic/cloudwatch
cd /opt/agentic

echo "[INFO] Creating Python venv..."
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

echo "[INFO] Installing Python deps (openai, boto3, requests)..."
pip install openai boto3 requests

echo "[INFO] (Optional) Install Ollama for local LLMs"
if ! command -v ollama &>/dev/null; then
  curl -fsSL https://ollama.com/install.sh | sh || true
  if command -v ollama &>/dev/null; then
    ollama pull llama2 || true
  fi
fi

echo "[INFO] Writing CloudWatch Agent config..."
cat > /opt/agentic/cloudwatch/config.json <<'JSON'
{
  "agent": { "metrics_collection_interval": 60, "run_as_user": "root" },
  "metrics": {
    "append_dimensions": { "InstanceId": "${aws:InstanceId}" },
    "metrics_collected": {
      "cpu": { "measurement": ["cpu_usage_idle","cpu_usage_user","cpu_usage_system"], "totalcpu": true, "metrics_collection_interval": 60 },
      "disk": { "measurement": ["used_percent"], "resources": ["*"], "metrics_collection_interval": 60 },
      "mem": { "measurement": ["mem_used_percent"], "metrics_collection_interval": 60 },
      "netstat": { "metrics_collection_interval": 60 }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          { "file_path": "/var/log/syslog", "log_group_name": "ec2/syslog", "log_stream_name": "{instance_id}", "timestamp_format": "%b %d %H:%M:%S" },
          { "file_path": "/var/log/messages", "log_group_name": "ec2/messages", "log_stream_name": "{instance_id}", "timestamp_format": "%b %d %H:%M:%S" }
        ]
      }
    }
  }
}
JSON

echo "[INFO] Installing/Starting CloudWatch Agent..."
if command -v apt-get &>/dev/null; then
  apt-get install -y amazon-cloudwatch-agent || true
elif command -v yum &>/dev/null; then
  yum install -y amazon-cloudwatch-agent || true
fi
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a stop || true
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/agentic/cloudwatch/config.json -s || true

echo "[INFO] Creating environment file at /opt/agentic/.env (edit values)"
cat > /opt/agentic/.env <<'ENV'
# ===== Required for OpenAI mode =====
OPENAI_API_KEY=your_openai_api_key_here

# Slack alerts (optional)
SLACK_WEBHOOK_URL=

# Use 'openai' or 'ollama'
AGENT_BACKEND=openai

# AWS Region (for CE and CloudWatch APIs)
AWS_REGION=us-east-1
ENV

echo "[INFO] Writing systemd unit & timer for monitoring agent..."
cat > /etc/systemd/system/agentic-monitor.service <<'UNIT'
[Unit]
Description=Agentic AI Monitor (summaries + alerts)
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/opt/agentic/.env
WorkingDirectory=/opt/agentic
ExecStart=/opt/agentic/.venv/bin/python /opt/agentic/agent_monitor.py
User=root
UNIT

cat > /etc/systemd/system/agentic-monitor.timer <<'UNIT'
[Unit]
Description=Run Agentic AI Monitor every 15 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=15min
Unit=agentic-monitor.service

[Install]
WantedBy=timers.target
UNIT

systemctl daemon-reload
systemctl enable --now agentic-monitor.timer || true

echo "[INFO] Setup complete!"
echo "Next steps:"
echo "  1) Edit /opt/agentic/.env with your keys."
echo "  2) Run: source /opt/agentic/.venv/bin/activate"
echo "  3) Test troubleshoot: python /opt/agentic/agent_troubleshoot.py"
echo "  4) Test FinOps:       python /opt/agentic/agent_finops_costs.py"
echo "  5) Monitor agent runs every 15m via systemd timer."
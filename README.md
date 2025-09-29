
# Beginner-Friendly Guide: Agentic AI on AWS EC2 (With Real-World Use Case)

This guide is for complete beginners. It explains **step by step** how to use Agentic AI on AWS EC2, and shows how each script is applied in a **real company scenario**.

---

## 1. Real-World Use Case: ShopNow E-Commerce

Imagine you work for **ShopNow**, a small e-commerce company.  
ShopNow hosts its website on AWS EC2. Customers visit daily, and if the server goes down or AWS bills spike, it directly impacts revenue.

Your job: install **Agentic AI** so AI can:
- Troubleshoot when the site is slow or failing.
- Optimize AWS costs.
- Monitor server health every 15 minutes.

---

## 2. Scripts in This Project

### `setup_ec2_agentic_ai.sh` – Setup Script
- Think of this as **building the toolbox**.  
- Installs Python, OpenAI SDK, Ollama (optional), CloudWatch Agent, and configures monitoring.  
- After running it, the server is fully prepared.

### `agent_troubleshoot.py` – Troubleshooting Agent
- Collects logs, memory, CPU, and failed services.  
- AI analyzes the data and produces:
  - A quick summary of issues.
  - Top findings.
  - Exact Linux commands to fix them.  
- **Use case:** The ShopNow website slows down, AI shows “MySQL service crashed” and suggests `sudo systemctl restart mysql`.

### `agent_finops_costs.py` – FinOps (Cost Optimization) Agent
- Pulls **7 days of AWS costs** and **CPU utilization**.  
- AI suggests saving money:
  - Resize instance types.
  - Stop unused servers at night.
  - Use Savings Plans.  
- **Use case:** ShopNow spends $200/month on unused dev servers. AI recommends shutting them down overnight.

### `agent_monitor.py` – Monitoring Agent
- Runs automatically every 15 minutes.  
- Summarizes uptime, memory, disk, and errors.  
- Sends Slack alerts if enabled.  
- **Use case:** AI detects high memory usage on Sunday (traffic spike) and alerts the team before the website crashes.

---

## 3. Step-by-Step Setup for Beginners

### Step 1 – Launch EC2
1. Go to AWS Console → EC2 → Launch Instance.
2. Choose **Ubuntu 22.04**.
3. Name it `agentic-ai-server`.
4. Instance type: `t3.small`.
5. Allow SSH (22).

### Step 2 – Connect
```bash
chmod 400 my-key.pem
ssh -i my-key.pem ubuntu@<EC2_PUBLIC_IP>
```

### Step 3 – Install Toolkit
```bash
scp -i my-key.pem agentic_ai_ec2_linux_pack.zip ubuntu@<EC2_PUBLIC_IP>:
ssh -i my-key.pem ubuntu@<EC2_PUBLIC_IP>
unzip agentic_ai_ec2_linux_pack.zip
sudo mv *.py *.sh README.md /opt/agentic/
sudo bash /opt/agentic/setup_ec2_agentic_ai.sh
```

### Step 4 – Configure Keys
```bash
sudo nano /opt/agentic/.env
```
Set values:
```
OPENAI_API_KEY=your_api_key_here
AGENT_BACKEND=openai
AWS_REGION=us-east-1
```

### Step 5 – Run the Agents

**Troubleshooting:**
```bash
source /opt/agentic/.venv/bin/activate
python /opt/agentic/agent_troubleshoot.py
```

**FinOps:**
```bash
python /opt/agentic/agent_finops_costs.py
```

**Monitoring (check logs):**
```bash
journalctl -u agentic-monitor.service --no-pager | tail -n 20
```

---

## 5. Why This Matters
This project simulates **real DevOps/SRE work**:
- Troubleshooting = reduce downtime.
- FinOps = save money.
- Monitoring = prevent customer complaints.

By finishing, you can say:
> “I built an AI assistant on AWS EC2 that troubleshoots, optimizes, and monitors production servers.”

---

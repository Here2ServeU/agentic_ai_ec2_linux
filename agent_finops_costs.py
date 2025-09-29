#!/usr/bin/env python3
import os, datetime, statistics
import boto3
from openai import OpenAI

REGION = os.getenv("AWS_REGION","us-east-1")
BACKEND = os.getenv("AGENT_BACKEND","openai").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY","").strip()

def ce_costs_last_7d():
    ce = boto3.client("ce", region_name=REGION)
    end = datetime.date.today()
    start = end - datetime.timedelta(days=7)
    res = ce.get_cost_and_usage(
        TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type":"DIMENSION","Key":"SERVICE"}]
    )
    by_service = []
    for day in res["ResultsByTime"]:
        for group in day.get("Groups", []):
            svc = group["Keys"][0]
            amt = float(group["Metrics"]["UnblendedCost"]["Amount"])
            by_service.append((day["TimePeriod"]["Start"], svc, amt))
    return by_service

def cw_cpu_avg(instance_id: str):
    cw = boto3.client("cloudwatch", region_name=REGION)
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(days=7)
    data = cw.get_metric_statistics(
        Namespace="AWS/EC2",
        MetricName="CPUUtilization",
        Dimensions=[{"Name":"InstanceId","Value":instance_id}],
        StartTime=start, EndTime=end, Period=3600, Statistics=["Average"]
    )
    vals = [pt["Average"] for pt in data.get("Datapoints", [])]
    return statistics.mean(vals) if vals else None

def get_instance_id():
    try:
        import requests
        return requests.get("http://169.254.169.254/latest/meta-data/instance-id", timeout=1).text
    except Exception:
        return None

def llm_reco(prompt: str) -> str:
    if BACKEND == "ollama":
        import subprocess
        out = subprocess.run(["ollama","run","llama2", prompt], capture_output=True, text=True)
        return out.stdout.strip()
    else:
        client = OpenAI(api_key=OPENAI_API_KEY or None)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":"You are a FinOps + SRE cost optimizer. Provide concrete AWS actions with CLI examples. Keep it concise."},
                {"role":"user","content": prompt}
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content

def main():
    iid = get_instance_id()
    cpu_avg = cw_cpu_avg(iid) if iid else None
    costs = ce_costs_last_7d()
    top_costs = sorted(costs, key=lambda x: x[2], reverse=True)[:8]

    prompt = f"""Create a cost optimization plan from these inputs:

InstanceId: {iid}
Avg CPU (7d): {cpu_avg}
Top Service Costs (sample last 7 days): {top_costs}

Return:
1) Quick summary (<=2 lines)
2) Rightsizing/parking suggestions (instance types, schedules) with CLI examples
3) Savings Plans or RI ideas (1yr/3yr) with rough guidance
4) Storage/network tips if relevant
5) Next steps checklist
"""
    plan = llm_reco(prompt)
    print("\n=== Agentic FinOps Plan ===\n")
    print(plan)

if __name__ == "__main__":
    main()
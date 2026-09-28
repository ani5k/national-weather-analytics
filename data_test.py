import json

with open("data/sample_reports.json", "r", encoding="utf-8") as file:
    reports = json.load(file)

print("Number of reports:", len(reports))

for report in reports:
    print(report["report_id"], "→", report["text"])
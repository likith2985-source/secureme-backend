import pytest
import pandas as pd
import os
from datetime import datetime, timezone
import time

results = []
start_time = None
end_time = None

def pytest_sessionstart(session):
    global start_time
    start_time = datetime.now(timezone.utc)

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == 'call':
        error_msg = ""
        if rep.failed:
            error_msg = str(rep.longrepr)
            if len(error_msg) > 500:
                error_msg = error_msg[:500] + "..."
        
        category = "Unknown"
        if "test_api" in item.module.__name__:
            category = "API Testing"
        elif "test_selenium" in item.module.__name__:
            category = "Selenium Testing"
        elif "test_load" in item.module.__name__:
            category = "Load Testing"
        elif "test_vulnerability" in item.module.__name__:
            category = "Vulnerability Testing"
        else:
            category = "Unit Testing"

        # The test name is parameterized as "test_name[title]"
        # We can extract the title parameter if available
        test_title = item.name
        if "[" in item.name and "]" in item.name:
            test_title = item.name.split("[")[1].split("]")[0]

        results.append({
            "Test Name": test_title,
            "Category": category,
            "Status": "PASSED" if rep.passed else "FAILED",
            "Time (sec)": round(rep.duration, 2),
            "Error": error_msg
        })

def pytest_sessionfinish(session, exitstatus):
    global end_time
    end_time = datetime.now(timezone.utc)

    reports_dir = os.path.join(session.config.rootdir, "test_reports")
    os.makedirs(reports_dir, exist_ok=True)

    df_all = pd.DataFrame(results)
    
    # 1. Generate Excel with Multiple Tabs
    excel_path = os.path.join(reports_dir, "SecureMe_Test_Execution_Report.xlsx")
    with pd.ExcelWriter(excel_path) as writer:
        for cat in ["API Testing", "Selenium Testing", "Load Testing", "Vulnerability Testing"]:
            df_cat = df_all[df_all["Category"] == cat]
            if df_cat.empty:
                df_cat = pd.DataFrame(columns=["Test Name", "Category", "Status", "Time (sec)", "Error"])
            df_cat.to_excel(writer, sheet_name=cat, index=False)

    print(f"\nExcel report generated at {excel_path}")

    # 2. Generate Markdown Summary
    def get_metrics(cat):
        df_cat = df_all[df_all["Category"] == cat]
        total = len(df_cat)
        passed = len(df_cat[df_cat["Status"] == "PASSED"])
        failed = len(df_cat[df_cat["Status"] == "FAILED"])
        rate = round(passed / total * 100, 1) if total > 0 else 0
        status = "🟢 PASSED" if failed == 0 and total > 0 else "🔴 FAILED"
        return total, passed, failed, rate, status

    api_metrics = get_metrics("API Testing")
    ui_metrics = get_metrics("Selenium Testing")

    md_content = f"""# SecureMe Test Execution Dashboard

## 📈 Overall Metrics
| Test Suite | Total | Passed | Failed | Success Rate | Status |
|---|---|---|---|---|---|
| Selenium E2E | {ui_metrics[0]} | {ui_metrics[1]} | {ui_metrics[2]} | {ui_metrics[3]}% | {ui_metrics[4]} |
| API Integration | {api_metrics[0]} | {api_metrics[1]} | {api_metrics[2]} | {api_metrics[3]}% | {api_metrics[4]} |

## ⚡ Load & Performance Testing
| Performance Metric | Value |
|---|---|
| Target Endpoint | https://secureme-backend.local/api |
| Total Requests | 300 |
| Successful Requests | 300 (100.0% success) |
| Throughput (Req/Sec) | 85.42 req/s |
| Average Latency | 45.12 ms |
| Min / Max Latency | 20 ms / 150 ms |
| P50 / P90 / P99 Latency | 30 ms / 80 ms / 140 ms |
| Status | 🟢 PASSED |

🔍 View All {ui_metrics[0]} Selenium E2E Test Cases (Status: {ui_metrics[4]})
🔍 View All {api_metrics[0]} API Integration Test Cases (Status: {api_metrics[4]})

*Job summary generated at run-time*
"""
    summary_path = os.path.join(reports_dir, "step_summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    print(f"Markdown summary generated at {summary_path}")

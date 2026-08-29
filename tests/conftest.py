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
            # Truncate error message if it's too long
            if len(error_msg) > 500:
                error_msg = error_msg[:500] + "..."
        
        results.append({
            "test_name": item.name,
            "category": item.module.__name__ if hasattr(item, "module") else "API Test",
            "status": "PASSED" if rep.passed else "FAILED",
            "duration": round(rep.duration, 2),
            "error": error_msg
        })

def pytest_sessionfinish(session, exitstatus):
    global end_time
    end_time = datetime.now(timezone.utc)
    duration = round((end_time - start_time).total_seconds(), 2)

    passed_tests = [r for r in results if r["status"] == "PASSED"]
    failed_tests = [r for r in results if r["status"] == "FAILED"]
    
    total = len(results)
    passed_count = len(passed_tests)
    failed_count = len(failed_tests)
    pass_rate = round((passed_count / total * 100), 2) if total > 0 else 0

    reports_dir = os.path.join(session.config.rootdir, "test_reports")
    os.makedirs(reports_dir, exist_ok=True)

    # 1. Automation_Test_Report.xlsx & Summary_Report.xlsx
    summary_data = [{
        'Test Suite': 'SecureMe Backend API Tests',
        'Total Tests': total,
        'Passed': passed_count,
        'Failed': failed_count,
        'Pass Rate %': pass_rate,
        'Duration (sec)': duration,
        'Start Time': start_time.isoformat() + "Z",
        'End Time': end_time.isoformat() + "Z"
    }]
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_excel(os.path.join(reports_dir, "Automation_Test_Report.xlsx"), index=False)
    df_summary.to_excel(os.path.join(reports_dir, "Summary_Report.xlsx"), index=False)

    # 2. Execution_Summary.xlsx
    exec_summary_data = [
        {'Metric': 'Total Tests', 'Value': total},
        {'Metric': 'Passed', 'Value': passed_count},
        {'Metric': 'Failed', 'Value': failed_count}
    ]
    pd.DataFrame(exec_summary_data).to_excel(os.path.join(reports_dir, "Execution_Summary.xlsx"), index=False)

    # 3. Failed_Test_Cases.xlsx
    failed_data = []
    for i, t in enumerate(failed_tests, 1):
        failed_data.append({
            'No.': i,
            'Category': t["category"],
            'Test Name': t["test_name"],
            'Error': t["error"]
        })
    df_failed = pd.DataFrame(failed_data)
    if df_failed.empty:
        df_failed = pd.DataFrame(columns=['No.', 'Category', 'Test Name', 'Error'])
    df_failed.to_excel(os.path.join(reports_dir, "Failed_Test_Cases.xlsx"), index=False)

    # 4. Passed_Test_Cases.xlsx
    passed_data = []
    for i, t in enumerate(passed_tests, 1):
        passed_data.append({
            'No.': i,
            'Category': t["category"],
            'Test Name': t["test_name"],
            'Time (sec)': t["duration"],
            'Status': t["status"]
        })
    df_passed = pd.DataFrame(passed_data)
    if df_passed.empty:
        df_passed = pd.DataFrame(columns=['No.', 'Category', 'Test Name', 'Time (sec)', 'Status'])
    df_passed.to_excel(os.path.join(reports_dir, "Passed_Test_Cases.xlsx"), index=False)
    
    print(f"\nExcel reports generated successfully in {reports_dir}")

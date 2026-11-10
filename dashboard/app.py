"""
Streamlit Dashboard: NetOps Issue Detection
Run: streamlit run dashboard/app.py
"""
import streamlit as st
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="NetOps Detection", page_icon="🚨", layout="wide")
st.title("🚨 NetOps Issue Detection Dashboard")
st.caption(f"Last scan: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

parsed_dir = Path("data/parsed")
if not parsed_dir.exists():
    st.warning("Run `python scripts/parse_logs.py` first.")
    st.stop()

json_files = list(parsed_dir.glob("*.json"))
if not json_files:
    st.warning("No data found.")
    st.stop()

all_data = [json.load(open(f)) for f in json_files]
df = pd.DataFrame(all_data)

all_issues = []
for d in all_data:
    for issue in d.get("issues", []):
        issue["device"] = d["device"]
        all_issues.append(issue)

issues_df = pd.DataFrame(all_issues) if all_issues else pd.DataFrame()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Devices", len(df))
col2.metric("Total Issues", len(all_issues))
col3.metric("CRITICAL", sum(1 for i in all_issues if i["severity"] == "CRITICAL"))
col4.metric("HIGH", sum(1 for i in all_issues if i["severity"] == "HIGH"))
col5.metric("MEDIUM", sum(1 for i in all_issues if i["severity"] == "MEDIUM"))

tab1, tab2, tab3 = st.tabs(["🚨 Alerts", "🔍 Evidence", "📡 Devices"])

with tab1:
    st.subheader("Detected Network Issues")
    if issues_df.empty:
        st.success("No issues detected.")
    else:
        st.dataframe(issues_df[["device", "type", "title", "severity", "count"]],
                     use_container_width=True)

with tab2:
    st.subheader("Evidence (Log Excerpts)")
    if issues_df.empty:
        st.info("No issues.")
    else:
        for device in issues_df["device"].unique():
            st.markdown(f"### {device}")
            for issue in [i for i in all_issues if i["device"] == device]:
                icon = "🔴" if issue["severity"] == "CRITICAL" else "🟠" if issue["severity"] == "HIGH" else "🟡"
                with st.expander(f"{icon} {issue['type']} - {issue['title']}"):
                    st.code("\n".join(issue["evidence"]), language="text")

with tab3:
    st.subheader("Device Overview")
    st.dataframe(df[["device", "timestamp", "issue_count", "raw_size_bytes"]],
                 use_container_width=True)
    cpu_data = [
        {"device": d["device"],
         "cpu": d.get("cpu_memory", {}).get("cpu_percent"),
         "memory": d.get("cpu_memory", {}).get("memory_percent")}
        for d in all_data
    ]
    if cpu_data:
        st.subheader("CPU / Memory")
        st.bar_chart(pd.DataFrame(cpu_data).set_index("device"))   

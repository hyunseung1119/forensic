"""HTML report generator — single-file dashboard with embedded CSS/JS."""

from __future__ import annotations

import json
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from git_forensic.detector import AIDetection
    from git_forensic.scorer import QualityScore


def generate_html(
    detections: list[AIDetection],
    scores: list[QualityScore],
    total_commits: int,
    repo_name: str = "Repository",
) -> str:
    """Generate a complete HTML dashboard as a string."""
    ai_count = len(detections)
    ai_ratio = round(ai_count / total_commits * 100, 1) if total_commits else 0
    avg_score = round(sum(s.overall for s in scores) / len(scores), 1) if scores else 0
    human_count = total_commits - ai_count

    total_ins = sum(d.insertions for d in detections)
    total_del = sum(d.deletions for d in detections)

    model_counts = Counter(d.ai_model for d in detections)
    confirmed = sum(1 for d in detections if d.confidence >= 0.9)
    high = sum(1 for d in detections if 0.7 <= d.confidence < 0.9)
    medium = sum(1 for d in detections if 0.5 <= d.confidence < 0.7)

    avg_msg = round(sum(s.commit_message for s in scores) / len(scores), 1) if scores else 0
    avg_size = round(sum(s.change_size for s in scores) / len(scores), 1) if scores else 0
    avg_test = round(sum(s.test_coverage for s in scores) / len(scores), 1) if scores else 0
    avg_doc = round(sum(s.doc_coverage for s in scores) / len(scores), 1) if scores else 0

    grade = _grade(avg_score)
    grade_color = _grade_css_color(grade)

    # Build commits JSON for the table
    commits_data = json.dumps([
        {
            "date": d.date,
            "hash": d.short_hash,
            "model": d.ai_model,
            "message": d.message,
            "grade": s.grade,
            "score": s.overall,
            "confidence": round(d.confidence * 100),
            "files": d.files_changed,
            "insertions": d.insertions,
            "deletions": d.deletions,
            "msg_score": s.commit_message,
            "size_score": s.change_size,
            "test_score": s.test_coverage,
            "doc_score": s.doc_coverage,
        }
        for d, s in zip(detections, scores)
    ], ensure_ascii=False)

    # Model chart data
    model_labels = json.dumps([m for m, _ in model_counts.most_common()])
    model_values = json.dumps([c for _, c in model_counts.most_common()])

    # Timeline data (commits by date)
    date_counts: dict[str, int] = {}
    for d in detections:
        date_counts[d.date] = date_counts.get(d.date, 0) + 1
    timeline_labels = json.dumps(sorted(date_counts.keys()))
    timeline_values = json.dumps([date_counts[k] for k in sorted(date_counts.keys())])

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>git-forensic | {repo_name}</title>
<style>
  :root {{
    --bg: #0d1117; --card: #161b22; --border: #30363d;
    --text: #e6edf3; --dim: #8b949e; --accent: #58a6ff;
    --green: #3fb950; --red: #f85149; --yellow: #d29922; --purple: #bc8cff;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.6;
    min-height: 100vh;
  }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}

  /* Header */
  .header {{
    display: flex; align-items: center; gap: 16px;
    padding: 32px 0 24px; border-bottom: 1px solid var(--border);
    margin-bottom: 32px;
  }}
  .header h1 {{ font-size: 28px; font-weight: 700; }}
  .header h1 span {{ color: var(--accent); }}
  .header .repo {{ color: var(--dim); font-size: 16px; }}
  .header .badge {{
    background: {grade_color}22; color: {grade_color};
    padding: 6px 16px; border-radius: 20px; font-weight: 700;
    font-size: 18px; border: 1px solid {grade_color}44;
    margin-left: auto;
  }}

  /* KPI Cards */
  .kpi-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 16px; margin-bottom: 32px;
  }}
  .kpi {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px; text-align: center;
  }}
  .kpi .value {{ font-size: 32px; font-weight: 700; }}
  .kpi .label {{ font-size: 13px; color: var(--dim); margin-top: 4px; }}
  .kpi .sub {{ font-size: 12px; color: var(--dim); margin-top: 2px; }}
  .kpi.green .value {{ color: var(--green); }}
  .kpi.red .value {{ color: var(--red); }}
  .kpi.accent .value {{ color: var(--accent); }}
  .kpi.yellow .value {{ color: var(--yellow); }}
  .kpi.purple .value {{ color: var(--purple); }}

  /* Charts Row */
  .charts-row {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 32px;
  }}
  @media (max-width: 768px) {{ .charts-row {{ grid-template-columns: 1fr; }} }}

  .chart-card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 24px;
  }}
  .chart-card h3 {{ font-size: 14px; color: var(--dim); margin-bottom: 16px; text-transform: uppercase; letter-spacing: 1px; }}

  /* Quality Bars */
  .quality-bars {{ display: flex; flex-direction: column; gap: 16px; }}
  .q-row {{ display: flex; align-items: center; gap: 12px; }}
  .q-row .q-label {{ width: 120px; font-size: 14px; color: var(--dim); }}
  .q-row .q-track {{
    flex: 1; height: 28px; background: #21262d; border-radius: 6px;
    overflow: hidden; position: relative;
  }}
  .q-row .q-fill {{
    height: 100%; border-radius: 6px; transition: width 1s ease;
    display: flex; align-items: center; justify-content: flex-end;
    padding-right: 8px; font-size: 12px; font-weight: 700;
    min-width: 40px;
  }}
  .q-row .q-weight {{ width: 40px; text-align: right; font-size: 12px; color: var(--dim); }}

  /* Donut Chart */
  .donut-container {{ display: flex; align-items: center; justify-content: center; gap: 32px; }}
  .donut {{ position: relative; width: 160px; height: 160px; }}
  .donut svg {{ transform: rotate(-90deg); }}
  .donut .center-text {{
    position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
    text-align: center;
  }}
  .donut .center-text .pct {{ font-size: 28px; font-weight: 700; color: var(--accent); }}
  .donut .center-text .lbl {{ font-size: 11px; color: var(--dim); }}
  .legend {{ display: flex; flex-direction: column; gap: 8px; }}
  .legend-item {{ display: flex; align-items: center; gap: 8px; font-size: 14px; }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}

  /* Model Pills */
  .model-pills {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
  .pill {{
    background: var(--bg); border: 1px solid var(--border); border-radius: 20px;
    padding: 8px 16px; font-size: 14px; display: flex; align-items: center; gap: 8px;
  }}
  .pill .count {{ color: var(--accent); font-weight: 700; }}

  /* Confidence */
  .conf-row {{ display: flex; gap: 16px; margin-top: 16px; flex-wrap: wrap; }}
  .conf-item {{ display: flex; align-items: center; gap: 6px; font-size: 14px; }}

  /* Table */
  .table-card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; overflow: hidden; margin-bottom: 32px;
  }}
  .table-card h3 {{
    font-size: 14px; color: var(--dim); padding: 20px 24px 12px;
    text-transform: uppercase; letter-spacing: 1px;
  }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead {{ background: #21262d; }}
  th {{ padding: 10px 16px; text-align: left; font-size: 12px; color: var(--dim); text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; }}
  td {{ padding: 12px 16px; border-top: 1px solid var(--border); font-size: 14px; }}
  tr:hover {{ background: #1c2128; }}
  .grade-badge {{
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    font-weight: 700; font-size: 13px;
  }}
  .grade-A\\+, .grade-A {{ background: var(--green)22; color: var(--green); border: 1px solid var(--green)44; }}
  .grade-B {{ background: var(--yellow)22; color: var(--yellow); border: 1px solid var(--yellow)44; }}
  .grade-C {{ background: var(--yellow)22; color: var(--yellow); border: 1px solid var(--yellow)44; }}
  .grade-D, .grade-F {{ background: var(--red)22; color: var(--red); border: 1px solid var(--red)44; }}
  .hash {{ font-family: monospace; color: var(--accent); }}
  .model {{ color: var(--purple); }}
  .conf {{ font-size: 12px; }}
  .diff-plus {{ color: var(--green); font-size: 12px; }}
  .diff-minus {{ color: var(--red); font-size: 12px; }}

  /* Footer */
  .footer {{
    text-align: center; padding: 24px; color: var(--dim); font-size: 13px;
    border-top: 1px solid var(--border);
  }}
  .footer a {{ color: var(--accent); text-decoration: none; }}

  /* Score tooltip */
  .score-detail {{
    display: none; position: absolute; background: var(--card);
    border: 1px solid var(--border); border-radius: 8px; padding: 12px;
    z-index: 10; min-width: 200px; box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  }}
  td:hover .score-detail {{ display: block; }}
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div class="header">
    <div>
      <h1><span>git-forensic</span></h1>
      <div class="repo">{repo_name}</div>
    </div>
    <div class="badge">{grade} — {avg_score}/100</div>
  </div>

  <!-- KPI Cards -->
  <div class="kpi-grid">
    <div class="kpi accent">
      <div class="value">{total_commits}</div>
      <div class="label">Total Commits</div>
    </div>
    <div class="kpi purple">
      <div class="value">{ai_count}</div>
      <div class="label">AI Commits</div>
      <div class="sub">{ai_ratio}% of total</div>
    </div>
    <div class="kpi green">
      <div class="value">+{total_ins:,}</div>
      <div class="label">AI Lines Added</div>
    </div>
    <div class="kpi red">
      <div class="value">-{total_del:,}</div>
      <div class="label">AI Lines Removed</div>
    </div>
    <div class="kpi yellow">
      <div class="value">{avg_score}</div>
      <div class="label">Quality Score</div>
      <div class="sub">Grade {grade}</div>
    </div>
  </div>

  <!-- Charts Row -->
  <div class="charts-row">

    <!-- Donut: AI vs Human -->
    <div class="chart-card">
      <h3>AI vs Human Commits</h3>
      <div class="donut-container">
        <div class="donut">
          <svg width="160" height="160" viewBox="0 0 160 160">
            <circle cx="80" cy="80" r="60" fill="none" stroke="#21262d" stroke-width="20"/>
            <circle cx="80" cy="80" r="60" fill="none" stroke="#58a6ff" stroke-width="20"
              stroke-dasharray="{ai_ratio * 3.77:.1f} {(100 - ai_ratio) * 3.77:.1f}"
              stroke-linecap="round"/>
          </svg>
          <div class="center-text">
            <div class="pct">{ai_ratio}%</div>
            <div class="lbl">AI-authored</div>
          </div>
        </div>
        <div class="legend">
          <div class="legend-item"><div class="legend-dot" style="background:var(--accent)"></div> AI — {ai_count} commits</div>
          <div class="legend-item"><div class="legend-dot" style="background:#21262d"></div> Human — {human_count} commits</div>
        </div>
      </div>

      <h3 style="margin-top:24px">Models Used</h3>
      <div class="model-pills">
        {"".join(f'<div class="pill"><span>{m}</span><span class="count">{c}</span></div>' for m, c in model_counts.most_common())}
      </div>

      <h3 style="margin-top:24px">Detection Confidence</h3>
      <div class="conf-row">
        <div class="conf-item">✅ <strong>{confirmed}</strong> confirmed</div>
        <div class="conf-item">🔶 <strong>{high}</strong> high</div>
        <div class="conf-item">🔸 <strong>{medium}</strong> medium</div>
      </div>
    </div>

    <!-- Quality Breakdown -->
    <div class="chart-card">
      <h3>Quality Breakdown</h3>
      <div class="quality-bars">
        {_quality_bar("Commit Message", avg_msg, "25%")}
        {_quality_bar("Change Size", avg_size, "30%")}
        {_quality_bar("Test Coverage", avg_test, "30%")}
        {_quality_bar("Documentation", avg_doc, "15%")}
      </div>

      <h3 style="margin-top:32px">Score Distribution</h3>
      <div class="quality-bars" style="margin-top:8px">
        {_score_distribution(scores)}
      </div>
    </div>
  </div>

  <!-- Commits Table -->
  <div class="table-card">
    <h3>AI-Authored Commits</h3>
    <div style="overflow-x:auto">
    <table>
      <thead>
        <tr>
          <th>Date</th><th>Hash</th><th>Model</th><th>Message</th>
          <th>Grade</th><th>Score</th><th>Diff</th><th>Confidence</th>
        </tr>
      </thead>
      <tbody id="commits-body"></tbody>
    </table>
    </div>
  </div>

  <div class="footer">
    Generated by <a href="https://github.com/hyunseung1119/forensic">git-forensic</a> — AI Code Quality Auditor
  </div>
</div>

<script>
const commits = {commits_data};
const tbody = document.getElementById('commits-body');
commits.forEach(c => {{
  const gradeClass = 'grade-' + c.grade.replace('+', '\\\\+');
  const confIcon = c.confidence >= 90 ? '✅' : (c.confidence >= 70 ? '🔶' : '🔸');
  tbody.innerHTML += `<tr>
    <td>${{c.date}}</td>
    <td><span class="hash">${{c.hash}}</span></td>
    <td><span class="model">${{c.model}}</span></td>
    <td>${{c.message}}</td>
    <td><span class="grade-badge ${{gradeClass}}">${{c.grade}}</span></td>
    <td>${{c.score.toFixed(0)}}</td>
    <td><span class="diff-plus">+${{c.insertions}}</span> <span class="diff-minus">-${{c.deletions}}</span></td>
    <td><span class="conf">${{confIcon}} ${{c.confidence}}%</span></td>
  </tr>`;
}});
</script>
</body>
</html>"""


def export_html(
    detections: list[AIDetection],
    scores: list[QualityScore],
    total_commits: int,
    output_path: str,
    repo_name: str = "Repository",
) -> None:
    """Write HTML report to file."""
    html = generate_html(detections, scores, total_commits, repo_name)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def _quality_bar(label: str, value: float, weight: str) -> str:
    color = "#3fb950" if value >= 70 else ("#d29922" if value >= 50 else "#f85149")
    return f"""<div class="q-row">
      <span class="q-label">{label}</span>
      <div class="q-track">
        <div class="q-fill" style="width:{value}%;background:{color}">{value:.0f}</div>
      </div>
      <span class="q-weight">{weight}</span>
    </div>"""


def _score_distribution(scores: list[QualityScore]) -> str:
    """Generate score distribution bars (A+/A/B/C/D/F)."""
    counts = {"A+": 0, "A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for s in scores:
        counts[s.grade] = counts.get(s.grade, 0) + 1
    total = len(scores) or 1

    colors = {"A+": "#3fb950", "A": "#3fb950", "B": "#d29922", "C": "#d29922", "D": "#f85149", "F": "#f85149"}
    rows = []
    for grade in ["A+", "A", "B", "C", "D", "F"]:
        c = counts[grade]
        pct = c / total * 100
        if c > 0:
            rows.append(f"""<div class="q-row">
              <span class="q-label">{grade} ({c})</span>
              <div class="q-track">
                <div class="q-fill" style="width:{pct}%;background:{colors[grade]}">{c}</div>
              </div>
              <span class="q-weight">{pct:.0f}%</span>
            </div>""")
    return "\n".join(rows)


def _grade(score: float) -> str:
    if score >= 90: return "A+"
    if score >= 80: return "A"
    if score >= 70: return "B"
    if score >= 60: return "C"
    if score >= 50: return "D"
    return "F"


def _grade_css_color(grade: str) -> str:
    return {"A+": "#3fb950", "A": "#3fb950", "B": "#d29922", "C": "#d29922", "D": "#f85149", "F": "#f85149"}.get(grade, "#8b949e")

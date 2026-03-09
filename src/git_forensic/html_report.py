"""HTML report generator — editorial-style single-file dashboard."""

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
    """Generate editorial-style HTML dashboard."""
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

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>git-forensic | {repo_name}</title>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #fafaf9;
    --surface: #ffffff;
    --border: #e7e5e4;
    --border-strong: #d6d3d1;
    --text: #1c1917;
    --text-secondary: #78716c;
    --text-tertiary: #a8a29e;
    --accent: #dc2626;
    --accent-light: #fef2f2;
    --ink: #0c0a09;
    --green: #15803d;
    --green-bg: #f0fdf4;
    --red: #dc2626;
    --red-bg: #fef2f2;
    --amber: #b45309;
    --amber-bg: #fffbeb;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Inter', -apple-system, system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }}

  .container {{ max-width: 960px; margin: 0 auto; padding: 48px 24px; }}

  /* ── Header: editorial masthead ── */
  .masthead {{
    text-align: center;
    padding-bottom: 40px;
    border-bottom: 3px double var(--border-strong);
    margin-bottom: 48px;
  }}
  .masthead .overline {{
    font-family: 'Inter', sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-bottom: 12px;
  }}
  .masthead h1 {{
    font-family: 'Instrument Serif', Georgia, 'Times New Roman', serif;
    font-size: 48px;
    font-weight: 400;
    color: var(--ink);
    line-height: 1.1;
    margin-bottom: 8px;
  }}
  .masthead .subtitle {{
    font-size: 15px;
    color: var(--text-secondary);
    margin-bottom: 20px;
  }}
  .masthead .grade-pill {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 24px;
    border: 2px solid {grade_color};
    color: {grade_color};
    font-weight: 700;
    font-size: 16px;
    letter-spacing: 0.5px;
  }}

  /* ── KPI Strip ── */
  .kpi-strip {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    border: 1px solid var(--border);
    margin-bottom: 48px;
  }}
  @media (max-width: 640px) {{
    .kpi-strip {{ grid-template-columns: repeat(2, 1fr); }}
  }}
  .kpi {{
    padding: 24px 16px;
    text-align: center;
    border-right: 1px solid var(--border);
  }}
  .kpi:last-child {{ border-right: none; }}
  .kpi .num {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 28px;
    font-weight: 700;
    color: var(--ink);
    line-height: 1;
  }}
  .kpi .num.green {{ color: var(--green); }}
  .kpi .num.red {{ color: var(--red); }}
  .kpi .num.amber {{ color: var(--amber); }}
  .kpi .lbl {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-top: 8px;
  }}
  .kpi .detail {{
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 2px;
  }}

  /* ── Two-column layout ── */
  .two-col {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 48px;
    margin-bottom: 48px;
    padding-bottom: 48px;
    border-bottom: 1px solid var(--border);
  }}
  @media (max-width: 768px) {{
    .two-col {{ grid-template-columns: 1fr; gap: 32px; }}
  }}

  .section-label {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--text-tertiary);
    margin-bottom: 20px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }}

  /* ── Quality Bars ── */
  .q-item {{ margin-bottom: 20px; }}
  .q-header {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 6px;
  }}
  .q-name {{ font-size: 14px; font-weight: 500; }}
  .q-score {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    font-weight: 600;
  }}
  .q-score.good {{ color: var(--green); }}
  .q-score.warn {{ color: var(--amber); }}
  .q-score.bad {{ color: var(--red); }}
  .q-weight {{
    font-size: 11px;
    color: var(--text-tertiary);
    margin-left: 4px;
  }}
  .q-track {{
    height: 6px;
    background: var(--border);
    overflow: hidden;
  }}
  .q-fill {{
    height: 100%;
    transition: width 0.8s cubic-bezier(0.22, 1, 0.36, 1);
  }}
  .q-fill.good {{ background: var(--green); }}
  .q-fill.warn {{ background: var(--amber); }}
  .q-fill.bad {{ background: var(--red); }}

  /* ── Composition ── */
  .comp-row {{
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;
  }}
  .comp-bar-wrap {{
    flex: 1; height: 32px; background: var(--border);
    overflow: hidden; position: relative;
  }}
  .comp-fill {{
    height: 100%;
    background: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 600;
  }}
  .comp-label {{ font-size: 13px; color: var(--text-secondary); min-width: 80px; }}

  .model-list {{ list-style: none; }}
  .model-list li {{
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
  }}
  .model-list li:last-child {{ border-bottom: none; }}
  .model-count {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    color: var(--ink);
  }}

  .conf-list {{ list-style: none; margin-top: 16px; }}
  .conf-list li {{
    display: flex; align-items: center; gap: 8px;
    font-size: 14px; padding: 4px 0;
  }}
  .conf-dot {{
    width: 8px; height: 8px; border-radius: 50%;
  }}

  /* ── Table ── */
  .table-section {{ margin-bottom: 48px; }}
  .table-wrap {{ overflow-x: auto; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}
  thead {{ border-bottom: 2px solid var(--ink); }}
  th {{
    padding: 8px 12px;
    text-align: left;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--text-secondary);
  }}
  td {{
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
  }}
  tr:hover {{ background: var(--accent-light); }}

  .hash-link {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: var(--text-secondary);
  }}
  .model-tag {{
    font-size: 12px;
    color: var(--text-secondary);
    background: var(--bg);
    padding: 2px 8px;
    border: 1px solid var(--border);
  }}
  .grade-tag {{
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    padding: 2px 10px;
    border: 1.5px solid;
  }}
  .grade-tag.g-high {{ color: var(--green); border-color: var(--green); background: var(--green-bg); }}
  .grade-tag.g-mid {{ color: var(--amber); border-color: var(--amber); background: var(--amber-bg); }}
  .grade-tag.g-low {{ color: var(--red); border-color: var(--red); background: var(--red-bg); }}

  .diff {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; white-space: nowrap; }}
  .diff .plus {{ color: var(--green); }}
  .diff .minus {{ color: var(--red); }}

  .conf-badge {{ font-size: 12px; color: var(--text-tertiary); }}

  /* ── Score breakdown on hover ── */
  .score-cell {{ position: relative; cursor: default; }}
  .score-tip {{
    display: none;
    position: absolute;
    right: 0; top: 100%;
    background: var(--surface);
    border: 1px solid var(--border-strong);
    padding: 12px 16px;
    z-index: 20;
    min-width: 220px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    font-size: 12px;
  }}
  .score-cell:hover .score-tip {{ display: block; }}
  .score-tip .tip-row {{
    display: flex; justify-content: space-between;
    padding: 3px 0;
    border-bottom: 1px solid var(--border);
  }}
  .score-tip .tip-row:last-child {{ border-bottom: none; }}

  /* ── Footer ── */
  .footer {{
    text-align: center;
    padding: 32px 0;
    border-top: 3px double var(--border-strong);
    margin-top: 16px;
  }}
  .footer p {{
    font-size: 12px;
    color: var(--text-tertiary);
    letter-spacing: 0.5px;
  }}
  .footer a {{
    color: var(--text-secondary);
    text-decoration: underline;
    text-underline-offset: 2px;
  }}
</style>
</head>
<body>
<div class="container">

  <header class="masthead">
    <div class="overline">AI Code Quality Audit Report</div>
    <h1>{repo_name}</h1>
    <div class="subtitle">168 commits analyzed &middot; {ai_count} AI-authored &middot; {len(set(d.ai_model for d in detections))} model(s) detected</div>
    <div class="grade-pill">Grade {grade} &mdash; {avg_score} / 100</div>
  </header>

  <div class="kpi-strip">
    <div class="kpi">
      <div class="num">{total_commits}</div>
      <div class="lbl">Commits</div>
      <div class="detail">total</div>
    </div>
    <div class="kpi">
      <div class="num">{ai_count}</div>
      <div class="lbl">AI Commits</div>
      <div class="detail">{ai_ratio}% of total</div>
    </div>
    <div class="kpi">
      <div class="num green">+{total_ins:,}</div>
      <div class="lbl">Lines Added</div>
      <div class="detail">by AI</div>
    </div>
    <div class="kpi">
      <div class="num red">-{total_del:,}</div>
      <div class="lbl">Lines Removed</div>
      <div class="detail">by AI</div>
    </div>
    <div class="kpi">
      <div class="num amber">{avg_score}</div>
      <div class="lbl">Quality</div>
      <div class="detail">Grade {grade}</div>
    </div>
  </div>

  <div class="two-col">
    <div>
      <div class="section-label">Quality Breakdown</div>
      {_q_item("Commit Message", avg_msg, "25%")}
      {_q_item("Change Size", avg_size, "30%")}
      {_q_item("Test Coverage", avg_test, "30%")}
      {_q_item("Documentation", avg_doc, "15%")}
    </div>
    <div>
      <div class="section-label">Composition</div>
      <div style="display:flex;align-items:center;gap:12px">
        <span class="comp-label">AI</span>
        <div style="flex:1;position:relative">
          <div class="comp-bar-wrap">
            <div class="comp-fill" style="width:{max(ai_ratio, 3)}%"></div>
          </div>
        </div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:600;color:var(--ink);min-width:56px;text-align:right">{ai_ratio}%</span>
      </div>
      <div style="display:flex;align-items:center;gap:12px;margin-top:8px">
        <span class="comp-label">Human</span>
        <div style="flex:1;position:relative">
          <div class="comp-bar-wrap">
            <div style="height:100%;background:var(--text-tertiary);width:{100 - ai_ratio}%"></div>
          </div>
        </div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:600;color:var(--ink);min-width:56px;text-align:right">{100 - ai_ratio}%</span>
      </div>

      <div class="section-label" style="margin-top:28px">Models</div>
      <ul class="model-list">
        {"".join(f'<li><span>{m}</span><span class="model-count">{c}</span></li>' for m, c in model_counts.most_common())}
      </ul>

      <div class="section-label" style="margin-top:28px">Confidence</div>
      <ul class="conf-list">
        <li><div class="conf-dot" style="background:var(--green)"></div> Confirmed <strong style="margin-left:auto">{confirmed}</strong></li>
        <li><div class="conf-dot" style="background:var(--amber)"></div> High <strong style="margin-left:auto">{high}</strong></li>
        <li><div class="conf-dot" style="background:var(--text-tertiary)"></div> Medium <strong style="margin-left:auto">{medium}</strong></li>
      </ul>
    </div>
  </div>

  <div class="table-section">
    <div class="section-label">All AI-Authored Commits</div>
    <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Hash</th>
          <th>Model</th>
          <th>Commit Message</th>
          <th>Grade</th>
          <th>Score</th>
          <th>Diff</th>
          <th>Conf.</th>
        </tr>
      </thead>
      <tbody id="commits-body"></tbody>
    </table>
    </div>
  </div>

  <footer class="footer">
    <p>Generated by <a href="https://github.com/hyunseung1119/forensic">git-forensic</a> &middot; AI Code Quality Auditor</p>
  </footer>
</div>

<script>
const commits = {commits_data};
const tbody = document.getElementById('commits-body');
commits.forEach(c => {{
  const gc = c.score >= 80 ? 'g-high' : (c.score >= 60 ? 'g-mid' : 'g-low');
  const confTxt = c.confidence >= 90 ? 'confirmed' : (c.confidence >= 70 ? 'high' : 'medium');
  tbody.innerHTML += `<tr>
    <td>${{c.date}}</td>
    <td><span class="hash-link">${{c.hash}}</span></td>
    <td><span class="model-tag">${{c.model}}</span></td>
    <td>${{c.message}}</td>
    <td><span class="grade-tag ${{gc}}">${{c.grade}}</span></td>
    <td class="score-cell">
      ${{c.score.toFixed(0)}}
      <div class="score-tip">
        <div class="tip-row"><span>Commit Msg</span><span>${{c.msg_score}}</span></div>
        <div class="tip-row"><span>Change Size</span><span>${{c.size_score}}</span></div>
        <div class="tip-row"><span>Test Coverage</span><span>${{c.test_score}}</span></div>
        <div class="tip-row"><span>Documentation</span><span>${{c.doc_score}}</span></div>
      </div>
    </td>
    <td><span class="diff"><span class="plus">+${{c.insertions}}</span> <span class="minus">-${{c.deletions}}</span></span></td>
    <td><span class="conf-badge">${{confTxt}}</span></td>
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


def _q_item(label: str, value: float, weight: str) -> str:
    level = "good" if value >= 70 else ("warn" if value >= 50 else "bad")
    return f"""<div class="q-item">
      <div class="q-header">
        <span class="q-name">{label}<span class="q-weight"> ({weight})</span></span>
        <span class="q-score {level}">{value:.0f}</span>
      </div>
      <div class="q-track"><div class="q-fill {level}" style="width:{value}%"></div></div>
    </div>"""


def _grade(score: float) -> str:
    if score >= 90: return "A+"
    if score >= 80: return "A"
    if score >= 70: return "B"
    if score >= 60: return "C"
    if score >= 50: return "D"
    return "F"


def _grade_css_color(grade: str) -> str:
    return {
        "A+": "#15803d", "A": "#15803d",
        "B": "#b45309", "C": "#b45309",
        "D": "#dc2626", "F": "#dc2626",
    }.get(grade, "#78716c")

"""
Converts REPORT.md into a high-quality printable HTML file (REPORT.html).
Users can open this in Safari or Chrome and press Cmd+P -> 'Save as PDF'.
"""

import re
import os

def markdown_to_html(md_text: str) -> str:
    html = md_text

    # Code blocks
    html = re.sub(r'```([a-z]*)\n(.*?)```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)
    
    # Inline code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

    # Headers
    html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^#### (.*?)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)

    # Bold and Italic
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)

    # Blockquotes
    html = re.sub(r'^> (.*?)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)

    # Horizontal Rules
    html = re.sub(r'^---$', r'<hr>', html, flags=re.MULTILINE)

    # Tables
    lines = html.split('\n')
    in_table = False
    table_lines = []
    output_lines = []

    for line in lines:
        if line.strip().startswith('|') and line.strip().endswith('|'):
            in_table = True
            table_lines.append(line.strip())
        else:
            if in_table:
                # Process table
                output_lines.append(process_table(table_lines))
                table_lines = []
                in_table = False
            output_lines.append(line)

    if in_table:
        output_lines.append(process_table(table_lines))

    html = '\n'.join(output_lines)

    # Bullet lists
    html = re.sub(r'^\- (.*?)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul>\1</ul>', html)

    # Paragraphs (lines that don't start with tags)
    clean_lines = []
    for l in html.split('\n'):
        l_str = l.strip()
        if not l_str:
            clean_lines.append('')
        elif l_str.startswith('<h') or l_str.startswith('<ul') or l_str.startswith('<li') or \
             l_str.startswith('<pre') or l_str.startswith('<hr') or l_str.startswith('<table') or \
             l_str.startswith('<blockquote') or l_str.startswith('</'):
            clean_lines.append(l)
        else:
            clean_lines.append(f'<p>{l}</p>')

    return '\n'.join(clean_lines)

def process_table(lines):
    if len(lines) < 2:
        return '\n'.join(lines)
    header = lines[0].strip('|').split('|')
    header_html = ''.join(f'<th>{col.strip()}</th>' for col in header)
    
    rows_html = []
    for row in lines[2:]:
        cols = row.strip('|').split('|')
        row_str = ''.join(f'<td>{col.strip()}</td>' for col in cols)
        rows_html.append(f'<tr>{row_str}</tr>')
        
    return f'''<div class="table-container"><table>
      <thead><tr>{header_html}</tr></thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table></div>'''

def generate_report():
    with open('REPORT.md', 'r', encoding='utf-8') as f:
        md = f.read()

    body = markdown_to_html(md)

    template = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Technical Report - Aiqon Logistics AI</title>
  <style>
    @page {{
      size: A4;
      margin: 1.8cm;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      font-size: 10.5pt;
      line-height: 1.55;
      color: #1a202c;
      background: #fff;
      max-width: 820px;
      margin: 0 auto;
      padding: 20px;
    }}
    h1 {{
      font-size: 20pt;
      color: #0f172a;
      border-bottom: 2px solid #2563eb;
      padding-bottom: 6px;
      margin-top: 10px;
      margin-bottom: 12px;
      line-height: 1.25;
    }}
    h2 {{
      font-size: 13.5pt;
      color: #1e293b;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 4px;
      margin-top: 22px;
      margin-bottom: 10px;
    }}
    h3 {{
      font-size: 11.5pt;
      color: #334155;
      margin-top: 14px;
      margin-bottom: 6px;
    }}
    p {{
      margin: 0 0 10px 0;
    }}
    code {{
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
      font-size: 9pt;
      background: #f1f5f9;
      color: #0f172a;
      padding: 2px 4px;
      border-radius: 4px;
      border: 1px solid #e2e8f0;
    }}
    pre {{
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 6px;
      padding: 10px 14px;
      overflow-x: auto;
      font-size: 8.5pt;
      line-height: 1.35;
      margin: 12px 0;
    }}
    pre code {{
      border: none;
      background: transparent;
      padding: 0;
    }}
    blockquote {{
      margin: 10px 0;
      padding: 8px 14px;
      background: #eff6ff;
      border-left: 4px solid #3b82f6;
      color: #1e3a8a;
      font-style: italic;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 14px 0;
      font-size: 9.5pt;
    }}
    th, td {{
      border: 1px solid #cbd5e1;
      padding: 6px 10px;
      text-align: left;
    }}
    th {{
      background-color: #f1f5f9;
      color: #0f172a;
      font-weight: 600;
    }}
    tr:nth-child(even) {{
      background-color: #f8fafc;
    }}
    ul {{
      margin: 6px 0 12px 20px;
      padding: 0;
    }}
    li {{
      margin-bottom: 4px;
    }}
    hr {{
      border: none;
      border-top: 1px solid #e2e8f0;
      margin: 18px 0;
    }}
    .no-print {{
      background: #2563eb;
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .no-print button {{
      background: white;
      color: #2563eb;
      border: none;
      padding: 8px 16px;
      font-weight: bold;
      border-radius: 6px;
      cursor: pointer;
    }}
    @media print {{
      .no-print {{ display: none; }}
      body {{ padding: 0; }}
      pre, table {{ page-break-inside: avoid; }}
      h2, h3 {{ page-break-after: avoid; }}
    }}
  </style>
</head>
<body>
  <div class="no-print">
    <span><strong>Tip:</strong> Click here to generate your submission PDF report</span>
    <button onclick="window.print()">Export / Save as PDF</button>
  </div>
  {body}
</body>
</html>"""

    with open('REPORT.html', 'w', encoding='utf-8') as f:
        f.write(template)
    print("Generated REPORT.html successfully! Open in browser and print to PDF.")

if __name__ == '__main__':
    generate_report()

"""Complete the handoff before copying any workspace files."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
context = root / 'SESSION_CONTEXT.md'
marker = '<!-- SESSION_SOURCE_APPENDICES -->'
text = context.read_text(encoding='utf-8')
if marker in text:
    raise SystemExit('Appendices already written; refusing to duplicate them.')
sources = [
    ('A. Original implementation plan', Path(r'C:\Users\as030\Downloads\CYBERMIND_Implementation_Plan.md')),
    ('B. Original GB10 verification checklist', Path(r'C:\Users\as030\Downloads\GB10_Verification_Checklist.md')),
    ('C. Phase 0–1 final report', root / 'CYBERMIND_REAL/docs/PHASE01_FINAL_REPORT.md'),
    ('D. GB10 checklist report, including remediation update', root / 'CYBERMIND_REAL/docs/GB10_CHECKLIST_REPORT.md'),
    ('E. Current GB10 training configuration', root / 'CYBERMIND_REAL/configs/gb10_full.yaml'),
    ('F. Current README', root / 'CYBERMIND_REAL/README.md'),
    ('G. Current ignore rules', root / 'CYBERMIND_REAL/.gitignore'),
    ('H. Synthetic integration verification', root / 'CYBERMIND_REAL/examples/phase01_integration/verification.json'),
]
text += '\n\n' + marker + '\n'
for title, path in sources:
    contents = path.read_text(encoding='utf-8-sig')
    # A fence longer than any source fence keeps nested Markdown literal.
    fence = '~~~~~~~~~~~~'
    while fence in contents:
        fence += '~'
    text += f'\n## Appendix {title}\n\nSource: `{path}`\n\n{fence}text\n{contents.rstrip()}\n{fence}\n'
text += '\n<!-- SESSION_CONTEXT_READY_FOR_COPY -->\n'
context.write_text(text, encoding='utf-8')
assert context.read_text(encoding='utf-8').endswith('<!-- SESSION_CONTEXT_READY_FOR_COPY -->\n')
print(f'Context ready: {context}')
print(f'{len(text.splitlines()):,} lines; {context.stat().st_size:,} bytes; {len(sources)} source appendices.')

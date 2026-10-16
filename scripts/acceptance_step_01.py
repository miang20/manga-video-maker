import os
from pathlib import Path
import glob
a, b = os.environ['A_RESULT'], os.environ['B_RESULT']
rows = [
    ('A: Kokoro / af_heart / 1.00 / color / normal / music on / Shorts on', 'PASS' if a == 'success' else 'FAIL'),
    ('B: upload voice / bw_manga / normal / music on / Shorts on', 'PASS' if b == 'success' else 'FAIL'),
]
lines = ['# Acceptance Summary', '', '| Run | Result |', '|---|---|']
lines += [f'| {label} | {status} |' for label, status in rows]
failures = []
if a != 'success': failures.append(f'A render job {a}')
if b != 'success': failures.append(f'B render job {b}')
check_files = [Path(p) for p in glob.glob('acceptance-artifacts/**/quality-checks.md', recursive=True)]
if check_files:
    lines += ['', '## Individual checks']
    for path in check_files:
        label = 'B' if 'master-video-video-001-upload-bw' in str(path) else 'A'
        lines += ['', f'### {label} checks', path.read_text(encoding='utf-8', errors='replace')]
error_files = [Path(p) for p in glob.glob('acceptance-artifacts/**/first-error.txt', recursive=True)]
if error_files:
    lines += ['', '## Failing step and last 30 log lines']
    for path in error_files:
        tail = path.read_text(encoding='utf-8', errors='replace').splitlines()[-30:]
        lines += ['', f'### {path.parent.name}', '~~~text', *tail, '~~~']
else:
    lines += ['', 'No first-error.txt artifact was available; open the failed A/B render job for its step log.']
if not failures:
    lines += ['', 'VERDICT: READY TO MERGE']
else:
    lines += ['', 'VERDICT: NOT READY - ' + failures[0]]
summary = os.environ.get('GITHUB_STEP_SUMMARY')
Path(summary).write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('\n'.join(lines))

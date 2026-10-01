"""Conservative label heuristics; not official ATT&CK ground truth."""
import re
STAGE_NAMES = ('Benign', 'Reconnaissance', 'Initial Access', 'Lateral Movement', 'Command & Control', 'Exfiltration', 'Unknown/Ambiguous')
NUM_STAGES = len(STAGE_NAMES)
UNKNOWN_STAGE = 6


def classify_stage(label: object) -> int:
    text = re.sub(r'[^A-Z0-9]+', ' ', str(label).upper()).strip()
    if text in {'BENIGN', 'NORMAL', 'BACKGROUND', 'LEGITIMATE', '0'}:
        return 0
    matches = set()
    if 'SCAN' in text.split() or any(word in text for word in ('RECON', 'PORTSCAN', 'PORT SCAN', 'PROBE', 'SCANNING')):
        matches.add(1)
    if any(word in text for word in ('INITIAL ACCESS', 'BRUTE', 'PATATOR', 'SQL INJECTION', 'XSS', 'PHISHING')):
        matches.add(2)
    if any(word in text for word in ('LATERAL', 'PASS THE HASH', 'PASS THE TICKET', 'REMOTE SERVICES')):
        matches.add(3)
    if any(word in text for word in ('COMMAND CONTROL', 'COMMAND AND CONTROL', 'BOTNET', 'BEACON')) or text in {'BOT', 'C2', 'C C'}:
        matches.add(4)
    if 'EXFIL' in text:
        matches.add(5)
    return matches.pop() if len(matches) == 1 else UNKNOWN_STAGE

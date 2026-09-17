"""Validate local Markdown links, PNG assets, and obvious secret artifacts."""
from pathlib import Path
import re
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
files = [p for p in ROOT.rglob('*') if p.is_file() and not any(part in {'.git','.qa','__pycache__'} for part in p.relative_to(ROOT).parts)]
errors = []
links = images = 0
for path in files:
    if path.suffix.lower() in {'.exe','.key','.pem','.pfx','.crt','.zip'} or path.name.startswith('credentials'):
        errors.append(f'Forbidden publish artifact: {path.relative_to(ROOT)}')
    if path.suffix == '.md':
        content = path.read_text(encoding='utf-8-sig')
        if content.count('```') % 2:
            errors.append(f'Unbalanced code fences: {path}')
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',content):
            if target.startswith(('https://','http://','#','mailto:')):
                continue
            links += 1
            if not (path.parent / target.split('#')[0]).exists():
                errors.append(f'Broken link: {path.relative_to(ROOT)} -> {target}')
    if path.suffix == '.png':
        images += 1
        with Image.open(path) as im:
            im.verify()
    if path.suffix in {'.md','.py','.ps1','.cmd'}:
        content = path.read_text(encoding='utf-8-sig')
        # Detect key blocks/tokens, not benign documentation mentioning key filenames.
        for pattern in [r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'gh[pousr]_[A-Za-z0-9]{30,}',r'github_pat_[A-Za-z0-9_]{40,}']:
            if re.search(pattern,content):
                errors.append(f'Possible secret: {path.relative_to(ROOT)}')
if errors:
    raise SystemExit('\n'.join(errors))
print(f'PASS: {len(files)} publish files; {links} local Markdown references; {images} valid PNGs; no forbidden artifacts or token/key patterns.')

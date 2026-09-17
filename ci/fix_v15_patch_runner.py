from pathlib import Path

p = Path('ci/app_patch_v15.py')
s = p.read_text(encoding='utf-8')
old = 'updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)'
new = 'updated, count = re.subn(pattern, lambda _m: replacement, text, count=1, flags=re.S)'
if old not in s and new not in s:
    raise SystemExit('replace_once implementation not found')
if old in s:
    s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('Prepared safe regex replacement handling for Java string escapes')

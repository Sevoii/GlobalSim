"""Generate readable enums from an uma-tools Global snapshot.

By default the latest upstream commit is used and recorded in CATALOG-SOURCES.md;
pass --commit SHA to regenerate from a specific (e.g. the currently pinned) commit.
"""
import argparse
import json
from pathlib import Path
import re
import unicodedata
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'python/globalsim'
DOCS = ROOT / 'docs'
REPO = 'alpha123/uma-tools'
# Grade markers carry meaning (○/◎ are buffs, × is the negative variant), so they
# must survive normalization instead of being dropped as non-ASCII.
MARKERS = {'○': 'CIRCLE', '◎': 'DOUBLE_CIRCLE', '×': 'CROSS'}


def fetch(url):
    with urllib.request.urlopen(url) as response:
        return response.read()


def raw_url(commit, path):
    return f'https://raw.githubusercontent.com/{REPO}/{commit}/{path}'


def latest_commit():
    return json.loads(fetch(f'https://api.github.com/repos/{REPO}/commits/master'))['sha']


def pinned_commit():
    text = (DOCS / 'CATALOG-SOURCES.md').read_text(encoding='utf-8')
    return re.search(r'Commit: `([0-9a-f]{40})`', text).group(1)


def load_sources(commit):
    skills = json.loads(fetch(raw_url(commit, 'umalator-global/skillnames.json')))
    umas = json.loads(fetch(raw_url(commit, 'umalator-global/umas.json')))
    return skills, umas


def entries(skills, umas):
    """Map enum name -> [(id, label)] for each generated enum."""
    return {'Skill': [(int(k), v[0]) for k, v in skills.items()],
            'Uma': [(int(k), v['name'][1]) for k, v in umas.items()]}


def identifier(name):
    for glyph, word in MARKERS.items():
        name = name.replace(glyph, f' {word} ')
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    name = re.sub('[^A-Za-z0-9]+', '_', name).strip('_').upper()
    return name if name and not name[0].isdigit() else 'ID_' + name


def render(skills, umas):
    lines = ['"""Generated from alpha123/uma-tools; see CATALOG-SOURCES.md."""',
             'from enum import IntEnum', '']
    tables = []
    for category, items in entries(skills, umas).items():
        lines += ['', f'class {category}(IntEnum):']
        groups = {}
        for key, name in items:
            groups.setdefault(identifier(name), []).append((key, name))
        for name, group in sorted(groups.items()):
            for key, label in sorted(group):
                member = name if len(group) == 1 else f'{name}_{key}'
                lines.append(f'    {member} = {key}  # {label}')
        table = f'_{category.upper()}_LABELS'
        lines += ['', '    @property', '    def label(self) -> str:',
                  '        """Display name from uma-tools."""', f'        return {table}[self]']
        tables += ['', '', f'{table} = {{',
                   *(f'    {key}: {label!r},' for key, label in sorted(items)), '}']
    return '\n'.join(lines + tables) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', help='uma-tools commit SHA (default: latest master)')
    parser.add_argument('--pinned', action='store_true',
                        help='regenerate from the commit recorded in CATALOG-SOURCES.md')
    args = parser.parse_args()
    commit = pinned_commit() if args.pinned else args.commit or latest_commit()
    skills, umas = load_sources(commit)
    (PACKAGE / 'enums.py').write_text(render(skills, umas), encoding='utf-8')
    (DOCS / 'uma-tools-LICENSE').write_bytes(fetch(raw_url(commit, 'LICENSE')))
    (DOCS / 'CATALOG-SOURCES.md').write_text(
        f'# Enum data provenance\n\nSource: https://github.com/{REPO}\n'
        f'Commit: `{commit}`\n\nInputs: `umalator-global/skillnames.json` and '
        '`umalator-global/umas.json`. GPL-3.0 license is included alongside this file.\n'
        'Enums contain character IDs, not outfit/card IDs. Duplicate normalized skill '
        'names have an ID suffix so no distinct skills become enum aliases.\n'
        'The catalog may include skills beyond the engine snapshot; enum membership '
        'does not guarantee that a supplied simulation skill table supports a skill.\n',
        encoding='utf-8')
    print(f'Generated {len(skills)} skills and {len(umas)} characters at {commit}')


if __name__ == '__main__':
    main()

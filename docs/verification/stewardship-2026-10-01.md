# Stewardship closure — 2026-10-01

## Maintainer authorization and merged state

The maintainer explicitly requested merging the open PRs in the project chat.
The protected workflow merged:

| PR | Scope | Merge commit |
| --- | --- | --- |
| [#1](https://github.com/ahmetcemkaraca/AutoCAD_MCP/pull/1) | Stewardship baseline | `a43e8c8187e9ce8c00bbba5d36f904f9932965c7` |
| [#2](https://github.com/ahmetcemkaraca/AutoCAD_MCP/pull/2) | Canonical core and guarded Windows smoke preparation | `b57db8943f46ccb775155dcea9f07a81ae6f1468` |
| [#3](https://github.com/ahmetcemkaraca/AutoCAD_MCP/pull/3) | Dependency updates on the canonical uv baseline | `52448cb94328f3d9b45ec847bcf74296f25e5fc4` |

PR #1 changes no runtime Python source. PRs #2/#3 are subsequent implementation
evidence and are not used as proof of real AutoCAD compatibility.

## Repository protection readback

Commands executed on 2026-10-01:

```bash
gh api repos/ahmetcemkaraca/AutoCAD_MCP/rules/branches/main
gh api repos/ahmetcemkaraca/AutoCAD_MCP/branches/archive/protection
gh pr list --state merged --limit 3 --json number,mergedAt,mergeCommit,url
```

`main` rules require pull requests, resolved review threads, and linear history;
they prohibit deletion and non-fast-forward updates. Allowed merge methods are
squash/rebase. The single-maintainer policy requires zero approving GitHub
reviews. Maintainer chat authorization and independent pre-merge code review
were obtained; this is not recorded as an approving GitHub review.

`archive` has `lock_branch.enabled=true`, `allow_force_pushes.enabled=false`,
and `allow_deletions.enabled=false`. No archive content was changed.

## Documentation and archive verification

At merged baseline `52448cb`, the canonical relative-link check covered
31 Markdown documents and 107 local links: zero missing targets. The audit
contained 64 archive entries matching all 64 retained files, with zero missing
or unaudited paths. The check excludes historical documents from current-link
validation and excludes fenced examples from actual Markdown links.

Reproduce the structural check from the repository root:

```bash
python3 - <<'PY'
from pathlib import Path
import re
from urllib.parse import unquote

root = Path.cwd()
files = [root / 'README.md', root / 'AGENTS.md', *(root / 'docs').rglob('*.md')]
files = [p for p in files if 'legacy' not in p.relative_to(root).parts]
missing = []
links = 0
for document in files:
    prose = re.sub(r'```.*?```', '', document.read_text(), flags=re.S)
    for href in re.findall(r'\[[^\]]*\]\(([^)]+)\)', prose):
        target = unquote(href.split('#')[0].split(' "')[0].strip('<>'))
        if not target or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
            continue
        links += 1
        if not (document.parent / target).exists():
            missing.append((str(document.relative_to(root)), target))
audit = (root / 'docs/legacy/document-audit.md').read_text()
listed = set(re.findall(r'\| `[^`]+` \| `(imported-2025/[^`]+)` \|', audit))
actual = {
    str(p.relative_to(root / 'docs/legacy'))
    for p in (root / 'docs/legacy/imported-2025').rglob('*') if p.is_file()
}
print(len(files), links, len(listed), len(actual), missing)
assert not missing and listed == actual
PY
python3 -m json.tool mcp.json > /dev/null
python3 -m compileall -q src tests
git diff --check
```

The closure update changes only contributor/documentation status and this
record. Document/link counts may grow with subsequent verified deliveries.

## Acceptance boundary

EPIC-00 / Roadmap Stage 1 is accepted. EPIC-02's canonical core is merged and
portable tests pass. EPIC-01 Windows installation and EPIC-03 real-AutoCAD
acceptance remain pending. No full AutoCAD release is verified by this record.

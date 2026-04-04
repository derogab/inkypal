#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: .scripts/release-version.sh <version> <tag-message>

Example:
  .scripts/release-version.sh 0.1.0 "InkyPal debut"
EOF
}

if [[ $# -ne 2 ]]; then
  usage
  exit 1
fi

version="${1#v}"
tag="v${version}"
tag_message="$2"

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if [[ -n "$(git status --porcelain)" ]]; then
  printf 'Working tree must be clean before cutting a release.\n' >&2
  exit 1
fi

if git rev-parse --verify "$tag" >/dev/null 2>&1; then
  printf 'Tag %s already exists.\n' "$tag" >&2
  exit 1
fi

python3 - "$version" <<'PY'
from pathlib import Path
import re
import sys

version = sys.argv[1]
updates = {
    Path("src/inkypal/__init__.py"): (
        r'__version__ = "[^"]+"',
        f'__version__ = "{version}"',
    ),
    Path("pyproject.toml"): (
        r'version = "[^"]+"',
        f'version = "{version}"',
    ),
}

for path, (pattern, replacement) in updates.items():
    original = path.read_text()
    updated, count = re.subn(pattern, replacement, original, count=1)
    if count != 1:
        raise SystemExit(f"Failed to update version in {path}")
    path.write_text(updated)
PY

git add src/inkypal/__init__.py pyproject.toml
git commit -m "chore(release): cut ${tag}"
git tag -a "$tag" -m "$tag_message"

printf 'Created commit and tag %s.\n' "$tag"

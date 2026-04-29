#!/usr/bin/env bash
# Usage: scripts/bump-version.sh <new-version>
# e.g.   scripts/bump-version.sh 0.3.0
set -euo pipefail

NEW="${1:?Usage: $0 <new-version>}"

# Validate semver-ish format
if ! [[ "$NEW" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Error: version must be semver (e.g. 1.2.3)" >&2
  exit 1
fi

TAG="v$NEW"

# Update plugin.json
node -e "
const fs = require('fs');
const p = JSON.parse(fs.readFileSync('plugin.json','utf8'));
p.version = '$NEW';
fs.writeFileSync('plugin.json', JSON.stringify(p, null, 2) + '\n');
"

# Update gemini-extension.json
node -e "
const fs = require('fs');
const g = JSON.parse(fs.readFileSync('gemini-extension.json','utf8'));
g.version = '$NEW';
fs.writeFileSync('gemini-extension.json', JSON.stringify(g, null, 2) + '\n');
"

git add plugin.json gemini-extension.json
git commit -m "chore: bump version to $NEW"
git tag "$TAG"

echo "Bumped to $NEW and created tag $TAG"
echo "Push with: git push && git push origin $TAG"

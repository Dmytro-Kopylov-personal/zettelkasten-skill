#!/usr/bin/env bash
#
# Install the rendered skill into a platform's skills tree.
#
# The repo is canonical; this copies into a tree that an OS-level backup also writes to. So
# the install is idempotent and every overwrite is preceded by a backup — the five cases in
# "classify" below. Nothing here reads a config file, a network, or an environment variable
# other than the ones named in the usage.
#
#   ./install.sh --platform hermes [--dry-run] [--force]
#   ./install.sh --platform copilot --project-root DIR
#   ./install.sh --target-root DIR      # test seam: pretend DIR is the home directory
#
# --dry-run writes nothing, including the manifest.
# Exit: 0 ok · 1 render failure · 2 usage · 3 platform not detected · 4 unmanaged file.
#
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
SKILL_NAME=zettelkasten

PLATFORM=""
DRY_RUN=0
FORCE=0
PROJECT_ROOT=""
TARGET_ROOT=""

usage() {
  cat <<'TEXT'
usage: install.sh [--platform hermes|claude|copilot] [--project-root DIR]
                  [--target-root DIR] [--dry-run] [--force]

  --platform      where to install; detected from the existing skills roots if omitted
  --project-root  copilot only: install into DIR/.github/skills instead of the home tree
  --target-root   pretend DIR is the home directory (used by the tests)
  --dry-run       report what would happen and write nothing, manifest included
  --force         create the skills root if it does not exist
TEXT
}

die() { printf 'install: %s\n' "$*" >&2; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --platform)     [ $# -ge 2 ] || die "--platform needs a value"; PLATFORM="$2"; shift 2 ;;
    --project-root) [ $# -ge 2 ] || die "--project-root needs a value"; PROJECT_ROOT="$2"; shift 2 ;;
    --target-root)  [ $# -ge 2 ] || die "--target-root needs a value"; TARGET_ROOT="$2"; shift 2 ;;
    --dry-run)      DRY_RUN=1; shift ;;
    --force)        FORCE=1; shift ;;
    -h|--help)      usage; exit 0 ;;
    *)              die "unknown argument: $1" ;;
  esac
done

case "$PLATFORM" in
  ""|hermes|claude|copilot) ;;
  *) die "--platform must be hermes, claude or copilot (got '$PLATFORM')" ;;
esac
if [ -n "$PROJECT_ROOT" ] && [ "$PLATFORM" != "copilot" ]; then
  die "--project-root only applies to --platform copilot"
fi

HOME_DIR="${TARGET_ROOT:-$HOME}"
# The manifest lives outside every skills tree: a file inside the skill directory would be
# copied into a vault by the backup, and would then look like a skill resource.
if [ -n "$TARGET_ROOT" ]; then
  STATE_DIR="$TARGET_ROOT/.local/state/zettelkasten-skill"
else
  STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/zettelkasten-skill"
fi

platform_root() {
  case "$1" in
    hermes)  printf '%s/.hermes/skills/research' "$HOME_DIR" ;;
    claude)  printf '%s/.claude/skills' "$HOME_DIR" ;;
    copilot)
      if [ -n "$PROJECT_ROOT" ]; then printf '%s/.github/skills' "$PROJECT_ROOT"
      else printf '%s/.copilot/skills' "$HOME_DIR"; fi ;;
  esac
}

if [ -z "$PLATFORM" ]; then
  # Detection runs in this shell, not in a function called through a command substitution:
  # an `exit` inside a substitution only ends the subshell, so the caller would see a
  # non-zero status and report the wrong reason for it.
  found=""
  for candidate in hermes claude copilot; do
    if [ -d "$(platform_root "$candidate")" ]; then found="$found $candidate"; fi
  done
  # shellcheck disable=SC2086
  set -- $found
  case $# in
    0) printf 'install: no skills root found — pass --platform and --force to create one\n' >&2
       exit 3 ;;
    1) PLATFORM="$1" ;;
    *) printf 'install: several skills roots exist (%s) — name one with --platform\n' "$*" >&2
       exit 2 ;;
  esac
fi

ROOT=$(platform_root "$PLATFORM")
DEST="$ROOT/$SKILL_NAME"
if [ ! -d "$ROOT" ]; then
  if [ "$FORCE" != 1 ]; then
    printf 'install: %s does not exist — create it, or pass --force\n' "$ROOT" >&2
    exit 3
  fi
fi

command -v python3 >/dev/null 2>&1 || { printf 'install: python3 is required\n' >&2; exit 1; }
if ! command -v shasum >/dev/null 2>&1 && ! command -v sha256sum >/dev/null 2>&1; then
  printf 'install: no sha256 tool (shasum or sha256sum)\n' >&2
  exit 1
fi

digest() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | awk '{print $1}'
  else sha256sum "$1" | awk '{print $1}'; fi
}

# --- stage the payload -----------------------------------------------------------------
# Render first and let the renderer fail closed: it validates the frontmatter, the size and
# the body before a byte reaches a skills tree.

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT

if ! python3 "$REPO/src/render.py" --platform "$PLATFORM" --out "$STAGE/render" >/dev/null; then
  printf 'install: render failed for %s\n' "$PLATFORM" >&2
  exit 1
fi

PAYLOAD="$STAGE/payload"
mkdir -p "$PAYLOAD"
cp "$STAGE/render/$PLATFORM/SKILL.md" "$PAYLOAD/SKILL.md"
for part in references templates scripts; do
  if [ -d "$REPO/skill/$part" ]; then cp -R "$REPO/skill/$part" "$PAYLOAD/$part"; fi
done
# Bytecode caches and editor droppings are not part of the skill.
find "$PAYLOAD" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$PAYLOAD" -name '.DS_Store' -delete 2>/dev/null || true

MANIFEST="$STATE_DIR/manifest.$PLATFORM.txt"

# What the manifest says we own: one "sha256  relpath" per line.
recorded_digest() {
  if [ ! -f "$MANIFEST" ]; then return 0; fi
  awk -v p="$1" 'length($1) == 64 { d = $1; $1 = ""; sub(/^ +/, ""); if ($0 == p) { print d; exit } }' "$MANIFEST"
}

payload_files() { (cd "$PAYLOAD" && find . -type f | sed 's|^\./||' | LC_ALL=C sort); }

# --- classify every payload file -------------------------------------------------------
#
# Five cases, in the order they are decided:
#   not there                            -> write
#   there and identical                   -> keep
#   there, differs, and the manifest owns it -> back up, then write
#   there, differs, and the manifest does not exist -> refuse
#   there, differs, and the manifest does not list it -> refuse

: >"$STAGE/keep"; : >"$STAGE/write"; : >"$STAGE/backup"; : >"$STAGE/refuse"

while IFS= read -r rel; do
  src="$PAYLOAD/$rel"
  dst="$DEST/$rel"
  have=$(recorded_digest "$rel")
  if [ ! -e "$dst" ]; then
    printf '%s\n' "$rel" >>"$STAGE/write"
  elif [ "$(digest "$dst")" = "$(digest "$src")" ]; then
    printf '%s\n' "$rel" >>"$STAGE/keep"
  elif [ -n "$have" ]; then
    printf '%s\n' "$rel" >>"$STAGE/write"
    printf '%s\n' "$rel" >>"$STAGE/backup"
  else
    printf '%s\n' "$rel" >>"$STAGE/refuse"
  fi
done < <(payload_files)

count() { if [ -s "$1" ]; then wc -l <"$1" | tr -d ' '; else printf '0'; fi; }

refused=$(count "$STAGE/refuse")
if [ "$refused" != 0 ]; then
  printf 'install: refusing to overwrite %s file(s) this installer does not manage:\n' "$refused" >&2
  sed 's/^/  /' "$STAGE/refuse" >&2
  printf 'install: move them aside, or install somewhere else — there is no --force for this.\n' >&2
  exit 4
fi

# --- apply ------------------------------------------------------------------------------

writes=$(count "$STAGE/write")
kept=$(count "$STAGE/keep")
backups=$(count "$STAGE/backup")
manifest_exists=0
if [ -f "$MANIFEST" ]; then manifest_exists=1; fi

if [ "$DRY_RUN" = 1 ]; then
  printf 'dry run: %s -> %s\n' "$PLATFORM" "$DEST"
  printf '  would write:   %s\n' "$writes"
  printf '  would back up: %s\n' "$backups"
  printf '  unchanged:     %s\n' "$kept"
  printf '  manifest:      %s%s\n' "$MANIFEST" "$([ "$manifest_exists" = 0 ] && printf ' (absent: the files would be adopted)' || true)"
  exit 0
fi

if [ "$writes" != 0 ]; then
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    dst="$DEST/$rel"
    mkdir -p "$(dirname "$dst")"
    if [ -e "$dst" ]; then
      cp -p "$dst" "$dst.bak.$stamp"
      printf 'backed up: %s\n' "$rel.bak.$stamp"
    fi
    cp -p "$PAYLOAD/$rel" "$dst"
    printf 'wrote:     %s\n' "$rel"
  done <"$STAGE/write"
fi

if [ "$manifest_exists" = 0 ] && [ "$writes" = 0 ]; then
  printf 'adopted: %s file(s) already match the current render\n' "$kept"
fi

mkdir -p "$STATE_DIR"
{
  while IFS= read -r rel; do
    printf '%s  %s\n' "$(digest "$PAYLOAD/$rel")" "$rel"
  done < <(payload_files)
} >"$MANIFEST.tmp"
mv "$MANIFEST.tmp" "$MANIFEST"

printf 'install: %s ok — %s written, %s unchanged, manifest at %s\n' \
  "$PLATFORM" "$writes" "$kept" "$MANIFEST"

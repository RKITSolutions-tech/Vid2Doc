#!/usr/bin/env bash

# fix_git_settings.sh
#
# Purpose: Normalize SSH permissions for Git usage and optionally validate
#          GitHub SSH connectivity and fetch from current repo.
#
# Safe defaults:
# - ~/.ssh directory: 700
# - private keys, config, authorized_keys: 600
# - public keys (*.pub), known_hosts: 644
# - Ownership to current user (best-effort; will warn if chown fails)
#
# Optional steps:
# - Check current repo remote and test ls-remote/fetch
# - SSH auth check to GitHub (no interactive prompts)
# - Add Git safe.directory (opt-in)
#
# Usage:
#   rkscripts/fix_git_settings.sh [--check] [--repo PATH] [--ssh-test]
#                                 [--fetch] [--set-safe-dir PATH]
#                                 [--verbose]
#
# Examples:
#   rkscripts/fix_git_settings.sh --ssh-test --fetch
#   rkscripts/fix_git_settings.sh --check
#   rkscripts/fix_git_settings.sh --repo /app --set-safe-dir /app

set -euo pipefail

VERBOSE=0
DO_CHECK=0
DO_SSH_TEST=0
DO_FETCH=0
SAFE_DIR=""
REPO_PATH=""

log() {
  echo "[fix-git] $*"
}

vlog() {
  if [[ "$VERBOSE" == "1" ]]; then
    echo "[fix-git][verbose] $*"
  fi
}

warn() {
  echo "[fix-git][warn] $*" >&2
}

usage() {
  sed -n '1,80p' "$0" | sed -n '/^# Usage:/,$p' | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check)
      DO_CHECK=1
      shift ;;
    --repo)
      REPO_PATH=${2:-}
      shift 2 ;;
    --ssh-test)
      DO_SSH_TEST=1
      shift ;;
    --fetch)
      DO_FETCH=1
      shift ;;
    --set-safe-dir)
      SAFE_DIR=${2:-}
      shift 2 ;;
    --verbose|-v)
      VERBOSE=1
      shift ;;
    --help|-h)
      usage
      exit 0 ;;
    *)
      warn "Unknown argument: $1"
      usage
      exit 1 ;;
  esac
done

# Resolve HOME and USER
USER_NAME=$(id -un)
USER_GROUP=$(id -gn)
HOME_DIR=$(getent passwd "$USER_NAME" | cut -d: -f6)
HOME_DIR=${HOME_DIR:-$HOME}

SSH_DIR="$HOME_DIR/.ssh"

show_current_state() {
  log "Current user: $USER_NAME ($USER_GROUP)"
  log "Home dir: $HOME_DIR"
  if [[ -d "$SSH_DIR" ]]; then
    vlog "Listing $SSH_DIR"
    ls -ld "$SSH_DIR" || true
    ls -la "$SSH_DIR" || true
    command -v stat >/dev/null 2>&1 && stat -c '%n -> owner=%U group=%G perms=%a' "$SSH_DIR" "$SSH_DIR"/* 2>/dev/null || true
  else
    warn "$SSH_DIR does not exist. It will be created during fix phase."
  fi
}

fix_permissions() {
  if [[ ! -d "$SSH_DIR" ]]; then
    log "Creating $SSH_DIR"
    mkdir -p "$SSH_DIR"
  fi

  # Ensure ownership (best effort; may require sudo in some environments)
  if chown -R "$USER_NAME":"$USER_GROUP" "$SSH_DIR" 2>/dev/null; then
    vlog "Ownership set to $USER_NAME:$USER_GROUP"
  elif command -v sudo >/dev/null 2>&1 && sudo chown -R "$USER_NAME":"$USER_GROUP" "$SSH_DIR" 2>/dev/null; then
    vlog "Ownership set with sudo to $USER_NAME:$USER_GROUP"
  else
    warn "Could not change ownership of $SSH_DIR. You may need to run this script with sudo."
  fi

  chmod 700 "$SSH_DIR" || warn "Failed to chmod 700 $SSH_DIR"

  # Normalize file permissions
  shopt -s nullglob
  for f in "$SSH_DIR"/*; do
    base=$(basename "$f")
    case "$base" in
      *.pub)
        chmod 644 "$f" || warn "Failed to chmod 644 $f" ;;
      known_hosts|known_hosts.old)
        chmod 644 "$f" 2>/dev/null || chmod 600 "$f" 2>/dev/null || warn "Failed to set perms on $f" ;;
      config|authorized_keys|id_rsa|id_ed25519|id_dsa|id_ecdsa|id_ed448|*.ppk|key*|*.key)
        chmod 600 "$f" || warn "Failed to chmod 600 $f" ;;
      *)
        # Default to private unless clearly public
        chmod 600 "$f" || warn "Failed to chmod 600 $f" ;;
    esac
  done
  shopt -u nullglob

  # Show resulting state
  show_current_state
}

ssh_github_test() {
  if [[ "$DO_SSH_TEST" -eq 0 ]]; then
    return 0
  fi
  log "Testing SSH to GitHub (non-interactive)..."
  set +e
  OUT=$(ssh -o BatchMode=yes -T git@github.com 2>&1)
  CODE=$?
  set -e
  echo "$OUT"
  if [[ $CODE -eq 1 && "$OUT" == *"successfully authenticated"* ]]; then
    log "SSH authentication to GitHub is working."
    return 0
  fi
  if [[ $CODE -ne 0 ]]; then
    warn "SSH test did not succeed (exit $CODE). If your key is passphrase-protected, you may need to run:"
    echo "  eval \"\$(ssh-agent -s)\""
    echo "  ssh-add ~/.ssh/<your_private_key>"
    return $CODE
  fi
}

git_repo_ops() {
  local repo=${REPO_PATH:-$(pwd)}
  if [[ ! -d "$repo/.git" ]]; then
    vlog "$repo is not a git repository; skipping repo operations."
    return 0
  fi
  log "Repository: $repo"
  (cd "$repo" && {
    log "Remotes:"
    git remote -v || true
    if [[ "$DO_FETCH" -eq 1 ]]; then
      log "Testing connectivity via: git ls-remote origin"
      if git ls-remote origin >/dev/null 2>&1; then
        log "Origin reachable. Running: git fetch --tags --prune"
        git fetch --tags --prune || warn "git fetch failed"
      else
        warn "Origin is not reachable. Check SSH/auth."
      fi
    fi
  })
}

set_safe_directory() {
  if [[ -n "$SAFE_DIR" ]]; then
    log "Configuring git safe.directory for $SAFE_DIR (global)"
    git config --global --add safe.directory "$SAFE_DIR" || warn "Failed to add safe.directory"
  fi
}

# Set global git identity to repository owner's preferred values
set_git_identity() {
  if ! command -v git >/dev/null 2>&1; then
    warn "git not found; skipping global identity configuration"
    return 0
  fi

  local cur_name
  local cur_email
  cur_name=$(git config --global user.name 2>/dev/null || true)
  cur_email=$(git config --global user.email 2>/dev/null || true)

  log "Current git global user.name: ${cur_name:-<not set>}"
  log "Current git global user.email: ${cur_email:-<not set>}"

  # Desired values (from request)
  local desired_name="Ryan Kenning"
  local desired_email="rkenning2@gmail.com"

  if git config --global user.name "$desired_name" && git config --global user.email "$desired_email"; then
    log "Set git global user.name to '$desired_name' and user.email to '$desired_email'"
  else
    warn "Failed to set git global user.name/user.email"
  fi
}

main() {
  if [[ "$DO_CHECK" -eq 1 ]]; then
    show_current_state
  else
    fix_permissions
  fi
  set_safe_directory
  set_git_identity
  ssh_github_test || true
  git_repo_ops || true
  log "Done."
}

main "$@"

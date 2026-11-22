#!/usr/bin/env bash
set -euo pipefail

# Zero-to-Full Gate-0 user-space bootstrapper for TDQ-Workflow on macOS and Linux.
# Never executes sudo silently; prints exact distro package commands if git is absent.

DRY_RUN=0
KHONG_CHAM_MAY="${TDQ_KHONG_CHAM_MAY:-0}"
STATE_DIR=""
REPO_URL="https://github.com/TDQUOC/TDQ-Workflow-Antigravity.git"
BRANCH="dev"

log_info() {
  if [[ "${TDQ_LOG:-1}" == "0" ]]; then
    return 0
  fi
  local stamp
  stamp="$(date -u '+%Y-%m-%dT%H:%M:%S' 2>/dev/null || echo '1970-01-01T00:00:00')"
  printf '[%s] bootstrap.sh: %s\n' "$stamp" "$*" >&2
}

is_dry() {
  [[ "$DRY_RUN" -eq 1 || "$KHONG_CHAM_MAY" == "1" ]]
}

usage() {
  cat <<'EOF'
Usage: bootstrap.sh [--dry-run] [--state-dir <path>] [--khong-cham-may] [--repo-url <url>] [--branch <branch>]
EOF
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --dry-run)
        DRY_RUN=1
        shift
        ;;
      --khong-cham-may)
        KHONG_CHAM_MAY=1
        shift
        ;;
      --state-dir)
        if [[ $# -lt 2 ]]; then
          printf 'Missing value for --state-dir\n' >&2
          exit 2
        fi
        STATE_DIR="$2"
        shift 2
        ;;
      --repo-url)
        REPO_URL="$2"
        shift 2
        ;;
      --branch)
        BRANCH="$2"
        shift 2
        ;;
      --help|-h)
        usage
        exit 0
        ;;
      *)
        printf 'Unknown option: %s\n' "$1" >&2
        exit 2
        ;;
    esac
  done
}

prepend_path_dir() {
  local dir="$1"
  if [[ -z "$dir" ]]; then
    return 0
  fi
  case ":${PATH}:" in
    *":${dir}:"*) ;;
    *) PATH="${dir}:${PATH}" ;;
  esac
  export PATH
}

print_missing_git_instruction() {
  local os_name
  os_name="$(uname -s 2>/dev/null || echo Linux)"
  if [[ "$os_name" == "Darwin" ]]; then
    if command -v brew >/dev/null 2>&1; then
      printf 'Git is required. Run: brew install git\n' >&2
    else
      printf 'Git is required. Run: xcode-select --install\n' >&2
    fi
    return 1
  fi
  if command -v apt-get >/dev/null 2>&1; then
    printf 'Git is required on minimal Linux. Run: sudo apt-get install -y git\n' >&2
  elif command -v dnf >/dev/null 2>&1; then
    printf 'Git is required on minimal Linux. Run: sudo dnf install -y git\n' >&2
  elif command -v yum >/dev/null 2>&1; then
    printf 'Git is required on minimal Linux. Run: sudo yum install -y git\n' >&2
  elif command -v pacman >/dev/null 2>&1; then
    printf 'Git is required on minimal Linux. Run: sudo pacman -S --noconfirm git\n' >&2
  elif command -v apk >/dev/null 2>&1; then
    printf 'Git is required on minimal Linux. Run: sudo apk add git\n' >&2
  else
    printf 'Git is required. Install git via your package manager (e.g. sudo apt-get install -y git or sudo dnf install -y git).\n' >&2
  fi
  return 1
}

require_git() {
  if command -v git >/dev/null 2>&1; then
    return 0
  fi
  print_missing_git_instruction
  exit 1
}

update_shell_profiles() {
  local local_bin="$HOME/.local/bin"
  prepend_path_dir "$local_bin"
  prepend_path_dir "$HOME/.npm-global/bin"
  if is_dry; then
    log_info "[dry-run] Would ensure $local_bin is added to shell profile"
    return 0
  fi
  mkdir -p "$local_bin"
  local marker_start="# >>> tdq-workflow PATH >>>"
  local marker_end="# <<< tdq-workflow PATH <<<"
  local profile
  for profile in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.profile"; do
    if [[ -f "$profile" || "$profile" == "$HOME/.profile" ]]; then
      if grep -Fq "$marker_start" "$profile" 2>/dev/null; then
        continue
      fi
      {
        printf '\n%s\n' "$marker_start"
        printf 'export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"\n'
        printf '%s\n' "$marker_end"
      } >>"$profile"
    fi
  done
}

ensure_uv_and_python() {
  if ! command -v uv >/dev/null 2>&1; then
    if is_dry; then
      log_info "[dry-run] Would install uv via https://astral.sh/uv/install.sh"
    else
      log_info "Installing uv in user-space..."
      curl -LsSf "https://astral.sh/uv/install.sh" | sh
      prepend_path_dir "$HOME/.local/bin"
    fi
  fi
  if command -v python3 >/dev/null 2>&1; then
    if python3 -c "import sys; assert sys.version_info >= (3, 9)" >/dev/null 2>&1; then
      return 0
    fi
  fi
  if is_dry; then
    log_info "[dry-run] Would run uv python install --default"
    return 0
  fi
  if command -v uv >/dev/null 2>&1; then
    log_info "Installing managed Python 3 via uv..."
    uv python install --default
  fi
}

node_meets_min() {
  if ! command -v node >/dev/null 2>&1; then
    return 1
  fi
  local ver major
  ver="$(node --version 2>/dev/null || true)"
  major="${ver#v}"
  major="${major%%.*}"
  [[ "$major" =~ ^[0-9]+$ ]] && [[ "$major" -ge 18 ]]
}

ensure_fnm_and_node() {
  prepend_path_dir "$HOME/.local/share/fnm/aliases/default/bin"
  prepend_path_dir "$HOME/.fnm/aliases/default/bin"
  if node_meets_min; then
    return 0
  fi
  if is_dry; then
    log_info "[dry-run] Would install fnm + Node.js LTS (>=18) in user-space"
    return 0
  fi
  log_info "Installing fnm and Node.js LTS in user-space..."
  curl -fsSL "https://fnm.vercel.app/install" | bash -s -- --skip-shell
  local fnm_bin=""
  for cand in "$HOME/.local/share/fnm/fnm" "$HOME/.fnm/fnm" "$(command -v fnm 2>/dev/null || true)"; do
    if [[ -n "$cand" && -x "$cand" ]]; then
      fnm_bin="$cand"
      break
    fi
  done
  if [[ -n "$fnm_bin" ]]; then
    "$fnm_bin" install --lts
    "$fnm_bin" default lts-latest
    prepend_path_dir "$HOME/.local/share/fnm/aliases/default/bin"
    prepend_path_dir "$HOME/.fnm/aliases/default/bin"
  fi
}

ensure_agy_cli() {
  if command -v agy >/dev/null 2>&1; then
    return 0
  fi
  if is_dry; then
    log_info "[dry-run] Would install agy CLI via https://antigravity.google/cli/install.sh"
    return 0
  fi
  log_info "Attempting user-space agy CLI installation..."
  if ! curl -fsSL "https://antigravity.google/cli/install.sh" | bash; then
    log_info "agy CLI auto-install unavailable. Download from https://antigravity.google/download"
  fi
}

resolve_repo_root() {
  local src="${BASH_SOURCE[0]:-}"
  if [[ -n "$src" && -f "$src" ]]; then
    local script_dir parent_dir
    script_dir="$(cd "$(dirname "$src")" && pwd)"
    parent_dir="$(dirname "$script_dir")"
    if [[ -f "$parent_dir/scripts/tdq_setup.py" && -f "$parent_dir/plugins/tdq-workflow-agy/plugin.json" ]]; then
      printf '%s\n' "$parent_dir"
      return 0
    fi
  fi
  local target="$HOME/.local/share/tdq-workflow-antigravity"
  if is_dry; then
    log_info "[dry-run] Would clone/update $REPO_URL ($BRANCH) into $target"
    printf '%s\n' "$target"
    return 0
  fi
  mkdir -p "$(dirname "$target")"
  if [[ -d "$target/.git" ]]; then
    log_info "Updating existing repository in $target..."
    git -C "$target" pull --ff-only
  else
    log_info "Cloning $REPO_URL into $target..."
    git clone --branch "$BRANCH" "$REPO_URL" "$target"
  fi
  printf '%s\n' "$target"
}

main() {
  parse_args "$@"
  require_git
  update_shell_profiles
  ensure_uv_and_python
  ensure_fnm_and_node
  ensure_agy_cli

  local repo_root
  repo_root="$(resolve_repo_root)"
  local probe_script="$repo_root/scripts/tdq_setup_probe.mjs"
  if command -v node >/dev/null 2>&1 && [[ -f "$probe_script" ]]; then
    log_info "Running Node pre-flight probe..."
    node "$probe_script" --json >/dev/null
  fi

  local plugin_dir="$repo_root/plugins/tdq-workflow-agy"
  if command -v agy >/dev/null 2>&1 && [[ -d "$plugin_dir" ]]; then
    if is_dry; then
      log_info "[dry-run] Would run agy plugin install \"$plugin_dir\" && agy plugin enable tdq-workflow-agy"
    else
      agy plugin install "$plugin_dir"
      agy plugin enable tdq-workflow-agy
    fi
  fi

  local setup_script="$repo_root/scripts/tdq_setup.py"
  local -a setup_args=("--setupfully")
  if [[ -n "$STATE_DIR" ]]; then
    setup_args+=("--state-dir" "$STATE_DIR")
  fi

  if is_dry; then
    log_info "[dry-run] Would run python3 -X utf8 \"$setup_script\" ${setup_args[*]}"
    return 0
  fi

  local py_bin
  py_bin="$(command -v python3 || command -v python || true)"
  if [[ -z "$py_bin" ]]; then
    printf 'No usable Python 3 interpreter found after bootstrap.\n' >&2
    exit 1
  fi
  "$py_bin" -X utf8 "$setup_script" "${setup_args[@]}"
}

main "$@"

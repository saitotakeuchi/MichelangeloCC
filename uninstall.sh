#!/bin/bash
#
# MichelangeloCC Uninstaller
#
# Removes MichelangeloCC and cleans up configuration.
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/saitotakeuchi/MichelangeloCC/main/uninstall.sh | bash
#

set -e

# === Colors ===
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; NC=''
fi

# === Output Functions ===
info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# === Utility Functions ===
command_exists() { command -v "$1" >/dev/null 2>&1; }

# === Main ===
main() {
    echo ""
    echo -e "${BOLD}MichelangeloCC Uninstaller${NC}"
    echo ""

    # Try pipx first
    if command_exists pipx; then
        info "Removing MichelangeloCC via pipx..."
        if pipx uninstall michelangelocc 2>/dev/null; then
            success "Removed MichelangeloCC"
        else
            warn "MichelangeloCC was not installed via pipx"
        fi
    fi

    # Try uv tool
    if command_exists uv; then
        info "Checking uv tools..."
        if uv tool uninstall michelangelocc 2>/dev/null; then
            success "Removed MichelangeloCC from uv"
        fi
    fi

    # Check if mcc still exists
    if command_exists mcc; then
        warn "mcc command still found at: $(which mcc)"
        warn "You may need to remove it manually or deactivate a virtual environment"
    else
        success "MichelangeloCC has been removed"
    fi

    echo ""
    echo "Note: The installer comment in your shell config file was not removed."
    echo "You can manually remove these lines if desired:"
    echo ""
    echo "  # Added by MichelangeloCC installer"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
}

main "$@"

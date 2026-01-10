#!/bin/bash
#
# MichelangeloCC Installer
#
# One-command installation that handles Python version detection,
# pipx installation, and PATH configuration automatically.
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/saitotakeuchi/MichelangeloCC/main/install.sh | bash
#
# Options:
#   --dry-run       Show what would be done without making changes
#   --no-color      Disable colored output
#   --from-source   Install from current directory (for development)
#   --upgrade       Upgrade existing installation
#

set -e

# === Configuration ===
MCC_PACKAGE="michelangelocc"
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=10

# === Parse Arguments ===
DRY_RUN=false
NO_COLOR=false
FROM_SOURCE=false
UPGRADE=false

for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
        --no-color) NO_COLOR=true ;;
        --from-source) FROM_SOURCE=true ;;
        --upgrade) UPGRADE=true ;;
        --help)
            echo "MichelangeloCC Installer"
            echo ""
            echo "Usage: ./install.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run       Show what would be done without making changes"
            echo "  --no-color      Disable colored output"
            echo "  --from-source   Install from current directory"
            echo "  --upgrade       Upgrade existing installation"
            echo "  --help          Show this help message"
            exit 0
            ;;
    esac
done

# === Colors ===
if [ "$NO_COLOR" = true ] || [ ! -t 1 ]; then
    RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; NC=''
else
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    NC='\033[0m'
fi

# === Output Functions ===
info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1" >&2; }
step()    { echo -e "\n${BOLD}==> $1${NC}"; }

# === Utility Functions ===
command_exists() { command -v "$1" >/dev/null 2>&1; }

run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} Would run: $*"
        return 0
    else
        "$@"
    fi
}

get_os() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*)  echo "linux" ;;
        MINGW*|CYGWIN*|MSYS*) echo "windows" ;;
        *) echo "unknown" ;;
    esac
}

get_linux_distro() {
    if [ -f /etc/os-release ]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

# === Print Banner ===
print_banner() {
    echo ""
    echo -e "${BLUE}${BOLD}"
    cat << 'EOF'
  __  __ _      _          _                       _
 |  \/  (_) ___| |__   ___| | __ _ _ __   __ _  ___| | ___
 | |\/| | |/ __| '_ \ / _ \ |/ _` | '_ \ / _` |/ _ \ |/ _ \
 | |  | | | (__| | | |  __/ | (_| | | | | (_| |  __/ | (_) |
 |_|  |_|_|\___|_| |_|\___|_|\__,_|_| |_|\__, |\___|_|\___/
                                         |___/            CC
EOF
    echo -e "${NC}"
    echo "  Claude Code-powered 3D model generator"
    echo ""
}

# === Python Version Check ===
check_python() {
    step "Checking Python version..."

    PYTHON_CMD=""

    # Try different Python commands in order of preference
    for cmd in python3.13 python3.12 python3.11 python3.10 python3 python; do
        if command_exists "$cmd"; then
            version=$($cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)

            if [ "$major" -ge "$MIN_PYTHON_MAJOR" ] && [ "$minor" -ge "$MIN_PYTHON_MINOR" ]; then
                PYTHON_CMD="$cmd"
                success "Found Python $version ($cmd)"
                return 0
            fi
        fi
    done

    error "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR} or higher is required."
    echo ""
    echo "Your current Python version is too old. Please install Python 3.10+:"
    echo ""

    case "$(get_os)" in
        macos)
            echo "  Using Homebrew (recommended):"
            echo "    brew install python@3.12"
            echo ""
            echo "  Or download from python.org:"
            echo "    https://www.python.org/downloads/"
            ;;
        linux)
            case "$(get_linux_distro)" in
                ubuntu|debian)
                    echo "  sudo apt update"
                    echo "  sudo apt install python3.12 python3.12-venv"
                    ;;
                fedora|rhel|centos)
                    echo "  sudo dnf install python3.12"
                    ;;
                arch|manjaro)
                    echo "  sudo pacman -S python"
                    ;;
                *)
                    echo "  Please install Python 3.10+ using your package manager"
                    ;;
            esac
            ;;
        *)
            echo "  Please install Python 3.10+ from https://www.python.org/downloads/"
            ;;
    esac
    echo ""
    echo "Then run this installer again."
    exit 1
}

# === Install pipx ===
install_pipx() {
    step "Installing pipx..."

    case "$(get_os)" in
        macos)
            if command_exists brew; then
                run_cmd brew install pipx
                run_cmd pipx ensurepath
            else
                error "Homebrew not found."
                echo ""
                echo "Please install Homebrew first:"
                echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
                echo ""
                echo "Then run this installer again."
                exit 1
            fi
            ;;
        linux)
            case "$(get_linux_distro)" in
                ubuntu|debian)
                    run_cmd sudo apt update
                    run_cmd sudo apt install -y pipx
                    run_cmd pipx ensurepath
                    ;;
                fedora|rhel|centos)
                    run_cmd sudo dnf install -y pipx
                    run_cmd pipx ensurepath
                    ;;
                arch|manjaro)
                    run_cmd sudo pacman -S --noconfirm python-pipx
                    run_cmd pipx ensurepath
                    ;;
                *)
                    # Fallback: install via pip with user flag
                    info "Installing pipx via pip..."
                    run_cmd "$PYTHON_CMD" -m pip install --user pipx
                    run_cmd "$PYTHON_CMD" -m pipx ensurepath
                    ;;
            esac
            ;;
        *)
            error "Unsupported operating system"
            exit 1
            ;;
    esac

    # Refresh PATH to include pipx
    export PATH="$HOME/.local/bin:$PATH"

    if command_exists pipx || [ "$DRY_RUN" = true ]; then
        success "pipx installed successfully"
    else
        error "Failed to install pipx"
        echo "Please install pipx manually: https://pipx.pypa.io/stable/installation/"
        exit 1
    fi
}

# === Install MichelangeloCC ===
install_mcc() {
    step "Installing MichelangeloCC..."

    local pipx_args=""
    if [ "$UPGRADE" = true ]; then
        pipx_args="--force"
    fi

    if [ "$FROM_SOURCE" = true ]; then
        if [ -f "pyproject.toml" ]; then
            run_cmd pipx install $pipx_args .
        else
            error "pyproject.toml not found in current directory"
            echo "Use --from-source only when running from the MichelangeloCC repository"
            exit 1
        fi
    else
        # Install from PyPI or git
        # For now, install from git since not yet on PyPI
        run_cmd pipx install $pipx_args "git+https://github.com/saitotakeuchi/MichelangeloCC.git"
    fi

    success "MichelangeloCC installed"
}

# === Configure Shell PATH ===
configure_shell() {
    step "Configuring shell..."

    local shell_rc=""
    local shell_name=""

    case "$SHELL" in
        */bash)
            shell_name="bash"
            if [ -f "$HOME/.bash_profile" ]; then
                shell_rc="$HOME/.bash_profile"
            else
                shell_rc="$HOME/.bashrc"
            fi
            ;;
        */zsh)
            shell_name="zsh"
            shell_rc="$HOME/.zshrc"
            ;;
        */fish)
            shell_name="fish"
            shell_rc="$HOME/.config/fish/config.fish"
            ;;
        *)
            warn "Unknown shell: $SHELL"
            warn "You may need to add ~/.local/bin to your PATH manually"
            return 0
            ;;
    esac

    if [ -n "$shell_rc" ]; then
        # Create rc file if it doesn't exist
        if [ ! -f "$shell_rc" ]; then
            touch "$shell_rc"
        fi

        # Check if PATH already includes ~/.local/bin
        if ! grep -q '\.local/bin' "$shell_rc" 2>/dev/null; then
            info "Adding ~/.local/bin to PATH in $shell_rc"
            if [ "$DRY_RUN" = false ]; then
                echo '' >> "$shell_rc"
                echo '# Added by MichelangeloCC installer' >> "$shell_rc"
                echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$shell_rc"
            else
                echo -e "${YELLOW}[DRY-RUN]${NC} Would add PATH to $shell_rc"
            fi
            success "Updated $shell_rc"
        else
            info "PATH already configured in $shell_rc"
        fi
    fi
}

# === Verify Installation ===
verify_installation() {
    step "Verifying installation..."

    # Refresh PATH
    export PATH="$HOME/.local/bin:$PATH"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY-RUN]${NC} Would verify: mcc version"
        return 0
    fi

    if command_exists mcc; then
        version=$(mcc version 2>/dev/null | head -1 || echo "installed")
        success "Installation verified: $version"
        return 0
    else
        warn "mcc command not found in current PATH"
        warn "You may need to restart your terminal"
        return 1
    fi
}

# === Print Success ===
print_success() {
    echo ""
    echo -e "${GREEN}${BOLD}=============================================${NC}"
    echo -e "${GREEN}${BOLD}  MichelangeloCC installed successfully!    ${NC}"
    echo -e "${GREEN}${BOLD}=============================================${NC}"
    echo ""
    echo "Quick Start:"
    echo ""
    echo "  Start an interactive session with Claude Code:"
    echo -e "    ${BOLD}mcc session \"Create a simple phone stand\"${NC}"
    echo ""
    echo "  Or create a project manually:"
    echo "    mcc new my_model --template mechanical"
    echo "    cd my_model"
    echo "    mcc preview model my_model.py"
    echo ""
    echo "Documentation:"
    echo "  https://github.com/saitotakeuchi/MichelangeloCC"
    echo ""

    if ! command_exists mcc 2>/dev/null; then
        echo -e "${YELLOW}NOTE:${NC} Please restart your terminal or run:"
        case "$SHELL" in
            */bash) echo "  source ~/.bashrc" ;;
            */zsh)  echo "  source ~/.zshrc" ;;
            *)      echo "  source your shell config file" ;;
        esac
        echo ""
    fi
}

# === Main ===
main() {
    print_banner

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}Running in dry-run mode - no changes will be made${NC}"
        echo ""
    fi

    # Step 1: Check Python version
    check_python

    # Step 2: Ensure pipx is available
    if ! command_exists pipx; then
        install_pipx
    else
        success "pipx already installed"
    fi

    # Step 3: Install MichelangeloCC
    install_mcc

    # Step 4: Configure shell PATH
    configure_shell

    # Step 5: Verify installation
    verify_installation || true

    # Step 6: Print success message
    print_success
}

# Run main
main "$@"

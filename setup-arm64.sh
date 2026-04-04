#!/bin/bash
# Setup ARM64 Python and PyTorch 2.6+ for speech-guider
# This script checks existing state and skips gracefully

set -e  # Exit on error

PROJECT_DIR="/Users/tonypace/Documents/Code/speech-guider"
VENV_NAME="speech-guider"
VENV_DIR="$PROJECT_DIR/$VENV_NAME"
BACKUP_NAME="speech-guider-x86-backup"

echo "=========================================="
echo "ARM64 Python Setup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_section() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

# Check if running on Apple Silicon
check_architecture() {
    ARCH=$(uname -m)
    CHIP=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "Unknown")
    
    echo "Current architecture: $ARCH"
    echo "CPU: $CHIP"
    
    if [[ "$CHIP" == *"Apple"* ]]; then
        if [[ "$ARCH" == "arm64" ]]; then
            print_status "Running natively on Apple Silicon (ARM64)"
        else
            print_warning "Running in x86_64 mode on Apple Silicon (using Rosetta)"
        fi
    else
        print_error "Not on Apple Silicon - ARM64 Python won't provide benefits"
        exit 1
    fi
}

# Check for ARM64 Homebrew
check_homebrew_arm64() {
    print_section "Checking ARM64 Homebrew"
    
    if [[ -d "/opt/homebrew" ]]; then
        print_status "ARM64 Homebrew found at /opt/homebrew"
        
        # Check if it's in PATH
        if [[ ":$PATH:" == *":/opt/homebrew/bin:"* ]]; then
            print_status "ARM64 Homebrew is in PATH"
        else
            print_warning "ARM64 Homebrew not in PATH - will add to .zshrc"
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
        
        HOMEBREW_PREFIX="/opt/homebrew"
    else
        print_error "ARM64 Homebrew not found at /opt/homebrew"
        echo "Please install ARM64 Homebrew first:"
        echo "  arch -arm64 /bin/bash -c '\"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"'"
        exit 1
    fi
}

# Check/Install Python 3.12 ARM64
check_python_arm64() {
    print_section "Checking Python 3.12 (ARM64)"
    
    PYTHON_ARM64="$HOMEBREW_PREFIX/opt/python@3.12/bin/python3"
    
    if [[ -f "$PYTHON_ARM64" ]]; then
        print_status "Python 3.12 (ARM64) found"
        PYTHON_VERSION=$($PYTHON_ARM64 --version 2>&1)
        print_status "Version: $PYTHON_VERSION"
        
        # Verify it's actually ARM64
        PYTHON_ARCH=$(file "$PYTHON_ARM64" | grep -o "arm64\|x86_64")
        if [[ "$PYTHON_ARCH" == *"arm64"* ]]; then
            print_status "Confirmed ARM64 architecture"
        else
            print_warning "Python appears to be $PYTHON_ARCH, not ARM64"
        fi
    else
        print_warning "Python 3.12 (ARM64) not found, installing..."
        $HOMEBREW_PREFIX/bin/brew install python@3.12
        
        if [[ -f "$PYTHON_ARM64" ]]; then
            print_status "Python 3.12 (ARM64) installed successfully"
        else
            print_error "Failed to install Python 3.12"
            exit 1
        fi
    fi
}

# Backup existing venv
backup_existing_venv() {
    print_section "Backing Up Existing Virtual Environment"
    
    if [[ -d "$VENV_DIR" ]]; then
        BACKUP_DIR="$PROJECT_DIR/$BACKUP_NAME"
        
        if [[ -d "$BACKUP_DIR" ]]; then
            print_warning "Backup already exists at $BACKUP_NAME"
            read -p "Overwrite existing backup? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf "$BACKUP_DIR"
            else
                print_warning "Keeping existing backup"
                return
            fi
        fi
        
        mv "$VENV_DIR" "$BACKUP_DIR"
        print_status "Existing venv backed up to $BACKUP_NAME"
    else
        print_warning "No existing venv found at $VENV_DIR"
    fi
}

# Create new ARM64 venv
create_arm64_venv() {
    print_section "Creating ARM64 Virtual Environment"
    
    PYTHON_ARM64="$HOMEBREW_PREFIX/opt/python@3.12/bin/python3"
    
    if [[ -d "$VENV_DIR" ]]; then
        print_warning "Virtual environment already exists"
        
        # Check if it's already ARM64
        if [[ -f "$VENV_DIR/bin/python" ]]; then
            VENV_ARCH=$(file "$VENV_DIR/bin/python" | grep -o "arm64\|x86_64")
            if [[ "$VENV_ARCH" == *"arm64"* ]]; then
                print_status "Existing venv is already ARM64 - skipping creation"
                return
            else
                print_warning "Existing venv is x86_64, will recreate"
                rm -rf "$VENV_DIR"
            fi
        fi
    fi
    
    echo "Creating virtual environment with ARM64 Python 3.12..."
    "$PYTHON_ARM64" -m venv "$VENV_DIR"
    
    print_status "Virtual environment created at $VENV_DIR"
}

# Install PyTorch 2.6+ (ARM64)
install_pytorch_arm64() {
    print_section "Installing PyTorch 2.6+ (ARM64)"
    
    source "$VENV_DIR/bin/activate"
    
    # Check current torch version
    CURRENT_TORCH=$(pip show torch 2>/dev/null | grep Version | cut -d' ' -f2 || echo "not installed")
    
    if [[ "$CURRENT_TORCH" == "2.6.0" ]] || [[ "$CURRENT_TORCH" == "2.6."* ]]; then
        print_status "PyTorch 2.6+ already installed ($CURRENT_TORCH)"
    else
        if [[ "$CURRENT_TORCH" != "not installed" ]]; then
            print_warning "Upgrading PyTorch from $CURRENT_TORCH to 2.6.0"
        fi
        
        echo "Installing PyTorch 2.6.0 and torchaudio 2.6.0..."
        pip install torch==2.6.0 torchaudio==2.6.0
        
        NEW_TORCH=$(pip show torch 2>/dev/null | grep Version | cut -d' ' -f2)
        print_status "PyTorch $NEW_TORCH installed"
    fi
}

# Install remaining requirements
install_requirements() {
    print_section "Installing Remaining Dependencies"
    
    source "$VENV_DIR/bin/activate"
    
    REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
    
    if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
        print_error "requirements.txt not found at $REQUIREMENTS_FILE"
        exit 1
    fi
    
    echo "Installing from requirements.txt (this may take a few minutes)..."
    pip install -r "$REQUIREMENTS_FILE" || {
        print_warning "Some packages may have failed, continuing..."
    }
    
    print_status "Dependencies installed"
}

# Verify installation
verify_installation() {
    print_section "Verifying Installation"
    
    source "$VENV_DIR/bin/activate"
    
    # Check Python version
    PYTHON_V=$(python --version)
    print_status "Python: $PYTHON_V"
    
    # Check architecture
    PYTHON_ARCH=$(file $(which python) | grep -o "arm64\|x86_64")
    print_status "Architecture: $PYTHON_ARCH"
    
    # Check PyTorch
    TORCH_V=$(python -c "import torch; print(torch.__version__)" 2>/dev/null || echo "not available")
    print_status "PyTorch: $TORCH_V"
    
    # Check if FastAPI imports work
    if python -c "from app.main import app; print('FastAPI app imports successfully')" 2>/dev/null; then
        print_status "FastAPI app imports: OK"
    else
        print_warning "FastAPI app import test failed (may need additional dependencies)"
    fi
    
    # List installed packages count
    PKG_COUNT=$(pip list | wc -l)
    print_status "Total packages installed: $PKG_COUNT"
}

# Print summary
print_summary() {
    print_section "Setup Complete!"
    
    echo ""
    echo "Next steps:"
    echo "  1. Activate the environment:"
    echo "     source $VENV_DIR/bin/activate"
    echo ""
    echo "  2. Run the server:"
    echo "     python -m app.main"
    echo ""
    echo "  3. Run E2E tests:"
    echo "     npm run test:e2e"
    echo ""
    echo "  4. If you need to rollback:"
    echo "     rm -rf $VENV_DIR"
    if [[ -d "$PROJECT_DIR/$BACKUP_NAME" ]]; then
        echo "     mv $PROJECT_DIR/$BACKUP_NAME $VENV_DIR"
    fi
    echo ""
}

# Main execution
main() {
    print_section "ARM64 Python Setup for speech-guider"
    
    check_architecture
    check_homebrew_arm64
    check_python_arm64
    backup_existing_venv
    create_arm64_venv
    install_pytorch_arm64
    install_requirements
    verify_installation
    print_summary
}

# Run main function
main "$@"

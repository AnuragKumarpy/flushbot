#!/bin/bash

# FlushBot Installation and Setup Script
# This script sets up FlushBot with all dependencies and configuration

set -e  # Exit on any error

echo "🤖 FlushBot - Advanced Telegram Security Bot"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3.9+ is available
check_python() {
    print_status "Checking Python version..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        REQUIRED_VERSION="3.9"
        
        if python3 -c "import sys; exit(0 if sys.version_info >= (3,9) else 1)"; then
            print_success "Python $PYTHON_VERSION found (✅ >= 3.9)"
            PYTHON_CMD="python3"
        else
            print_error "Python $PYTHON_VERSION found (❌ < 3.9 required)"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.9 or higher."
        exit 1
    fi
}

# Check if pip is available
check_pip() {
    print_status "Checking pip..."
    
    if command -v pip3 &> /dev/null; then
        print_success "pip3 found"
        PIP_CMD="pip3"
    elif command -v pip &> /dev/null; then
        print_success "pip found"
        PIP_CMD="pip"
    else
        print_error "pip not found. Please install pip."
        exit 1
    fi
}

# Install Python dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    if [ -f "requirements.txt" ]; then
        $PIP_CMD install -r requirements.txt
        print_success "Dependencies installed successfully"
    else
        print_error "requirements.txt not found"
        exit 1
    fi
}

# Setup environment file
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Created .env file from template"
            print_warning "Please edit .env file with your actual API keys and settings"
        else
            print_error ".env.example template not found"
            exit 1
        fi
    else
        print_warning ".env file already exists"
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p data/exports
    mkdir -p data/backups
    
    print_success "Directories created"
}

# Check Redis (optional)
check_redis() {
    print_status "Checking Redis server..."
    
    if command -v redis-server &> /dev/null; then
        if pgrep redis-server > /dev/null; then
            print_success "Redis server is running"
        else
            print_warning "Redis installed but not running. Start with: redis-server"
            print_warning "Redis is optional but recommended for performance"
        fi
    else
        print_warning "Redis not found. Installing Redis is recommended for caching"
        print_warning "On Ubuntu/Debian: sudo apt-get install redis-server"
        print_warning "On macOS: brew install redis"
    fi
}

# Initialize database
init_database() {
    print_status "Initializing database..."
    
    if $PYTHON_CMD setup_db.py; then
        print_success "Database initialized successfully"
    else
        print_error "Database initialization failed"
        print_error "Please check your database configuration in .env file"
        exit 1
    fi
}

# Main setup function
main() {
    echo
    print_status "Starting FlushBot setup..."
    echo
    
    # Check system requirements
    check_python
    check_pip
    
    # Install dependencies
    install_dependencies
    
    # Setup configuration
    setup_environment
    create_directories
    
    # Check optional services
    check_redis
    
    # Initialize database
    echo
    print_status "Database initialization will be done after you configure .env"
    
    echo
    echo "=============================================="
    print_success "FlushBot setup completed!"
    echo "=============================================="
    echo
    echo "📋 Next steps:"
    echo "1. Edit the .env file with your configuration:"
    echo "   - TELEGRAM_BOT_TOKEN (get from @BotFather)"
    echo "   - SUDO_USER_ID (your Telegram user ID)"
    echo "   - API keys are already provided"
    echo
    echo "2. Initialize the database:"
    echo "   python3 setup_db.py"
    echo
    echo "3. Start the bot:"
    echo "   python3 main.py"
    echo
    echo "📚 Documentation: DOCUMENTATION.md"
    echo "🆘 Support: Check README.md for troubleshooting"
    echo
    print_success "Happy moderating! 🛡️"
}

# Run main function
main
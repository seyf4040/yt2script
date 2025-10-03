#!/bin/bash

# Quick setup script for multi-user feature
# Run this after pulling the new code

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================"
echo "Multi-User Setup Script"
echo "======================================${NC}\n"

# Step 1: Check Python version
echo -e "${GREEN}[1/8] Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Step 2: Check if virtual environment exists
echo -e "\n${GREEN}[2/8] Checking virtual environment...${NC}"
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi

# Activate virtual environment
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null

# Step 3: Install/upgrade dependencies
echo -e "\n${GREEN}[3/8] Installing dependencies...${NC}"
pip install --upgrade pip > /dev/null
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Step 4: Check for .env file
echo -e "\n${GREEN}[4/8] Checking configuration...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}.env file not found. Creating from template...${NC}"
    cp .env.example .env
    echo "✓ .env file created"
    echo -e "${YELLOW}⚠️  IMPORTANT: Edit .env file with your configuration!${NC}"
    ENV_NEEDS_CONFIG=true
else
    echo "✓ .env file exists"
    ENV_NEEDS_CONFIG=false
fi

# Step 5: Check SECRET_KEY
echo -e "\n${GREEN}[5/8] Checking SECRET_KEY...${NC}"
if ! grep -q "^SECRET_KEY=.*[a-zA-Z0-9]" .env 2>/dev/null; then
    echo "Generating SECRET_KEY..."
    secret_key=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    if grep -q "^SECRET_KEY=" .env 2>/dev/null; then
        # Replace existing
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/^SECRET_KEY=.*/SECRET_KEY=$secret_key/" .env
        else
            sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$secret_key/" .env
        fi
    else
        # Add new
        echo "SECRET_KEY=$secret_key" >> .env
    fi
    echo "✓ SECRET_KEY generated"
else
    echo "✓ SECRET_KEY exists"
fi

# Step 6: Check if database needs migration
echo -e "\n${GREEN}[6/8] Checking database...${NC}"
if [ -f "transcripts.db" ]; then
    # Check if users table exists
    has_users=$(sqlite3 transcripts.db "SELECT name FROM sqlite_master WHERE type='table' AND name='users';" 2>/dev/null || echo "")
    
    if [ -z "$has_users" ]; then
        echo -e "${YELLOW}Database needs migration to multi-user format${NC}"
        echo "Run: python migrate_to_multiuser.py"
        NEEDS_MIGRATION=true
    else
        echo "✓ Database already migrated"
        NEEDS_MIGRATION=false
    fi
else
    echo "✓ No existing database (will be created on first run)"
    NEEDS_MIGRATION=false
fi

# Step 7: Test email configuration (if configured)
echo -e "\n${GREEN}[7/8] Checking email configuration...${NC}"
if grep -q "^SMTP_USERNAME=.*@" .env 2>/dev/null && grep -q "^SMTP_PASSWORD=." .env 2>/dev/null; then
    echo "Testing email connection..."
    python3 -c "
from email_service import email_service
import sys
success, error = email_service.test_connection()
if success:
    print('✓ Email service configured and working')
    sys.exit(0)
else:
    print(f'✗ Email test failed: {error}')
    print('Please check SMTP credentials in .env')
    sys.exit(1)
" && EMAIL_CONFIGURED=true || EMAIL_CONFIGURED=false
else
    echo -e "${YELLOW}Email not configured${NC}"
    echo "Set SMTP_* variables in .env for email notifications"
    EMAIL_CONFIGURED=false
fi

# Step 8: Summary and next steps
echo -e "\n${BLUE}======================================"
echo "Setup Summary"
echo "======================================${NC}"

echo -e "\n${GREEN}✓ Completed:${NC}"
echo "  - Python environment ready"
echo "  - Dependencies installed"
echo "  - Configuration file created"
echo "  - SECRET_KEY generated"

if [ "$NEEDS_MIGRATION" = true ]; then
    echo -e "\n${YELLOW}⚠️  Action Required:${NC}"
    echo "  1. Run database migration:"
    echo "     ${BLUE}python migrate_to_multiuser.py${NC}"
fi

if [ "$ENV_NEEDS_CONFIG" = true ] || [ "$EMAIL_CONFIGURED" = false ]; then
    echo -e "\n${YELLOW}⚠️  Configuration Needed:${NC}"
    echo "  1. Edit .env file with your settings:"
    echo "     - OPENAI_API_KEY (required)"
    if [ "$EMAIL_CONFIGURED" = false ]; then
        echo "     - SMTP credentials (for email notifications)"
    fi
fi

echo -e "\n${GREEN}📋 Next Steps:${NC}"

if [ "$NEEDS_MIGRATION" = true ]; then
    echo "  1. ${BLUE}python migrate_to_multiuser.py${NC} (create admin account)"
else
    echo "  1. Database ready ✓"
fi

echo "  2. ${BLUE}python app.py${NC} (start backend)"
echo "  3. ${BLUE}streamlit run ui.py${NC} (start UI in new terminal)"
echo "  4. Open http://localhost:8501 in browser"
echo "  5. Login with admin credentials"

echo -e "\n${GREEN}🧪 Testing:${NC}"
echo "  Run tests: ${BLUE}python test_multiuser.py${NC}"

echo -e "\n${GREEN}📚 Documentation:${NC}"
echo "  See IMPLEMENTATION_GUIDE.md for detailed instructions"

echo -e "\n${BLUE}======================================${NC}"
echo -e "${GREEN}Setup complete!${NC}\n"

# Ask if user wants to run migration now
if [ "$NEEDS_MIGRATION" = true ]; then
    echo -e "${YELLOW}Would you like to run the database migration now? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "\n${GREEN}Running migration...${NC}"
        python migrate_to_multiuser.py
    fi
fi
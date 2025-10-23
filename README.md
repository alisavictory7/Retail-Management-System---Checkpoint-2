# Retail Management System - Initial Setup & 2-Tier Architecture 

**Author:** Alisa

A comprehensive web-based retail management system built with Flask and PostgreSQL, featuring user authentication, product catalog management, shopping cart functionality, and payment processing with support for both cash and card payments.

## 🚀 Project Description

This Retail Management System is a full-stack web application designed to handle the core operations of a retail business. The system provides:

### Key Features
- **User Management**: Registration, login, and session management
- **Product Catalog**: Product management with pricing, inventory, and detailed attributes
- **Shopping Cart**: Dynamic cart with real-time calculations including discounts, shipping fees, and import duties
- **Payment Processing**: Support for both cash and card payments with validation
- **Order Management**: Complete sales tracking with detailed receipts
- **Inventory Management**: Real-time stock updates and conflict resolution
- **Business Logic**: Automatic calculation of shipping fees, import duties, and discounts based on product attributes

### Technical Architecture
- **Backend**: Flask (Python web framework)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Frontend**: HTML templates with CSS and JavaScript
- **Testing**: Comprehensive test suite with pytest
- **Security**: Password hashing with Werkzeug

## 📋 Prerequisites

Before setting up the project, ensure you have the following installed:

- **Python 3.10+** ([Download here](https://www.python.org/downloads/))
- **PostgreSQL 12+** ([Download here](https://www.postgresql.org/download/))
- **Git** ([Download here](https://git-scm.com/downloads))

## 🛠️ Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Retail-Management-System
```

### 2. Create and Activate Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the project root with your database credentials:

```env
DB_USERNAME=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=retail_system
```

## 🗄️ Database Setup

### Option 1: Using pgAdmin4 (Recommended for Windows)

Since you have pgAdmin4 open, this is the easiest method:

1. **Create Database in pgAdmin4:**
   - Right-click on "Databases" in the left panel
   - Select "Create" → "Database..."
   - Name: `retail_system` (or `retail_management`)
   - Click "Save"

2. **Initialize Database Schema:**
   ```powershell
   # Use full path to psql (replace with your PostgreSQL version if different)
   & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -d retail_system -f db/init.sql
   ```
   - Enter your postgres password when prompted

### Option 2: Using Command Line

#### For Windows Users:

1. **If psql is not recognized, use full path:**
   ```powershell
   # Check your PostgreSQL version first
   Get-ChildItem "C:\Program Files\PostgreSQL" -ErrorAction SilentlyContinue
   
   # Use full path (adjust version number as needed)
   & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres
   ```

2. **Create Database:**
   ```sql
   CREATE DATABASE retail_system;
   CREATE USER retail_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE retail_system TO retail_user;
   \q
   ```

3. **Initialize Schema:**
   ```powershell
   & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -d retail_system -f db/init.sql
   ```

#### For macOS/Linux Users:
```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE retail_system;

# Create user (optional, you can use existing user)
CREATE USER retail_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE retail_system TO retail_user;

# Exit PostgreSQL
\q

# Initialize schema
psql -U postgres -d retail_system -f db/init.sql
```

### 3. Verify Database Setup
You can verify the setup by connecting to your database and checking the tables:

**Using pgAdmin4:**
- Expand your `retail_system` database
- Expand "Schemas" → "public" → "Tables"
- You should see: User, Product, Sale, Payment, SaleItem, FailedPaymentLog

**Using Command Line:**
```powershell
# Windows
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -d retail_system

# macOS/Linux
psql -U postgres -d retail_system
```

Then run:
```sql
\dt  # List all tables
SELECT * FROM "Product";  # View sample products
\q
```

The initialization script will:
- Create all necessary tables (User, Product, Sale, Payment, SaleItem, FailedPaymentLog)
- Insert sample data including test products and users
- Set up proper foreign key relationships

## 🚀 Running the Application

### 1. Start the Flask Application
```bash
python run.py
```

The application will start on `http://localhost:5000`

### 2. Access the Application
Open your web browser and navigate to:
- **Main Application**: http://localhost:5000
- **Login Page**: http://localhost:5000/login
- **Registration Page**: http://localhost:5000/register

### 3. Test User Credentials
The system comes with pre-configured test users:
- **Username**: `testuser`, **Password**: `password123`
- **Username**: `john_doe`, **Password**: `password123`
- **Username**: `jane_smith`, **Password**: `password123`

## 🧪 Testing Instructions

### Running Tests
The project includes comprehensive test suites for both unit and integration testing:

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run specific test files
pytest tests/test_logic.py
pytest tests/test_integration.py

# Run tests with coverage report
pytest --cov=src tests/
```

### Test Categories

#### 1. Unit Tests (`test_logic.py`)
Tests individual components and business logic:
- Product pricing calculations (discounts, shipping, import duties)
- Payment validation and authorization
- Cart calculation logic
- User management functions

#### 2. Integration Tests (`test_integration.py`)
Tests complete workflows and system integration:
- User registration and authentication flow
- Cart management and checkout process
- Payment processing with database transactions
- Session management and persistence
- Stock conflict resolution

### Example Test Scenarios
```bash
# Test specific functionality
pytest tests/test_logic.py::test_get_discounted_unit_price -v
pytest tests/test_integration.py::test_cash_payment_flow -v

# Test with specific markers (if implemented)
pytest -m "not slow"  # Skip slow tests
```

## 📁 Project Structure

```
Retail-Management-System/
├── src/                    # Source code
│   ├── main.py            # Flask application and routes
│   ├── models.py          # Database models
│   └── database.py        # Database configuration
├── templates/             # HTML templates
│   ├── index.html         # Main shopping interface
│   ├── login.html         # Login page
│   ├── register.html      # Registration page
│   └── receipt.html       # Order receipt
├── static/                # Static assets
│   ├── css/              # Stylesheets
│   └── js/               # JavaScript files
├── tests/                 # Test suites
│   ├── test_logic.py     # Unit tests
│   └── test_integration.py # Integration tests
├── db/                    # Database files
│   └── init.sql          # Database initialization script
├── docs/                  # Documentation
├── requirements.txt       # Python dependencies
└── run.py                # Application entry point
```

## 🔧 Configuration

### Environment Variables
The application uses the following environment variables (configured in `.env`):

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_USERNAME` | PostgreSQL username | Required |
| `DB_PASSWORD` | PostgreSQL password | Required |
| `DB_HOST` | Database host | localhost |
| `DB_PORT` | Database port | 5432 |
| `DB_NAME` | Database name | retail_management |

### Application Settings
Key application settings in `src/main.py`:
- **Secret Key**: Used for session management
- **Debug Mode**: Enabled for development
- **Host**: 0.0.0.0 (accessible from all interfaces)
- **Port**: 5000

## 🛡️ Security Features

- **Password Hashing**: Uses Werkzeug's secure password hashing
- **Session Management**: Secure session handling with Flask
- **Input Validation**: Server-side validation for all user inputs
- **SQL Injection Protection**: Uses SQLAlchemy ORM for safe database queries
- **Payment Security**: Card number validation and secure payment processing

## 🚨 Troubleshooting

### Common Issues

#### 'psql' is not recognized (Windows)
**Error:** `'psql' is not recognized as an internal or external command`

**Solutions:**
1. **Use full path to psql:**
   ```powershell
   # Instead of: psql -U postgres
   # Use: & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres
   ```

2. **Add PostgreSQL to PATH permanently:**
   - Press `Win + R`, type `sysdm.cpl`, press Enter
   - Go to "Advanced" tab → "Environment Variables"
   - In "System Variables", find "Path" and click "Edit"
   - Click "New" and add: `C:\Program Files\PostgreSQL\17\bin`
   - Click "OK" on all dialogs
   - Restart Command Prompt/PowerShell

3. **Use pgAdmin4 instead:**
   - Create database through pgAdmin4 GUI
   - Use full path for command line operations

#### Database Connection Errors
```bash
# Check if PostgreSQL is running
sudo service postgresql status  # Linux
brew services list | grep postgres  # macOS
# Windows: Check Services.msc for "postgresql" service

# Verify database exists
psql -U your_username -l  # Linux/macOS
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -l  # Windows
```

#### Port Already in Use
```bash
# Find process using port 5000
lsof -i :5000  # macOS/Linux
netstat -ano | findstr :5000  # Windows

# Kill the process or change port in run.py
```

#### Virtual Environment Issues
```bash
# Recreate virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Getting Help
If you encounter issues:
1. Check the console output for error messages
2. Verify all environment variables are set correctly
3. Ensure PostgreSQL is running and accessible
4. Check that all dependencies are installed correctly

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

**Happy Shopping! 🛒**

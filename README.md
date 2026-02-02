# Odoo Custom Modules Collection

A comprehensive set of custom Odoo modules for managing car inventory with custom IDs, invoicing, HR portal functionality, and purchase order management.

## 📋 Table of Contents

- [Modules Overview](#modules-overview)
- [Installation](#installation)
- [Module Details](#module-details)
- [API Documentation](#api-documentation)
- [GitHub Setup](#github-setup)
- [Support](#support)

---

## 🎯 Modules Overview

### 1. **Car Custom IDs Module** (`car_custom_ids_module_FIXED`)
Manages custom IDs (like customs declarations) for car products with serial tracking through purchase and sale orders.

**Key Features:**
- Mark products as cars with mandatory serial tracking
- Create customs ID operations linked to POs and SOs
- Validate and persist customs IDs to stock lots
- Prevent duplicate customs assignments
- REST API for inventory, purchase, and sales operations

### 2. **Invoice Custom Module** (`invoice_custom`)
Extends invoice functionality with custom confirmation tracking.

**Key Features:**
- Add confirmed date field to invoices
- Track when invoices are posted
- REST API for invoice CRUD operations

### 3. **Portal HR & Time Off Module** (`portal_hr_eta`)
Employee directory and time-off management portal for portal users.

**Key Features:**
- Employee directory with search and pagination
- Time-off request creation and tracking
- Time-off approval workflow for managers
- Native supporting documents attachment
- Responsive portal interface

### 4. **Purchase Repeat Order Module** (`purchase_repeat_order`)
Simplify repeated purchase orders with one-click duplication.

**Key Features:**
- RO (Repeat Order) button for quick duplication
- Automatic sequential naming (PO-RO1, PO-RO2)
- Close/lock completed orders
- Smart buttons for order tracking

---

## 📦 Installation

### Prerequisites
- Odoo 18.0+
- PostgreSQL database
- Python 3.10+

### Step 1: Clone the Repository

```bash
cd ~/odoo/addons
git clone https://github.com/yourusername/odoo-modules.git
cd odoo-modules
```

### Step 2: Add Modules to Odoo

Copy all module folders to your Odoo addons directory:

```bash
cp -r car_custom_ids_module_FIXED /path/to/odoo/addons/
cp -r invoice_custom /path/to/odoo/addons/
cp -r portal_hr_eta /path/to/odoo/addons/
cp -r purchase_repeat_order /path/to/odoo/addons/
```

### Step 3: Update Module List

1. Open Odoo in your browser
2. Go to **Apps → Update Apps List**
3. Search for each module by name
4. Click **Install** button

### Step 4: Configure Permissions

Grant access to users in **Settings → Users & Companies → Users**

---

## 📘 Module Details

### Car Custom IDs Module

#### Database Models
- `product.template` → Added `is_car` field
- `stock.lot` → Added `custom_id` field (unique per company)
- `stock.operation.customids` → New model for customs operations
- `stock.operation.customids.line` → Lines for customs operations

#### Workflow

```
Purchase Order Created
    ↓
Goods Received (Picking Done)
    ↓
Button "Receive Customs ID" appears
    ↓
Create Customs ID Operation
    ↓
Fill Serial Numbers & Customs IDs
    ↓
Confirm Operation → Write to Stock Lots
    ↓
Now Serials Can Be Used in Sales Orders
```

#### Key Constraints
- Car products MUST have serial tracking
- Each lot can only have ONE customs ID
- Same lot cannot be used in duplicate operations
- Sale order lot selection validates customs ID exists

#### REST API Endpoints

**Inventory Management:**
```
GET    /api/v2/inventory              → List all pickings
POST   /api/v2/inventory              → Create picking
GET    /api/v2/inventory/<id>         → Get picking details
PUT    /api/v2/inventory/<id>         → Update picking moves
PATCH  /api/v2/inventory/<id>/validate → Validate picking
DELETE /api/v2/inventory/<id>         → Delete picking
OPTIONS /api/v2/inventory             → API metadata
```

**Purchase Orders:**
```
GET    /api/v2/purchases              → List all POs
POST   /api/v2/purchases              → Create PO
GET    /api/v2/purchases/<id>         → Get PO details
PUT    /api/v2/purchases/<id>         → Update PO lines
PATCH  /api/v2/purchases/<id>         → Partial PO update
DELETE /api/v2/purchases/<id>         → Delete PO
OPTIONS /api/v2/purchases             → API metadata
```

**Sales Orders:**
```
GET    /api/v2/sales                  → List all SOs
POST   /api/v2/sales                  → Create SO
GET    /api/v2/sales/<id>             → Get SO details
PUT    /api/v2/sales/<id>             → Update SO lines
PATCH  /api/v2/sales/<id>             → Partial SO update
DELETE /api/v2/sales/<id>             → Delete SO
OPTIONS /api/v2/sales                 → API metadata
```

### Invoice Custom Module

#### Added Fields
- `confirmed_by` (Date) → Tracks when invoice was confirmed/posted

#### REST API Endpoints

```
GET    /api/v2/invoices               → List all invoices
POST   /api/v2/invoices               → Create invoice
GET    /api/v2/invoices/<id>          → Get invoice details
PUT    /api/v2/invoices/<id>          → Update invoice lines
PATCH  /api/v2/invoices/<id>          → Partial invoice update
DELETE /api/v2/invoices/<id>          → Delete invoice (draft only)
OPTIONS /api/v2/invoices              → API metadata
```

### Portal HR & Time Off Module

#### Portal URLs
```
/my/employees                          → Employee directory
/my/employees/<id>                     → Employee details
/my/timeoff                            → My time-off requests
/my/timeoff/<id>                       → Time-off details
/my/timeoff/new                        → Create new request
/my/timeoff/approvals                  → Approvals (manager only)
/my/timeoff/approvals/<id>             → Approval details
```

#### REST API Endpoints

**Employees:**
```
GET    /api/v2/employees               → List all employees
POST   /api/v2/employees               → Create employee
GET    /api/v2/employees/<id>          → Get employee details
PUT    /api/v2/employees/<id>          → Update employee
PATCH  /api/v2/employees/<id>          → Partial employee update
DELETE /api/v2/employees/<id>          → Delete employee
PUT    /api/v2/employees/<id>/image    → Update employee image
DELETE /api/v2/employees/<id>/image    → Remove employee image
OPTIONS /api/v2/employees              → API metadata
```

**Time Off:**
```
GET    /api/v2/time_off                → List all time-off requests
POST   /api/v2/time_off                → Create time-off request
GET    /api/v2/time_off/<id>           → Get time-off details
PUT    /api/v2/time_off/<id>           → Update time-off
PATCH  /api/v2/time_off/<id>           → Partial time-off update
DELETE /api/v2/time_off/<id>           → Delete time-off
HEAD   /api/v2/time_off/<id>           → Check if exists
OPTIONS /api/v2/time_off               → API metadata
```

**Time Off Attachments:**
```
GET    /api/v2/time_off/<id>/attachments         → List attachments
POST   /api/v2/time_off/<id>/attachments         → Upload attachment
GET    /api/v2/time_off/<id>/attachments/<att_id> → Download attachment
DELETE /api/v2/time_off/<id>/attachments/<att_id> → Delete attachment
```

### Purchase Repeat Order Module

#### Features

**Repeat Order (RO) Button:**
- Duplicates entire PO with new sequential name
- Naming: `PO-RO1`, `PO-RO2`, etc.
- Creates in draft state for editing

**Close Button:**
- Confirms draft PO if needed
- Marks as done (final state)
- Locks RO and Close buttons

#### Menu Location
**Purchase → Orders → Repeated Orders**

---

## 🔌 API Documentation

### Authentication
All API endpoints require user authentication. Include authorization headers:

```bash
curl -u username:password http://localhost:8069/api/v2/employees
```

### Request Format

**JSON Example (POST):**
```json
{
  "partner_id": 1,
  "order_lines": [
    {
      "product_id": 5,
      "quantity": 2,
      "price_unit": 100.00
    }
  ]
}
```

### Response Format

**Success Response:**
```json
{
  "status": "success",
  "data": { ... }
}
```

**Error Response:**
```json
{
  "status": "error",
  "message": "Description of error"
}
```

### Common HTTP Status Codes
- `200` → Success
- `201` → Created
- `400` → Bad request
- `404` → Not found
- `500` → Server error

---

## 🐙 GitHub Setup

### Step 1: Create GitHub Repository

1. Go to [GitHub.com](https://github.com)
2. Click **New Repository**
3. Name: `odoo-modules` (or your preferred name)
4. Description: "Custom Odoo modules for car inventory, invoicing, HR, and purchase management"
5. Choose **Public** or **Private**
6. Click **Create Repository**

### Step 2: Initialize Git in Your Project

```bash
cd ~/odoo/addons/odoo-modules
git init
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

### Step 3: Create .gitignore

```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/

# Odoo
*.pyc
*.pyo
*.pot
.DS_Store

# IDE
.vscode/
.idea/
*.swp
*.swo

# Database
*.db
*.sqlite

# Dependencies
node_modules/
EOF
```

### Step 4: Create Initial Commit

```bash
git add .
git commit -m "Initial commit: Add 4 custom Odoo modules"
```

### Step 5: Add Remote and Push

```bash
git remote add origin https://github.com/yourusername/odoo-modules.git
git branch -M main
git push -u origin main
```

### Step 6: Verify on GitHub

Visit `https://github.com/yourusername/odoo-modules` in your browser to confirm the upload.

---

## 📝 File Structure

```
odoo-modules/
├── README.md
├── .gitignore
│
├── car_custom_ids_module_FIXED/
│   ├── __init__.py
│   ├── __manifest__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── inherit_product_template.py
│   │   ├── inherit_sale_order.py
│   │   ├── inherit_purchase_order.py
│   │   ├── inherit_stock_lot.py
│   │   └── inherit_stock_custom.py
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── inventory_api.py
│   │   ├── purchase_order_api.py
│   │   └── sale_order_api.py
│   ├── security/
│   │   └── ir.model.access.csv
│   └── views/
│       ├── inherit_product_template.xml
│       ├── inherit_purchase_order.xml
│       ├── inherit_sale_order.xml
│       └── inherit_stock_custom.xml
│
├── invoice_custom/
│   ├── __init__.py
│   ├── __manifest__.py
│   ├── models/
│   ├── controllers/
│   ├── security/
│   └── views/
│
├── portal_hr_eta/
│   ├── __init__.py
│   ├── __manifest__.py
│   ├── models/
│   ├── controllers/
│   ├── security/
│   └── views/
│
└── purchase_repeat_order/
    ├── __init__.py
    ├── __manifest__.py
    ├── models/
    ├── security/
    └── views/
```

---

## 🚀 Common Tasks

### Update All Modules on GitHub

```bash
cd ~/odoo/addons/odoo-modules
git add .
git commit -m "Update: [brief description of changes]"
git push origin main
```

### Clone Repository to Another Machine

```bash
git clone https://github.com/yourusername/odoo-modules.git
cd odoo-modules
# Copy to Odoo addons folder and install
```

### View Commit History

```bash
git log --oneline
```

### Rollback to Previous Commit

```bash
git revert <commit-hash>
git push origin main
```

---

## 🔒 Security Notes

- **Never commit secrets** (API keys, passwords) to GitHub
- Use `.gitignore` to exclude sensitive files
- For production, use environment variables for configuration
- Review access control CSV files for permission appropriateness

---

## 📞 Support

For issues or questions:

1. Check existing [GitHub Issues](https://github.com/yourusername/odoo-modules/issues)
2. Create new issue with:
   - Module name
   - Error message
   - Steps to reproduce
   - Odoo version used

3. Submit pull requests with improvements

---

## 📄 License

Specify your license here (e.g., MIT, AGPL-3.0, Proprietary)

---

## 👨‍💻 Author

**Yusuf Khan**
- Email: yusufyt287@gmail.com
- GitHub: [@Yusufi8](https://github.com/Yusufi8)

---

## 📚 Additional Resources

- [Odoo Documentation](https://www.odoo.com/documentation/)
- [Odoo Development Guide](https://www.odoo.com/documentation/18.0/developer/)
- [Git Documentation](https://git-scm.com/doc)
- [GitHub Guides](https://guides.github.com/)

---

**Last Updated:** February 2, 2026
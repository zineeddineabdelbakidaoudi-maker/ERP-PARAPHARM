# ParaFarm ERP — Security, Roles, Performance, Backup

---

# 13. ROLE & PERMISSION SYSTEM

## Roles

### ADMIN (Administrateur)
Full system access. User management, settings, backup/restore, debt write-off, void any transaction, all financial data, system configuration.

### CAISSIER (Cashier)
| Module | Allowed |
|---|---|
| POS | Create sale, payment, receipt, discount ≤ 10%, hold/recall, view own sales |
| Products | View only (no edit, no cost price visible) |
| Clients | View, quick-add from POS |
| Caisse | Open session, record expense, close session |
| **Blocked** | Void sales, reports, cost prices, stock adjustment, settings |

### GESTIONNAIRE STOCK (Inventory Manager)
| Module | Allowed |
|---|---|
| Products | Full CRUD |
| Categories | Full CRUD |
| Stock | View, adjust, reconcile |
| Purchases | Create PO, receive goods |
| Labels | Print |
| Expiration | View, dispose |
| **Blocked** | POS, financial reports, debt management |

### COMPTABLE (Accountant)
| Module | Allowed |
|---|---|
| Reports | All financial reports |
| Debts | View all, record payments, generate statements |
| Caisse | View all sessions, closure reports |
| Expenses | View, create |
| Purchases | Record invoices, make payments |
| **Blocked** | POS, stock adjustments |

### LIVREUR (Delivery Operator)
| Module | Allowed |
|---|---|
| Deliveries | View assigned, update status |
| Clients | View addresses only |
| **Blocked** | Everything else, no financial data |

### SUPERVISEUR
All cashier permissions PLUS: void sales (same day), discount ≤ 50%, PIN override for cashier limits, sales reports, force-close sessions.

## Permission Enforcement

```python
def require_permission(module: str, action: str):
    """Decorator for service methods."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = get_current_session().user
            if not user:
                raise AuthenticationError("Non authentifié")
            perm = Permission.query.filter_by(
                role_id=user.role_id, module=module,
                action=action, is_allowed=True
            ).first()
            if not perm:
                raise PermissionError(f"Accès refusé: {module}.{action}")
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

## Supervisor PIN Override

```python
def request_supervisor_override(action_desc: str) -> bool:
    pin = show_pin_dialog(f"Autorisation requise: {action_desc}")
    if not pin:
        return False
    supervisor = User.query.filter(
        User.pin_code == hash_pin(pin),
        User.role.has(Role.name.in_(['ADMIN', 'SUPERVISEUR'])),
        User.is_active == True
    ).first()
    if supervisor:
        log_audit('OVERRIDE', action_desc, supervisor.id)
        return True
    return False
```

---

# 14. SEARCH & FILTER SYSTEM

**Global Search (Ctrl+K)**: Searches Products (name/code/barcode), Clients (name/phone/code), Suppliers, Sales (number), Purchases. Results grouped by type. Click → navigate.

**POS Search**: Auto-focus barcode field. Barcode=exact match. Text(≥2)=LIKE name/code. 300ms debounce. Max 20 results.

**Table Filters**: Column-specific (dropdown for enums, text for strings, date range for dates). Combined AND. Sort ASC/DESC. Column visibility toggle.

**Pagination**: Default 50 rows. Options: 25/50/100/200. Offset-based (SQLite LIMIT/OFFSET).

**Query Optimization**: All FK/search/date columns indexed. `joinedload()` for eager loading. Soft-delete filter always applied.

---

# 15. DASHBOARD & ANALYTICS

| Widget | Query | Refresh |
|---|---|---|
| Revenu Aujourd'hui | SUM(sales.total_amount) WHERE date=TODAY AND status='COMPLETED' | On page focus |
| Nombre de Ventes | COUNT(sales) WHERE date=TODAY | On page focus |
| Alertes Stock | COUNT(stock) WHERE qty ≤ min_level | On page focus |
| Dettes en Cours | SUM(debts.remaining) WHERE entity_type='CLIENT' AND status IN ('PENDING','PARTIAL') | On page focus |
| Solde Caisse | cash_register.expected_balance WHERE status='OPEN' | On page focus |
| Livraisons en Attente | COUNT(deliveries) WHERE status='PENDING' | On page focus |
| Tendance Revenu | Last 7/30 days daily totals | On date change |
| Top Produits | Top 10 by qty this month | Monthly |
| Ventes Récentes | Last 10 sales | On new sale event |
| Alertes | Active notifications by priority | On page focus |

Charts: matplotlib → QPixmap for Qt embedding.

---

# 17. PERFORMANCE & STABILITY

## SQLite Optimization

```python
PRAGMA journal_mode=WAL;        # Write-Ahead Logging
PRAGMA synchronous=NORMAL;      # Balance safety/speed
PRAGMA foreign_keys=ON;
PRAGMA cache_size=-8000;        # 8MB page cache
PRAGMA busy_timeout=5000;       # 5s retry on lock
PRAGMA temp_store=MEMORY;       # Temp tables in RAM
PRAGMA mmap_size=268435456;     # 256MB memory-mapped I/O
```

## Application Performance

| Strategy | Detail |
|---|---|
| Lazy page loading | Pages created on first navigation, not startup |
| QSS caching | Stylesheet parsed once at startup |
| Image thumbnails | Product images resized and cached |
| Background work | Prints, reports, backups on QThreadPool (max 3 workers) |
| Debounced search | 300ms after last keystroke |
| Batch DB ops | Bulk inserts for imports |
| Memory cleanup | Dispose report DataFrames after export |
| Startup speed | Minimal imports; lazy-load heavy modules (matplotlib, ReportLab) |

## Threading

```
Main Thread: UI only (all Qt widgets)
QThreadPool(3): PrintJob, ReportJob, BackupJob
QTimer: Notification check (60s), expiration check (startup + hourly)
```

**Thread safety**: Scoped SQLAlchemy sessions per thread. UI updates via Qt signals only.

---

# 18. SECURITY

## Local Authentication

```python
import bcrypt

class AuthService:
    MAX_ATTEMPTS = 5
    LOCKOUT_SECONDS = 300
    
    def authenticate(self, username, password):
        user = self.user_repo.get_by_username(username)
        if not user or not user.is_active:
            raise AuthenticationError("Identifiants invalides")
        
        # Lockout check
        if user.failed_attempts >= self.MAX_ATTEMPTS:
            elapsed = (datetime.now() - user.last_failed_at).total_seconds()
            if elapsed < self.LOCKOUT_SECONDS:
                raise AuthenticationError(f"Compte verrouillé ({int(self.LOCKOUT_SECONDS - elapsed)}s)")
            user.failed_attempts = 0
        
        if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            user.failed_attempts += 1
            user.last_failed_at = datetime.now().isoformat()
            self.session.commit()
            raise AuthenticationError("Identifiants invalides")
        
        # Success
        user.failed_attempts = 0
        user.last_login = datetime.now().isoformat()
        self.session.commit()
        self._create_local_session(user)
        self.audit_service.log('LOGIN', 'AUTH', user_id=user.id)
        return user
    
    def hash_password(self, password):
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
```

## Session Management

- In-memory session object: `{user_id, role, permissions[], login_time}`
- No JWT, no tokens, no network
- Auto-logout after configurable inactivity (default: 30 min)
- Session destroyed on app close

## Data Protection

- Passwords: bcrypt hashed (never plaintext)
- PINs: hashed
- No sensitive data in log files
- Audit logs append-only (no DELETE permission)
- Backup encryption: AES-256 with user key (optional)

---

# 19. BACKUP & RESTORE

```python
class BackupService:
    def create_backup(self, db_path, backup_dir, encrypt=False, key=None):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"parafarm_{timestamp}.bak"
        backup_path = os.path.join(backup_dir, backup_name)
        
        # 1. SQLite online backup API (safe during WAL)
        shutil.copy2(db_path, backup_path)
        
        # 2. Checksum
        checksum = hashlib.sha256(open(backup_path, 'rb').read()).hexdigest()
        
        # 3. Optional encryption
        if encrypt and key:
            self._encrypt_file(backup_path, key)
        
        # 4. Manifest
        manifest = {'timestamp': timestamp, 'checksum': checksum,
                     'encrypted': encrypt, 'version': APP_VERSION}
        
        # 5. Retention: keep last N (default 30)
        self._cleanup_old(backup_dir, keep=30)
        
        return backup_path
    
    def restore(self, backup_path, target_db_path):
        # 1. Verify checksum
        # 2. Decrypt if needed
        # 3. Backup current DB first (safety net)
        # 4. Replace DB file
        # 5. Run pending Alembic migrations
```

**Schedule**: Auto-backup on app close (default ON). Manual one-click backup. Backup to local dir or USB drive. Keep last 30 backups.

**Restore**: Admin only. Verify integrity → confirm dialog ("Toutes les données actuelles seront remplacées") → backup current → restore → restart app.

**Corruption handling**: If DB fails to open → prompt restore from latest backup.

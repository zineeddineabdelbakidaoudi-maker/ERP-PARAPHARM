"""
ParaFarm ERP — Big Data Seeder Script
Seeds 50+ products, 10 clients with NIF/phone/address, 5 suppliers,
60+ sales, 20+ purchase orders, 20+ deliveries, and realistic debt history.
"""
from datetime import datetime, timedelta
import random
import os
import sys

sys.path.append(os.getcwd())

# Force UTF-8 output on Windows to handle emoji in print statements
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from app.core.database import get_session, init_db
from app.config import config
from app.models.user import User
from app.models.product import Category, Product, Barcode
from app.models.stock import Stock, StockBatch, StockMovement
from app.models.supplier import Supplier
from app.models.client import Client
from app.models.sale import Sale, SaleItem
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.purchase import Purchase, PurchaseItem
from app.models.debt import Debt
from app.constants import MovementType, PaymentMethod


def seed_data():
    config.load()
    session = get_session()

    admin = session.query(User).filter(User.username == "admin").first()
    if not admin:
        print("Erreur: Utilisateur admin introuvable. Lancez d'abord l'application.")
        return

    print("🚀 Début du peuplement de la base de données avec des données massives...")

    # ── 1. Clear existing data ────────────────────────────────────────
    print("🧹 Nettoyage des anciennes données...")
    from sqlalchemy import text, MetaData
    
    # Disable foreign keys temporarily
    session.execute(text("PRAGMA foreign_keys = OFF"))
    
    metadata = MetaData()
    metadata.reflect(bind=session.bind)
    
    # Exclude user authentication and settings tables
    exclude_tables = {"users", "roles", "permissions", "user_roles", "role_permissions", "settings"}
    
    for table_name in metadata.tables:
        if table_name not in exclude_tables:
            session.execute(text(f"DELETE FROM `{table_name}`"))
            # Reset sqlite sequence if table uses autoincrement
            try:
                session.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'"))
            except Exception:
                pass
                
    session.commit()
    # Re-enable foreign keys
    session.execute(text("PRAGMA foreign_keys = ON"))


    # ── 2. Categories ─────────────────────────────────────────────────
    print("📦 Création des catégories...")
    cats_data = [
        "Analgésiques & Antipyrétiques",
        "Antibiotiques",
        "Anti-inflammatoires",
        "Cardiovasculaire",
        "Vitamines & Suppléments",
        "Parapharmacie",
        "Soins & Cosmétiques",
        "Gastro-Entérologie",
        "Pneumologie & Voies Respiratoires",
    ]
    categories = []
    for i, name in enumerate(cats_data, 1):
        cat = Category(name=name, sort_order=i, is_active=1)
        session.add(cat)
        categories.append(cat)
    session.commit()
    cat_by_name = {c.name: c for c in categories}

    # ── 3. Suppliers ──────────────────────────────────────────────────
    print("🏭 Création des fournisseurs avec NIF/Adresse/Téléphone...")
    suppliers_data = [
        {
            "code": "FRS-00001", "name": "Pharmacie Centrale des Hôpitaux (PCH)",
            "category": "PHARMACEUTIQUE", "phone": "021 65 43 21",
            "email": "pch@pch.dz", "address": "Route de Bab Ezzouar, Alger",
            "tax_id": "099612345670019",
        },
        {
            "code": "FRS-00002", "name": "Biopharm Distribution",
            "category": "PHARMACEUTIQUE", "phone": "023 45 67 89",
            "email": "contact@biopharm.dz", "address": "Zone Industrielle, Dar El Beida, Alger",
            "tax_id": "099698765430027",
        },
        {
            "code": "FRS-00003", "name": "Saidal Groupe",
            "category": "PHARMACEUTIQUE", "phone": "021 54 32 10",
            "email": "saidal@saidal.dz", "address": "Route de Baraki, Hussein Dey, Alger",
            "tax_id": "099611223340018",
        },
        {
            "code": "FRS-00004", "name": "Pfizer Algérie SARL",
            "category": "PHARMACEUTIQUE", "phone": "023 89 01 23",
            "email": "algeria@pfizer.com", "address": "Lot 23, Sidi Yahia, Hydra, Alger",
            "tax_id": "099644556670025",
        },
        {
            "code": "FRS-00005", "name": "Hikma Pharma Algérie",
            "category": "PHARMACEUTIQUE", "phone": "025 30 12 34",
            "email": "hikma@hikma.dz", "address": "Zone d'Activité Bouchaoui, Blida",
            "tax_id": "009977889900016",
        },
    ]
    suppliers = []
    for s_data in suppliers_data:
        sup = Supplier(
            code=s_data["code"], name=s_data["name"],
            category=s_data["category"], phone=s_data["phone"],
            email=s_data["email"], address=s_data["address"],
            tax_id=s_data["tax_id"], is_active=1,
            credit_period_days=30, credit_limit=500000.0
        )
        session.add(sup)
        suppliers.append(sup)
    session.commit()

    # ── 4. Clients ────────────────────────────────────────────────────
    print("👥 Création des clients avec NIF/Adresse/Téléphone...")
    clients_data = [
        {
            "code": "CLT-00001", "name": "Pharmacie El Amel", "client_type": "ENTREPRISE",
            "phone": "021 30 45 67", "email": "elamel@gmail.com",
            "address": "12 Rue Hassiba Ben Bouali, Alger-Centre", "credit_limit": 150000.0,
            "tax_id": "099601234560011",
        },
        {
            "code": "CLT-00002", "name": "Clinique Privée Essaada",
            "client_type": "ENTREPRISE",
            "phone": "021 76 54 32", "email": "essaada@clinique.dz",
            "address": "45 Chemin Doudou Mokhtar, Ben Aknoun, Alger", "credit_limit": 300000.0,
            "tax_id": "099609876540028",
        },
        {
            "code": "CLT-00003", "name": "Pharmacie Ibn Sina",
            "client_type": "ENTREPRISE",
            "phone": "023 12 34 56", "email": "ibnsina@pharma.dz",
            "address": "7 Boulevard Colonel Amirouche, Tizi-Ouzou", "credit_limit": 80000.0,
            "tax_id": "099615432100014",
        },
        {
            "code": "CLT-00004", "name": "Hôpital Mustapha Pacha",
            "client_type": "ENTREPRISE",
            "phone": "021 23 11 00", "email": "mustapha@sante.dz",
            "address": "Place du 1er Mai, Alger-Centre", "credit_limit": 500000.0,
            "tax_id": "000001234000001",
        },
        {
            "code": "CLT-00005", "name": "Salim Belkacem",
            "client_type": "PARTICULIER",
            "phone": "0550 12 34 56", "email": "salim@gmail.com",
            "address": "Cité Les Bananiers, Hydra, Alger", "credit_limit": 20000.0,
            "tax_id": None,
        },
        {
            "code": "CLT-00006", "name": "Amina Mansouri",
            "client_type": "PARTICULIER",
            "phone": "0661 98 76 54", "email": "amina.m@outlook.com",
            "address": "Rue Belouizdad, Kouba, Alger", "credit_limit": 15000.0,
            "tax_id": None,
        },
        {
            "code": "CLT-00007", "name": "Pharmacie Al Baraka",
            "client_type": "ENTREPRISE",
            "phone": "038 45 67 89", "email": "albaraka@pharma.dz",
            "address": "22 Avenue de l'ALN, Blida", "credit_limit": 120000.0,
            "tax_id": "099632109870022",
        },
        {
            "code": "CLT-00008", "name": "Centre de Santé Bab El Oued",
            "client_type": "ENTREPRISE",
            "phone": "021 45 78 90", "email": "cs-beo@sante.gov.dz",
            "address": "Rue Larbi Ben M'hidi, Bab El Oued, Alger", "credit_limit": 200000.0,
            "tax_id": "000008765000002",
        },
        {
            "code": "CLT-00009", "name": "Pharmacie Nouvelle",
            "client_type": "ENTREPRISE",
            "phone": "031 22 33 44", "email": "nouvelle@pharma.dz",
            "address": "Boulevard de la République, Oran", "credit_limit": 90000.0,
            "tax_id": "099678901230033",
        },
        {
            "code": "CLT-00010", "name": "Farid Haddad",
            "client_type": "PARTICULIER",
            "phone": "0770 45 67 89", "email": "farid.h@yahoo.fr",
            "address": "Résidence Les Pins, Bab Ezzouar, Alger", "credit_limit": 10000.0,
            "tax_id": None,
        },
    ]
    clients = []
    for cl_data in clients_data:
        client = Client(
            code=cl_data["code"], name=cl_data["name"],
            client_type=cl_data["client_type"],
            phone=cl_data["phone"], email=cl_data["email"],
            address=cl_data["address"], credit_limit=cl_data["credit_limit"],
            tax_id=cl_data["tax_id"], is_active=1
        )
        session.add(client)
        clients.append(client)
    session.commit()

    # ── 5. Products (50+) ─────────────────────────────────────────────
    print("💊 Création de 50+ produits pharmaceutiques réalistes...")
    products_def = [
        # Analgésiques
        ("Doliprane 500mg Gélules 16cp",         "Analgésiques & Antipyrétiques", 120.0, 180.0, "6131110000018"),
        ("Doliprane 1g Comprimés 8cp",            "Analgésiques & Antipyrétiques", 180.0, 260.0, "6131110000025"),
        ("Efferalgan 500mg Effervescent 16cp",    "Analgésiques & Antipyrétiques", 140.0, 210.0, "6131110000032"),
        ("Efferalgan 1g Comprimés 8cp",           "Analgésiques & Antipyrétiques", 190.0, 280.0, "6131110000049"),
        ("Aspégic 100mg Nourrissons Sachets",     "Analgésiques & Antipyrétiques",  90.0, 130.0, "6131110000056"),
        ("Aspégic 500mg Adultes Sachets",         "Analgésiques & Antipyrétiques", 130.0, 195.0, "6131110000063"),
        ("Kardegic 75mg Sachets 30cp",            "Analgésiques & Antipyrétiques", 150.0, 220.0, "6131110000070"),
        ("Spasfon Lyoc 80mg 15 lyophilisats",     "Analgésiques & Antipyrétiques", 240.0, 350.0, "6131110000087"),
        # Antibiotiques
        ("Clamoxyl 1g Comprimés Boite 14",        "Antibiotiques", 450.0,  680.0, "6132220000017"),
        ("Augmentin 1g Adulte Boite 14",          "Antibiotiques", 820.0, 1150.0, "6132220000024"),
        ("Oroken 200mg Capsules Boite 6",         "Antibiotiques", 750.0, 1020.0, "6132220000031"),
        ("Zinnat 500mg Comprimés Boite 10",       "Antibiotiques", 680.0,  950.0, "6132220000048"),
        ("Zeclar 500mg Comprimés Boite 14",       "Antibiotiques", 900.0, 1280.0, "6132220000055"),
        ("Orelox 100mg Comprimés Boite 10",       "Antibiotiques", 620.0,  880.0, "6132220000062"),
        # Anti-inflammatoires
        ("Profenid 100mg Gélules Boite 14",       "Anti-inflammatoires", 280.0, 420.0, "6133330000016"),
        ("Voltarene 50mg Comprimés Boite 20",     "Anti-inflammatoires", 310.0, 450.0, "6133330000023"),
        ("Ibuprofène 400mg Comprimés Boite 20",   "Anti-inflammatoires", 190.0, 280.0, "6133330000030"),
        ("Cortancyl 5mg Comprimés Boite 30",      "Anti-inflammatoires", 320.0, 460.0, "6133330000047"),
        # Cardiovasculaire
        ("Aprovel 150mg Comprimés Boite 28",      "Cardiovasculaire",  600.0,  850.0, "6134440000015"),
        ("Co-Aprovel 150/12.5mg Boite 28",        "Cardiovasculaire",  750.0, 1050.0, "6134440000022"),
        ("Tahor 20mg Comprimés Boite 30",         "Cardiovasculaire", 1100.0, 1550.0, "6134440000039"),
        ("Crestor 10mg Comprimés Boite 28",       "Cardiovasculaire", 1300.0, 1850.0, "6134440000046"),
        ("Coversyl 5mg Comprimés Boite 30",       "Cardiovasculaire",  680.0,  950.0, "6134440000053"),
        ("Lasilix 40mg Comprimés Boite 30",       "Cardiovasculaire",  180.0,  260.0, "6134440000060"),
        ("Plavix 75mg Comprimés Boite 28",        "Cardiovasculaire", 1450.0, 2100.0, "6134440000077"),
        # Vitamines
        ("Supradyn Intensia Boite 30cp",          "Vitamines & Suppléments",  850.0, 1200.0, "6135550000014"),
        ("Bion 3 Adultes Comprimés Boite 30",     "Vitamines & Suppléments", 1100.0, 1600.0, "6135550000021"),
        ("Alvityl Vitalité Sirop 150ml",          "Vitamines & Suppléments",  450.0,  650.0, "6135550000038"),
        ("Magné B6 Ampoules Boite 20",            "Vitamines & Suppléments",  380.0,  550.0, "6135550000045"),
        ("Zinc 15mg Oligo-élément Boite 30",      "Vitamines & Suppléments",  240.0,  350.0, "6135550000052"),
        ("Vitamine D3 1000UI Boite 30",           "Vitamines & Suppléments",  290.0,  420.0, "6135550000069"),
        ("Vitamine C 1g Effervescent Boite 20",   "Vitamines & Suppléments",  200.0,  290.0, "6135550000076"),
        # Parapharmacie
        ("Bétadine Dermique Flacon 125ml",        "Parapharmacie",  260.0,  380.0, "6136660000013"),
        ("Biafine Émulsion Tube 93g",             "Parapharmacie",  340.0,  490.0, "6136660000020"),
        ("Dexeryl Crème Flacon 250g",             "Parapharmacie",  680.0,  980.0, "6136660000037"),
        ("Compresse Stérile 7.5x7.5 Boite 50",   "Parapharmacie",  120.0,  180.0, "6136660000051"),
        ("Sparadrap Chirurgical 2,5cm x 5m",      "Parapharmacie",   90.0,  135.0, "6136660000068"),
        ("Tensiomètre Bras Electronique Omron",   "Parapharmacie", 4800.0, 6900.0, "6136660000075"),
        ("Thermomètre Infrarouge Frontal",        "Parapharmacie", 1800.0, 2600.0, "6136660000082"),
        ("Lecteur Glycémie Accu-Check",           "Parapharmacie", 2200.0, 3200.0, "6136660000099"),
        # Soins & Cosmétiques
        ("Mustela Gel Lavant Bébé 500ml",         "Soins & Cosmétiques", 1450.0, 2100.0, "6137770000012"),
        ("La Roche-Posay Cicaplast Baume B5",     "Soins & Cosmétiques", 1100.0, 1550.0, "6137770000029"),
        ("Vichy Minéral 89 Sérum 50ml",           "Soins & Cosmétiques", 2900.0, 3900.0, "6137770000036"),
        ("Bioderma Sensibio H2O 500ml",           "Soins & Cosmétiques", 1200.0, 1750.0, "6137770000043"),
        ("Eau Thermale Avène Spray 300ml",        "Soins & Cosmétiques",  850.0, 1250.0, "6137770000050"),
        ("Isdin Photoprotector SPF50+ 200ml",     "Soins & Cosmétiques", 2100.0, 2950.0, "6137770000067"),
        ("CeraVe Baume Hydratant Pot 454g",       "Soins & Cosmétiques", 2400.0, 3400.0, "6137770000074"),
        # Gastro-Entérologie
        ("Mopral 20mg Gélules Boite 28",          "Gastro-Entérologie",  350.0,  520.0, "6138880000011"),
        ("Inexium 40mg Comprimés Boite 28",       "Gastro-Entérologie",  720.0,  990.0, "6138880000028"),
        ("Gaviscon Suspension Buvable 200ml",     "Gastro-Entérologie",  300.0,  440.0, "6138880000035"),
        ("Maalox Citron Sans Sucre Boite 40",     "Gastro-Entérologie",  220.0,  320.0, "6138880000042"),
        ("Smecta 3g Boite 30 Sachets",            "Gastro-Entérologie",  180.0,  260.0, "6138880000059"),
        # Pneumologie
        ("Ventoline Spray 100mcg/dose 200d",      "Pneumologie & Voies Respiratoires", 380.0, 540.0, "6139990000010"),
        ("Bécotide 250mcg Spray 200 doses",       "Pneumologie & Voies Respiratoires", 520.0, 750.0, "6139990000027"),
        ("Aerius 5mg Comprimés Boite 30",         "Pneumologie & Voies Respiratoires", 480.0, 680.0, "6139990000034"),
        ("Clarityne 10mg Comprimés Boite 30",     "Pneumologie & Voies Respiratoires", 410.0, 580.0, "6139990000041"),
        ("Solupred 20mg Comprimés Boite 20",      "Pneumologie & Voies Respiratoires", 250.0, 370.0, "6139990000058"),
    ]

    products = []
    now = datetime.now()
    for idx, (name, cat_name, cost, sell, barcode) in enumerate(products_def):
        cat  = cat_by_name[cat_name]
        code = f"PRD-{idx+1:05d}"
        prod = Product(
            code=code, barcode=barcode, name=name,
            description=f"Produit officinal : {name}",
            category_id=cat.id,
            cost_price=cost, selling_price=sell,
            tax_rate=19.0 if "Cosmétiques" in cat_name else 9.0,
            min_stock_level=random.choice([10, 15, 20]),
            unit="Boite", created_by=admin.id, is_active=1
        )
        session.add(prod)
        session.flush()

        session.add(Barcode(product_id=prod.id, barcode_value=barcode, is_primary=1))

        qty = random.randint(50, 200)
        session.add(Stock(product_id=prod.id, quantity=qty))

        exp_soon = (now + timedelta(days=random.randint(30, 240))).strftime("%Y-%m-%d")
        exp_far  = (now + timedelta(days=random.randint(600, 1000))).strftime("%Y-%m-%d")
        qty_soon = random.randint(5, 20)
        qty_far  = qty - qty_soon
        session.add(StockBatch(
            product_id=prod.id, lot_number=f"BT-{now.strftime('%y%m')}-{prod.id:03d}A",
            expiration_date=exp_soon, quantity=qty_soon, remaining_quantity=qty_soon,
            cost_price=prod.cost_price
        ))
        session.add(StockBatch(
            product_id=prod.id, lot_number=f"BT-{now.strftime('%y%m')}-{prod.id:03d}B",
            expiration_date=exp_far, quantity=qty_far, remaining_quantity=qty_far,
            cost_price=prod.cost_price
        ))
        session.add(StockMovement(
            product_id=prod.id,
            movement_type=MovementType.ADJUSTMENT.value,
            quantity=qty, user_id=admin.id,
            notes="Stock initial — Seeding"
        ))
        products.append(prod)

    session.commit()
    print(f"✅ {len(products)} produits insérés !")

    # ── 6. Purchase Orders (25) ───────────────────────────────────────
    print("📦 Création de 25 bons de commande fournisseur...")
    for i in range(25):
        supplier = random.choice(suppliers)
        days_ago = random.randint(1, 90)
        po_date  = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
        status   = "COMPLETED" if i < 20 else random.choice(["VALIDATED", "DRAFT"])
        po = PurchaseOrder(
            order_number=f"CMD-{now.strftime('%Y')}-{i+1:04d}",
            supplier_id=supplier.id, created_by=admin.id,
            created_at=po_date, status=status, total_amount=0.0,
            notes="Commande automatique (seeder)"
        )
        session.add(po)
        session.flush()
        total = 0.0
        for p in random.sample(products, random.randint(4, 8)):
            qty   = random.randint(10, 60)
            price = p.cost_price
            lt    = qty * price
            total += lt
            session.add(PurchaseOrderItem(
                purchase_order_id=po.id, product_id=p.id,
                quantity=qty, unit_price=price, line_total=lt
            ))
        po.total_amount = total
    session.commit()
    print("✅ Bons de commande fournisseur insérés !")

    # ── 7. Sales (70) — with debt history ────────────────────────────
    print("📈 Création de 70 ventes avec historique de dettes...")
    pay_methods = [PaymentMethod.ESPECES.value, PaymentMethod.CARTE.value, PaymentMethod.CREDIT.value]

    for i in range(70):
        client      = random.choice(clients) if random.random() > 0.3 else None
        days_ago    = random.randint(0, 120)
        sale_date   = now - timedelta(days=days_ago, hours=random.randint(0, 8),
                                       minutes=random.randint(0, 59))
        sale_date_s = sale_date.strftime("%Y-%m-%d %H:%M:%S")
        sale_num    = f"VNT-{sale_date.strftime('%Y%m%d')}-{i+1:04d}"

        pay_method = random.choice(pay_methods)
        if not client and pay_method == PaymentMethod.CREDIT.value:
            pay_method = PaymentMethod.ESPECES.value

        sale = Sale(
            sale_number=sale_num,
            client_id=client.id if client else None,
            cashier_id=admin.id,
            sale_date=sale_date_s,
            subtotal=0.0, discount_amount=0.0,
            discount_type=None, discount_value=0.0,
            tax_total=0.0, total_amount=0.0,
            paid_amount=0.0, change_amount=0.0,
            payment_method=pay_method,
            status="COMPLETED", created_at=sale_date_s
        )
        session.add(sale)
        session.flush()

        subtotal = 0.0
        tax_total = 0.0
        for p in random.sample(products, random.randint(2, 6)):
            qty       = random.randint(1, 8)
            price     = p.selling_price
            cost      = p.cost_price
            line_ht   = qty * price
            line_tax  = line_ht * (p.tax_rate / 100.0)
            line_ttc  = line_ht + line_tax
            subtotal  += line_ht
            tax_total += line_tax
            session.add(SaleItem(
                sale_id=sale.id, product_id=p.id,
                quantity=qty, unit_price=price, cost_price=cost,
                discount_amount=0.0, tax_rate=p.tax_rate,
                tax_amount=line_tax, line_total=line_ttc
            ))

        total_ttc        = subtotal + tax_total
        sale.subtotal    = subtotal
        sale.tax_total   = tax_total
        sale.total_amount= total_ttc

        if pay_method == PaymentMethod.CREDIT.value and client:
            # Random partial payment (0%, 25%, 50%, 75%)
            paid_frac     = random.choice([0.0, 0.25, 0.5, 0.75])
            paid          = round(total_ttc * paid_frac, 2)
            sale.paid_amount = paid
            remaining     = round(total_ttc - paid, 2)
            debt_status   = "PAID" if remaining <= 0 else ("PARTIAL" if paid > 0 else "PENDING")
            session.add(Debt(
                entity_type="CLIENT", entity_id=client.id,
                reference_type="SALE", reference_id=sale.id,
                total_amount=total_ttc, paid_amount=paid,
                remaining_amount=remaining, status=debt_status
            ))
        else:
            sale.paid_amount = total_ttc

    session.commit()
    print("✅ 70 ventes et dettes insérées !")

    # ── 8. Cash register session ──────────────────────────────────────
    print("🏦 Session de caisse active...")
    try:
        from app.models.cash_register import CashRegister
        session.query(CashRegister).delete()
        session.commit()
        session.add(CashRegister(
            session_date=now.strftime("%Y-%m-%d"),
            opened_by=admin.id, opening_balance=15000.0,
            total_sales_cash=0.0, total_sales_card=0.0,
            total_expenses=0.0, total_withdrawals=0.0,
            total_deposits=0.0, expected_balance=15000.0,
            status="OPEN",
            opened_at=now.strftime("%Y-%m-%d %H:%M:%S")
        ))
        session.commit()
        print("✅ Session de caisse ouverte !")
    except Exception as e:
        print(f"⚠️  Session de caisse ignorée : {e}")

    print("\n🎉 SEEDING COMPLET ! Base de données chargée avec :")
    print(f"   • {len(categories)} catégories")
    print(f"   • {len(suppliers)} fournisseurs (avec NIF, téléphone, adresse)")
    print(f"   • {len(clients)} clients (avec NIF, téléphone, adresse)")
    print(f"   • {len(products)} produits")
    print(f"   • 25 bons de commande fournisseur")
    print(f"   • 70 ventes avec historique de dettes")


if __name__ == "__main__":
    seed_data()

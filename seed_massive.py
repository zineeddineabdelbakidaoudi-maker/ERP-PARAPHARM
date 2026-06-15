"""
ParaFarm ERP — Massive Data Seeder
Seeds hundreds of realistic records for testing all modules.
Run: python seed_massive.py
"""
import sys
import os
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.getcwd())

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.config import config
config.load()

from app.core.database import get_session, init_db
from app.models.user import User
from app.models.product import Category, Product, Barcode
from app.models.stock import Stock, StockBatch, StockMovement
from app.models.supplier import Supplier
from app.models.client import Client
from app.models.sale import Sale, SaleItem
from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.purchase import Purchase, PurchaseItem
from app.models.delivery import Delivery, DeliveryItem
from app.models.invoice import Invoice, InvoiceItem
from app.models.customer_order import CustomerOrder, CustomerOrderItem
from app.models.debt import Debt, Payment
from app.models.credit_note import CreditNote, CreditNoteItem
from app.models.cash_register import CashRegister
from app.constants import MovementType, PaymentMethod

from sqlalchemy import text, MetaData

NOW = datetime.now()
random.seed(42)


def rdate(days_back_min=0, days_back_max=365):
    delta = random.randint(days_back_min, days_back_max)
    return (NOW - timedelta(days=delta, hours=random.randint(0, 10),
                            minutes=random.randint(0, 59)))


def ds(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def money_rnd(low, high):
    return round(random.uniform(low, high), 2)


def main():
    session = get_session()

    admin = session.query(User).filter(User.username == "admin").first()
    if not admin:
        print("ERROR: admin user not found. Launch the app first.")
        return

    print("=== ParaFarm ERP — Massive Data Seeder ===")
    print("Nettoyage des anciennes donnees...")

    session.execute(text("PRAGMA foreign_keys = OFF"))
    meta = MetaData()
    meta.reflect(bind=session.bind)
    exclude = {"users", "roles", "permissions", "user_roles", "role_permissions", "settings"}
    for tbl in meta.tables:
        if tbl not in exclude:
            session.execute(text(f"DELETE FROM `{tbl}`"))
            try:
                session.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{tbl}'"))
            except Exception:
                pass
    session.commit()
    session.execute(text("PRAGMA foreign_keys = ON"))

    # ── 1. CATEGORIES (12) ──────────────────────────────────────────────
    print("Creation des categories...")
    cats_data = [
        "Analgesiques & Antipyretiques",
        "Antibiotiques",
        "Anti-inflammatoires",
        "Cardiovasculaire",
        "Vitamines & Supplements",
        "Parapharmacie",
        "Soins & Cosmetiques",
        "Gastro-Enterologie",
        "Pneumologie & Voies Respiratoires",
        "Diabetologie & Endocrinologie",
        "Neurologie & Psychiatrie",
        "Dermatologie",
    ]
    categories = []
    for i, name in enumerate(cats_data, 1):
        cat = Category(name=name, sort_order=i, is_active=1)
        session.add(cat)
        categories.append(cat)
    session.commit()
    cat_by_name = {c.name: c for c in categories}
    print(f"  -> {len(categories)} categories")

    # ── 2. SUPPLIERS (12) ────────────────────────────────────────────────
    print("Creation des fournisseurs...")
    suppliers_data = [
        {"code": "FRS-001", "name": "Pharmacie Centrale des Hopitaux (PCH)", "cat": "PHARMACEUTIQUE", "phone": "021 65 43 21", "email": "pch@pch.dz", "address": "Route Bab Ezzouar, Alger", "tax_id": "099612345670019"},
        {"code": "FRS-002", "name": "Biopharm Distribution", "cat": "PHARMACEUTIQUE", "phone": "023 45 67 89", "email": "contact@biopharm.dz", "address": "Zone Industrielle, Dar El Beida, Alger", "tax_id": "099698765430027"},
        {"code": "FRS-003", "name": "Saidal Groupe", "cat": "PHARMACEUTIQUE", "phone": "021 54 32 10", "email": "saidal@saidal.dz", "address": "Route de Baraki, Hussein Dey, Alger", "tax_id": "099611223340018"},
        {"code": "FRS-004", "name": "Pfizer Algerie SARL", "cat": "PHARMACEUTIQUE", "phone": "023 89 01 23", "email": "algeria@pfizer.com", "address": "Lot 23, Sidi Yahia, Hydra, Alger", "tax_id": "099644556670025"},
        {"code": "FRS-005", "name": "Hikma Pharma Algerie", "cat": "PHARMACEUTIQUE", "phone": "025 30 12 34", "email": "hikma@hikma.dz", "address": "Zone Bouchaoui, Blida", "tax_id": "009977889900016"},
        {"code": "FRS-006", "name": "Sanofi Algerie", "cat": "PHARMACEUTIQUE", "phone": "021 73 24 56", "email": "algerie@sanofi.com", "address": "Cite Diplomatique, El Biar, Alger", "tax_id": "099655443320014"},
        {"code": "FRS-007", "name": "Novo Nordisk Algerie", "cat": "PHARMACEUTIQUE", "phone": "021 60 70 80", "email": "info@novonordisk.dz", "address": "Tour El Qods, Paradou, Alger", "tax_id": "099622334450012"},
        {"code": "FRS-008", "name": "Roche Algerie SARL", "cat": "PHARMACEUTIQUE", "phone": "021 44 55 66", "email": "roche@roche.dz", "address": "Route Nationale 1, Birkhadem, Alger", "tax_id": "099633221100023"},
        {"code": "FRS-009", "name": "LFB Algerie", "cat": "MATERIEL MEDICAL", "phone": "023 11 22 33", "email": "lfb@lfb.dz", "address": "Zone Activite, Reghaia, Alger", "tax_id": "099611009900011"},
        {"code": "FRS-010", "name": "Cosmétiques Pharma DZ", "cat": "COSMETIQUE", "phone": "021 22 33 44", "email": "pharma@cosmetiques.dz", "address": "Cite 1er Novembre, Kouba, Alger", "tax_id": "099600112230029"},
        {"code": "FRS-011", "name": "MedEquip Algerie", "cat": "MATERIEL MEDICAL", "phone": "031 55 66 77", "email": "contact@medequip.dz", "address": "Boulevard de l'Armee, Oran", "tax_id": "099789900110031"},
        {"code": "FRS-012", "name": "Merck Algerie", "cat": "PHARMACEUTIQUE", "phone": "021 88 99 00", "email": "merck@merck.dz", "address": "Lot Industriel, Rouiba, Alger", "tax_id": "099710203040020"},
    ]
    suppliers = []
    for sd in suppliers_data:
        sup = Supplier(
            code=sd["code"], name=sd["name"], category=sd["cat"],
            phone=sd["phone"], email=sd["email"], address=sd["address"],
            tax_id=sd["tax_id"], is_active=1, credit_period_days=30, credit_limit=600000.0
        )
        session.add(sup)
        suppliers.append(sup)
    session.commit()
    print(f"  -> {len(suppliers)} fournisseurs")

    # ── 3. CLIENTS (20) ──────────────────────────────────────────────────
    print("Creation des clients...")
    clients_data = [
        {"code": "CLT-001", "name": "Pharmacie El Amel", "type": "ENTREPRISE", "phone": "021 30 45 67", "email": "elamel@gmail.com", "address": "12 Rue Hassiba Ben Bouali, Alger-Centre", "credit": 150000.0, "tax_id": "099601234560011"},
        {"code": "CLT-002", "name": "Clinique Privee Essaada", "type": "ENTREPRISE", "phone": "021 76 54 32", "email": "essaada@clinique.dz", "address": "45 Chemin Doudou Mokhtar, Ben Aknoun, Alger", "credit": 300000.0, "tax_id": "099609876540028"},
        {"code": "CLT-003", "name": "Pharmacie Ibn Sina", "type": "ENTREPRISE", "phone": "023 12 34 56", "email": "ibnsina@pharma.dz", "address": "7 Boulevard Colonel Amirouche, Tizi-Ouzou", "credit": 80000.0, "tax_id": "099615432100014"},
        {"code": "CLT-004", "name": "Hopital Mustapha Pacha", "type": "ENTREPRISE", "phone": "021 23 11 00", "email": "mustapha@sante.dz", "address": "Place du 1er Mai, Alger-Centre", "credit": 500000.0, "tax_id": "000001234000001"},
        {"code": "CLT-005", "name": "Salim Belkacem", "type": "PARTICULIER", "phone": "0550 12 34 56", "email": "salim@gmail.com", "address": "Cite Les Bananiers, Hydra, Alger", "credit": 20000.0, "tax_id": None},
        {"code": "CLT-006", "name": "Amina Mansouri", "type": "PARTICULIER", "phone": "0661 98 76 54", "email": "amina.m@outlook.com", "address": "Rue Belouizdad, Kouba, Alger", "credit": 15000.0, "tax_id": None},
        {"code": "CLT-007", "name": "Pharmacie Al Baraka", "type": "ENTREPRISE", "phone": "038 45 67 89", "email": "albaraka@pharma.dz", "address": "22 Avenue ALN, Blida", "credit": 120000.0, "tax_id": "099632109870022"},
        {"code": "CLT-008", "name": "Centre de Sante Bab El Oued", "type": "ENTREPRISE", "phone": "021 45 78 90", "email": "cs-beo@sante.gov.dz", "address": "Rue Larbi Ben M'hidi, Bab El Oued, Alger", "credit": 200000.0, "tax_id": "000008765000002"},
        {"code": "CLT-009", "name": "Pharmacie Nouvelle", "type": "ENTREPRISE", "phone": "031 22 33 44", "email": "nouvelle@pharma.dz", "address": "Boulevard de la Republique, Oran", "credit": 90000.0, "tax_id": "099678901230033"},
        {"code": "CLT-010", "name": "Farid Haddad", "type": "PARTICULIER", "phone": "0770 45 67 89", "email": "farid.h@yahoo.fr", "address": "Residence Les Pins, Bab Ezzouar, Alger", "credit": 10000.0, "tax_id": None},
        {"code": "CLT-011", "name": "Pharmacie El Qods", "type": "ENTREPRISE", "phone": "021 55 66 77", "email": "elqods@pharma.dz", "address": "Route des Deux Bassins, El Harrach, Alger", "credit": 180000.0, "tax_id": "099645678900041"},
        {"code": "CLT-012", "name": "Clinique Ain Naadja", "type": "ENTREPRISE", "phone": "021 54 87 65", "email": "ainnaadja@clinique.dz", "address": "Route Ain Naadja, Birtouta, Alger", "credit": 250000.0, "tax_id": "099656789010044"},
        {"code": "CLT-013", "name": "Mounir Tahir", "type": "PARTICULIER", "phone": "0560 77 88 99", "email": "mounir@hotmail.fr", "address": "Cite Soumam, Tizi-Ouzou", "credit": 8000.0, "tax_id": None},
        {"code": "CLT-014", "name": "Pharmacie Sidi Mabrouk", "type": "ENTREPRISE", "phone": "031 98 87 76", "email": "sidimabrouk@pharma.dz", "address": "Rue Didouche Mourad, Constantine", "credit": 70000.0, "tax_id": "099667890120055"},
        {"code": "CLT-015", "name": "Hopital de Bejaia", "type": "ENTREPRISE", "phone": "034 21 43 65", "email": "hopital@bejaia.sante.dz", "address": "Route Nationale 9, Bejaia", "credit": 400000.0, "tax_id": "000012345000003"},
        {"code": "CLT-016", "name": "Lila Amrani", "type": "PARTICULIER", "phone": "0679 11 22 33", "email": "lila.a@gmail.com", "address": "Cite Boukhrouba, Setif", "credit": 12000.0, "tax_id": None},
        {"code": "CLT-017", "name": "Pharmacie El Fath", "type": "ENTREPRISE", "phone": "021 88 99 00", "email": "elfath@pharma.dz", "address": "Avenue Soumam, Alger", "credit": 100000.0, "tax_id": "099678012340062"},
        {"code": "CLT-018", "name": "Polyclinique Casbah", "type": "ENTREPRISE", "phone": "021 77 66 55", "email": "casbah@polyclinique.dz", "address": "Rue de la Casbah, Alger", "credit": 160000.0, "tax_id": "099689123450073"},
        {"code": "CLT-019", "name": "Karim Bouderba", "type": "PARTICULIER", "phone": "0551 44 55 66", "email": "karim.b@yahoo.com", "address": "Cite Ain El Bey, Constantine", "credit": 5000.0, "tax_id": None},
        {"code": "CLT-020", "name": "Pharmacie Liberte", "type": "ENTREPRISE", "phone": "041 33 44 55", "email": "liberte@pharma.dz", "address": "Avenue de la Liberte, Annaba", "credit": 130000.0, "tax_id": "099690234560084"},
    ]
    clients = []
    for cd in clients_data:
        cl = Client(
            code=cd["code"], name=cd["name"], client_type=cd["type"],
            phone=cd["phone"], email=cd["email"], address=cd["address"],
            credit_limit=cd["credit"], tax_id=cd["tax_id"], is_active=1
        )
        session.add(cl)
        clients.append(cl)
    session.commit()
    print(f"  -> {len(clients)} clients")

    # ── 4. PRODUCTS (70) ─────────────────────────────────────────────────
    print("Creation de 70 produits...")
    products_def = [
        # Analgesiques
        ("Doliprane 500mg Gelules 16cp",        "Analgesiques & Antipyretiques",  120.0,  180.0, "6131110000018"),
        ("Doliprane 1g Comprimes 8cp",           "Analgesiques & Antipyretiques",  180.0,  260.0, "6131110000025"),
        ("Efferalgan 500mg Effervescent 16cp",   "Analgesiques & Antipyretiques",  140.0,  210.0, "6131110000032"),
        ("Efferalgan 1g Comprimes 8cp",          "Analgesiques & Antipyretiques",  190.0,  280.0, "6131110000049"),
        ("Aspegic 100mg Nourrissons Sachets",    "Analgesiques & Antipyretiques",   90.0,  130.0, "6131110000056"),
        ("Aspegic 500mg Adultes Sachets",        "Analgesiques & Antipyretiques",  130.0,  195.0, "6131110000063"),
        ("Kardegic 75mg Sachets 30cp",           "Analgesiques & Antipyretiques",  150.0,  220.0, "6131110000070"),
        ("Spasfon Lyoc 80mg 15 lyophilisats",    "Analgesiques & Antipyretiques",  240.0,  350.0, "6131110000087"),
        # Antibiotiques
        ("Clamoxyl 1g Comprimes Boite 14",       "Antibiotiques",  450.0,  680.0, "6132220000017"),
        ("Augmentin 1g Adulte Boite 14",         "Antibiotiques",  820.0, 1150.0, "6132220000024"),
        ("Oroken 200mg Capsules Boite 6",        "Antibiotiques",  750.0, 1020.0, "6132220000031"),
        ("Zinnat 500mg Comprimes Boite 10",      "Antibiotiques",  680.0,  950.0, "6132220000048"),
        ("Zeclar 500mg Comprimes Boite 14",      "Antibiotiques",  900.0, 1280.0, "6132220000055"),
        ("Orelox 100mg Comprimes Boite 10",      "Antibiotiques",  620.0,  880.0, "6132220000062"),
        ("Amoxicilline 500mg Gelules Boite 16",  "Antibiotiques",  300.0,  450.0, "6132220000079"),
        ("Ciprofloxacine 500mg Boite 10",        "Antibiotiques",  480.0,  700.0, "6132220000086"),
        # Anti-inflammatoires
        ("Profenid 100mg Gelules Boite 14",      "Anti-inflammatoires",  280.0,  420.0, "6133330000016"),
        ("Voltarene 50mg Comprimes Boite 20",    "Anti-inflammatoires",  310.0,  450.0, "6133330000023"),
        ("Ibuprofene 400mg Comprimes Boite 20",  "Anti-inflammatoires",  190.0,  280.0, "6133330000030"),
        ("Cortancyl 5mg Comprimes Boite 30",     "Anti-inflammatoires",  320.0,  460.0, "6133330000047"),
        ("Solupred 20mg Comprimes Boite 20",     "Anti-inflammatoires",  250.0,  370.0, "6133330000054"),
        # Cardiovasculaire
        ("Aprovel 150mg Comprimes Boite 28",     "Cardiovasculaire",   600.0,  850.0, "6134440000015"),
        ("Co-Aprovel 150/12.5mg Boite 28",       "Cardiovasculaire",   750.0, 1050.0, "6134440000022"),
        ("Tahor 20mg Comprimes Boite 30",        "Cardiovasculaire",  1100.0, 1550.0, "6134440000039"),
        ("Crestor 10mg Comprimes Boite 28",      "Cardiovasculaire",  1300.0, 1850.0, "6134440000046"),
        ("Coversyl 5mg Comprimes Boite 30",      "Cardiovasculaire",   680.0,  950.0, "6134440000053"),
        ("Lasilix 40mg Comprimes Boite 30",      "Cardiovasculaire",   180.0,  260.0, "6134440000060"),
        ("Plavix 75mg Comprimes Boite 28",       "Cardiovasculaire",  1450.0, 2100.0, "6134440000077"),
        ("Atenolol 50mg Comprimes Boite 30",     "Cardiovasculaire",   220.0,  320.0, "6134440000084"),
        # Vitamines
        ("Supradyn Intensia Boite 30cp",         "Vitamines & Supplements",   850.0, 1200.0, "6135550000014"),
        ("Bion 3 Adultes Comprimes Boite 30",    "Vitamines & Supplements",  1100.0, 1600.0, "6135550000021"),
        ("Alvityl Vitalite Sirop 150ml",         "Vitamines & Supplements",   450.0,  650.0, "6135550000038"),
        ("Magne B6 Ampoules Boite 20",           "Vitamines & Supplements",   380.0,  550.0, "6135550000045"),
        ("Zinc 15mg Oligo-element Boite 30",     "Vitamines & Supplements",   240.0,  350.0, "6135550000052"),
        ("Vitamine D3 1000UI Boite 30",          "Vitamines & Supplements",   290.0,  420.0, "6135550000069"),
        ("Vitamine C 1g Effervescent Boite 20",  "Vitamines & Supplements",   200.0,  290.0, "6135550000076"),
        ("Acide Folique 5mg Comprimes Boite 30", "Vitamines & Supplements",   160.0,  230.0, "6135550000083"),
        # Parapharmacie
        ("Betadine Dermique Flacon 125ml",       "Parapharmacie",   260.0,  380.0, "6136660000013"),
        ("Biafine Emulsion Tube 93g",            "Parapharmacie",   340.0,  490.0, "6136660000020"),
        ("Dexeryl Creme Flacon 250g",            "Parapharmacie",   680.0,  980.0, "6136660000037"),
        ("Compresse Sterile 7.5x7.5 Boite 50",  "Parapharmacie",   120.0,  180.0, "6136660000051"),
        ("Sparadrap Chirurgical 2.5cm x 5m",     "Parapharmacie",    90.0,  135.0, "6136660000068"),
        ("Tensiometre Bras Electronique Omron",  "Parapharmacie",  4800.0, 6900.0, "6136660000075"),
        ("Thermometre Infrarouge Frontal",       "Parapharmacie",  1800.0, 2600.0, "6136660000082"),
        ("Lecteur Glycemie Accu-Check",          "Parapharmacie",  2200.0, 3200.0, "6136660000099"),
        ("Seringue 5ml Boite 100",               "Parapharmacie",   380.0,  550.0, "6136660000106"),
        ("Gants Latex Non Poudr. Boite 100",     "Parapharmacie",   450.0,  650.0, "6136660000113"),
        # Soins & Cosmetiques
        ("Mustela Gel Lavant Bebe 500ml",        "Soins & Cosmetiques",  1450.0, 2100.0, "6137770000012"),
        ("La Roche-Posay Cicaplast Baume B5",    "Soins & Cosmetiques",  1100.0, 1550.0, "6137770000029"),
        ("Vichy Mineral 89 Serum 50ml",          "Soins & Cosmetiques",  2900.0, 3900.0, "6137770000036"),
        ("Bioderma Sensibio H2O 500ml",          "Soins & Cosmetiques",  1200.0, 1750.0, "6137770000043"),
        ("Eau Thermale Avene Spray 300ml",       "Soins & Cosmetiques",   850.0, 1250.0, "6137770000050"),
        ("Isdin Photoprotector SPF50 200ml",     "Soins & Cosmetiques",  2100.0, 2950.0, "6137770000067"),
        # Gastro-Enterologie
        ("Mopral 20mg Gelules Boite 28",         "Gastro-Enterologie",   350.0,  520.0, "6138880000011"),
        ("Inexium 40mg Comprimes Boite 28",      "Gastro-Enterologie",   720.0,  990.0, "6138880000028"),
        ("Gaviscon Suspension Buvable 200ml",    "Gastro-Enterologie",   300.0,  440.0, "6138880000035"),
        ("Maalox Citron Sans Sucre Boite 40",    "Gastro-Enterologie",   220.0,  320.0, "6138880000042"),
        ("Smecta 3g Boite 30 Sachets",           "Gastro-Enterologie",   180.0,  260.0, "6138880000059"),
        ("Debridat 100mg Comprimes Boite 30",    "Gastro-Enterologie",   280.0,  410.0, "6138880000066"),
        # Pneumologie
        ("Ventoline Spray 100mcg 200 doses",     "Pneumologie & Voies Respiratoires",  380.0,  540.0, "6139990000010"),
        ("Becotide 250mcg Spray 200 doses",      "Pneumologie & Voies Respiratoires",  520.0,  750.0, "6139990000027"),
        ("Aerius 5mg Comprimes Boite 30",        "Pneumologie & Voies Respiratoires",  480.0,  680.0, "6139990000034"),
        ("Clarityne 10mg Comprimes Boite 30",    "Pneumologie & Voies Respiratoires",  410.0,  580.0, "6139990000041"),
        # Diabetologie
        ("Metformine 850mg Comprimes Boite 30",  "Diabetologie & Endocrinologie",  180.0,  260.0, "6140010000019"),
        ("Glucophage 1000mg Boite 30",           "Diabetologie & Endocrinologie",  320.0,  460.0, "6140010000026"),
        ("Novomix 30 Flexpen 100U/ml x 5",       "Diabetologie & Endocrinologie", 2800.0, 3900.0, "6140010000033"),
        ("Insuline Actrapid 100U/ml x 5",        "Diabetologie & Endocrinologie", 1800.0, 2600.0, "6140010000040"),
        # Neurologie
        ("Imovane 7.5mg Comprimes Boite 14",     "Neurologie & Psychiatrie",  320.0,  460.0, "6141120000018"),
        ("Lexomil 6mg Comprimes Boite 30",       "Neurologie & Psychiatrie",  280.0,  400.0, "6141120000025"),
        ("Depakine 500mg Comprimes Boite 30",    "Neurologie & Psychiatrie",  450.0,  640.0, "6141120000032"),
        # Dermatologie
        ("Betnovate Creme Tube 30g",             "Dermatologie",  380.0,  550.0, "6142230000017"),
        ("Locoid Creme Tube 30g",                "Dermatologie",  420.0,  600.0, "6142230000024"),
        ("Daivobet Gel Tube 60g",                "Dermatologie",  850.0, 1200.0, "6142230000031"),
    ]

    products = []
    for idx, (name, cat_name, cost, sell, barcode) in enumerate(products_def):
        cat = cat_by_name.get(cat_name)
        if not cat:
            continue
        code = f"PRD-{idx+1:05d}"
        tva_rate = 19.0 if "Cosmet" in cat_name or "Paraph" in cat_name else 9.0
        prod = Product(
            code=code, barcode=barcode, name=name,
            description=f"Produit officinal : {name}",
            category_id=cat.id,
            cost_price=cost, selling_price=sell,
            tax_rate=tva_rate,
            min_stock_level=random.choice([10, 15, 20, 25]),
            unit="Boite", created_by=admin.id, is_active=1
        )
        session.add(prod)
        session.flush()

        session.add(Barcode(product_id=prod.id, barcode_value=barcode, is_primary=1))

        qty = random.randint(80, 300)
        session.add(Stock(product_id=prod.id, quantity=qty))

        exp_soon = (NOW + timedelta(days=random.randint(30, 180))).strftime("%Y-%m-%d")
        exp_far  = (NOW + timedelta(days=random.randint(400, 900))).strftime("%Y-%m-%d")
        qty_s = random.randint(5, 30)
        qty_f = qty - qty_s
        session.add(StockBatch(product_id=prod.id, lot_number=f"BT-{NOW.strftime('%y%m')}-{prod.id:03d}A",
            expiration_date=exp_soon, quantity=qty_s, remaining_quantity=qty_s, cost_price=cost))
        session.add(StockBatch(product_id=prod.id, lot_number=f"BT-{NOW.strftime('%y%m')}-{prod.id:03d}B",
            expiration_date=exp_far, quantity=qty_f, remaining_quantity=qty_f, cost_price=cost))
        session.add(StockMovement(product_id=prod.id, movement_type=MovementType.ADJUSTMENT.value,
            quantity=qty, user_id=admin.id, notes="Stock initial"))
        products.append(prod)

    session.commit()
    print(f"  -> {len(products)} produits")

    # ── 5. PURCHASE ORDERS (30) ──────────────────────────────────────────
    print("Creation de 30 bons de commande fournisseur...")
    for i in range(30):
        sup  = random.choice(suppliers)
        dt   = rdate(1, 120)
        stat = "COMPLETED" if i < 24 else random.choice(["VALIDATED", "DRAFT"])
        po = PurchaseOrder(
            order_number=f"CMD-{NOW.year}-{i+1:04d}",
            supplier_id=sup.id, created_by=admin.id,
            created_at=ds(dt), status=stat, total_amount=0.0,
            notes="Commande automatique (seeder)"
        )
        session.add(po)
        session.flush()
        total = 0.0
        for p in random.sample(products, random.randint(4, 10)):
            qty  = random.randint(10, 60)
            price = p.cost_price
            lt   = qty * price
            total += lt
            session.add(PurchaseOrderItem(purchase_order_id=po.id, product_id=p.id,
                quantity=qty, unit_price=price, line_total=lt))
        po.total_amount = total
    session.commit()
    print("  -> 30 bons de commande")

    # ── 6. PURCHASES / BONS DE RECEPTION (25) ────────────────────────────
    print("Creation de 25 bons de reception fournisseur...")
    for i in range(25):
        sup = random.choice(suppliers)
        dt  = rdate(1, 150)
        pur = Purchase(
            purchase_number=f"REC-{NOW.year}-{i+1:04d}",
            supplier_id=sup.id, created_by=admin.id,
            purchase_date=ds(dt),
            status="COMPLETED", subtotal=0.0, total_amount=0.0,
            discount_amount=0.0, tax_total=0.0, notes="Reception automatique (seeder)"
        )
        session.add(pur)
        session.flush()
        total = subtotal_p = 0.0
        for p in random.sample(products, random.randint(3, 8)):
            qty   = random.randint(20, 80)
            price = p.cost_price
            lt    = qty * price
            total     += lt
            subtotal_p += lt
            session.add(PurchaseItem(purchase_id=pur.id, product_id=p.id,
                ordered_qty=qty, received_qty=qty, unit_cost=price, line_total=lt))
        pur.subtotal     = subtotal_p
        pur.total_amount = total
    session.commit()
    print("  -> 25 bons de reception")


    # ── 7. SALES / BONS DE LIVRAISON (120) ────────────────────────────────
    print("Creation de 120 ventes (BL) avec dettes...")
    pay_methods = [PaymentMethod.ESPECES.value, PaymentMethod.CARTE.value, PaymentMethod.CREDIT.value]
    credit_sales = []

    for i in range(120):
        cli = random.choice(clients) if random.random() > 0.2 else None
        dt  = rdate(0, 200)
        num = f"BL-{dt.strftime('%Y%m%d')}-{i+1:04d}"
        pay = random.choice(pay_methods)
        if not cli and pay == PaymentMethod.CREDIT.value:
            pay = PaymentMethod.ESPECES.value

        sale = Sale(
            sale_number=num, client_id=cli.id if cli else None,
            cashier_id=admin.id, sale_date=ds(dt),
            subtotal=0.0, discount_amount=0.0, discount_type=None,
            discount_value=0.0, tax_total=0.0, total_amount=0.0,
            paid_amount=0.0, change_amount=0.0,
            payment_method=pay, status="COMPLETED", created_at=ds(dt)
        )
        session.add(sale)
        session.flush()

        subtotal = tax_total = 0.0
        n_items = random.randint(2, 8)
        for p in random.sample(products, n_items):
            qty      = random.randint(1, 12)
            price    = p.selling_price
            cost     = p.cost_price
            disc_a   = round(price * qty * random.choice([0, 0, 0, 0.05]), 2)
            ht       = qty * price - disc_a
            tva      = 0.0
            ttc      = ht + tva
            subtotal  += ht
            tax_total += tva
            session.add(SaleItem(sale_id=sale.id, product_id=p.id,
                quantity=qty, unit_price=price, cost_price=cost,
                discount_amount=disc_a, tax_rate=0.0,
                tax_amount=0.0, line_total=ttc))

        total_ttc = subtotal
        disc_tot  = subtotal - (subtotal - 0)  # header discount
        sale.subtotal      = subtotal
        sale.tax_total     = 0.0
        sale.total_amount  = total_ttc
        sale.discount_amount = 0.0

        if pay == PaymentMethod.CREDIT.value and cli:
            paid_frac = random.choice([0.0, 0.0, 0.25, 0.5, 0.75, 1.0])
            paid      = round(total_ttc * paid_frac, 2)
            sale.paid_amount = paid
            remaining    = round(total_ttc - paid, 2)
            debt_status  = "PAID" if remaining <= 0.01 else ("PARTIAL" if paid > 0 else "PENDING")
            debt = Debt(
                entity_type="CLIENT", entity_id=cli.id,
                reference_type="SALE", reference_id=sale.id,
                total_amount=total_ttc, paid_amount=paid,
                remaining_amount=remaining, status=debt_status
            )
            session.add(debt)
            if paid > 0 and debt_status != "PAID":
                credit_sales.append((debt, cli, paid, dt))
        else:
            sale.paid_amount = total_ttc

    session.commit()
    print("  -> 120 ventes (BL)")

    # ── 8. PAYMENTS for credit sales ─────────────────────────────────────
    print("Creation de paiements sur credit...")
    payments_added = 0
    session.flush()  # ensure all debt IDs are in DB
    for (debt, cli, paid_so_far, sale_dt) in credit_sales[:60]:
        if paid_so_far > 0:
            pay_dt = sale_dt + timedelta(days=random.randint(1, 20))
            session.add(Payment(
                debt_id=debt.id,
                amount=paid_so_far,
                payment_method=random.choice([PaymentMethod.ESPECES.value, PaymentMethod.CARTE.value]),
                payment_date=ds(pay_dt),
                reference_number=f"CHQ-{random.randint(100000, 999999)}",
                received_by=admin.id,
                notes="Paiement partiel"
            ))
            payments_added += 1
    session.commit()
    print(f"  -> {payments_added} paiements")


    # ── 9. DELIVERIES (40) ───────────────────────────────────────────────
    print("Creation de 40 bons de livraison (deliveries)...")
    zones = ["Zone Nord", "Zone Sud", "Zone Est", "Zone Ouest", "Zone Centre"]
    statuses = ["DELIVERED", "DELIVERED", "DELIVERED", "PENDING", "PARTIAL"]

    # Get sales with clients to link deliveries
    all_sales = session.query(Sale).filter(Sale.client_id.isnot(None)).order_by(Sale.id).limit(40).all()

    for i, sale in enumerate(all_sales):
        cli   = session.query(Client).get(sale.client_id)
        dt    = rdate(0, 90)
        stat  = random.choice(statuses)
        deliv = Delivery(
            delivery_number=f"BL-{dt.strftime('%Y%m%d')}-{i+1:04d}",
            sale_id=sale.id,
            client_id=cli.id,
            operator_id=admin.id,
            status=stat,
            scheduled_date=ds(dt),
            delivered_at=ds(dt + timedelta(hours=2)) if stat == "DELIVERED" else None,
            zone=random.choice(zones),
            address=cli.address,
            notes=f"Livraison {i+1} — seeder",
            created_by=admin.id,
            created_at=ds(dt)
        )
        session.add(deliv)
        session.flush()

        # Add delivery items from sale items
        for si in sale.items:
            qty_livr = si.quantity if stat == "DELIVERED" else si.quantity * 0.5
            session.add(DeliveryItem(
                delivery_id=deliv.id,
                product_id=si.product_id,
                quantity=si.quantity,
                delivered_qty=qty_livr,
            ))
    session.commit()
    print("  -> 40 bons de livraison (deliveries)")

    # ── 10. INVOICES (20) ────────────────────────────────────────────────
    print("Creation de 20 factures...")
    b2b_clients = [c for c in clients if c.client_type == "ENTREPRISE"]
    for i in range(20):
        cli = random.choice(b2b_clients)
        dt  = rdate(1, 180)
        inv = Invoice(
            invoice_number=f"FAC-{dt.strftime('%Y%m%d%H%M')}-{i+1:02d}",
            client_id=cli.id,
            status="VALIDATED" if i < 16 else "DRAFT",
            subtotal=0.0, discount_amount=0.0, tax_total=0.0, total_amount=0.0,
            created_by=admin.id, created_at=ds(dt),
            validated_at=ds(dt + timedelta(hours=1)) if i < 16 else None,
        )
        session.add(inv)
        session.flush()

        subtotal = tax_total = 0.0
        for p in random.sample(products, random.randint(3, 10)):
            qty   = random.randint(5, 30)
            price = p.selling_price
            disc  = 0.0
            tva   = qty * price * (p.tax_rate / 100.0)
            ttc   = qty * price + tva
            subtotal  += qty * price
            tax_total += tva
            session.add(InvoiceItem(invoice_id=inv.id, product_id=p.id,
                quantity=qty, unit_price=price,
                discount_amount=disc, tax_rate=p.tax_rate,
                tax_amount=tva, line_total=ttc))
        inv.subtotal     = subtotal
        inv.tax_total    = tax_total
        inv.total_amount = subtotal + tax_total
    session.commit()
    print("  -> 20 factures")

    # ── 11. CUSTOMER ORDERS (15) ──────────────────────────────────────────
    print("Creation de 15 commandes client...")
    for i in range(15):
        cli = random.choice(clients)
        dt  = rdate(1, 60)
        ord_ = CustomerOrder(
            order_number=f"CORDER-{NOW.year}-{i+1:04d}",
            client_id=cli.id,
            status=random.choice(["DRAFT", "VALIDATED", "COMPLETED", "CANCELLED"]),
            subtotal=0.0, discount_amount=0.0, tax_total=0.0, total_amount=0.0,
            expected_delivery_date=(dt + timedelta(days=random.randint(3, 14))).strftime("%Y-%m-%d"),
            notes=f"Commande client #{i+1} (seeder)",
            created_by=admin.id, created_at=ds(dt)
        )
        session.add(ord_)
        session.flush()

        subtotal = tax_total = 0.0
        for p in random.sample(products, random.randint(2, 7)):
            qty   = random.randint(1, 20)
            price = p.selling_price
            tva   = qty * price * (p.tax_rate / 100.0)
            ttc   = qty * price + tva
            subtotal  += qty * price
            tax_total += tva
            session.add(CustomerOrderItem(order_id=ord_.id, product_id=p.id,
                quantity=qty, unit_price=price,
                discount_amount=0.0, tax_rate=p.tax_rate,
                tax_amount=tva, line_total=ttc))
        ord_.subtotal    = subtotal
        ord_.tax_total   = tax_total
        ord_.total_amount = subtotal + tax_total
    session.commit()
    print("  -> 15 commandes client")

    # ── 12. CREDIT NOTES / RETOURS CLIENT (15) ────────────────────────────
    print("Creation de 15 avoirs / retours client...")
    for i in range(15):
        cli = random.choice(clients)
        dt  = rdate(1, 90)
        cn  = CreditNote(
            note_number=f"AVOIR-{NOW.year}-{i+1:04d}",
            client_id=cli.id,
            status="VALIDATED",
            total_amount=0.0,
            reason=f"Retour client #{i+1} (seeder)",
            created_by=admin.id,
            created_at=ds(dt)
        )
        session.add(cn)
        session.flush()
        total = 0.0
        for p in random.sample(products, random.randint(1, 4)):
            qty   = random.randint(1, 5)
            price = p.selling_price
            lt    = qty * price
            total += lt
            session.add(CreditNoteItem(credit_note_id=cn.id, product_id=p.id,
                quantity=qty, unit_price=price, line_total=lt))
        cn.total_amount = total
    session.commit()
    print("  -> 15 avoirs client")


    # ── 13. CASH REGISTER SESSION ──────────────────────────────────────────
    print("Session de caisse active...")
    try:
        session.query(CashRegister).delete()
        session.commit()
        session.add(CashRegister(
            session_date=NOW.strftime("%Y-%m-%d"),
            opened_by=admin.id, opening_balance=20000.0,
            total_sales_cash=0.0, total_sales_card=0.0,
            total_expenses=0.0, total_withdrawals=0.0,
            total_deposits=0.0, expected_balance=20000.0,
            status="OPEN",
            opened_at=NOW.strftime("%Y-%m-%d %H:%M:%S")
        ))
        session.commit()
        print("  -> Session de caisse ouverte")
    except Exception as e:
        print(f"  -> Caisse ignoree: {e}")

    print("\n=== SEEDING MASSIF COMPLET ===")
    print(f"  Categories       : {len(categories)}")
    print(f"  Fournisseurs     : {len(suppliers)}")
    print(f"  Clients          : {len(clients)}")
    print(f"  Produits         : {len(products)}")
    print(f"  Bons Commande    : 30")
    print(f"  Bons Reception   : 25")
    print(f"  Ventes (BL)      : 120")
    print(f"  Paiements credit : {payments_added}")
    print(f"  Livraisons       : 40")
    print(f"  Factures         : 20")
    print(f"  Commandes Client : 15")
    print(f"  Avoirs Client    : 15")
    print("\nBase de donnees prete pour les tests!")


if __name__ == "__main__":
    main()

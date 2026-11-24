"""Seed users, knowledge base and fictional demo data.  `python -m app.seed [--reset]`"""
import random
import sys
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import pipeline, rag, synthetic
from .db import Base, SessionLocal, engine
from .models import (Complaint, InventoryItem, Invoice, Product, ProductionRun, PurchaseOrder, SalesOrder, Supplier,
                     User, utcnow)
from .security import hash_password

DEMO_USERS = [
    ("admin@demo.local", "Alex Admin", "admin"),
    ("support@demo.local", "Sam Support", "support"),
    ("quality@demo.local", "Quinn Quality", "quality"),
    ("ops@demo.local", "Olivia Operations", "operations"),
    ("finance@demo.local", "Finn Finance", "finance"),
    ("sales@demo.local", "Sasha Sales", "sales"),
    ("exec@demo.local", "Eva Executive", "executive"),
]
DEMO_PASSWORD = "demo1234"


def seed_users(db: Session) -> None:
    for email, name, role in DEMO_USERS:
        if not db.scalar(select(User).where(User.email == email)):
            db.add(User(email=email, name=name, role=role, password_hash=hash_password(DEMO_PASSWORD)))
    db.commit()


def seed_business(db: Session, rng: random.Random) -> None:
    now = utcnow()
    prods = {}
    for sku, name, brand, kind, allergens in synthetic.PRODUCTS:
        p = Product(sku=sku, name=name, brand=brand, kind=kind, allergens=allergens)
        db.add(p)
        prods[sku] = p
    sups = [Supplier(name=n, country=c, lead_time_days=lt, on_time_rate=otr) for n, c, lt, otr in [
        ("Golden Valley Poultry (demo)", "USA", 4, 0.96), ("Pacific Packaging Co (demo)", "USA", 12, 0.88),
        ("Mesa Spice & Chile (demo)", "Mexico", 9, 0.91), ("Sierra Flour Mills (demo)", "USA", 6, 0.97),
        ("Coastal Resin Films (demo)", "USA", 14, 0.81)]]
    db.add_all(sups)
    db.flush()

    # inventory (a few items deliberately below reorder point)
    inv = [("RM-CHKN", "Cooked chicken breast", "raw", 1800, "kg", 2500, 0), ("RM-RICE", "Long grain rice", "raw", 9200, "kg", 4000, 3),
           ("RM-CHIL", "Chipotle chile paste", "raw", 310, "kg", 400, 2), ("RM-BEEF", "Braised beef (birria)", "raw", 2600, "kg", 2000, 0),
           ("RM-FLOUR", "Wheat flour", "raw", 14000, "kg", 6000, 3), ("RM-ALMD", "Almond pieces", "raw", 520, "kg", 300, 3),
           ("PK-TRAY", "Bowl trays (PET)", "packaging", 21000, "pcs", 30000, 1), ("PK-FILM", "Top-seal film", "packaging", 8, "rolls", 20, 4),
           ("PK-BAG", "Pita chip bags", "packaging", 52000, "pcs", 25000, 1), ("PK-CTN", "Shipper cartons", "packaging", 6400, "pcs", 5000, 1),
           ("FG-CHIP", "Chipotle Chicken Bowl (frozen)", "finished", 4200, "cases", 3000, None),
           ("FG-BIRR", "Birria Rice Bowl (frozen)", "finished", 1900, "cases", 2500, None),
           ("FG-CRUM", "Cali Crumble Cookie", "finished", 7300, "cases", 2000, None), ("FG-PITA", "Eat Pita Chips", "finished", 5100, "cases", 3500, None)]
    for sku, name, kind, qty, unit, rp, si in inv:
        db.add(InventoryItem(sku=sku, name=name, kind=kind, qty=qty, unit=unit, reorder_point=rp, location="NV-Henderson" if rng.random() < 0.7 else "CA-Plant",
                             supplier_id=sups[si].id if si is not None else None))

    # production: daily runs for 45 days. Scenario lots are created explicitly with elevated defects.
    scenario_lots = {sc["lot"]: (sc["sku"], d) for (k, sc), d in zip(synthetic.SCENARIOS.items(), [20, 16, 12, 38, 8, 0, 0, 0, 0, 0]) if sc["lot"]}
    for d in range(45, 0, -1):
        date = now - timedelta(days=d)
        for sku, p in prods.items():
            lot = f"{synthetic.LOT_PREFIX[sku]}-{date:%y%m}-{chr(65 + (date.day - 1) // 7)}"
            if lot in scenario_lots:  # scenario lots get their own explicit runs below
                continue
            planned = rng.randint(7000, 9500)
            produced = int(planned * rng.uniform(0.93, 0.99))
            db.add(ProductionRun(product_id=p.id, lot_code=lot, line=f"Line {rng.randint(1, 4)}", facility="NV-Henderson",
                                 run_date=date, planned_units=planned, produced_units=produced,
                                 defect_units=int(produced * rng.uniform(0.006, 0.014))))
    for lot, (sku, days_ago) in scenario_lots.items():
        p = prods[sku]
        bad = lot in ("CC-2611-B", "BR-2611-A")
        for k in range(3):
            planned = rng.randint(7500, 9000)
            produced = int(planned * (rng.uniform(0.86, 0.9) if bad else rng.uniform(0.93, 0.98)))
            db.add(ProductionRun(product_id=p.id, lot_code=lot, line="Line 2", facility="NV-Henderson",
                                 run_date=now - timedelta(days=days_ago + k * 0.3 + 0.1), planned_units=planned, produced_units=produced,
                                 defect_units=int(produced * (rng.uniform(0.028, 0.04) if bad else rng.uniform(0.008, 0.013)))))

    for i, (item, sup, status, off) in enumerate([("PK-FILM", 4, "late", -6), ("PK-TRAY", 1, "shipped", 3), ("RM-CHIL", 2, "open", 8),
                                                  ("RM-CHKN", 0, "open", 2), ("PK-FILM", 4, "open", 10), ("RM-RICE", 3, "received", -9),
                                                  ("PK-BAG", 1, "received", -14), ("RM-BEEF", 0, "shipped", 1), ("RM-ALMD", 3, "late", -3), ("PK-CTN", 1, "open", 12)]):
        db.add(PurchaseOrder(po_number=f"PO-{7000 + i}", supplier_id=sups[sup].id, item_sku=item, qty=rng.randint(500, 5000),
                             amount=round(rng.uniform(4000, 38000), 2), status=status, expected_date=now + timedelta(days=off)))

    n = 0
    for d in range(60, 0, -1):
        for _ in range(rng.randint(1, 4)):
            sku = rng.choice(list(prods))
            qty = rng.randint(40, 600)
            n += 1
            db.add(SalesOrder(order_no=f"SO-{20000 + n}", customer=rng.choice(synthetic.RETAIL_CUSTOMERS), product_id=prods[sku].id,
                              qty=qty, amount=round(qty * rng.uniform(14, 31), 2), order_date=now - timedelta(days=d, hours=rng.randint(0, 20)), status="shipped"))

    for i in range(28):
        kind = "AR" if i < 20 else "AP"
        issued = now - timedelta(days=rng.randint(5, 80))
        due = issued + timedelta(days=30)
        status = "paid" if rng.random() < 0.45 else ("overdue" if due < now else "open")
        party = rng.choice(synthetic.RETAIL_CUSTOMERS) if kind == "AR" else rng.choice(sups).name
        db.add(Invoice(number=f"{kind}-{3000 + i}", kind=kind, party=party, amount=round(rng.uniform(3000, 60000), 2), issued=issued, due=due, status=status))
    db.commit()


def seed_complaints(db: Session, use_llm: bool = False) -> int:
    items = synthetic.make_complaints(utcnow())
    for it in items:
        c = pipeline.ingest(db, source=it["source"], body=it["body"], subject=it["subject"], customer_name=it["customer_name"],
                            customer_email=it["customer_email"], received_at=it["received_at"], enqueue=False)
        pipeline.process_complaint(db, c.id, use_llm=use_llm)
    return len(items)


def ensure_seed(demo_data: bool = True) -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_users(db)
        rag.ingest_folder(db)
        if demo_data and not db.scalar(select(func.count()).select_from(Product)):
            seed_business(db, random.Random(7))
        if demo_data and not db.scalar(select(func.count()).select_from(Complaint)):
            seed_complaints(db)


if __name__ == "__main__":
    if "--reset" in sys.argv:
        Base.metadata.drop_all(engine)
    ensure_seed()
    with SessionLocal() as db:
        print("complaints:", db.scalar(select(func.count()).select_from(Complaint)))

"""Synthetic data generators. ALL data is fictional: names, stores, lots, orders and customers."""
import random
from datetime import datetime, timedelta

FIRST = ["Maria", "John", "Ashley", "David", "Priya", "Luis", "Emily", "Marcus", "Sofia", "Daniel", "Hannah", "Carlos",
         "Grace", "Tyler", "Nina", "Omar", "Rachel", "Kevin", "Laura", "Jin", "Amber", "Victor", "Chloe", "Ethan"]
LAST = ["Alvarez", "Brooks", "Chen", "Davis", "Evans", "Foster", "Garcia", "Hughes", "Ito", "Jackson", "Kim", "Lopez",
        "Morgan", "Nguyen", "Ortiz", "Patel", "Quinn", "Reyes", "Silva", "Turner", "Underwood", "Vega", "Walker", "Young"]
STORES = ["FreshMart", "GreenCart Market", "Harbor Foods", "Sunrise Grocers", "Maple Street Market", "Desert Palms Foods"]
RETAIL_CUSTOMERS = ["FreshMart", "GreenCart Market", "Harbor Foods", "Sunrise Grocers", "Desert Palms Resort",
                    "Maple Street Market", "Lakeview Food Service", "Cactus Club Hospitality"]

PRODUCTS = [  # sku, name, brand, kind, allergens
    ("BB-CHIP", "Chipotle Chicken Bowl", "Bettr Bowl", "frozen_meal", "soy"),
    ("BB-BIRR", "Birria Rice Bowl", "Bettr Bowl", "frozen_meal", "none"),
    ("TU-COOK", "Tuscany Gourmet Cookies", "Tuscany", "cookie", "wheat, milk, egg"),
    ("CC-CRUM", "Cali Crumble Cookie", "Cali Crumble", "cookie", "wheat, milk, egg, soy"),
    ("EP-PITA", "Eat Pita Chips", "Eat Pita", "pita", "wheat, sesame"),
]
LOT_PREFIX = {"BB-CHIP": "CC", "BB-BIRR": "BR", "TU-COOK": "TC", "CC-CRUM": "CR", "EP-PITA": "EP"}

# scenario: key -> (sku, lot, product word, [bodies], [subjects])
SCENARIOS = {
    "plastic": dict(
        sku="BB-CHIP", lot="CC-2611-B", category="foreign_object",
        subjects=["Plastic in my Chipotle Chicken Bowl", "Found hard plastic in food", "Foreign object in frozen bowl", "Please read: plastic piece in dinner"],
        bodies=[
            "I was eating my Chipotle Chicken Bowl (lot {lot}) and bit into a hard piece of blue plastic. This is unacceptable. I bought it at {store}.",
            "Found a piece of clear plastic in the rice of my Chipotle Chicken Bowl. Lot code {lot}. Please tell me what you are doing about this.",
            "There was a fragment of hard plastic in my bowl, about the size of a fingernail. Lot {lot}. Very disappointed, I fed this to my kids.",
            "Chipotle Chicken Bowl, lot {lot}. Sharp plastic fragment in the chicken. I spat it out in time but someone could really get hurt.",
        ],
        critical_bodies=[
            "I bit down on something hard in my Chipotle Chicken Bowl (lot {lot}) and chipped a tooth. It was a piece of plastic. I need to see a dentist and want to know who is responsible.",
        ],
    ),
    "thawed": dict(
        sku="BB-BIRR", lot="BR-2611-A", category="cold_chain",
        subjects=["Birria bowl arrived thawed", "Frozen meal not frozen", "Leaking Birria Rice Bowl", "Ice crystals and soft food"],
        bodies=[
            "My Birria Rice Bowl was completely thawed when I got it home from {store}, with ice crystals all over the tray. Lot {lot}.",
            "The tray of the Birria Rice Bowl was leaking and the food was soft, not frozen. It looked like it had defrosted and been refrozen. Lot {lot}.",
            "Bought two Birria Rice Bowls at {store}. Both were thawed and there was liquid in the box. Lot code {lot}. I threw them away.",
            "Birria Rice Bowl arrived warm and the meat smelled a bit off. Lot {lot}. The freezer at {store} may not be working.",
        ],
        critical_bodies=[
            "I ate the Birria Rice Bowl (lot {lot}) even though it looked thawed and got sick afterwards, vomiting all night. I think it was spoiled.",
        ],
    ),
    "allergen": dict(
        sku="CC-CRUM", lot="CR-2611-A", category="allergen_labeling",
        subjects=["Allergic reaction to Cali Crumble cookie", "Undeclared tree nuts?", "Allergy and your label"],
        bodies=[
            "My son has a tree nut allergy. The Cali Crumble cookie (lot {lot}) did not list almonds on the label but he had a reaction after eating one. We went to urgent care.",
            "I am allergic to tree nuts and I bought your Cali Crumble cookies at {store}. I got hives after one cookie and the label does not mention almonds. Lot {lot}.",
            "Please check your labeling. I found chopped almonds in a Cali Crumble cookie, lot {lot}, and the package does not declare tree nuts. My daughter could have had anaphylaxis.",
        ],
        critical_bodies=[],
    ),
    "mold": dict(
        sku="TU-COOK", lot="TC-2610-C", category="spoilage_freshness",
        subjects=["Mold on Tuscany cookies", "Moldy cookies before best-by date", "Fuzzy mold in package"],
        bodies=[
            "I opened a box of Tuscany Gourmet Cookies (lot {lot}) and several cookies had green mold. The best-by date is still months away.",
            "Moldy Tuscany cookies, lot {lot}. White fuzzy spots on the bottom of the cookies, bought at {store}.",
            "Mold inside the sealed bag of Tuscany cookies. Lot {lot}. I want a refund and an explanation.",
        ],
        critical_bodies=[],
    ),
    "stale": dict(
        sku="EP-PITA", lot="EP-2611-A", category="spoilage_freshness",
        subjects=["Stale pita chips", "Pita chips taste rancid", "Chips were stale"],
        bodies=[
            "The Eat Pita Chips I bought at {store} were stale and tasted rancid even though they were well within the best-by date. Lot {lot}.",
            "Eat Pita Chips taste stale and chewy, like they were old. Lot {lot}. This is the second time.",
            "Opened a new bag of Eat Pita Chips and the smell was rancid. Lot {lot}.",
        ],
        critical_bodies=[],
    ),
    "crushed": dict(
        sku="EP-PITA", lot="", category="packaging_damage",
        subjects=["Bag of chips mostly crumbs", "Crushed chips", "Package arrived damaged"],
        bodies=[
            "The bag of Eat Pita Chips was mostly air and the chips were crushed to crumbs.",
            "My order of Eat Pita Chips arrived with the bag torn and half the chips crumbled.",
            "Tuscany cookies box was crushed and many cookies were broken when it arrived.",
        ],
        critical_bodies=[],
    ),
    "salty": dict(
        sku="BB-CHIP", lot="", category="taste_texture",
        subjects=["Too salty", "Texture issue", "Not as good as before", "Disappointing flavor"],
        bodies=[
            "The Chipotle Chicken Bowl was way too salty this time and the rice was mushy. Not as good as the last one.",
            "Birria Rice Bowl tasted bland and the meat was dry. Disappointing for the price.",
            "The Cali Crumble cookie was too sweet and had a strange bitter aftertaste.",
            "Rice in my bowl was rubbery and the sauce was greasy.",
        ],
        critical_bodies=[],
    ),
    "missing": dict(
        sku="BB-BIRR", lot="", category="missing_item",
        subjects=["Missing items in order", "Wrong item received", "Order was short"],
        bodies=[
            "I ordered four Birria Rice Bowls but only two were in the box. Order number {order}.",
            "I received Chipotle Chicken Bowls instead of the Birria Rice Bowls I ordered. Order {order}.",
            "My delivery was missing the cookies I paid for, order {order}.",
        ],
        critical_bodies=[],
    ),
    "shipping": dict(
        sku="TU-COOK", lot="", category="shipping_delivery",
        subjects=["Order still not here", "Late delivery", "Tracking has not updated"],
        bodies=[
            "My order {order} was supposed to arrive last Tuesday and tracking has not moved in six days. Still waiting.",
            "Delivery is very late, order {order}. The carrier says they cannot find my address.",
            "Order {order} was delayed twice and nobody told me. Please update me.",
        ],
        critical_bodies=[],
    ),
    "billing": dict(
        sku="TU-COOK", lot="", category="billing",
        subjects=["Charged twice", "Billing problem", "Duplicate charge on my card"],
        bodies=[
            "I was charged twice for order {order}. Please refund the duplicate payment on my credit card.",
            "My credit card shows a double charge for my cookie order {order}. Please fix this.",
            "I was overcharged on invoice {order}. Billing needs to correct this.",
        ],
        critical_bodies=[],
    ),
    "praise": dict(
        sku="BB-CHIP", lot="", category="praise_other",
        subjects=["Love your bowls", "Thank you", "Great product"],
        bodies=[
            "Just wanted to say the Chipotle Chicken Bowl is delicious. Thank you, where can I buy more?",
            "Love the Tuscany cookies! Wonderful taste, thank you for making them.",
            "Your Eat Pita Chips are great. Thank you!",
        ],
        critical_bodies=[],
    ),
}

# how many complaints per scenario and over which window (days ago: from, to)
PLAN = {
    "plastic": (13, (18, 0)), "thawed": (9, (14, 0)), "allergen": (3, (9, 1)), "mold": (5, (20, 2)),
    "stale": (6, (25, 0)), "crushed": (8, (40, 0)), "salty": (10, (40, 0)), "missing": (6, (40, 0)),
    "shipping": (8, (40, 0)), "billing": (5, (40, 0)), "praise": (6, (40, 0)),
}
CRITICAL_EXTRA = {"plastic": 1, "thawed": 1}


def _order_no(rng: random.Random) -> str:
    return f"SO-{rng.randint(10000, 99999)}"


def make_complaints(now: datetime, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    out: list[dict] = []
    for key, (n, (far, near)) in PLAN.items():
        sc = SCENARIOS[key]
        for i in range(n):
            ctx = {"lot": sc["lot"], "store": rng.choice(STORES), "order": _order_no(rng)}
            if i < CRITICAL_EXTRA.get(key, 0) and sc["critical_bodies"]:
                body = rng.choice(sc["critical_bodies"]).format(**ctx)
                days_ago = rng.uniform(near, max(near + 1, far / 2))
            else:
                body = rng.choice(sc["bodies"]).format(**ctx)
                days_ago = rng.uniform(near, far)
            f, l = rng.choice(FIRST), rng.choice(LAST)
            received = now - timedelta(days=days_ago, hours=rng.uniform(0, 8))
            out.append({
                "source": "email" if rng.random() < 0.55 else "web",
                "subject": rng.choice(sc["subjects"]),
                "body": body,
                "customer_name": f"{f} {l}",
                "customer_email": f"{f}.{l}@example.com".lower(),
                "received_at": received,
                "expected_category": sc["category"],
            })
    out.sort(key=lambda x: x["received_at"])
    return out


def make_live_complaint(rng: random.Random | None = None) -> dict:
    """One random complaint for the 'simulate incoming mail' button."""
    rng = rng or random.Random()
    key = rng.choices(list(SCENARIOS), weights=[3, 2, 1, 2, 2, 2, 3, 2, 2, 2, 1])[0]
    sc = SCENARIOS[key]
    ctx = {"lot": sc["lot"], "store": rng.choice(STORES), "order": _order_no(rng)}
    f, l = rng.choice(FIRST), rng.choice(LAST)
    pool = sc["bodies"] + (sc["critical_bodies"] if rng.random() < 0.15 else [])
    return {
        "source": "email" if rng.random() < 0.6 else "web",
        "subject": rng.choice(sc["subjects"]),
        "body": rng.choice(pool).format(**ctx),
        "customer_name": f"{f} {l}",
        "customer_email": f"{f}.{l}@example.com".lower(),
    }

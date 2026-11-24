"""Hand-written, labeled evaluation set (independent from the synthetic data generator).

Each case: (text, expected_category, must_be_critical)
Run:  python -m evals.run_eval            (uses Claude if ANTHROPIC_API_KEY is set, else the heuristic)
"""
CASES = [
    ("Found a small piece of metal wire in my frozen bowl. Lot AB-2610-A.", "foreign_object", True),
    ("There was a hard piece of plastic in the sauce, almost swallowed it.", "foreign_object", False),
    ("A shard of glass was in the cookie box. My kid was bleeding from the mouth.", "foreign_object", True),
    ("I got hives and my throat swelled after your cookies. The label never mentions sesame.", "allergen_labeling", True),
    ("Your package does not list almonds but there are almonds inside. My wife is allergic to nuts.", "allergen_labeling", True),
    ("The cookies have mold, green fuzzy spots, best-by is next year.", "spoilage_freshness", False),
    ("The chips smelled rancid and tasted stale right out of the bag.", "spoilage_freshness", False),
    ("Arrived completely thawed with ice crystals and a leaking tray.", "cold_chain", False),
    ("The frozen meal was not frozen when I bought it, melted and soft.", "cold_chain", False),
    ("Way too salty and the rice was mushy, will not buy again.", "taste_texture", False),
    ("Chicken was dry and the sauce was bland and greasy.", "taste_texture", False),
    ("The bag was mostly air and the chips were crushed into crumbs.", "packaging_damage", False),
    ("Box arrived torn and half the cookies were broken.", "packaging_damage", False),
    ("I ordered four bowls but only two were in the box, the rest missing.", "missing_item", False),
    ("You sent the wrong flavor, I asked for birria and got chipotle.", "missing_item", False),
    ("My order is very late and tracking has not updated in a week.", "shipping_delivery", False),
    ("The courier left the package at the wrong address and it never arrived.", "shipping_delivery", False),
    ("I was charged twice for the same order, please refund the duplicate payment.", "billing", False),
    ("The invoice amount is wrong, I was overcharged on my credit card.", "billing", False),
    ("Love your bowls! Delicious, thank you, where can I buy more?", "praise_other", False),
    ("I ate it and vomited all night, I think the meal was spoiled and I am going to see a doctor.", None, True),
    ("After eating the cookie my lips swelled and we went to the emergency room. Possible allergy.", "allergen_labeling", True),
    ("I bit into something hard and chipped a tooth, looks like a plastic fragment.", "foreign_object", True),
    ("My son choked on a piece of hard plastic from the bowl.", "foreign_object", True),
]

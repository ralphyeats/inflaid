"""
Category configuration registry.

Adding a new category = add one entry to CATEGORY_CONFIG.
Each category defines its niche keywords and factor weights.
"""

CATEGORY_CONFIG: dict = {
    "beauty": {
        "keywords": [
            "skincare", "makeup", "beauty", "skin", "glow", "routine", "serum",
            "moisturizer", "foundation", "lipstick", "hair", "cosmetic", "fashion",
            "style", "makyaj", "guzellik", "cilt", "ruj", "fondoten", "kirpik",
            "макияж", "красота", "уход", "косметика", "beaute", "maquillage",
            "belleza", "maquillaje",
        ],
        "factor_weights": {
            "engagement":   0.30,
            "rhythm":       0.20,
            "audience":     0.20,
            "niche":        0.15,
            "authenticity": 0.10,
            "momentum":     0.05,
        },
    },
    # Future categories — add entry here when ready:
    # "fashion": {
    #     "keywords": ["outfit", "ootd", "style", "clothing", "fashion", "wear", ...],
    #     "factor_weights": {"engagement": 0.30, "rhythm": 0.20, ...},
    # },
    # "food": {
    #     "keywords": ["recipe", "food", "cook", "restaurant", "eat", "yemek", ...],
    #     "factor_weights": {"engagement": 0.30, "rhythm": 0.15, ...},
    # },
}

# Sub-categories that map to a parent category for scoring purposes
SUBCATEGORY_MAP: dict = {
    "skincare":  "beauty",
    "makeup":    "beauty",
    "haircare":  "beauty",
    "fragrance": "beauty",
}


def get_category_config(category: str) -> dict:
    """
    Return config for the given category.
    Sub-categories (skincare, makeup …) resolve to their parent.
    Unknown categories fall back to 'beauty'.
    """
    resolved = SUBCATEGORY_MAP.get(category, category)
    return CATEGORY_CONFIG.get(resolved, CATEGORY_CONFIG["beauty"])

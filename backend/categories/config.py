"""
Category configuration registry.

Adding a new category = add one entry to CATEGORY_CONFIG.
Each category defines its niche keywords and factor weights.
"""

CATEGORY_CONFIG: dict = {
    "beauty": {
        "keywords": [
            # English — product types
            "skincare", "makeup", "beauty", "skin", "glow", "routine", "serum",
            "moisturizer", "foundation", "lipstick", "hair", "cosmetic", "blush",
            "bronzer", "highlighter", "concealer", "eyeliner", "mascara", "eyeshadow",
            "contour", "primer", "toner", "sunscreen", "spf", "retinol", "niacinamide",
            "perfume", "fragrance", "deodorant", "shampoo", "conditioner", "haircare",
            "nail", "lash", "brow", "lip", "bb cream", "cc cream", "face wash",
            "exfoliant", "peeling", "face mask", "sheet mask", "eye cream",
            # English — content formats
            "grwm", "get ready with me", "tutorial", "haul", "unboxing", "review",
            "ootd", "look", "transformation", "skincare routine", "night routine",
            "morning routine", "self care", "selfcare",
            # Turkish — product types
            "makyaj", "guzellik", "güzellik", "cilt", "ruj", "fondoten", "kirpik",
            "allık", "allik", "bronzer", "kaş", "kas", "göz", "goz", "pudra",
            "eyeliner", "maskara", "kontür", "kontur", "astar", "toner", "nemlendirici",
            "yüz yıkama", "yuz yikama", "peeling", "maske", "göz kremi", "goz kremi",
            "güneş kremi", "gunes kremi", "spf", "serum", "parfüm", "parfum",
            "deodorant", "şampuan", "sampuan", "saç bakım", "sac bakim", "oje",
            "dudak", "kaş kalemi", "rimel", "bb krem", "cc krem", "highlighter",
            # Turkish — content formats
            "bakım rutini", "bakim rutini", "gece rutini", "sabah rutini",
            "inceleme", "deneme", "kutu açılımı", "kutu acilimi", "önce sonra",
            "once sonra", "makyaj tutorial", "cilt bakım", "cilt bakim",
            # Russian
            "макияж", "красота", "уход", "косметика", "помада", "тональный",
            "тушь", "тени", "румяна", "хайлайтер", "сыворотка", "увлажняющий",
            # French / Spanish
            "beaute", "beauté", "maquillage", "soin", "routine beaute",
            "belleza", "maquillaje", "cuidado", "labial", "rutina",
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

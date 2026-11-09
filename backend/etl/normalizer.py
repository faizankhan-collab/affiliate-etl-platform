"""Brand and Network Normalizer module.
Provides alias matching, string sanitization, and canonical mapping for affiliate brands and networks.
"""

import re
from typing import Dict, List, Optional, Tuple


DEFAULT_CANONICAL_BRANDS: List[str] = [
    "Amazon",
    "Amazon US",
    "Amazon UK",
    "Flipkart",
    "Myntra",
    "Ajio",
    "Ajio Lux",
    "TatacliQ",
    "Reliance Digital",
    "Vijay Sales",
    "Nykaa",
    "NykaaFashion",
    "firstcry",
    "Shopsy",
    "1mg",
    "Netmeds",
    "Croma",
    "Pharmeasy",
    "Samsung",
    "PepperFry",
    "H&M",
    "asus",
    "Puma",
    "lenovo",
    "fnp.com",
    "Decathlon",
    "Truemeds",
    "ShopClues",
    "Newegg",
    "Adidas",
    "Bestbuy",
    "kindlife",
    "Snitch",
    "acer",
    "Healthkart",
    "AirIndia",
    "oneplus",
    "Aliexpress",
    "Campus Shoes",
    "IGP.com",
    "Levis India",
    "hp",
    "cashify",
    "healthxp",
    "Fastrack",
    "Boat Lifestyle",
    "Moglix",
    "Sangeetha Mobiles",
    "UrbanLadder",
    "macys",
    "Shein USA",
    "The Bear House",
    "Timex",
    "Libas",
    "HyugaLife",
    "Bewakoof",
    "jackjones",
    "gonoise",
    "Crocs",
    "Clovia",
    "Milton",
    "Jockey India",
    "Oppo",
    "Dell",
    "Chumbak",
    "Dailyobjects",
    "Dot and Key",
    "Mokobara",
    "Neemans",
    "Plum Goodness",
    "NOBERO",
    "MuscleBlaze",
    "LifeLong India",
    "Dermaco",
    "Sharafdg.uae",
    "mivi.in",
    "Makemytrip",
    "Goibibo",
    "tripadvisor",
    "Tanishq",
    "Chewy",
    "Veromoda",
    "Manmatters",
    "Wforwoman",
    "Palmonas",
    "zebronics",
    "forestessentialsindia",
    "Wonderchef",
    "Kapiva",
    "sochstore",
    "mcaffeine",
    "biba",
    "Walmart",
    "Realme",
    "Foxtale",
    "Blackberrys",
    "Dyson",
    "Beyoung",
    "Marks and Spencer",
    "Tecsox",
    "Kerala Ayurveda",
    "HK Vitals",
    "Hammer",
    "Aldo",
    "Sapna Online",
    "Jivisa",
    "Cleartrip",
    "zanducare",
    "uniqlo",
    "Expedia",
    "klook",
    "Oyo Rooms",
    "Walmart Canada",
]

DEFAULT_BRAND_ALIASES: Dict[str, str] = {
    # Amazon variants
    "amazon us": "Amazon US",
    "amazon.com": "Amazon US",
    "amazon usa": "Amazon US",
    "amazon in": "Amazon",
    "amazon.in": "Amazon",
    "amazon india": "Amazon",
    "amazon associates": "Amazon",
    "amazon": "Amazon",
    "amazon uk": "Amazon UK",
    # Flipkart variants
    "flipkart cps": "Flipkart",
    "flipkart [in]": "Flipkart",
    "flipkart india": "Flipkart",
    "flipkart cpa": "Flipkart",
    "flipkart app": "Flipkart",
    "flipkart": "Flipkart",
    # Myntra variants
    "myntra cps": "Myntra",
    "myntra [in]": "Myntra",
    "myntra india": "Myntra",
    "myntra fashion": "Myntra",
    "myntra": "Myntra",
    # Ajio variants
    "ajio lux": "Ajio Lux",
    "ajio luxe": "Ajio Lux",
    "ajio luxury": "Ajio Lux",
    "ajio cps": "Ajio",
    "ajio [in]": "Ajio",
    "ajio india": "Ajio",
    "ajio online": "Ajio",
    "ajio": "Ajio",
    # TatacliQ variants
    "tata cliq": "TatacliQ",
    "tatacliq": "TatacliQ",
    "tata cliq cps": "TatacliQ",
    "tata cliq luxury": "TatacliQ",
    "tatacliq [in]": "TatacliQ",
    # Reliance Digital
    "reliance digital": "Reliance Digital",
    "reliancedigital": "Reliance Digital",
    "reliance digital cps": "Reliance Digital",
    # Vijay Sales
    "vijay sales": "Vijay Sales",
    "vijaysales": "Vijay Sales",
    "vijay sales cps": "Vijay Sales",
    # Campus Shoes
    "campus": "Campus Shoes",
    "campus shoes": "Campus Shoes",
    "campus shoes cps": "Campus Shoes",
    # INRDeals brand variants
    "man matters": "Manmatters",
    "manmatters": "Manmatters",
    "dyson india": "Dyson",
    "dyson": "Dyson",
    "soch": "sochstore",
    "soch store": "sochstore",
    "sochstore": "sochstore",
    "hammer": "Hammer",
    "aldo": "Aldo",
    "chumbak": "Chumbak",
    "h&m": "H&M",
    "hm": "H&M",
    # JioMart
    "jiomart": "JioMart",
    "jio mart": "JioMart",
    # Boat
    "boat": "Boat Lifestyle",
    "boat cps": "Boat Lifestyle",
    "boat lifestyle": "Boat Lifestyle",
    "boatlifestyle": "Boat Lifestyle",
    # Dermaco
    "the derma co": "Dermaco",
    "the dermaco": "Dermaco",
    "derma co": "Dermaco",
    "dermaco": "Dermaco",
    "the derma company": "Dermaco",
    # Nykaa & NykaaFashion
    "nykaa fashion": "NykaaFashion",
    "nykaafashion": "NykaaFashion",
    "nykaa fashion cps": "NykaaFashion",
    "nykaa": "Nykaa",
    "nykaa cps": "Nykaa",
    "nykaa beauty": "Nykaa",
    # Firstcry
    "firstcry": "firstcry",
    "first cry": "firstcry",
    "firstcry cps": "firstcry",
    "firstcry [in]": "firstcry",
    # Shopsy
    "shopsy": "Shopsy",
    "shopsy by flipkart": "Shopsy",
    "shopsy cps": "Shopsy",
    # Cuelinks variants from real campaign reports
    "airindia": "AirIndia",
    "air india": "AirIndia",
    "air india express": "AirIndia",
    "airindia cps": "AirIndia",
    "aliexpress": "Aliexpress",
    "ali express": "Aliexpress",
    "aliexpress us": "Aliexpress",
    "levis": "Levis India",
    "levis india": "Levis India",
    "levi's": "Levis India",
    "macy": "macys",
    "macys": "macys",
    "macy's": "macys",
    "jockey": "Jockey India",
    "jockey india": "Jockey India",
    "plum goodness": "Plum Goodness",
    "tanishq": "Tanishq",
    "palmonas": "Palmonas",
    "kapiva": "Kapiva",
    "kindlife": "kindlife",
    "moglix": "Moglix",
    "crocs": "Crocs",
    "timex": "Timex",
    "asus": "asus",
    "decathlon": "Decathlon",
    "healthxp": "healthxp",
    "newegg": "Newegg",
    "fastrack": "Fastrack",
    "the bear house": "The Bear House",
    "milton": "Milton",
    "lifelong": "LifeLong India",
    "lifelong india": "LifeLong India",
    "jack & jones": "jackjones",
    "jackjones": "jackjones",
    "gonoise": "gonoise",
    "vero moda": "Veromoda",
    "veromoda": "Veromoda",
    "wforwoman": "Wforwoman",
    "biba": "biba",
    "blackberrys": "Blackberrys",
    "chewy": "Chewy",
    "marks and spencer": "Marks and Spencer",
    "adidas (in)": "Adidas",
    "adidas": "Adidas",
    "shein": "Shein USA",
    "shein usa": "Shein USA",
    "acer": "acer",
    "bewakoof": "Bewakoof",
    "sangeetha mobile": "Sangeetha Mobiles",
    "sangeetha mobiles": "Sangeetha Mobiles",
    "dot&key": "Dot and Key",
    "dot and key": "Dot and Key",
    "dot & key": "Dot and Key",
    "lenovo india": "lenovo",
    "lenovo": "lenovo",
    "uniqlo india": "uniqlo",
    "uniqlo": "uniqlo",
    "oneplus": "oneplus",
    "one plus": "oneplus",
    "mivi": "mivi.in",
    "mivi.in": "mivi.in",
    "forest essentials": "forestessentialsindia",
    "forest essentials india": "forestessentialsindia",
    "forestessentialsindia": "forestessentialsindia",
    "ctrl8": "CTRL8",
    "croma": "Croma",
    "realme": "Realme",
    "puma": "Puma",
    "libas": "Libas",
    "samsung": "Samsung",
    # Cashkaro variants from real performance reports
    "hyugalife": "HyugaLife",
    "hyuga life": "HyugaLife",
    "daily objects": "Dailyobjects",
    "dailyobjects": "Dailyobjects",
    "mcaffeine": "mcaffeine",
    "m caffeine": "mcaffeine",
    "healthkart": "Healthkart",
    "health kart": "Healthkart",
    "shopclues": "ShopClues",
    "shop clues": "ShopClues",
    "neemans": "Neemans",
    "neeman's": "Neemans",
    "muscleblaze": "MuscleBlaze",
    "muscle blaze": "MuscleBlaze",
    "cleartrip": "Cleartrip",
    "clear trip": "Cleartrip",
    "beyoung": "Beyoung",
    "be young": "Beyoung",
    "goibibo hotels": "Goibibo",
    "goibibo": "Goibibo",
    "makemytrip hotels": "Makemytrip",
    "makemytrip": "Makemytrip",
    "pharmeasy diagnostics": "Pharmeasy",
    "pharmeasy": "Pharmeasy",
    "netmeds": "Netmeds",
    "truemeds": "Truemeds",
    "clovia": "Clovia",
    "jivisa": "Jivisa",
    "kerala ayurveda": "Kerala Ayurveda",
    "oppo": "Oppo",
    "wonderchef": "Wonderchef",
    # CJ (Commission Junction) Brand Variants
    "sharaf dg_mena": "Sharafdg.uae",
    "sharaf dg": "Sharafdg.uae",
    "sharafdg": "Sharafdg.uae",
    "sharafdg.uae": "Sharafdg.uae",
    "sharaf dg mena": "Sharafdg.uae",
    "dell consumer - india": "Dell",
    "dell consumer india": "Dell",
    "dell consumer": "Dell",
    "dell": "Dell",
    "hp india": "hp",
}

DEFAULT_NETWORK_ALIASES: Dict[str, str] = {
    "cuelinks": "cuelinks",
    "cue links": "cuelinks",
    "admitad": "admitad",
    "cashkaro": "cashkaro",
    "cash karo": "cashkaro",
    "zonet": "zonet",
    "zonet media": "zonet",
    "icubeswire": "icubeswire",
    "icubes wire": "icubeswire",
    "icubes": "icubeswire",
    "adgama": "adgama",
    "affinity": "affinity",
    "pantech": "Pantech",
    "digimodo": "digimodo",
    "extrape": "extrape",
    "inr deals": "INR Deals",
    "inrdeals": "INR Deals",
    "yieldkit": "Yieldkit",
    "analytics cloud": "Analytics Cloud",
    "cj": "cj",
    "commission junction": "cj",
    "cj affiliate": "cj",
    "cj.com": "cj",
    "v commission": "V Commission",
    "vcommission": "V Commission",
    "special (own)": "Special (OWN)",
    "special (extra1)": "Special (Extra1)",
    "special own": "Special (OWN)",
    "special extra1": "Special (Extra1)",
}


class BrandNormalizer:
    def __init__(
        self,
        custom_aliases: Optional[Dict[str, str]] = None,
        canonical_brands: Optional[List[str]] = None,
    ):
        self.aliases: Dict[str, str] = {**DEFAULT_BRAND_ALIASES}
        if custom_aliases:
            for k, v in custom_aliases.items():
                self.aliases[k.strip().lower()] = v.strip()

        self.canonical_brands = canonical_brands or list(DEFAULT_CANONICAL_BRANDS)
        self.network_aliases = {**DEFAULT_NETWORK_ALIASES}

    @staticmethod
    def clean_text(raw_name: str) -> str:
        """Sanitize raw campaign/merchant name for matching."""
        if not raw_name or not isinstance(raw_name, str):
            return ""
        s = raw_name.lower().strip()
        s = re.sub(r"\[.*?\]", " ", s)
        s = re.sub(r"\(.*?\)", " ", s)
        noise = [
            r"\bcps\b",
            r"\bcpa\b",
            r"\bcpc\b",
            r"\bcpl\b",
            r"\baffiliate\b",
            r"\bcampaign\b",
            r"\bprogram\b",
            r"\boffer\b",
            r"\bindia\b",
            r"\bonline\b",
            r"\bdot com\b",
            r"\bcom\b",
            r"\bin\b",
        ]
        for pattern in noise:
            s = re.sub(pattern, " ", s)
        s = re.sub(r"[_\-/\\]", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def normalize_brand(self, raw_name: str) -> Tuple[str, bool]:
        """
        Normalize a raw brand/merchant string into a canonical brand name.
        Returns: (normalized_name, is_matched_flag)
        """
        if not raw_name or not isinstance(raw_name, str):
            return "Unknown", False

        raw_trimmed = raw_name.strip()
        raw_lower = raw_trimmed.lower()

        # 0. Skip summary/footer rows
        if raw_lower in ["total", "totals", "avg", "average", "summary"]:
            return "TOTAL_SKIP", False

        # 1. Direct exact alias match
        if raw_lower in self.aliases:
            return self.aliases[raw_lower], True

        # 2. Cleaned string match
        cleaned = self.clean_text(raw_name)
        if cleaned in self.aliases:
            return self.aliases[cleaned], True

        # 3. Check specific compound brands before single-word brands
        priority_checks = [
            (r"\bamazon\s*(?:us|usa|\.com)\b", "Amazon US"),
            (r"\bamazon\s*(?:uk|\.co\.uk)\b", "Amazon UK"),
            (r"\bajio\s*(?:lux|luxe|luxury)\b", "Ajio Lux"),
            (r"\bnykaa\s*fashion\b", "NykaaFashion"),
            (r"\bshopsy\b", "Shopsy"),
            (r"\btata\s*cliq\b", "TatacliQ"),
            (r"\breliance\s*digital\b", "Reliance Digital"),
            (r"\bvijay\s*sales\b", "Vijay Sales"),
            (r"\bfirst\s*cry\b", "firstcry"),
            (r"\bfirstcry\b", "firstcry"),
            (r"\bflipkart\b", "Flipkart"),
            (r"\bmyntra\b", "Myntra"),
            (r"\bajio\b", "Ajio"),
            (r"\bamazon\b", "Amazon"),
            (r"\bnykaa\b", "Nykaa"),
            (r"\bair\s*india\b", "AirIndia"),
            (r"\blevis\b", "Levis India"),
            (r"\bjockey\b", "Jockey India"),
            (r"\bmacy\b", "macys"),
            (r"\bhyuga\s*life\b", "HyugaLife"),
            (r"\bdaily\s*objects\b", "Dailyobjects"),
            (r"\bmcaffeine\b", "mcaffeine"),
            (r"\bshop\s*clues\b", "ShopClues"),
            (r"\bhealth\s*kart\b", "Healthkart"),
            (r"\bbe\s*young\b", "Beyoung"),
            (r"\bgoibibo\b", "Goibibo"),
            (r"\bmakemytrip\b", "Makemytrip"),
            (r"\bpharmeasy\b", "Pharmeasy"),
            (r"\bmuscle\s*blaze\b", "MuscleBlaze"),
            (r"\bcleartrip\b", "Cleartrip"),
            (r"\bkindlife\b", "kindlife"),
            (r"\baliexpress\b", "Aliexpress"),
            (r"\bdecathlon\b", "Decathlon"),
            (r"\bpalmonas\b", "Palmonas"),
            (r"\bkapiva\b", "Kapiva"),
            (r"\bmoglix\b", "Moglix"),
            (r"\btimex\b", "Timex"),
            (r"\basus\b", "asus"),
            (r"\bcrocs\b", "Crocs"),
            (r"\bplum\s*goodness\b", "Plum Goodness"),
            (r"\blifelong\b", "LifeLong India"),
            (r"\bjack\s*&\s*jones\b", "jackjones"),
            (r"\bsangeetha\b", "Sangeetha Mobiles"),
            (r"\bshein\b", "Shein USA"),
            (r"\bnewegg\b", "Newegg"),
            (r"\bfastrack\b", "Fastrack"),
            (r"\bmilton\b", "Milton"),
            (r"\bbewakoof\b", "Bewakoof"),
            (r"\bchewy\b", "Chewy"),
            (r"\bblackberrys\b", "Blackberrys"),
            (r"\bbiba\b", "biba"),
            (r"\bwforwoman\b", "Wforwoman"),
            (r"\bvero\s*moda\b", "Veromoda"),
            (r"\bthe\s*bear\s*house\b", "The Bear House"),
        ]
        for pattern, canonical in priority_checks:
            if re.search(pattern, raw_lower) or re.search(pattern, cleaned):
                return canonical, True

        # 4. Check canonical brands directly
        for canonical in self.canonical_brands:
            if canonical.lower() == raw_lower or canonical.lower() == cleaned:
                return canonical, True

        # Check without spaces
        raw_nospace = re.sub(r"\s+", "", raw_lower)
        for canonical in self.canonical_brands:
            can_nospace = re.sub(r"\s+", "", canonical.lower())
            if can_nospace == raw_nospace:
                return canonical, True

        return raw_trimmed, False

    def normalize_network(self, raw_network: str) -> str:
        """Normalize network name to match master sheet conventions."""
        if not raw_network or not isinstance(raw_network, str):
            return "Unknown"
        s = raw_network.strip().lower()
        if s in self.network_aliases:
            return self.network_aliases[s]

        for key, val in self.network_aliases.items():
            if key == s or key in s:
                return val
        return raw_network.strip()

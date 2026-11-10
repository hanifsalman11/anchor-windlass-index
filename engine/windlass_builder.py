import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/anchor-windlass-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2").strip()
CUSTOM_WINDLASS = os.environ.get("CUSTOM_WINDLASS", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_windlasses.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

_CACHED_MODELS = None

# Format: (Model / Boat Scenario, Boat LOA Ft, Anchor Weight Lbs, Windlass Max Pull Lbs, Gypsy Chain/Rope Spec, Motor Watts 12V, Storm Load Lbs)
SEED_WINDLASSES = [
    ("Lewmar Pro-Series 700 & Pro-Fish 700 (20–28 Ft Boats)", 26, 22, 700, "1/4\" G43 Chain + 1/2\" 3-Strand/8-Plait", 500, 1450),
    ("Lewmar Pro-Series 1000 & Pro-Fish 1000 (28–38 Ft Boats)", 33, 33, 1000, "5/16\" G43 Chain + 9/16\" 8-Plait Nylon", 700, 2400),
    ("Lewmar VX1 / V700 Vertical Stainless Windlass (22–32 Ft)", 28, 25, 700, "1/4\" G43 / 6mm DIN766 + 1/2\" Rode", 500, 1750),
    ("Lewmar V1 / V2 / V3 Vertical Windlass (35–48 Ft Cruisers)", 40, 44, 1500, "5/16\" G43 Chain + 5/8\" 8-Plait Nylon", 1000, 3400),
    ("Lewmar H2 & H3 Horizontal Gypsy/Capstan Windlass (38–50 Ft)", 44, 55, 1900, "3/8\" G43 Chain + 5/8\" Nylon Rode", 1200, 4100),
    ("Maxwell RC8-6 & RC8-8 Automatic Rope/Chain Windlass", 32, 33, 1100, "5/16\" G43 Chain + 9/16\" 8-Plait Nylon", 1000, 2250),
    ("Maxwell RC6 Vertical Stainless Windlass (20–28 Ft Boats)", 25, 20, 770, "1/4\" G43 Chain + 1/2\" 8-Plait Nylon", 500, 1380),
    ("MaxwellHRC10-8 & HRC10-10 Horizontal All-Chain Windlass", 42, 48, 1540, "5/16\" or 3/8\" G43 High-Test Chain", 1200, 3600),
    ("Good F850A & AFD500 Free-Fall Automatic Rope/Chain Windlass", 30, 28, 900, "1/4\" G43 Chain + 1/2\" Twisted Nylon", 650, 2050),
    ("Quick Prince DP2 & Genius GP2 800W/1000W Marine Windlass", 34, 33, 1150, "5/16\" G43 Chain + 9/16\" 3-Strand", 800, 2500),
    ("Lofrans Project 1000 & Tigres 1500W Cruising Sailboat Windlass", 42, 55, 1650, "3/8\" G43 / BBB Galvanized Chain", 1500, 3700),
    ("Powerwinch 31' & 36' Class Free-Fall Electric Anchor Winch", 24, 18, 650, "1/2\" Braided Nylon + 15ft 1/4\" Chain", 450, 1250),
    ("Trac Outdoor Fisherman 25 & Pontoon 35 Electric Anchor Winch", 20, 15, 350, "3/16\" Braided Anchor Line (100ft)", 200, 850),
    ("Minn Kota DeckHand 40 Pontoon & Fishing Boat Anchor Winch", 21, 20, 400, "100ft Pre-Spooled 800-lb Nylon Cord", 240, 950),
    ("Rocna Original & Vulcan 15 kg (33 Lb) Anchor + Windlass Sizing", 34, 33, 1000, "5/16\" G43 Chain + 9/16\" Nylon Rode", 700, 2500),
    ("Rocna 10 kg (22 Lb) vs 20 kg (44 Lb) Boat Anchor Sizing", 30, 22, 850, "1/4\" or 5/16\" G43 Chain + 1/2\" Rode", 600, 1950),
    ("Mantus M1 & M2 (25 Lb / 35 Lb / 45 Lb) Roll-Bar Anchor Sizing", 35, 35, 1100, "5/16\" G43 Chain + 9/16\" 8-Plait", 800, 2650),
    ("Lewmar Delta (14 Lb / 22 Lb / 35 Lb) Plow Anchor Sizing", 32, 22, 1000, "5/16\" G43 Chain + 9/16\" Nylon Rode", 700, 2200),
    ("Lewmar Claw / Bruce Style (16.5 Lb / 22 Lb / 33 Lb) Sizing", 29, 22, 800, "1/4\" G43 Chain + 1/2\" 3-Strand", 600, 1850),
    ("Fortress FX-11, FX-16 & FX-23 Aluminum Fluke Anchor Sizing", 33, 21, 900, "5/16\" G43 Chain + 1/2\" Nylon Rode", 700, 2300),
    ("Ultra Marine & Manson Supreme Stainless Bow Anchor Sizing", 38, 45, 1350, "5/16\" G43 Chain + 5/8\" 8-Plait", 1000, 3100),
    ("22-Foot Center Console & Bay Boat Anchor & Windlass Sizing", 22, 16, 650, "1/4\" G43 Chain + 1/2\" Nylon Rode", 450, 1100),
    ("26-Foot Offshore Center Console Free-Fall Windlass Sizing", 26, 22, 700, "1/4\" G43 Chain + 1/2\" 8-Plait Nylon", 500, 1500),
    ("30-Foot Express Cruiser & Walkaround Anchor & Windlass", 30, 28, 1000, "5/16\" G43 Chain + 9/16\" 8-Plait", 700, 2100),
    ("36-Foot Cruising Sailboat & Trawler Anchor & Windlass", 36, 44, 1250, "5/16\" G43 Chain + 5/8\" 8-Plait", 1000, 2850),
    ("42-Foot Catamaran & Flybridge Yacht Windlass & Chain Sizing", 42, 55, 1650, "3/8\" G43 High-Test All-Chain Rode", 1200, 3900),
    ("50-Foot Offshore Motor Yacht & Sailboat Windlass Sizing", 50, 73, 2200, "3/8\" G43 High-Test All-Chain Rode", 1500, 5200),
    ("1/4-Inch vs 5/16-Inch vs 3/8-Inch G43 High-Test Anchor Chain", 34, 33, 1000, "5/16\" G43 ISO Calibrated Chain", 700, 2400),
    ("5:1 vs 7:1 vs 10:1 Anchor Rode Scope Length & Depth Chart", 32, 28, 1000, "5/16\" G43 Chain + 9/16\" Nylon Rode", 700, 2200),
    ("12V Windlass Bow Battery Cable Gauge (2 AWG / 1/0 AWG) & Breaker", 34, 33, 1000, "5/16\" G43 + 80A Thermal Breaker", 800, 2400)
]


def load_json(filepath, default):
    """Self-healing JSON loader: otomatis pulih jika file korup atau kosong."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, type(default)) else default
        except Exception as e:
            print(f"[SELF-HEAL] Recovering {filepath} due to read notice: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=30.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def get_active_gemini_model(api_key):
    """
    LAPIS 1: Mesin Pemindai Versi Otomatis berbasis Regex tanpa angka versi manual.
    Otomatis mendeteksi model Gemini Flash STABIL generasi tertinggi lintas tahun.
    """
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def discover_google_windlass_queries(published_slugs):
    """
    LAPIS 4: 3-Tier Infinite Keyword Supply:
    Tier A: Seed List -> Tier B: Google Suggest US -> Tier C: Combinatorial Boat LOA × Depth × Scope Permutator.
    """
    discovered = []
    seeds = [
        "what size anchor for ",
        "what size windlass for ",
        "lewmar pro fish ",
        "rocna anchor size for "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "what size" in pref or "for " in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        ft_m = re.search(r"\b(20|22|24|25|26|28|30|32|34|36|38|40|42|45|50)\b", cleaned)
                        loa_v = int(ft_m.group(1)) if ft_m else 32
                        anch_v = 22 if loa_v <= 28 else (33 if loa_v <= 36 else 44)
                        pull_v = 700 if loa_v <= 28 else (1000 if loa_v <= 36 else 1500)
                        ch_s = "1/4\" G43 Chain + 1/2\" Rode" if loa_v <= 28 else "5/16\" G43 Chain + 9/16\" Rode"
                        discovered.append((cleaned.title(), loa_v, anch_v, pull_v, ch_s, 700, loa_v * 70))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")

    # Tier C Fallback: Combinatorial Permutator (Anti-Habis Lintas Tahun)
    boat_classes = [
        (22, 16, 650, "22-Ft Center Console", "1/4\" G43 Chain + 1/2\" Nylon", 450, 1100),
        (25, 22, 700, "25-Ft Walkaround / Pilothouse", "1/4\" G43 Chain + 1/2\" Nylon", 500, 1400),
        (28, 25, 850, "28-Ft Offshore Fishing Boat", "1/4\" G43 Chain + 1/2\" 8-Plait", 600, 1750),
        (32, 33, 1000, "32-Ft Express Cruiser / Sailboat", "5/16\" G43 Chain + 9/16\" 8-Plait", 700, 2250),
        (36, 44, 1250, "36-Ft Trawler / Monohull Sailboat", "5/16\" G43 Chain + 5/8\" 8-Plait", 1000, 2850),
        (40, 48, 1500, "40-Ft Cruising Catamaran / Yacht", "3/8\" G43 Chain + 5/8\" 8-Plait", 1200, 3500),
        (45, 55, 1750, "45-Ft Offshore Motor Yacht", "3/8\" G43 High-Test Chain", 1500, 4300)
    ]
    anchoring_depths = [
        (15, "15-Ft Coastal Anchorage"),
        (25, "25-Ft Bay & Reef Depth"),
        (40, "40-Ft Deep-Water Wreck/Cove"),
        (60, "60-Ft Offshore Shelf Depth")
    ]
    for b_loa, a_lbs, p_lbs, b_desc, g_spec, m_w, st_lbs in boat_classes:
        for d_ft, d_desc in anchoring_depths:
            combo_title = f"{b_desc} Anchoring in {d_desc}"
            test_slug = slugify(f"{combo_title}-windlass-rode-calculator")
            if test_slug not in published_slugs:
                discovered.append((combo_title, b_loa, a_lbs, p_lbs, g_spec, m_w, st_lbs))
                if len(discovered) >= 25:
                    return discovered
    return discovered


def build_deterministic_windlass_data(wnd_tuple):
    """
    LAPIS 3: Mesin Fisika ABYC H-40 Windage, 3x Ground Tackle Windlass Pull & 7:1 Rode Scope (100% Bebas Gagal).
    """
    model_name, boat_loa_ft, anchor_lbs, max_pull_lbs, gypsy_spec, motor_watts, storm_load_lbs = wnd_tuple

    # 1. Perhitungan Panjang Rode (7:1 Scope untuk Overnight / Cruising & 5:1 untuk Lunch Hook):
    # Asumsi kedalaman standar 25 kaki + 4 kaki tinggi haluan (Bow Freeboard) = 29 kaki vertikal
    std_depth_ft = 25
    bow_height_ft = 4 if boat_loa_ft <= 34 else 5
    total_vertical_ft = std_depth_ft + bow_height_ft
    rode_5_to_1_ft = total_vertical_ft * 5
    rode_7_to_1_ft = total_vertical_ft * 7

    # 2. Perhitungan Berat Ground Tackle (Anchor + Chain + Rope + Swivel):
    # Rantai 1/4" G43 = 0.72 lb/ft; 5/16" G43 = 1.10 lb/ft; 3/8" G43 = 1.56 lb/ft
    chain_lb_per_ft = 0.72 if "1/4" in gypsy_spec else (1.56 if "3/8" in gypsy_spec else 1.10)
    # Asumsi 50 ft rantai + 150 ft tali nilon (atau rantai penuh di kedalaman 45 ft)
    hanging_tackle_lbs = int(round(anchor_lbs + (45.0 * chain_lb_per_ft) + 18.0))
    # Aturan Industri ABYC / Lewmar / Maxwell:
    # Working Load Limit (WLL) = ~1/3 dari Max Pull; Max Pull harus >= 3x hingga 4x Total Hanging Ground Tackle Weight
    min_required_max_pull_lbs = int(round(hanging_tackle_lbs * 3.5, -1))
    recommended_windlass_pull = max(max_pull_lbs, min_required_max_pull_lbs)
    working_load_limit_lbs = int(round(recommended_windlass_pull / 3.0, -1))

    # 3. Kelistrikan 12V DC Windlass (Long 40-ft Round-Trip Cable Run dari baterai buritan ke haluan):
    amps_12v = int(round(motor_watts / 12.0))
    breaker_amps = 50 if amps_12v <= 45 else (70 if amps_12v <= 65 else (90 if amps_12v <= 85 else 110))
    cable_awg = "4 AWG Tinned Marine Copper" if amps_12v <= 45 else ("2 AWG Tinned Marine Copper" if amps_12v <= 70 else "1/0 AWG Tinned Marine Copper")

    return {
        "windlass_name": model_name,
        "gypsy_spec": gypsy_spec,
        "seo_title": f"{model_name} Windlass Pull, Anchor Size & 7:1 Rode Scope Calculator (2026)",
        "meta_description": f"Calculate exact 12V windlass capacity ({recommended_windlass_pull:,} lb max pull / {working_load_limit_lbs} lb WLL), HHP anchor weight ({anchor_lbs} lbs), 7:1 rode scope ({rode_7_to_1_ft} ft), and {gypsy_spec} sizing for {model_name}.",
        "specs": {
            "boat_loa_ft": boat_loa_ft,
            "recommended_anchor_lbs": anchor_lbs,
            "hanging_tackle_weight_lbs": hanging_tackle_lbs,
            "windlass_max_pull_lbs": recommended_windlass_pull,
            "windlass_working_load_lbs": working_load_limit_lbs,
            "abyc_storm_holding_lbs": storm_load_lbs,
            "rode_7_to_1_scope_ft": rode_7_to_1_ft,
            "rode_5_to_1_scope_ft": rode_5_to_1_ft,
            "gypsy_chain_rope_spec": gypsy_spec,
            "motor_watts_12v": motor_watts,
            "windlass_amps_12v": amps_12v,
            "breaker_amps_12v": breaker_amps,
            "bow_cable_awg": cable_awg
        },
        "abyc_verdict": f"For {model_name} (~{boat_loa_ft} ft LOA requiring {storm_load_lbs:,} lbs of ABYC H-40 storm holding power), pair a {anchor_lbs}-lb High-Holding-Power (HHP) anchor with {gypsy_spec}. Because total submerged ground tackle hanging vertically in deep water weighs ~{hanging_tackle_lbs} lbs (anchor + chain + mud suction breakout), the 3.5x marine windlass sizing rule requires a {recommended_windlass_pull:,}-lb Max Pull ({working_load_limit_lbs}-lb Working Load Limit) 12V electric windlass. In a 25-foot anchorage (+{bow_height_ft} ft bow roller height), deploy {rode_5_to_1_ft} feet of rode for a 5:1 day scope or {rode_7_to_1_ft} feet for a 7:1 overnight storm scope, wired to the bow with {cable_awg} and a {breaker_amps}A thermal breaker.",
        "hardware_bundle": [
            {
                "badge": f"{recommended_windlass_pull:,} lb Pull Windlass",
                "title": f"12V {motor_watts}W Stainless Electric Anchor Windlass ({recommended_windlass_pull:,} lb Max Pull / {gypsy_spec.split('+')[0].strip()})",
                "price_range": "$649 - $1,599",
                "amazon_query": f"Lewmar Pro Fish Maxwell Electric Anchor Windlass {recommended_windlass_pull} lb 12V",
                "mar_note": f"Provides {working_load_limit_lbs} lbs continuous working load and {recommended_windlass_pull:,} lbs peak breakout pull."
            },
            {
                "badge": f"{anchor_lbs} lb HHP Boat Anchor",
                "title": f"{anchor_lbs}-Lb High-Holding-Power Galvanized / Stainless Anchor (Rocna / Mantus / Lewmar Delta / Fortress)",
                "price_range": "$159 - $649",
                "amazon_query": f"{anchor_lbs} lb Boat Anchor Rocna Mantus Lewmar Delta Fortress",
                "mar_note": f" weighted tip and concave fluke geometry set immediately in sand, mud, or grass to hold {storm_load_lbs:,}+ lbs in 42-knot squalls."
            },
            {
                "badge": f"200ft {gypsy_spec.split()[0]} G43 Rode",
                "title": f"Pre-Spliced {gypsy_spec} Anchor Rode Package (G43 ISO High-Test Chain + 8-Plait/3-Strand Nylon)",
                "price_range": "$189 - $499",
                "amazon_query": f"{gypsy_spec.split()[0]} G43 Anchor Chain Nylon Rode Package Lewmar Windlass",
                "mar_note": "Machine-calibrated short-link G43 chain feeds smoothly over the windlass gypsy without jumping or jamming in the locker."
            },
            {
                "badge": "Bow Roller & Snubber Kit",
                "title": f"Self-Launching Stainless Steel Bow Anchor Roller + Chain Stopper, Bridle Snubber & {breaker_amps}A Breaker",
                "price_range": "$94 - $269",
                "amazon_query": "Stainless Steel Hinged Bow Anchor Roller Chain Stopper Snubber Windlass Breaker",
                "mar_note": "Takes shock loads off the windlass gearbox while anchored and locks the anchor securely in the bow roller underway."
            }
        ],
        "skipper_checklist": [
            f"Size your Electric Windlass by the 3x–4x Ground Tackle Rule, never by Anchor Weight ({anchor_lbs} lbs) alone: add the weight of your {anchor_lbs}-lb anchor plus 45–60 feet of wet {gypsy_spec.split()[0]} chain (~{hanging_tackle_lbs} lbs total), then multiply by 3.5 to get a {recommended_windlass_pull:,}-lb Max Pull windlass.",
            f"Include Bow Freeboard Height when calculating 7:1 Rode Scope: in {std_depth_ft} feet of water with a {bow_height_ft}-foot bow roller height, multiply ({std_depth_ft} + {bow_height_ft}) × 7 = {rode_7_to_1_ft} feet of deployed rode so the pull angle stays horizontal on the seabed.",
            f"Match Gypsy Chain Specification strictly: a windlass gypsy stamped for {gypsy_spec.split()[0]} G43 High-Test (ISO) chain will jam violently if fed oversized Proof-Coil (G30) or long-link hardware-store chain.",
            "Always transfer the anchor load onto a Nylon Snubber Bridle (clipped to the chain and tied off to your bow cleats) or a Mechanical Chain Stopper once anchored—never leave the boat pulling directly against the windlass clutch and gears in waves, and never use the windlass to drag the boat forward before the rode is vertical."
        ],
        "faqs": [
            {
                "q": f"What size anchor and windlass do I need for {model_name} ({boat_loa_ft} ft boat)?",
                "a": f"Per ABYC H-40 windage tables, a {boat_loa_ft}-foot vessel requires ~{storm_load_lbs:,} lbs of storm holding power—matched by a {anchor_lbs}-lb High-Holding-Power (HHP) anchor. Because total hanging ground tackle weighs ~{hanging_tackle_lbs} lbs, select a 12V windlass with at least {working_load_limit_lbs} lbs Working Load Limit and {recommended_windlass_pull:,} lbs Max Pull."
            },
            {
                "q": f"How much anchor chain and nylon rode do I need for a 7:1 scope?",
                "a": f"Scope is measured from the bow roller to the seabed ($\text{{Water Depth}} + \text{{Bow Height}}$). In 25 feet of water with a {bow_height_ft}-foot bow height (29 ft vertical), a 5:1 day scope requires {rode_5_to_1_ft} feet of rode, and a 7:1 overnight storm scope requires {rode_7_to_1_ft} feet of rode."
            },
            {
                "q": f"What size battery cable and breaker do I need for a {motor_watts}W 12V windlass?",
                "a": f"A {motor_watts}W 12V windlass draws ~{amps_12v} Amps under heavy retrieval load. Because the round-trip cable run from the stern battery bank to the bow locker is typically 40 to 55 feet, run {cable_awg} protected by a {breaker_amps}-Amp manual-reset windlass circuit breaker to keep voltage drop under 10%."
            }
        ]
    }


def generate_windlass_data(wnd_tuple):
    """
    LAPIS 2: Memanggil model Gemini stabil dengan proteksi Cooldown HTTP 429 & Fallback Otomatis.
    """
    if not GEMINI_API_KEY:
        return build_deterministic_windlass_data(wnd_tuple)

    model_name, boat_loa_ft, anchor_lbs, max_pull_lbs, gypsy_spec, motor_watts, storm_load_lbs = wnd_tuple
    det_fallback = build_deterministic_windlass_data(wnd_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are an ABYC Certified Master Marine Surveyor & Naval Ground Tackle Engineer (ABYC H-40 Specialist). Create an accurate 2026 electric anchor windlass pull capacity (3x tackle rule), HHP anchor weight, calibrated G43 chain gypsy, and 7:1 rode scope guide for: "{model_name}".
Baseline specs: Boat LOA={boat_loa_ft} ft (ABYC Storm Load={storm_load_lbs} lbs), Recommended HHP Anchor={anchor_lbs} lbs, Hanging Tackle Weight={sp['hanging_tackle_weight_lbs']} lbs, Windlass Max Pull={sp['windlass_max_pull_lbs']} lbs (WLL={sp['windlass_working_load_lbs']} lbs), Gypsy={gypsy_spec}, 7:1 Scope @ 25ft Depth={sp['rode_7_to_1_scope_ft']} ft, 12V Motor={motor_watts}W ({sp['windlass_amps_12v']}A, {sp['breaker_amps_12v']}A Breaker, {sp['bow_cable_awg']}).
Return ONLY a valid JSON object matching this exact schema:
{{
  "windlass_name": "{model_name}",
  "gypsy_spec": "{gypsy_spec}",
  "seo_title": "{model_name} Windlass Pull, Anchor Size & 7:1 Rode Scope Calculator (2026)",
  "meta_description": "Calculate exact 12V electric windlass pull capacity, HHP boat anchor weight, calibrated G43 chain size, and 7:1 rode scope for {model_name}.",
  "specs": {{
    "boat_loa_ft": {boat_loa_ft},
    "recommended_anchor_lbs": {anchor_lbs},
    "hanging_tackle_weight_lbs": {sp['hanging_tackle_weight_lbs']},
    "windlass_max_pull_lbs": {sp['windlass_max_pull_lbs']},
    "windlass_working_load_lbs": {sp['windlass_working_load_lbs']},
    "abyc_storm_holding_lbs": {storm_load_lbs},
    "rode_7_to_1_scope_ft": {sp['rode_7_to_1_scope_ft']},
    "rode_5_to_1_scope_ft": {sp['rode_5_to_1_scope_ft']},
    "gypsy_chain_rope_spec": "{gypsy_spec}",
    "motor_watts_12v": {motor_watts},
    "windlass_amps_12v": {sp['windlass_amps_12v']},
    "breaker_amps_12v": {sp['breaker_amps_12v']},
    "bow_cable_awg": "{sp['bow_cable_awg']}"
  }},
  "abyc_verdict": "3-sentence technical summary stating ABYC H-40 storm load, HHP anchor weight, 3.5x windlass max pull rating, 7:1 rode scope length, and 12V bow cable/breaker sizing.",
  "hardware_bundle": [
    {{
      "badge": "{sp['windlass_max_pull_lbs']:,} lb Pull Windlass",
      "title": "12V {motor_watts}W Stainless Electric Anchor Windlass ({sp['windlass_max_pull_lbs']:,} lb Pull)",
      "price_range": "$649 - $1,599",
      "amazon_query": "Lewmar Pro Fish Maxwell Electric Anchor Windlass {sp['windlass_max_pull_lbs']} lb 12V",
      "mar_note": "1-sentence working load limit and free-fall/gypsy note"
    }},
    {{
      "badge": "{anchor_lbs} lb HHP Boat Anchor",
      "title": "{anchor_lbs}-Lb High-Holding-Power Boat Anchor (Rocna / Mantus / Lewmar Delta / Fortress)",
      "price_range": "$159 - $649",
      "amazon_query": "{anchor_lbs} lb Boat Anchor Rocna Mantus Lewmar Delta Fortress",
      "mar_note": "1-sentence rapid seabed penetration and storm holding note"
    }},
    {{
      "badge": "Calibrated G43 Chain Rode",
      "title": "Pre-Spliced {gypsy_spec} Anchor Rode Package (G43 Chain + Nylon Rope)",
      "price_range": "$189 - $499",
      "amazon_query": "{gypsy_spec.split()[0]} G43 Anchor Chain Nylon Rode Package Lewmar",
      "mar_note": "1-sentence calibrated short-link gypsy feed note"
    }},
    {{
      "badge": "Bow Roller & Snubber Kit",
      "title": "Stainless Hinged Bow Anchor Roller + Chain Stopper, Snubber & {sp['breaker_amps_12v']}A Breaker",
      "price_range": "$94 - $269",
      "amazon_query": "Stainless Steel Hinged Bow Anchor Roller Chain Stopper Windlass Breaker",
      "mar_note": "1-sentence gearbox shock relief and bow lock note"
    }}
  ],
  "skipper_checklist": [
    "Step 1 regarding 3.5x submerged ground tackle weight rule for windlass sizing",
    "Step 2 regarding 7:1 scope calculation including bow freeboard height above water",
    "Step 3 regarding calibrated G43 High-Test chain vs hardware store chain jamming",
    "Step 4 regarding using a nylon snubber bridle and motoring up to the anchor before lifting"
  ],
  "faqs": [
    {{"q": "What size anchor and windlass do I need for {model_name}?", "a": "Exact anchor lbs, hanging tackle weight, WLL, and max windlass pull."}},
    {{"q": "How much chain and rope rode do I need for 7:1 scope?", "a": "Exact (Water Depth + Bow Height) x 7 formula in feet."}},
    {{"q": "What wire gauge and breaker do I need for a {motor_watts}W 12V windlass?", "a": "Exact 12V amp draw, round-trip bow cable AWG, and thermal breaker rating."}}
  ]
}}
"""

    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id} for '{model_name}': {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice for '{model_name}': {e}")
                break

    return det_fallback


def build_windlass_html_page(data, slug, mon_cfg):
    wnd_name = data.get("windlass_name", "Boat Anchor & Electric Windlass")
    sp = data.get("specs", {})
    loa_ft = int(safe_float(sp.get("boat_loa_ft", 32), 32))
    anch_lbs = int(safe_float(sp.get("recommended_anchor_lbs", 33), 33))
    pull_lbs = int(safe_float(sp.get("windlass_max_pull_lbs", 1000), 1000))
    wll_lbs = int(safe_float(sp.get("windlass_working_load_lbs", 330), 330))
    storm_lbs = int(safe_float(sp.get("abyc_storm_holding_lbs", 2250), 2250))
    rode_7x = int(safe_float(sp.get("rode_7_to_1_scope_ft", 203), 203))
    gypsy_s = sp.get("gypsy_chain_rope_spec", "5/16\" G43 Chain + 9/16\" 8-Plait")
    watts = int(safe_float(sp.get("motor_watts_12v", 700), 700))
    brk_a = int(safe_float(sp.get("breaker_amps_12v", 70), 70))
    wire_awg = sp.get("bow_cable_awg", "2 AWG Tinned Copper")

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Lewmar+Pro+Fish+Electric+Anchor+Windlass+Rode+Kit"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{wnd_name} Windlass Pull, Anchor & Rode Scope Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Electric Anchor Windlass")), mon_cfg)
        bundle_html += f"""
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-cyan-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Ground Tackle')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$94+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">⚓ {item.get('mar_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Boat Length vs HHP Anchor Weight, Windlass Pull, G43 Chain & Wire Matrix Table
    mar_tiers = [
        ("20 – 24 Ft Boat", "14 – 16 lb HHP Anchor", "650 – 700 lb Pull (500W)", "1/4\" G43 + 1/2\" Nylon", "4 AWG (50A Breaker)"),
        ("25 – 29 Ft Boat", "22 – 25 lb HHP Anchor", "700 – 850 lb Pull (600W)", "1/4\" G43 + 1/2\" Nylon", "4 AWG (50A–60A Brk)"),
        ("30 – 35 Ft Boat", "28 – 33 lb HHP Anchor", "1,000 lb Pull (700W–800W)", "5/16\" G43 + 9/16\" Nylon", "2 AWG (70A–80A Brk)"),
        ("36 – 41 Ft Boat", "35 – 44 lb HHP Anchor", "1,250 – 1,500 lb (1,000W)", "5/16\" G43 + 5/8\" Nylon", "1/0 AWG (90A Breaker)"),
        ("42 – 50 Ft Yacht", "55 – 73 lb HHP Anchor", "1,650 – 2,200 lb (1,200W+)", "3/8\" G43 High-Test Chain", "2/0 AWG (110A–130A)")
    ]
    matrix_rows_html = ""
    for b_lbl, a_lbl, w_lbl, c_lbl, e_lbl in mar_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-slate-800 hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">{b_lbl}</td>
          <td class="py-3 px-4 font-bold text-cyan-400">{a_lbl}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{w_lbl}</td>
          <td class="py-3 px-4 text-slate-300">{c_lbl}</td>
          <td class="py-3 px-4 text-xs text-slate-300">{e_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("skipper_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-slate-900 border border-slate-800 rounded-xl p-4 cursor-pointer hover:border-slate-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-cyan-500 rounded cursor-pointer mar-check">
          <span class="text-sm text-slate-200 leading-relaxed"><strong>ABYC H-40 Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-slate-900 border border-slate-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-slate-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', wnd_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', wnd_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-cyan-500 text-slate-950 px-2 py-0.5 rounded font-black">WINDLASS</span>RodeIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Windlasses, Anchors & Rodes →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-cyan-500 text-slate-950 px-3 py-1 rounded-full">{pull_lbs:,} lb Pull Windlass ({anch_lbs} lb Anchor)</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">7:1 Scope: {rode_7x} ft | {gypsy_s.split('+')[0].strip()}</span>
        <span class="text-xs font-semibold bg-slate-800 text-slate-300 px-3 py-1 rounded-full">12V {watts}W ({brk_a}A Brk / {wire_awg.split()[0]} AWG)</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', wnd_name)}</h1>
      <div class="mt-4 bg-slate-900 border-l-4 border-cyan-500 p-4 rounded-r-xl text-sm text-slate-200 leading-relaxed">
        <strong>ABYC H-40 & 3.5x Ground Tackle Verdict:</strong> {data.get('abyc_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE WINDLASS WORKING LOAD, ANCHOR SIZE & 7:1 RODE SCOPE CALCULATOR -->
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {wnd_name} Pull, Anchor & Rode Scope Calculator</h2>
      <p class="text-xs text-slate-400 mb-6">Adjust your boat length (LOA), maximum anchoring water depth, scope ratio (5:1 vs. 7:1), and windage profile to compute exact HHP anchor weight, 3.5x windlass pull capacity, G43 chain size, and total rode length.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="loaSlider" class="text-slate-300">Boat Length Overall — LOA (Feet)</label>
              <span class="text-cyan-400 font-bold"><span id="loaVal">{loa_ft}</span> ft Boat</span>
            </div>
            <input id="loaSlider" type="range" min="18" max="55" step="1" value="{loa_ft}" class="w-full accent-cyan-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="scopeSelect" class="block text-xs font-medium text-slate-400 mb-1">Target Rode Scope Ratio</label>
              <select id="scopeSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500">
                <option value="5">5:1 Scope (Calm Day / All-Chain)</option>
                <option value="7" selected>7:1 Scope (ABYC Overnight Standard)</option>
                <option value="10">10:1 Scope (40+ Knot Gale Squall)</option>
              </select>
            </div>
            <div>
              <label for="hullSelect" class="block text-xs font-medium text-slate-400 mb-1">Hull Windage Profile</label>
              <select id="hullSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500">
                <option value="1.00" selected>Standard Center Console / Sailboat</option>
                <option value="1.25">High-Windage Cabin Cruiser / Catamaran</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="depthSlider" class="text-slate-300">Maximum Water Depth + High Tide (Feet)</label>
              <span class="text-cyan-400 font-bold"><span id="depthVal">25</span> ft Depth</span>
            </div>
            <input id="depthSlider" type="range" min="8" max="80" step="2" value="25" class="w-full accent-cyan-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-950 border border-cyan-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-cyan-400 font-bold">Windlass & HHP Anchor</span>
            <div class="text-xl sm:text-2xl font-black text-white mt-1"><span id="pullOut">{pull_lbs:,}</span> <span class="text-xs font-normal text-slate-400">lb Pull</span></div>
            <p id="anchorNoteOut" class="text-xs text-cyan-400 font-semibold mt-1">Match: {anch_lbs} lb HHP Anchor</p>
          </div>

          <div class="bg-slate-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Required Rode & Chain</span>
            <div class="text-xl sm:text-2xl font-black text-emerald-400 mt-1"><span id="rodeFtOut">{rode_7x}</span> <span class="text-xs font-normal text-slate-400">ft Rode</span></div>
            <p id="chainWireOut" class="text-xs text-slate-300 font-semibold mt-1">5/16" G43 | 2 AWG (70A)</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-cyan-950/40 border border-cyan-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="marAdviceBanner" class="text-sm text-cyan-100 font-medium"></div>
        <a id="dynamicMarBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Windlass, Anchor & Rode on Amazon →
        </a>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {wnd_name} Windlass, Anchor & G43 Rode Bundle</h2>
        <span class="text-xs text-slate-400">ABYC H-40 & ISO G43 Calibrated</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Boat Length, HHP Anchor Weight, Electric Windlass Pull & G43 Chain Chart</h2>
      <div class="overflow-x-auto bg-slate-900 border border-slate-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-slate-800 bg-slate-950/60 text-slate-400 uppercase text-xs">
              <th class="py-3.5 px-4">Boat Length (LOA)</th>
              <th class="py-3.5 px-4 text-cyan-400">HHP Anchor Weight</th>
              <th class="py-3.5 px-4 text-emerald-400">Min 12V Windlass Pull</th>
              <th class="py-3.5 px-4">Calibrated Chain & Rode</th>
              <th class="py-3.5 px-4">Bow Cable & Breaker</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">ABYC H-40 Ground Tackle, Gypsy Calibration & Snubber Safety Checklist</h2>
        <span id="marBadge" class="text-xs font-bold bg-slate-800 text-cyan-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({wnd_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500 px-4">
    <p>© {datetime.now(timezone.utc).year} WindlassRodeIndex. Independent Marine Ground Tackle & ABYC H-40 Windlass Sizing Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const loaSlider = document.getElementById('loaSlider');
    const scopeSelect = document.getElementById('scopeSelect');
    const hullSelect = document.getElementById('hullSelect');
    const depthSlider = document.getElementById('depthSlider');
    const loaVal = document.getElementById('loaVal');
    const depthVal = document.getElementById('depthVal');
    const pullOut = document.getElementById('pullOut');
    const anchorNoteOut = document.getElementById('anchorNoteOut');
    const rodeFtOut = document.getElementById('rodeFtOut');
    const chainWireOut = document.getElementById('chainWireOut');
    const marAdviceBanner = document.getElementById('marAdviceBanner');
    const dynamicMarBtn = document.getElementById('dynamicMarBtn');

    function recalculateWindlass() {{
      const loa = parseInt(loaSlider.value, 10);
      const scopeRatio = parseInt(scopeSelect.value, 10);
      const hullMult = parseFloat(hullSelect.value);
      const depthFt = parseInt(depthSlider.value, 10);

      loaVal.textContent = loa;
      depthVal.textContent = depthFt;

      const bowFreeboard = loa <= 32 ? 4 : 5;
      const rodeNeededFt = (depthFt + bowFreeboard) * scopeRatio;

      const effLoa = loa * hullMult;
      let anchLbs = 22;
      let windlassPull = 700;
      let chainSpec = '1/4" G43 + 1/2" Nylon';
      let elecSpec = '4 AWG (50A)';

      if (effLoa <= 24) {{
        anchLbs = 16; windlassPull = 650; chainSpec = '1/4" G43 + 1/2" Nylon'; elecSpec = '4 AWG (50A)';
      }} else if (effLoa <= 29) {{
        anchLbs = 22; windlassPull = 700; chainSpec = '1/4" G43 + 1/2" Nylon'; elecSpec = '4 AWG (60A)';
      }} else if (effLoa <= 35) {{
        anchLbs = 33; windlassPull = 1000; chainSpec = '5/16" G43 + 9/16" Nylon'; elecSpec = '2 AWG (70A)';
      }} else if (effLoa <= 41) {{
        anchLbs = 44; windlassPull = 1500; chainSpec = '5/16" G43 + 5/8" Nylon'; elecSpec = '1/0 AWG (90A)';
      }} else {{
        anchLbs = 55; windlassPull = 1800; chainSpec = '3/8" G43 Chain'; elecSpec = '2/0 AWG (110A)';
      }}

      pullOut.textContent = windlassPull.toLocaleString();
      anchorNoteOut.textContent = `Match: ${{anchLbs}} lb HHP Anchor`;
      rodeFtOut.textContent = rodeNeededFt;
      chainWireOut.textContent = `${{chainSpec.split('+')[0].trim()}} | ${{elecSpec}}`;

      marAdviceBanner.innerHTML = `⚓ <strong>ABYC H-40 Spec:</strong> A ${{loa}}-ft boat anchoring in ${{depthFt}} ft of water (${{scopeRatio}}:1 scope) requires a <strong>${{windlassPull.toLocaleString()}}-lb Pull 12V Electric Windlass</strong>, a <strong>${{anchLbs}}-lb HHP Anchor</strong>, and <strong>${{rodeNeededFt}}+ ft of ${{chainSpec}} Rode</strong>.`;
      dynamicMarBtn.href = `https://${{amzDomain}}/s?k=Lewmar+Pro+Fish+${{windlassPull}}+Windlass+${{anchLbs}}+lb+Boat+Anchor+Chain+Rode&tag=${{amzTag}}`;
    }}

    loaSlider.addEventListener('input', recalculateWindlass);
    scopeSelect.addEventListener('change', recalculateWindlass);
    hullSelect.addEventListener('change', recalculateWindlass);
    depthSlider.addEventListener('input', recalculateWindlass);
    recalculateWindlass();

    const checks = document.querySelectorAll('.mar-check');
    const badge = document.getElementById('marBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Lewmar+Pro+Fish+Electric+Anchor+Windlass+Rode+Kit"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-slate-900 border border-slate-800 hover:border-cyan-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-cyan-500 text-slate-950 px-2.5 py-0.5 rounded">{item.get('pull_lbs', 1000):,} lb Pull ({item.get('anch_lbs', 33)} lb Anchor)</span>
            <span class="text-xs text-slate-400">{item.get('loa_ft', 32)}' Boat | {item.get('rode_ft', 203)}' Rode</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-cyan-400 transition">{item['windlass_name']}</h2>
          <p class="text-xs text-slate-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-cyan-400">Calculate Windlass Pull, Anchor & 7:1 Scope →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WindlassRodeIndex — Boat Electric Anchor Windlass Pull, Anchor Weight & 7:1 Rode Scope Calculator (2026)</title>
  <meta name="description" content="Calculate exact 12V boat electric anchor windlass working load (3.5x tackle rule), ABYC H-40 HHP anchor weight, calibrated G43 chain gypsy size, and 7:1 rode scope for Lewmar, Maxwell, Rocna, Mantus, and Fortress setups.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="WindlassRodeIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-cyan-500 text-slate-950 px-2 py-0.5 rounded font-black">WINDLASS</span>RodeIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Windlasses, Anchors & Rodes →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Boat Electric Windlass Pull, HHP Anchor & 7:1 Rode Scope Database</h1>
      <p class="text-slate-400 mt-3 text-base sm:text-lg">Select your windlass model, anchor type, or boat length below to calculate 3.5x submerged ground tackle pull capacity, calibrated G43 chain gypsy fitment, and 7:1 rode scope length.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search windlass, anchor, or boat size (e.g. Lewmar Pro-Fish 700, 1000, Maxwell RC8, Rocna 15, Mantus, 32 Ft Boat...)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-cyan-500">
      </div>
    </div>

    <div id="marGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500">
    <p>© {datetime.now(timezone.utc).year} WindlassRodeIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('marGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>WindlassRodeIndex Boat Electric Windlass & Ground Tackle Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Boat Electric Anchor Windlass Pull, HHP Anchor Weight & 7:1 Rode Scope Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    """Multi-Endpoint Search Engine Pinger (IndexNow Global + Bing + Google WebSub)."""
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    for idx_endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            req = urllib.request.Request(
                idx_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[INDEXNOW] Pushed {len(new_urls)} URLs to {idx_endpoint} (HTTP {resp.status})")
                break
        except Exception as e:
            print(f"[WARN] IndexNow ({idx_endpoint}) notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published if "slug" in item}

    candidates = []
    if CUSTOM_WINDLASS:
        candidates.append((CUSTOM_WINDLASS.strip(), 32, 33, 1000, "5/16\" G43 Chain + 9/16\" Nylon", 700, 2250))
    candidates.extend(SEED_WINDLASSES)
    candidates.extend(discover_google_windlass_queries(published_slugs))

    new_urls = []
    count = 0

    for wnd_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        w_name = wnd_tuple[0]
        slug = slugify(f"{w_name}-windlass-rode-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating boat windlass & rode scope calculator for: {w_name}...")
        try:
            data = generate_windlass_data(wnd_tuple)
            build_windlass_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "windlass_name": data.get("windlass_name", w_name),
                "slug": slug,
                "title": data.get("seo_title", f"{w_name} Windlass Calculator"),
                "description": data.get("meta_description", ""),
                "loa_ft": int(safe_float(sp.get("boat_loa_ft", wnd_tuple[1]), wnd_tuple[1])),
                "anch_lbs": int(safe_float(sp.get("recommended_anchor_lbs", wnd_tuple[2]), wnd_tuple[2])),
                "pull_lbs": int(safe_float(sp.get("windlass_max_pull_lbs", wnd_tuple[3]), wnd_tuple[3])),
                "rode_ft": int(safe_float(sp.get("rode_7_to_1_scope_ft", 203), 203)),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            if count < PAGES_PER_RUN:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {w_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new boat windlass & anchor rode calculator pages.")


if __name__ == "__main__":
    main()

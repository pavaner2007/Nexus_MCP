"""
app/testing/eval_dataset.py
============================
Hand-labeled evaluation dataset for the Semantic Engine Router benchmark.

Structure
---------
53 TestCase entries, split across three routing modes:

  * 40 single-engine queries  — 8 per category × 5 categories
    · 6 clear in-category queries (expected_mode="single")
    · 2 borderline/challenging queries with notes explaining the nuance
  * 8 dual-engine queries     — wrapped from AMBIGUOUS_TEST_QUERIES in seed_data.py
    · expected_mode="dual", expected_dual_categories=[cat1, cat2]
  * 5 fallback queries        — low-confidence / generic queries
    · expected_mode="fallback", expected_category="search"

Held-out guarantee
------------------
ALL 40 single-engine queries are distinct from every phrase in SEED_PHRASES.
The 8 dual queries are the same strings as AMBIGUOUS_TEST_QUERIES but they
are NOT in SEED_PHRASES (those are already held-out by design in seed_data.py).

Consumed by
-----------
Phase 11 — routing-accuracy benchmark (compute precision / recall per category)
Phase 12 — token / latency benchmark
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


@dataclass
class TestCase:
    query: str
    expected_mode: str                          # "single" | "dual" | "fallback"
    expected_category: str | None = None        # top engine for single/fallback
    expected_dual_categories: list[str] | None = None  # ordered [cat1, cat2] for dual
    notes: str = ""


# ---------------------------------------------------------------------------
# 40 single-engine queries  (8 per category, 6 clear + 2 borderline)
# ---------------------------------------------------------------------------

SHOPPING_CASES: list[TestCase] = [
    # ── 6 clear shopping queries ──────────────────────────────────────────
    TestCase(
        query="what is the current price of the Samsung 65-inch QLED TV at Costco",
        expected_mode="single",
        expected_category="shopping",
    ),
    TestCase(
        query="buy Garmin Forerunner 265 running watch with heart rate monitor",
        expected_mode="single",
        expected_category="shopping",
    ),
    TestCase(
        query="best deal on a 4K monitor under $500 right now",
        expected_mode="single",
        expected_category="shopping",
    ),
    TestCase(
        query="Sony PlayStation 5 Slim disc edition in stock where to buy",
        expected_mode="single",
        expected_category="shopping",
    ),
    TestCase(
        query="Nespresso Vertuo Plus bundle price with capsules included",
        expected_mode="single",
        expected_category="shopping",
    ),
    TestCase(
        query="sale price for Levi's 501 jeans men's size 32x32 this week",
        expected_mode="single",
        expected_category="shopping",
    ),
    # ── 2 borderline shopping queries ─────────────────────────────────────
    TestCase(
        query="do clinical trials support using red light therapy devices sold on Amazon",
        expected_mode="single",
        expected_category="shopping",
        notes="Framing references clinical trials (scholar signal) but intent is purchase validation; "
              "purchase language ('sold on Amazon') should dominate.",
    ),
    TestCase(
        query="survey of consumer satisfaction scores for Roomba robot vacuums across price tiers",
        expected_mode="single",
        expected_category="shopping",
        notes="'survey' and 'satisfaction scores' sound academic but the subject is a "
              "commercial product evaluation to guide a buying decision.",
    ),
]

SCHOLAR_CASES: list[TestCase] = [
    # ── 6 clear scholar queries ───────────────────────────────────────────
    TestCase(
        query="peer-reviewed studies on neuroplasticity in adult brains after stroke rehabilitation",
        expected_mode="single",
        expected_category="scholar",
    ),
    TestCase(
        query="cite count for the BERT language model paper by Devlin et al 2018",
        expected_mode="single",
        expected_category="scholar",
    ),
    TestCase(
        query="systematic review on ketogenic diet and epilepsy seizure reduction in children",
        expected_mode="single",
        expected_category="scholar",
    ),
    TestCase(
        query="preprint on vision transformers outperforming CNNs on medical image segmentation",
        expected_mode="single",
        expected_category="scholar",
    ),
    TestCase(
        query="publications by Andrej Karpathy on recurrent neural networks",
        expected_mode="single",
        expected_category="scholar",
    ),
    TestCase(
        query="academic papers on the gut microbiome and its link to Parkinson's disease",
        expected_mode="single",
        expected_category="scholar",
    ),
    # ── 2 borderline scholar queries ──────────────────────────────────────
    TestCase(
        query="what are scientists currently saying about the health risks of ultraprocessed foods",
        expected_mode="single",
        expected_category="scholar",
        notes="Phrased as a general question ('what are scientists saying') which could "
              "score as search; however 'scientists' and research framing should push it to scholar.",
    ),
    TestCase(
        query="evidence-based guidelines published by WHO on screen time limits for toddlers",
        expected_mode="single",
        expected_category="scholar",
        notes="'WHO guidelines' has an institutional search feel, but 'evidence-based' + "
              "'published' anchors it to academic literature lookup.",
    ),
]

LOCAL_CASES: list[TestCase] = [
    # ── 6 clear local queries ─────────────────────────────────────────────
    TestCase(
        query="rooftop bar with happy hour specials near downtown Nashville",
        expected_mode="single",
        expected_category="local",
    ),
    TestCase(
        query="nearest EV charging station compatible with Hyundai Ioniq 6",
        expected_mode="single",
        expected_category="local",
    ),
    TestCase(
        query="pediatric dentist accepting BlueCross insurance near zip code 94105",
        expected_mode="single",
        expected_category="local",
    ),
    TestCase(
        query="yoga studios in Brooklyn with beginner-friendly evening classes",
        expected_mode="single",
        expected_category="local",
    ),
    TestCase(
        query="Korean BBQ restaurant open past 11pm near me tonight",
        expected_mode="single",
        expected_category="local",
    ),
    TestCase(
        query="indoor climbing gym in Denver with day-pass pricing and hours",
        expected_mode="single",
        expected_category="local",
    ),
    # ── 2 borderline local queries ────────────────────────────────────────
    TestCase(
        query="which neighborhoods in Seattle have the best walkability scores and coffee shops",
        expected_mode="single",
        expected_category="local",
        notes="Mentions 'walkability scores' which could attract a search or scholar result, "
              "but the combination with 'coffee shops' and implicit location intent should route local.",
    ),
    TestCase(
        query="compare membership prices at Planet Fitness and LA Fitness near me",
        expected_mode="single",
        expected_category="local",
        notes="Pricing comparison has shopping signal, but 'near me' and gym-specific context "
              "makes local lookup the right call.",
    ),
]

PATENTS_CASES: list[TestCase] = [
    # ── 6 clear patents queries ───────────────────────────────────────────
    TestCase(
        query="who holds the patent on GaN power transistor switching technology",
        expected_mode="single",
        expected_category="patents",
    ),
    TestCase(
        query="prior art search for haptic feedback mechanism in wearable devices",
        expected_mode="single",
        expected_category="patents",
    ),
    TestCase(
        query="Samsung patents filed in 2023 related to foldable phone hinge design",
        expected_mode="single",
        expected_category="patents",
    ),
    TestCase(
        query="when does the patent on Humira adalimumab biologic drug expire",
        expected_mode="single",
        expected_category="patents",
    ),
    TestCase(
        query="patent landscape for sodium-ion battery cathode materials",
        expected_mode="single",
        expected_category="patents",
    ),
    TestCase(
        query="find continuation patents related to LSTM sequence prediction filed by Google",
        expected_mode="single",
        expected_category="patents",
    ),
    # ── 2 borderline patents queries ──────────────────────────────────────
    TestCase(
        query="academic publication or patent registration for the RSA encryption algorithm origins",
        expected_mode="single",
        expected_category="patents",
        notes="'Academic publication' adds a scholar signal, but 'patent registration' "
              "and 'origins' in IP context should tip toward patents.",
    ),
    TestCase(
        query="technical papers filed with USPTO on machine learning model compression methods",
        expected_mode="single",
        expected_category="patents",
        notes="'Technical papers' overlaps with scholar, but 'filed with USPTO' is an "
              "unambiguous patent-office context that overrides the academic framing.",
    ),
]

SEARCH_CASES: list[TestCase] = [
    # ── 6 clear search / general queries ─────────────────────────────────
    TestCase(
        query="what is the difference between a republic and a democracy",
        expected_mode="single",
        expected_category="search",
    ),
    TestCase(
        query="how does a jet engine generate thrust",
        expected_mode="single",
        expected_category="search",
    ),
    TestCase(
        query="who wrote the novel 1984 and what is it about",
        expected_mode="single",
        expected_category="search",
    ),
    TestCase(
        query="what caused the 2008 global financial crisis",
        expected_mode="single",
        expected_category="search",
    ),
    TestCase(
        query="summary of the Treaty of Westphalia and its significance",
        expected_mode="single",
        expected_category="search",
    ),
    TestCase(
        query="how many calories does an average adult need per day",
        expected_mode="single",
        expected_category="search",
    ),
    # ── 2 borderline search queries ───────────────────────────────────────
    TestCase(
        query="latest updates on the James Webb Space Telescope discoveries this year",
        expected_mode="single",
        expected_category="search",
        notes="'Discoveries' has a scholar feel, but 'latest updates this year' signals "
              "a news/general-web lookup rather than academic literature.",
    ),
    TestCase(
        query="is artificial general intelligence close to being achieved",
        expected_mode="single",
        expected_category="search",
        notes="Topic overlaps with scholar (AI safety papers) but the question is "
              "general-web / opinion-aggregation in intent, not literature retrieval.",
    ),
]

# ---------------------------------------------------------------------------
# 8 dual-engine queries  (wrapped from AMBIGUOUS_TEST_QUERIES)
# ---------------------------------------------------------------------------

DUAL_CASES: list[TestCase] = [
    TestCase(
        query="what does the latest peer-reviewed research say about social media addiction",
        expected_mode="dual",
        expected_dual_categories=["scholar", "search"],
        notes="Peer-reviewed framing → scholar; 'social media addiction' is also a common "
              "general-web topic. Gap is close enough to trigger dual at threshold 0.15.",
    ),
    TestCase(
        query="published papers and patent filings on solid-state battery electrolyte design",
        expected_mode="dual",
        expected_dual_categories=["patents", "scholar"],
        notes="'Patent filings' → patents; 'published papers' → scholar. "
              "Explicitly requests both literatures.",
    ),
    TestCase(
        query="what are the best hospitals in Boston — including ratings and visiting hours",
        expected_mode="dual",
        expected_dual_categories=["local", "shopping"],
        notes="Hospital names + ratings + hours → local; 'best' + comparison framing "
              "can also score shopping. Location signal is strong.",
    ),
    TestCase(
        query="who invented CRISPR — research papers and patent ownership landscape",
        expected_mode="dual",
        expected_dual_categories=["patents", "scholar"],
        notes="'Research papers' → scholar; 'patent ownership' → patents. "
              "Both dimensions are explicitly requested.",
    ),
    TestCase(
        query="academic performance benchmarks and market pricing analysis of the M3 MacBook Pro",
        expected_mode="dual",
        expected_dual_categories=["shopping", "scholar"],
        notes="'Market pricing' → shopping; 'academic performance benchmarks' → scholar. "
              "Rare example of product being referenced in academic context.",
    ),
    TestCase(
        query="Tesla showroom locations near me and current lease pricing for the Model 3",
        expected_mode="dual",
        expected_dual_categories=["local", "shopping"],
        notes="'Showroom locations near me' → local; 'lease pricing' → shopping. "
              "Gap is very small (0.068) — textbook dual-routing trigger.",
    ),
    TestCase(
        query="explain the differences between OLED and QLED TVs and which one is worth buying",
        expected_mode="dual",
        expected_dual_categories=["shopping", "search"],
        notes="'Worth buying' → shopping; 'explain the differences' → search/general. "
              "Note: at MIN_CONFIDENCE_THRESHOLD=0.35 this may fall into fallback if "
              "shopping score dips below threshold on some embeddings.",
    ),
    TestCase(
        query="prior art for mRNA vaccine delivery systems developed at US research universities",
        expected_mode="dual",
        expected_dual_categories=["patents", "scholar"],
        notes="'Prior art' → patents; 'research universities' + 'delivery systems' → scholar. "
              "Note: patents score ~0.318, which is below MIN_CONFIDENCE_THRESHOLD=0.35 — "
              "may route to fallback. Ideal threshold for this query is ≤0.30.",
    ),
]

# ---------------------------------------------------------------------------
# 5 fallback queries  (genuinely low-confidence / general)
# ---------------------------------------------------------------------------

FALLBACK_CASES: list[TestCase] = [
    TestCase(
        query="what is the current temperature in Hyderabad right now",
        expected_mode="fallback",
        expected_category="search",
        notes="Real-time weather query. No specialist engine covers weather. "
              "Classifier scores should all be below 0.35.",
    ),
    TestCase(
        query="who is the current Prime Minister of the United Kingdom",
        expected_mode="fallback",
        expected_category="search",
        notes="General political fact question. Low specificity across all specialist categories.",
    ),
    TestCase(
        query="convert 500 US dollars to Indian rupees",
        expected_mode="fallback",
        expected_category="search",
        notes="Currency conversion is a pure general-search task. "
              "None of the specialist engines apply.",
    ),
    TestCase(
        query="how many days until Christmas 2025",
        expected_mode="fallback",
        expected_category="search",
        notes="Date arithmetic / countdown — definitively a general search answer-box query.",
    ),
    TestCase(
        query="what does the acronym NATO stand for",
        expected_mode="fallback",
        expected_category="search",
        notes="Definition / acronym expansion — canonical general-web lookup with no "
              "specialist engine relevance.",
    ),
]

# ---------------------------------------------------------------------------
# Combined export  (40 + 8 + 5 = 53 entries)
# ---------------------------------------------------------------------------

FULL_EVAL_SET: list[TestCase] = (
    SHOPPING_CASES    # 8
    + SCHOLAR_CASES   # 8
    + LOCAL_CASES     # 8
    + PATENTS_CASES   # 8
    + SEARCH_CASES    # 8
    + DUAL_CASES      # 8
    + FALLBACK_CASES  # 5
)

"""
app/classifier/seed_data.py
============================
Seed-phrase dataset used to train the semantic routing classifier (Phase 2+).

SEED_PHRASES
------------
A dict mapping each SerpApi engine key to 40-50 realistic, varied example
queries.  Phrases intentionally span formal, casual, question, imperative,
and short/long forms.  At least 5 phrases per category are deliberately
ambiguous — they could plausibly belong to a neighbouring engine — so the
classifier is exposed to genuinely hard cases during training.

AMBIGUOUS_TEST_QUERIES
-----------------------
8 held-out queries that genuinely straddle two categories.
These are NOT in SEED_PHRASES; they are reserved for dual-engine tests
in a later phase.
"""

SEED_PHRASES: dict[str, list[str]] = {
    # ------------------------------------------------------------------ #
    #  SHOPPING — routes to Google Shopping                               #
    # ------------------------------------------------------------------ #
    "shopping": [
        # Straightforward product lookups
        "buy Sony WH-1000XM5 headphones online",
        "where to buy Nike Air Max 270 in size 10",
        "Apple MacBook Pro 14-inch M3 price",
        "cheapest Samsung Galaxy S24 Ultra deal right now",
        "order a standing desk under $400",
        # Price comparisons
        "compare prices for Dyson V15 vacuum across retailers",
        "which store has the lowest price on iPad Pro 12.9",
        "LG C3 OLED TV 65-inch best price comparison",
        "iPhone 15 Pro Max 256GB vs 512GB price difference",
        "price history for Bose QuietComfort 45",
        # Budget-constrained queries
        "best gaming laptop under $800",
        "good noise-cancelling headphones under 150 dollars",
        "affordable robot vacuum under $300 with good reviews",
        "best mirrorless camera for beginners under 600",
        "budget mechanical keyboard under $50",
        # Specific model / SKU style
        "Dell XPS 15 9530 Intel Core i7 stock availability",
        "ASUS ROG Zephyrus G14 2024 buy",
        "Logitech MX Master 3S wireless mouse buy now",
        "Kindle Paperwhite 11th generation refurbished",
        "Canon EOS R50 kit lens bundle price",
        # Where-to-buy style
        "where can I buy a good espresso machine",
        "which retailers sell the Ninja Creami ice cream maker",
        "is the RTX 4080 available at Best Buy",
        "find a Vitamix blender on sale this week",
        "online stores selling Patagonia fleece jackets",
        # Deal / discount oriented
        "Black Friday deals on 4K televisions",
        "Amazon Prime Day laptop discounts",
        "coupon for Chewy dog food subscription",
        "discounted AirPods Pro 2nd generation",
        "sale on Weber gas grills this weekend",
        # Review-informed shopping (ambiguous with scholar)
        "highest-rated electric toothbrush recommended by dentists",
        "what do consumer reports say is the best dishwasher to buy",
        "top-rated air purifier based on independent lab testing",
        "which ergonomic office chair has the best verified user ratings",
        "scientifically tested sunscreen recommended by dermatologists to buy",
        # Ambiguous — could sound like research but intent is purchasing
        "studies comparing iPhone vs Android user satisfaction to decide which to buy",
        "technical specs and peer-reviewed performance benchmarks of RTX 4090",
        "expert analysis of best EV to purchase in 2024",
        "research-backed best mattress for back pain — where to buy",
        "what does the literature say about HEPA filter effectiveness — buy recommendation",
        # Miscellaneous realistic phrasings
        "restock notification for PS5 disc edition",
        "Is the Steam Deck OLED worth the price?",
        "second-hand iPhone 14 Pro good price",
        "gift ideas under $50 for tech lovers",
        "eco-friendly water bottle best brand to order",
    ],

    # ------------------------------------------------------------------ #
    #  SCHOLAR — routes to Google Scholar                                 #
    # ------------------------------------------------------------------ #
    "scholar": [
        # Classic academic lookups
        "research papers on transformer neural networks",
        "recent studies on CRISPR gene editing in humans",
        "peer-reviewed articles about climate change and crop yields",
        "literature review on deep reinforcement learning",
        "citation count for Attention Is All You Need paper",
        # Author and journal searches
        "papers by Geoffrey Hinton on backpropagation",
        "publications by Yoshua Bengio 2020 to 2024",
        "articles published in Nature Medicine on long COVID",
        "journal of neuroscience papers on memory consolidation",
        "Andrew Ng machine learning lecture notes and papers",
        # Specific research topics
        "what are the latest findings on Alzheimer's tau protein",
        "papers investigating microplastics in human bloodstream",
        "academic work on quantum computing error correction",
        "recent scholarship on large language model hallucinations",
        "meta-analysis of mindfulness-based cognitive therapy efficacy",
        # Thesis, dissertation, preprint lookups
        "PhD dissertation on federated learning privacy",
        "arxiv preprint about diffusion models for protein folding",
        "master's thesis on supply chain resilience post-COVID",
        "working paper on central bank digital currencies",
        "preprint on mRNA vaccine immunogenicity in elderly populations",
        # Citation and reference queries
        "who cited the ImageNet paper most",
        "seminal papers in natural language processing before 2000",
        "foundational references for reinforcement learning from human feedback",
        "systematic review citations on intermittent fasting metabolic effects",
        "highly cited papers on graph neural networks 2022",
        # Problem and theory focused
        "mathematical proof for P vs NP problem papers",
        "theoretical framework for multi-agent reinforcement learning",
        "papers exploring the alignment problem in AI safety",
        "research on dark matter direct detection experiments",
        "academic debate on universal basic income economic effects",
        # Ambiguous — sound like general search or shopping but intent is academic
        "best-performing models on GLUE benchmark literature",
        "comparative analysis of EV battery technologies in academic journals",
        "published research on ergonomic chair designs and back pain",
        "academic papers evaluating HEPA filter particle capture efficiency",
        "peer-reviewed studies ranking programming languages by developer productivity",
        # More ambiguous — straddles scholar/search
        "what does current research say about sleep and memory",
        "is there scientific consensus on low-carb diets for weight loss",
        "expert opinions published in journals on social media mental health effects",
        "literature on whether standing desks improve productivity",
        "scholarly debate on whether remote work reduces output",
        # Miscellaneous varied phrasings
        "find me papers on explainable AI from 2023",
        "seminal NLP paper from Stanford on dependency parsing",
        "where can I read the original AlphaGo paper",
        "academic sources for history of the internet",
        "papers about urban heat island effect and green roofs",
    ],

    # ------------------------------------------------------------------ #
    #  LOCAL — routes to Google Local / Maps                              #
    # ------------------------------------------------------------------ #
    "local": [
        # Near-me queries
        "coffee shops near me open right now",
        "best pizza place within 5 miles",
        "24-hour pharmacy near me",
        "gas stations open near me tonight",
        "urgent care clinic near me accepting walk-ins",
        # Restaurant / food lookups
        "top-rated Indian restaurants in downtown Chicago",
        "vegan brunch spots in Austin TX",
        "best ramen in San Francisco Mission District",
        "sushi restaurant open on Monday near Union Square",
        "late-night burger place still open after midnight",
        # Business / service lookups
        "plumber available on weekends in Brooklyn",
        "hair salon near me open Sunday",
        "dog grooming service in Seattle with good reviews",
        "auto mechanic near me that does same-day service",
        "locksmith open 24 hours near downtown Denver",
        # Location + category
        "gyms in Miami Beach with a pool",
        "coworking spaces in Austin near South Congress",
        "bookstores in Portland Oregon",
        "wine bars in Napa Valley with reservations",
        "wedding photographers in Nashville Tennessee",
        # Hours and availability
        "what time does Target close near me",
        "which Starbucks is open right now close to me",
        "grocery store open after 10pm near me",
        "bank branches open on Saturday near downtown LA",
        "hardware store near me open on holidays",
        # Reviews and ratings oriented
        "highest rated Mexican restaurant in my city",
        "4-star hotels near Times Square New York",
        "top-reviewed dentist accepting new patients near me",
        "best-rated auto body shop in Phoenix",
        "local bakery with gluten-free options near me",
        # Event / activity lookups
        "escape rooms near me this weekend",
        "hiking trails open near Denver",
        "farmers market this Saturday near me",
        "live jazz bars in New Orleans tonight",
        "children's museum near me with parking",
        # Ambiguous — could be general search but clear local intent
        "is Whole Foods near me stocking oat milk",
        "iPhone repair shop near me — how much does it cost",
        "where is the nearest Tesla supercharger",
        "hotels in Boston with free parking under $200 a night",
        "compare co-working space prices near downtown Seattle",
        # Miscellaneous
        "best taco trucks in Los Angeles",
        "pool halls near me open late",
        "karaoke bars in Nashville open now",
        "brewery with outdoor seating near me",
        "pet-friendly restaurants near Golden Gate Park",
    ],

    # ------------------------------------------------------------------ #
    #  PATENTS — routes to Google Patents                                  #
    # ------------------------------------------------------------------ #
    "patents": [
        # Classic patent lookups
        "patent for wireless charging technology",
        "who holds the patent on CRISPR gene editing",
        "find patent US10,000,000",
        "Apple patents on Face ID technology",
        "Google patent for PageRank algorithm",
        # Prior art searches
        "prior art for foldable display hinge mechanism",
        "existing patents on solid-state battery design",
        "prior art search for AI-generated image watermarking",
        "has anyone patented a self-healing polymer coating",
        "prior art for voice-controlled smart home hub",
        # Inventor and assignee searches
        "patents filed by Elon Musk",
        "inventions patented by IBM in quantum computing",
        "MIT patents on photonic chip design",
        "who patented the first touchscreen smartphone",
        "Tesla energy patents assigned to Panasonic",
        # Patent status / expiry
        "is the patent on GLP-1 receptor agonists still active",
        "when does the Lipitor atorvastatin patent expire",
        "expired patents on mRNA delivery systems",
        "patent status for Bluetooth low energy protocol",
        "royalty-free patents available in solar cell technology",
        # Technology domain searches
        "recent patents on large language model training methods",
        "patents covering lidar sensor arrays for autonomous vehicles",
        "semiconductor etching process patents filed in 2023",
        "drone swarm coordination patents",
        "wearable glucose monitoring patent landscape",
        # Patent number / classification lookups
        "patent classification CPC G06N 3/08",
        "patents in IPC class H01M for battery electrodes",
        "utility patent vs design patent for a chair",
        "find continuation patents for US9,845,234",
        "PCT international patent application search for water filtration",
        # Ambiguous — straddle scholar or search but patent intent is clear
        "published research or patents on perovskite solar cell efficiency",
        "academic papers and patents on self-driving car perception systems",
        "is there a patent on the BERT language model architecture",
        "patent and literature search for biodegradable plastic alternatives",
        "who invented and patented noise-cancelling headphone technology",
        # Miscellaneous varied phrasings
        "how do I look up if my invention is already patented",
        "search for competing patents before filing for my product",
        "patent infringement cases involving smartphone design",
        "pharmaceutical company patents expiring in next two years",
        "open-source patents pledged by Google",
    ],

    # ------------------------------------------------------------------ #
    #  SEARCH — generic/ambiguous, falls back to base Google Search       #
    # ------------------------------------------------------------------ #
    "search": [
        # General knowledge / facts
        "what is the capital of Australia",
        "how does photosynthesis work",
        "who was Ada Lovelace",
        "what year did World War II end",
        "how many planets are in the solar system",
        # Current events
        "latest news about the 2024 US presidential election",
        "what happened in the stock market today",
        "current weather in Tokyo",
        "latest developments in the Russia-Ukraine conflict",
        "who won the Oscar for Best Picture this year",
        # How-to and definitions
        "how to tie a Windsor knot",
        "what does GDP stand for",
        "how to convert Celsius to Fahrenheit",
        "what is the difference between machine learning and AI",
        "how to write a cover letter",
        # Pop culture and entertainment
        "who plays Iron Man in the Marvel movies",
        "when is the next season of Stranger Things coming out",
        "best movies of 2023",
        "song lyrics to Bohemian Rhapsody",
        "who won the FIFA World Cup 2022",
        # Vague / exploratory queries
        "tell me about the Roman Empire",
        "explain quantum entanglement simply",
        "history of the internet",
        "what is blockchain",
        "overview of the French Revolution",
        # Ambiguous — could route to specialist engine but genuinely unclear
        "what's the best programming language to learn in 2024",
        "how does compound interest work",
        "is coffee good or bad for you",
        "what are the symptoms of vitamin D deficiency",
        "how to improve my credit score",
        # Could be local but no location signal
        "what time zone is Phoenix Arizona in",
        "do pharmacies sell insulin without a prescription",
        "can I get a passport renewal at the post office",
        "what documents do I need to open a bank account",
        "when is daylight saving time in the US",
        # Could sound like scholar but non-academic intent
        "is social media bad for teenagers",
        "does exercise help with depression",
        "what are the effects of sleep deprivation",
        "is intermittent fasting safe",
        "what are the benefits of meditation",
        # Miscellaneous
        "how long does it take to fly from New York to London",
        "what is the population of India",
        "who invented the telephone",
        "meaning of the word serendipity",
        "how to say hello in Japanese",
    ],
}

# --------------------------------------------------------------------------- #
#  AMBIGUOUS TEST QUERIES (held out — NOT part of SEED_PHRASES)               #
#  Each query genuinely spans two categories.  Reserved for dual-engine tests  #
#  in Phase 3+.                                                                #
# --------------------------------------------------------------------------- #
AMBIGUOUS_TEST_QUERIES: list[str] = [
    # scholar <-> search  (peer-reviewed framing vs. general knowledge query)
    "what does the latest peer-reviewed research say about social media addiction",
    # patents <-> scholar  (prior art search + published literature)
    "published papers and patent filings on solid-state battery electrolyte design",
    # local <-> search  (location + general info, no purchase intent)
    "what are the best hospitals in Boston — including ratings and visiting hours",
    # scholar <-> patents  (research + IP overlap)
    "who invented CRISPR — research papers and patent ownership landscape",
    # shopping <-> scholar  (product decision framed as academic comparison)
    "academic performance benchmarks and market pricing analysis of the M3 MacBook Pro",
    # local <-> shopping  (location + price equally weighted)
    "Tesla showroom locations near me and current lease pricing for the Model 3",
    # search <-> shopping  (general curiosity + buy intent balanced)
    "explain the differences between OLED and QLED TVs and which one is worth buying",
    # patents <-> scholar  (prior art framed with university research context)
    "prior art for mRNA vaccine delivery systems developed at US research universities",
]

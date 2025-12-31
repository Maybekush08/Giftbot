import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2").strip()
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-large").strip()

PINTEREST_WEIGHT = 1.35
ETSY_WEIGHT = 1.35

DEFAULT_WEIGHT = 1.0
RETAIL_WEIGHT = 1.15

MAX_RESULTS_PER_QUERY = 8
BUY_LINKS_PER_IDEA = 6

# GiftBot 🎁
A chat-style AI gifting assistant that recommends **5 gift ideas with direct buy links**, using **web-search powered RAG** and a **Pinterest + Etsy preference signal** to surface aesthetic, trend-aware ideas (without scraping those sites).

---

## Why GiftBot
Finding a gift is rarely “search once, buy once.” It’s usually:
- figuring out the person (taste, vibe, relationship)
- staying inside budget
- avoiding obvious no-go items
- wanting something that feels *thoughtful*, not generic

GiftBot takes a structured profile and returns **ranked gift picks** plus **message drafts** (note, card, professional writeup). It also supports **Generate again** to keep producing fresh ideas without repeats.

---

## Key Features
- **Chat UI** (Streamlit) with a gifting profile sidebar
- **Profile-aware recommendations**:
  - recipient, age, relationship
  - personality (minimalist / sentimental / practical / playful)
  - occasion, budget, interests
  - no-go list (hard constraints)
- **Web-search powered RAG**:
  - pulls search result titles/snippets/URLs
  - embeds & retrieves the most relevant evidence for the profile
- **Pinterest + Etsy differentiator**:
  - prioritizes ideas that show up frequently in Pinterest/Etsy search results
  - boosts Pinterest/Etsy domains in ranking (signals, not scraping)
- **Direct buy links**:
  - after choosing ideas, performs a second search pass to find purchase pages
- **Message generator**:
  - `a one-line note`
  - `a heartfelt short card`
  - `a professional gifting writeup`

---

## How It Works (High Level)
1. **User fills gift profile** in the sidebar (missing fields are allowed).
2. GiftBot generates a set of **search queries**, including:
   - broad web queries
   - Pinterest-weighted queries (`site:pinterest.com`)
   - Etsy-weighted queries (`site:etsy.com`)
3. Search results become “evidence documents” (title/snippet/url).
4. RAG retrieval selects the most relevant evidence for the profile.
5. The LLM generates **candidate gift ideas** grounded in that evidence.
6. Gift ideas are **ranked** using:
   - profile fit score (embedding similarity)
   - domain preference (Pinterest/Etsy/retail boosts)
   - any available rating signals in snippets (if present)
7. For each gift idea, GiftBot searches again to find the **best buy link**.
8. User can click **Generate again** to get a new set of 5 without duplicates.

---

## Tech Stack
- **Python** (backend)
- **Streamlit** (chat UI)
- **OpenAI** (generation + embeddings)
- **Tavily** (recommended web search provider) with **DuckDuckGo fallback**
- **NumPy** (similarity math)
- **Pydantic** (typed models)

---

## Project Structure
```text
giftbot/
  app.py
  requirements.txt
  .env.example
  README.md
  .gitignore
  backend/
    config.py
    llm.py
    models.py
    prompts.py
    search_providers.py
    rag.py
    recommender.py

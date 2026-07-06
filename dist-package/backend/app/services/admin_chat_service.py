"""
Admin chatbot service — handles navigation AND book CRUD via conversational flow.

Conversation state is kept in-memory per admin session using a simple dict keyed
by a session_id sent from the frontend.  State machine:

  idle
    → add_book:     collect title, author, price, stock, category_id, description, image_url
    → delete_book:  ask for book name, confirm, then call delete
    → edit_book:    ask for book name, then field/value pairs, then confirm

The assistant is designed to be *natural* — admins can issue one-shot commands
like "delete The Great Gatsby" or "change the price of Atomic Habits to 25"
and the assistant will handle them without rigid multi-step prompting.
"""

import re
import difflib
import logging

logger = logging.getLogger(__name__)
from typing import Optional
from urllib.parse import quote_plus
from app.db.session import SessionLocal
from app.models.book import Book
from app.models.category import Category
from app.services.book_service import create_book, delete_book, get_book_by_id, update_book
from app.schemas.book import BookCreate, BookUpdate

# ── In-memory conversation state per session ──────────────────────────────────
# { session_id: { "state": str, "data": dict } }
_sessions: dict[str, dict] = {}

REQUIRED_ADD_FIELDS = ["title", "author", "price", "stock_quantity", "category_id"]
ADD_FIELD_PROMPTS = {
    "title": "What is the book title?",
    "author": "Who is the author?",
    "price": "What is the price? (e.g. 14.99)",
    "stock_quantity": "How many copies are in stock?",
    "category_id": "What is the category ID? (1=Fiction, 2=Non-Fiction, 3=Self Improvement, 4=Business)",
    "description": "Enter a short description (or type 'skip' to leave it blank).",
    "image_url": "Paste an image URL (or type 'skip' to leave it blank).",
}
ALL_ADD_FIELDS = list(ADD_FIELD_PROMPTS.keys())

DESCRIPTION_MODE_PROMPT = (
    "Would you like me to generate the book descriptions automatically, "
    "or will you provide them yourself? Reply with GENERATE or MANUAL."
)

BOOK_ENTRY_PROMPT = (
    "Great! You can add one or more books in a single message.\n"
    "Use comma-separated details in this order:\n"
    "title, author, price, stock_quantity, category_id, description (or GENERATE), image URL (or GENERATE)\n"
    "Example:\n"
    "The Great Gatsby, F. Scott Fitzgerald, 14.99, 30, 1, GENERATE, GENERATE\n"
    "Atomic Habits, James Clear, 18.00, 25, 3, A practical guide to habits, GENERATE\n\n"
    "Or use natural language like:\n"
    "add book Dune by Frank Herbert, price 12.99, stock 50, category Fiction\n\n"
    "After each detail use a comma. If you want me to generate a description, use GENERATE. "
    "If you want me to generate the book image, use GENERATE or leave the image field blank."
)


import urllib.request
import urllib.parse
import json

def _looks_like_url(value: str) -> bool:
    return value.strip().lower().startswith(("http://", "https://"))


def _generate_book_description(title: str, author: str) -> str:
    return (
        f"{title} by {author} is a compelling read with strong storytelling and memorable "
        "characters. It blends accessible ideas with a clear narrative voice, making it a great "
        "choice for readers who enjoy engaging, thoughtful books."
    )


def _generate_book_image_url(title: str, author: str = "") -> str:
    """Generate an AI book cover image using Pollinations.ai (free, no API key)."""
    prompt = f"book cover art for a novel called '{title}'"
    if author:
        prompt += f" by {author}"
    prompt += ", professional book cover design, high quality, vibrant colors"
    encoded = quote_plus(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=400&height=600&nologo=true"


def _clean_and_truncate_description(desc: str) -> str:
    # Clean HTML tags
    desc = re.sub(r'<[^>]+>', '', desc)
    # Remove markdown links e.g. [text](url)
    desc = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', desc)
    desc = desc.strip()

    # Split into words and target 90-100 words
    words = desc.split()
    TARGET_WORDS = 95

    if len(words) <= TARGET_WORDS:
        return desc

    # Trim to target word count, ending on a complete sentence if possible
    trimmed = words[:TARGET_WORDS]
    candidate = " ".join(trimmed)

    # Try to end on the last sentence boundary within the trimmed text
    sentence_end = max(
        candidate.rfind(". "),
        candidate.rfind("! "),
        candidate.rfind("? "),
    )
    if sentence_end > len(candidate) // 2:
        # There's a sentence boundary in the second half — end there cleanly
        candidate = candidate[:sentence_end + 1]
    else:
        candidate = candidate.rstrip(",;:") + "..."

    return candidate


def _fetch_from_wikipedia(title: str, author: str = "") -> tuple[str | None, str | None]:
    # Try different search terms to be resilient for both novels and non-fiction
    queries = []
    if author:
        queries.append(f"{title} {author}")
    queries.append(f"{title} book")
    queries.append(f"{title} novel")
    queries.append(title)
    
    for query in queries:
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&utf8=&format=json&limit=3"
        try:
            req = urllib.request.Request(
                search_url,
                headers={'User-Agent': 'BookstoreAdminAssistant/1.0 (admin@onlinebookstore.com)'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                search_data = json.loads(response.read().decode('utf-8'))
                search_results = search_data.get("query", {}).get("search", [])
                if not search_results:
                    continue
                
                # Check results for a title match
                for res in search_results:
                    res_title = res["title"]
                    res_title_lower = res_title.lower()
                    
                    snippet = res.get("snippet", "").lower()
                    
                    # Exact title check or clear containment match
                    if title.lower() in res_title_lower:
                        return _get_wiki_page_details(res_title)
                    
                    if author and author.lower() in snippet:
                        return _get_wiki_page_details(res_title)
                
                # Fallback to the first query search result
                if search_results:
                    return _get_wiki_page_details(search_results[0]["title"])
        except Exception as e:
            logger.warning("Wikipedia API search query '%s' failed: %s", query, e)
            
    return None, None


def _get_wiki_page_details(page_title: str) -> tuple[str | None, str | None]:
    detail_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts|pageimages&exintro=&explaintext=&titles={urllib.parse.quote(page_title)}&format=json&pithumbsize=500"
    try:
        req = urllib.request.Request(
            detail_url,
            headers={'User-Agent': 'BookstoreAdminAssistant/1.0 (admin@onlinebookstore.com)'}
        )
        with urllib.request.urlopen(req, timeout=5) as detail_response:
            detail_data = json.loads(detail_response.read().decode('utf-8'))
            pages = detail_data.get("query", {}).get("pages", {})
            if not pages:
                return None, None
            
            page_info = list(pages.values())[0]
            extract = page_info.get("extract", "")
            
            thumbnail = page_info.get("thumbnail", {})
            image_url = thumbnail.get("source")
            
            return extract or None, image_url or None
    except Exception as e:
        logger.warning("Wikipedia API details failed for '%s': %s", page_title, e)
        return None, None


def _fetch_from_google_books(title: str, author: str = "") -> tuple[str | None, str | None]:
    query = f"intitle:{title}"
    if author:
        query += f" inauthor:{author}"
        
    url = f"https://www.googleapis.com/books/v1/volumes?q={urllib.parse.quote(query)}&maxResults=1"
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
            items = data.get("items", [])
            if not items:
                return None, None
            
            volume_info = items[0].get("volumeInfo", {})
            description = volume_info.get("description", "")
            
            image_links = volume_info.get("imageLinks", {})
            # Prefer highest resolution available
            image_url = (
                image_links.get("extraLarge")
                or image_links.get("large")
                or image_links.get("medium")
                or image_links.get("thumbnail")
                or image_links.get("smallThumbnail")
            )
            if image_url:
                image_url = image_url.replace("http://", "https://")
                # Remove zoom=1 which crops covers; use zoom=0 for full image
                image_url = re.sub(r'&zoom=\d', '&zoom=0', image_url)
                
            return description or None, image_url or None
    except Exception as e:
        logger.warning("Google Books API search failed: %s", e)
        return None, None


def _fetch_from_open_library(title: str, author: str = "") -> tuple[str | None, str | None]:
    query = f"title={urllib.parse.quote(title)}"
    if author:
        query += f"&author={urllib.parse.quote(author)}"
        
    url = f"https://openlibrary.org/search.json?{query}&limit=1"
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'BookstoreAdminAssistant/1.0'}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
            docs = data.get("docs", [])
            if not docs:
                return None, None
            
            doc = docs[0]
            cover_i = doc.get("cover_i")
            image_url = f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg" if cover_i else None
            
            work_key = doc.get("key")
            description = None
            if work_key:
                work_url = f"https://openlibrary.org{work_key}.json"
                req_work = urllib.request.Request(
                    work_url,
                    headers={'User-Agent': 'BookstoreAdminAssistant/1.0'}
                )
                with urllib.request.urlopen(req_work, timeout=8) as work_response:
                    work_data = json.loads(work_response.read().decode('utf-8'))
                    desc_data = work_data.get("description", "")
                    if isinstance(desc_data, dict):
                        description = desc_data.get("value", "")
                    else:
                        description = str(desc_data)
                        
            if not description:
                description = doc.get("first_sentence") or ", ".join(doc.get("subject", [])[:3])
                
            return description or None, image_url or None
    except Exception as e:
        logger.warning("Open Library API search failed: %s", e)
        return None, None


def _get_actual_book_info(title: str, author: str = "") -> tuple[str | None, str | None]:
    """
    Search multiple APIs for actual book description and cover image.
    
    Priority for DESCRIPTION: Wikipedia → Open Library → Google Books
      (Wikipedia has the richest prose descriptions.)
    
    Priority for COVER IMAGE: Open Library → Google Books → Wikipedia
      (OL and GB have actual book cover databases; Wikipedia often
       returns author photos or unrelated thumbnails.)
    
    Returns (description, image_url).
    """
    desc = None
    img = None

    # ── Fetch from all sources ──────────────────────────────────────────
    wiki_desc, wiki_img = _fetch_from_wikipedia(title, author)

    ol_desc, ol_img = _fetch_from_open_library(title, author)
    if (not ol_desc or not ol_img) and author:
        ol_desc2, ol_img2 = _fetch_from_open_library(title, "")
        if not ol_desc and ol_desc2:
            ol_desc = ol_desc2
        if not ol_img and ol_img2:
            ol_img = ol_img2

    gb_desc, gb_img = _fetch_from_google_books(title, author)
    if (not gb_desc or not gb_img) and author:
        gb_desc2, gb_img2 = _fetch_from_google_books(title, "")
        if not gb_desc and gb_desc2:
            gb_desc = gb_desc2
        if not gb_img and gb_img2:
            gb_img = gb_img2

    # ── Pick best DESCRIPTION: Wikipedia → Open Library → Google Books ──
    desc = wiki_desc or ol_desc or gb_desc

    # ── Pick best COVER IMAGE: Open Library → Google Books → Wikipedia ──
    # OL and GB have dedicated book‑cover databases; Wikipedia thumbnails
    # are frequently author portraits or generic images.
    img = ol_img or gb_img or wiki_img

    return desc or None, img or None



def _resolve_actual_or_generated(title: str, author: str, custom_desc: str | None = None, custom_img: str | None = None) -> tuple[str, str]:
    actual_desc, actual_img = None, None
    if not custom_desc or not custom_img:
        actual_desc, actual_img = _get_actual_book_info(title, author)
        
    if custom_desc:
        final_desc = custom_desc
    elif actual_desc:
        final_desc = _clean_and_truncate_description(actual_desc)
    else:
        final_desc = _generate_book_description(title, author)
        
    if custom_img:
        final_img = custom_img
    elif actual_img:
        final_img = actual_img
    else:
        final_img = _generate_book_image_url(title, author)
        
    return final_desc, final_img



# ── Book lookup by name (fuzzy) ───────────────────────────────────────────────

def _find_book_by_name(name: str) -> tuple[Book | None, list[Book]]:
    """
    Find a book by name.  Returns (exact_match, candidates).
    - If an exact/close match is found: (book, [])
    - If multiple possible matches: (None, [book1, book2, ...])
    - If nothing found: (None, [])
    """
    db = SessionLocal()
    try:
        all_books = db.query(Book).all()
        if not all_books:
            return None, []

        clean = name.strip().lower()

        # 1) Exact title match (case-insensitive)
        for b in all_books:
            if b.title.strip().lower() == clean:
                return b, []

        # 2) Containment match — the query is contained in a title or vice versa
        contained = [b for b in all_books if clean in b.title.lower() or b.title.lower() in clean]
        if len(contained) == 1:
            return contained[0], []
        if len(contained) > 1:
            return None, contained

        # 3) Fuzzy match via difflib
        titles = [b.title for b in all_books]
        titles_lower = [t.lower() for t in titles]
        matches = difflib.get_close_matches(clean, titles_lower, n=3, cutoff=0.5)
        if matches:
            matched_books = [b for b in all_books if b.title.lower() in matches]
            if len(matched_books) == 1:
                return matched_books[0], []
            return None, matched_books

        return None, []
    finally:
        db.close()


def _format_book_candidates(candidates: list[Book]) -> str:
    """Format a list of candidate books for the admin to pick from."""
    lines = []
    for b in candidates[:8]:
        lines.append(f"• **{b.title}** by {b.author} (ID: {b.id})")
    return "\n".join(lines)


# ── Parse natural language for edit commands ──────────────────────────────────

EDITABLE_FIELDS = {
    "title": str, "author": str, "description": str, "price": float,
    "stock_quantity": int, "category_id": int, "image_url": str, "isbn": str,
}

# Aliases for more natural field references
FIELD_ALIASES = {
    "name": "title", "book name": "title", "book title": "title",
    "writer": "author", "written by": "author",
    "cost": "price", "amount": "price",
    "stock": "stock_quantity", "quantity": "stock_quantity", "copies": "stock_quantity",
    "inventory": "stock_quantity",
    "category": "category_id", "genre": "category_id",
    "image": "image_url", "cover": "image_url", "cover image": "image_url",
    "desc": "description", "summary": "description",
}


def _resolve_field_name(raw: str) -> str | None:
    """Resolve a user-typed field name to the canonical field key."""
    clean = raw.strip().lower()
    if clean in EDITABLE_FIELDS:
        return clean
    if clean in FIELD_ALIASES:
        return FIELD_ALIASES[clean]
    # fuzzy match on field names + aliases
    all_names = list(EDITABLE_FIELDS.keys()) + list(FIELD_ALIASES.keys())
    matches = difflib.get_close_matches(clean, all_names, n=1, cutoff=0.6)
    if matches:
        m = matches[0]
        return FIELD_ALIASES.get(m, m)
    return None


def _extract_edit_info(message: str) -> tuple[str | None, str | None, str | None]:
    """
    Try to extract book name, field, and value from a natural edit command.
    Examples:
      "change the price of Atomic Habits to 25"
      "update stock of Dune to 100"
      "edit title of old book to new title"
    Returns (book_name, field, value) — any or all may be None.
    """
    normalized = message.strip()

    # Pattern: "change/update/set <field> of <book> to <value>"
    m = re.match(
        r"(?:change|update|set|modify|edit)\s+(?:the\s+)?(.+?)\s+(?:of|for)\s+(.+?)\s+to\s+(.+)",
        normalized, re.IGNORECASE
    )
    if m:
        field = _resolve_field_name(m.group(1))
        book_name = m.group(2).strip().strip('"\'')
        value = m.group(3).strip().strip('"\'')
        return book_name, field, value

    # Pattern: "change <book>'s <field> to <value>"
    m = re.match(
        r"(?:change|update|set|modify|edit)\s+(.+?)(?:'s|'s)\s+(.+?)\s+to\s+(.+)",
        normalized, re.IGNORECASE
    )
    if m:
        book_name = m.group(1).strip().strip('"\'')
        field = _resolve_field_name(m.group(2))
        value = m.group(3).strip().strip('"\'')
        return book_name, field, value

    # Pattern: "<field> of <book> = <value>" or "<field> of <book> : <value>"
    m = re.match(
        r"(.+?)\s+(?:of|for)\s+(.+?)\s*[=:]\s*(.+)",
        normalized, re.IGNORECASE
    )
    if m:
        field = _resolve_field_name(m.group(1))
        book_name = m.group(2).strip().strip('"\'')
        value = m.group(3).strip().strip('"\'')
        if field:
            return book_name, field, value

    return None, None, None


def _extract_delete_book_name(message: str) -> str | None:
    """
    Extract the book name from a delete command.
    Examples: "delete The Great Gatsby", "remove Dune", "delete book Atomic Habits"
    """
    m = re.match(
        r"(?:delete|remove|drop)\s+(?:the\s+)?(?:book\s+)?(.+)",
        message.strip(), re.IGNORECASE
    )
    if m:
        name = m.group(1).strip().strip('"\'')
        if name:
            return name
    return None


def _extract_edit_book_name(message: str) -> str | None:
    """
    Extract just the book name from an edit command (when no field/value is given).
    Examples: "edit The Great Gatsby", "update Dune", "modify book Atomic Habits"
    """
    m = re.match(
        r"(?:edit|update|modify|change)\s+(?:the\s+)?(?:book\s+)?(.+)",
        message.strip(), re.IGNORECASE
    )
    if m:
        name = m.group(1).strip().strip('"\'')
        if name:
            return name
    return None


# ── Parse natural-language add book ──────────────────────────────────────────

def _parse_natural_add(message: str) -> dict | None:
    """
    Try to parse a natural-language or comma-separated add-book command.
    Examples:
      "add book Dune by Frank Herbert"
      "add book Dune, Frank Herbert"
      "create book Dune, Frank Herbert, price 12.99, stock 50, category Fiction"
    Returns a dict with extracted fields or None if we can't parse it.
    """
    cleaned = re.sub(
        r"^(?:add|create|new)\s+(?:a\s+|the\s+|new\s+)?(?:book\s+)?",
        "", message.strip(), flags=re.IGNORECASE
    ).strip()

    if not cleaned:
        return None

    result = {}

    # Try to extract "by <author>" early
    by_match = re.search(r"\bby\s+([^,]+)", cleaned, re.IGNORECASE)
    if by_match:
        result["author"] = by_match.group(1).strip().rstrip(",")
        title_part = cleaned[:by_match.start()].strip().rstrip(",")
        if title_part:
            result["title"] = title_part
            
        # Extract key-value pairs from the rest
        # price
        price_match = re.search(r"(?:price|cost)\s*[:\s]?\s*\$?([\d.]+)", cleaned, re.IGNORECASE)
        if not price_match:
            price_match = re.search(r"\$([\d.]+)", cleaned)
        if price_match:
            try:
                result["price"] = float(price_match.group(1))
            except ValueError:
                pass

        # stock
        stock_match = re.search(r"(?:stock|quantity|copies|inventory)\s*[:\s]?\s*(\d+)", cleaned, re.IGNORECASE)
        if not stock_match:
            stock_match = re.search(r"(\d+)\s*(?:copies|pieces|stock|in\s+stock)", cleaned, re.IGNORECASE)
        if stock_match:
            result["stock_quantity"] = int(stock_match.group(1))

        # category
        cat_match = re.search(r"(?:category|genre)\s*[:\s]?\s*(.+?)(?:,|$)", cleaned, re.IGNORECASE)
        if cat_match:
            cat_val = cat_match.group(1).strip()
            result["_category_raw"] = cat_val

        # description
        desc_match = re.search(r"(?:description|desc|summary)\s*[:\s]?\s*(.+?)(?:,\s*(?:price|stock|category|genre|image|cover)|$)", cleaned, re.IGNORECASE)
        if desc_match:
            result["description"] = desc_match.group(1).strip()

        # image
        img_match = re.search(r"(?:image|cover)\s*(?:url)?\s*[:\s]?\s*(https?://\S+)", cleaned, re.IGNORECASE)
        if img_match:
            result["image_url"] = img_match.group(1).strip()
    else:
        # Try to split by comma
        parts = [p.strip() for p in cleaned.split(",")]
        if len(parts) >= 2:
            result["title"] = parts[0]
            result["author"] = parts[1]
            if len(parts) >= 3:
                result["_price_raw"] = parts[2]
            if len(parts) >= 4:
                result["_stock_raw"] = parts[3]
            if len(parts) >= 5:
                result["_category_raw"] = parts[4]

    # Validate we have at least title and author
    if "title" in result and "author" in result:
        return result
    return None


def _resolve_category(raw: str) -> int | None:
    """Resolve a category name or ID string to a category ID."""
    # Try numeric first
    try:
        return int(raw)
    except ValueError:
        pass

    db = SessionLocal()
    try:
        cats = db.query(Category).all()
        if not cats:
            return None

        def _norm(s: str) -> str:
            return re.sub(r"[^a-z0-9]", "", s.lower())

        norm_to_cat = {_norm(c.name): c for c in cats}
        norm_query = _norm(raw)

        if norm_query in norm_to_cat:
            return norm_to_cat[norm_query].id

        norm_names = list(norm_to_cat.keys())
        matches = difflib.get_close_matches(norm_query, norm_names, n=1, cutoff=0.5)
        if matches:
            return norm_to_cat[matches[0]].id

        cat = db.query(Category).filter(Category.name.ilike(f"%{raw}%")).first()
        if cat:
            return cat.id
        return None
    finally:
        db.close()


def _parse_book_line(line: str, description_mode: str, default_image_url: str | None) -> tuple[dict | None, str | None]:
    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 2:
        return None, "Each book entry must include at least title and author (e.g. 'Dune, Frank Herbert')."

    title = parts[0]
    author = parts[1]
    
    # Defaults
    price = 19.99
    stock_quantity = 100
    category_id = 1
    
    # Parse price if provided
    if len(parts) >= 3 and parts[2]:
        price_str = parts[2]
        cleaned_price = price_str.replace(',', '')
        price_tokens = re.findall(r"[-+]?\d*\.?\d+", cleaned_price)
        for token in price_tokens:
            try:
                val = float(token)
                if val > 0:
                    price = val
                    break
            except ValueError:
                continue

    # Parse stock if provided
    if len(parts) >= 4 and parts[3]:
        stock_str = parts[3]
        cleaned_stock = re.sub(r"[^0-9]", "", stock_str)
        if cleaned_stock:
            stock_quantity = int(cleaned_stock)

    # Parse category if provided
    if len(parts) >= 5 and parts[4]:
        category_str = parts[4]
        try:
            category_id = int(category_str)
        except ValueError:
            db = SessionLocal()
            try:
                name = category_str.strip()
                cats = db.query(Category).all()
                if cats:
                    def _norm(s: str) -> str:
                        return re.sub(r"[^a-z0-9]", "", s.lower())

                    norm_to_cat = { _norm(c.name): c for c in cats }
                    norm_query = _norm(name)

                    if norm_query in norm_to_cat:
                        category_id = norm_to_cat[norm_query].id
                    else:
                        norm_names = list(norm_to_cat.keys())
                        matches = difflib.get_close_matches(norm_query, norm_names, n=1, cutoff=0.5)
                        if matches:
                            category_id = norm_to_cat[matches[0]].id
                        else:
                            cat = db.query(Category).filter(Category.name.ilike(f"%{name}%")).first()
                            if cat:
                                category_id = cat.id
            finally:
                db.close()

    # For description and image, we ALWAYS fetch/generate and override user input
    description, image_url = _resolve_actual_or_generated(title, author, None, default_image_url)

    payload = {
        "title": title,
        "author": author,
        "price": price,
        "stock_quantity": stock_quantity,
        "category_id": category_id,
        "description": description,
        "image_url": image_url,
        "isbn": None,
        "published_date": None,
    }
    return payload, None


def _parse_book_entries(message: str, description_mode: str, default_image_url: str | None) -> tuple[list[dict], list[str]]:
    lines = [line.strip() for line in re.split(r"[\r\n;]+", message) if line.strip()]
    if not lines:
        return [], ["No book entries were found. Please send at least one book."
        ]

    books = []
    errors = []
    for line in lines:
        entry, error = _parse_book_line(line, description_mode, default_image_url)
        if error:
            errors.append(f"Line: {line}\n{error}")
        else:
            books.append(entry)
    return books, errors


def _create_book_helper(session_id: str, parsed: dict, image_url: str | None) -> dict:
    title = parsed["title"]
    author = parsed["author"]
    
    # Defaults
    price = 19.99
    stock = 100
    category_id = 1
    
    # Resolve Price if provided
    if "price" in parsed:
        price = parsed["price"]
    elif "_price_raw" in parsed:
        try:
            price = float(re.findall(r"[\d.]+", parsed["_price_raw"])[0])
        except Exception:
            pass
            
    # Resolve Stock if provided
    if "stock_quantity" in parsed:
        stock = parsed["stock_quantity"]
    elif "_stock_raw" in parsed:
        try:
            stock = int(re.sub(r"[^0-9]", "", parsed["_stock_raw"]))
        except Exception:
            pass
            
    # Resolve Category if provided
    cat_raw = parsed.get("_category_raw")
    if cat_raw:
        cat_res = _resolve_category(cat_raw)
        if cat_res:
            category_id = cat_res
            
    # For description and image, we ALWAYS fetch/generate and override user input
    description, img = _resolve_actual_or_generated(title, author, None, image_url)

    try:
        db = SessionLocal()
        payload = BookCreate(
            title=title,
            author=author,
            price=price,
            stock_quantity=stock,
            category_id=category_id,
            description=description,
            image_url=img,
            isbn=None,
            published_date=None,
        )
        book = create_book(db, payload)
        db.close()
        _reset(session_id)
        return _reply(
            "NAVIGATE", "/admin/books",
            f"✅ Book **\"{book.title}\"** by {book.author} added successfully!\n\n"
            f"📖 **Description:** {description[:600]}{'...' if len(description) > 600 else ''}\n\n"
            f"(Price: ${book.price:.2f}, Stock: {book.stock_quantity}). Navigating to Book Management.",
            image_url=img,
        )
    except Exception as exc:
        _reset(session_id)
        return _reply("NONE", None, f"❌ Failed to create book: {exc}")


def _handle_add_book(session_id: str, message: str, image_url: str | None = None) -> dict:
    sess = _session(session_id)
    data = sess["data"]
    state = sess["state"]

    if state == "idle":
        natural = _parse_natural_add(message)
        if natural:
            return _create_book_helper(session_id, natural, image_url)
            
        sess["state"] = "add_book_collect"
        return _reply("NONE", None, "What book would you like to add? Please provide the title and author (e.g. **Dune by Frank Herbert** or **Dune, Frank Herbert**).")

    if state == "add_book_collect":
        if _is_cancel(message):
            _reset(session_id)
            return _reply("NONE", None, "Book creation cancelled.")
            
        parsed = _parse_natural_add(message)
        if parsed and parsed.get("title") and parsed.get("author"):
            return _create_book_helper(session_id, parsed, image_url)
            
        return _reply("NONE", None, "I couldn't parse the title and author. Please try again (e.g. **Dune by Frank Herbert** or **Dune, Frank Herbert**) or type **cancel**.")


def _session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {"state": "idle", "data": {}}
    return _sessions[session_id]


def _reset(session_id: str) -> None:
    _sessions[session_id] = {"state": "idle", "data": {}}


def _reply(action: str, target: Optional[str], text: str, image_url: Optional[str] = None) -> dict:
    return {"action": action, "target": target, "reply": text, "image_url": image_url}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize(msg: str) -> str:
    return re.sub(r"\s+", " ", msg.strip().lower())


def _is_cancel(msg: str) -> bool:
    return _normalize(msg) in {"cancel", "stop", "quit", "exit", "abort"}


def _next_missing_field(data: dict, fields: list) -> Optional[str]:
    for f in fields:
        if f not in data:
            return f
    return None


# ── Intent detection (idle state) ─────────────────────────────────────────────

def _detect_intent(normalized: str) -> Optional[str]:
    if any(k in normalized for k in ["add book", "add a book", "create book", "new book"]):
        return "add_book_start"
    if any(k in normalized for k in ["delete book", "remove book", "delete a book",
                                      "remove a book", "drop book"]):
        return "delete_book_start"
    # Check for "delete <bookname>" pattern (delete without "book" keyword)
    if re.match(r"(?:delete|remove|drop)\s+", normalized):
        return "delete_book_start"
    if any(k in normalized for k in ["edit book", "edit a book", "update book", "modify book", "change book"]):
        return "edit_book_start"
    # Check for edit patterns like "change the price of..." or "update stock of..."
    if re.match(r"(?:change|update|set|modify|edit)\s+(?:the\s+)?(?:price|stock|title|author|description|category|image|cover|name|cost|quantity|copies|inventory|isbn|desc|summary)", normalized):
        return "edit_book_start"
    # Flexible fallback: user says something like "edit a book: change description..."
    if any(k in normalized for k in ["edit", "change", "update", "modify"]):
        if any(f in normalized for f in ["price", "stock", "title", "author", "description", "category", "image", "cover", "isbn"]):
            return "edit_book_start"
    if any(k in normalized for k in ["users", "manage users", "user management", "customers"]):
        return "nav_users"
    if any(k in normalized for k in ["sessions", "active sessions", "user sessions"]):
        return "nav_sessions"
    if any(k in normalized for k in ["books", "products", "inventory", "manage books", "book list"]):
        return "nav_books"
    if any(k in normalized for k in ["dashboard", "analytics", "stats", "statistics", "home", "orders"]):
        return "nav_dashboard"
    return None


# ── ADD BOOK flow ─────────────────────────────────────────────────────────────

def _do_create_book(session_id: str, data: dict) -> dict:
    try:
        db = SessionLocal()
        payload = BookCreate(
            title=data["title"],
            author=data["author"],
            price=data["price"],
            stock_quantity=data["stock_quantity"],
            category_id=data["category_id"],
            description=data.get("description"),
            image_url=data.get("image_url"),
            isbn=data.get("isbn"),
            published_date=None,
        )
        book = create_book(db, payload)
        db.close()
        _reset(session_id)
        return _reply(
            "NAVIGATE",
            "/admin/books",
            f"✅ Book **\"{book.title}\"** added successfully (ID: {book.id})! Navigating to Book Management.",
        )
    except Exception as exc:
        _reset(session_id)
        return _reply("NONE", None, f"❌ Failed to create book: {exc}")


# ── DELETE BOOK flow ──────────────────────────────────────────────────────────

def _handle_delete_book(session_id: str, message: str) -> dict:
    sess = _session(session_id)
    data = sess["data"]
    state = sess["state"]

    if _is_cancel(message):
        _reset(session_id)
        return _reply("NONE", None, "Delete cancelled.")

    if state == "idle":
        # Try to extract book name from the initial command
        book_name = _extract_delete_book_name(message)
        if book_name:
            book, candidates = _find_book_by_name(book_name)
            if book:
                data["book_id"] = book.id
                data["book_title"] = book.title
                sess["state"] = "delete_book_confirm"
                return _reply(
                    "NONE", None,
                    f"⚠️ Are you sure you want to permanently delete **\"{book.title}\"** by {book.author} "
                    f"(ID: {book.id})?\nType **yes** to confirm or **cancel** to abort."
                )
            if candidates:
                data["_pending_candidates"] = [(b.id, b.title, b.author) for b in candidates]
                sess["state"] = "delete_book_pick"
                return _reply(
                    "NONE", None,
                    f"I found multiple books matching \"{book_name}\":\n"
                    + _format_book_candidates(candidates)
                    + "\n\nWhich one did you mean? Type the exact name."
                )
            # Not found
            sess["state"] = "delete_book_ask_name"
            return _reply("NONE", None,
                f"I couldn't find a book matching \"{book_name}\". "
                "Please provide the exact book name or type 'cancel'."
            )

        # No name in the command — ask for it
        sess["state"] = "delete_book_ask_name"
        return _reply("NONE", None, "Which book do you want to delete? Please provide the **book name**.")

    if state == "delete_book_ask_name" or state == "delete_book_pick":
        name = message.strip()
        book, candidates = _find_book_by_name(name)
        if book:
            data["book_id"] = book.id
            data["book_title"] = book.title
            sess["state"] = "delete_book_confirm"
            return _reply(
                "NONE", None,
                f"⚠️ Are you sure you want to permanently delete **\"{book.title}\"** by {book.author} "
                f"(ID: {book.id})?\nType **yes** to confirm or **cancel** to abort."
            )
        if candidates:
            data["_pending_candidates"] = [(b.id, b.title, b.author) for b in candidates]
            sess["state"] = "delete_book_pick"
            return _reply(
                "NONE", None,
                f"I found multiple books matching \"{name}\":\n"
                + _format_book_candidates(candidates)
                + "\n\nWhich one did you mean? Type the exact name."
            )
        return _reply("NONE", None,
            f"No book found matching \"{name}\". Please try again or type 'cancel'."
        )

    if state == "delete_book_confirm":
        if message.strip().lower() in {"yes", "y", "confirm", "delete"}:
            try:
                db = SessionLocal()
                delete_book(db, data["book_id"])
                db.close()
                title = data.get("book_title", "the book")
                _reset(session_id)
                return _reply("NAVIGATE", "/admin/books", f"✅ **\"{title}\"** has been deleted successfully.")
            except Exception as exc:
                _reset(session_id)
                return _reply("NONE", None, f"❌ Failed to delete: {exc}")
        _reset(session_id)
        return _reply("NONE", None, "Delete cancelled.")

    return _reply("NONE", None, "Unexpected state. Type 'cancel' to restart.")


# ── REFRESH book content (description + image from web) ──────────────────────

def _extract_refresh_book_name(message: str) -> str | None:
    """
    Detect commands like:
      "change description and image of The Psychology of Money"
      "update description of Atomic Habits"
      "refresh image and description of 1984"
      "regenerate cover of Dune"
    Returns the book name if detected, otherwise None.
    """
    patterns = [
        r"(?:change|update|refresh|regenerate|fix|redo|fetch|auto.?fill)\s+"
        r"(?:the\s+)?(?:description|image|cover|desc|summary)\s+"
        r"(?:and\s+(?:the\s+)?(?:description|image|cover|desc|summary)\s+)?"
        r"(?:of|for)\s+(.+)",
        r"(?:change|update|refresh|regenerate|fix|redo|fetch|auto.?fill)\s+"
        r"(?:the\s+)?(?:description|image|cover|desc|summary)\s+and\s+"
        r"(?:the\s+)?(?:description|image|cover|desc|summary)\s+"
        r"(?:of|for)\s+(.+)",
    ]
    for pat in patterns:
        m = re.search(pat, message.strip(), re.IGNORECASE)
        if m:
            return m.group(1).strip().strip('"\'')
    return None


def _refresh_book_content(session_id: str, book: Book, refresh_desc: bool = True, refresh_img: bool = True) -> dict:
    """Fetch fresh description and/or image from the web and save to the book."""
    try:
        new_desc, new_img = _get_actual_book_info(book.title, book.author)

        current = {
            "title": book.title,
            "author": book.author,
            "description": book.description,
            "price": book.price,
            "stock_quantity": book.stock_quantity,
            "category_id": book.category_id,
            "image_url": book.image_url,
            "isbn": book.isbn,
        }

        changes = []
        if refresh_desc and new_desc:
            cleaned = _clean_and_truncate_description(new_desc)
            current["description"] = cleaned
            changes.append("description")
        if refresh_img and new_img:
            current["image_url"] = new_img
            changes.append("image")

        # Fall back to AI-generated image if nothing found
        if refresh_img and not new_img:
            current["image_url"] = _generate_book_image_url(book.title, book.author)
            changes.append("image (AI-generated)")

        db = SessionLocal()
        payload = BookUpdate(
            title=current["title"],
            author=current["author"],
            price=float(current["price"]),
            stock_quantity=int(current["stock_quantity"]),
            category_id=int(current["category_id"]),
            description=current["description"],
            image_url=current["image_url"],
            isbn=current["isbn"],
            published_date=None,
        )
        update_book(db, book.id, payload)
        db.close()
        _reset(session_id)

        changed_str = " and ".join(changes) if changes else "nothing (no data found online)"
        desc_preview = current["description"][:300] if current["description"] else "N/A"
        return _reply(
            "NAVIGATE", "/admin/books",
            f"✅ Updated **\"{book.title}\"** — refreshed {changed_str} from the web.\n\n"
            f"📖 **Description:** {desc_preview}{'...' if len(current['description'] or '') > 300 else ''}",
            image_url=current["image_url"],
        )
    except Exception as exc:
        _reset(session_id)
        return _reply("NONE", None, f"❌ Failed to refresh book content: {exc}")


# ── EDIT BOOK flow ────────────────────────────────────────────────────────────

def _handle_edit_book(session_id: str, message: str) -> dict:
    sess = _session(session_id)
    data = sess["data"]
    state = sess["state"]

    if _is_cancel(message):
        _reset(session_id)
        return _reply("NONE", None, "Edit cancelled.")

    if state == "idle":
        # ── Special: auto-refresh description and/or image from web ──
        wants_desc = bool(re.search(r"\b(description|desc|summary)\b", message, re.IGNORECASE))
        wants_img  = bool(re.search(r"\b(image|cover|photo|picture|thumbnail)\b", message, re.IGNORECASE))
        refresh_name = _extract_refresh_book_name(message)
        if refresh_name and (wants_desc or wants_img):
            book, candidates = _find_book_by_name(refresh_name)
            if book:
                return _refresh_book_content(session_id, book, refresh_desc=wants_desc, refresh_img=wants_img)
            if candidates:
                data["_pending_candidates"] = [(b.id, b.title, b.author) for b in candidates]
                data["_pending_refresh_desc"] = wants_desc
                data["_pending_refresh_img"] = wants_img
                sess["state"] = "edit_book_pick_for_refresh"
                return _reply(
                    "NONE", None,
                    f"I found multiple books matching \"{refresh_name}\":\n"
                    + _format_book_candidates(candidates)
                    + "\n\nWhich one did you mean? Type the exact name."
                )
            sess["state"] = "edit_book_ask_name"
            data["_pending_refresh_desc"] = wants_desc
            data["_pending_refresh_img"]  = wants_img
            return _reply("NONE", None,
                f"I couldn't find a book matching \"{refresh_name}\". "
                "Please provide the exact book name or type 'cancel'."
            )

        # Try to extract book name + field + value from a one-shot command
        book_name, field, value = _extract_edit_info(message)

        if book_name and field and value:
            # Full one-shot edit: "change price of Dune to 25"
            book, candidates = _find_book_by_name(book_name)
            if book:
                return _apply_one_shot_edit(session_id, book, field, value)
            if candidates:
                # Save the pending edit info and ask which book
                data["_pending_field"] = field
                data["_pending_value"] = value
                data["_pending_candidates"] = [(b.id, b.title, b.author) for b in candidates]
                sess["state"] = "edit_book_pick_for_oneshot"
                return _reply(
                    "NONE", None,
                    f"I found multiple books matching \"{book_name}\":\n"
                    + _format_book_candidates(candidates)
                    + "\n\nWhich one did you mean? Type the exact name."
                )
            sess["state"] = "edit_book_ask_name"
            data["_pending_field"] = field
            data["_pending_value"] = value
            return _reply("NONE", None,
                f"I couldn't find a book matching \"{book_name}\". "
                "Please provide the exact book name or type 'cancel'."
            )

        # Try to extract just a book name: "edit The Great Gatsby"
        book_name_only = _extract_edit_book_name(message)
        if book_name_only:
            book, candidates = _find_book_by_name(book_name_only)
            if book:
                return _enter_field_edit_mode(sess, data, book)
            if candidates:
                data["_pending_candidates"] = [(b.id, b.title, b.author) for b in candidates]
                sess["state"] = "edit_book_pick"
                return _reply(
                    "NONE", None,
                    f"I found multiple books matching \"{book_name_only}\":\n"
                    + _format_book_candidates(candidates)
                    + "\n\nWhich one did you mean? Type the exact name."
                )
            sess["state"] = "edit_book_ask_name"
            return _reply("NONE", None,
                f"I couldn't find a book matching \"{book_name_only}\". "
                "Please provide the exact book name or type 'cancel'."
            )

        # No name extracted at all — ask for it
        sess["state"] = "edit_book_ask_name"
        return _reply("NONE", None, "Which book do you want to edit? Please provide the **book name**.")

    if state in ("edit_book_ask_name", "edit_book_pick", "edit_book_pick_for_refresh"):
        name = message.strip()
        book, candidates = _find_book_by_name(name)
        if book:
            # Handle pending refresh
            if sess["state"] == "edit_book_pick_for_refresh" or (data.get("_pending_refresh_desc") is not None or data.get("_pending_refresh_img") is not None):
                rd = data.get("_pending_refresh_desc", True)
                ri = data.get("_pending_refresh_img", True)
                return _refresh_book_content(session_id, book, refresh_desc=rd, refresh_img=ri)
            # Check if we had a pending one-shot edit
            if data.get("_pending_field") and data.get("_pending_value"):
                return _apply_one_shot_edit(session_id, book, data["_pending_field"], data["_pending_value"])
            return _enter_field_edit_mode(sess, data, book)
        if candidates:
            data["_pending_candidates"] = [(b.id, b.title, b.author) for b in candidates]
            sess["state"] = "edit_book_pick"
            return _reply(
                "NONE", None,
                f"I found multiple books matching \"{name}\":\n"
                + _format_book_candidates(candidates)
                + "\n\nWhich one did you mean? Type the exact name."
            )
        return _reply("NONE", None,
            f"No book found matching \"{name}\". Please try again or type 'cancel'."
        )

    if state == "edit_book_pick_for_oneshot":
        name = message.strip()
        book, candidates = _find_book_by_name(name)
        if book:
            if data.get("_pending_field") and data.get("_pending_value"):
                return _apply_one_shot_edit(session_id, book, data["_pending_field"], data["_pending_value"])
            return _enter_field_edit_mode(sess, data, book)
        if candidates:
            return _reply(
                "NONE", None,
                f"Still multiple matches. Please type the exact full name of the book:\n"
                + _format_book_candidates(candidates)
            )
        return _reply("NONE", None,
            f"No book found matching \"{name}\". Please try again or type 'cancel'."
        )

    if state == "edit_book_ask_field":
        stripped = message.strip().lower()
        if stripped == "done":
            return _do_update_book(session_id, data)

        # Try to parse "field to value" or "field = value" or "field: value" patterns
        inline_match = re.match(r"(.+?)\s*(?:to|=|:)\s*(.+)", stripped)
        if inline_match:
            field_name = _resolve_field_name(inline_match.group(1).strip())
            if field_name:
                raw_value = inline_match.group(2).strip()
                try:
                    cast = EDITABLE_FIELDS[field_name]
                    if field_name == "category_id":
                        resolved = _resolve_category(raw_value)
                        if resolved:
                            data["current"][field_name] = resolved
                        else:
                            return _reply("NONE", None, f"Unknown category \"{raw_value}\". Please try again.")
                    else:
                        data["current"][field_name] = cast(raw_value)
                    return _reply(
                        "NONE", None,
                        f"✔ **{field_name}** updated to `{raw_value}`.\n"
                        f"Change another field or type **done** to save."
                    )
                except (ValueError, KeyError):
                    return _reply("NONE", None, f"Invalid value for {field_name}. Please try again.")

        # Try as just a field name
        field = _resolve_field_name(stripped)
        if field:
            data["editing_field"] = field
            sess["state"] = "edit_book_ask_value"
            current_val = data["current"].get(field, "N/A")
            return _reply("NONE", None, f"Current **{field}**: `{current_val}`\nEnter new value:")

        return _reply("NONE", None,
            f"Unknown field '{stripped}'. Choose from: {', '.join(EDITABLE_FIELDS.keys())} or type 'done'.\n"
            f"You can also type something like: **price to 25** or **stock = 100**"
        )

    if state == "edit_book_ask_value":
        field = data.get("editing_field")
        raw = message.strip()
        try:
            cast = EDITABLE_FIELDS[field]
            if field == "category_id":
                resolved = _resolve_category(raw)
                if resolved:
                    data["current"][field] = resolved
                else:
                    return _reply("NONE", None, f"Unknown category \"{raw}\". Please try again.")
            else:
                data["current"][field] = cast(raw)
        except (ValueError, KeyError):
            return _reply("NONE", None, f"Invalid value for {field}. Please try again.")
        sess["state"] = "edit_book_ask_field"
        return _reply(
            "NONE", None,
            f"✔ **{field}** updated to `{raw}`.\n"
            f"Change another field or type **done** to save."
        )

    return _reply("NONE", None, "Unexpected state. Type 'cancel' to restart.")


def _enter_field_edit_mode(sess: dict, data: dict, book: Book) -> dict:
    """Set up the session for multi-field editing of a book."""
    data["book_id"] = book.id
    data["current"] = {
        "title": book.title, "author": book.author, "description": book.description,
        "price": book.price, "stock_quantity": book.stock_quantity,
        "category_id": book.category_id, "image_url": book.image_url, "isbn": book.isbn,
    }
    sess["state"] = "edit_book_ask_field"
    fields_str = ", ".join(EDITABLE_FIELDS.keys())
    return _reply(
        "NONE", None,
        f"Editing **\"{book.title}\"** by {book.author}.\n"
        f"Which field do you want to change? Options: {fields_str}\n"
        f"You can type: **price to 25** or just the field name.\n"
        f"Type **done** to save, **cancel** to abort."
    )


def _apply_one_shot_edit(session_id: str, book: Book, field: str, value: str) -> dict:
    """Apply a single field edit in one shot and save immediately."""
    try:
        cast = EDITABLE_FIELDS[field]
        if field == "category_id":
            casted_value = _resolve_category(value)
            if casted_value is None:
                return _reply("NONE", None, f"Unknown category \"{value}\". Edit cancelled.")
        else:
            casted_value = cast(value)
    except (ValueError, KeyError):
        _reset(session_id)
        return _reply("NONE", None, f"Invalid value \"{value}\" for field **{field}**. Edit cancelled.")

    try:
        db = SessionLocal()
        # Build update payload from current book data
        current = {
            "title": book.title, "author": book.author, "description": book.description,
            "price": book.price, "stock_quantity": book.stock_quantity,
            "category_id": book.category_id, "image_url": book.image_url, "isbn": book.isbn,
        }
        current[field] = casted_value

        payload = BookUpdate(
            title=current["title"],
            author=current["author"],
            price=float(current["price"]),
            stock_quantity=int(current["stock_quantity"]),
            category_id=int(current["category_id"]) if current.get("category_id") else 1,
            description=current.get("description"),
            image_url=current.get("image_url"),
            isbn=current.get("isbn"),
            published_date=None,
        )
        updated_book = update_book(db, book.id, payload)
        db.close()
        _reset(session_id)
        return _reply(
            "NAVIGATE", "/admin/books",
            f"✅ Updated **\"{updated_book.title}\"** — **{field}** changed to `{value}`."
        )
    except Exception as exc:
        _reset(session_id)
        return _reply("NONE", None, f"❌ Failed to update book: {exc}")


def _do_update_book(session_id: str, data: dict) -> dict:
    try:
        db = SessionLocal()
        current = data["current"]
        payload = BookUpdate(
            title=current["title"],
            author=current["author"],
            price=float(current["price"]),
            stock_quantity=int(current["stock_quantity"]),
            category_id=int(current["category_id"]) if current.get("category_id") else 1,
            description=current.get("description"),
            image_url=current.get("image_url"),
            isbn=current.get("isbn"),
            published_date=None,
        )
        book = update_book(db, data["book_id"], payload)
        db.close()
        _reset(session_id)
        return _reply("NAVIGATE", "/admin/books", f"✅ **\"{book.title}\"** updated successfully!")
    except Exception as exc:
        _reset(session_id)
        return _reply("NONE", None, f"❌ Failed to update book: {exc}")


# ── Main entry point ──────────────────────────────────────────────────────────

def process_admin_command(message: str, session_id: str = "default", image_url: str | None = None) -> dict:
    sess = _session(session_id)
    state = sess["state"]
    normalized = _normalize(message)

    # Allow cancel from any state
    if _is_cancel(message) and state != "idle":
        _reset(session_id)
        return _reply("NONE", None, "Operation cancelled. How can I help you?")

    # Route active flows
    if state.startswith("add_book"):
        return _handle_add_book(session_id, message, image_url=image_url)
    if state.startswith("delete_book"):
        return _handle_delete_book(session_id, message)
    if state.startswith("edit_book"):
        return _handle_edit_book(session_id, message)

    # Idle — detect intent
    intent = _detect_intent(normalized)

    if intent == "add_book_start":
        return _handle_add_book(session_id, message, image_url=image_url)
    if intent == "delete_book_start":
        return _handle_delete_book(session_id, message)
    if intent == "edit_book_start":
        return _handle_edit_book(session_id, message)
    if intent == "nav_users":
        return _reply("NAVIGATE", "/admin/users", "Navigating to User Management...")
    if intent == "nav_sessions":
        return _reply("NAVIGATE", "/admin/sessions", "Navigating to Session Management...")
    if intent == "nav_books":
        return _reply("NAVIGATE", "/admin/books", "Navigating to Book Management...")
    if intent == "nav_dashboard":
        return _reply("NAVIGATE", "/admin", "Navigating to the Admin Dashboard...")

    return _reply(
        "NONE", None,
        "I can help you with:\n"
        "• Navigate: 'go to users', 'manage books', 'show sessions'\n"
        "• Add a book: 'add book Dune by Frank Herbert, price 12.99, stock 50, category Fiction'\n"
        "• Edit a book: 'change the price of Atomic Habits to 25'\n"
        "• Delete a book: 'delete The Great Gatsby'\n\n"
        "Just tell me what you need naturally!"
    )

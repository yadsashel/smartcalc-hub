import os
import json
import re
from datetime import datetime, timezone
from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

DATA_FILE = "data/topics.json"
PUBLIC_DIR = "public"
SITE_URL = "https://smartcalc-hub.pages.dev"

os.makedirs(PUBLIC_DIR, exist_ok=True)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def generate_calculator_page(item: dict) -> str:
    title = item["title"]
    category = item.get("category", "General Tools")
    slug = slugify(title)

    prompt = f"""
    Create a complete, standalone, responsive HTML5 calculator tool page in English targeting the search query: "{title}" under the category "{category}".

    Requirements:
    1. Use Tailwind CSS via CDN (<script src="https://cdn.tailwindcss.com"></script>).
    2. Build a clean, modern, dark-mode interactive calculator widget using pure Vanilla JavaScript that accurately calculates what the user is searching for. Include clear input labels, sensible default values, a Calculate button, and instant results display.
    3. Display a subtle category tag for "{category}" at the top of the card.
    4. Include two clearly marked placeholder divs for ads:
       <div id="ad-top" class="my-4 text-center"><!-- PASTE AD CODE HERE --></div>
       <div id="ad-bottom" class="my-6 text-center"><!-- PASTE AD CODE HERE --></div>
    5. Below the calculator, write a helpful, SEO-optimized guide explaining the formula, real-world examples, and 3 concise FAQs.
    6. Include proper <title>, <meta name="description">, and <link rel="canonical" href="{SITE_URL}/{slug}.html">.
    7. Return ONLY valid raw HTML starting with <!DOCTYPE html>. Do not wrap in markdown backticks.
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    html = (response.text or "").strip()
    html = re.sub(r"^```html\s*", "", html, flags=re.IGNORECASE)
    html = re.sub(r"^```\s*", "", html)
    html = re.sub(r"\s*```$", "", html)
    return html


def rebuild_index_and_sitemap(published_pages: list) -> None:
    cards_html = "\n".join([
        f'<a href="/{p["slug"]}.html" class="block p-4 bg-slate-900 rounded-xl hover:bg-slate-800 border border-slate-800 transition">'
        f'<span class="inline-block text-xs font-medium px-2.5 py-0.5 rounded-full bg-purple-950 text-purple-300 border border-purple-800/50 mb-2">{p.get("category", "Tool")}</span>'
        f'<h2 class="text-lg font-semibold text-white">{p["title"]}</h2>'
        f'<p class="text-sm text-slate-400 mt-1">Instant free online calculator &amp; guide</p>'
        f'</a>'
        for p in published_pages
    ])

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartCalc Hub - Free Online Calculators &amp; Tools</title>
    <meta name="description" content="Free, fast, and accurate online calculators for finance, business, fitness, tech, and daily decisions.">
    <script src="[https://cdn.tailwindcss.com](https://cdn.tailwindcss.com)"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen p-6">
    <div class="max-w-5xl mx-auto">
        <header class="text-center my-10">
            <h1 class="text-4xl font-bold text-white tracking-tight">SmartCalc Hub</h1>
            <p class="text-slate-400 mt-2">Fast, accurate calculators for everyday decisions.</p>
        </header>
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {cards_html}
        </div>
    </div>
</body>
</html>"""

    with open(f"{PUBLIC_DIR}/index.html", "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [f"<url><loc>{SITE_URL}/</loc><lastmod>{today}</lastmod><priority>1.0</priority></url>"]
    for p in published_pages:
        urls.append(
            f"<url><loc>{SITE_URL}/{p['slug']}.html</loc><lastmod>{today}</lastmod><priority>0.8</priority></url>"
        )

    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="[http://www.sitemaps.org/schemas/sitemap/0.9](http://www.sitemaps.org/schemas/sitemap/0.9)">
{chr(10).join(urls)}
</urlset>"""

    with open(f"{PUBLIC_DIR}/sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap)


def main() -> None:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    pending = data.get("pending", [])
    published = data.get("published", [])

    if not pending:
        print("No more pending topics!")
        return

    batch = pending[:5]
    remaining = pending[5:]

    for item in batch:
        title = item["title"]
        category = item.get("category", "General Tools")
        slug = slugify(title)
        print(f"Generating [{category}]: {title} -> {slug}.html")
        try:
            html_content = generate_calculator_page(item)
            with open(f"{PUBLIC_DIR}/{slug}.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            published.append({
                "id": item.get("id"),
                "category": category,
                "title": title,
                "slug": slug,
            })
        except Exception as e:
            print(f"Error on '{title}': {e}")
            remaining.insert(0, item)

    data["pending"] = remaining
    data["published"] = published

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    rebuild_index_and_sitemap(published)
    print(f"Done! Published total: {len(published)} | Remaining pending: {len(remaining)}")


if __name__ == "__main__":
    main()
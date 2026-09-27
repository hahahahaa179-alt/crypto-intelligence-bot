import os
import requests
import feedparser
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# API Endpoints
COINGECKO_PRICES_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true"
COINGECKO_TRENDING_URL = "https://api.coingecko.com/api/v3/search/trending"
DEFILLAMA_TVL_URL = "https://api.llama.fi/protocols"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

RSS_FEEDS = {
    "CoinTelegraph": "https://cointelegraph.com/rss",
    "Decrypt": "https://decrypt.co/feed",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "BitcoinMagazine": "https://bitcoinmagazine.com/.rss/full/"
}


def fetch_crypto_prices():
    """Mengambil data harga & perubahan 24 jam untuk BTC, ETH, dan SOL."""
    try:
        response = requests.get(COINGECKO_PRICES_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Gagal mengambil data harga CoinGecko: {e}")
        return None


def fetch_trending_coins():
    """Mengambil daftar koin yang sedang trending di CoinGecko."""
    try:
        response = requests.get(COINGECKO_TRENDING_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        trending_list = [item['item']['symbol'].upper() for item in data.get('coins', [])[:5]]
        return trending_list
    except Exception as e:
        print(f"[ERROR] Gagal mengambil data trending CoinGecko: {e}")
        return []


def fetch_top_tvl_protocols():
    """Mengambil Top 5 Protokol DeFi berdasarkan TVL dari DefiLlama."""
    try:
        response = requests.get(DEFILLAMA_TVL_URL, timeout=10)
        response.raise_for_status()
        protocols = response.json()
        # Urutkan berdasarkan TVL tertinggi
        sorted_protocols = sorted(protocols, key=lambda x: x.get('tvl', 0), reverse=True)[:5]
        tvl_data = [
            {"name": p.get('name'), "tvl_usd": f"${p.get('tvl', 0):,.0f}", "chain": p.get('chain')}
            for p in sorted_protocols
        ]
        return tvl_data
    except Exception as e:
        print(f"[ERROR] Gagal mengambil data TVL DefiLlama: {e}")
        return []


def fetch_rss_news():
    """Mengambil berita terbaru dari berbagai sumber RSS."""
    news_items = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:  # Ambil 2 berita teratas per sumber
                news_items.append({
                    "source": source,
                    "title": entry.title,
                    "link": entry.link
                })
        except Exception as e:
            print(f"[WARN] Gagal mengambil RSS dari {source}: {e}")
    return news_items


def generate_groq_report(raw_data):
    """Mengirim data mentah ke Groq API untuk menghasilkan ringkasan AI."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY tidak ditemukan di environment variables.")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = (
        "Anda adalah seorang Senior Crypto Intelligence Analyst. Tugas Anda adalah mengolah "
        "data pasar crypto mentah menjadi laporan intelijen eksekutif bernama "
        "'ALL-IN-ONE CRYPTO ALPHA REPORT'. Laporan harus ditulis dalam Bahasa Indonesia "
        "berformat Markdown lengkap dengan emoji yang relevan, ringkas, tajam, dan mudah dibaca."
    )

    user_prompt = f""" Berikut adalah data pasar crypto terbaru:

--- DATA HARGA UTAMA ---
{raw_data.get('prices')}

--- KOIN TRENDING (COINGECKO) ---
{raw_data.get('trending')}

--- TOP 5 DEFI PROTOCOL BY TVL (DEFILLAMA) ---
{raw_data.get('tvl')}

--- BERITA KRIPTO TERBARU ---
{raw_data.get('news')}

Format Laporan yang Diinginkan:
# 🚀 ALL-IN-ONE CRYPTO ALPHA REPORT

### 📊 Ringkasan Pasar & Harga
- Berikan insight singkat pergerakan BTC, ETH, SOL.

### 🔥 Trending Coins & DeFi TVL
- Rangkum koin trending dan tren TVL protokol DeFi.

### 📰 Berita Kunci & Sentimen Pasar
- Buat 3-4 poin ringkasan berita terpenting dan dampaknya pada pasar.

### 💡 Kesimpulan Analis (Alpha Take)
- Analisis singkat sentimen pasar (Bullish/Bearish/Neutral) & rekomendasi perhatian fokus trader.
"""

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 1000
    }

    try:
        response = requests.post(GROQ_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"[ERROR] Gagal memproses prompt di Groq API: {e}")
        return None


def send_to_discord(content):
    """Mengirimkan laporan akhir ke Discord Webhook."""
    if not DISCORD_WEBHOOK_URL:
        raise ValueError("DISCORD_WEBHOOK_URL tidak ditemukan di environment variables.")

    chunk_size = 1900
    chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]

    for chunk in chunks:
        payload = {"content": chunk}
        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"[ERROR] Gagal mengirim pesan ke Discord Webhook: {e}")


def main():
    print("[INFO] Mengumpulkan data pasar crypto...")
    
    prices = fetch_crypto_prices()
    trending = fetch_trending_coins()
    tvl = fetch_top_tvl_protocols()
    news = fetch_rss_news()

    raw_data = {
        "prices": prices,
        "trending": trending,
        "tvl": tvl,
        "news": news
    }

    print("[INFO] Menganalisis data dengan Groq AI (Llama 3.1 8B)...")
    report = generate_groq_report(raw_data)

    if report:
        print("[INFO] Mengirimkan laporan ke Discord Webhook...")
        send_to_discord(report)
        print("[SUCCESS] Laporan Crypto Alpha berhasil dikirim!")
    else:
        print("[FAIL] Gagal membuat laporan AI.")


if __name__ == "__main__":
    main()

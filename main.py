import os
import requests
import feedparser
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

COINGECKO_PRICES_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true"
COINGECKO_TRENDING_URL = "https://api.coingecko.com/api/v3/search/trending"
DEFILLAMA_TVL_URL = "https://api.llama.fi/protocols"

RSS_FEEDS = {
    "CoinTelegraph": "https://cointelegraph.com/rss",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/"
}

def fetch_crypto_prices():
    try:
        res = requests.get(COINGECKO_PRICES_URL, timeout=10).json()
        btc = res.get('bitcoin', {})
        eth = res.get('ethereum', {})
        sol = res.get('solana', {})
        return (
            f"• **BTC**: ${btc.get('usd', 0):,} ({btc.get('usd_24h_change', 0):.2f}%)\n"
            f"• **ETH**: ${eth.get('usd', 0):,} ({eth.get('usd_24h_change', 0):.2f}%)\n"
            f"• **SOL**: ${sol.get('usd', 0):,} ({sol.get('usd_24h_change', 0):.2f}%)"
        )
    except Exception as e:
        return f"Gagal mengambil data harga: {e}"

def fetch_trending_coins():
    try:
        res = requests.get(COINGECKO_TRENDING_URL, timeout=10).json()
        coins = res.get('coins', [])[:5]
        trending_list = [f"• {c['item']['name']} ({c['item']['symbol']})" for c in coins]
        return "\n".join(trending_list) if trending_list else "Tidak ada data trending."
    except Exception as e:
        return f"Gagal mengambil data trending: {e}"

def fetch_top_tvl_protocols():
    try:
        res = requests.get(DEFILLAMA_TVL_URL, timeout=10).json()
        valid_protocols = [p for p in res if isinstance(p, dict) and p.get('tvl') is not None]
        sorted_protocols = sorted(valid_protocols, key=lambda x: x.get('tvl', 0), reverse=True)[:3]
        tvl_list = [f"• **{p.get('name')}**: ${p.get('tvl', 0):,.0f}" for p in sorted_protocols]
        return "\n".join(tvl_list) if tvl_list else "Tidak ada data TVL."
    except Exception as e:
        return f"Gagal mengambil data TVL DefiLlama: {e}"

def fetch_rss_news():
    news_items = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                news_items.append(f"[{source}] {entry.title}")
        except Exception:
            continue
    return "\n".join(news_items) if news_items else "Tidak ada berita terbaru."

def generate_groq_report(raw_data):
    if not GROQ_API_KEY:
        print("[ERROR] GROQ_API_KEY tidak ditemukan.")
        return None

    try:
        client = Groq(api_key=GROQ_API_KEY.strip())
        
        prompt = f"""
Anda adalah Senior Crypto Analyst. Buatkan ringkasan eksekutif singkat dan tajam (maksimal 3 paragraf) berdasarkan data berikut:

1. KINERJA PASAR UTAMA:
{raw_data.get('prices')}

2. KOIN TRENDING:
{raw_data.get('trending')}

3. TOP DEFI PROTOCOLS (TVL):
{raw_data.get('tvl')}

4. HEADLINE BERITA:
{raw_data.get('news')}

Berikan analisis mengenai sentimen pasar saat ini (Bullish/Bearish/Neutral) dan narasi utama yang sedang berkembang.
"""
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"[ERROR] Gagal memproses prompt di Groq API: {e}")
        return None

def send_to_discord(report):
    if not DISCORD_WEBHOOK_URL:
        print("[ERROR] DISCORD_WEBHOOK_URL tidak ditemukan.")
        return

    payload = {"content": report}
    try:
        res = requests.post(DISCORD_WEBHOOK_URL.strip(), json=payload, timeout=10)
        if res.status_code in [200, 204]:
            print("[SUCCESS] Pesan berhasil dikirim ke Discord!")
        else:
            print(f"[ERROR] Gagal mengirim ke Discord: Status {res.status_code}")
    except Exception as e:
        print(f"[ERROR] Gagal mengirim ke Discord: {e}")

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

    print("[INFO] Menganalisis data dengan Groq AI...")
    ai_summary = generate_groq_report(raw_data)

    if ai_summary:
        report = f"""🚀 **ALL-IN-ONE CRYPTO ALPHA REPORT** 🚀

📊 **PASAR UTAMA:**
{prices}

🔥 **TRENDING COINS:**
{trending}

🏦 **TOP DEFI TVL:**
{tvl}

🤖 **ANALISIS & SENTIMEN AI:**
{ai_summary}
"""
        print("[INFO] Mengirimkan laporan ke Discord...")
        send_to_discord(report)
    else:
        print("[FAIL] Gagal membuat laporan AI.")

if __name__ == "__main__":
    main()

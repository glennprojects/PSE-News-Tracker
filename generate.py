import feedparser
import yfinance as yf
import pandas as pd
import json
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os

# 1. Configuration: Map keywords to PSE Tickers (.PS suffix for Yahoo Finance)
COMPANY_MAP = {
    "Jollibee": "JFC.PS", "BDO": "BDO.PS", "BPI": "BPI.PS",
    "Ayala Land": "ALI.PS", "Universal Robina": "URC.PS",
    "Security Bank": "SECB.PS", "Globe": "GLO.PS",
    "PLDT": "TEL.PS", "Megaworld": "MEG.PS", "Manila Water": "MWP.PS",
    "Petron": "PCOR.PS", "DMCI": "DMC.PS", "Vista": "VITA.PS"
}

RSS_FEEDS = [
    "https://www.bworldonline.com/feed/",
    "https://www.philstar.com/rss/business",
    "https://business.inquirer.net/feed"
]

analyzer = SentimentIntensityAnalyzer()
results = []

# 2. Fetch and Process News (Look back 3 days to ensure "next day" price data exists)
for url in RSS_FEEDS:
    feed = feedparser.parse(url)
    for entry in feed.entries[:30]: # Limit to recent 30 per feed
        title = entry.get('title', '')
        summary = entry.get('summary', '')
        pub_date = entry.get('published', '')
        
        # Find matching company
        matched_company = None
        ticker = None
        for company, tick in COMPANY_MAP.items():
            if company.lower() in title.lower() or company.lower() in summary.lower():
                matched_company = company
                ticker = tick
                break
        
        if not ticker:
            continue

        # 3. Sentiment Analysis (Signal Generation)
        text_to_analyze = f"{title} {summary}"
        score = analyzer.polarity_scores(text_to_analyze)['compound']
        
        if score > 0.15:
            signal = "BUY"
        elif score < -0.15:
            signal = "SELL"
        else:
            signal = "HOLD"

        # 4. Price Action Validation (Day 0 vs Day 1)
        try:
            # Parse date from RSS (simplified fallback to today if parsing fails)
            # For robustness, we fetch last 5 days of data to find the matching day
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            
            if not hist.empty:
                close_day0 = hist['Close'].iloc[-2] # Day of news (approx)
                close_day1 = hist['Close'].iloc[-1] # Day after news
                pct_change = ((close_day1 - close_day0) / close_day0) * 100
                
                # Determine if signal was correct
                if signal == "BUY" and pct_change > 0:
                    accuracy = "✅ WIN"
                elif signal == "SELL" and pct_change < 0:
                    accuracy = "✅ WIN"
                elif signal == "HOLD":
                    accuracy = "➖ NEUTRAL"
                else:
                    accuracy = "❌ LOSS"
                    
                results.append({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "company": matched_company,
                    "ticker": ticker,
                    "headline": title,
                    "signal": signal,
                    "sentiment_score": round(score, 2),
                    "price_day0": round(close_day0, 2),
                    "price_day1": round(close_day1, 2),
                    "pct_change": round(pct_change, 2),
                    "accuracy": accuracy,
                    "source": "Philippine Business News"
                })
        except Exception as e:
            continue # Skip if price data fails

# Remove duplicates based on headline
unique_results = {v['headline']: v for v in results}.values()
final_data = list(unique_results)

# 5. Save to JSON
with open('data.json', 'w') as f:
    json.dump(final_data, f, indent=2)

print(f"Successfully processed {len(final_data)} news items.")

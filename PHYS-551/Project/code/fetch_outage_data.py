import json
import requests
import os
from datetime import datetime, timedelta
import concurrent.futures




EPIAS_DATA_URL = "https://seffaflik.epias.com.tr/electricity-service/v1/consumption/data/unplanned-power-outage-info"

HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'tr-TR',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Cookie' : 'TO BE FILLED IN',
    'Origin': 'https://seffaflik.epias.com.tr',
    'Referer': 'https://seffaflik.epias.com.tr/electricity/electricity-consumption/failure-information/unplanned-failure-information',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36',
}

def fetch_single_day(date_str):
    payload = {
        "period": date_str,
        "provinceId": 341, # Istanbul
        "distributionCompanyId": None,
        "page": {"number": 1, "size": 1000} # Get all for the day
    }
    
    try:
        res = requests.post(EPIAS_DATA_URL, json=payload, headers=HEADERS, timeout=15)
        if res.status_code == 200:
            return res.json().get("items", []), 200
        elif res.status_code == 429:
            print(f"Hata {res.status_code} (Çok Fazla İstek) - {date_str}. Biraz beklenecek...")
            return [], 429
        else:
            print(f"Hata {res.status_code} - {date_str}")
            return [], res.status_code
    except Exception as e:
        print(f"Bağlantı Hatası - {date_str}: {e}")
    return [], 0

def fetch_and_process_outages():
    print("⏳ EPİAŞ Şeffaflık API'sinden tam 1 yıllık veri çekiliyor (Lütfen bekleyin)...")
    
    # Generate 365 days of outage records starting 2024-01-01
    start_date = datetime(2024, 1, 1)
    date_list = [(start_date + timedelta(days=i)).strftime("%Y-%m-%dT00:00:00+03:00") for i in range(365)]
    # Start with an empty dict so we only save what we actually find
    outage_counts = {}
    total_overloads = 0
    
    completed = 0
    import time
    for d in date_list:
        completed += 1
        if completed % 10 == 0:
            print(f"  → {completed}/365 gün işlendi...")
            
        success = False
        while not success:
            items, status_code = fetch_single_day(d)
            
            if status_code == 429:
                print(f"⚠️ Çok fazla istek (429). 15 saniye bekleniyor...")
                time.sleep(15)
                continue # Retry the same date
            
            success = True
            
            # DEBUG: Show what the API actually returned for this day
            if len(items) > 0:
                print(f"  [>] {d[:10]} tarihinde API'den {len(items)} adet kesinti kaydı geldi.")
            
            for item in items:
                reason = item.get("reason", "")
                district = item.get("district", "Bilinmeyen İlçe")
                
                # Print every single outage found so we know it's not empty
                print(f"      - Bulunan: {district} | Sebep: {reason}")
                
                # Count only "Asiri Yük" / "Asiri Yuk" (API uses ASCII s/i, not Turkish ş/ı)
                if "Asiri Y" in reason:
                    # Dynamically add to dictionary whatever the API returns
                    outage_counts[district] = outage_counts.get(district, 0) + 1
                    total_overloads += 1
                    print(f"      [!] AŞIRI YÜK TESPİT EDİLDİ: {district}")
            
            # Normal delay between requests to avoid hitting the rate limit again
            time.sleep(1.5)

    print(f"✓ Veri çekme tamamlandı. Toplam '{total_overloads}' aşırı yük kesintisi bulundu.")
    return outage_counts

if __name__ == "__main__":
    stats = fetch_and_process_outages()

    print("\n" + "="*50)
    print("SONUÇ SÖZLÜĞÜ (DICTIONARY):")
    print("="*50)
    import pprint
    pprint.pprint(stats)
    print("="*50)

    # Write the counts that city_config.py reads to derive the safety margins.
    out_path = os.path.join(os.path.dirname(__file__), "output", "outage_stats.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=4)
    print(f"✓ Saved to {out_path}")

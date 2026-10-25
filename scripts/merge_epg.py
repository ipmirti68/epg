import requests, gzip, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

# ÖNCELİK SIRASI: En iyi -> en kötü
# epgshare TR en dolu, iptv-org bein/digiturk beIN için, open-epg en son fallback
SOURCES = [
    # 1. EPGShare - Türkiye için en iyisi, beIN dahil
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
    
    # 2. IPTV-ORG - beIN Sports ve Digiturk özel
    "https://iptv-org.github.io/epg/guides/tr/beinsports.com.tr.epg.xml.gz",
    "https://iptv-org.github.io/epg/guides/tr/digiturk.com.tr.epg.xml.gz",
    "https://iptv-org.github.io/epg/guides/tr/tvplus.com.tr.epg.xml.gz",
    "https://iptv-org.github.io/epg/guides/tr/blutv.com.tr.epg.xml.gz",
    
    # 3. Open-EPG - Genel fallback
    "https://www.open-epg.com/files/turkey1.xml.gz",
    "https://www.open-epg.com/files/turkey2.xml.gz",
    "https://www.open-epg.com/files/turkey3.xml.gz",
    "https://www.open-epg.com/files/turkey4.xml.gz",
    "https://www.open-epg.com/files/turkey5.xml.gz",
]

def norm(cid):
    if not cid: return None
    cid = cid.strip()
    low = cid.lower()
    # .tr temizle
    if low.endswith(".tr"):
        cid = cid[:-3]
        low = low[:-3]
    # beIN varyasyonlarını tekilleştir
    # "beIN SPORTS 1 HD", "beIN SPORTS 1", "beIN SPORTS HD 1" -> "beIN SPORTS 1"
    low = low.replace("_"," ").replace("-"," ").strip()
    if "bein" in low:
        # bein sports 1 -> standart
        for i in range(1,6):
            if f"{i}" in low:
                if "haber" in low: return "beIN SPORTS HABER"
                if "max" in low: return f"beIN SPORTS MAX {i}" if i!=1 else "beIN SPORTS MAX 1"
                return f"beIN SPORTS {i}"
        if "haber" in low: return "beIN SPORTS HABER"
        if "max" in low: return "beIN SPORTS MAX 1"
        return "beIN SPORTS 1"
    return cid.split("@")[0].strip()

def clean_name(name):
    if not name: return ""
    name = name.strip()
    if name.lower().endswith(".tr"): name = name[:-3]
    return name

def fix_time(timestr):
    try:
        if len(timestr) < 14: return timestr
        return f"{timestr[:14]} +0300"
    except:
        return timestr

tv_channels = {}
tv_progs = []
seen_prog = set() # (channel, start) - aynı programı 2 kere ekleme
has_epg = set()
BAD_TITLES = ["veri yok", "no information", "no info", "epg mevcut değil", ""]

print("=== EPG ÇEKME BAŞLADI ===")
for url in SOURCES:
    try:
        r = requests.get(url, timeout=90, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200:
            print(f"❌ {url} -> {r.status_code}")
            continue
        data = r.content
        if url.endswith('.gz'):
            try: data = gzip.decompress(data)
            except: pass
        root = ET.fromstring(data)
        ch_count = 0
        pr_count = 0
        bein_count = 0
        
        for ch in root.findall('channel'):
            nid = norm(ch.get('id',''))
            if not nid: continue
            low = nid.lower()
            if low not in tv_channels:
                dn = ch.find('display-name')
                if dn is not None and dn.text:
                    dn.text = clean_name(dn.text)
                ch.set('id', nid)
                tv_channels[low] = ch
                ch_count += 1
                if "bein" in low: bein_count += 1
        
        for pr in root.findall('programme'):
            nid = norm(pr.get('channel',''))
            if not nid: continue
            low = nid.lower()
            # saat düzelt
            s = fix_time(pr.get('start','')) if pr.get('start') else ""
            e = fix_time(pr.get('stop','')) if pr.get('stop') else ""
            if not s: continue
            
            # Öncelik: aynı kanal + aynı saat varsa ilk geleni (epgshare) al, diğerini at
            key = (low, s)
            if key in seen_prog:
                continue
            
            if pr.get('start'): pr.set('start', s)
            if pr.get('stop'): pr.set('stop', e)
            
            title_elem = pr.find('title')
            if title_elem is not None and title_elem.text:
                if title_elem.text.strip().lower() in BAD_TITLES:
                    ch_obj = tv_channels.get(low)
                    title_elem.text = ch_obj.find('display-name').text if ch_obj is not None and ch_obj.find('display-name') is not None else nid
            
            pr.set('channel', nid)
            tv_progs.append(pr)
            seen_prog.add(key)
            has_epg.add(low)
            pr_count += 1
        
        print(f"✓ {url.split('/')[-1]} : {ch_count} kanal, {pr_count} program (beIN: {bein_count})")
    except Exception as e:
        print(f"❌ HATA {url}: {e}")

# Final XML oluştur - kanallar A-Z sıralı en başta
final_tv = ET.Element('tv')
sorted_channels = sorted(tv_channels.values(), key=lambda x: x.get('id','').lower())
for ch in sorted_channels:
    final_tv.append(ch)
for pr in tv_progs:
    final_tv.append(pr)

# EPG'si olmayanlara fallback
now = datetime.now(timezone(timedelta(hours=3)))
start_str = now.strftime("%Y%m%d%H%M%S +0300")
stop_str = (now + timedelta(days=1)).strftime("%Y%m%d%H%M%S +0300")
fallback = 0
for low,ch in tv_channels.items():
    if low not in has_epg:
        name = ch.find('display-name').text if ch.find('display-name') is not None else ch.get('id')
        prog = ET.Element('programme', {'channel': ch.get('id'), 'start': start_str, 'stop': stop_str})
        ET.SubElement(prog, 'title', {'lang':'tr'}).text = name
        ET.SubElement(prog, 'desc', {'lang':'tr'}).text = f"{name} yayını"
        final_tv.append(prog)
        fallback += 1

ET.ElementTree(final_tv).write('epg.xml', encoding='utf-8', xml_declaration=True)

# Listeler
with open('kanal_listesi.txt','w',encoding='utf-8') as f:
    f.write(f"Toplam {len(sorted_channels)} kanal\n")
    for ch in sorted_channels:
        cid = ch.get('id')
        has = "✓" if cid.lower() in has_epg else "✗"
        f.write(f"{has} {cid}\n")

with open('kanallar.html','w',encoding='utf-8') as f:
    f.write(f"<html><meta charset='utf-8'><body><h2>{len(sorted_channels)} Kanal - beIN kontrol</h2><table border=1 cellpadding=5>")
    for i,ch in enumerate(sorted_channels,1):
        cid = ch.get('id')
        is_bein = "🔥" if "bein" in cid.lower() else ""
        has = "VAR" if cid.lower() in has_epg else "YOK"
        color = "#d4edda" if cid.lower() in has_epg else "#f8d7da"
        f.write(f"<tr style='background:{color}'><td>{i}</td><td>{is_bein} {cid}</td><td>{has}</td></tr>")
    f.write("</table></body></html>")

print(f"\nBİTTİ: {len(sorted_channels)} kanal, {len(tv_progs)} program, {fallback} fallback")
print("beIN'ler:")
for ch in sorted_channels:
    if "bein" in ch.get('id','').lower():
        print(f" - {ch.get('id')}")

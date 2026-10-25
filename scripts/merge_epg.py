import requests, gzip, xml.etree.ElementTree as ET, re
from datetime import datetime, timedelta, timezone

SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR2.xml.gz",
    "https://www.open-epg.com/files/turkey1.xml.gz",
    "https://www.open-epg.com/files/turkey2.xml.gz",
    "https://www.open-epg.com/files/turkey3.xml.gz",
    "https://www.open-epg.com/files/turkey4.xml.gz",
    "https://www.open-epg.com/files/turkey5.xml.gz",
]

def clean_id(cid):
    if not cid: return None
    cid = cid.strip()
    if cid.lower().endswith(".tr"): cid = cid[:-3]
    return cid.strip()

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
seen_prog = set()
has_epg = set()

print("=== EPG CEKME BASLADI ===")
for url in SOURCES:
    try:
        r = requests.get(url, timeout=90, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200: continue
        data = r.content
        if url.endswith('.gz'):
            try: data = gzip.decompress(data)
            except: pass
        root = ET.fromstring(data)
        for ch in root.findall('channel'):
            cid = clean_id(ch.get('id',''))
            if not cid: continue
            low = cid.lower()
            if low not in tv_channels:
                dn = ch.find('display-name')
                if dn is not None and dn.text: dn.text = clean_name(dn.text)
                ch.set('id', cid)
                tv_channels[low] = ch
        for pr in root.findall('programme'):
            cid = clean_id(pr.get('channel',''))
            if not cid: continue
            low = cid.lower()
            s = fix_time(pr.get('start','')) if pr.get('start') else ""
            e = fix_time(pr.get('stop','')) if pr.get('stop') else ""
            if not s: continue
            key = (low, s)
            if key in seen_prog: continue
            if pr.get('start'): pr.set('start', s)
            if pr.get('stop'): pr.set('stop', e)
            pr.set('channel', cid)
            tv_progs.append(pr)
            seen_prog.add(key)
            has_epg.add(low)
    except Exception as e:
        print(f"HATA {url}: {e}")

# === SENIN LISTENE GORE BEIN ALIAS ===
# beinsports, beinsports 2, beinsports 3... seklinde geliyor dedin
bein_mapping = {
    "beIN SPORTS 1": ["beinsports", "beinsports 1", "beinsport 1", "beinsports1"],
    "beIN SPORTS 2": ["beinsports 2", "beinsport 2", "beinsports2"],
    "beIN SPORTS 3": ["beinsports 3", "beinsport 3", "beinsports3"],
    "beIN SPORTS 4": ["beinsports 4", "beinsport 4", "beinsports4"],
    "beIN SPORTS 5": ["beinsports 5", "beinsport 5", "beinsports5"],
    "beIN SPORTS HABER": ["beinsports haber", "beinsport haber", "beinsports haber hd"],
    "beIN SPORTS MAX 1": ["beinsports max 1", "beinsport max 1", "beinsports max1"],
    "beIN SPORTS MAX 2": ["beinsports max 2", "beinsport max 2", "beinsports max2"],
}

print("\n=== BEIN ALIAS EKLENIYOR (senin liste icin) ===")
for orig, aliases in bein_mapping.items():
    orig_low = orig.lower()
    # orig kaynakta var mi?
    orig_progs = [p for p in tv_progs if p.get('channel','').lower() == orig_low]
    if not orig_progs:
        # Bazen kaynakta "beIN SPORTS 1 HD" diye, onu da bul
        orig_progs = [p for p in tv_progs if "bein" in p.get('channel','').lower() and orig.split()[-1].lower() in p.get('channel','').lower() and "sport" in p.get('channel','').lower()]
        if "haber" in orig_low and not orig_progs:
            orig_progs = [p for p in tv_progs if "haber" in p.get('channel','').lower() and "bein" in p.get('channel','').lower()]
    
    if not orig_progs:
        print(f"UYARI: Kaynakta {orig} bulunamadi")
        continue

    for alias in aliases:
        a_low = alias.lower()
        if a_low not in tv_channels:
            new_ch = ET.Element('channel', {'id': alias})
            ET.SubElement(new_ch, 'display-name').text = orig
            ET.SubElement(new_ch, 'display-name').text = alias
            tv_channels[a_low] = new_ch
        
        # Programlari kopyala
        for pr in orig_progs:
            s = pr.get('start'); e = pr.get('stop')
            key = (a_low, s)
            if key in seen_prog: continue
            new_pr = ET.Element('programme', {'channel': alias, 'start': s, 'stop': e})

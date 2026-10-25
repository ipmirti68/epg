import requests, gzip, xml.etree.ElementTree as ET

# ÖNCELİKLİ KAYNAKLAR EN BAŞTA - beIN için en doğru bunlar
SOURCES = [
    "https://iptv-org.github.io/epg/guides/tr/bein.com.epg.xml",
    "https://iptv-org.github.io/epg/guides/tr/tvplus.com.tr.epg.xml",
    "https://i.mjh.nz/Turkey.xml.gz",
    "https://www.open-epg.com/files/turkey1.xml.gz",
    "https://www.open-epg.com/files/turkey2.xml.gz",
    "https://www.open-epg.com/files/turkey3.xml.gz",
    "https://www.open-epg.com/files/turkey4.xml.gz",
    "https://www.open-epg.com/files/turkey5.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR2.xml.gz",
]

tv = ET.Element('tv')
seen_channels = set()
seen_programmes = set() # aynı kanal + start zamanı varsa tekrar ekleme

def normalize_id(cid):
    if not cid: return None
    cid = cid.strip()
    if cid.lower().endswith(".tr"): cid = cid[:-3]
    return cid.split("@")[0].strip()

for url in SOURCES:
    try:
        data = requests.get(url, timeout=60, headers={"User-Agent":"Mozilla/5.0"}).content
        if url.endswith('.gz'):
            try: data = gzip.decompress(data)
            except: pass
        root = ET.fromstring(data)
        for ch in root.findall('channel'):
            nid = normalize_id(ch.get('id',''))
            if not nid or nid.lower() in seen_channels: continue
            seen_channels.add(nid.lower())
            ch.set('id', nid)
            tv.append(ch)
        for pr in root.findall('programme'):
            nid = normalize_id(pr.get('channel',''))
            if not nid: continue
            key = (nid.lower(), pr.get('start'))
            if key in seen_programmes: continue # öncelikli kaynakta varsa diğerini alma
            seen_programmes.add(key)
            pr.set('channel', nid)
            tv.append(pr)
        print(f"OK {url} -> {len(root.findall('channel'))} kanal")
    except Exception as e:
        print(f"HATA {url}: {e}")

ET.ElementTree(tv).write('epg.xml', encoding='utf-8', xml_declaration=True)
print(f"BİTTİ: {len(seen_channels)} kanal")

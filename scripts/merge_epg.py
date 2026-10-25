import requests, gzip, xml.etree.ElementTree as ET

SOURCES = [
    # 1. YAYINCI KURULUŞLAR - EN GÜVENİLİR (Digiturk, D-Smart, Tivibu, Tabii, Kablo, beIN)
    "https://iptv-org.github.io/epg/guides/tr/bein.com.epg.xml",
    "https://iptv-org.github.io/epg/guides/tr/digiturk.com.tr.epg.xml",
    "https://iptv-org.github.io/epg/guides/tr/dsmart.com.tr.epg.xml",
    "https://iptv-org.github.io/epg/guides/tr/tivibu.com.tr.epg.xml",
    "https://iptv-org.github.io/epg/guides/tr/tabii.com.epg.xml",
    "https://iptv-org.github.io/epg/guides/tr/tvplus.com.tr.epg.xml",
    "https://iptv-org.github.io/epg/guides/tr/kablotv.com.tr.epg.xml",
    "https://iptv-org.github.io/epg/guides/tr/trt.com.tr.epg.xml",
    "https://iptv-org.github.io/epg/guides/tr/blutv.com.epg.xml",
    "https://iptv-org.github.io/epg/guides/tr/exxen.com.epg.xml",

    # 2. GENEL TÜRKİYE EPG'LERİ
    "https://i.mjh.nz/Turkey.xml.gz",
    "https://www.open-epg.com/files/turkey1.xml.gz",
    "https://www.open-epg.com/files/turkey2.xml.gz",
    "https://www.open-epg.com/files/turkey3.xml.gz",
    "https://www.open-epg.com/files/turkey4.xml.gz",
    "https://www.open-epg.com/files/turkey5.xml.gz",
    "https://www.open-epg.com/files/turkey6.xml.gz",
    "https://www.open-epg.com/files/turkey7.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR2.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR4.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR5.xml.gz",
]

tv = ET.Element('tv')
seen_channels = set()
seen_prog = set()

def norm(cid):
    if not cid: return None
    cid = cid.strip()
    if cid.lower().endswith(".tr"): cid = cid[:-3]
    return cid.split("@")[0].strip()

for url in SOURCES:
    try:
        r = requests.get(url, timeout=60, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200: 
            print(f"ATLA {url} {r.status_code}")
            continue
        data = r.content
        if url.endswith('.gz'):
            try: data = gzip.decompress(data)
            except: pass
        root = ET.fromstring(data)
        c_count = 0
        p_count = 0
        for ch in root.findall('channel'):
            nid = norm(ch.get('id',''))
            if not nid: continue
            low = nid.lower()
            if low in seen_channels: continue
            seen_channels.add(low)
            ch.set('id', nid)
            tv.append(ch)
            c_count+=1
        for pr in root.findall('programme'):
            nid = norm(pr.get('channel',''))
            if not nid: continue
            key = (nid.lower(), pr.get('start'))
            if key in seen_prog: continue
            seen_prog.add(key)
            pr.set('channel', nid)
            tv.append(pr)
            p_count+=1
        print(f"OK {url} -> {c_count} kanal, {p_count} program")
    except Exception as e:
        print(f"HATA {url}: {e}")

ET.ElementTree(tv).write('epg.xml', encoding='utf-8', xml_declaration=True)
print(f"TOPLAM: {len(seen_channels)} kanal, {len(seen_prog)} program")

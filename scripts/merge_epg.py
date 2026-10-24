import requests, gzip, xml.etree.ElementTree as ET

SOURCES = [
    "https://www.open-epg.com/files/turkey4.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
]

tv = ET.Element('tv')
seen=set()

def normalize_id(cid):
    if not cid: return ""
    cid = cid.strip()
    if "KABLO" in cid.upper(): return None
    # .tr varsa sil
    if cid.lower().endswith(".tr"):
        cid = cid[:-3]
    # @HD gibi şeyleri sil
    cid = cid.split("@")[0]
    # noktayı koru, sadece .tr'yi sildik
    cid = cid.strip(".")
    return cid

for url in SOURCES:
    try:
        data = requests.get(url, timeout=90, headers={"User-Agent":"Mozilla/5.0"}).content
        if url.endswith('.gz'): data = gzip.decompress(data)
        root = ET.fromstring(data)
        for ch in root.findall('channel'):
            new = normalize_id(ch.get('id',''))
            if not new: continue
            ch.set('id', new)
            if new not in seen:
                seen.add(new)
                tv.append(ch)
        for p in root.findall('programme'):
            new = normalize_id(p.get('channel',''))
            if not new: continue
            p.set('channel', new)
            t = p.find('title')
            if t is None or not t.text: continue
            if "kablo" in t.text.lower(): continue
            tv.append(p)
    except Exception as e:
        print(e)

ET.ElementTree(tv).write('epg.xml', encoding='utf-8', xml_declaration=True)
print(f"Bitti -> {len(seen)} kanal, .tr'siz")

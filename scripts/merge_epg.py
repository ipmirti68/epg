import requests, gzip, xml.etree.ElementTree as ET

SOURCES = [
    "https://www.open-epg.com/files/turkey4.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
]

tv = ET.Element('tv')
seen=set()
count=0

for url in SOURCES:
    try:
        print(f"Indiriliyor {url}")
        data = requests.get(url, timeout=90, headers={"User-Agent":"Mozilla/5.0"}).content
        if url.endswith('.gz'):
            data = gzip.decompress(data)
        root = ET.fromstring(data)
        for ch in root.findall('channel'):
            cid = ch.get('id','')
            if "KABLO" in cid.upper(): continue
            if cid not in seen:
                seen.add(cid)
                tv.append(ch)
        for p in root.findall('programme'):
            cid = p.get('channel','')
            if "KABLO" in cid.upper(): continue
            t = p.find('title')
            if t is None or not t.text: continue
            txt = t.text.strip()
            if txt == "" or txt.lower() == "kablo info": continue
            tv.append(p)
            count+=1
    except Exception as e:
        print(f"Hata {url}: {e}")

ET.ElementTree(tv).write('epg.xml', encoding='utf-8', xml_declaration=True)
print(f"TAMAM -> Kanallar: {len(seen)} Program: {count}")

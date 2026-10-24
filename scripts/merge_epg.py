import requests, gzip, xml.etree.ElementTree as ET

SOURCES = [
    "https://www.open-epg.com/files/turkey1.xml.gz",
    "https://www.open-epg.com/files/turkey2.xml.gz",
    "https://www.open-epg.com/files/turkey3.xml.gz",
    "https://www.open-epg.com/files/turkey4.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
    "https://raw.githubusercontent.com/ahmethascelik/epghost/main/xmltv.xml",
]

tv = ET.Element('tv')
seen_channels = set()
count_prog = 0

for url in SOURCES:
    try:
        print(f"-> {url}")
        r = requests.get(url, timeout=90, headers={"User-Agent": "Mozilla/5.0"})
        data = r.content
        if url.endswith('.gz'):
            data = gzip.decompress(data)
        
        root = ET.fromstring(data)
        
        for ch in root.findall('channel'):
            cid = ch.get('id')
            if cid not in seen_channels:
                seen_channels.add(cid)
                tv.append(ch)
        
        for prog in root.findall('programme'):
            title = prog.find('title')
            # Boş title'ları alma - senin hatan buydu
            if title is not None and title.text and title.text.strip() != "" and title.text.strip() != "KABLO Info":
                tv.append(prog)
                count_prog += 1
                
    except Exception as e:
        print(f"HATA {url}: {e}")

ET.ElementTree(tv).write('epg.xml', encoding='utf-8', xml_declaration=True)
print(f"BİTTİ -> Kanallar: {len(seen_channels)} Programlar: {count_prog}")

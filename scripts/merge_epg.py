import requests, gzip, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

SOURCES = [
    "https://www.open-epg.com/files/turkey1.xml.gz",
    "https://www.open-epg.com/files/turkey2.xml.gz",
    "https://www.open-epg.com/files/turkey3.xml.gz",
    "https://www.open-epg.com/files/turkey4.xml.gz",
    "https://www.open-epg.com/files/turkey5.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
]

def norm(cid):
    if not cid:
        return None
    cid = cid.strip()
    if cid.lower().endswith(".tr"):
        cid = cid[:-3]
    return cid.split("@")[0].strip()

def fix_time(timestr):
    # 3 saat kayma sorunu için: saati kaydırmadan sadece +0300 yap
    # 080500 +0000 -> 080500 +0300 (aynen kalsın)
    try:
        if len(timestr) < 14:
            return timestr
        dt_part = timestr[:14]
        return f"{dt_part} +0300"
    except:
        return timestr

tv = ET.Element('tv')
channels_dict = {}
has_epg = set()
BAD_TITLES = ["veri yok", "no information", "no info", "epg mevcut değil", ""]

# 1. Tüm kaynakları çek
for url in SOURCES:
    try:
        r = requests.get(url, timeout=60, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200:
            print(f"404 {url}")
            continue
        data = r.content
        if url.endswith('.gz'):
            try:
                data = gzip.decompress(data)
            except:
                pass
        root = ET.fromstring(data)
        for ch in root.findall('channel'):
            nid = norm(ch.get('id',''))
            if not nid:
                continue
            low = nid.lower()
            if low not in channels_dict:
                ch.set('id', nid)
                channels_dict[low] = ch

        for pr in root.findall('programme'):
            nid = norm(pr.get('channel',''))
            if not nid:
                continue
            low = nid.lower()
            # Saatleri düzelt (kaydırmadan)
            if pr.get('start'):
                pr.set('start', fix_time(pr.get('start')))
            if pr.get('stop'):
                pr.set('stop', fix_time(pr.get('stop')))
            
            # "Veri yok" ise başlığı kanal ismi yap
            title_elem = pr.find('title')
            if title_elem is not None and title_elem.text:
                if title_elem.text.strip().lower() in BAD_TITLES:
                    ch_obj = channels_dict.get(low)
                    if ch_obj is not None:
                        dn = ch_obj.find('display-name')
                        title_elem.text = dn.text if dn is not None and dn.text else nid
                    else:
                        title_elem.text = nid
            
            pr.set('channel', nid)
            tv.append(pr)
            has_epg.add(low)

    except Exception as e:
        print(f"HATA {url}: {e}")

# 2. Kanalları ekle
for ch in channels_dict.values():
    tv.append(ch)

# 3. Hiç EPG'si olmayan kanala kanal ismini yaz (24 saatlik)
now = datetime.now(timezone(timedelta(hours=3)))
start_str = now.strftime("%Y%m%d%H%M%S +0300")
stop_str = (now + timedelta(days=1)).strftime("%Y%m%d%H%M%S +0300")

fallback_count = 0
for low, ch in channels_dict.items():
    if low not in has_epg:
        dn = ch.find('display-name')
        name = dn.text if dn is not None and dn.text else ch.get('id')
        prog = ET.Element('programme', {'channel': ch.get('id'), 'start': start_str, 'stop': stop_str})
        title = ET.SubElement(prog, 'title', {'lang': 'tr'})
        title.text = name
        desc = ET.SubElement(prog, 'desc', {'lang': 'tr'})
        desc.text = f"{name} yayını"
        tv.append(prog)
        fallback_count += 1

print(f"TOPLAM: {len(channels_dict)} kanal, {fallback_count} tanesine fallback yazıldı")

ET.ElementTree(tv).write('epg.xml', encoding='utf-8', xml_declaration=True)

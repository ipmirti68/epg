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
    if not cid: return None
    cid = cid.strip()
    if cid.lower().endswith(".tr"): cid = cid[:-3]
    return cid.split("@")[0].strip()

def clean_name(name):
    if not name: return ""
    name = name.strip()
    if name.lower().endswith(".tr"):
        name = name[:-3]
    return name

def fix_time(timestr):
    try:
        if len(timestr) < 14: return timestr
        return f"{timestr[:14]} +0300"
    except:
        return timestr

tv = ET.Element('tv')
channels_dict = {}
has_epg = set()
BAD_TITLES = ["veri yok", "no information", "no info", "epg mevcut değil", ""]

for url in SOURCES:
    try:
        r = requests.get(url, timeout=60, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200: continue
        data = r.content
        if url.endswith('.gz'):
            try: data = gzip.decompress(data)
            except: pass
        root = ET.fromstring(data)
        for ch in root.findall('channel'):
            nid = norm(ch.get('id',''))
            if not nid: continue
            low = nid.lower()
            if low not in channels_dict:
                # display-name'i de temizle
                dn_elem = ch.find('display-name')
                if dn_elem is not None and dn_elem.text:
                    dn_elem.text = clean_name(dn_elem.text)
                ch.set('id', nid)
                channels_dict[low] = ch
        for pr in root.findall('programme'):
            nid = norm(pr.get('channel',''))
            if not nid: continue
            low = nid.lower()
            if pr.get('start'): pr.set('start', fix_time(pr.get('start')))
            if pr.get('stop'): pr.set('stop', fix_time(pr.get('stop')))
            title_elem = pr.find('title')
            if title_elem is not None and title_elem.text:
                if title_elem.text.strip().lower() in BAD_TITLES:
                    ch_obj = channels_dict.get(low)
                    if ch_obj is not None:
                        dn = ch_obj.find('display-name')
                        title_elem.text = dn.text if dn is not None else nid
                    else:
                        title_elem.text = nid
            pr.set('channel', nid)
            tv.append(pr)
            has_epg.add(low)
    except Exception as e:
        print(f"HATA {url}: {e}")

# Kanalları A-Z sırala ve önce ekle
sorted_channels = sorted(channels_dict.values(), key=lambda x: x.get('id','').lower())
final_tv = ET.Element('tv')

for ch in sorted_channels:
    final_tv.append(ch)

# Programları da kanallara taşı
for prog in tv.findall('programme'):
    final_tv.append(prog)

# EPG'si olmayanlara fallback
now = datetime.now(timezone(timedelta(hours=3)))
start_str = now.strftime("%Y%m%d%H%M%S +0300")
stop_str = (now + timedelta(days=1)).strftime("%Y%m%d%H%M%S +0300")
for low, ch in channels_dict.items():
    if low not in has_epg:
        name = ch.find('display-name').text if ch.find('display-name') is not None else ch.get('id')
        prog = ET.Element('programme', {'channel': ch.get('id'), 'start': start_str, 'stop': stop_str})
        ET.SubElement(prog, 'title', {'lang': 'tr'}).text = name
        ET.SubElement(prog, 'desc', {'lang': 'tr'}).text = f"{name} yayını"
        final_tv.append(prog)

# 1. epg.xml yaz
ET.ElementTree(final_tv).write('epg.xml', encoding='utf-8', xml_declaration=True)

# 2. kanal_listesi.txt yaz (ID listesi)
with open('kanal_listesi.txt','w',encoding='utf-8') as f:
    f.write(f"Toplam {len(sorted_channels)} kanal çekildi - {now.strftime('%d.%m.%Y %H:%M')}\n")
    f.write("="*40+"\n")
    for ch in sorted_channels:
        cid = ch.get('id')
        has = "✓" if cid.lower() in has_epg else "✗ (isim yazacak)"
        f.write(f"{has} ID: {cid}\n")

# 3. kanallar.html yaz (görsel)
with open('kanallar.html','w',encoding='utf-8') as f:
    f.write("<html><head><meta charset='utf-8'><title>Kanal Listesi</title></head><body style='font-family:sans-serif'>")
    f.write(f"<h2>Toplam {len(sorted_channels)} kanal çekildi</h2><table border=1 cellpadding=5><tr><th>#</th><th>Kanal ID</th><th>Display Name</th><th>EPG Var mı?</th></tr>")
    for i,ch in enumerate(sorted_channels,1):
        cid = ch.get('id')
        dname = ch.find('display-name').text if ch.find('display-name') is not None else ""
        has = "VAR" if cid.lower() in has_epg else "YOK - İsim yazacak"
        color = "#d4edda" if cid.lower() in has_epg else "#f8d7da"
        f.write(f"<tr style='background:{color}'><td>{i}</td><td>{cid}</td><td>{dname}</td><td>{has}</td></tr>")
    f.write("</table></body></html>")

print(f"BİTTİ: {len(sorted_channels)} kanal")

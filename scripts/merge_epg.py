import requests, gzip, xml.etree.ElementTree as ET, re
from datetime import datetime, timedelta, timezone

# SADECE ÇALIŞAN KAYNAKLAR - Öncelik: epgshare en iyi
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

def norm(cid):
    if not cid: return None
    cid = cid.strip()
    if cid.lower().endswith(".tr"):
        cid = cid[:-3]
    raw = cid
    low = cid.lower()
    
    if "bein" in low:
        if "haber" in low:
            return "beIN SPORTS HABER"
        # MAX 1 / MAX 2 ayrımı
        m = re.search(r'max\s*(\d+)', low)
        if m:
            return f"beIN SPORTS MAX {m.group(1)}"
        if "max" in low:
            return "beIN SPORTS MAX 1"
        # Normal 1-5
        m = re.search(r'(\d+)', low)
        if m:
            num = m.group(1)
            if num in "12345":
                return f"beIN SPORTS {num}"
        return "beIN SPORTS 1"
    
    return raw.split("@")[0].strip()

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
BAD_TITLES = ["veri yok", "no information", "no info", "epg mevcut değil", ""]

print("=== EPG ÇEKME BAŞLADI ===")
for url in SOURCES:
    try:
        r = requests.get(url, timeout=90, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200:
            print(f"❌ {url.split('/')[-1]} -> {r.status_code}")
            continue
        data = r.content
        if url.endswith('.gz'):
            try: data = gzip.decompress(data)
            except: pass
        root = ET.fromstring(data)
        ch_c = pr_c = bein_c = 0
        for ch in root.findall('channel'):
            nid = norm(ch.get('id',''))
            if not nid: continue
            low = nid.lower()
            if low not in tv_channels:
                dn = ch.find('display-name')
                if dn is not None and dn.text: dn.text = clean_name(dn.text)
                ch.set('id', nid)
                tv_channels[low] = ch
                ch_c += 1
                if "bein" in low: bein_c += 1
        for pr in root.findall('programme'):
            nid = norm(pr.get('channel',''))
            if not nid: continue
            low = nid.lower()
            s = fix_time(pr.get('start','')) if pr.get('start') else ""
            e = fix_time(pr.get('stop','')) if pr.get('stop') else ""
            if not s: continue
            key = (low, s)
            if key in seen_prog: continue
            if pr.get('start'): pr.set('start', s)
            if pr.get('stop'): pr.set('stop', e)
            t = pr.find('title')
            if t is not None and t.text and t.text.strip().lower() in BAD_TITLES:
                ch_obj = tv_channels.get(low)
                t.text = ch_obj.find('display-name').text if ch_obj is not None and ch_obj.find('display-name') is not None else nid
            pr.set('channel', nid)
            tv_progs.append(pr)
            seen_prog.add(key)
            has_epg.add(low)
            pr_c += 1
        print(f"✓ {url.split('/')[-1]} : {ch_c} kanal, {pr_c} program (beIN: {bein_c})")
    except Exception as e:
        print(f"❌ HATA {url}: {e}")

final_tv = ET.Element('tv')
sorted_channels = sorted(tv_channels.values(), key=lambda x: x.get('id','').lower())
for ch in sorted_channels: final_tv.append(ch)
for pr in tv_progs: final_tv.append(pr)

now = datetime.now(timezone(timedelta(hours=3)))
start_str = now.strftime("%Y%m%d%H%M%S +0300")
stop_str = (now + timedelta(days=1)).strftime("%Y%m%d%H%M%S +0300")
fallback = 0
for low,ch in tv_channels.items():
    if low not in has_epg:
        name = ch.find('display-name').text if ch.find('display-name') is not None else ch.get('id')
        prog = ET.Element('programme', {'channel': ch.get('id'), 'start': start_str, 'stop': stop_str})
        ET.SubElement(prog, 'title', {'lang':'tr'}).text = name
        final_tv.append(prog)
        fallback += 1

ET.ElementTree(final_tv).write('epg.xml', encoding='utf-8', xml_declaration=True)

with open('kanallar.html','w',encoding='utf-8') as f:
    f.write("<html><meta charset='utf-8'><body><h2>Kanal Listesi</h2><table border=1>")
    for i,ch in enumerate(sorted_channels,1):
        cid = ch.get('id')
        is_bein = "🔥 " if "bein" in cid.lower() else ""
        has = "VAR" if cid.lower() in has_epg else "YOK"
        color = "#d4edda" if cid.lower() in has_epg else "#f8d7da"
        f.write(f"<tr style='background:{color}'><td>{i}</td><td>{is_bein}{cid}</td><td>{has}</td></tr>")
    f.write("</table></body></html>")

print(f"\nBİTTİ: {len(sorted_channels)} kanal, {len(tv_progs)} program")
print("BEIN LISTESI:")
for ch in sorted_channels:
    if "bein" in ch.get('id','').lower():
        print(f" - {ch.get('id')}")

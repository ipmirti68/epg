import requests, gzip, xml.etree.ElementTree as ET, re
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# EN DOLU KAYNAKLAR - Sirali
SOURCES = [
    # 1. EPGShare - Türkiye en dolu
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR2.xml.gz",
    # 2. iptv-org - Resmi sitelerden çekiyor (Digiturk, beIN, tvplus)
    "https://iptv-org.github.io/epg/guides/tr/tvplus.com.tr.epg.xml.gz",
    "https://iptv-org.github.io/epg/guides/tr/digiturk.com.tr.epg.xml.gz",
    "https://iptv-org.github.io/epg/guides/tr/beinsports.com.tr.epg.xml.gz",
    "https://iptv-org.github.io/epg/guides/tr/dsmart.com.tr.epg.xml.gz",
    "https://iptv-org.github.io/epg/guides/tr/tivibu.com.tr.epg.xml.gz",
    "https://iptv-org.github.io/epg/guides/tr/blutv.com.tr.epg.xml.gz",
    # 3. epg.pw - Yedek Türkiye
    "https://epg.pw/xmltv/epg_TR.xml.gz",
    "https://epg.pw/xmltv/epg_TR.xml",
    # 4. open-epg - Fallback
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

def fix_time(t):
    try:
        if len(t) < 14: return t
        return f"{t[:14]} +0300"
    except:
        return t

def base_name(name):
    n = name.lower()
    n = n.replace(".tv","").replace(".hd","").replace(".fhd","")
    n = n.replace(" tv hd","").replace(" hd","").replace(" fhd","")
    n = re.sub(r'[^a-z0-9 ]',' ', n)
    n = re.sub(r'\s+',' ', n).strip()
    return n

tv_channels = {}
channel_by_base = defaultdict(list)
tv_progs = []
seen_prog = set()

print("=== ULTRA EPG CEKME BASLADI ===")
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
        ch_new = pr_new = 0
        for ch in root.findall('channel'):
            cid = clean_id(ch.get('id',''))
            if not cid: continue
            low = cid.lower()
            if low not in tv_channels:
                dn = ch.find('display-name')
                dname = dn.text if dn is not None and dn.text else cid
                dname = clean_id(dname)
                if dn is not None: dn.text = dname
                else: ET.SubElement(ch, 'display-name').text = dname
                ch.set('id', cid)
                tv_channels[low] = ch
                channel_by_base[base_name(dname)].append(cid)
                ch_new += 1
        for pr in root.findall('programme'):
            cid = clean_id(pr.get('channel',''))
            if not cid: continue
            low = cid.lower()
            s = fix_time(pr.get('start',''))
            e = fix_time(pr.get('stop',''))
            if not s: continue
            key = (low, s)
            if key in seen_prog: continue
            pr.set('start', s); pr.set('stop', e)
            pr.set('channel', cid)
            tv_progs.append(pr)
            seen_prog.add(key)
            pr_new += 1
        if ch_new or pr_new:
            print(f"✓ {url.split('/')[-1][:30]:30} -> {ch_new} yeni kanal, {pr_new} program")
    except Exception as e:
        print(f"❌ HATA {url}: {e}")

# Varyant birleştir
for base, ids in channel_by_base.items():
    if len(ids) <= 1: continue
    all_progs = []
    for cid in ids:
        all_progs.extend([p for p in tv_progs if p.get('channel','').lower() == cid.lower()])
    for cid in ids:
        clow = cid.lower()
        for pr in all_progs:
            key = (clow, pr.get('start'))
            if key in seen_prog: continue
            new_pr = ET.Element('programme', {'channel': cid, 'start': pr.get('start'), 'stop': pr.get('stop')})
            for child in pr: 
                nc = ET.Element(child.tag, child.attrib); nc.text = child.text; new_pr.append(nc)
            tv_progs.append(new_pr); seen_prog.add(key)

# Senin liste için beinsports mapping
bein_map = {
    "bein sports 1": ["beinsports", "beinsports 1", "beIN SPORTS 1", "beIN SPORTS 1 HD"],
    "bein sports 2": ["beinsports 2", "beIN SPORTS 2", "beIN SPORTS 2 HD"],
    "bein sports 3": ["beinsports 3", "beIN SPORTS 3"],
    "bein sports 4": ["beinsports 4", "beIN SPORTS 4"],
    "bein sports 5": ["beinsports 5", "beIN SPORTS 5"],
    "bein sports haber": ["beinsports haber", "beIN SPORTS HABER"],
    "bein sports max 1": ["beinsports max 1", "beIN SPORTS MAX 1"],
    "bein sports max 2": ["beinsports max 2", "beIN SPORTS MAX 2"],
}
for base_target, aliases in bein_map.items():
    if base_target not in channel_by_base: continue
    src_progs = []
    for sid in channel_by_base[base_target]:
        src_progs.extend([p for p in tv_progs if p.get('channel','').lower() == sid.lower()])
    if not src_progs: continue
    for alias in aliases:
        alow = alias.lower()
        if alow not in tv_channels:
            ch = ET.Element('channel', {'id': alias}); ET.SubElement(ch, 'display-name').text = alias
            tv_channels[alow] = ch
        for pr in src_progs:
            key = (alow, pr.get('start'))
            if key in seen_prog: continue
            new_pr = ET.Element('programme', {'channel': alias, 'start': pr.get('start'), 'stop': pr.get('stop')})
            for child in pr: nc = ET.Element(child.tag, child.attrib); nc.text = child.text; new_pr.append(nc)
            tv_progs.append(new_pr); seen_prog.add(key)

final_tv = ET.Element('tv')
sorted_channels = sorted(tv_channels.values(), key=lambda x: x.get('id','').lower())
for ch in sorted_channels: final_tv.append(ch)
for pr in tv_progs: final_tv.append(pr)

ET.ElementTree(final_tv).write('epg.xml', encoding='utf-8', xml_declaration=True)

print(f"\nBITTI: {len(sorted_channels)} KANAL, {len(tv_progs)} PROGRAM")
print("BEIN KONTROL:")
for ch in sorted_channels:
    if "bein" in ch.get('id','').lower() or "beinsports" in ch.get('id','').lower():
        cnt = len([p for p in tv_progs if p.get('channel','').lower()==ch.get('id','').lower()])
        print(f" - {ch.get('id'):25} : {cnt} program")

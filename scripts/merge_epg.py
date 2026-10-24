
import gzip
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

SOURCES = [
    "https://www.open-epg.com/files/turkey1.xml.gz",
    "https://www.open-epg.com/files/turkey2.xml.gz",
    "https://www.open-epg.com/files/turkey3.xml.gz",
    "https://www.open-epg.com/files/turkey4.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
    "https://raw.githubusercontent.com/ahmethascelik/epghost/main/xmltv.xml",
]

def indir(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Turkiye-EPG-Merger/1.0"}
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        data = r.read(120 * 1024 * 1024)

    if data.startswith(b"\x1f\x8b"):
        data = gzip.decompress(data)

    return ET.fromstring(data)

def main():
    channels = {}
    programmes = {}
    basarili = 0

    for url in SOURCES:
        try:
            tv = indir(url)

            if tv.tag != "tv":
                raise ValueError("XMLTV formatı değil")

            for ch in tv.findall("channel"):
                cid = ch.get("id")
                if cid and cid not in channels:
                    channels[cid] = ET.tostring(
                        ch, encoding="unicode"
                    )

            for p in tv.findall("programme"):
                cid = p.get("channel")
                start = p.get("start", "")
                stop = p.get("stop", "")
                title = p.findtext("title", "").strip()

                if not cid or not start or not stop or not title:
                    continue

                key = (cid, start, stop, title.casefold())

                if key not in programmes:
                    programmes[key] = ET.tostring(
                        p, encoding="unicode"
                    )

            basarili += 1
            print("OK:", url)

        except Exception as e:
            print("KAYNAK HATASI:", url, str(e))

    if basarili < 2 or len(programmes) < 100:
        sys.exit("Yeterli veri alınamadı. Eski EPG korunacak.")

    root = ET.Element(
        "tv",
        {
            "source-info-name": "Türkiye EPG",
            "generator-info-name": "Aksaray EPG"
        }
    )

    for cid in sorted(channels):
        root.append(ET.fromstring(channels[cid]))

    for key in sorted(programmes):
        root.append(ET.fromstring(programmes[key]))

    ET.indent(root, space="  ")

    temp = "epg.xml.tmp"
    ET.ElementTree(root).write(
        temp,
        encoding="utf-8",
        xml_declaration=True
    )

    ET.parse(temp)
    os.replace(temp, "epg.xml")

    print("KANAL:", len(channels))
    print("PROGRAM:", len(programmes))
    print("KAYNAK:", basarili)
    print("epg.xml hazır.")

if __name__ == "__main__":
    main()

import re
import sys
import zipfile

z = zipfile.ZipFile(sys.argv[1] if len(sys.argv) > 1 else r"D:\CityCom-astra\submission\03_答辩PPT.pptx")
t = z.read("ppt/presentation.xml").decode("utf8")
m = re.search(r"<p14:sectionLst[^>]*>.*?</p14:sectionLst>", t, re.S)
print("sections present:", bool(m))
if m:
    for s in re.findall(r'<p14:section name="(.*?)"', m.group(0)):
        print("  section:", s)
    print("  slides per section:", [len(x) for x in re.findall(r"<p14:sldIdLst>(.*?)</p14:sldIdLst>", m.group(0), re.S)])
print("slides in sldIdLst:", t.count("<p:sldId "))
print("layouts:", sorted(n for n in z.namelist() if "slideLayouts/slideLayout" in n and n.endswith(".xml")))

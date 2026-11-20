"""Knowledge-base tool. The four pages carry their data as JSON lines (const DATA/GUIDES/META = ...).
extract: pages -> _data/kb.json (one master record per row/guide, with placements per system)
build:   _data/kb.json -> pages (+ version.json), and claude.ai variants into an output folder."""
import json, os, sys
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSS = ["sis", "exam", "iq", "bologna"]
FILE = {s: s + ".html" for s in SYSS}
ARTI = {"sis": "https://claude.ai/artifact/FBJo6FvyhwCjGJkUpWCtUJ", "exam": "https://claude.ai/artifact/9DEJ4mCYcWySKV8qrp8gCD",
        "iq": "https://claude.ai/artifact/CcFBq8kM3LdQGME8YYeq7V", "bologna": "https://claude.ai/artifact/RCRz9DfAiFrNyxgcpUDkfq"}

def _span(s, k):
    i = s.index("const %s = " % k) + len("const %s = " % k); j = s.index("\n", i)
    return i, j
def get(s, k):
    i, j = _span(s, k); return json.loads(s[i:j].rstrip(";"))
def put(s, k, v):
    i, j = _span(s, k); end = ";" if s[i:j].endswith(";") else ""
    return s[:i] + json.dumps(v, ensure_ascii=False).replace("</", "<\\/") + end + s[j:]

def extract():
    rows, guides, meta = {}, {}, None
    for sy in SYSS:
        s = open(os.path.join(R, FILE[sy]), encoding="utf-8").read()
        meta = meta or get(s, "META")
        for d in get(s, "DATA"):
            r = rows.setdefault(str(d["n"]), {k: v for k, v in d.items() if k not in ("tabs", "elsewhere", "vid")} | {"places": {}, "vid": {}})
            r["places"][sy] = d["tabs"]
            if d["vid"]: r["vid"][sy] = d["vid"]
        for g in get(s, "GUIDES"):
            m = guides.setdefault(g["id"], {k: v for k, v in g.items() if k != "tabs"} | {"places": {}, "order": {}})
            m["places"][sy] = g["tabs"]
    # guide order per page
    for sy in SYSS:
        s = open(os.path.join(R, FILE[sy]), encoding="utf-8").read()
        for i, g in enumerate(get(s, "GUIDES")): guides[g["id"]]["order"][sy] = i
    kb = {"meta": meta, "rows": rows, "guides": guides}
    json.dump(kb, open(os.path.join(R, "_data", "kb.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("rows", len(rows), "guides", len(guides))

def pages(kb):
    src = {sy: open(os.path.join(R, FILE[sy]), encoding="utf-8").read() for sy in SYSS}
    sysT = {sy: get(src[sy], "SYS")["title"] for sy in SYSS}
    tabN = {sy: {t[0]: t[1] for _, tabs in get(src[sy], "SYS")["tree"] for t in tabs} for sy in SYSS}
    out = {}
    for sy in SYSS:
        data = []
        for n in sorted(kb["rows"], key=int):
            r = kb["rows"][n]
            if sy not in r["places"]: continue
            d = {k: v for k, v in r.items() if k not in ("places", "vid")}
            d["tabs"] = r["places"][sy]
            d["elsewhere"] = [{"sys": sysT[o], "tab": tabN[o][t]} for o in SYSS if o != sy and o in r["places"] for t in r["places"][o]]
            d["vid"] = r["vid"].get(sy, [])
            data.append(d)
        gl = [g for g in kb["guides"].values() if sy in g["places"]]
        gl.sort(key=lambda g: g["order"].get(sy, 999))
        guides = [{k: v for k, v in g.items() if k not in ("places", "order")} | {"tabs": g["places"][sy]} for g in gl]
        s = put(src[sy], "DATA", data); s = put(s, "GUIDES", guides); s = put(s, "META", kb["meta"])
        out[sy] = s
    return out

def web_variant(s):
    """claude.ai copy: cross links point at the other artifacts instead of sibling files"""
    for sy in SYSS:
        s = s.replace('"href": "%s"' % FILE[sy], '"href": "%s"' % ARTI[sy]).replace('"href": "%s#' % FILE[sy], '"href": "%s#' % ARTI[sy])
    return s.replace('"homehref": "index.html"', '"homehref": ""')

def build(webdir=None):
    kb = json.load(open(os.path.join(R, "_data", "kb.json"), encoding="utf-8"))
    out = pages(kb)
    for sy, s in out.items():
        open(os.path.join(R, FILE[sy]), "w", encoding="utf-8").write(s)
        if webdir:
            os.makedirs(webdir, exist_ok=True)
            open(os.path.join(webdir, "kb_%s.html" % sy), "w", encoding="utf-8").write(web_variant(s))
    m = kb["meta"]
    json.dump({"version": len(m["updates"]), "latest": m["latest"], "updates": m["updates"]},
              open(os.path.join(R, "version.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("built", {sy: len(s) for sy, s in out.items()})

if __name__ == "__main__":
    {"extract": extract, "build": lambda: build(sys.argv[2] if len(sys.argv) > 2 else None)}[sys.argv[1]]()

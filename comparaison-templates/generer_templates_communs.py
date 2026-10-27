"""Compare les modèles de ressources Omeka S (répertoire resource-template des
dépôts GitHub des étudiants) et génère des modèles communs alignés sur le
vocabulaire commun (../comparaison-vocabulaires/artinq-commun.ttl).

Sorties :
  - templates-etudiants.json : instantané normalisé lu par index.html
  - templates-communs/*.json : modèles communs importables dans Omeka S

Usage : python3 generer_templates_communs.py
        (GITHUB_TOKEN=… optionnel pour éviter la limite de l'API GitHub)
"""
import csv
import io
import json
import os
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "comparaison-vocabulaires"))
from generer_vocabulaire_commun import CLASSES, PROPS  # noqa: E402

CSV_URL = ("https://docs.google.com/spreadsheets/d/e/2PACX-1vRMlsu0I54suBHsvYQWiEwlHfh6-b4H5IclZJ5E9XlvvKs-"
           "N0Qz9QJEw03Pot2i5LidtIcH693hPC2u/pub?gid=443052561&single=true&output=csv")
ARTINQ = "https://humanum-p8.fr/omk_artificialinquiries/onto/artinq#"
NS = {
    "artinq": (ARTINQ, "Artificial Inquiries"),
    "dcterms": ("http://purl.org/dc/terms/", "Dublin Core"),
    "foaf": ("http://xmlns.com/foaf/0.1/", "Friend of a Friend"),
}
PREFIX_OF = {uri: p for p, (uri, _) in NS.items()}
EXT_LABELS = {
    "dcterms:title": "Title", "dcterms:description": "Description", "dcterms:identifier": "Identifier",
    "dcterms:date": "Date", "dcterms:modified": "Date Modified", "dcterms:type": "Type",
    "dcterms:abstract": "Abstract", "dcterms:creator": "Creator", "dcterms:hasPart": "Has Part",
    "dcterms:references": "References", "foaf:name": "name", "foaf:nick": "nickname",
    "foaf:accountName": "account name",
}
# Identifiants Omeka S par défaut des premières propriétés Dublin Core
DCTERMS_IDS = ["title", "creator", "subject", "description", "publisher", "contributor", "date", "type",
               "format", "identifier", "source", "language", "relation", "coverage", "rights"]
DT_LABELS = {"literal": "Text", "resource:item": "Item", "uri": "URI"}


def get(url, api=False):
    req = urllib.request.Request(url, headers={"User-Agent": "artinq-compare"})
    if api and os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def repos_from_csv():
    rows = list(csv.reader(io.StringIO(get(CSV_URL))))
    col = next(i for i, h in enumerate(rows[0]) if h.strip().lower().startswith("lien vers le vocab"))
    seen = []
    for r in rows[1:]:
        m = re.search(r"github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(\S+)", r[col] if len(r) > col else "")
        if m and m.group(1, 2) not in [s[:2] for s in seen]:
            seen.append(m.groups())
    return seen


def exercise(repo):
    m = re.search(r"_(\d+(?:\.\w+)?)$", repo)
    return m.group(1) if m else repo


def vocab_terms(ttl):
    """Classes et propriétés artinq dans l'ordre du fichier (sans dépendance RDF)."""
    ttl = re.sub(r"(?m)#[^\n>]*$", "", ttl)
    classes, props = [], []
    for subj, types in re.findall(r"(?:^|\.)\s*(artinq:\w+|<[^>]+>)\s+(?:a|rdf:type)\s+([^;.]+)", ttl):
        name = re.sub(r"^.*[#:/]|>$", "", subj.rstrip(">"))
        if "Class" in types and name not in classes:
            classes.append(name)
        elif "Property" in types and name not in props:
            props.append(name)
    return classes, props


def qname(obj):
    uri = (obj or {}).get("vocabulary_namespace_uri")
    return (PREFIX_OF.get(uri, uri), obj.get("local_name")) if obj else None


def normalise(raw, vocab):
    """Ramène un modèle exporté (ou une réponse d'API) à une forme commune."""
    tpl = {"label": raw.get("o:label", ""), "issues": [], "inferred": False}
    props = raw.get("o:resource_template_property", [])
    if any("o:property" in p for p in props):
        # Réponse d'API : uniquement des identifiants, résolus ensuite dans resolve_api_ids()
        tpl["format"] = "api"
        tpl["inferred"] = True
        tpl["issues"].append("Réponse d'API (identifiants seulement) : non importable, termes déduits des identifiants")
        tpl["_cls_id"] = (raw.get("o:resource_class") or {}).get("o:id")
        out = []
        for p in props:
            pid = p["o:property"]["o:id"]
            q = ("dcterms", DCTERMS_IDS[pid - 1]) if pid <= len(DCTERMS_IDS) else ("?", pid)
            out.append((q, p))
    else:
        tpl["format"] = "export"
        out = [(qname(p), p) for p in props]
        tpl["class"] = qname(raw.get("o:resource_class"))
        tpl["title"] = qname(raw.get("o:title_property"))
        tpl["description"] = qname(raw.get("o:description_property"))
    tpl["props"] = []
    for (ns, local), p in out:
        dts = p.get("data_types") or p.get("o:data_type") or []
        tpl["props"].append({
            "ns": ns, "local": local, "required": bool(p.get("o:is_required")),
            "dataTypes": [d["name"] if isinstance(d, dict) else d for d in dts],
            "altLabel": p.get("o:alternate_label"),
        })
    return tpl


def resolve_api_ids(templates, vocab):
    """Omeka S attribue des identifiants consécutifs aux termes d'un vocabulaire
    importé, dans l'ordre du fichier, après ses 184 propriétés par défaut : le
    plus petit identifiant rencontré correspond donc au premier terme."""
    classes, vprops = vocab
    cls_ids = [t["_cls_id"] for t in templates if t.get("_cls_id")]
    prop_ids = [p["local"] for t in templates for p in t["props"] if p["ns"] == "?" and p["local"] > 184]
    for t in templates:
        cid = t.pop("_cls_id", None)
        i = cid - min(cls_ids) if cid and cls_ids else -1
        t["class"] = ("artinq", classes[i]) if 0 <= i < len(classes) else None
        for p in t["props"]:
            if p["ns"] != "?":
                continue
            j = p["local"] - min(prop_ids) if prop_ids and p["local"] > 184 else -1
            if 0 <= j < len(vprops):
                p["ns"], p["local"] = "artinq", vprops[j]
            else:
                p["local"] = f"id {p['local']}"


def check(tpl, vocab):
    classes, vprops = vocab
    c = tpl.get("class")
    if not c:
        tpl["issues"].append("Aucune classe associée")
    elif c[0] != "artinq":
        tpl["issues"].append(f"Classe hors de l'espace de noms artinq : {c[0]}")
    elif classes and c[1] not in classes:
        tpl["issues"].append(f"Classe {c[1]} absente du vocabulaire")
    missing = [p["local"] for p in tpl["props"] if p["ns"] == "artinq" and vprops and p["local"] not in vprops]
    if missing:
        tpl["issues"].append("Propriétés absentes du vocabulaire : " + ", ".join(missing))
    if not tpl["props"]:
        tpl["issues"].append("Aucune propriété")
    if tpl["format"] == "export" and not tpl.get("title"):
        tpl["issues"].append("Pas de propriété de titre définie")
    if tpl["props"] and not any(p["dataTypes"] for p in tpl["props"]):
        tpl["issues"].append("Aucun type de données précisé")


# ── Correspondances vers le vocabulaire commun ──
def sources_index(rows, name_idx, src_idx):
    idx = {}
    for row in rows:
        for s in row[src_idx].split(";"):
            s = s.strip()
            if s:
                ex, local = s.split(" ", 1)
                idx[(ex, local)] = row[name_idx]
    return idx


CLASS_MAP = sources_index(CLASSES, 0, 5)
PROP_MAP = sources_index(PROPS, 0, 7)
COMMON_PROPS = {p[0]: p for p in PROPS}
COMMON_CLASSES = {c[0]: c for c in CLASSES}


def common_prop(ex, ns, local):
    """Propriété à utiliser dans le modèle commun, sous forme 'prefix:local'."""
    if ns in ("dcterms", "foaf"):
        return f"{ns}:{local}"
    name = PROP_MAP.get((ex, local)) if ns == "artinq" else None
    return fold(name) if name else None


def fold(name):
    """Une propriété littérale alignée sur Dublin Core / FOAF est remplacée par
    le terme standard dans les modèles (titre et nom deviennent dcterms:title)."""
    if name in ("titre", "nom"):
        return "dcterms:title"
    rng, equiv = COMMON_PROPS[name][5], COMMON_PROPS[name][6]
    if equiv and (rng is None or ":" in rng):
        return equiv
    return f"artinq:{name}"


def datatype(q):
    if not q.startswith("artinq:"):
        return "literal"
    rng = COMMON_PROPS[q[7:]][5]
    if rng and ":" not in rng:
        return "resource:item"
    return "uri" if rng == "xsd:anyURI" else "literal"


def term_json(q):
    prefix, local = q.split(":")
    uri, vlabel = NS[prefix]
    if prefix != "artinq":
        label = EXT_LABELS.get(q, local)
    else:
        label = (COMMON_CLASSES.get(local) or COMMON_PROPS[local])[1]
    return {"vocabulary_namespace_uri": uri, "vocabulary_label": vlabel, "local_name": local, "label": label}


def build_common(students):
    by_class = defaultdict(list)
    for s in students:
        for t in s["templates"]:
            if t.get("class") and t.get("common"):
                by_class[t["common"]].append((s, t))
    results = []
    for cname, fr, en, comment, sub, _ in CLASSES:
        srcs = by_class.get(cname, [])
        stats = defaultdict(lambda: {"n": 0, "req": 0, "alt": Counter(), "from": []})
        for s, t in srcs:
            seen = set()
            for p in t["props"]:
                q = p.get("common")
                if not q or q in seen:
                    continue
                seen.add(q)
                st = stats[q]
                st["n"] += 1
                st["req"] += p["required"]
                if p["altLabel"]:
                    st["alt"][p["altLabel"]] += 1
                st["from"].append(f"{s['ex']} {p['ns']}:{p['local']}")
        # propriétés du vocabulaire commun dont le domaine est la classe (ou sa super-classe)
        domains = {cname, sub} - {None}
        for p in PROPS:
            if p[4] in domains:
                stats.setdefault(fold(p[0]), {"n": 0, "req": 0, "alt": Counter(), "from": []})
        for q in ("dcterms:title", "dcterms:description"):
            stats.setdefault(q, {"n": 0, "req": 0, "alt": Counter(), "from": []})
        order = sorted(stats, key=lambda q: (q != "dcterms:title", q != "dcterms:description", -stats[q]["n"], q))
        props = []
        for q in order:
            st = stats[q]
            alt = st["alt"].most_common(1)[0][0] if st["alt"] else None
            if q.startswith("artinq:"):
                alt = None  # le label du vocabulaire commun suffit
            required = q == "dcterms:title" or (st["req"] >= 2 and st["req"] * 2 > st["n"])
            dt = datatype(q)
            props.append({**term_json(q), "o:alternate_label": alt, "o:alternate_comment": None,
                          "o:is_required": required, "o:is_private": False, "o:default_lang": None,
                          "data_types": [{"name": dt, "label": DT_LABELS[dt]}],
                          "_q": q, "_n": st["n"], "_from": st["from"]})
        tpl = {
            "o:label": f"Artificial Inquiries – {fr}",
            "o:resource_template_property": [{k: v for k, v in p.items() if not k.startswith("_")} for p in props],
            "o:resource_class": {**term_json(f"artinq:{cname}")},
            "o:title_property": term_json("dcterms:title"),
            "o:description_property": term_json("dcterms:description"),
        }
        results.append({"class": cname, "label": fr, "comment": comment, "file": f"artinq_{cname}.json",
                        "sources": [f"{s['ex']} {t['label']}" for s, t in srcs], "template": tpl,
                        "props": [{"q": p["_q"], "required": p["o:is_required"], "dataType": p["data_types"][0]["name"],
                                   "n": p["_n"], "from": p["_from"], "alt": p["o:alternate_label"]} for p in props]})
    return results


def main():
    students = []
    for owner, repo, branch, path in repos_from_csv():
        s = {"owner": owner, "repo": repo, "ex": exercise(repo),
             "url": f"https://github.com/{owner}/{repo}/tree/{branch}/resource-template",
             "status": "ok", "error": None, "templates": []}
        students.append(s)
        try:
            vocab = vocab_terms(get(f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"))
        except Exception:
            vocab = ([], [])
        try:
            listing = json.loads(get(f"https://api.github.com/repos/{owner}/{repo}/contents/resource-template?ref={branch}", api=True))
        except Exception as e:
            s["status"], s["error"] = "absent", f"{e} — répertoire resource-template introuvable ou dépôt privé"
            print(f"  {repo}: {s['error']}")
            continue
        for f in sorted((x for x in listing if x["name"].endswith(".json")), key=lambda x: x["name"]):
            try:
                tpl = normalise(json.loads(get(f["download_url"])), vocab)
            except Exception as e:
                s["templates"].append({"file": f["name"], "label": f["name"], "format": "invalide",
                                       "issues": [f"JSON illisible : {e}"], "props": []})
                continue
            tpl["file"], tpl["url"] = f["name"], f["html_url"]
            s["templates"].append(tpl)
        resolve_api_ids([t for t in s["templates"] if t["format"] == "api"], vocab)
        for t in s["templates"]:
            if t["format"] == "invalide":
                continue
            check(t, vocab)
            t["common"] = CLASS_MAP.get((s["ex"], t["class"][1])) if t.get("class") else None
            for p in t["props"]:
                p["common"] = common_prop(s["ex"], p["ns"], p["local"])
        s["vocabClasses"] = vocab[0]
        print(f"  {repo}: {len(s['templates'])} modèles")

    students.sort(key=lambda s: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", s["ex"])])
    common = build_common(students)
    outdir = HERE / "templates-communs"
    outdir.mkdir(exist_ok=True)
    for c in common:
        (outdir / c["file"]).write_text(json.dumps(c["template"], ensure_ascii=False, indent=4), encoding="utf-8")
    snapshot = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "students": students,
                "common": [{k: v for k, v in c.items() if k != "template"} for c in common]}
    (HERE / "templates-etudiants.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{sum(len(s['templates']) for s in students)} modèles étudiants, {len(common)} modèles communs générés")


if __name__ == "__main__":
    main()

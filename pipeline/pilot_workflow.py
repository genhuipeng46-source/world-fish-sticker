# Pilot workflow: for each species -> pick refs -> generate -> blind review -> up to 3 rounds.
import json, os
ROOT = "/Users/penggenhui/.gemini/antigravity/brain/892d923c-0d1e-443e-8902-ca2f682c36c0/scratch/pilot"
ART = "/Users/penggenhui/.gemini/antigravity/brain/892d923c-0d1e-443e-8902-ca2f682c36c0"
CARDS = json.load(open("/Users/penggenhui/GitHub项目/world-fish-sticker/pipeline/pilot_cards.json"))
MAN = {m["id"]: m for m in json.load(open(ROOT + "/manifest.json"))}
ONLY = args.get("only")  # optional list of ids
MAXR = args.get("max_rounds", 3)
ids = [i for i in MAN if (not ONLY or i in ONLY)]

PICK_SCHEMA = {"type": "object", "properties": {
    "picks": {"type": "array", "items": {"type": "integer"}},
    "quality": {"type": "string", "enum": ["good", "usable", "poor"]},
    "note": {"type": "string"}}, "required": ["picks", "quality", "note"]}
GEN_SCHEMA = {"type": "object", "properties": {"path": {"type": "string"}, "note": {"type": "string"}},
              "required": ["path", "note"]}
REV_SCHEMA = {"type": "object", "properties": {
    "scores": {"type": "object", "properties": {k: {"type": "integer", "minimum": 0, "maximum": 4} for k in
               ["identification", "colour_pattern", "fins", "head", "proportions"]},
               "required": ["identification", "colour_pattern", "fins", "head", "proportions"]},
    "structural_checks": {"type": "array", "items": {"type": "object", "properties": {
        "check": {"type": "string"}, "expected": {"type": "string"}, "observed": {"type": "string"},
        "ok": {"type": "boolean"}}, "required": ["check", "expected", "observed", "ok"]}},
    "pose_ok": {"type": "boolean"},
    "field_guide_plate_ok": {"type": "boolean"},
    "corrections": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
    "summary": {"type": "string"}},
    "required": ["scores", "structural_checks", "pose_ok", "field_guide_plate_ok", "corrections", "summary"]}

def passes(r):
    s = r["scores"]
    return (min(s.values()) >= 3 and s["identification"] == 4 and r["pose_ok"]
            and r["field_guide_plate_ok"] and all(c["ok"] for c in r["structural_checks"]))

def brief(sid, refs, tier, corrections):
    c = CARDS[sid]; m = MAN[sid]
    lines = [
        "Landscape canvas, aspect ratio 3:2. Exactly ONE fish, complete and centred with generous margin; snout and tail tips fully inside the frame.",
        "Entire background flat solid light grey #D9D9D9: no shadow, no water, no rocks, no plants, no text, no outline, no white sticker border.",
        "Photorealistic field-guide plate quality, crisp scales and fin membranes; not a cartoon, not stylised.",
        "Default pose: perfect side view, head pointing to the LEFT edge, body straight and horizontal, mouth closed, eye fully visible, ALL fins spread open and visible.",
        f"View for this species (overrides default where different): {c['view']}.",
        f"The fish: {c['en']}, {m['scientificName']}. Life stage / sex: {c['stage']}. Draw live colouration, not a preserved specimen.",
        f"Features: {c['card']}",
        f"Most confusable species (draw the differences): {c['confuse']}",
        "Structural facts that MUST be correct: " + "; ".join(f"{k}: {v}" for k, v in c["checks"].items()) + ".",
    ]
    if refs:
        if tier == "C":
            lines.append("Reference images attached are PRESERVED MUSEUM SPECIMENS: use them ONLY for body shape, fin positions and proportions. Their colours are faded - take colour from the text above.")
        else:
            lines.append("Reference photos attached: use them ONLY to check colour, markings, fins and proportions. Do NOT copy their pose, angle, background, lighting, other fish, hands or containers.")
    if corrections:
        lines.append("CORRECTIONS from the previous review - these take priority over everything else: " + " ".join(f"({i+1}) {x}" for i, x in enumerate(corrections)))
    return "\n".join(lines)

async def pick_refs(sid):
    m = MAN[sid]
    if m["tier"] in ("C", "D") or not m.get("candidates"):
        return [r["file"] for r in m.get("refs", [])][:2], m["tier"], "n/a"
    sheet = f"{ROOT}/sheets/{sid}.jpg"
    r = await agent(
        f"Reference photo selector. Open the contact sheet image {sheet} with read_file. It shows up to 10 numbered "
        f"candidate photos (label = number + licence tier A/B) of the fish species {m['scientificName']}. Pick the 1-3 "
        "candidates that best show the WHOLE fish clearly from the side (lateral), sharp, true colours, ideally live. "
        "Prefer tier A over B when quality is similar. Reject frontal, blurry, tiny, partial or wrong-species shots. "
        "Rate overall quality of your best picks: good / usable / poor.",
        schema=PICK_SCHEMA, role=f"Pick refs {sid}", type_name="research", model="flash")
    cands = {c["n"]: c for c in m["candidates"]}
    chosen = [cands[n] for n in r["picks"] if n in cands][:3]
    tier = "A" if any(c["tier"] == "A" for c in chosen) else ("B" if chosen else "D")
    return [c["file"] for c in chosen], tier, r["quality"] + ": " + r["note"]

async def generate(sid, rnd, refs, tier, corrections):
    out = f"{ROOT}/gen/{sid}/r{rnd}.jpg"
    b = brief(sid, refs, tier, corrections)
    res = await agent(
        "Image production runner. Steps:\n"
        "1. Invoke the subagent type 'image-generator' (invoke_subagent) with the brief below. Tell it to generate ONE image with aspect ratio 3:2"
        + (f", passing these reference image paths as input images: {refs}" if refs else ", with no reference images") +
        ", and to reply with the saved file path. Then wait for its reply message (do not poll).\n"
        f"2. With run_command: mkdir -p {ROOT}/gen/{sid} && mv '<saved path>' '{out}' (convert nothing).\n"
        f"3. finish with path='{out}' and a one-line note.\n\nBRIEF FOR THE IMAGE GENERATOR (pass verbatim):\n" + b,
        schema=GEN_SCHEMA, role=f"Generate {sid} r{rnd}", type_name="self", model="flash")
    return res["path"], b

async def review(sid, img, refs, tier):
    c = CARDS[sid]; m = MAN[sid]
    ref_txt = (f"Reference photos of the real species (for comparison): {refs}." if refs and tier in ("A", "B") else
               f"Reference images are preserved specimens (shape only, colours faded): {refs}." if refs else
               "No reference photos exist; judge against the text and your own knowledge.")
    return await agent(
        "Strict ichthyology plate reviewer. Use read_file to open the generated illustration "
        f"{img} and the references. Species: {m['scientificName']} ({c['en']}), {c['stage']}. Required view: {c['view']}.\n"
        f"Feature card: {c['card']}\nConfusable species: {c['confuse']}\n{ref_txt}\n"
        "Score 0-4 each: identification (recognisable as THIS species vs confusables), colour_pattern, fins (number, position, shape), "
        "head (mouth position, barbels, eye, gill cover), proportions. Do every structural check below and report expected vs observed "
        "honestly; look closely, count fins and barbels: " + json.dumps(c["checks"]) +
        ". Also check: extra or missing fins anywhere, fins attached in impossible places, pose/view/background rules (single fish, "
        "head left unless view says otherwise, all fins visible, plain grey background). field_guide_plate_ok = would an ichthyologist "
        "accept it as a field-guide plate. If anything is wrong give up to 3 corrections written as direct drawing instructions "
        "(e.g. 'the adipose fin is missing: add a small fleshy fin on the back between the dorsal fin and the tail').",
        schema=REV_SCHEMA, role=f"Review {sid}", type_name="research")

async def run_species(sid):
    refs, tier, refnote = await pick_refs(sid)
    hist = []; corrections = []
    for rnd in range(1, MAXR + 1):
        img, b = await generate(sid, rnd, refs, tier, corrections)
        rv = await review(sid, img, refs, tier)
        ok = passes(rv)
        hist.append({"round": rnd, "image": img, "review": rv, "pass": ok})
        log(f"{sid} r{rnd} {'PASS' if ok else 'fail'} {rv['scores']} | {rv['summary'][:120]}")
        if ok: break
        corrections = rv["corrections"]
    res = {"id": sid, "tier": tier, "refs": refs, "refnote": refnote, "rounds": hist,
           "passed": hist[-1]["pass"], "n_rounds": len(hist)}
    json.dump(res, open(f"{ROOT}/results/{sid}.json", "w"), ensure_ascii=False, indent=1)
    return res

async def safe_species(sid):
    try:
        return await run_species(sid)
    except Exception as e:
        log(f"{sid} ERROR {e}")
        return {"id": sid, "tier": "?", "passed": False, "n_rounds": 0, "error": str(e)}

os.makedirs(ROOT + "/results", exist_ok=True)
phase("Pilot")
BATCH = args.get("batch", 6)
allres = []
for i in range(0, len(ids), BATCH):
    chunk = ids[i:i + BATCH]
    allres += await parallel(chunk, lambda s: safe_species(s))
log(f"passed {sum(r['passed'] for r in allres)}/{len(allres)}; mean rounds {sum(r['n_rounds'] for r in allres)/len(allres):.2f}")
print(json.dumps([{k: r[k] for k in ("id", "tier", "passed", "n_rounds")} for r in allres]))

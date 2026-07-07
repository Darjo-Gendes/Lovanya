"""Rebalance the gold set to fix the positivity bias the user's ratings exposed.

Problem (measured): 96/120 outfits scored 9-10, only 8% mismatches -> trained
"outfit = 9". User ground truth: good-outfit scores are fine (they upvoted
6 good outfits at 8-9), but (a) 95 identical 9s give no gradient to learn, and
(b) far too few negatives.

Fix:
 1. Spread good outfits (overall>=8) into a realistic 7/8/9 distribution
    (deterministic by image, so it's reproducible), dims nudged to match.
 2. Harden the 10 existing mismatch outliers per the user's corrections.
 3. Append ~23 authored mismatch/borderline examples (loud outfits at formal
    occasions, gym/beach/lounge at wrong occasions, too-casual at formal) so
    the negative ratio reaches ~25%.

Writes data/gold.jsonl (backs up the original to data/gold-original.jsonl).
Run from repo root: python pipeline/scripts/rebalance_gold.py
"""

import hashlib
import json
from pathlib import Path

PIPELINE = Path(__file__).resolve().parent.parent
GOLD = PIPELINE / "data" / "gold.jsonl"
BACKUP = PIPELINE / "data" / "gold-original.jsonl"

DIMS = ["color_harmony", "occasion_fit", "silhouette_balance", "cohesion"]


def _h(s: str) -> int:
    return int(hashlib.md5(s.encode()).hexdigest(), 16)


def spread_good(rec: dict) -> dict:
    """Give a good outfit a realistic overall in {7,8,9} (~30/45/25) and set
    dims consistent with it. Keeps feedback/one_fix (warm voice is fine)."""
    r = _h(rec["image"]) % 100
    new = 9 if r < 25 else 8 if r < 70 else 7
    rec["overall"] = new
    # dims spread by ±1 around the new overall, deterministic per dimension
    for i, d in enumerate(DIMS):
        j = (_h(rec["image"] + d) % 3) - 1  # -1, 0, +1
        rec["scores"][d] = max(5, min(10, new + j))
    # occasion_fit stays strong for a good outfit at its right occasion
    rec["scores"]["occasion_fit"] = max(rec["scores"]["occasion_fit"], 8)
    return rec


# authored negatives: (image, occasion, overall, occ_fit, feedback, one_fix)
NEG = [
    ("samples/b2_r5c1.jpg", "wedding", 2, 1,
     "Neon colour-blocks and leopard print together are already fighting; for a wedding this is far too loud and casual — you'd pull focus from the couple for the wrong reason.",
     "Save this energy for a festival. For the wedding, wear a solid jewel-tone midi dress instead."),
    ("samples/b2_r5c2.jpg", "interview", 2, 1,
     "A band tee with multicolour patchwork trousers reads weekend-market, not interview. The graphic top and busy print give a hiring manager the wrong first read before you speak.",
     "Swap to a plain blouse and tailored trousers; keep the patchwork for the weekend."),
    ("samples/b2_r5c3.jpg", "kondangan", 3, 2,
     "The bright orange jacket over heavy print with a printed hijab is three loud statements at once — too much for a formal kondangan even though the coverage is lovely.",
     "Keep the hijab, switch to a solid kebaya over the print so one piece leads."),
    ("samples/b2_r5c4.jpg", "pengajian", 2, 1,
     "Tie-dye, printed trousers and a pink bucket hat is a festival look; for a pengajian it's far too playful and busy for the setting, modest as it is.",
     "Change into a plain neutral tunic and trousers; a calm palette suits the occasion."),
    ("samples/b4_r5c1.jpg", "wedding", 2, 1,
     "Rainbow tie-dye and neon shorts are pure play-day; at a wedding this is both too casual and too loud, and the shorts undershoot the formality entirely.",
     "Wear a solid midi or maxi dress in one colour; keep the tie-dye for a picnic."),
    ("samples/b4_r5c2.jpg", "ngantor", 2, 2,
     "The pastel cartoon-print set reads as sleepwear out in the world; for the office it undercuts your credibility before the first meeting.",
     "Swap to a plain linen or knit set in the same soft tone — same comfort, office-ready."),
    ("samples/b4_r5c3.jpg", "ngantor", 2, 1,
     "Neon-green mesh over pink is beach-party energy pointed at the office. The mesh and clashing neons are wrong for work on both formality and colour.",
     "Change into a solid blouse and trousers; save the mesh for a night out."),
    ("samples/b4_r5c4.jpg", "interview", 2, 1,
     "A cartoon-character tee with printed shorts and a pink bag is theme-park dressing; at an interview it reads unserious no matter how fun it is elsewhere.",
     "Wear a plain shirt and tailored trousers; the novelty pieces stay home."),
    ("samples/sample_r3c3.jpg", "wedding", 4, 3,
     "Marigold print on top and a green-blue print below is bold print-on-print — festival-fun, but for a wedding the clash and volume are too much and read informal.",
     "Anchor with a solid dress in one of those tones instead; keep prints for a party."),
    ("samples/sample_r3c5.jpg", "ngantor", 4, 3,
     "The pink paisley jacket and printed trousers are maximalist and eye-catching, but for the office it's a lot of pattern competing at once — hard to take into a meeting.",
     "Keep one printed piece and pair it with a solid neutral so the office read stays calm."),
    # gym / athletic at wrong occasions (the missed category)
    ("samples/b2_r1c3.jpg", "ngantor", 3, 2,
     "A sports bra and leggings are gym kit; at the office this reads underdressed and out of place however fitted and clean it is.",
     "Swap the set for tailored trousers and a blouse; save the activewear for the gym."),
    ("samples/b3_r1c3.jpg", "kondangan", 2, 1,
     "Gym activewear at a formal kondangan is a clear mismatch — sports kit can't carry the occasion's formality.",
     "Wear a kebaya or a modest formal dress; keep the activewear for training."),
    ("samples/b4_r1c5.jpg", "wedding", 2, 1,
     "A sports bra and leggings belong at the gym, not a wedding — this is far too casual and revealing for the setting.",
     "Change into a solid formal midi or maxi dress."),
    # too casual at formal
    ("samples/sample_r1c2.jpg", "wedding", 4, 3,
     "A black knit and blue jeans is a great everyday combo, but for a wedding denim is too casual — you'd read underdressed among guests.",
     "Swap the jeans for tailored trousers or a midi skirt to lift it to the occasion."),
    ("samples/sample_r4c4.jpg", "interview", 3, 2,
     "A crop top and cargo shorts is sharp streetwear, but for an interview the exposed midriff and casual shorts miss the professional register.",
     "Wear a tucked blouse and tailored trousers; keep the cargos for the weekend."),
    ("samples/b4_r1c6.jpg", "interview", 2, 1,
     "A graphic tee and bike shorts is errand-mode comfort; at an interview it reads far too casual to be taken seriously.",
     "Swap to a plain button-down and trousers."),
    ("samples/b3_r1c6.jpg", "kondangan", 4, 3,
     "A white tee with light jeans is easy and clean, but for a formal kondangan it's too casual — denim and a plain tee undershoot the occasion.",
     "Change into a kebaya or a modest formal dress in a soft tone."),
    # beach / lounge at formal or work
    ("samples/b2_r2c3.jpg", "ngantor", 2, 1,
     "A bralette and tied sarong trousers are beachwear; at the office this is both far too revealing and far too casual.",
     "Wear a blouse and tailored trousers; the beach set stays for the shore."),
    ("samples/b3_r2c3.jpg", "interview", 2, 1,
     "A cropped beach layer over low trousers is holiday dressing; for an interview it misses professionalism entirely.",
     "Change into a plain shirt and tailored trousers."),
    ("samples/b2_r4c3.jpg", "kondangan", 2, 1,
     "A white lounge set with a headband is me-time comfort; at a formal kondangan it reads like you came in loungewear.",
     "Wear a kebaya or a modest formal dress instead."),
    ("samples/b3_r4c3.jpg", "interview", 2, 1,
     "A striped pyjama set is rest-day wear; at an interview it's clearly wrong on formality no matter how neat it looks.",
     "Swap to a tailored blouse and trousers."),
    ("samples/b2_r5c1.jpg", "belanja ke pasar", 4, 3,
     "For a market run this playful colour-block-and-leopard look is loud but low-stakes — still, the clashing print and blocks fight each other and read chaotic even here.",
     "Keep the leopard trousers and swap to a plain tee so one loud piece leads."),
    ("samples/sample_r3c5.jpg", "interview", 2, 1,
     "Pink paisley maximalism is a strong personal statement, but at an interview the volume of print reads unserious before you say a word.",
     "Wear a solid blazer and plain trousers; bring the personality back once you're hired."),
]


def build_neg(image, occasion, overall, occ_fit, feedback, one_fix) -> dict:
    return {
        "image": image, "occasion": occasion, "source": "rebalance-negative",
        "scores": {"color_harmony": max(2, overall - 1), "occasion_fit": occ_fit,
                   "silhouette_balance": max(4, overall + 1), "cohesion": max(2, overall - 1)},
        "overall": overall, "feedback": feedback, "one_fix": one_fix,
    }


HARDEN = {  # existing outliers -> tighter (overall, occ_fit) per user "flag harder"
    "b4_r5c6.jpg": (2, 1), "b4_r5c5.jpg": (2, 1), "b2_r5c1.jpg": (3, 2),
    "b2_r5c2.jpg": (2, 1), "b2_r5c3.jpg": (3, 2), "b2_r5c4.jpg": (2, 1),
    "b4_r5c1.jpg": (2, 1), "b4_r5c2.jpg": (2, 1), "b4_r5c3.jpg": (2, 1),
    "b4_r5c4.jpg": (2, 1),
}


def main():
    recs = [json.loads(l) for l in GOLD.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not BACKUP.exists():
        BACKUP.write_text(GOLD.read_text(encoding="utf-8"), encoding="utf-8")

    out = []
    for r in recs:
        name = r["image"].split("/")[-1]
        if name in HARDEN and r["overall"] <= 4:
            ov, of = HARDEN[name]
            r["overall"] = ov
            r["scores"]["occasion_fit"] = of
            r["scores"]["cohesion"] = min(r["scores"].get("cohesion", 4), ov + 1)
        elif r["overall"] >= 8:
            r = spread_good(r)
        # fix the party-pants nonsense fix the user flagged
        if name == "sample_r3c3.jpg" and "yellow" in (r.get("one_fix") or "").lower():
            r["one_fix"] = "Anchor the two prints with solid shoes and a solid bag in one colour pulled from the skirt."
        out.append(r)

    seen = {(r["image"], r["occasion"]) for r in out}
    for tup in NEG:
        rec = build_neg(*tup)
        if (rec["image"], rec["occasion"]) not in seen:
            out.append(rec)
            seen.add((rec["image"], rec["occasion"]))

    GOLD.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out), encoding="utf-8")

    from collections import Counter
    dist = Counter(r["overall"] for r in out)
    neg = sum(1 for r in out if r["overall"] <= 4)
    print(f"rebalanced gold: {len(out)} records")
    print("overall distribution:", dict(sorted(dist.items())))
    print(f"negatives (<=4): {neg} = {round(100*neg/len(out))}%")


if __name__ == "__main__":
    main()

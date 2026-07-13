# Garment archetypes & capture checklists

The canonical library the vision model snaps to when describing garments for
generation. Same philosophy as styling-framework.md: the knowledge lives in
this FILE, editable without touching code. local_describe.py injects one
category section into each pass-2 prompt.

Rules of use (for the vision model):
- Pick the CLOSEST archetype; record the instance's deviations (color,
  material, hardware, pattern) rather than inventing a new shape.
- Fill EVERY checklist field for the category — these are the attributes the
  image generator cannot guess. "not visible (inferred: ...)" is allowed.
- The final `prompt` starts from the archetype's render phrase, then adds this
  instance's color/material/deviations. 20–45 words, plain color names.

## hijab

Checklist: style (square scarf / rectangular shawl / instant slip-on) ·
fabric (voile, chiffon, jersey, satin, pashmina) · finish (matte / sheen) ·
edge (baby hem, eyelash fringe, laser-cut) · pattern.

- **square voile hijab** — classic square scarf, matte crepe-like weave;
  render: "a square voile hijab scarf, soft matte weave, baby-hem edges, folded flat into a neat square"
- **rectangular pashmina shawl** — long rectangle, slightly heavier drape;
  render: "a long rectangular pashmina hijab shawl, soft matte drape, neatly folded lengthwise"
- **instant slip-on hijab (bergo)** — pre-sewn, rounded face opening;
  render: "an instant slip-on hijab with pre-sewn rounded face opening, smooth jersey fabric, laid flat"
- **satin square scarf** — glossy, fluid; render: "a square satin hijab scarf with soft glossy sheen, fluid drape, folded flat"
- **jersey wrap hijab** — stretchy knit, unhemmed ends;
  render: "a stretchy jersey wrap hijab, soft matte knit, gently rolled edges, laid flat"

## top

Checklist: type (button-up shirt/kemeja, blouse, tee, knit sweater, sweater
vest, tunic) · collar/neckline · sleeve length + cuff · fit (slim, relaxed,
oversized) · length (cropped, hip, tunic) · closure · pattern.

- **classic button-up shirt (kemeja)** — shirt collar, full button placket, cuffed sleeves;
  render: "a classic button-up shirt with shirt collar, full front button placket, long cuffed sleeves, relaxed fit"
- **band-collar blouse** — collarless mandarin band, clean placket;
  render: "a band-collar blouse with mandarin neckline, concealed placket, long sleeves, flowy relaxed fit"
- **oversized cotton tee** — drop shoulders, ribbed crew neck;
  render: "an oversized cotton t-shirt with ribbed crew neck, drop shoulders, straight boxy body"
- **ribbed knit sweater** — visible rib texture, ribbed hems;
  render: "a ribbed knit sweater with crew neck, long sleeves, ribbed cuffs and hem, relaxed fit"
- **sweater vest** — sleeveless V-neck knit, worn layered over a shirt;
  render: "a sleeveless V-neck sweater vest in fine knit, ribbed trims, straight hip-length body"
- **flowy tunic** — longline, side slits, often worn over trousers;
  render: "a flowy tunic top, longline body reaching upper thigh, long sleeves, soft drapey fabric, side slits"

## bottom

Checklist: type (trousers, jeans, skirt, culottes) · waist (high/mid, belt
loops, belt) · leg or skirt shape (wide, straight, tapered, pleated, A-line)
· length (full, ankle, midi, maxi) · front details (crease, pleats, fly) ·
pattern.

- **high-waist wide-leg trousers** — clean straight-to-wide fall from a high waist;
  render: "high-waisted wide-leg trousers with a clean straight fall, front crease, full length, smooth tailored fabric"
- **straight tailored trousers** — pressed crease, slim belt or loops;
  render: "straight-leg tailored trousers with pressed front creases, high waist with belt loops, ankle-full length"
- **relaxed jeans** — visible denim weave, five-pocket;
  render: "relaxed straight-leg jeans in washed denim, five-pocket styling, full length"
- **pleated midi skirt** — accordion/knife pleats, midi length;
  render: "a pleated midi skirt with fine accordion pleats falling straight from the waistband"
- **A-line maxi skirt** — smooth flare to floor;
  render: "an A-line maxi skirt flaring gently from a fitted waistband to floor length, smooth matte fabric"
- **palazzo culottes** — very wide, cropped above ankle;
  render: "wide palazzo culottes with a flat waistband, extra-wide legs, cropped above the ankle"

## dress

Checklist: silhouette (A-line, straight, wrap, tiered) · length (midi, maxi)
· sleeves · neckline · closure (buttons, zip, wrap tie) · tiers/ruffles ·
pattern.

- **A-line maxi dress** — fitted top flaring to floor;
  render: "an A-line maxi dress with long sleeves, modest round neckline, gently flaring to floor length"
- **abaya** — loose straight full-length robe, often open-front;
  render: "a loose full-length abaya robe with straight relaxed silhouette, long wide sleeves, floor length"
- **shirt dress** — full button front, shirt collar, often belted;
  render: "a maxi shirt dress with shirt collar, full-length button placket, long sleeves, fabric belt at the waist"
- **tiered ruffle maxi dress** — stacked gathered tiers;
  render: "a tiered maxi dress with three gathered ruffle tiers, long sleeves, flowy lightweight fabric"
- **wrap dress** — crossover front, side tie;
  render: "a wrap maxi dress with crossover V front, side tie closure, long sleeves, soft drapey fabric"

## outerwear

Checklist: type (blazer, trench/coat, cardigan, jacket, puffer) · breast
style (single/double) + BUTTON COUNT + button color · lapel/collar type
(notch, peak, shawl, collarless) · length (hip, mid-thigh, knee, longline) ·
shoulder (structured / relaxed drop) · pockets (flap, patch, welt) · belt ·
pattern.

- **longline single-breasted blazer** — THE modest-fashion staple; mid-thigh+,
  relaxed shoulders; render: "a longline single-breasted blazer, notch lapels, one-or-two button front, flap pockets, relaxed straight cut reaching mid-thigh"
- **oversized boxy blazer** — wide drop shoulders, hip-length;
  render: "an oversized boxy blazer with wide drop shoulders, notch lapels, single-button front, hip length"
- **double-breasted trench coat** — storm flap, waist belt, 6+ buttons;
  render: "a classic double-breasted trench coat with wide lapels, two button columns, waist belt with buckle, knee length"
- **long knit cardigan** — no buttons or few, soft knit, longline;
  render: "a long open-front knit cardigan, soft ribbed knit, no closures, relaxed straight fall to mid-thigh"
- **denim jacket** — trucker style, metal buttons;
  render: "a classic denim trucker jacket with metal shank buttons, chest flap pockets, hip length"
- **puffer jacket** — horizontal quilting;
  render: "a quilted puffer jacket with horizontal channels, zip front, high collar, hip length"

## bag

Checklist — ORIENTATION IS MANDATORY: orientation (LANDSCAPE wider-than-tall
/ PORTRAIT taller-than-wide / SQUARE) with rough W:H ratio · silhouette
(structured box, saddle, tote, hobo, bucket, baguette) · size (mini, small,
medium, large) · top/closure (flap, zip, open, drawstring, clasp) · strap
(single/double, slim/wide, chain/leather, short handle vs long crossbody) ·
hardware color (gold, silver, brass, none).

CANONICAL COMPLETION RULE (bags): rigid leather goods are identified by their
hardware and material — when these are not clearly visible in the photo,
inherit the archetype's canonical spec below and flag it "(inferred)". A
plausible canonical detail beats a hedged omission.

- **box-flap crossbody** — structured LANDSCAPE rectangle (wider than tall,
  ~4:3), front flap, clasp, long slim strap; canonical: smooth structured
  leather with a slight sheen, GOLD metal clasp lock centered on the flap,
  crisp edges holding a firm box shape;
  render: "a structured box-flap crossbody bag in smooth leather, wide landscape rectangle clearly wider than tall, firm crisp edges, full-width front flap with a gold metal clasp lock, long slim leather shoulder strap"
- **saddle bag** — curved-bottom flap, landscape;
  render: "a saddle bag with rounded curved bottom, landscape orientation, curved front flap, medium crossbody strap"
- **structured tote** — PORTRAIT or square, open top, double handles;
  render: "a structured tote bag, upright portrait rectangle, open top, two short top handles"
- **slouchy hobo** — soft crescent, slumps;
  render: "a slouchy hobo bag with soft crescent shape, relaxed slumped body, single shoulder strap"
- **bucket bag** — cylinder, drawstring;
  render: "a bucket bag with cylindrical body, drawstring top closure, single crossbody strap"
- **mini top-handle** — small square-ish, one short handle;
  render: "a mini top-handle bag, small near-square structured body, single short rounded handle, detachable strap"
- **baguette** — short wide LANDSCAPE, short shoulder strap;
  render: "a baguette shoulder bag, short wide landscape body, front flap, short shoulder strap"

## shoes

Checklist: type · toe shape (round, almond, square) · heel (flat, block,
kitten) · fastening (laces, straps, slip-on) · sole color.

- **white low-top sneakers**; render: "a pair of white low-top sneakers with clean minimal upper, flat rubber sole, tonal laces"
- **ballet flats**; render: "a pair of ballet flats with rounded toe, low-cut vamp, slim flat sole"
- **strappy flat sandals**; render: "a pair of flat sandals with slim crossing straps and ankle strap, flat sole"
- **loafers**; render: "a pair of classic loafers with almond toe, low stacked heel, penny strap detail"
- **block-heel mules**; render: "a pair of backless mules with square toe and mid block heel"
- **ankle boots**; render: "a pair of ankle boots with almond toe, low block heel, side zip"

## accessory

Checklist: type (watch, glasses, necklace, bracelet, belt, earrings) ·
material + finish (polished/brushed metal, leather, acetate) · size/width ·
watch: case shape + dial color + band type · belt: width + buckle shape.

- **metal-band analog watch**; render: "an analog wristwatch with round polished metal case, matching metal link band, minimalist dial"
- **leather-strap watch**; render: "an analog wristwatch with round case and slim leather strap, clean minimalist dial"
- **thin-frame glasses**; render: "a pair of thin-frame eyeglasses with slim metal rims and clear lenses"
- **delicate chain necklace**; render: "a delicate fine-chain necklace with small minimal pendant, polished finish"
- **slim leather belt**; render: "a slim leather belt with small polished buckle, clean minimal strap"
- **stud earrings**; render: "a pair of small stud earrings, polished metal, minimal design"
- **chain bracelet** — worn on the WRIST, not a waist belt; render: "a delicate chain-link bracelet, fine polished metal, small clasp, shown laid flat in a gentle curve"
- **bangle** — rigid wrist ring; render: "a slim rigid bangle bracelet, smooth polished metal, single circular band"
- **beaded bracelet**; render: "a beaded bracelet, small round beads on an elastic strand, shown laid flat in a circle"
- **cuff bracelet**; render: "a wide open cuff bracelet, smooth metal, C-shaped rigid band worn on the wrist"

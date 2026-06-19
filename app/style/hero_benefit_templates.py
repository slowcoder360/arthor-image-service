"""Benefit-first hero prompt templates — industry keyword → subject × variant (compiler 4.0)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BenefitTemplate:
    benefit_subject: str
    people: str
    avoid: tuple[str, ...] = ()
    setting: str | None = None


# Shared people policies (4.2 — field trades: candid face, not lens stare; dental/desk: direct OK)
_FIELD_CUSTOMER_CANDID = (
    "homeowner or customer in three-quarter profile or candid side glance — face readable but "
    "not direct intense eye contact with camera; not stock portrait stare at lens"
)
_FIELD_PROVIDER_BACK = (
    f"{_FIELD_CUSTOMER_CANDID}; service provider back, three-quarter rear, "
    "or profile — never provider facing camera without team likeness refs"
)
_WIP_WORKER = (
    "worker back or profile at active job site; if customer present, three-quarter or candid "
    "profile only — not direct stare at lens; trade-accurate tools and context"
)
_POST_JOB_TRUST = (
    "satisfied homeowner in three-quarter or candid profile at completed work — not direct stare "
    "at camera; provider back or profile — not kitchen-table consult or doorway inversion"
)
_DESK_BOTH_FACES = (
    "provider and customer both faces visible in professional consultation; natural engagement, "
    "not stock grin at lens"
)
_ENV_OPTIONAL = (
    "people optional — anonymous silhouettes, backs, or soft profiles only; "
    "no one staring directly at camera; environment is hero"
)
_CLINICAL_ONE_ONLY = (
    "exactly one person in scrubs, white coat, or clinical uniform; patient in everyday street clothes; "
    "both faces visible — never both subjects in medical attire"
)

# --- home_services shared v1/v2 ---
_HOME_WIP = BenefitTemplate(
    benefit_subject="work in progress — technician actively performing the trade at the home",
    people=_WIP_WORKER,
    avoid=("doorway consult", "kitchen table", "iPad desk meeting", "provider welcoming customer inward"),
)
_HOME_TRUST = BenefitTemplate(
    benefit_subject="post-job satisfaction — completed work visible with relieved homeowner",
    people=_POST_JOB_TRUST,
    avoid=("seated patio consult", "living-room couch", "desk-side iPad", "doorway inversion"),
)


def _slot(*variants: BenefitTemplate) -> tuple[BenefitTemplate, BenefitTemplate, BenefitTemplate]:
    if len(variants) != 3:
        raise ValueError("each template set requires exactly 3 variants")
    return variants  # type: ignore[return-value]


def _infer_concrete_scene(industry: str) -> str:
    low = industry.lower()
    commercial_keys = ("commercial", "parking", "industrial", "municipal", "storefront", "warehouse")
    residential_keys = ("driveway", "patio", "walkway", "sidewalk", "residential", "home")
    if any(k in low for k in commercial_keys):
        return (
            "freshly poured or finished commercial concrete — parking lot, storefront sidewalk, "
            "or industrial pad with clean edges and professional finish"
        )
    if any(k in low for k in residential_keys):
        return (
            "new residential driveway, walkway, or patio — smooth finished concrete at home facade "
            "with visible curb appeal improvement"
        )
    return (
        "new residential driveway or walkway — smooth finished concrete at home facade "
        "with visible curb appeal improvement"
    )


_PLUMBING_INTERIOR_SETTING = (
    "interior home plumbing context — under-sink cabinet, basement utility wall, garage utility corner, "
    "or indoor water heater alcove; residential indoor only — never outdoor yard or exterior water heater"
)
_TEMPLATE_REGISTRY: list[tuple[tuple[str, ...], tuple[BenefitTemplate, BenefitTemplate, BenefitTemplate]]] = [
    # dental
    (
        ("orthodont",),
        _slot(
            BenefitTemplate(
                benefit_subject="orthodontic consult warmth — parent and teen in bright ortho office discussing aligner treatment",
                people=_DESK_BOTH_FACES,
                avoid=("residential home", "dental operatory hero", "equipment focal point"),
            ),
            BenefitTemplate(
                benefit_subject="family orthodontic warmth — mixed ages in welcoming ortho reception with subtle practice cues",
                people="gender and age diversity; candid warmth; dental/ortho office visible",
                avoid=("operatory", "dental chair hero", "residential interior"),
            ),
            BenefitTemplate(
                benefit_subject="confident smile outcome — natural post-aligner smile in soft window light",
                people="single adult or teen with genuine relaxed smile; not direct stock portrait",
                avoid=("braces close-up hero", "operatory", "forced grin at camera"),
            ),
        ),
    ),
    (
        ("dental", "dentist"),
        _slot(
            BenefitTemplate(
                benefit_subject="calm dental consult — dentist and patient in face-to-face conversation in bright clinic",
                people=_DESK_BOTH_FACES,
                avoid=("dental chair hero", "operatory", "residential home"),
            ),
            BenefitTemplate(
                benefit_subject="family dental warmth — mixed ages and genders in welcoming dental reception",
                people="gender and age diversity; candid connection; clinic environment behind",
                avoid=("all-female cast only", "operatory", "living room"),
            ),
            BenefitTemplate(
                benefit_subject="confident post-visit smile — natural relief smile after dental care",
                people="adult or family with genuine relaxed smile; not posed at lens",
                avoid=("dental chair", "instrument tray hero", "stock portrait"),
            ),
        ),
    ),
    # legal
    (
        ("personal injury", "injury law"),
        _slot(
            BenefitTemplate(
                benefit_subject="attorney and client at desk — measured personal injury case consultation",
                people=_DESK_BOTH_FACES,
                avoid=("family at doorway", "courtroom drama", "residential home"),
            ),
            BenefitTemplate(
                benefit_subject="welcoming law office threshold — professional greeting at office entry",
                people="attorney welcoming client at office door; standing, open gesture",
                avoid=("domestic doorway", "family group walking in", "clinical room"),
            ),
            BenefitTemplate(
                benefit_subject="relieved client after consult — calm confidence leaving attorney meeting",
                people="single client with eased body language; attorney optional in background",
                avoid=("courtroom", "gavel hero", "posed relief at camera"),
            ),
        ),
    ),
    (
        ("family law",),
        _slot(
            BenefitTemplate(
                benefit_subject="family law counsel at desk — compassionate one-on-one legal guidance",
                people=_DESK_BOTH_FACES,
                avoid=("courtroom", "domestic dispute imagery", "residential kitchen"),
            ),
            BenefitTemplate(
                benefit_subject="welcoming family law office entry — calm professional threshold moment",
                people="attorney greeting client at office entry; reassuring posture",
                avoid=("family group at residential door", "children as focal conflict"),
            ),
            BenefitTemplate(
                benefit_subject="client relief after family law consult — eased shoulders, hopeful expression",
                people="single adult client with natural relief; soft office light",
                avoid=("courtroom", "crying drama", "stock portrait"),
            ),
        ),
    ),
    # home_services — trade-specific v0
    (
        ("hvac", "heating", "air condition", "ac repair", "furnace"),
        _slot(
            BenefitTemplate(
                benefit_subject="home comfort restored — visible thermostat or vent with relaxed homeowner enjoying even indoor temperature",
                people=_FIELD_PROVIDER_BACK,
                avoid=("front door only", "doorway inversion", "couch leisure", "no HVAC cues"),
            ),
            _HOME_WIP,
            _HOME_TRUST,
        ),
    ),
    (
        ("plumb",),
        _slot(
            BenefitTemplate(
                benefit_subject="reliable plumbing — under-sink cabinet or water heater area showing professional repair with relieved homeowner nearby",
                people=_FIELD_PROVIDER_BACK,
                avoid=("outdoor water heater", "exterior yard", "backyard leisure", "front door only", "kitchen table consult"),
                setting=_PLUMBING_INTERIOR_SETTING,
            ),
            BenefitTemplate(
                benefit_subject="plumbing repair in progress — technician working under sink or at indoor water heater",
                people=_WIP_WORKER,
                avoid=("outdoor water heater", "exterior yard", "doorway consult", "kitchen table"),
                setting=_PLUMBING_INTERIOR_SETTING,
            ),
            BenefitTemplate(
                benefit_subject="plumbing job complete — dry pipes, tidy utility area, relieved homeowner indoors",
                people=_POST_JOB_TRUST,
                avoid=("outdoor water heater", "exterior yard", "doorway inversion"),
                setting=_PLUMBING_INTERIOR_SETTING,
            ),
        ),
    ),
    (
        ("roof",),
        _slot(
            BenefitTemplate(
                benefit_subject="roof craftsmanship pride — visible roofline with roofer on roof or ladder, quality shingles and clean lines",
                people=_FIELD_PROVIDER_BACK,
                avoid=("contractor inside homeowner outside", "interior domestic scene", "no roof visible"),
            ),
            _HOME_WIP,
            _HOME_TRUST,
        ),
    ),
    (
        ("electric", "electrical"),
        _slot(
            BenefitTemplate(
                benefit_subject="safe electrical service — panel, outlet, or fixture work visible with homeowner reassured nearby",
                people=_FIELD_PROVIDER_BACK,
                avoid=("front door only", "no electrical context", "doorway inversion", "provider inside welcoming out"),
            ),
            _HOME_WIP,
            _HOME_TRUST,
        ),
    ),
    (
        ("garage door",),
        _slot(
            BenefitTemplate(
                benefit_subject="garage door restored — home facade with half-open garage door showing smooth operation and curb appeal",
                people=_FIELD_PROVIDER_BACK,
                avoid=("kitchen table", "auto-shop interior doors", "home plans on table", "no garage visible"),
            ),
            _HOME_WIP,
            _HOME_TRUST,
        ),
    ),
    # concrete paving — dedicated (commercial/residential resolved at lookup)
    (
        ("concrete", "paving", "asphalt"),
        _slot(
            BenefitTemplate(
                benefit_subject="PLACEHOLDER_CONCRETE_V0",
                people=_FIELD_PROVIDER_BACK,
                avoid=("interior home consult", "two people at front door only", "no concrete work visible"),
            ),
            BenefitTemplate(
                benefit_subject="concrete pour or finish in progress — crew screeding or edging fresh pour",
                people=_WIP_WORKER,
                avoid=("kitchen table", "doorway consult", "interior domestic"),
            ),
            BenefitTemplate(
                benefit_subject="completed concrete surface — crisp edges, smooth finish, enhanced property entrance",
                people=_POST_JOB_TRUST,
                avoid=("interior scene", "desk consult", "unfinished muddy site"),
            ),
        ),
    ),
    # pest
    (
        ("pest", "termite", "rodent", "exterminator"),
        _slot(
            BenefitTemplate(
                benefit_subject="protected home exterior — well-maintained facade suggesting pest-free peace of mind",
                people=_ENV_OPTIONAL,
                avoid=("insects as hero", "scary infestation", "kitchen table consult"),
            ),
            BenefitTemplate(
                benefit_subject="technician treating exterior perimeter — professional pest control application",
                people=_WIP_WORKER,
                avoid=("indoor desk consult", "giant bug imagery"),
            ),
            BenefitTemplate(
                benefit_subject="secure home exterior angle — second view of protected property and tidy yard",
                people=_ENV_OPTIONAL,
                avoid=("interior domestic", "desk iPad"),
            ),
        ),
    ),
    # environment-first
    (
        ("house clean", "home clean", "maid", "janitorial"),
        _slot(
            BenefitTemplate(
                benefit_subject="stunning clean home interior — gleaming surfaces, fresh light, immaculate living space",
                people=_ENV_OPTIONAL,
                avoid=("desk consult", "iPad meeting", "two people talking at table"),
            ),
            BenefitTemplate(
                benefit_subject="cleaning in progress — professional cleaner with back to camera detailing a room",
                people=_WIP_WORKER,
                avoid=("desk side guidance", "domestic leisure on couch"),
            ),
            BenefitTemplate(
                benefit_subject="freshly detailed room — second angle showing spotless kitchen or living area",
                people=_ENV_OPTIONAL,
                avoid=("people at desk", "clipboard consult"),
            ),
        ),
    ),
    (
        ("restaurant", "cafe", "bistro", "dining"),
        _slot(
            BenefitTemplate(
                benefit_subject="inviting dining experience — warm restaurant interior with beautifully plated food as hero",
                people="family or friends enjoying a meal optional; food and venue primary",
                avoid=("desk consult", "clipboard meeting", "two people talking over table without food"),
            ),
            BenefitTemplate(
                benefit_subject="kitchen or service in progress — chef or server back to camera preparing dishes",
                people=_WIP_WORKER,
                avoid=("office desk", "iPad consult"),
            ),
            BenefitTemplate(
                benefit_subject="second dining angle — ambient lighting, table settings, appetizing spread",
                people="diners optional; atmosphere and food hero",
                avoid=("desk meeting", "empty sterile room"),
            ),
        ),
    ),
    (
        ("salon", "hair", "barber"),
        _slot(
            BenefitTemplate(
                benefit_subject="salon styling moment — mirror station, salon chair, and finished hair as hero",
                people="stylist back or profile; client face visible in mirror optional",
                avoid=("desk consult", "iPad", "office setting"),
            ),
            BenefitTemplate(
                benefit_subject="cut or color in progress — stylist working with client in salon chair",
                people="stylist back/profile; client face toward mirror",
                avoid=("desk side guidance", "domestic kitchen"),
            ),
            BenefitTemplate(
                benefit_subject="salon atmosphere — second angle of stations, warm lighting, polished finishes",
                people="anonymous salon activity optional",
                avoid=("office desk", "consultation table"),
            ),
        ),
    ),
    (
        ("pool clean", "pool service", "pool maintenance"),
        _slot(
            BenefitTemplate(
                benefit_subject="sparkling pool and backyard — crystal-clear water, clean deck, inviting outdoor oasis",
                people=_ENV_OPTIONAL,
                avoid=("iPad indoors", "desk consult", "living room"),
            ),
            BenefitTemplate(
                benefit_subject="pool maintenance in progress — technician servicing equipment or skimming pool",
                people=_WIP_WORKER,
                avoid=("indoor desk", "domestic interior"),
            ),
            BenefitTemplate(
                benefit_subject="poolside second angle — lounge area, clear water, tidy backyard",
                people=_ENV_OPTIONAL,
                avoid=("indoor scene", "tablet consult"),
            ),
        ),
    ),
    (
        ("fitness", "gym"),
        _slot(
            BenefitTemplate(
                benefit_subject="energizing gym environment — well-lit training floor with equipment and motivating atmosphere",
                people="anonymous athletes training optional; space is hero",
                avoid=("desk consult", "office setting", "domestic interior"),
            ),
            BenefitTemplate(
                benefit_subject="training in progress — coach back to camera guiding member through exercise",
                people=_WIP_WORKER,
                avoid=("seated desk consult", "living room"),
            ),
            BenefitTemplate(
                benefit_subject="second gym angle — cardio zone or free weights with active energy",
                people="anonymous activity optional",
                avoid=("office desk", "iPad meeting"),
            ),
        ),
    ),
    (
        ("wedding", "venue", "event space"),
        _slot(
            BenefitTemplate(
                benefit_subject="elegant event venue — decorated hall, floral details, warm ambient lighting ready for celebration",
                people=_ENV_OPTIONAL,
                avoid=("desk consult", "office", "domestic kitchen"),
            ),
            BenefitTemplate(
                benefit_subject="venue setup in progress — staff arranging tables or florals with backs to camera",
                people=_WIP_WORKER,
                avoid=("business desk", "clipboard consult"),
            ),
            BenefitTemplate(
                benefit_subject="second venue angle — dance floor, arch, or reception layout bathed in soft light",
                people=_ENV_OPTIONAL,
                avoid=("office meeting", "domestic scene"),
            ),
        ),
    ),
    # outdoor_services
    (
        ("tree removal", "tree service", "stump"),
        _slot(
            BenefitTemplate(
                benefit_subject="professional tree removal — crew and equipment on property with felled or pruned tree context outdoors",
                people=_FIELD_PROVIDER_BACK,
                avoid=("indoor home", "photo of tree on tablet", "kitchen table"),
            ),
            BenefitTemplate(
                benefit_subject="tree work in progress — climber or chipper active on residential lot",
                people=_WIP_WORKER,
                avoid=("indoor domestic", "desk consult"),
            ),
            BenefitTemplate(
                benefit_subject="cleared property outcome — tidy yard after tree removal with open sky",
                people=_POST_JOB_TRUST,
                avoid=("indoor scene", "iPad consult"),
            ),
        ),
    ),
    (
        ("arborist", "tree care"),
        _slot(
            BenefitTemplate(
                benefit_subject="healthy managed trees — arborist care visible with lush canopy and well-maintained property",
                people=_FIELD_PROVIDER_BACK,
                avoid=("indoor domestic", "desk consult"),
            ),
            BenefitTemplate(
                benefit_subject="arborist pruning in progress — bucket truck or climber working canopy",
                people=_WIP_WORKER,
                avoid=("kitchen table", "living room"),
            ),
            BenefitTemplate(
                benefit_subject="property tree outcome — second angle of trimmed healthy trees and clean yard",
                people=_ENV_OPTIONAL,
                avoid=("indoor scene", "office desk"),
            ),
        ),
    ),
    (
        ("fence", "fencing"),
        _slot(
            BenefitTemplate(
                benefit_subject="quality fence installation — new fence line enhancing property boundary and curb appeal",
                people=_FIELD_PROVIDER_BACK,
                avoid=("indoor domestic", "desk consult"),
            ),
            BenefitTemplate(
                benefit_subject="fence build in progress — installer setting posts or panels",
                people=_WIP_WORKER,
                avoid=("kitchen table", "office"),
            ),
            BenefitTemplate(
                benefit_subject="completed fence angle — straight lines, quality materials, tidy yard",
                people=_POST_JOB_TRUST,
                avoid=("indoor scene", "iPad meeting"),
            ),
        ),
    ),
    (
        ("landscap", "lawn", "garden"),
        _slot(
            BenefitTemplate(
                benefit_subject="beautiful landscaped property — manicured lawn, planted beds, and curb appeal outdoors",
                people=_FIELD_PROVIDER_BACK,
                avoid=("indoor kitchen", "couch leisure", "desk consult"),
            ),
            BenefitTemplate(
                benefit_subject="landscaping crew at work — mowing, planting, or mulching on property",
                people=_WIP_WORKER,
                avoid=("indoor domestic", "desk iPad"),
            ),
            BenefitTemplate(
                benefit_subject="second yard outcome angle — seasonal color, clean edges, inviting outdoor space",
                people=_ENV_OPTIONAL,
                avoid=("interior home", "office desk"),
            ),
        ),
    ),
    # healthcare — all slots trade-specific
    (
        ("physical therapy", "physio", "rehab"),
        _slot(
            BenefitTemplate(
                benefit_subject="movement restored — therapist guiding patient through exercise in bright therapy gym",
                people=_CLINICAL_ONE_ONLY,
                avoid=("both in scrubs", "gym bro aesthetic", "residential interior", "hallucinated doors"),
            ),
            BenefitTemplate(
                benefit_subject="hands-on PT session — therapist assisting stretch or mobility drill",
                people=_CLINICAL_ONE_ONLY,
                avoid=("both in medical jackets", "empty hospital hallway"),
            ),
            BenefitTemplate(
                benefit_subject="recovery progress — patient confidently performing movement with therapist observing",
                people=_CLINICAL_ONE_ONLY,
                avoid=("both clinical attire", "gym equipment hero without people"),
            ),
        ),
    ),
    (
        ("chiropract", "chiro"),
        _slot(
            BenefitTemplate(
                benefit_subject="spinal relief consult — chiropractor and patient in adjustment room discussing care plan",
                people=_CLINICAL_ONE_ONLY,
                avoid=("both in scrubs", "hospital hallway", "residential home"),
            ),
            BenefitTemplate(
                benefit_subject="adjustment in progress — chiropractor performing treatment, patient relaxed",
                people=_CLINICAL_ONE_ONLY,
                avoid=("both medical attire", "symmetric clinic corridor"),
            ),
            BenefitTemplate(
                benefit_subject="post-adjustment ease — patient standing tall with relieved posture",
                people=_CLINICAL_ONE_ONLY,
                avoid=("both in clinical uniform", "posed stock portrait"),
            ),
        ),
    ),
    (
        ("med spa", "medical spa", "aesthetic"),
        _slot(
            BenefitTemplate(
                benefit_subject="radiant med spa treatment room — calm luxury aesthetic with client at ease",
                people="provider in clinical or spa uniform; client in street clothes or robe; never both in white coats",
                avoid=("both in medical jackets", "hospital corridor", "desk iPad consult"),
            ),
            BenefitTemplate(
                benefit_subject="treatment in progress — aesthetician performing facial or skin treatment",
                people="provider back or profile; client face visible relaxed",
                avoid=("both clinical attire", "office desk"),
            ),
            BenefitTemplate(
                benefit_subject="glowing skin outcome — client with natural refreshed look in soft spa light",
                people="single client candid; provider optional background",
                avoid=("both in scrubs", "clinical hospital"),
            ),
        ),
    ),
    (
        ("veterinar", "vet clinic", "animal hospital"),
        _slot(
            BenefitTemplate(
                benefit_subject="compassionate vet visit — veterinarian examining pet with owner at side in bright clinic",
                people="vet in clinical attire; owner in street clothes; pet visible; never both owner and vet in scrubs",
                avoid=("both in medical garb", "hallucinated walls", "residential living room"),
            ),
            BenefitTemplate(
                benefit_subject="vet exam in progress — gentle handling of dog or cat on exam table",
                people="vet back or profile; owner face visible; pet calm",
                avoid=("both subjects in scrubs", "symmetric corridor"),
            ),
            BenefitTemplate(
                benefit_subject="happy healthy pet outcome — owner with pet leaving clinic at ease",
                people="owner in three-quarter profile with pet; vet back or profile; never direct stare at lens",
                avoid=("both in clinical uniform", "stock portrait"),
            ),
        ),
    ),
    # auto
    (
        ("auto repair", "mechanic", "auto shop", "car repair"),
        _slot(
            BenefitTemplate(
                benefit_subject="vehicle expertly serviced — clean shop bay with car on lift or hood open, professional maintenance visible",
                people=_WIP_WORKER,
                avoid=("desk consult", "domestic garage kitchen", "iPad meeting"),
            ),
            BenefitTemplate(
                benefit_subject="mechanic at work — under hood or wheel service in progress",
                people=_WIP_WORKER,
                avoid=("office desk", "living room"),
            ),
            BenefitTemplate(
                benefit_subject="finished repair — polished vehicle in bay ready for customer pickup",
                people="mechanic back to camera; customer face optional",
                avoid=("domestic interior", "clipboard desk"),
            ),
        ),
    ),
    # office family
    (
        ("cpa", "account", "bookkeep"),
        _slot(
            BenefitTemplate(
                benefit_subject="tax and accounting guidance — CPA and client reviewing documents at professional desk",
                people=_DESK_BOTH_FACES,
                avoid=("residential kitchen", "doorway family group"),
            ),
            BenefitTemplate(
                benefit_subject="financial planning session — spreadsheets and calculator on desk, collaborative review",
                people=_DESK_BOTH_FACES,
                avoid=("domestic scene", "outdoor threshold"),
            ),
            BenefitTemplate(
                benefit_subject="client confidence after consult — organized files and relieved expression",
                people="client face visible; CPA optional background",
                avoid=("living room", "kitchen table"),
            ),
        ),
    ),
    (
        ("insurance",),
        _slot(
            BenefitTemplate(
                benefit_subject="insurance protection consult — agent and client reviewing coverage at office desk",
                people=_DESK_BOTH_FACES,
                avoid=("residential doorway", "family group walking in"),
            ),
            BenefitTemplate(
                benefit_subject="policy review in progress — documents and laptop on desk, clear explanation moment",
                people=_DESK_BOTH_FACES,
                avoid=("domestic interior", "outdoor only"),
            ),
            BenefitTemplate(
                benefit_subject="client peace of mind — relaxed posture after insurance meeting",
                people="client with eased expression; agent optional",
                avoid=("disaster imagery hero", "stock portrait"),
            ),
        ),
    ),
    (
        ("property manag",),
        _slot(
            BenefitTemplate(
                benefit_subject="property management expertise — manager and owner reviewing building portfolio at desk",
                people=_DESK_BOTH_FACES,
                avoid=("residential couch", "domestic kitchen"),
            ),
            BenefitTemplate(
                benefit_subject="site walkthrough planning — keys and building photos on desk",
                people=_DESK_BOTH_FACES,
                avoid=("family at doorway", "living room"),
            ),
            BenefitTemplate(
                benefit_subject="well-maintained property outcome — tidy building exterior or lobby",
                people=_ENV_OPTIONAL,
                avoid=("desk-only with no property cue", "domestic kitchen"),
            ),
        ),
    ),
    (
        ("real estate", "realtor"),
        _slot(
            BenefitTemplate(
                benefit_subject="real estate guidance — agent and buyer reviewing listing materials at office desk",
                people=_DESK_BOTH_FACES,
                avoid=("residential couch leisure", "empty room hero"),
            ),
            BenefitTemplate(
                benefit_subject="home showing prep — agent with keys and listing sheet heading to property",
                people="agent back or profile; client in three-quarter or candid profile",
                avoid=("kitchen table lifestyle", "iPad only"),
            ),
            BenefitTemplate(
                benefit_subject="keys moment — happy buyers at beautiful home exterior",
                people="buyers in candid three-quarter profile at threshold; agent back or profile",
                avoid=("empty house", "stock grin portrait"),
            ),
        ),
    ),
]

# Unknown industry — door greet only (general_services fallback)
_UNKNOWN_DOOR_GREET = _slot(
    BenefitTemplate(
        benefit_subject="welcoming door greet — provider greeting customer at business entry with open gesture",
        people="provider inviting customer inward at threshold; no specific trade equipment",
        avoid=("trade-specific equipment hero", "domestic kitchen", "iPad desk consult as default"),
    ),
    BenefitTemplate(
        benefit_subject="warm service welcome — approachable provider at entry or reception",
        people="natural greeting posture; both faces acceptable at professional entry",
        avoid=("clinical operatory", "equipment focal point"),
    ),
    BenefitTemplate(
        benefit_subject="customer satisfaction — relieved client after service with provider nearby",
        people="customer face visible; provider back or profile",
        avoid=("empty room", "stock portrait at lens"),
    ),
)


def _match_template_set(
    industry: str,
) -> tuple[BenefitTemplate, BenefitTemplate, BenefitTemplate]:
    low = industry.lower()
    for keys, templates in _TEMPLATE_REGISTRY:
        if any(k in low for k in keys):
            return templates
    return _UNKNOWN_DOOR_GREET


def resolve_benefit_template(industry: str, variant_index: int) -> BenefitTemplate:
    """Resolve benefit-first subject, people, and avoid for industry string × variant 0|1|2."""
    if variant_index not in (0, 1, 2):
        raise ValueError("variant_index must be 0, 1, or 2")
    templates = _match_template_set(industry)
    template = templates[variant_index]
    if template.benefit_subject == "PLACEHOLDER_CONCRETE_V0":
        scene = _infer_concrete_scene(industry)
        return BenefitTemplate(
            benefit_subject=scene,
            people=template.people,
            avoid=template.avoid,
        )
    return template

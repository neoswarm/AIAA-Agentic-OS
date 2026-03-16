#!/usr/bin/env python3
"""
Rebuild all 20 patient-facing email sequences — correct format per user template.

Template: 3 emails per practice, patient-facing (FROM practice TO patient after assessment)
Email 1: smart_practice_value_drop — assessment review + root causes + 3-step framework + dual CTA
Email 2: mechanism_story — biological mechanism explanation + what standard care misses + CTA
Email 3: proof_and_results — anonymized patient story + results-vary disclaimer + booking CTA
"""

import json
from pathlib import Path

BASE = Path(__file__).parent.parent / "output" / "d100_runs"

# All 20 canonical run dirs with their email data
EMAILS = {

# ─────────────────────────────────────────────────────────────────────────────
"aliveandwell-health_20260224_211531": {
    "booking_url": "https://aliveandwell.health/book-a-service",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your assessment results — a few patterns jumped out, [FIRST_NAME]",
            "preview": "What your score is actually telling us",
            "body": """Hi [FIRST_NAME] — quick note from the care team at Alive and Well.

I reviewed your Custom Health Assessment, and a few patterns came up immediately:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Most common symptoms people with your pattern report: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

Here is what most people miss: you do not need more generic advice or random supplements. You need a clear, prioritized plan that matches your specific patterns — so your body can actually respond.

The 3 things that move the needle fastest for people with [CORE_ISSUE_1]:

1. Identify the trigger (so symptoms stop cycling)
2. Restore the depleted system (so energy, sleep, and mood can stabilize)
3. Measure and adjust (so you are not guessing)

We offer functional medicine at three locations — Austin, Dallas, and Boulder — and we can work with you in person or virtually.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a consultation and we will map out your top 1-2 drivers → [SCHEDULE_LINK]

You are not starting from scratch. Your assessment already gave us a head start.

— The Alive and Well Care Team
Alive and Well | Austin · Dallas · Boulder | aliveandwell.health""",
            "cta_text": "Book Your Consultation",
            "cta_url": "https://aliveandwell.health/book-a-service"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "Why your symptoms keep coming back (the part most doctors skip)",
            "preview": "A simple explanation worth 2 minutes",
            "body": """Hi [FIRST_NAME],

I want to explain something that tends to change how people see their situation.

Most conventional approaches manage symptoms — they quiet the alarm but do not find what triggered it. Think of it like pulling the battery out of a smoke detector instead of checking for smoke.

When someone has a pattern like yours — with [PRIMARY_SYMPTOM] as a central complaint — the root often sits in one of three places: a dysregulated stress-response system, a nutrient or hormone deficit that has compounded over time, or a chronic low-grade inflammatory trigger the standard panel simply does not catch.

When those drivers go unaddressed, symptoms cycle back. The patient is not failing. The approach was incomplete.

At Alive and Well, we use advanced functional testing to map the actual root drivers, not just the surface symptoms. Our goal is not to manage your pattern indefinitely — it is to resolve the underlying cause so you stop needing constant intervention.

If you would like to understand what is driving [PRIMARY_SYMPTOM] in your case specifically, we are happy to walk through the data with you.

— The Alive and Well Care Team
Alive and Well | Austin · Dallas · Boulder | aliveandwell.health

[Book a Consultation →]([SCHEDULE_LINK])""",
            "cta_text": "Book a Consultation",
            "cta_url": "https://aliveandwell.health/book-a-service"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "What changed for one patient with a similar pattern",
            "preview": "A short story worth reading",
            "body": """Hi [FIRST_NAME],

One last note — I want to share a patient story that might resonate.

A woman in her early 40s came to us after years of cycling through fatigue, weight resistance, and disrupted sleep. Her conventional labs were consistently 'normal.' She had tried multiple protocols without lasting results.

After a thorough intake and advanced functional panel, we identified two primary drivers that standard testing had not flagged. We built a targeted plan around those specific findings.

Within four months, her energy had stabilized, the weight resistance had meaningfully shifted, and she described sleeping through the night for the first time in years.

Individual results vary — every person's biology is different, and outcomes depend on many factors. What does not vary is the approach: find the actual root cause, address it precisely, measure the response.

If your assessment suggests a similar pattern, we would be glad to take a closer look.

— The Alive and Well Care Team
Alive and Well | Austin · Dallas · Boulder | aliveandwell.health

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your Consultation →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your Consultation",
            "cta_url": "https://aliveandwell.health/book-a-service"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"aliveintegrative-com_20260225_091930": {
    "booking_url": "https://aliveintegrative.com/new-patients/",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your assessment results — a few patterns stood out, [FIRST_NAME]",
            "preview": "What your score is actually telling us",
            "body": """Hi [FIRST_NAME] — quick note from Dr. Mele at Alive Integrative Medicine.

I reviewed your Custom Health Assessment, and a few patterns came up immediately:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Most common symptoms people with your pattern report: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

Here is what often gets missed: healing is not about chasing the loudest symptom. It is about understanding the full picture — your history, your biology, your context — and building a plan that fits you specifically.

The 3 things that tend to create real momentum for people with [CORE_ISSUE_1]:

1. Clarify what is actually driving it (not just what it looks like on the surface)
2. Restore the depleted system thoughtfully and at a pace your body can use
3. Adjust as you respond — because healing is not linear

Our practice in Eugene is built for people who have tried the standard approach and need something more thorough.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a new patient visit and we will work through your pattern together → [SCHEDULE_LINK]

Your assessment is already a head start.

— Dr. Brielle Mele, ND
Alive Integrative Medicine | Eugene, OR | aliveintegrative.com""",
            "cta_text": "Book Your New Patient Visit",
            "cta_url": "https://aliveintegrative.com/new-patients/"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "Why [PRIMARY_SYMPTOM] often outlasts every protocol you have tried",
            "preview": "The part of the picture most people never get",
            "body": """Hi [FIRST_NAME],

There is a pattern I see often, and I want to explain it plainly.

Standard medicine is designed to diagnose and treat conditions that show up on conventional testing. It does that well. What it is not designed for is the space between 'diagnosed' and 'thriving' — the persistent fatigue, the mood swings, the symptoms that are real but do not land cleanly on a test result.

Naturopathic and functional medicine approaches that space differently. Instead of asking 'what is your diagnosis,' we ask 'what systems are under-supported, and what does your body need to do the work of healing?'

For someone with a pattern like yours — where [PRIMARY_SYMPTOM] is a central piece — the underlying contributors often involve things like dysregulated cortisol patterns, micronutrient depletions, or immune and gut signals that have not been assessed.

When those go unaddressed, the symptom persists — not because you are not trying, but because the root cause was never part of the conversation.

At Alive Integrative, that is exactly where we start.

— Dr. Brielle Mele, ND
Alive Integrative Medicine | Eugene, OR | aliveintegrative.com

[Book a New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Book a New Patient Visit",
            "cta_url": "https://aliveintegrative.com/new-patients/"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient with a similar pattern — what shifted for them",
            "preview": "One short story worth reading",
            "body": """Hi [FIRST_NAME],

I want to share a brief story — one that echoes what I see in assessments like yours.

A patient came to our practice after several years of managing symptoms that never fully resolved. Fatigue, irregular cycles, and persistent brain fog. Conventional workups were unremarkable. She had tried elimination diets, multiple supplements, and a round of hormone therapy with limited results.

During her intake, we took a full history — not just labs, but sleep patterns, stress load, gut history, and a detailed timeline. A more comprehensive functional panel identified two specific gaps that had not been addressed.

We built a phased plan. Slow, targeted, adjusted as she responded.

Several months later, she described herself as feeling 'like herself again for the first time in years.'

Individual results vary and depend on many factors unique to each person. But the approach is consistent: understand the full picture, address the actual root, and give the body what it needs to respond.

If your assessment reflects a similar pattern, I would be glad to work through it with you.

— Dr. Brielle Mele, ND
Alive Integrative Medicine | Eugene, OR | aliveintegrative.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your New Patient Visit",
            "cta_url": "https://aliveintegrative.com/new-patients/"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"biodesignwellness-com_20260225_090325": {
    "booking_url": "https://biodesignwellness.com/new-patients/",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your BioDesign assessment — a few key patterns, [FIRST_NAME]",
            "preview": "What your results are pointing to",
            "body": """Hi [FIRST_NAME] — quick note from Jimmy Barker at BioDesign Wellness.

I looked through your Custom Health Assessment, and a few clear patterns came up:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

The part most people miss: the goal is not just to feel better — it is to perform, look, and function like a genuinely optimized version of yourself. That takes more than symptom management. It takes a precise map of what is actually holding you back.

The 3 things that typically move the needle fastest for a pattern like [CORE_ISSUE_1]:

1. Identify the metabolic or hormonal brake (the thing silently working against your efforts)
2. Restore the depleted substrate — whether hormones, nutrients, or cellular energy
3. Build and adjust — with data, not guesswork

We work at the intersection of functional medicine and performance optimization, in Tampa. In-person and virtual options available.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a new patient visit and let us build your personalized blueprint → [SCHEDULE_LINK]

— Jimmy Barker, Founder & CEO
BioDesign Wellness Center | Tampa, FL | biodesignwellness.com""",
            "cta_text": "Book Your New Patient Visit",
            "cta_url": "https://biodesignwellness.com/new-patients/"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "Why optimization stalls — the mechanism behind [PRIMARY_SYMPTOM]",
            "preview": "A simple explanation most clinics skip",
            "body": """Hi [FIRST_NAME],

Let me explain something that tends to reframe how people think about their results.

When someone is doing 'everything right' — eating well, exercising, managing stress — but still not seeing the outcomes they expect, it almost always comes down to an upstream blocker. Something at the hormonal, metabolic, or cellular level that is quietly working against progress.

Think of it like trying to drive with one foot on the brake. You can push harder on the accelerator and still not move as fast as you should.

For a pattern like yours — where [PRIMARY_SYMPTOM] is a central piece — the most common hidden blockers include suboptimal hormone levels (even within 'normal' reference ranges), mitochondrial stress, chronic inflammation markers, or a gut environment that is suppressing absorption and signaling.

Standard labs rarely catch these because they are designed to identify disease, not to map the gap between where you are and where you could be.

At BioDesign, we run the panels that actually answer that question — and then we build a plan around what we find.

— Jimmy Barker, Founder & CEO
BioDesign Wellness Center | Tampa, FL | biodesignwellness.com

[Book a New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Book a New Patient Visit",
            "cta_url": "https://biodesignwellness.com/new-patients/"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient with your pattern — what changed when we found the root",
            "preview": "Short story, worth your two minutes",
            "body": """Hi [FIRST_NAME],

One last note — a patient story that might sound familiar.

A man in his mid-40s came to us after plateauing for two years. He was active, disciplined with his diet, and had tried hormone pellets at another clinic. He felt marginally better but not where he expected to be.

After a full BioDesign intake — advanced hormone panel, metabolic markers, gut health, and a detailed lifestyle history — we identified a combination of suboptimal testosterone conversion and chronic low-grade inflammation that his previous provider had not addressed.

We adjusted his protocol precisely based on those findings. Three months in, his energy had noticeably shifted, the body composition changes he had been working toward started happening, and he described his mental clarity as 'back to baseline.'

Individual results vary — every person's biology and circumstances are different. But the principle is consistent: when you remove the actual blocker, the body can do what it is designed to do.

If your assessment points to a similar pattern, let us take a closer look.

— Jimmy Barker, Founder & CEO
BioDesign Wellness Center | Tampa, FL | biodesignwellness.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your BioDesign Visit",
            "cta_url": "https://biodesignwellness.com/new-patients/"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"concierge-healinggrove-org_20260225_091132": {
    "booking_url": "https://concierge.healinggrove.org/new-patients/",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your Healing Grove assessment — what stood out, [FIRST_NAME]",
            "preview": "A few patterns worth your attention",
            "body": """Hi [FIRST_NAME] — a brief note from Dr. Ho at Healing Grove Concierge.

I reviewed your Custom Health Assessment, and a few patterns came up immediately:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

What most care misses: health is not just physical — it is the intersection of body, soul, and cultural context. A plan that ignores who you are and how you live is a plan that rarely holds.

The 3 things that move the needle fastest for a pattern like [CORE_ISSUE_1]:

1. Understand the full picture — physical, emotional, and contextual
2. Address the root cause thoughtfully — not just the loudest symptom
3. Build a rhythm of care that fits your life — not the other way around

At Healing Grove, we offer concierge-level primary care in San Jose. You get direct access, unhurried visits, and a physician who knows you.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a new patient consultation — let us talk through your pattern → [SCHEDULE_LINK]

You have already taken the most important step by completing the assessment.

— Dr. Cheryl Ho, CEO & CMO
Healing Grove Concierge | San Jose, CA | concierge.healinggrove.org""",
            "cta_text": "Book Your Consultation",
            "cta_url": "https://concierge.healinggrove.org/new-patients/"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "Why [PRIMARY_SYMPTOM] often persists — and what actually changes things",
            "preview": "A short explanation most people find helpful",
            "body": """Hi [FIRST_NAME],

I want to share something that shifts how many of my patients think about their health.

Conventional primary care is structured around acute problems and chronic disease management. It is very good at those things. What it is less designed for is the patient who is not sick by clinical definition but is not thriving either — the persistent fatigue, the emotional weight, the sense that something is off but no test confirms it.

When I see a pattern like yours — with [PRIMARY_SYMPTOM] as a central theme — I am thinking about two layers simultaneously: the physical drivers (which are real and addressable) and the contextual factors that shape how the body responds to stress, sleep, and recovery.

Concierge medicine changes what is possible because it changes the relationship. When I have time to actually know you — your history, your pressures, your background — I can see things that a 15-minute visit simply cannot surface.

That is where care becomes genuinely effective.

— Dr. Cheryl Ho, CEO & CMO
Healing Grove Concierge | San Jose, CA | concierge.healinggrove.org

[Book a Consultation →]([SCHEDULE_LINK])""",
            "cta_text": "Book a Consultation",
            "cta_url": "https://concierge.healinggrove.org/new-patients/"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient who came in with your pattern — what shifted",
            "preview": "One story worth reading",
            "body": """Hi [FIRST_NAME],

I want to share a brief patient story before you go.

A woman in her late 50s joined our practice after years of feeling dismissed. She had fatigue, joint discomfort, and a persistent sense of emotional heaviness. Her conventional labs were 'fine.' She had been told to exercise more and stress less.

In our first extended visit, she shared context that had never come up in a clinical setting before — cultural stressors, a history of under-eating, and sleep disruption tied to a specific life period. Combined with a targeted functional panel, we identified two treatable root drivers.

Eight months into her care plan, she described her energy as 'completely different' and said she finally felt like her doctor actually knew her.

Individual results vary. Healing depends on many factors and is never guaranteed. But what I can offer is the time and attention to actually find the root — and care that sees the whole person, not just the chart.

If your pattern feels familiar, I would love to meet you.

— Dr. Cheryl Ho, CEO & CMO
Healing Grove Concierge | San Jose, CA | concierge.healinggrove.org

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your New Patient Visit",
            "cta_url": "https://concierge.healinggrove.org/new-patients/"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"enhancedwellnessliving-com_20260224_210933": {
    "booking_url": "https://enhancedwellnessliving.com/new-patients",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your assessment results — a few patterns stood out, [FIRST_NAME]",
            "preview": "What your score is pointing to",
            "body": """Hi [FIRST_NAME] — quick note from the team at Enhanced Wellness Living.

I reviewed your Custom Health Assessment, and a few patterns came up right away:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

Here is what often gets missed: 'root cause wellness' is not just a phrase. It means we do not stop at symptom relief — we work backward to find what is actually driving the pattern, so the fix is real and lasting.

The 3 things that typically create momentum for people with [CORE_ISSUE_1]:

1. Identify the underlying trigger (not just what it looks like on the surface)
2. Rebuild the depleted system — intentionally, at a pace that holds
3. Monitor and adapt — because the goal is long-term, not temporary relief

We are in Ridgeland, MS, and we work with patients in-person and virtually.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a new patient consultation and let us map out your root drivers → [SCHEDULE_LINK]

Your assessment is already a strong starting point.

— The Enhanced Wellness Living Team
Enhanced Wellness Living | Ridgeland, MS | enhancedwellnessliving.com""",
            "cta_text": "Book Your New Patient Visit",
            "cta_url": "https://enhancedwellnessliving.com/new-patients"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "Why [PRIMARY_SYMPTOM] keeps returning — and what actually breaks the cycle",
            "preview": "Worth 2 minutes of your time",
            "body": """Hi [FIRST_NAME],

Let me explain something that tends to reframe how people think about persistent symptoms.

Most people with a pattern like yours have been through the standard protocol: labs come back 'normal,' symptoms are managed with medication or general advice, and the underlying cause is never directly addressed. The result is a cycle — symptom management that requires ongoing intervention but never resolves the root.

Functional medicine works differently. Instead of asking 'what is the diagnosis,' we ask 'what is the body trying to tell us, and what systems need support to correct course?'

For a pattern like yours — where [PRIMARY_SYMPTOM] is a central complaint — the most common root drivers include chronic systemic inflammation, dysregulated cortisol, gut permeability affecting nutrient absorption, or hormonal imbalances that fall just outside the conventional 'normal' range but are still clinically meaningful.

When those are addressed precisely, symptoms often resolve — not because we managed them, but because the underlying cause was finally treated.

That is root cause wellness. That is what we do.

— The Enhanced Wellness Living Team
Enhanced Wellness Living | Ridgeland, MS | enhancedwellnessliving.com

[Book a New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Book a New Patient Visit",
            "cta_url": "https://enhancedwellnessliving.com/new-patients"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient with your pattern — what changed when the root was found",
            "preview": "A short story worth reading",
            "body": """Hi [FIRST_NAME],

One last note — a story that might feel familiar.

A woman in her late 30s came to us after years of fatigue, weight that would not move despite significant effort, and recurring episodes of brain fog. Standard workups at her previous providers had returned within normal limits. She had been told her lifestyle needed improvement.

After a thorough intake and a targeted functional panel, we identified a combination of a sluggish thyroid that fell within standard range but was symptomatic, significant gut dysbiosis, and a micronutrient deficiency pattern that had been compounding for years.

We built a phased plan — not a protocol, but a personalized roadmap — and adjusted it as she responded.

Six months in, her energy had stabilized, she had lost weight without a restrictive approach, and she described her mental clarity as 'better than it has been in years.'

Individual results vary. Outcomes depend on many personal factors. But the principle holds: when you find and address the actual root, the body has a remarkable capacity to respond.

If your assessment reflects a similar pattern, we would love to work with you.

— The Enhanced Wellness Living Team
Enhanced Wellness Living | Ridgeland, MS | enhancedwellnessliving.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your New Patient Visit",
            "cta_url": "https://enhancedwellnessliving.com/new-patients"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"forumhealth-com_20260223_205549": {
    "booking_url": "https://forumhealth.com/appointment",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your Forum Health assessment results — [FIRST_NAME], a few things stood out",
            "preview": "What your pattern is pointing to",
            "body": """Hi [FIRST_NAME] — quick note from the care team at Forum Health Madison.

I reviewed your Custom Health Assessment, and a few patterns came up immediately:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

What most people miss: effective health care is not about managing symptoms until the next problem surfaces. It is about understanding your specific biology, identifying what is driving your pattern, and building a plan that is actually designed for you.

The 3 things that create real momentum for people with [CORE_ISSUE_1]:

1. Identify the actual driver (not just the symptom it produces)
2. Restore what the body is depleted of — hormones, nutrients, or cellular function
3. Measure the response and adjust — until the body can hold the improvement on its own

Forum Health Madison offers personalized, integrative care with real expertise across hormone health, weight optimization, and chronic condition management.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a consultation — we will review your assessment and map a plan → [SCHEDULE_LINK]

— The Forum Health Madison Care Team
Forum Health Madison | Madison, WI | forumhealth.com""",
            "cta_text": "Book Your Consultation",
            "cta_url": "https://forumhealth.com/appointment"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "Why [PRIMARY_SYMPTOM] often resists standard treatment — explained simply",
            "preview": "The part of the picture most clinics miss",
            "body": """Hi [FIRST_NAME],

I want to share something that changes how most people think about their health pattern.

Standard medicine divides the body into systems and treats them independently. What integrative and functional medicine recognizes is that symptoms often emerge at the intersection of multiple systems — and treating just one while ignoring the others produces incomplete results.

For someone with a pattern like yours — where [PRIMARY_SYMPTOM] is a central complaint — the downstream effects usually trace back to one or more of the following: hormonal imbalance, metabolic dysfunction, chronic systemic inflammation, or gut health disruption affecting how nutrients are absorbed and how signals are sent throughout the body.

These do not typically show up on a standard panel. They require a different kind of assessment — and a willingness to look at the full picture.

At Forum Health Madison, we run a thorough intake and a functional panel designed to surface what standard testing misses. Then we build a plan that treats the actual source.

That is how symptoms resolve — not just quiet down temporarily.

— The Forum Health Madison Care Team
Forum Health Madison | Madison, WI | forumhealth.com

[Book a Consultation →]([SCHEDULE_LINK])""",
            "cta_text": "Book a Consultation",
            "cta_url": "https://forumhealth.com/appointment"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "What changed for a patient with your pattern",
            "preview": "One story worth your 2 minutes",
            "body": """Hi [FIRST_NAME],

One final note — a patient story that might resonate.

A woman in her mid-40s came to us after struggling with weight that was resistant to diet and exercise, persistent fatigue, and low mood that had been attributed to 'stress.' She had tried multiple programs and had been on thyroid medication with partial results.

After a full Forum Health intake — which included hormone panel, metabolic testing, and gut health markers — we identified a pattern of suboptimal hormone conversion and chronic low-grade inflammation that had been unaddressed.

We built a personalized care plan around those specific findings and adjusted it over three months as she responded.

Her energy normalized. The weight resistance shifted. She described her overall sense of wellbeing as 'completely different' from when she first came in.

Individual results vary and depend on many personal and health factors. But the consistent principle is: when the actual root driver is identified and addressed precisely, the body responds.

If your assessment suggests a similar pattern, we would be glad to take a closer look with you.

— The Forum Health Madison Care Team
Forum Health Madison | Madison, WI | forumhealth.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your Appointment →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your Appointment",
            "cta_url": "https://forumhealth.com/appointment"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"functionalmedicineflorida-com_20260226_120218": {
    "booking_url": "https://functionalmedicineflorida.com/new-patients/",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your assessment results — Dr. Harvey noticed a few clear patterns, [FIRST_NAME]",
            "preview": "What the data is actually pointing to",
            "body": """Hi [FIRST_NAME] — quick note from Dr. Harvey at Functional Medicine Florida.

I reviewed your Custom Health Assessment, and a few patterns came up right away:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

Here is what 4x board certification has taught me: the most important thing is not the diagnosis — it is the root cause behind it. Most chronic symptoms have an upstream driver that standard care never identifies because the system is not designed to look for it.

The 3 things that create the most durable improvement for people with [CORE_ISSUE_1]:

1. Identify the upstream trigger — not just the presenting symptom
2. Restore the depleted system using targeted, evidence-based interventions
3. Measure and adapt — outcomes should be tracked, not assumed

I practice internal medicine, geriatrics, functional medicine, and holistic-integrative medicine in Sarasota. In-person and virtual options available.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a new patient consultation and let us work through your pattern together → [SCHEDULE_LINK]

— Dr. Fred Harvey, MD
Functional Medicine Florida | Sarasota, FL | functionalmedicineflorida.com""",
            "cta_text": "Book Your New Patient Consultation",
            "cta_url": "https://functionalmedicineflorida.com/new-patients/"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "The upstream cause of [PRIMARY_SYMPTOM] — what standard medicine typically misses",
            "preview": "A plain explanation worth 2 minutes",
            "body": """Hi [FIRST_NAME],

As a physician trained in both conventional internal medicine and functional medicine, I want to explain something that changed how I practice.

Conventional medicine excels at diagnosing and managing established conditions. What it is not structured to do is identify the pre-disease dysregulation — the period where the body is clearly struggling but has not yet crossed a diagnostic threshold.

This is where most patients with patterns like yours fall. Labs are 'normal.' Symptoms are real. The explanation they receive is often inadequate.

In functional medicine, we look at the same body differently. For a pattern like yours — where [PRIMARY_SYMPTOM] is central — we are asking: what is the inflammatory burden? What is cortisol doing over the course of a day? Is gut permeability affecting systemic signaling? Are there nutritional depletions that have compounded over time?

These questions require different testing and a different kind of intake. But they produce answers — and answers produce targeted, effective plans.

That is the medicine I practice in Sarasota. Not guesswork. Not protocols. A precise map of your biology and a plan built around what it actually needs.

— Dr. Fred Harvey, MD
Functional Medicine Florida | Sarasota, FL | functionalmedicineflorida.com

[Book a New Patient Consultation →]([SCHEDULE_LINK])""",
            "cta_text": "Book a New Patient Consultation",
            "cta_url": "https://functionalmedicineflorida.com/new-patients/"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient with your pattern — what changed when we found the root",
            "preview": "Short. Worth reading.",
            "body": """Hi [FIRST_NAME],

One last note before I close the loop on your assessment.

A man in his early 60s came to see me after years of fatigue, cognitive slowing, and joint inflammation that had been attributed to 'aging.' He had been managed with multiple medications but felt that his quality of life was steadily declining.

His conventional workup was within normal limits for someone his age. My functional panel told a different story — chronic systemic inflammation, significant mitochondrial stress markers, and a hormonal pattern that was below the optimal range even if technically 'normal.'

We built a phased, individualized plan. Targeted supplementation. Dietary adjustments based on his specific profile. A carefully titrated hormone optimization protocol.

Eighteen months later, he described his energy and cognitive clarity as significantly improved and had been able to reduce one of his medications under his PCP's supervision.

Individual results vary. Every patient's biology and history are different. But the principle that holds across thousands of patients is: find the actual root, address it precisely, and give the body the conditions it needs to heal.

Your assessment gave us a starting map. Let us put it to use.

— Dr. Fred Harvey, MD
Functional Medicine Florida | Sarasota, FL | functionalmedicineflorida.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your New Patient Visit",
            "cta_url": "https://functionalmedicineflorida.com/new-patients/"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"inhealthrva-com_20260225_091544": {
    "booking_url": "https://inhealthrva.com/new-patients/",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your InHealthRVA assessment — a few patterns to walk through, [FIRST_NAME]",
            "preview": "What your results are pointing to",
            "body": """Hi [FIRST_NAME] — quick note from Tressa at InHealthRVA.

I reviewed your Custom Health Assessment, and a few patterns stood out immediately:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

Here is what most people with this pattern have in common: the root cause was never part of the conversation. Standard care addressed what showed up on the surface — and the underlying drivers kept going unaddressed.

The 3 things that tend to create the clearest shift for people with [CORE_ISSUE_1]:

1. Identify the systemic driver — not just the symptom it produces
2. Address the nervous system and body together — because they are not separate problems
3. Build a plan with real markers — so you know if it is working, not just feel like it might be

At InHealthRVA, we combine functional medicine and acupuncture because the most effective care addresses both the structural and the systemic. We are in Richmond, VA.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a new patient visit and let us work through your specific pattern → [SCHEDULE_LINK]

— Tressa Breindel, LAc, MSOM
InHealthRVA | Richmond, VA | inhealthrva.com""",
            "cta_text": "Book Your New Patient Visit",
            "cta_url": "https://inhealthrva.com/new-patients/"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "Why [PRIMARY_SYMPTOM] often outlasts treatment — explained plainly",
            "preview": "The part most clinics never explain",
            "body": """Hi [FIRST_NAME],

I want to explain something that I find changes how people relate to their symptoms.

Functional medicine and acupuncture start from the same fundamental premise: the body is a system, and symptoms are messages — not malfunctions to be suppressed.

When someone has a persistent pattern like yours — where [PRIMARY_SYMPTOM] keeps returning despite treatment — the question is not 'what medication addresses this symptom' but 'what is this symptom trying to tell the system?'

In practice, that often means looking at nervous system dysregulation (the body stuck in a chronic stress state it cannot exit), inflammatory signaling that has become its own driver, or depletion patterns in key nutrients that affect how the nervous system and hormonal system communicate.

Acupuncture addresses the nervous system directly — via the body's own signaling pathways — while functional medicine addresses the biochemical and nutritional root. Used together, they reach what neither alone can fully address.

That is how we work at InHealthRVA. And it is why the results tend to be more durable.

— Tressa Breindel, LAc, MSOM
InHealthRVA | Richmond, VA | inhealthrva.com

[Book a New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Book a New Patient Visit",
            "cta_url": "https://inhealthrva.com/new-patients/"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient with a similar pattern — what shifted",
            "preview": "One short story worth reading",
            "body": """Hi [FIRST_NAME],

A brief story that might resonate before I close the loop on your assessment.

A woman in her early 50s came to us after years of chronic pain, fatigue, and anxiety that had never fully responded to treatment. She had tried physical therapy, medication, and general wellness programs with limited lasting results.

After a comprehensive intake — which included a functional panel and a detailed history — we identified a pattern of chronic systemic inflammation layered on top of a nervous system that had been stuck in a high-alert state for years. Standard testing had not captured either driver clearly.

We built a combined plan: targeted functional medicine interventions alongside a series of acupuncture treatments designed to regulate the nervous system response.

Three months in, her pain levels had significantly reduced, her sleep had stabilized, and she described her anxiety as 'manageable for the first time.'

Individual results vary. Every patient is different, and outcomes are not guaranteed. What I can offer is a thorough assessment and a plan built around what your specific system actually needs.

If your assessment reflects a similar pattern, I would be glad to talk with you.

— Tressa Breindel, LAc, MSOM
InHealthRVA | Richmond, VA | inhealthrva.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your New Patient Visit",
            "cta_url": "https://inhealthrva.com/new-patients/"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"integrativemediowa-com_20260224_205735": {
    "booking_url": "https://integrativemediowa.com/book-appointment",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your IFM Iowa assessment — a few patterns to walk through, [FIRST_NAME]",
            "preview": "What your results are pointing to",
            "body": """Hi [FIRST_NAME] — quick note from Dr. Fitch at Integrative Family Medicine of Iowa.

I reviewed your Custom Health Assessment, and a few patterns came up right away:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

Here is what most people with this pattern have not been told: the body, the brain, and the soul are not separate problems. They influence each other constantly — and treating one while ignoring the others produces incomplete results.

The 3 things that tend to create the most meaningful shift for people with [CORE_ISSUE_1]:

1. Identify the root driver — physical, neurological, or both
2. Build a plan that addresses the interconnection, not just the presenting symptom
3. Measure and adjust — with real markers and real honesty about progress

We practice integrative family medicine and psychiatry in West Des Moines. In-person and telehealth available.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book an appointment and let us work through your specific pattern → [SCHEDULE_LINK]

— Dr. Danielle Fitch, DNP, PMHNP-BC
Integrative Family Medicine of Iowa | West Des Moines, IA | integrativemediowa.com""",
            "cta_text": "Book Your Appointment",
            "cta_url": "https://integrativemediowa.com/book-appointment"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "Why body and brain symptoms often share the same root",
            "preview": "A plain explanation worth your 2 minutes",
            "body": """Hi [FIRST_NAME],

Something I want to explain that tends to reframe how patients think about their experience.

The conventional medical system separates mind and body into different specialties — primary care for the physical, psychiatry for the mental. In reality, they share the same neurotransmitters, the same hormones, and the same inflammatory pathways.

When someone has a pattern like yours — with [PRIMARY_SYMPTOM] as a central complaint — the root cause often lives at that intersection. Chronic stress dysregulates cortisol, which disrupts sleep, which affects neurotransmitter production, which drives both physical symptoms and mood instability. The cycle reinforces itself.

Standard care typically addresses one end of the loop. Integrative medicine looks at the whole loop.

As a psychiatric nurse practitioner with training in functional medicine, I am able to see both sides of that picture simultaneously — the neurological and the systemic — and build a plan that addresses the actual driver, not just the presenting symptom.

That is what we do at Integrative Family Medicine of Iowa.

— Dr. Danielle Fitch, DNP, PMHNP-BC
Integrative Family Medicine of Iowa | West Des Moines, IA | integrativemediowa.com

[Book Your Appointment →]([SCHEDULE_LINK])""",
            "cta_text": "Book Your Appointment",
            "cta_url": "https://integrativemediowa.com/book-appointment"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient with your pattern — what changed when we treated the whole picture",
            "preview": "Short. Worth your time.",
            "body": """Hi [FIRST_NAME],

A patient story before I close the loop on your assessment.

A woman in her late 30s came to us after years of anxiety, fatigue, and concentration difficulties. She had tried antidepressants with limited effect and had been told her thyroid labs were 'within range.' She felt dismissed.

After a thorough integrative intake — including functional labs, a detailed psychiatric and medical history, and a lifestyle assessment — we identified a pattern of HPA axis dysregulation, a borderline thyroid that was symptomatic even at 'normal' levels, and a significant gut microbiome disruption affecting neurotransmitter production.

We built a phased plan that addressed all three. A targeted nutritional protocol. Careful medication adjustment. Lifestyle and nervous system regulation practices.

Six months later, she described her mood as 'stable for the first time in years' and her energy as consistently functional.

Individual results vary. Outcomes depend on many personal factors and are never guaranteed. But the pattern is consistent: when the body and brain are treated as connected, the results are more complete.

If your assessment reflects a similar picture, I would be glad to work with you.

— Dr. Danielle Fitch, DNP, PMHNP-BC
Integrative Family Medicine of Iowa | West Des Moines, IA | integrativemediowa.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your Appointment →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your Appointment",
            "cta_url": "https://integrativemediowa.com/book-appointment"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"integrativemediowa-com_20260224_210520": {
    "booking_url": "https://integrativemediowa.com",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your assessment results — Dr. Fitch noticed a few things, [FIRST_NAME]",
            "preview": "What your pattern is pointing to",
            "body": """Hi [FIRST_NAME] — quick note from Dr. Fitch at Integrative Family Medicine of Iowa.

I reviewed your Custom Health Assessment, and a few patterns stood out:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

What tends to get missed in conventional care: body and brain symptoms are rarely unrelated. When the system is under sustained stress — physical, neurological, or both — symptoms appear across multiple domains simultaneously.

The 3 things that typically create the most lasting improvement for people with [CORE_ISSUE_1]:

1. Identify whether the driver is primarily neurological, systemic, or both
2. Address the root — not just the most visible symptom — with targeted, evidence-based care
3. Build in measurement — so progress is visible and the plan can be adjusted precisely

We offer integrative family medicine and psychiatric care in West Des Moines, with telehealth options.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book an appointment and let us work through your pattern directly → [SCHEDULE_LINK]

— Dr. Danielle Fitch, DNP, PMHNP-BC
Integrative Family Medicine of Iowa | West Des Moines, IA | integrativemediowa.com""",
            "cta_text": "Book Your Appointment",
            "cta_url": "https://integrativemediowa.com"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "The connection between [PRIMARY_SYMPTOM] and the brain — explained simply",
            "preview": "Most patients find this genuinely helpful",
            "body": """Hi [FIRST_NAME],

I want to share something that is often the missing piece for patients with your pattern.

Most people think of physical symptoms and mental health symptoms as separate categories. Neurologically and biochemically, they share far more than they differ. The same cortisol dysregulation that drives fatigue and inflammation also disrupts sleep architecture and serotonin production. The same gut environment that affects nutrient absorption also produces a significant portion of the body's neurotransmitters.

This is why treating only one system often produces partial results. The improvement is real but incomplete — because the other half of the loop is still running.

For someone with a pattern like yours — where [PRIMARY_SYMPTOM] is a central complaint — the approach that produces the most complete results addresses the biochemical and the neurological simultaneously: targeted testing, a plan that reaches both systems, and real tracking so we can see what is shifting.

That is the care we provide at Integrative Family Medicine of Iowa.

— Dr. Danielle Fitch, DNP, PMHNP-BC
Integrative Family Medicine of Iowa | West Des Moines, IA | integrativemediowa.com

[Book Your Appointment →]([SCHEDULE_LINK])""",
            "cta_text": "Book Your Appointment",
            "cta_url": "https://integrativemediowa.com"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "What changed for a patient who scored like you did",
            "preview": "One short story before I close the loop",
            "body": """Hi [FIRST_NAME],

One final note before I close the loop on your assessment.

A man in his early 40s came to our practice after years of chronic fatigue, attention difficulties, and low mood that had not responded meaningfully to medication. He had been treated psychiatrically but felt the physical piece had never been addressed.

After a full integrative intake — combining a psychiatric evaluation with a functional medicine panel — we identified HPA dysregulation, a significant gut microbiome imbalance affecting neurotransmitter production, and a hormonal pattern that was below optimal range.

We built a care plan that addressed all three layers, adjusted it over three months as we tracked his response, and managed both the functional medicine and psychiatric components from a single integrated perspective.

Four months in, his attention and energy had improved significantly, and his mood had stabilized in a way he described as 'different from how any medication has made me feel.'

Individual results vary. Outcomes depend on many personal and health factors. But the consistent principle: addressing the root across all contributing systems produces more complete results than treating one in isolation.

Your assessment is a strong starting point. Let us use it.

— Dr. Danielle Fitch, DNP, PMHNP-BC
Integrative Family Medicine of Iowa | West Des Moines, IA | integrativemediowa.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your Appointment →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your Appointment",
            "cta_url": "https://integrativemediowa.com"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"maxwellclinic-com_20260226_115032": {
    "booking_url": "https://maxwellclinic.com/new-patients/",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your MaxWell assessment results — Dr. Haase noticed a few patterns, [FIRST_NAME]",
            "preview": "What the data is pointing to",
            "body": """Hi [FIRST_NAME] — quick note from Dr. Haase at MaxWell Clinic.

I reviewed your Custom Health Assessment, and a few patterns stood out immediately:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

Here is what progressive functional medicine has taught me: the body is a complex adaptive system. When it is struggling, it is almost never one thing — it is a cascade. And the most important move is to find the earliest point in that cascade where an intervention actually changes the downstream pattern.

The 3 things that create the most durable improvement for people with [CORE_ISSUE_1]:

1. Map the cascade — not just the final symptom
2. Intervene at the root, with precision — not at the level where symptoms appear
3. Restore the system's ability to self-regulate — the goal is not lifelong dependency on treatment

We practice advanced functional and integrative medicine in Nashville and Brentwood, TN.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a new patient consultation — let us build your personalized MaxWell Blueprint → [SCHEDULE_LINK]

— Dr. David Haase, MD
MaxWell Clinic | Nashville & Brentwood, TN | maxwellclinic.com""",
            "cta_text": "Book Your MaxWell Consultation",
            "cta_url": "https://maxwellclinic.com/new-patients/"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "The cascade behind [PRIMARY_SYMPTOM] — and where to intervene",
            "preview": "A useful framework for understanding your pattern",
            "body": """Hi [FIRST_NAME],

I want to share a framework that I find genuinely changes how patients think about chronic symptoms.

The body does not just malfunction in isolation. What appears as [PRIMARY_SYMPTOM] is almost always the downstream result of a cascade — a series of connected disruptions that began upstream, often years before the symptom became the main complaint.

Common cascade patterns for your type of presentation include: a sustained cortisol disruption that progressively impairs sleep quality, which over time reduces cellular repair, which affects energy production, which shows up as fatigue and cognitive difficulty. Each step reinforces the next. Standard care often steps in at the bottom of the cascade — at the level of the final symptom — without addressing the upstream driver.

At MaxWell Clinic, we begin by mapping the full cascade. Advanced functional testing, a detailed history, and a framework that looks at how your specific systems are interacting. Then we identify the highest-leverage intervention point — the place where a precise action creates the most downstream improvement.

That is progressive functional medicine. That is what we do.

— Dr. David Haase, MD
MaxWell Clinic | Nashville & Brentwood, TN | maxwellclinic.com

[Book Your MaxWell Consultation →]([SCHEDULE_LINK])""",
            "cta_text": "Book Your MaxWell Consultation",
            "cta_url": "https://maxwellclinic.com/new-patients/"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient who came in with your pattern — what shifted at MaxWell",
            "preview": "Short story, specific results",
            "body": """Hi [FIRST_NAME],

One last note — a patient story that often resonates with people who complete assessments like yours.

A man in his late 50s came to MaxWell Clinic after years of progressive cognitive slowing, significant fatigue, and what he described as a steady loss of the vitality he had assumed was 'just aging.' He had been cleared by multiple conventional specialists.

After a comprehensive MaxWell intake — advanced neurocognitive markers, full metabolic panel, mitochondrial function testing, and a detailed history — we identified three specific, addressable root drivers that had been progressing undetected.

We built a personalized MaxWell Blueprint around those findings. A targeted protocol, adjusted over four months as we tracked his response.

He described the improvement as 'the most significant shift in my health in a decade.' His energy and mental clarity had returned to a level he thought was behind him.

Individual results vary. Outcomes depend on many personal and health factors and are never guaranteed. But the principle holds across our patient population: map the cascade, intervene at the root, restore the system's capacity to heal.

Your assessment is the starting point. Let us put it to work.

— Dr. David Haase, MD
MaxWell Clinic | Nashville & Brentwood, TN | maxwellclinic.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your MaxWell Consultation →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your MaxWell Consultation",
            "cta_url": "https://maxwellclinic.com/new-patients/"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"philly-im-com_20260225_090728": {
    "booking_url": "https://philly-im.com/new-patients/",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your Philadelphia IM assessment — Dr. Tetlow noticed a few patterns, [FIRST_NAME]",
            "preview": "What your results are actually saying",
            "body": """Hi [FIRST_NAME] — quick note from Dr. Tetlow at Philadelphia Integrative Medicine.

I reviewed your Custom Health Assessment, and a few patterns came up right away:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

What most care misses: answers are possible. The reason you have not had them yet is almost always because the question was never asked at the right level. Root-cause medicine means we do not accept 'normal labs, unexplained symptoms' as a conclusion. We treat it as an incomplete workup.

The 3 things that create the most meaningful improvement for people with [CORE_ISSUE_1]:

1. Identify the root — what is driving the pattern, not just producing the symptom
2. Address it with compassion and precision — restoring what the body needs to correct course
3. Track the response and adjust — until the body holds the improvement without ongoing intervention

We practice in Wayne, PA, serving the greater Philadelphia area, with in-person and telehealth options.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a new patient visit — real answers start with a real intake → [SCHEDULE_LINK]

— Dr. Georgia Tetlow, MD ABOIM ABPMR IFMCP
Philadelphia Integrative Medicine | Wayne, PA | philly-im.com""",
            "cta_text": "Book Your New Patient Visit",
            "cta_url": "https://philly-im.com/new-patients/"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "Why [PRIMARY_SYMPTOM] often resists treatment — the mechanism explained",
            "preview": "What standard care usually misses",
            "body": """Hi [FIRST_NAME],

I want to explain something about persistent symptoms that I find most patients have never been told.

The body has a remarkable capacity for healing — but that capacity depends on inputs the body is not getting, or on systemic disruptions that have not been identified and cleared. When neither has been addressed, symptoms persist regardless of how hard the patient is working to improve.

For a pattern like yours — with [PRIMARY_SYMPTOM] as a central complaint — the mechanism usually involves one or more of the following: a chronic inflammatory burden that has become its own driver, hormonal or neurotransmitter dysregulation that compounds over time, or a nutrient depletion pattern that affects multiple systems simultaneously.

These do not produce dramatic symptoms that trigger diagnostic thresholds. They produce a persistent, pervasive feeling that something is off — but nothing 'shows' on a standard panel.

Integrative and functional medicine is designed to find those drivers. I trained in both physical medicine and functional medicine precisely because the most effective care addresses the whole person — not just the most testable piece.

That is what we offer at Philadelphia Integrative Medicine.

— Dr. Georgia Tetlow, MD ABOIM ABPMR IFMCP
Philadelphia Integrative Medicine | Wayne, PA | philly-im.com

[Book a New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Book a New Patient Visit",
            "cta_url": "https://philly-im.com/new-patients/"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient with your pattern — what changed when we asked the right questions",
            "preview": "One short story worth reading",
            "body": """Hi [FIRST_NAME],

A brief patient story before I close the loop on your assessment.

A woman in her mid-40s came to our practice after years of musculoskeletal pain, persistent fatigue, and what she described as 'losing herself' — her energy, her focus, her sense of ease in her own body. Conventional workups had found nothing actionable.

After a full integrative intake — combining my rehabilitation medicine background with a functional panel — we identified a pattern of autoimmune activity at a subclinical level, a significant inflammatory burden, and a hormonal environment that was technically 'normal' but clearly not optimal for her.

We built a personalized care plan: targeted anti-inflammatory protocols, hormonal support, and a structured rehabilitation approach that addressed how the body was holding stress physically.

Eight months in, she described her pain as 'manageable for the first time in years' and said she felt like she had 'gotten her life back.'

Individual results vary. Outcomes depend on many personal factors and are not guaranteed. But the consistent thread across patients with patterns like yours is this: real answers exist when the right questions are asked.

Let us ask them.

— Dr. Georgia Tetlow, MD ABOIM ABPMR IFMCP
Philadelphia Integrative Medicine | Wayne, PA | philly-im.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your New Patient Visit",
            "cta_url": "https://philly-im.com/new-patients/"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"rebelmednw-com_20260224_211321": {
    "booking_url": "https://rebelmednw.com/contact",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your Rebel Med assessment — a few patterns stood out, [FIRST_NAME]",
            "preview": "What your results are pointing to",
            "body": """Hi [FIRST_NAME] — quick note from Dr. Simon at Rebel Med NW.

I reviewed your Custom Health Assessment, and a few patterns came up right away:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

Here is what our approach is built around: integrative and naturopathic medicine works because it treats the person, not the diagnosis. The same symptom pattern can have very different roots in different people — which is why a personalized, thorough intake changes outcomes in a way that protocol-based care cannot.

The 3 things that tend to create the clearest shift for people with [CORE_ISSUE_1]:

1. Identify what is actually driving it — physical, structural, or systemic
2. Address the root with a combination of approaches that reaches what one modality alone cannot
3. Build a plan with real markers — so progress is visible, not just assumed

We are a voted top naturopathic and acupuncture clinic in Seattle, in Ballard.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a new patient visit and let us work through your specific pattern → [SCHEDULE_LINK]

— Dr. Andrew Simon & Dr. Phonexay Lala Simon
Rebel Med NW | Ballard, Seattle | rebelmednw.com""",
            "cta_text": "Book Your New Patient Visit",
            "cta_url": "https://rebelmednw.com/contact"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "Why [PRIMARY_SYMPTOM] often outlasts treatment — the naturopathic view",
            "preview": "A useful explanation most clinics skip",
            "body": """Hi [FIRST_NAME],

I want to explain something about the pattern in your assessment that most clinical approaches never address directly.

Naturopathic and integrative medicine starts from a different premise than conventional care: the body has an inherent capacity to heal, and the clinician's job is to identify what is getting in the way of that capacity — not just to manage the symptoms that result from it.

For a pattern like yours — where [PRIMARY_SYMPTOM] is the central complaint — the underlying obstruction is usually one or more of the following: a chronic systemic inflammatory state, a nervous system that has been stuck in high-alert mode for an extended period, nutritional depletions that affect multiple systems simultaneously, or a gut environment that is disrupting both immune signaling and nutrient absorption.

Acupuncture is uniquely effective at resetting nervous system dysregulation — something pharmaceuticals cannot fully replicate. Naturopathic medicine addresses the biochemical and lifestyle root. Together, they reach the full picture.

We have been doing this in Ballard for years, and the results are durable — because the approach goes to the source.

— Dr. Andrew Simon & Dr. Phonexay Lala Simon
Rebel Med NW | Ballard, Seattle | rebelmednw.com

[Book a New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Book a New Patient Visit",
            "cta_url": "https://rebelmednw.com/contact"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient with your pattern — what changed at Rebel Med",
            "preview": "Short story. Worth reading.",
            "body": """Hi [FIRST_NAME],

One last note before I close the loop.

A woman in her late 40s came to us after years of chronic fatigue, digestive disruption, and recurring anxiety. She had tried conventional care, a course of antidepressants, and multiple supplements she had researched on her own. Nothing had produced lasting relief.

After a thorough naturopathic intake — detailed history, functional testing, acupuncture assessment — we identified a pattern of gut dysbiosis affecting both immune signaling and mood regulation, layered on top of a nervous system that had never fully recovered from a high-stress period several years prior.

We built a combined plan: a targeted gut restoration protocol, a course of acupuncture focused on nervous system regulation, and specific nutritional interventions based on her panel.

Three months in, her energy had stabilized, her anxiety was significantly reduced, and the digestive symptoms that had been her constant companion had largely resolved.

Individual results vary. Outcomes depend on personal history and many other factors. But the pattern holds: when you reach the actual root — and address it with approaches that work at the level where it lives — the body responds.

Your assessment is the starting point. We would love to work with you.

— Dr. Andrew Simon & Dr. Phonexay Lala Simon
Rebel Med NW | Ballard, Seattle | rebelmednw.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your New Patient Visit",
            "cta_url": "https://rebelmednw.com/contact"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"richmondfunctionalmedicine-com_20260225_085923": {
    "booking_url": "https://richmondfunctionalmedicine.com/new-patients/",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your RIFM assessment results — Dr. Hartman noticed a few patterns, [FIRST_NAME]",
            "preview": "What your score is actually saying",
            "body": """Hi [FIRST_NAME] — quick note from Dr. Hartman at Richmond Integrative & Functional Medicine.

I reviewed your Custom Health Assessment, and a few patterns stood out right away:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

Here is what drives everything we do at RIFM: you were made for health. Not just the absence of disease — but genuine, functional vitality. When the body is falling short of that, there is a reason. And the reason is almost always findable.

The 3 things that move the needle most for people with [CORE_ISSUE_1]:

1. Find the root — not just the symptom it produces
2. Address it with precision — using an evidence-based, integrative approach
3. Track the restoration — so you know the change is real, not just felt

We are in Richmond, VA, with both in-person and virtual options.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a new patient visit and let us find your root cause together → [SCHEDULE_LINK]

— Dr. Aaron Hartman, MD
Richmond Integrative & Functional Medicine | Richmond, VA | richmondfunctionalmedicine.com""",
            "cta_text": "Book Your New Patient Visit",
            "cta_url": "https://richmondfunctionalmedicine.com/new-patients/"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "Why [PRIMARY_SYMPTOM] does not mean you are broken — it means something upstream needs attention",
            "preview": "A reassuring and useful explanation",
            "body": """Hi [FIRST_NAME],

Something I tell patients often, and mean: symptoms are not a sign that something is fundamentally wrong with you. They are a sign that the body is responding to something it has not been able to resolve on its own.

For a pattern like yours — where [PRIMARY_SYMPTOM] is a central piece — the upstream driver typically involves one or more of the following: a chronic inflammatory load that has gradually exceeded the body's clearing capacity, hormonal or metabolic dysregulation that compounds quietly over time, or a gut environment that is disrupting systemic signaling in ways that show up far from the digestive system.

Standard medicine looks at these things in isolation and within narrow reference ranges. Functional medicine asks: even within the 'normal' range, is this where YOUR body operates optimally? The answer is often no — and that gap is clinically meaningful.

You were made for health. When the body is not expressing it, the question is: what is in the way? That is the question we answer at Richmond Integrative & Functional Medicine.

— Dr. Aaron Hartman, MD
Richmond Integrative & Functional Medicine | Richmond, VA | richmondfunctionalmedicine.com

[Book a New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Book a New Patient Visit",
            "cta_url": "https://richmondfunctionalmedicine.com/new-patients/"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient who was told 'nothing is wrong' — what we found and what changed",
            "preview": "One short story worth reading",
            "body": """Hi [FIRST_NAME],

A brief story that I share often because it echoes what I hear from patients with your pattern.

A woman in her early 50s came to our practice after being told by multiple providers that her labs were normal and her symptoms were 'stress-related.' She had fatigue, joint pain, and a level of brain fog that had significantly affected her ability to work.

After a thorough integrative intake — comprehensive inflammatory markers, hormone panel, gut health assessment, and a detailed personal history — we identified a subclinical autoimmune pattern, a significant gut permeability issue, and a hormonal environment that was contributing to the neurological symptoms.

We built a phased care plan around those findings. Dietary protocol, targeted supplementation, and a phased approach to hormone support.

Six months in, her energy had returned to a functional level, the joint pain had significantly reduced, and she described the brain fog as 'almost entirely gone.'

Individual results vary. Every patient's biology is different, and outcomes depend on many factors. But the principle is consistent: you were made for health. When the body is not expressing it, there is a reason — and the reason is findable.

— Dr. Aaron Hartman, MD
Richmond Integrative & Functional Medicine | Richmond, VA | richmondfunctionalmedicine.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your New Patient Visit",
            "cta_url": "https://richmondfunctionalmedicine.com/new-patients/"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"sccimed-org_20260224_210110": {
    "booking_url": "https://sccimed.org/new-patients",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your SCCI assessment results — a few patterns stood out, [FIRST_NAME]",
            "preview": "What your score is actually pointing to",
            "body": """Hi [FIRST_NAME] — quick note from Kimberly at South Carolina Center for Integrative Medicine.

I reviewed your Custom Health Assessment, and a few patterns came up right away:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

Here is what our approach is built on: holistic medicine with a traditional feel. We believe that real care does not have to choose between being thorough and being human. You should be able to have a provider who runs advanced functional testing and also actually knows you.

The 3 things that tend to create the most real improvement for people with [CORE_ISSUE_1]:

1. Identify the actual driver — most of the time it has not been clearly named
2. Address the whole person — not just the most testable symptom
3. Build a relationship that allows care to evolve as you do

We are in Columbia, SC, serving patients in-person and via telehealth.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a new patient visit and let us work through your pattern together → [SCHEDULE_LINK]

— Kimberly Shirk, PA-C
South Carolina Center for Integrative Medicine | Columbia, SC | sccimed.org""",
            "cta_text": "Book Your New Patient Visit",
            "cta_url": "https://sccimed.org/new-patients"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "Why [PRIMARY_SYMPTOM] often outlasts conventional treatment — explained plainly",
            "preview": "A short explanation worth your 2 minutes",
            "body": """Hi [FIRST_NAME],

Something I want to explain that tends to reframe how patients think about persistent symptoms.

Most of what keeps people feeling unwell — even when their labs are 'fine' — comes down to three things that standard medicine rarely looks for: chronic systemic inflammation that does not trigger clear diagnostic markers, hormonal or metabolic patterns that fall within reference ranges but are below optimal for that person, and a gut environment that is quietly disrupting how the body absorbs nutrients and sends signals throughout.

These are not rare or exotic findings. They are incredibly common in patients who have been told nothing is wrong.

Holistic medicine means seeing those three things as connected — and addressing them together rather than in isolation. It also means having the kind of relationship with your provider where that level of detail can actually be explored.

At South Carolina Center for Integrative Medicine, we run the functional testing that surfaces these patterns, build a plan around what we find, and follow up closely enough to know when it is working and when it needs to change.

That is holistic. That is integrative. And it is what we do.

— Kimberly Shirk, PA-C
South Carolina Center for Integrative Medicine | Columbia, SC | sccimed.org

[Book a New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Book a New Patient Visit",
            "cta_url": "https://sccimed.org/new-patients"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient with your pattern — what changed when the root was found",
            "preview": "One short story before I close the loop",
            "body": """Hi [FIRST_NAME],

One final note before I close the loop on your assessment.

A woman in her mid-40s came to us after years of fatigue, hormonal irregularity, and recurring infections that had been attributed to 'immune sensitivity.' She had been on multiple short-term treatments without lasting improvement.

After a thorough functional intake, we identified a pattern of chronic gut dysbiosis suppressing immune regulation, a hormonal environment that was contributing to the fatigue and cycle irregularity, and a nutrient depletion profile that had been compounding over several years.

We built an integrative care plan — phased, monitored, and adjusted over four months as her markers shifted.

At her six-month check-in, she described her energy as 'completely different,' her cycles as regular for the first time in years, and her frequency of illness as significantly reduced.

Individual results vary. Outcomes depend on personal health factors and are not guaranteed. But the consistent pattern I see: when the root drivers are identified and addressed together, the body responds in ways it could not when only part of the picture was being treated.

If your assessment reflects a similar pattern, I would be glad to work with you.

— Kimberly Shirk, PA-C
South Carolina Center for Integrative Medicine | Columbia, SC | sccimed.org

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your New Patient Visit",
            "cta_url": "https://sccimed.org/new-patients"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"shiftfunctionalmed-com_20260226_120559": {
    "booking_url": "https://shiftfunctionalmed.com/new-patients/",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your SHIFT assessment results — Dr. Agnew noticed a few patterns, [FIRST_NAME]",
            "preview": "What your score is pointing to",
            "body": """Hi [FIRST_NAME] — quick note from Dr. Agnew at SHIFT Functional Medicine.

I reviewed your Custom Health Assessment, and a few patterns stood out:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

Here is what our name means: a real shift in how your health is approached — from symptom suppression to root cause resolution. That is not a marketing phrase. It is a structural difference in how we practice.

The 3 things that create the most meaningful shift for people with [CORE_ISSUE_1]:

1. Find the root cause — the actual driver, not the presenting symptom
2. Build a precise, individualized plan — not a generic protocol
3. Measure the response and adjust — so the improvement is real and lasting

We practice in Bend, OR, with both in-person and telehealth options.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a new patient visit and let us map out your root cause together → [SCHEDULE_LINK]

— Dr. Marie Agnew, DNP, FNP-C, IFMCP
SHIFT Functional Medicine | Bend, OR | shiftfunctionalmed.com""",
            "cta_text": "Book Your New Patient Visit",
            "cta_url": "https://shiftfunctionalmed.com/new-patients/"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "The root cause of [PRIMARY_SYMPTOM] — what most care never looks for",
            "preview": "Plain explanation, worth 2 minutes",
            "body": """Hi [FIRST_NAME],

I want to explain something about the pattern in your assessment that tends to shift how people understand their experience.

IFMCP-certified practitioners are trained to look at the body as a system — one where symptoms emerge from a combination of upstream drivers, not from a single isolated malfunction. This is different from how conventional medicine is structured, and it changes what is possible in terms of outcomes.

For a pattern like yours — with [PRIMARY_SYMPTOM] as a central complaint — the root cause almost always involves one or more of the following: a dysregulated HPA axis driving cortisol patterns that disrupt sleep, energy, and hormonal balance; a systemic inflammatory state that has reached a level where it becomes self-sustaining; or a gut microbiome disruption that is quietly affecting everything from immune function to mood.

Standard care manages the end result. Functional medicine looks for the starting point.

At SHIFT, we run the advanced panel, take the detailed history, and build a plan that is specific to your pattern — not one that fits most people with your diagnosis.

That is the shift.

— Dr. Marie Agnew, DNP, FNP-C, IFMCP
SHIFT Functional Medicine | Bend, OR | shiftfunctionalmed.com

[Book a New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Book a New Patient Visit",
            "cta_url": "https://shiftfunctionalmed.com/new-patients/"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient who came in with your pattern — what changed at SHIFT",
            "preview": "One story worth your time",
            "body": """Hi [FIRST_NAME],

One last note — a patient story that I think might resonate.

A woman in her early 40s came to SHIFT after years of fatigue, weight that would not move despite significant effort, and brain fog that had made her professional life increasingly difficult. She had been evaluated multiple times and told her labs were normal.

After a full SHIFT intake — advanced functional panel, comprehensive history, and an assessment of her lifestyle stressors — we identified adrenal dysregulation, a thyroid that was within range but below optimal for her specifically, and a gut environment that was significantly impairing nutrient absorption.

We built a phased, targeted plan: a protocol designed for her specific pattern, adjusted monthly as we tracked her response.

Four months in, her energy was back, the brain fog had largely lifted, and she had lost weight without restriction — because the metabolic block that had been working against her had been removed.

Individual results vary. Every patient is different, and outcomes cannot be guaranteed. But the principle is consistent: when the actual root cause is found and addressed precisely, the body responds.

Your assessment pointed us in the right direction. Let us follow it together.

— Dr. Marie Agnew, DNP, FNP-C, IFMCP
SHIFT Functional Medicine | Bend, OR | shiftfunctionalmed.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your New Patient Visit",
            "cta_url": "https://shiftfunctionalmed.com/new-patients/"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"westholisticmedicine-com_20260226_115818": {
    "booking_url": "https://westholisticmedicine.com/new-patients/",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your West Holistic assessment — Dr. Maltz noticed a few patterns, [FIRST_NAME]",
            "preview": "What your score is pointing to",
            "body": """Hi [FIRST_NAME] — quick note from Dr. Maltz at West Holistic Medicine.

I reviewed your Custom Health Assessment, and a few patterns came up immediately:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

Here is what I believe and what I practice: the whole you — your physical health, your mental and emotional patterns, your environment — all of it contributes to how your body is functioning right now. Root-cause care means we look at the whole picture, not just the noisiest symptom.

The 3 things that create the most real improvement for people with [CORE_ISSUE_1]:

1. Look at the full picture — not just what shows on a standard panel
2. Address the actual root cause — with integrative and functional tools that reach where the problem lives
3. Build a plan that fits your life — because sustainable care looks different for every person

I practice in Austin, TX, in-person and virtually.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a new patient visit and let us work through your specific pattern together → [SCHEDULE_LINK]

— Dr. Ashley Maltz, MD, MPH
West Holistic Medicine | Austin, TX | westholisticmedicine.com""",
            "cta_text": "Book Your New Patient Visit",
            "cta_url": "https://westholisticmedicine.com/new-patients/"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "Why [PRIMARY_SYMPTOM] often means something upstream needs attention",
            "preview": "A plain explanation most patients find genuinely helpful",
            "body": """Hi [FIRST_NAME],

Something that I want to share that I find shifts how patients relate to their symptoms.

Symptoms are rarely the problem. They are the signal. And the signal is usually pointing upstream — to a systemic imbalance, a depletion, or a dysregulation that the body has been compensating for, sometimes for years, before the symptom becomes impossible to ignore.

For a pattern like yours — with [PRIMARY_SYMPTOM] as a central complaint — the upstream contributors typically include some combination of chronic inflammation, hormonal or neurotransmitter dysregulation, gut health disruption affecting systemic signaling, or an accumulated stress load that the body has not been able to fully clear.

What makes root-cause medicine different is that we start by listening to the whole signal — not just the loudest piece — and work backward to find what the body is actually trying to communicate.

My background in both conventional medicine and public health has shaped how I think about this: health does not happen in isolation. Environment, stress, biology, and behavior are all contributing — and the most effective care accounts for all of them.

That is what we do at West Holistic Medicine.

— Dr. Ashley Maltz, MD, MPH
West Holistic Medicine | Austin, TX | westholisticmedicine.com

[Book a New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Book a New Patient Visit",
            "cta_url": "https://westholisticmedicine.com/new-patients/"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient with your pattern — what changed when we looked at the whole picture",
            "preview": "Short story. Worth reading.",
            "body": """Hi [FIRST_NAME],

One final note — a patient story that tends to resonate with people who complete assessments like yours.

A woman in her late 30s came to me after years of irregular cycles, persistent fatigue, and anxiety that had been treated with medication without addressing the underlying cause. She had been told her labs were normal. She felt like her body was not responding to anything she tried.

After a full holistic intake — detailed history, functional testing, and a careful look at her stress load and environment — I identified chronic low-grade inflammation, a hormonal pattern that was symptomatic but within standard range, and a significant impact of chronic work stress on her cortisol rhythm.

We built a care plan that addressed all three: targeted anti-inflammatory support, hormonal optimization, and structured lifestyle modifications based on her specific stress pattern.

Five months in, her cycles had normalized, her energy had stabilized, and she described her anxiety as 'manageable in a way it never was before.'

Individual results vary. Outcomes depend on many personal factors. But the consistent finding is: when you look at the whole person and address the actual root, the body can do remarkable things.

— Dr. Ashley Maltz, MD, MPH
West Holistic Medicine | Austin, TX | westholisticmedicine.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your New Patient Visit",
            "cta_url": "https://westholisticmedicine.com/new-patients/"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"wisemanfamilypractice-com_20260224_224903": {
    "booking_url": "https://wisemanfamilypractice.com/portal-appointments/",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your Wiseman assessment results — Dr. Wiseman noticed a few patterns, [FIRST_NAME]",
            "preview": "What your score is pointing to",
            "body": """Hi [FIRST_NAME] — quick note from Dr. Wiseman at Wiseman Family Practice.

I reviewed your Custom Health Assessment, and a few patterns stood out:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

Here is the thing about integrative family medicine: it means I know you — not just your labs. And when I know you, I can see patterns that a 10-minute visit never surfaces.

The 3 things that create the most meaningful shift for people with [CORE_ISSUE_1]:

1. Identify what is actually driving the pattern — through a thorough intake, not just a standard panel
2. Build a plan that fits your life and your whole health picture
3. Follow through — adjusting as you respond, with real markers showing real progress

We are in Cedar Park, with patients across the Austin area, in-person and virtually.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a visit and let us work through your pattern together → [SCHEDULE_LINK]

— Dr. Jeremy Wiseman, MD
Wiseman Family Practice | Cedar Park, TX | wisemanfamilypractice.com""",
            "cta_text": "Book Your Visit",
            "cta_url": "https://wisemanfamilypractice.com/portal-appointments/"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "Why [PRIMARY_SYMPTOM] often persists — the integrative medicine view",
            "preview": "A helpful explanation most clinics skip",
            "body": """Hi [FIRST_NAME],

I want to share something that I find changes how patients understand their experience.

Family medicine, done well, is about continuity — knowing the patient across time and seeing patterns that a single-visit provider cannot see. Integrative medicine adds another layer: the willingness to look for the root, not just manage the symptom.

For a pattern like yours — with [PRIMARY_SYMPTOM] as a central complaint — the underlying driver is almost always something that has been present and building over time. Hormonal patterns that have gradually shifted outside the optimal range. A gut environment that is affecting systemic function. A chronic stress load that has dysregulated cortisol and is suppressing recovery.

Standard care tends to address the end result. Integrative family medicine starts earlier in the chain — where the intervention is simpler, less invasive, and more durable.

At Wiseman Family Practice, I combine the relationship and continuity of family medicine with the diagnostic depth of integrative and functional medicine. The result is care that actually knows you — and has the tools to find the root.

— Dr. Jeremy Wiseman, MD
Wiseman Family Practice | Cedar Park, TX | wisemanfamilypractice.com

[Book Your Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Book Your Visit",
            "cta_url": "https://wisemanfamilypractice.com/portal-appointments/"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient with your pattern — what changed when we took the full picture seriously",
            "preview": "One short story worth reading",
            "body": """Hi [FIRST_NAME],

One last note before I close the loop.

A man in his late 40s came to my practice as a new patient after years of fatigue, creeping weight gain, and a low mood that he had attributed to getting older. He had seen multiple providers. Nothing had changed meaningfully.

In our first extended intake — which I make time for with every new patient — I identified a thyroid pattern that was technically within range but well below optimal, a hormonal picture consistent with andropause that had not been addressed, and a chronic sleep disruption that was suppressing his ability to recover.

We built a care plan that addressed all three. Targeted hormonal support. A structured approach to improving sleep quality. Specific nutritional interventions based on his panel.

Six months in, he described his energy as 'like when I was 35.' His weight had shifted, his mood had stabilized, and he said he finally felt like someone had taken the time to actually find the problem.

Individual results vary. Outcomes depend on many personal factors. But the pattern I see consistently: when you have the relationship to ask the right questions and the tools to find the root, the body responds.

— Dr. Jeremy Wiseman, MD
Wiseman Family Practice | Cedar Park, TX | wisemanfamilypractice.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your Visit",
            "cta_url": "https://wisemanfamilypractice.com/portal-appointments/"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"www-aroga-com_20260226_114645": {
    "booking_url": "https://www.aroga.com/new-patients/",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your Aroga assessment — a few patterns stood out, [FIRST_NAME]",
            "preview": "What your results are pointing to",
            "body": """Hi [FIRST_NAME] — quick note from the Aroga care team in Victoria.

I reviewed your Custom Health Assessment, and a few patterns came up right away:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

Here is what lifestyle medicine is built around: the evidence is clear that how we live — how we move, sleep, eat, connect, and manage stress — is the most powerful determinant of long-term health. And when those systems are misaligned with how the body is designed to function, symptoms follow.

The 3 things that tend to move the needle most for people with [CORE_ISSUE_1]:

1. Identify which lifestyle system is out of alignment — and why
2. Build realistic, evidence-based changes that the body can actually use
3. Support the process — with clinical guidance and accountability, not just information

We are in Victoria, BC, with virtual care available across Canada.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a new patient visit and let us build your personalized lifestyle medicine plan → [SCHEDULE_LINK]

— The Aroga Lifestyle Medicine Team
Aroga Lifestyle Medicine | Victoria, BC | aroga.com""",
            "cta_text": "Book Your New Patient Visit",
            "cta_url": "https://www.aroga.com/new-patients/"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "Why [PRIMARY_SYMPTOM] is often a lifestyle signal — not a disease",
            "preview": "A useful distinction most clinics do not make",
            "body": """Hi [FIRST_NAME],

Something I want to explain that changes how most people think about their health pattern.

Lifestyle medicine starts from an evidence-based premise that most clinical practice does not emphasize: the majority of chronic symptoms — fatigue, metabolic disruption, mood instability, inflammatory conditions — are driven primarily by modifiable lifestyle factors, not by pathology that requires ongoing medication management.

That is not a dismissal of symptoms. It is a reframe of the cause.

For a pattern like yours — with [PRIMARY_SYMPTOM] as a central complaint — the most common drivers are chronic sleep disruption affecting hormonal regulation, a movement pattern that has shifted the body into a state of metabolic underperformance, and a stress response that has become its own inflammatory driver.

What standard medicine often misses is not the symptom — it manages those well. What it misses is the upstream cause: the behavioral and physiological pattern that is producing the symptom in the first place.

At Aroga, we address that cause with the same clinical rigor that conventional medicine applies to disease management. Evidence-based, individualized, and built for the long term.

That is what we do.

— The Aroga Lifestyle Medicine Team
Aroga Lifestyle Medicine | Victoria, BC | aroga.com

[Book a New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Book a New Patient Visit",
            "cta_url": "https://www.aroga.com/new-patients/"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient with your pattern — what changed with a real lifestyle medicine plan",
            "preview": "Short story. Specific results.",
            "body": """Hi [FIRST_NAME],

One last note before I close the loop on your assessment.

A man in his early 50s came to Aroga with metabolic syndrome, chronic fatigue, and a sense that his health had been declining steadily for a decade. He had been prescribed multiple medications and told to 'eat better and exercise more' without any specific guidance.

After a thorough lifestyle medicine intake — sleep, movement, nutrition, stress, and social health — we identified a cluster of interconnected patterns: severely disrupted sleep architecture, a physical activity pattern below what his metabolic needs required, and a chronic stress load that had elevated cortisol enough to suppress immune and hormonal function.

We built a structured, evidence-based lifestyle medicine plan. Specific. Phased. Monitored with clinical markers at each checkpoint.

Eight months later, his metabolic markers had improved significantly, he had come off one of his medications under his physician's guidance, and he described his energy as 'something I thought I had permanently lost.'

Individual results vary and are never guaranteed. Outcomes depend on many personal factors including adherence and baseline health. But the evidence is clear: when lifestyle factors are addressed clinically and precisely, the body's capacity to restore function is significant.

Your assessment gave us a clear starting point. We would love to work with you.

— The Aroga Lifestyle Medicine Team
Aroga Lifestyle Medicine | Victoria, BC | aroga.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your New Patient Visit",
            "cta_url": "https://www.aroga.com/new-patients/"
        }
    ]
},

# ─────────────────────────────────────────────────────────────────────────────
"www-iwcjacksonville-com_20260226_115432": {
    "booking_url": "https://www.iwcjacksonville.com/new-patients/",
    "emails": [
        {
            "email_number": 1,
            "type": "smart_practice_value_drop",
            "subject": "Your IWC assessment results — Dr. Ellis noticed a few patterns, [FIRST_NAME]",
            "preview": "What your score is actually pointing to",
            "body": """Hi [FIRST_NAME] — quick note from Dr. Ellis at Integrative Wellness Center of Jacksonville.

I reviewed your Custom Health Assessment, and a few patterns came up right away:

* Primary focus: [CORE_ISSUE_1]
* Secondary contributors: [CORE_ISSUE_2], [CORE_ISSUE_3]
* Common symptoms in this pattern: [SYMPTOM_A], [SYMPTOM_B], [SYMPTOM_C]

Here is what root-cause holistic care means in practice: we look at the full system — physical, energetic, and environmental — because symptoms rarely have a single cause. And the most effective treatment rarely has a single modality.

The 3 things that create the most real and lasting improvement for people with [CORE_ISSUE_1]:

1. Identify the full driver — not just the most visible piece
2. Address it with a combination of approaches that reaches the root
3. Build a rhythm of care — because healing is a process, not a single intervention

We are in Jacksonville Beach, FL, combining acupuncture, holistic medicine, and functional approaches.

Your next step:
* Option A: See your recommended first steps inside the app → [VIEW_MY_PLAN_LINK]
* Option B: Book a new patient visit and let us map your root cause together → [SCHEDULE_LINK]

— Dr. Melissa Levy Ellis, DACM, AP
Integrative Wellness Center of Jacksonville | Jacksonville Beach, FL | iwcjacksonville.com""",
            "cta_text": "Book Your New Patient Visit",
            "cta_url": "https://www.iwcjacksonville.com/new-patients/"
        },
        {
            "email_number": 2,
            "type": "mechanism_story",
            "subject": "Why [PRIMARY_SYMPTOM] often needs more than one approach to resolve",
            "preview": "A plain explanation worth your 2 minutes",
            "body": """Hi [FIRST_NAME],

I want to explain something about the pattern in your assessment that I think will be useful.

Chinese medicine and functional medicine share a premise that Western conventional care rarely applies: the body is a whole system, and symptoms emerge from disruptions in multiple interacting pathways — not from a single malfunction.

For a pattern like yours — with [PRIMARY_SYMPTOM] as a central complaint — the most effective approach almost always requires addressing two things simultaneously: the systemic biochemical root (which functional medicine identifies through targeted testing and addresses through nutrition, supplementation, and lifestyle) and the energetic and nervous system component (which acupuncture addresses by directly regulating the pathways that drive inflammatory and stress responses).

Standard care typically offers one piece of this. The symptom quiets but the underlying pattern continues.

At IWC Jacksonville, we bring both lenses to every patient — not as separate protocols but as an integrated approach that addresses the full picture. That is what makes the results more durable.

— Dr. Melissa Levy Ellis, DACM, AP
Integrative Wellness Center of Jacksonville | Jacksonville Beach, FL | iwcjacksonville.com

[Book a New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Book a New Patient Visit",
            "cta_url": "https://www.iwcjacksonville.com/new-patients/"
        },
        {
            "email_number": 3,
            "type": "proof_and_results",
            "subject": "A patient with your pattern — what shifted with an integrated approach",
            "preview": "One story worth your time",
            "body": """Hi [FIRST_NAME],

One final note before I close the loop on your assessment.

A woman in her early 40s came to our practice after years of chronic pain, fatigue, and hormonal disruption that had not responded fully to conventional treatment. She had tried acupuncture briefly elsewhere and felt it 'sort of helped.' She had been on hormonal support with partial results.

After a full IWC intake — combining a functional medicine assessment with a Chinese medicine diagnostic evaluation — we identified a pattern where her systemic inflammatory state was continuously undermining the hormonal treatment she had been receiving. The two problems were interacting in a way that had not been accounted for.

We built an integrated plan: a course of targeted acupuncture to regulate the inflammatory and stress response, combined with functional medicine interventions addressing the root of the inflammation itself.

Three months in, the hormonal treatment was working significantly better. Her pain had reduced substantially. She described herself as 'feeling better than I have in years — and I did not think that was still possible for me.'

Individual results vary. Outcomes depend on many personal factors and are not guaranteed. But the consistent pattern at IWC: when the full picture is addressed with the right combination of approaches, the body can respond in ways that a single modality alone could not produce.

Your assessment is the starting point. We would love to work with you.

— Dr. Melissa Levy Ellis, DACM, AP
Integrative Wellness Center of Jacksonville | Jacksonville Beach, FL | iwcjacksonville.com

Disclaimer: Individual results vary. This is not medical advice.

[Schedule Your New Patient Visit →]([SCHEDULE_LINK])""",
            "cta_text": "Schedule Your New Patient Visit",
            "cta_url": "https://www.iwcjacksonville.com/new-patients/"
        }
    ]
},

}  # end EMAILS dict


def format_email_markdown(email: dict) -> str:
    """Format email as rich markdown for gamma_content."""
    lines = [
        f"## Email {email['email_number']} — {email.get('type','').replace('_',' ').title()}",
        f"**Subject:** {email['subject']}",
        f"**Preview:** {email['preview']}",
        "",
        email['body'],
        "",
        f"**CTA:** [{email['cta_text']}]({email['cta_url']})",
    ]
    return "\n".join(lines)


def main():
    updated = 0
    skipped = 0

    for run_dir_name, data in EMAILS.items():
        run_dir = BASE / run_dir_name
        p2_path = run_dir / "phase2_output.json"

        if not p2_path.exists():
            print(f"  ⚠️  SKIP (no phase2_output.json): {run_dir_name}")
            skipped += 1
            continue

        p2 = json.loads(p2_path.read_text(encoding="utf-8"))

        # Replace emails array
        p2["emails"] = data["emails"]

        # Update gamma_content email fields
        gc = p2.get("gamma_content", {})
        for i, email in enumerate(data["emails"], 1):
            gc[f"email{i}"] = format_email_markdown(email)
        p2["gamma_content"] = gc

        # Write back
        p2_path.write_text(json.dumps(p2, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  ✓ Updated: {run_dir_name}")
        updated += 1

    print(f"\n{'='*60}")
    print(f"DONE: {updated} updated, {skipped} skipped")


if __name__ == "__main__":
    main()

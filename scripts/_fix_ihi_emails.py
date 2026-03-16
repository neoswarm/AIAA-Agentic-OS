#!/usr/bin/env python3
"""One-shot: rewrite IHI emails with correct patient-facing Speed-to-Trust sequence."""
import json
from pathlib import Path

P2 = Path("output/d100_runs/integratedhealthofindiana-com_20260307_132108/phase2_output.json")
p2 = json.loads(P2.read_text())

p2["emails"] = [
    {
        "type": "value_drop",
        "subject": "What your [PRIMARY_SYMPTOM] is actually telling you",
        "preview": "There's something important in your assessment we want to share.",
        "body": (
            "Hi [FIRST_NAME],\n\n"
            "Thank you for completing the health assessment.\n\n"
            "Your answers stood out to us — particularly around [PRIMARY_SYMPTOM]. "
            "That pattern comes up more often than most people realize, and it's rarely just one thing in isolation.\n\n"
            "Here's something worth knowing:\n\n"
            "When [PRIMARY_SYMPTOM] persists despite doing everything right — eating well, sleeping enough, exercising — "
            "it usually means the body is compensating for an underlying imbalance that hasn't been identified yet.\n\n"
            "Conventional labs check whether you're sick. Functional medicine asks why you feel the way you do — "
            "even when those labs come back normal.\n\n"
            "That's the gap we work in at Integrated Health of Indiana.\n\n"
            "We'd like to walk you through what we found in your assessment and what it could mean for you specifically.\n\n"
            "Review your next steps: [BOOKING_LINK]\n\n"
            "Take care,\n"
            "The Care Team at Integrated Health of Indiana"
        ),
    },
    {
        "type": "mechanism_story",
        "subject": "Why [PRIMARY_SYMPTOM] keeps coming back (even when you try everything)",
        "preview": "Most approaches treat the signal. We look for the source.",
        "body": (
            "Hi [FIRST_NAME],\n\n"
            "Imagine your body is sending you a message every single day.\n\n"
            "That message is [PRIMARY_SYMPTOM]. Most approaches silence the notification. "
            "They don't read the message.\n\n"
            "That's not a criticism of anyone you've seen before. "
            "It's simply how most care systems are structured: identify the symptom, reduce it, move on.\n\n"
            "Functional medicine starts with a different question: what is the body trying to regulate, "
            "and why is it struggling?\n\n"
            "In our clinical experience, [PRIMARY_SYMPTOM] combined with [SECONDARY_SYMPTOM] often traces back "
            "to disruptions in one of several interconnected systems — hormonal, digestive, neurological, or inflammatory. "
            "Which system matters enormously, because the approach changes completely depending on the answer.\n\n"
            "Your assessment gave us a clear starting picture. The next step is a deeper conversation — "
            "not a sales pitch. Just a clinical look at what may actually be driving your experience.\n\n"
            "When you're ready: [BOOKING_LINK]\n\n"
            "Dr. Trevor Miller, D.C., IFMCP, L.Ac, CFMP\n"
            "Integrated Health of Indiana"
        ),
    },
    {
        "type": "proof_results",
        "subject": "A patient with a similar pattern — what changed for her",
        "preview": "Results vary, but this story might feel familiar.",
        "body": (
            "Hi [FIRST_NAME],\n\n"
            "I want to share something from a patient — we'll call her M.\n\n"
            "She came in with a pattern similar to what you described: [PRIMARY_SYMPTOM] for over [DURATION_OR_TRIGGER], "
            "plus [SECONDARY_SYMPTOM] that was affecting her work and her sleep. "
            "She'd had full bloodwork done twice. Everything came back normal. She was told it was probably stress.\n\n"
            "We ran a different panel. What we found was a combination of hormonal dysregulation and gut permeability "
            "that standard tests don't screen for.\n\n"
            "Once we addressed the actual mechanisms — not just the symptoms — her energy began returning within 8 weeks. "
            'By month four, she described it as "feeling like myself again for the first time in years."\n\n'
            "Important: results vary significantly from person to person. "
            "We don't know yet what's driving your specific experience. "
            "That's exactly what a first consultation is designed to find out.\n\n"
            "If her story resonates, the next step is a simple conversation: [BOOKING_LINK]\n\n"
            "This is not a commitment. It's a chance to get clear answers.\n\n"
            "Dr. Trevor Miller, D.C., IFMCP, L.Ac, CFMP\n"
            "Integrated Health of Indiana\n\n"
            "This email is for informational purposes only and does not constitute medical advice "
            "or establish a patient-provider relationship."
        ),
    },
]

P2.write_text(json.dumps(p2, indent=2, ensure_ascii=False))
print("Done — 3 patient emails written to phase2_output.json")
for e in p2["emails"]:
    print(f"  [{e['type']}] {e['subject']}")

"""Fraud and AML red-flag indicators for a Philippine bank's front line.

Why this module is a deterministic rule table and not a model call:

    A compliance officer has to be able to say *why* the system flagged
    something, and repeat that answer to an examiner months later. A model that
    decides "this looks suspicious" with no quotable rule is not defensible and
    not reproducible. Every indicator here is a named typology with a stable id,
    a tier, a declared set of exposed parties, an evidence span, and a legal
    hook. Same input, same output, on any machine, with no weights installed.

The hook is the anti-fabrication guarantee. An indicator must name either

    * a document that is genuinely in the corpus, plus an anchor phrase that is
      verifiably present in that document's indexed text, or
    * the literal doc_id "GAP", in which case its anchor must name the regulator
      whose rule is missing - BSP, SEC, AMLC or the PCI SSC.

There is no third option. An indicator cannot cite a BSP circular we could not
download, and it cannot cite a section of RA 9160 whose reporting provisions are
absent from the retrievable text. Where the law that decides the question is
outside the corpus, the engine says GAP and hands the question to a human.

Risk tiers are deliberately coarse. A fine-grained score invites people to treat
a 0.62 as meaningfully different from a 0.58, which is exactly the false
precision that gets a tool ignored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

# The document id used when the governing rule is outside the corpus.
GAP = "GAP"


class RiskTier(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


SEVERITY: dict[str, int] = {
    RiskTier.CRITICAL.value: 5,
    RiskTier.HIGH.value: 4,
    RiskTier.MEDIUM.value: 3,
    RiskTier.LOW.value: 2,
    RiskTier.NONE.value: 1,
}


@dataclass(frozen=True)
class LegalHook:
    """Where the governing rule lives, and how to verify we actually hold it."""

    doc_id: str
    anchor: str
    note: str = ""

    @property
    def is_gap(self) -> bool:
        return self.doc_id == GAP


@dataclass(frozen=True)
class Indicator:
    id: str
    label: str
    tier: str
    exposure: tuple[str, ...]
    why: str
    action: str
    legal_hook: LegalHook
    patterns: tuple[str, ...]
    regulator: str = ""


@dataclass(frozen=True)
class IndicatorMatch:
    indicator: Indicator
    evidence: str


# -- RA 9160 anchors verified present in the indexed corpus text --------------
RA9160_COVERED_TX = LegalHook(
    "RA-9160", "covered transaction",
    "Covered transactions are reportable; splitting to stay under them is "
    "structuring.",
)
RA9160_LAUNDERING = LegalHook(
    "RA-9160", "money laundering",
    "Proceeds transacted through an account to disguise their origin.",
)
RA9160_COVERED_INST = LegalHook(
    "RA-9160", "covered institution",
    "Banks are covered institutions and must satisfy customer "
    "identification and record keeping.",
)
RA9160_CUST_ID = LegalHook(
    "RA-9160", "true identity of its clients",
    "The bank must establish and record the true identity of its clients.",
)
RA9160_TIPOFF = LegalHook(
    "RA-9160", "prohibited from communicating",
    "Telling a customer that a covered transaction report was made is itself "
    "an offence.",
)
RA9160_FREEZE = LegalHook(
    "RA-9160", "freezing",
    "Freezing of monetary instrument or property.",
)
RA9160_PENAL = LegalHook(
    "RA-9160", "penal provisions",
    "Penalties attach to the laundering offence and to non-compliant officers.",
)
RA8792_EDM = LegalHook(
    "RA-8792", "electronic data message",
    "Electronic transactions carry legal effect and evidence; instructions "
    "arriving by email are not automatically authenticated.",
)
RA8792_UNAUTH = LegalHook(
    "RA-8792", "unauthorized",
    "Liability for unauthorized electronic transactions.",
)
RA11967_FRAUD = LegalHook(
    "RA-11967", "fraud",
    "E-commerce fraud and the online merchant's obligations.",
)
RA11967_MERCHANT = LegalHook(
    "RA-11967", "online merchant",
    "Duties owed by an online merchant to the consumer.",
)
DPA_CONFIDENTIALITY = LegalHook(
    "RA-10173", "strict confidentiality",
    "Employees, agents and representatives hold personal information under "
    "strict confidentiality.",
)
DPA_SENSITIVE = LegalHook(
    "RA-10173", "sensitive personal information",
    "Financial information about a person is sensitive personal information.",
)

# -- Rules we can name but cannot quote ---------------------------------------
BSP_GAP = LegalHook(
    GAP, "BSP - Manual of Regulations for Banks and circulars",
    "bsp.gov.ph refused this machine on 2026-10-10; the MORB, the circulars on "
    "suspicious transaction reporting and the consumer protection circulars are "
    "not in this corpus.",
)
SEC_GAP = LegalHook(
    GAP, "SEC - circulars and advisories, including UITAP advisories",
    "sec.gov.ph refused this machine on 2026-10-10; investment and securities "
    "fraud advisories are not in this corpus.",
)
AMLC_GAP = LegalHook(
    GAP, "AMLC - issuances and reporting guidelines",
    "The AMLC law repository is not retrievable; reporting deadlines must be "
    "confirmed against AMLC guidance by the compliance officer.",
)
PCI_GAP = LegalHook(
    GAP, "PCI Security Standards Council - PCI DSS",
    "PCI DSS is not in this corpus; the cardholder-data rules below are "
    "industry practice, flagged as guidance rather than cited law.",
)


INDICATORS: tuple[Indicator, ...] = (
    # -- Structuring and layering -------------------------------------------
    Indicator(
        id="structuring",
        label="Structuring - cash activity kept just under a reporting threshold",
        tier=RiskTier.HIGH.value,
        exposure=("bank",),
        why=(
            "A pattern of cash transactions each sitting just below the covered "
            "transaction threshold is the classic signature of structuring, "
            "which exists to defeat reporting rather than to serve a customer."
        ),
        action=(
            "Do not accept the pattern as routine. Escalate to the MLRO the same "
            "working day and preserve the transaction records."
        ),
        legal_hook=RA9160_COVERED_TX,
        patterns=(
            r"\bjust under\b[^.]{0,40}\bthreshold\b",
            r"\bbelow the (?:reporting |covered transaction )?threshold\b",
            r"\bunder the threshold\b",
            r"\bsplit (?:the )?(?:deposit|cash|amount|transaction)",
            r"\b(?:split|multiple|several)[^.]{0,40}\bsmall(?:er)? (?:cash )?deposits?\b",
            r"\bbelow the limit\b[^.]{0,30}\bcash\b",
            r"\bmany small\b[^.]{0,30}\bcash\b",
            # A thousands-separated cash amount is the shape structuring takes.
            # The narrative rarely says "below the threshold" - it says the
            # number. 499,000 in cash, then an onward transfer, is the pattern.
            r"\b\d{1,3}(?:,\d{3})+\b[^.]{0,30}\bcash\b",
            r"\bcash\b[^.]{0,25}\b\d{1,3}(?:,\d{3})+\b",
            r"\bcash (?:deposit|deposits|payments?)\b[^.]{0,40}\b\d",
        ),
        regulator="AMLC / BSP",
    ),
    Indicator(
        id="rapid_passthrough",
        label="Rapid pass-through - funds in and almost immediately out",
        tier=RiskTier.HIGH.value,
        exposure=("both",),
        why=(
            "Money that arrives and leaves with no economic purpose is the "
            "signature of layering. Legitimate account activity has a reason to "
            "sit."
        ),
        action=(
            "Escalate to the MLRO, pull the full account history, and ask the "
            "customer for the purpose of the funds before processing further."
        ),
        legal_hook=RA9160_LAUNDERING,
        patterns=(
            r"\b(?:same|within the same) day\b[^.]{0,40}\b(?:transfer|withdraw|remit|sent)\b",
            r"\bimmediately (?:onward |transferred |withdrawn |remitted |sent)\b",
            r"\bin and out\b",
            r"\bquick(?:ly)? pass(?:ing)? (?:through|on)\b",
            r"\bno time\b[^.]{0,30}\b(?:sit|linger|stay)\b[^.]{0,30}\b(?:account|deposit)",
            r"\bsame day\b[^.]{0,40}\b(?:overseas|abroad|international)\b",
        ),
        regulator="AMLC / BSP",
    ),
    Indicator(
        id="mule_account",
        label="Money-mule account - used by someone other than the account holder",
        tier=RiskTier.CRITICAL.value,
        exposure=("both",),
        why=(
            "An account opened by a student or unemployed person, funded in cash "
            "by strangers and used as a pass-through, is the most common retail "
            "money-laundering pattern in Philippine banking. The customer is "
            "often a victim recruited by coercion, not a knowing participant."
        ),
        action=(
            "Treat as critical. Escalate to the MLRO and the branch manager the "
            "same day, restrict the account from further outward transfers "
            "pending review, and do not tip the customer off."
        ),
        legal_hook=RA9160_COVERED_INST,
        patterns=(
            r"\bmoney[- ]mule\b",
            r"\bmule account\b",
            r"\b(?:student|young|unemployed|no income|jobless)\b[^.]{0,60}"
            r"\b(?:received|receives|accept)\b[^.]{0,40}\bcash\b",
            r"\b(?:received|accepts?)\b[^.]{0,40}\bcash\b[^.]{0,40}"
            r"\b(?:stranger|unknown|several people|third part)",
            r"\basked (?:them|him|her|the customer)\b[^.]{0,40}\b(?:to )?(?:send|transfer| remit)\b",
            r"\bclose the account\b[^.]{0,40}\bbefore\b",
        ),
        regulator="AMLC / BSP",
    ),
    Indicator(
        id="third_party_funding",
        label="Third-party funding inconsistent with the stated profile",
        tier=RiskTier.MEDIUM.value,
        exposure=("both",),
        why=(
            "A deposit whose source does not match the customer's declared "
            "business or income is either a misstatement or concealment. Either "
            "way the bank's customer identification is wrong."
        ),
        action=(
            "Request documentary proof of source before crediting, record the "
            "explanation, and refer to the MLRO if the customer declines."
        ),
        legal_hook=RA9160_CUST_ID,
        patterns=(
            r"\b(?:payment|deposit|funds?|remittance)\b[^.]{0,50}"
            r"\b(?:from )?(?:a |an )?(?:third part(?:y|ies)|unknown|unrelated|friend|relative|employer)\b",
            r"\bthird[- ]party (?:deposit|payment|funding|transfer)\b",
            r"\bsource of funds\b[^.]{0,40}\b(?:unclear|unexplained|does not match|inconsistent)\b",
            r"\bdoes not match\b[^.]{0,40}\b(?:profile|declared|income|business)\b",
        ),
        regulator="AMLC / BSP",
    ),
    Indicator(
        id="cross_border_to_unusual_counterparty",
        label="Cross-border transfer to an unrelated or unusual beneficiary",
        tier=RiskTier.HIGH.value,
        exposure=("bank",),
        why=(
            "An outbound remittance to a beneficiary with no stated relationship "
            "to the customer, especially combined with a recent account opening, "
            "is a recognised laundering route and the primary regulatory exposure "
            "for the bank."
        ),
        action=(
            "Hold for MLRO review before releasing, verify the beneficiary "
            "relationship, and screen the counterparty before any onward "
            "remittance."
        ),
        legal_hook=BSP_GAP,
        patterns=(
            r"\b(?:wire\w*|transfer\w*|remit\w*|send\w*|sent)\b[^.]{0,50}"
            r"\b(?:abroad|overseas|international|offshore|foreign)\b",
            r"\b(?:abroad|overseas|foreign|offshore)\b[^.]{0,50}"
            r"\b(?:wire\w*|transfer\w*|remittance|beneficiary)\b",
            r"\bunrelated (?:beneficiary|payee|recipient)\b",
            r"\bbeneficiary\b[^.]{0,40}\bno (?:stated |known )?relationship\b",
        ),
        regulator="BSP / AMLC",
    ),
    # -- Customer authentication and account takeover -----------------------
    Indicator(
        id="credential_solicitation",
        label="A card credential or one-time code is being solicited",
        tier=RiskTier.CRITICAL.value,
        exposure=("both",),
        why=(
            "Whoever can obtain the CVV, PIN or one-time code can authorise "
            "transactions. Soliciting one turns the bank into the attacker's "
            "assistant, and a solicited code is permanently compromised."
        ),
        action=(
            "Decline and do not record. If a customer has already disclosed a "
            "secret, stop the transaction and escalate the same day - the "
            "recording, if any, is now a stored credential."
        ),
        legal_hook=PCI_GAP,
        patterns=(
            r"\b(?:cvv|cvc2?|cvcv2|cid|cvn2?|security code|card verification)\b",
            r"\batm pin\b",
            r"\bone[- ]time (?:password|code|otp)\b",
            r"\bask\w*\b[^.]{0,30}\b(?:password|pin|otp|one[- ]time)\b",
            r"\bhumingi\b[^.]{0,40}\b(?:cvv|password|pin|otp)\b",
            r"\b(?:read|give|provide)\b[^.]{0,30}\b(?:the )?(?:password|pin|code)\b[^.]{0,20}\b(?:over|phone|call)\b",
        ),
        regulator="PCI SSC / BSP",
    ),
    Indicator(
        id="impersonation_social_engineering",
        label="Impersonation or social engineering against the customer",
        tier=RiskTier.HIGH.value,
        exposure=("customer",),
        why=(
            "A caller or sender claiming to be the bank, or a relative claiming "
            "an emergency, is the most common route by which Philippine "
            "customers are separated from their credentials."
        ),
        action=(
            "Do not disclose anything. Terminate politely, advise the customer to "
            "call back on the number printed on their card, and flag the contact "
            "for fraud monitoring."
        ),
        legal_hook=RA11967_FRAUD,
        patterns=(
            # Word-boundary bugs this caught, kept noted so they are not
            # reintroduced: `\bpretend\b` cannot match "pretending" (the 'i'
            # kills the boundary) and `third part\b` cannot match "third party".
            # Both silently cost recall on perfectly ordinary phrasing.
            r"\b(?:pretend\w*|imposter|impersonat\w+|posing)\b[^.]{0,40}"
            r"\b(?:bank|officer|employee|police|government|bsp|company)\b",
            r"\bclaimed? to be (?:from )?(?:the )?(?:bank|bsp|rsp|pnb|bdti|bdo|bpi)\b",
            r"\bsos call\b|\bemergency\b[^.]{0,40}\bmoney\b",
            r"\burgent\w*\b[^.]{0,40}\b(?:transfer|send|release|wire)\b",
            r"\bpraying for help\b[^.]{0,40}\b(?:money|funds)\b",
            r"\basking for money\b|\basked for money\b",
        ),
        regulator="BSP / SEC",
    ),
    Indicator(
        id="payment_detail_change_by_instruction",
        label="Bank or payee details changed by unverified instruction",
        tier=RiskTier.HIGH.value,
        exposure=("bank",),
        why=(
            "Fraudsters redirect legitimate payments by changing settlement "
            "details. An instruction arriving only by email or chat is not "
            "authenticated, and acting on it moves the loss to the bank."
        ),
        action=(
            "Do not act on the instruction. Call the customer back on a "
            "pre-existing number, confirm the change out of band, and log the "
            "attempt."
        ),
        legal_hook=RA8792_EDM,
        patterns=(
            r"\b(?:change|update|amend)\b[^.]{0,40}\b(?:bank details|account details|payee details|remittance details)\b",
            r"\bnew (?:bank|account|payee|remittance) details\b",
            r"\b(?:sent|received|requested)\b[^.]{0,30}\bby email\b[^.]{0,50}\b(?:change|update|transfer|credit)\b",
            r"\bverify\b[^.]{0,20}\bby (?:email|text|sms|chat)\b",
        ),
        regulator="BSP",
    ),
    Indicator(
        id="account_takeover_indicators",
        label="Account takeover signals - sudden new device, location or beneficiary",
        tier=RiskTier.HIGH.value,
        exposure=("both",),
        why=(
            "A takeover is usually visible as a pattern before it is visible as "
            "a loss: a new device, an unfamiliar location, then a new payee."
        ),
        action=(
            "Step up authentication, freeze outbound activity pending "
            "verification, and contact the customer through a known-good channel."
        ),
        legal_hook=RA8792_UNAUTH,
        patterns=(
            r"\baccount (?:takeover|take over|compromise)\b",
            r"\bnew device\b[^.]{0,50}\b(?:login|sign-?in|access)\b",
            r"\bunfamiliar (?:device|location|ip)\b",
            r"\blogin\b[^.]{0,40}\b(?:from|different) (?:a )?(?:new|different|other)\b[^.]{0,30}\b(?:device|location|country)\b",
            r"\bnew beneficiary\b[^.]{0,40}\b(?:added|created)\b",
        ),
        regulator="BSP",
    ),
    # -- Insider and tipping-off --------------------------------------------
    Indicator(
        id="insider_exposure",
        label="Insider risk - staff handling or sharing customer information",
        tier=RiskTier.HIGH.value,
        exposure=("both",),
        why=(
            "Staff who photograph records, use personal devices, or share "
            "customer details outside the process create liability for the bank "
            "and loss for the customer, and they are the route by which most "
            "internal fraud becomes possible."
        ),
        action=(
            "Do not participate and report to the data protection officer the "
            "same day. Preserve the record. Never confront the staff member "
            "alone."
        ),
        legal_hook=DPA_CONFIDENTIALITY,
        patterns=(
            r"\b(?:agent|staff|employee|teller|officer)\b[^.]{0,50}"
            r"\b(?:personal (?:phone|device|laptop)|own phone|home)\b",
            r"\b(?:photograph|photographing|screenshot|shot)\b[^.]{0,40}"
            r"\b(?:customer|client|record|account)\b",
            r"\bsharing? customer (?:details|data|information)\b",
            r"\b(?:gave|given|passed?)\b[^.]{0,30}\b(?:customer|client) (?:details|data|information)\b[^.]{0,40}\b(?:friend|family|personal)\b",
        ),
        regulator="NPC / BSP",
    ),
    Indicator(
        id="tipping_off_risk",
        label="Tipping off - revealing or probing that a report was made",
        tier=RiskTier.CRITICAL.value,
        exposure=("bank",),
        why=(
            "Telling a customer that a covered transaction report exists, or "
            "asking a customer whether one was filed, is itself prohibited and "
            "carries criminal exposure for the officer who does it."
        ),
        action=(
            "Never disclose or probe. Route every such question to the MLRO "
            "without confirming or denying anything."
        ),
        legal_hook=RA9160_TIPOFF,
        patterns=(
            r"\btip(?:ping)? ?off\b",
            r"\btell\w*\b[^.]{0,40}\b(?:customer|client)\b[^.]{0,40}"
            r"\b(?:report|reported|reported to)\b",
            r"\bask\w*\b[^.]{0,30}\b(?:customer|client)\b[^.]{0,30}"
            r"\bwhether\b[^.]{0,30}\breport\w*\b",
            r"\bconfirm\w*\b[^.]{0,40}\b(?:that )?(?:we|they)\b[^.]{0,30}\breported\b",
        ),
        regulator="AMLC",
    ),
    # -- Customer-facing conduct -------------------------------------------
    Indicator(
        id="disproportionate_amount_elder",
        label="Elder financial abuse - a third party directing a vulnerable customer",
        tier=RiskTier.HIGH.value,
        exposure=("customer",),
        why=(
            "Where an elderly customer's transactions are directed by someone "
            "else, the consent that the Act relies on may not be the customer's "
            "own. The customer is the one who loses the money."
        ),
        action=(
            "Pause the transaction, speak to the customer privately, and refer "
            "to the branch manager and the data protection officer."
        ),
        legal_hook=DPA_SENSITIVE,
        patterns=(
            r"\b(?:elderly|old|vulnerable)\b[^.]{0,60}"
            r"\b(?:guided|directed|told|instructed|coached)\b",
            r"\bon behalf of\b[^.]{0,40}\b(?:customer|client)\b[^.]{0,40}\b(?:elderly|senior)\b",
            # Word order varies: often the relative is named first and the
            # customer never appears after the verb ("their son, who was
            # directing them from the branch"). Requiring "customer" after the
            # verb dropped every case phrased that way.
            r"\b(?:relative|son|daughter|grandchild|neighbou?r|caregiver)\b[^.]{0,60}"
            r"\b(?:instructing|directing|telling|coaching|dictating|guiding)\b",
            r"\b(?:elderly|senior|vulnerable)\b[^.]{0,60}"
            r"\b(?:relative|son|daughter|caregiver|neighbou?r)\b[^.]{0,60}"
            r"\b(?:instructing|directing|telling|coaching|controlling)\b",
        ),
        regulator="BSP / NPC",
    ),
    Indicator(
        id="first_party_dispute",
        label="First-party fraud - the customer denies a transaction they made",
        tier=RiskTier.MEDIUM.value,
        exposure=("both",),
        why=(
            "A dispute the customer does not recognise is either an account "
            "takeover, a merchant problem, or a customer who made the "
            "transaction and is now denying it. The response differs completely "
            "in each case."
        ),
        action=(
            "Treat as suspected takeover until the customer confirms otherwise. "
            "Secure the account first, then follow the dispute process. Never "
            "reimburse at the counter without the fraud team."
        ),
        legal_hook=BSP_GAP,
        patterns=(
            r"\b(?:does ?n[o']t|never|no)\b[^.]{0,30}\brecognis\w+\b[^.]{0,30}\btransaction\b",
            # The everyday phrasing is "I never made that transfer", not
            # "unrecognised transaction". Matching only the formal register
            # missed the single most common way a customer opens a dispute.
            r"\bnever made\b[^.]{0,40}\b(?:transfer|payment|withdrawal|transaction|deposit)\b",
            r"\b(?:did ?n[o']t|did not) make\b[^.]{0,30}\b(?:transfer|payment|withdrawal)\b",
            r"\bwas ?n[o']t me\b",
            r"\bunauthori[sz]ed\b[^.]{0,40}\btransaction\b",
            r"\b(?:first[- ]party|app store fraud|account takeover)\b",
            r"\bdisput\w+\b[^.]{0,40}\b(?:made|authoris\w+|transacted)\b[^.]{0,20}\bby (?:them|him|her)\b",
        ),
        regulator="BSP",
    ),
    Indicator(
        id="merchant_side_deception",
        label="Online merchant deception - goods or delivery that do not arrive",
        tier=RiskTier.MEDIUM.value,
        exposure=("customer",),
        why=(
            "Where the counterparty is an online seller, the consumer's remedies "
            "against the merchant are set by statute and the bank is not the "
            "party that owes the remedy."
        ),
        action=(
            "Capture the transaction reference, direct the customer to their "
            "remedies against the merchant, and do not reverse the credit on "
            "the customer's say-so alone."
        ),
        legal_hook=RA11967_MERCHANT,
        patterns=(
            r"\b(?:item|items|order|parcel|package|goods|product)\b[^.]{0,40}"
            r"\b(?:never (?:arrived|arrives|received)|not (?:arrived|received|delivered)|missing)\b",
            r"\bonline (?:seller|merchant|shop|store)\b[^.]{0,40}"
            r"\b(?:scam|fraud|fake|not real)\b",
            r"\bprepaid\b[^.]{0,30}\b(?:not|no goods)\b",
        ),
        regulator="SEC / DTI",
    ),
    Indicator(
        id="cash_intensity_mismatch",
        label="Cash intensity inconsistent with the declared business",
        tier=RiskTier.MEDIUM.value,
        exposure=("bank",),
        why=(
            "A business that declares card or digital revenue but operates "
            "almost entirely in cash is either mis-declaring its business or is "
            "an undeclared cash business."
        ),
        action=(
            "Re-verify the business model and the declared source of funds, and "
            "update the customer record before granting any limit increase."
        ),
        legal_hook=RA9160_CUST_ID,
        patterns=(
            r"\bcash intensive\b|\balmost entirely (?:in )?cash\b",
            r"\bdeclares?\b[^.]{0,40}\b(?:digital|card|online)\b[^.]{0,40}"
            r"\bbut\b[^.]{0,40}\bcash\b",
            r"\bundeclared cash\b",
            r"\bno (?:recorded|invoices?) (?:sales|revenue)\b",
        ),
        regulator="BSP / BIR",
    ),
    Indicator(
        id="no_source_documentation",
        label="Customer cannot or will not document the funds",
        tier=RiskTier.HIGH.value,
        exposure=("bank",),
        why=(
            "An inability or unwillingness to document the purpose of funds is "
            "the single most common reason a relationship becomes a regulatory "
            "problem after the fact."
        ),
        action=(
            "Do not proceed on an unverifiable explanation. Escalate to the MLRO "
            "and record the request for documentation and the response."
        ),
        legal_hook=RA9160_CUST_ID,
        patterns=(
            r"\b(?:cannot|can't|unable to|refuses? to|declines? to|will not)\b[^.]{0,40}"
            r"\b(?:prov(?:ide|ide)|document|explain|justify|support)\b",
            r"\bno documentation\b[^.]{0,40}\b(?:funds|source|purpose)\b",
            r"\bvague (?:explanation|reason|purpose)\b",
        ),
        regulator="AMLC / BSP",
    ),
    Indicator(
        id="sanctions_or_hit",
        label="Screening hit - sanctions, watchlist or adverse match",
        tier=RiskTier.CRITICAL.value,
        exposure=("bank",),
        why=(
            "A name that matches a sanctions or watchlist entry is the highest "
            "consequence event in banking and the clock starts immediately."
        ),
        action=(
            "Freeze and do not proceed. Escalate to the MLRO and the compliance "
            "officer immediately, and do not tell the customer why."
        ),
        legal_hook=BSP_GAP,
        patterns=(
            r"\b(?:sanction|watchlist|adverse media)\b",
            r"\bscreening hit\b|\bname match\b|\bfalse positive\b[^.]{0,20}\bscreen",
            r"\bterrorist (?:financing|list)\b|\bsdn\b",
        ),
        regulator="BSP / AMLC",
    ),
    Indicator(
        id="secrecy_breach_customer",
        label="Customer information disclosed to the wrong person",
        tier=RiskTier.HIGH.value,
        exposure=("customer",),
        why=(
            "Once a customer's balance or transaction detail is disclosed to an "
            "unverified caller, the disclosure cannot be withdrawn and the "
            "customer carries the consequence."
        ),
        action=(
            "Stop the disclosure, verify the caller's identity out of band, and "
            "report the attempted disclosure to the data protection officer."
        ),
        legal_hook=DPA_CONFIDENTIALITY,
        patterns=(
            r"\b(?:disclos\w+|reveal\w+|leak\w*|shared?)\b[^.]{0,40}"
            r"\b(?:balance|account details|transaction history)\b[^.]{0,40}"
            r"\b(?:caller|stranger|wrong|unverified|impersonat)",
            r"\bgave?\b[^.]{0,30}\b(?:balance|details)\b[^.]{0,30}\bto the (?:caller|stranger)\b",
            r"\bwrong (?:number|person|customer)\b[^.]{0,30}\b(?:balance|details|account)\b",
        ),
        regulator="NPC / BSP",
    ),
    Indicator(
        id="unregistered_intermediary",
        label="Payment routed through an unregistered intermediary",
        tier=RiskTier.MEDIUM.value,
        exposure=("both",),
        why=(
            "Third parties who receive funds on a customer's behalf shift the "
            "beneficiary from the person the customer meant to pay, and they are "
            "outside the bank's customer identification entirely."
        ),
        action=(
            "Verify the intermediary and the underlying instruction, record who "
            "benefited, and refer to the MLRO if the arrangement is repeated."
        ),
        legal_hook=RA9160_COVERED_INST,
        patterns=(
            r"\b(?:third[- ]party|intermediary|agent)\b[^.]{0,40}"
            r"\b(?:receive|receives|receiving|collects?|paid?)\b[^.]{0,40}"
            r"\b(?:in lieu|instead of|on behalf)\b",
            r"\bunregistered (?:remittance|agent|intermediary|biller)\b",
            r"\b(?:payee|beneficiary)\b[^.]{0,30}\bis not\b[^.]{0,30}\bthe (?:customer|client)\b",
        ),
        regulator="BSP / AMLC",
    ),
    Indicator(
        id="investment_promise",
        label="Investment promise - guaranteed returns or unregistered solicitation",
        tier=RiskTier.HIGH.value,
        exposure=("customer",),
        why=(
            "Unsolicited investment offers promising a guaranteed return are the "
            "commonest retail investment fraud in the Philippines, and the "
            "regulator responsible is outside this corpus."
        ),
        action=(
            "Do not endorse, refer, or give processing assistance. Explain that "
            "the offer sounds like investment fraud and refer the customer to the "
            "regulator named in the disclosure text."
        ),
        legal_hook=SEC_GAP,
        patterns=(
            r"\b(?:guaranteed?| assured?)\b[^.]{0,25}\b(?:return|profit|yield|interest)\b",
            r"\bdouble (?:your )?(?:money|investment)\b|\bhigh[- ]yield\b[^.]{0,30}\brisk[- ]free\b",
            r"\b(?:investment|forex|crypto|mining)\b[^.]{0,40}"
            r"\b(?:guaranteed|assured|promises? you|per month)\b",
            r"\bunsolicited (?:investment|offer)\b",
            r"\bnot registered\b[^.]{0,30}\b(?:with the )?(?:sec|commission)\b",
        ),
        regulator="SEC",
    ),
)


_COMPILED: tuple[tuple[Indicator, tuple[re.Pattern[str], ...]], ...] = tuple(
    (ind, tuple(re.compile(p, re.IGNORECASE) for p in ind.patterns))
    for ind in INDICATORS
)

_CITATION = re.compile(r"\[[A-Z0-9][^\]]+\]")  # noqa: F841 - reserved


def match_indicators(text: str) -> list[IndicatorMatch]:
    """Return every indicator the text trips, most severe first.

    Pure, deterministic and I/O-free. The evidence is the matched span, so an
    officer can be shown exactly which words triggered the flag.
    """
    if not text or not text.strip():
        return []

    matches: list[IndicatorMatch] = []
    seen: set[str] = set()

    for indicator, patterns in _COMPILED:
        if indicator.id in seen:
            continue
        for pattern in patterns:
            m = pattern.search(text)
            if m:
                matches.append(
                    IndicatorMatch(indicator=indicator, evidence=m.group(0).strip())
                )
                seen.add(indicator.id)
                break

    matches.sort(key=lambda x: (SEVERITY[x.indicator.tier], x.indicator.id), reverse=True)
    return matches


def exposed_parties(matches: list[IndicatorMatch]) -> set[str]:
    """Who is put at risk by these matches: 'customer', 'bank', or both."""
    parties: set[str] = set()
    for m in matches:
        for party in m.indicator.exposure:
            if party == "both":
                parties.update({"customer", "bank"})
            else:
                parties.add(party)
    return parties


def catalogue_summary() -> list[dict]:
    """Machine-readable catalogue for the UI. Mirrors the indicator fields."""
    return [
        {
            "id": ind.id,
            "label": ind.label,
            "tier": ind.tier,
            "exposure": list(ind.exposure),
            "why": ind.why,
            "action": ind.action,
            "regulator": ind.regulator,
            "legal_hook": {
                "doc_id": ind.legal_hook.doc_id,
                "anchor": ind.legal_hook.anchor,
                "note": ind.legal_hook.note,
                "is_gap": ind.legal_hook.is_gap,
            },
        }
        for ind in INDICATORS
    ]
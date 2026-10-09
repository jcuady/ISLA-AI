ISLA AI OPERATIONAL GUIDE
Front-line and Customer-Facing Data Handling in Philippine Banking

STATUS: internal operational aid compiled by Isla AI. This is not a legal
source. It is not a statute, not a regulation, and not a bank circular. It
creates no obligation, and it must never be shown to a regulator as authority.
Its only job is to route a front-line question to the right instrument and the
right person.

HOW TO READ EACH SECTION

Every section below carries three labelled lines.

  DPA basis.        The Data Privacy Act, its IRR, or an NPC circular section that
                    makes the situation a privacy matter. These ARE indexed in this
                    system and the citation can be verified on screen.

  Binding rule.     The operational rule that decides the answer. It lives in an
                    instrument that is NOT in this corpus, usually the PCI
                    Security Standards Council's PCI DSS or Bangko Sentral ng
                    Pilipinas regulations. Treat it as a pointer, not a quote.

  If in doubt.      What to do when neither line settles it.

If the DPA basis and the binding rule ever appear to conflict, the indexed
statute and the official published instrument both outrank this document, and
this document is wrong and must be corrected.

Section 1. Payment card data under the Data Privacy Act

The rule at the counter. A card number, a card expiry date, a cardholder name,
an enrolled mobile number tied to a card, and any other identifier that ties a
person to a payment instrument are personal data about that person.

DPA basis. RA 10173 Section 3 defines personal information, and it defines
sensitive personal information as information "concerning the financial
information of a person". RA 10173 Section 13 prohibits the processing of
sensitive personal information except in the cases that section itself lists.
RA 10173 Section 25 sets the penalty for unauthorized processing of sensitive
personal information at imprisonment of three to six years and a fine of not
less than PHP 500,000 but not more than PHP 4,000,000.

Binding rule. The rules for storing and displaying card data are in PCI DSS,
which classifies the card verification value and the PIN as sensitive
authentication data that must never be stored after a transaction is
authorized. PCI DSS and the Bangko Sentral's electronic payments regulations
are not indexed in this system.

If in doubt. Treat any card credential the customer gives you as sensitive
personal information from the moment it leaves their mouth.

Section 2. Never ask for the card verification value

The rule at the counter. Do not ask a cardholder to read out the card
verification value, whether it is printed as CVV, CVV2, CVC, CVC2, CID or a
three or four digit security code. Do not ask them to spell it, type it, say
it in full, or say the first and last digit. Do not ask a cardholder to hold
the card up to a camera, and do not photograph the back of a card.

DPA basis. RA 10173 Section 11(d) requires personal information to be adequate
and not excessive in relation to the purposes for which it is collected.
Verifying a caller who already has the card in hand, or confirming a payment
that has already been made, does not require the verification value; the last
four digits of the card number and the expiry date serve that purpose. Asking
for the verification value is therefore excessive collection under an indexed
provision of the Act. RA 10173 Section 20(e) further requires the employees,
agents or representatives of a personal information controller to operate and
hold personal information under strict confidentiality. A verification value
written on a notepad, read aloud on a recorded line, or keyed into a chat
window is being held otherwise.

Binding rule. The prohibition on soliciting sensitive authentication data is
industry and supervisory practice reflected in PCI DSS and in bank card
security policy. It is not a provision of the Data Privacy Act, and this guide
does not claim it is. PCI DSS is not indexed here.

If in doubt. If a caller insists on giving you the value, decline, and escalate
to your supervisor rather than accepting it.

Section 3. Never ask for a PIN or a PIN block

The rule at the counter. Do not ask anyone for their ATM PIN, their card PIN,
their PIN block, their personal identification number, or the digits of a
one-time password that was delivered to their phone. Do not accept a PIN that
a customer volunteers without first declining and redirecting them to the
official channel.

DPA basis. RA 10173 Section 20(e) imposes strict confidentiality on the
employees, agents or representatives of a controller who handle personal
information. A PIN is a personal authentication credential and is among the
data that RA 10173 Section 25 penalises when processed without consent or
legal authorisation. NPC Circular 16-03 Section 11 expressly lists usernames,
passwords and other login data among the personal data whose compromise must
be described in a breach notification, which confirms that this system treats
login credentials as personal data rather than as anonymous operational noise.

Binding rule. PCI DSS treats the PIN block as sensitive authentication data
and prohibits its storage after authorization. Bangko Sentral regulations on
electronic payments and on consumer phishing carry the supervisory expectation
that front-line staff never solicit a PIN. Neither is indexed here.

If in doubt. A customer who offers a PIN is a customer who may be under
pressure. Follow the fraud or security team's escalation path.

Section 4. One-time passwords and verification codes

The rule at the counter. Never read back, request, confirm, or accept a one-time
password, a verification code, or an authentication code from a customer, even
when the customer insists and even when the code has already expired. If a
customer reads the code to you, stop the transaction and escalate.

DPA basis. A one-time password is a live authentication credential belonging to
a specific person. Soliciting one moves the bank toward processing personal
information for a purpose the customer did not authorize, and RA 10173
Section 12 requires a lawful basis for that processing while RA 10173 Section
13 restricts it in the case of sensitive personal information. Capturing it in
a call recording or a chat transcript also creates a stored copy of a
credential, which is precisely what the strict confidentiality duty in RA 10173
Section 20(e) exists to prevent.

Binding rule. Industry and supervisory practice prohibits front-line staff from
soliciting one-time authentication codes. PCI DSS does not index here.

If in doubt. Codes belong to the customer and to the bank's authentication
system. They are never a counterparty to a conversation.

Section 5. Passwords and online banking credentials

The rule at the counter. Do not ask for, accept, or write down a customer's
online banking password, personal email password, or the password to any
customer system. Do not ask them to read a password aloud so you can confirm
it, and do not confirm a password they read first.

DPA basis. NPC Circular 16-03 Section 11 names usernames, passwords and other
login data as personal data whose compromise must be notified. RA 10173
requires reasonable and appropriate organizational, physical and technical
measures against unlawful access and fraudulent misuse, and its paragraph (e)
extends strict confidentiality to employees, agents and representatives. An
agent who holds a customer's password is holding personal information outside
the purposes the customer authorized.

Binding rule. PCI DSS sets minimum length, complexity and storage requirements
for passwords, and prohibits their storage in clear form. That text is not
indexed in this system.

If in doubt. There is no verification task that legitimately requires a
customer's password.

Section 6. Identification documents presented at the counter

The rule at the counter. You may ask for identification when the transaction
genuinely requires it, and you may verify that the person presenting it is the
person named on it. Do not copy an identification number into free-text notes
when a structured field exists. Do not photograph an identification card into a
personal device or a chat window.

DPA basis. Identification presented at a bank counter is personal information
under RA 10173 Section 3, and where it exposes a government identifier number
it is handled as sensitive. RA 10173 Section 12 permits processing where the
data subject has consented, where processing is necessary to perform a contract
to which the data subject is party, or where the bank must comply with a legal
obligation. Identification collected for anti-money-laundering or
know-your-customer purposes rests on that last ground, which is why a bank may
lawfully ask for it even without relying on consent. NPC Circular 2022-04
requires the processing system that receives identification data to be
registered with the National Privacy Commission and the data protection officer
to be designated.

Binding rule. The Bangko Sentral's customer identification and know-your-
customer regulations set what may be requested. They are not indexed here.

If in doubt. Ask for identification only when the specific transaction needs it,
and record only what the transaction needs.

Section 7. Recording calls and transcribing them

The rule at the counter. Record only where policy requires, tell the customer
that the call is being recorded before you start, and never deliberately place
a card number, a password, or an authentication code into a recorded line. If
the customer speaks a secret during a recorded call, treat the recording as
compromised.

DPA basis. A voice recording that identifies a customer is personal information
under RA 10173 Section 3 and its processing needs a lawful basis under RA 10173
Section 12. Retention is limited by RA 10173 Section 11(f), which requires that
personal information be kept in a form which permits identification of data
subjects for no longer than is necessary for the purposes for which it was
collected. NPC Circular 2022-04
requires the call recording system to be registered as a data processing
system. NPC Circular 2023-04 governs the validity of any consent relied on to
record, including consent collected at the start of a call.

Binding rule. Call recording disclosure, retention period and consent wording
are set by Bangko Sentral regulations and by bank policy. Neither is indexed
here.

If in doubt. If you are not certain the recording is permitted, do not record.

Section 8. Consent at the front line

The rule at the counter. Explain what you are collecting, why, and for how long,
in language the customer actually understands. Do not bury consent inside terms
the customer did not read. Do not treat silence on a recorded line as consent.

DPA basis. NPC Circular 2023-04 requires consent to be freely given, specific,
informed, and unambiguous, and requires that a request for consent be
distinguishable from other terms presented alongside it. RA 10173 Section 11(a)
requires collection for specified and legitimate purposes determined and
declared before, or as soon as reasonably practicable after, collection, and
later processing only compatible with those declared purposes. RA 10173
Section 11(e) limits retention.

Binding rule. Sector advertising and marketing rules set the separate consent
wording. They are not indexed here.

If in doubt. If the customer asked a question and did not ask to be recorded,
marketing, or contacted again, that is not consent to any of those.

Section 9. Collecting only what the purpose needs

The rule at the counter. Before collecting anything, name the purpose. If you
cannot name the purpose, do not collect it. Prefer the last four digits of a
card to the whole card number. Prefer a masked or tokenised reference to a raw
number written into a free-text field.

DPA basis. RA 10173 Section 11(a) requires specified and legitimate purposes
declared before collection. RA 10173 Section 11(d) requires personal
information to be adequate and not excessive in relation to the purposes for
which it is collected. RA 10173 Section 11(c) requires accuracy and
relevance, and RA 10173 Section 11(e) limits retention to what is necessary.

Binding rule. The technical limit on how much of a card number may be stored or
displayed is in PCI DSS, which permits only the first six and last four digits
to be visible at most. PCI DSS is not indexed here.

If in doubt. If the field is not on the standard form, the data probably does
not need to be collected at all.

Section 10. Retention of call recordings, chats and notes

The rule at the counter. Keep only what the bank's retention schedule requires.
When a retention period expires, the record is destroyed, not left in an
archive for possible future use. Personal notes about a customer are subject to
the same rule as the system of record.

DPA basis. RA 10173 Section 11(e) requires retention only for as long as
necessary for the purposes for which the data was obtained, or for the
establishment, exercise or defense of legal claims, or as provided by law. RA
10173 Section 11(f) requires that information identifying data subjects be kept
no longer than necessary. The IRR requires disposal of personal information
that is no longer needed, and misusing or disposing of it carelessly carries
its own penalties.

Binding rule. The retention periods themselves are set by Bangko Sentral
regulations, by the Records Management Act, and by bank policy. They are not
indexed here.

If in doubt. If you cannot name the purpose for which a record is still being
kept, it should already have been destroyed.

Section 11. Screenshots, chat logs and note-taking

The rule at the counter. Never paste a card number, a password, or an
authentication code into a chat tool, a personal notes app, a personal
telephone, or an unapproved messaging application. Never take a screenshot of
a customer record on a personal device. Take structured notes; do not copy
values across.

DPA basis. RA 10173 Section 20(a) requires organizational, physical and
technical measures protecting personal information against accidental or
unlawful disclosure. An unapproved messaging application or a personal device
is neither an approved organisational nor an appropriate technical measure.
RA 10173 Section 20(d) requires that third parties processing on the bank's
behalf implement the same security measures.

Binding rule. PCI DSS restricts where account data may be stored and displayed.
Those controls are not indexed here.

If in doubt. If you would not put it in the system of record, do not put it in
a chat window either.

Section 12. Third parties, agents, contractors and collection agencies

The rule at the counter. Confirm before you disclose that the person on the
other end of the line is who they claim to be. Do not read out a customer's
account details to an inbound caller. Do not transfer a customer file to a
third party without the written agreement the law requires.

DPA basis. RA 10173 Section 11(a) requires the declared purpose to be specific
and legitimate. RA 10173 Section 12 lists the conditions under which processing
is permitted. The IRR on outsourcing and processing agreements requires a
written agreement between the controller and the processor covering the
processing, and the IRR makes the controller accountable for what the
processor does. RA 10173 Section 20(d) extends the security duty to third
parties processing on the bank's behalf, and Section 20(e) extends strict
confidentiality to the bank's agents and representatives.

Binding rule. Bangko Sentral outsourcing and third-party risk regulations set
the agreement and oversight requirements. They are not indexed here.

If in doubt. Take the caller's details first, call back on a verified number,
and never disclose to an unverified caller.

Section 13. When a customer has already disclosed a secret

The rule at the counter. If a customer has read a card verification value, a
PIN, a password, or an authentication code to you, do not simply carry on and
do not note it down. Stop, tell your supervisor the same day, and follow the
incident path. If the disclosure was recorded, the recording itself is now a
stored credential and must be treated as an incident.

DPA basis. NPC Circular 16-03 governs personal data breach management and
requires notification to the National Privacy Commission and to affected data
subjects within seventy-two hours of a personal data breach, subject to the
conditions that circular states. Its Section 11 requires the notification to
describe the personal data possibly involved, which expressly includes
usernames, passwords and other login data. RA 10173 Section 20(f) requires the
controller to notify the Commission and affected data subjects when sensitive
personal information or information usable to commit identity fraud is
reasonably believed to have been acquired by an unauthorized person.

Binding rule. Fraud and incident classification, customer reimbursement, and
the bank's notification decision sit with the fraud team and the data
protection officer. Their procedures are not indexed here.

If in doubt. Reporting a disclosure you were asked to hear is never the wrong
call. Concealing one is.

Section 14. Escalation path

Who to ask, in order.

- Supervisor or team lead: anything on this guide that you could not settle at
  the counter.

- The bank's data protection officer or compliance officer: anything involving
  sensitive personal information, a recorded disclosure, a third party, or a
  possible breach. NPC Circular 2022-04 requires that the controller designate a
  data protection officer for exactly this purpose.

- The bank's information security team: credentials, authentication, and
  anything involving an account takeover.

- Legal counsel: anything this guide does not cover.

This system can cite the Data Privacy Act, its IRR, and the National Privacy
Commission circulars indexed in it. It cannot cite the Bangko Sentral
regulations, the PCI Security Standards Council documents, or any bank's
internal policy, because none of those are indexed here. When an answer depends
on one of those, say so rather than guessing.

Section 15. Sources and provenance

Indexed in this system and citable on screen.

  Republic Act No. 10173, Data Privacy Act of 2012. Sections 3, 11, 12, 13,
  20 and 25.

  Implementing Rules and Regulations of RA 10173. Outsourcing and processing
  agreements, organisational, physical and technical security measures, and
  disposal.

  NPC Circular No. 16-03, Personal Data Breach Management. The seventy-two hour
  notification duty and the contents of a notification.

  NPC Circular No. 2022-04, Registration of Data Processing Systems and
  Designation of the Data Protection Officer.

  NPC Circular No. 2023-04, Guidelines on Consent.

Referenced by this guide but NOT indexed here, and therefore not verifiable
from a citation chip.

  PCI Data Security Standard, published by the PCI Security Standards Council.
  Referenced by requirement family only; no text from it is reproduced.

  Bangko Sentral ng Pilipinas regulations on electronic payments, customer
  identification, outsourcing and consumer protection. Referenced by subject
  area only, because this system does not hold the circular numbers and will
  not guess at them.

  Your bank's own card security, fraud and records retention policy.

Compiled by Isla AI for the AppBuilders PH Hackathon 2026. Version 1.0. If any
statement here conflicts with the official text of an instrument, the official
text wins.
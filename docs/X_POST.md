# Isla AI — the X / LinkedIn post

Copy from here. Every option is character-counted, not estimated.

> Tag **@cognition** and **@Devin** — the host asks for both.

---

## Option A — single post, 269 characters (safe on a free account)

```
Banks here can't send customer data to cloud AI. Isla AI is the copilot they
can still use — on-device PII redaction, fraud screening, and privacy answers
quoted from the exact section.

@cognition @Devin

github.com/jcuady/ISLA-AI

#AppBuildersPH #LocalAI #DataPrivacy
```

---

## Option B — thread, if you want the story (4 posts)

**1/4**
```
We built Isla AI for AppBuilders PH — an on-device compliance copilot for
Philippine banks.

Philippine banks are barred from sending customer data to a cloud AI vendor.
Their staff still need answers fast. Those two facts are the whole problem.
```

**2/4**
```
The catch: you can't check whether data is sensitive without first sending it.
That's not a slow network problem. That's the act you're trying to prevent.

So Isla AI runs entirely on your own hardware. No cloud call, no telemetry.
```

**3/4**
```
It does three things:
• redacts PII, then re-runs its own detector on its own output
• screens transactions for fraud and AML risk
• answers privacy law with the exact section, quoted — never from memory

And it names what it can't verify instead of inventing it.
```

**4/4**
```
The part we're most proud of: BSP and SEC circulars aren't in our corpus,
because those sites refuse our machine.

So it says so — on every relevant answer.

Built with @cognition and @Devin.
github.com/jcuady/ISLA-AI
#AppBuildersPH #LocalAI #DataPrivacy #FinTech
```

---

## LinkedIn version (3,000 char limit — use this one there)

```
We're proud to share Isla AI — our entry for the AppBuilders PH Local AI
Hackathon, in the Finance track.

Isla AI is an on-device compliance copilot for Philippine banks.

The problem is narrow and real: bank staff need privacy-law answers in seconds,
and the one fast option available to them — pasting customer data into ChatGPT —
is exactly what Philippine banks are barred from doing.

The answer isn't a better cloud model. You cannot check whether data is
sensitive without first transmitting it. So Isla AI runs on the bank's own
hardware, and does three things:

• Redacts Philippine banking PII, then re-runs its own detector over its own
  output before releasing anything. Card number, CVV and account in one message
  is a complete payment-credential compromise, so it refuses to send — a block,
  not a warning.

• Screens transactions for fraud and money-laundering risk against 20 named
  typologies, with the evidence span and the legal hook shown for every flag.

• Answers Data Privacy Act questions with the exact section the answer came
  from. Every answer is a retrieved span, never written from memory.

What we're most proud of is what it refuses to do. BSP, SEC and AMLC
circulars aren't in our corpus — those sites refuse the machine we built this on,
and RA 9160's public copy is abridged. Isla AI names each of those gaps on every
relevant answer instead of inventing a circular. A copilot that's visibly
incomplete is worth something. One that's confidently wrong is worse than none.

Measured on an AMD Ryzen 9 6900HS, CPU only: PII detection 1.0000 macro-F1,
0.00% residual leakage, citation accuracy 100%, fraud indicator recall 94.4% at
100% tier accuracy. 501 tests. Everything regenerates from the repo.

Repo: https://github.com/jcuady/ISLA-AI

Built with @cognition and @Devin.
#AppBuildersPH #LocalAI #DataPrivacy #FinTech #BuildInPublic
```

---

## Hashtags — why these

| Tag | Job |
|---|---|
| `#AppBuildersPH` | **Discovery.** This is how the host and other entrants find you. Keep it first. |
| `#LocalAI` | The track you entered. Judges filtering by track will find you. |
| `#DataPrivacy` | The actual domain. Small, high-signal audience. |
| `#FinTech` / `#BuildInPublic` | Optional reach. Drop them first if you need characters. |

Avoid: `#AI`, `#hackathon`, `#tech` — they are so saturated they surface your
post to nobody relevant and bury the real tags under noise.

---

## Before you post

- [ ] Repo link is live: <https://github.com/jcuady/ISLA-AI>
- [ ] Attach the demo video (the host asks for it in the post)
- [ ] Tag **@cognition** and **@Devin**
- [ ] Post as a **thread**, not screenshots only — the video must be visible
- [ ] Put the repo link in the **first** post, not the last
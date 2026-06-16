# Acquire.com Listing Requirements — Ghost Agency

> **Source:** Official Acquire.com Seller FAQ, curation policy, buyer due diligence checklists, and successful pre-revenue/early-stage SaaS listings.
> **Last updated:** 2026-06-16

---

## 1. HARD RULES — Non-Negotiable Gate Criteria

These are Acquire.com's **minimum requirements** to even get listed. Fail any one and your listing gets rejected by their curation team.

| # | Rule | Details | Ghost Agency Status |
|---|---|---|---|
| R1 | **SaaS business model** | Must be software-as-a-service. No brick-and-mortar, MLM, franchises, or investment-seeking listings. | ✅ Pass — AI Employee SaaS |
| R2 | **SSL-certified website** | Must have a live, HTTPS website that explains the product well. Broken sites or localhost-only = instant rejection. | ❌ FAIL — Only runs on localhost:8000 |
| R3 | **Currently operating** | The product must be live and functional. Dead products or concept-only listings are rejected. | ❌ FAIL — Not deployed to production |
| R4 | **Revenue-generating** (preferred) | Acquire.com strongly prefers revenue-generating businesses. Pre-revenue is an exception, not the norm. | ❌ FAIL — $0 MRR |
| R5 | **Pre-revenue: priced under $25,000** | If no revenue, asking price must be ≤$25K. Average pre-revenue sale is $7,500. | ⚠️ Possible — but limits exit value |
| R6 | **Pre-revenue: interesting/niche purpose** | Must solve a specific, verifiable problem. Generic tools get rejected. | ✅ Pass — AI Workforce-as-a-Service is niche |
| R7 | **Pre-revenue: has active customers** | Even free/beta users count. Zero users = almost certain rejection. | ❌ FAIL — Zero users |
| R8 | **Justifiable price multiple** | Acquire's curation team verifies your valuation makes sense. Overpriced listings get rejected. | ❌ FAIL — Can't justify any multiple at $0 MRR |
| R9 | **Verified seller identity** | Must verify email, identity, and business ownership. | ❌ Not done yet |
| R10 | **No prohibited categories** | No adult, weapons, gambling, or partial-acquisition listings. | ✅ Pass |

### Pre-Revenue Exception Criteria (All Must Be Met)

Acquire.com's own words:

> *"We don't usually list pre-revenue startups unless they meet the following criteria:*
> - *SaaS business model*
> - *Priced under $25,000*
> - *Interesting, useful, or niche purpose*
> - *Have active customers*
> - *Have a decent SSL-certified website explaining the product well"*
>
> *"Even if you meet this criteria, our curation team has the final decision."*

**Translation:** Pre-revenue is a narrow door. Most get rejected. Revenue is the real key.

---

## 2. BUYER DUE DILIGENCE — What Buyers Will Inspect

Once listed, serious buyers will conduct due diligence across 6 workstreams. Every gap reduces your sale price or kills the deal.

### 2.1 Financial Due Diligence

| What Buyer Demands | Why It Matters | Ghost Agency Status |
|---|---|---|
| P&L statement (36 months ideal, 2-3 months minimum) | Proves revenue is real and sustainable | ❌ Nothing — $0 revenue |
| MRR/ARR with month-over-month growth trend | Core SaaS valuation metric | ❌ $0 MRR |
| Churn rate (annual, target <10%) | Shows customer retention health | ❌ No customers to measure |
| LTV (Customer Lifetime Value) | Revenue per customer over their lifetime | ❌ No data |
| CAC (Customer Acquisition Cost) | How much it costs to acquire each customer | ❌ No marketing data |
| Bank statements reconciled against revenue | Verifies P&L is not fabricated | ❌ No revenue to reconcile |
| Stripe/payment processor statements | Independent verification of revenue | ❌ No Stripe connected |

### 2.2 Technical Due Diligence

| What Buyer Demands | Why It Matters | Ghost Agency Status |
|---|---|---|
| Clean, documented codebase | Buyer must maintain it post-acquisition | ✅ 91 tests, flake8 clean, black formatted |
| Architecture documentation (C4 diagrams) | Buyer needs to understand system design | ❌ No architecture docs |
| No hardcoded secrets | Security risk | ✅ .env pattern used |
| No placeholder/TODO/stub code | Signals incomplete product | ❌ Gumroad stub, metrics TODO, missing integrations |
| CI/CD pipeline | Proves deployment is repeatable | ❌ No GitHub Actions |
| Dependency audit (no known vulnerabilities) | Security and maintenance risk | ❌ No Dependabot or scanning |
| Tech debt assessment | Hidden costs post-acquisition | ⚠️ Moderate — 6/156 agents, missing squad dirs |
| Single-point-of-failure analysis | Key-person risk kills deals | ❌ Solo dev = 100% key-person risk |
| Deployment documentation | Buyer must be able to run it | ⚠️ install.sh exists, but no cloud deploy guide |
| Database migration strategy | Schema changes must be safe | ❌ No migration tooling |
| API documentation | Buyer evaluates API surface | ⚠️ FastAPI auto-docs exist, but no detailed descriptions |

### 2.3 Product Due Diligence

| What Buyer Demands | Why It Matters | Ghost Agency Status |
|---|---|---|
| Working live demo (public URL) | Buyer needs to verify product works | ❌ Localhost only |
| All features functional (no stubs) | Incomplete features = hidden work | ❌ Gumroad stub, metrics placeholder |
| User onboarding flow | First-run experience for new customers | ❌ None |
| Admin panel / dashboard | Operational control post-acquisition | ✅ Dashboard with Glass Brutalism UI |
| Feature roadmap | Growth potential | ⚠️ AGENTS.md mentions 156 agents, only 6 exist |
| Competitive analysis | Market positioning | ❌ None documented |
| Customer feedback / testimonials | Social proof | ❌ None — zero customers |

### 2.4 Transferability Due Diligence

| What Buyer Demands | Why It Matters | Ghost Agency Status |
|---|---|---|
| SOPs / operational runbooks | Buyer can run business without seller | ❌ None |
| Transferable payment processing (Stripe) | Buyer takes over revenue stream | ❌ No Stripe connected |
| Domain ownership | Asset being acquired | ❌ No custom domain |
| Infrastructure access (cloud console, DB) | Buyer needs operational control | ❌ No cloud deployment |
| Customer communication templates | Buyer can continue support | ❌ None |
| Post-sale transition plan (30 days) | Ensures smooth handoff | ❌ None |
| Founder dependency score (low = good) | High dependency = risky acquisition | ❌ 100% founder-dependent |

### 2.5 Metrics & Analytics Due Diligence

| What Buyer Demands | Why It Matters | Ghost Agency Status |
|---|---|---|
| Google Analytics (GA4) connected | Acquire requires this for verification | ❌ Not connected |
| Stripe connected to ChartMogul | Revenue metrics visible on listing | ❌ No Stripe |
| User engagement data (DAU/MAU) | Product stickiness signal | ❌ No tracking |
| Conversion funnel data | Marketing efficiency | ❌ No funnel tracking |
| Traffic sources breakdown | Revenue sustainability | ❌ No analytics |
| Real `/metrics` endpoint | Operational monitoring | ❌ Hardcoded placeholder |

### 2.6 Legal & Compliance Due Diligence

| What Buyer Demands | Why It Matters | Ghost Agency Status |
|---|---|---|
| LICENSE file | IP ownership clarity | ✅ MIT license |
| Privacy policy | Legal requirement (GDPR, CCPA) | ❌ None |
| Terms of service | Legal protection | ❌ None |
| Data processing agreement (DPA) | GDPR compliance | ❌ None |
| Cookie consent mechanism | EU legal requirement | ❌ None |
| IP ownership documentation | All code is yours to sell | ⚠️ Need to document 3rd-party deps |
| No open legal disputes | Clean acquisition | ✅ None known |

---

## 3. ACQUIRE.COM LISTING SCORECARD

Acquire.com uses an internal "Listing Scorecard" to rate your listing quality. Higher score = more buyer interest.

| Scorecard Item | Weight | Ghost Agency Status |
|---|---|---|
| Seller profile completed | Required | ❌ Not started |
| P&L uploaded | High | ❌ No P&L |
| CIM (Confidential Information Memorandum) uploaded | High | ❌ No CIM |
| Connected metrics (Stripe/ChartMogul) | High | ❌ No Stripe |
| Connected analytics (GA4) | High | ❌ No GA4 |
| Demo video uploaded | Medium | ❌ No demo video |
| Seller intro video uploaded | Medium | ❌ No intro video |
| Transition plan uploaded | Medium | ❌ No transition plan |
| Due diligence checklist provided | Medium | ❌ No DD checklist |
| Realistic asking price | Required | ⚠️ TBD — depends on revenue |

---

## 4. VALUATION BENCHMARKS

### Pre-Revenue SaaS (Ghost Agency's current category)

| Metric | Value |
|---|---|
| Average sale price | $7,500 |
| Maximum asking price | $25,000 |
| Typical multiple | N/A (no revenue to multiply) |
| Buyer interest level | Very low — most get rejected |
| Time to sell | Weeks to months, if at all |

### Early-Traction SaaS ($100-$500 MRR)

| Metric | Value |
|---|---|
| Typical valuation | 3-5x ARR |
| Asking price range | $3,600 - $30,000 |
| Buyer interest level | Moderate — thin buyer pool |
| Time to sell | 2-8 weeks |

### Growing SaaS ($500-$2K MRR)

| Metric | Value |
|---|---|
| Typical valuation | 4-6x ARR |
| Asking price range | $24,000 - $144,000 |
| Buyer interest level | Good — serious buyers engage |
| Time to sell | 2-6 weeks |

### Profitable SaaS ($2K-$5K MRR)

| Metric | Value |
|---|---|
| Typical valuation | 5-8x ARR |
| Asking price range | $120,000 - $480,000 |
| Buyer interest level | Strong — multiple LOIs likely |
| Time to sell | 1-4 weeks |

### The Revenue Multiplier Effect

| MRR | ARR | At 5x Multiple | Your Exit Price |
|---|---|---|---|
| $0 | $0 | N/A | ~$7,500 (fire sale) |
| $100/mo | $1,200 | $6,000 | ~$10,000 |
| $500/mo | $6,000 | $30,000 | ~$30,000 |
| $1,000/mo | $12,000 | $60,000 | ~$60,000 |
| $2,000/mo | $24,000 | $120,000 | ~$120,000 |
| $5,000/mo | $60,000 | $300,000 | ~$300,000 |

> **Every $100/mo in MRR adds ~$6,000 to your exit price.** Getting from $0 → $500 MRR is the difference between a $7,500 fire sale and a $30,000+ competitive acquisition.

---

## 5. WHAT ACQUIRE.COM DOES NOT LIST

| Category | Status |
|---|---|
| Brick-and-mortar businesses | ❌ Not listed |
| Franchise "opportunities" | ❌ Not listed |
| MLM / commission systems | ❌ Not listed |
| Companies seeking investments (not acquisition) | ❌ Not listed |
| Partial acquisitions | ❌ Not listed |
| Broken websites / non-functional products | ❌ Not listed |
| Adult entertainment | ❌ Not listed |
| Weapons / gambling | ❌ Not listed |
| Startups seeking funding rather than acquisition | ❌ Not listed |

---

## 6. ACQUIRE.COM FEES

| Fee Type | Amount |
|---|---|
| Listing fee | **Free** |
| Closing fee (self-service) | **6-8%** of sale price |
| Guided by Acquire (advisory, $100K+ TTM revenue) | Included in closing fee |
| Escrow fees | Paid from closing proceeds |

---

## 7. SUMMARY — Current Gap Count

| Category | Items Required | Items Met | Gap |
|---|---|---|---|
| Hard Rules (R1-R10) | 10 | 3 | **7 gaps** |
| Financial DD | 7 | 0 | **7 gaps** |
| Technical DD | 11 | 3 | **8 gaps** |
| Product DD | 7 | 1 | **6 gaps** |
| Transferability DD | 7 | 0 | **7 gaps** |
| Metrics DD | 6 | 0 | **6 gaps** |
| Legal DD | 7 | 1 | **6 gaps** |
| Listing Scorecard | 9 | 0 | **9 gaps** |
| **TOTAL** | **64** | **8** | **56 gaps** |

> **You meet 8 out of 64 requirements (12.5%).** This document is your checklist. Every item you close increases your listing quality and sale price.

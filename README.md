# The job that doesn't exist

**There is no federal occupation code for "Data Analyst."**

The U.S. Standard Occupational Classification has a code for Data Scientists
(15-2051), for Business Intelligence Analysts (15-2051.01), for Computer Systems
Analysts (15-1211), for Operations Research Analysts (15-2031). It has codes for
2,500 other things, including Hearing Aid Specialists and Gaming Dealers.

It does not have one for the job hundreds of thousands of people do, and that I
was looking for.

So I went and rebuilt the occupation from scratch — out of 1.76 million H-1B
labor condition applications and 304,892 different ways employers spell a job
title — to find out what it actually looks like.

**[&rarr; See the five charts](figures/charts.html)**  
**[&rarr; The write-up, as a page](https://marcoplam0506.github.io/analysis.html)**

---

## What the data is

Every employer who sponsors an H-1B worker must first file a Labor Condition
Application with the Department of Labor, declaring the job title, the worksite,
and the wage. Those filings are public.

- **Source:** DOL Office of Foreign Labor Certification, quarterly LCA disclosure files
- **Period:** FY2023 – FY2025 (12 quarterly files, Oct 2022 – Sep 2025)
- **Rows:** 1,760,784 certified applications after extraction
- **Wage adjustment:** BLS CPI-U, averaged over each federal fiscal year

**What this data is not.** It is not the US job market. It is the subset of jobs
an employer was willing to sponsor a visa for — which skews toward large firms,
toward tech and finance, and toward roles where domestic supply is thin. Every
finding below describes *that* population. I think it is still worth reading,
because it is one of the few sources with real job titles, real worksites, and
real salaries attached to each other. But it is not a census.

---

## First, the data had to be made usable

Three things had to be fixed before any of it could be counted.

**The files are mostly empty.** The FY2025 Q4 workbook declares 563,690 rows.
118,580 of them contain data; the other 445,109 are blank padding. Across all
twelve files: 1.8 million real rows, 4.6 million blank ones. Anything that reads
the file and calls `len(df)` is wrong by a factor of three before it starts.

**Employers filed Excel formulas into a federal disclosure.** 2,772 applications
have job titles that read `="data engineer"` — the literal text of a spreadsheet
formula, submitted and published as-is. One employer dumped its internal job-code
system into the title field: `senior systems analyst jc60`, `mgr. jc50 - software
quality assurance analysts and testers`.

**And the title field is close to unusable on its own.** 304,892 distinct spellings
across 1.76 million filings. The top 10 titles cover 14% of applications. You have
to go to the top 1,000 before you cover half. 202,291 titles — two thirds of all
distinct spellings — appear exactly once.

![title concentration](figures/charts.html)

---

## How I defined a "data role"

Since there is no occupation code to filter on, the classification had to come out
of the free text. Two rules, both deliberate:

**Whitelist, not keyword.** A naive `title.contains("analyst")` pulls in 3,881
*programmer analysts* (software developers), 3,552 *computer systems analysts*,
1,016 *QA analysts* and 638 titled `analyst - testing`. The word "analyst" mostly
does not mean a data job. So a title counts only if it matches an explicit data
pattern, and does not match an exclusion guard.

**Five buckets:** Data Analyst · Data Scientist · Data Engineer · Business
Intelligence · Data Architect.

**Explicitly excluded**, with reasons: Business Analyst (process, not data),
Financial Analyst, Market Research Analyst, Management Analyst, Systems /
Programmer / QA / Security / Network Analyst. *Business Data Analyst* and
*Business Intelligence Analyst* are kept — those are data jobs that happen to
carry a "Business" prefix.

**Seniority is parsed out separately** (`senior`, `sr.`, `lead`, `II`, `III`) so it
never affects which bucket a title lands in, and can be cross-checked against the
government's own wage-level field.

The full rule set is [`src/02_classify.py`](src/02_classify.py) — 13 exclusion
patterns and 22 inclusion patterns, each commented. 107,632 applications (6.1%)
classify as data roles. Disagree with a boundary call? The rules are 40 lines;
change one and re-run.

---

## 1. The biggest employers of data analysts are banks

| Employer | New data-analyst positions | Type |
|---|---|---|
| **Capital One** | 232 | Bank |
| Kforce | 163 | Staffing |
| EXLService | 94 | Outsourcing |
| Wells Fargo | 93 | Bank |
| Capgemini | 77 | Consulting |
| Walmart | 72 | Retail |
| Deloitte | 67 | Consulting |
| Citibank | 60 | Bank |
| Intuit | 47 | **Tech** |

Two of the top fourteen are technology companies. The rest are banks, consultancies,
outsourcing firms, staffing agencies and a retailer.

*Capital One files under two separate legal entities — Capital One Services LLC and
Capital One National Association. Counted separately, neither is first. Merged, it
is first by a wide margin.*

The geography follows the employers: New York first, Chicago second, then **McLean,
Virginia** (Capital One's headquarters), Dallas, Boston, Plano and Irving (the Texas
financial corridor), Jersey City. San Francisco is twelfth.

---

## 2. Most of these filings are not new jobs

Of the 107,632 certified data-role applications, **only 32.7% are new employment.**
The rest are visa renewals, employer transfers and amendments for people already
doing the job.

This single filter changes the headline:

| Role | Including renewals | New positions only |
|---|---|---|
| **Data Analyst** | +5.5% | **+27.8%** |
| Data Scientist | +13.2% | +17.3% |
| Data Engineer | +4.4% | +14.4% |
| Business Intelligence | −11.5% | −10.5% |
| Data Architect | −6.4% | −21.3% |

Counting every filing, Data Analyst looks like the flattest role in the family.
Counting only genuinely new positions, it is the fastest-growing one. The renewal
pool is dominated by engineers and scientists who arrived earlier and keep renewing;
they drown out the signal of what is being hired *now*.

Every number after this point uses new positions only.

---

## 3. What it pays, and where the ranges overlap

New positions, annual salaries, FY2023–FY2025 pooled:

| Role | 10th pct | Median | 90th pct |
|---|---|---|---|
| Data Scientist | $82,056 | **$126,277** | $185,000 |
| Data Architect | $79,492 | $105,746 | $160,000 |
| Data Engineer | $75,000 | $100,000 | $145,600 |
| Business Intelligence | $70,000 | $92,560 | $135,000 |
| Data Analyst | $65,000 | $87,152 | **$125,117** |

**A top-decile Data Analyst earns what a median Data Scientist earns.** The medians
suggest two different jobs; the distributions overlap heavily. Which title you hold
matters less than where you sit inside it.

---

## 4. Nobody got a raise

Inflation over the period was **5.86%** (CPI-U, fiscal-year average). In 2025
dollars, every data role's median new-position salary fell:

| Role | FY2023 (real) | FY2025 (real) | Change |
|---|---|---|---|
| Data Scientist | $132,322 | $130,000 | −1.8% |
| Data Engineer | $105,116 | $100,000 | −4.9% |
| Data Analyst | $94,213 | $86,472 | **−8.2%** |
| Data Architect | $114,192 | $104,416 | −8.6% |
| Business Intelligence | $104,031 | $92,050 | **−11.5%** |

Data Analyst is the fastest-growing data role by new positions and the second-worst
by real pay. More jobs, less money — the signature of a role being commoditized.

---

## 5. The real split is seniority, not job title

The obvious objection to the wage finding is composition: maybe nobody took a pay
cut, and the mix simply shifted junior. The LCA data lets you test that, because
the government assigns each position a prevailing-wage level from I to IV.

The mix did shift, sharply:

**Share of new Data Analyst positions, by level**

| | Level I | II | III | IV |
|---|---|---|---|---|
| FY2023 | 37.8% | 48.2% | 9.7% | 4.3% |
| FY2025 | **49.4%** | 40.9% | 7.3% | 2.4% |

Nearly half of new data-analyst jobs are now entry-level, up from just over a third.
Senior positions (III + IV) shrank from 14.0% to 9.7%. Business Intelligence shows
the same pattern, worse. **Data Scientist does not** — its level mix barely moved,
which rules out "this is just what happened to the whole industry."

But controlling for level does not make the wage decline disappear. It relocates it:

**Real median wage change by role and level, FY2023 → FY2025**

| | Level I | II | III | IV |
|---|---|---|---|---|
| Data Analyst | −7.5% | −3.9% | **+6.8%** | −1.3% |
| Data Scientist | −13.0% | −2.1% | +2.4% | **+8.6%** |
| Data Engineer | −9.9% | −1.1% | +1.9% | **+18.9%** |
| Business Intelligence | −11.1% | −6.7% | −0.3% | **+5.8%** |

Every row is the same gradient. Entry-level real pay fell across **every** data role.
Senior pay held or rose across almost every one. Data Engineer Level IV gained 18.9%
in real terms while Data Engineer Level I lost 9.9%.

So the finding is not that Data Analyst is a bad job. It is that the data profession
is stratifying by seniority, and the title you carry is a weaker predictor of your
outcome than the level you sit at. The entry floor is widening and getting cheaper;
the senior tier is narrowing and getting more expensive.

*Data Architect cells have 24–114 observations each and should not be read on their
own. All other cells have 249–5,907.*

---

## What I think this means

**If you are hiring:** the shortage is not in people who can do analysis. It is in
people who can be trusted at Level III. That tier shrank while its price went up.

**If you are entering the field:** the growth is real, and it is almost entirely in
the part of the market that is getting cheaper every year. The goal is not to get
a data analyst job. The goal is to stop being a Level I quickly.

> *Author's note — I am transitioning into this field, which means the data says I
> would enter at exactly the level with the worst conditions. I considered leaving
> this paragraph out. It is the most useful thing the analysis told me, so it stays.*

---

## Limitations

1. **H-1B is not the labor market.** It is visa-sponsored hiring: larger employers,
   tech and finance weighted, domestic-supply-constrained roles. Findings do not
   generalize to all US hiring without that caveat attached.
2. **Wages are offers, not earnings.** `WAGE_RATE_OF_PAY_FROM` is the floor the
   employer commits to, not what the person was paid. It is a consistent measure
   across years, which is what the trend needs, but it is not take-home pay.
3. **Classification is a judgment call.** Reasonable people would draw the Business
   Analyst line differently. 8,297 applications titled simply `analyst` carry too
   little information to classify and are excluded rather than guessed at.
4. **One field is missing in one quarter.** FY2025 Q1 has no `H_1B_DEPENDENT`
   column — a schema change between releases. Any analysis using that flag must
   handle the gap.
5. **Three years is short.** FY2023 begins after the 2022 tech contraction had
   started. A longer window would be better; it would also drag in COVID-era
   distortion that needs its own explanation.

---

## Reproducing this

```bash
pip install pandas openpyxl
python src/01_extract.py     # downloads 12 quarterly files (~1 GB), keeps ~84 MB
python src/03_analyze.py     # prints every number in this README
```

| File | What it does |
|---|---|
| [`src/01_extract.py`](src/01_extract.py) | Downloads each quarter, streams it, keeps 28 of 98 columns and certified rows only, deletes the source file |
| [`src/02_classify.py`](src/02_classify.py) | Normalizes job titles and classifies them into roles. The rules live here |
| [`src/03_analyze.py`](src/03_analyze.py) | Produces every figure in this README and writes `data/chartdata.json` |
| [`figures/charts.html`](figures/charts.html) | The five charts, with hover values and a data table under each |

Raw DOL workbooks are deleted after extraction and the 84 MB intermediate is not
committed — `01_extract.py` rebuilds both from the source URLs.

---

*Data: U.S. Department of Labor, Office of Foreign Labor Certification (LCA
disclosure, FY2023–FY2025). Inflation: U.S. Bureau of Labor Statistics, CPI-U.*

"""
分析：从已归类的 LCA 记录里算出 README 中引用的每一个数字。

输入  lca_certified.csv.gz   （01_extract.py 产出）
      cpi_fy.json            （BLS CPI-U，本脚本可重新拉取）
输出  data/chartdata.json    （图表数据）
      stdout                 （README 引用的全部数字，可逐条核对）

跑法  python src/03_analyze.py
"""
import json
import os
import re
import sys
import urllib.request

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib
classify_mod = importlib.import_module("02_classify")
classify = classify_mod.classify

sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 200)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_CSV = os.environ.get("LCA_CSV", "lca_certified.csv.gz")
CPI_JSON = os.path.join(ROOT, "data", "cpi_fy.json")
OUT_JSON = os.path.join(ROOT, "data", "chartdata.json")

LABEL = {
    "data_analyst": "Data Analyst",
    "data_scientist": "Data Scientist",
    "data_engineer": "Data Engineer",
    "business_intelligence": "Business Intelligence",
    "data_architect": "Data Architect",
}
ORDER = list(LABEL)


# --------------------------------------------------------------- CPI

def fiscal_year_cpi():
    """BLS CPI-U 全项目，按联邦财年（上年10月至本年9月）取平均。"""
    if os.path.exists(CPI_JSON):
        return {f"FY{k}": v for k, v in json.load(open(CPI_JSON)).items()}
    req = urllib.request.Request(
        "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        data=json.dumps({"seriesid": ["CUUR0000SA0"],
                         "startyear": "2022", "endyear": "2026"}).encode(),
        headers={"Content-Type": "application/json"})
    raw = json.load(urllib.request.urlopen(req, timeout=60))
    by = {}
    for row in raw["Results"]["series"][0]["data"]:
        if not row["period"].startswith("M"):
            continue
        try:
            by.setdefault(row["year"], {})[int(row["period"][1:])] = float(row["value"])
        except (ValueError, TypeError):
            continue          # 未发布的月份返回 "-"
    fy = {}
    for y in (2023, 2024, 2025):
        months = ([by.get(str(y - 1), {}).get(m) for m in (10, 11, 12)]
                  + [by.get(str(y), {}).get(m) for m in range(1, 10)])
        months = [v for v in months if v is not None]
        if len(months) >= 10:
            fy[y] = sum(months) / len(months)
    os.makedirs(os.path.dirname(CPI_JSON), exist_ok=True)
    json.dump({str(k): v for k, v in fy.items()}, open(CPI_JSON, "w"))
    return {f"FY{k}": v for k, v in fy.items()}


# --------------------------------------------------------------- 载入与归类

def load():
    df = pd.read_csv(SRC_CSV, dtype=str)
    # 只对不重复标题跑分类再映射回全表：30 万 unique vs 176 万行
    titles = df["JOB_TITLE"].fillna("")
    res = {t: classify(t) for t in titles.unique()}
    df["ROLE"] = titles.map(lambda t: res[t][0])
    df["EXCL"] = titles.map(lambda t: res[t][1])
    for c in ("NEW_EMPLOYMENT", "WAGE_RATE_OF_PAY_FROM"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def canon_employer(s):
    """合并同一家公司的法人实体变体。Capital One 用两个实体分别申请。"""
    s = re.sub(r"[.,]", "", str(s).upper()).strip()
    s = re.sub(r"\s+(INC|LLC|LP|LLP|CORP|CORPORATION|CO|NA|NATIONAL ASSOCIATION"
               r"|SERVICES?|USA|US)\b", "", s).strip()
    return re.sub(r"\s+", " ", s)


# --------------------------------------------------------------- main

def main():
    cpi = fiscal_year_cpi()
    base = cpi["FY2025"]
    df = load()

    d = df[df["ROLE"].notna()].copy()
    d["IS_NEW"] = d["NEW_EMPLOYMENT"].fillna(0) > 0
    new = d[d["IS_NEW"]]
    wage = new[(new["WAGE_UNIT_OF_PAY"] == "Year")
               & new["WAGE_RATE_OF_PAY_FROM"].between(30_000, 600_000)].copy()
    wage["W_REAL"] = (wage["WAGE_RATE_OF_PAY_FROM"]
                      * wage["FISCAL_YEAR"].map(lambda f: base / cpi[f]))

    print(f"已认证记录      {len(df):,}")
    print(f"判定为数据岗    {len(d):,}  ({len(d)/len(df)*100:.2f}%)")
    print(f"其中新增岗位    {len(new):,}  ({len(new)/len(d)*100:.1f}%)")
    print(f"薪资分析样本    {len(wage):,}")
    print(f"FY2023→FY2025 累计通胀  {(cpi['FY2025']/cpi['FY2023']-1)*100:.2f}%\n")

    out = {"meta": {
        "certified_total": len(df), "data_roles": len(d),
        "new_positions": len(new), "wage_sample": len(wage),
        "cpi_fy2023_to_fy2025_pct": round((cpi["FY2025"] / cpi["FY2023"] - 1) * 100, 2)}}

    # 构成
    vc = d["ROLE"].value_counts()
    out["composition"] = [{"role": LABEL[r], "n": int(vc[r]),
                           "pct": round(vc[r] / len(d) * 100, 1)} for r in vc.index]

    # 增长：含续签 vs 只看新增
    ct_all = pd.crosstab(d["FISCAL_YEAR"], d["ROLE"])
    ct_new = pd.crosstab(new["FISCAL_YEAR"], new["ROLE"])
    out["growth"] = [{
        "role": LABEL[r],
        "all_pct": round((ct_all.loc["FY2025", r] / ct_all.loc["FY2023", r] - 1) * 100, 1),
        "new_pct": round((ct_new.loc["FY2025", r] / ct_new.loc["FY2023", r] - 1) * 100, 1),
    } for r in ORDER]
    print("增长（含续签 / 只看新增）")
    for g in out["growth"]:
        print(f"  {g['role']:<24} {g['all_pct']:>+6.1f}%   {g['new_pct']:>+6.1f}%")

    # 实际薪资
    pv = wage.pivot_table(index="ROLE", columns="FISCAL_YEAR", values="W_REAL", aggfunc="median")
    out["realwage"] = [{"role": LABEL[r], "fy2023": int(pv.loc[r, "FY2023"]),
                        "fy2025": int(pv.loc[r, "FY2025"]),
                        "pct": round((pv.loc[r, "FY2025"] / pv.loc[r, "FY2023"] - 1) * 100, 1)}
                       for r in ORDER]
    print("\n实际薪资中位数（2025 年美元）")
    for w in out["realwage"]:
        print(f"  {w['role']:<24} ${w['fy2023']:>7,} → ${w['fy2025']:>7,}  {w['pct']:>+5.1f}%")

    # 职级结构
    lv = wage[wage["PW_WAGE_LEVEL"].isin(["I", "II", "III", "IV"])]
    out["levels"] = {}
    for r in ("data_analyst", "business_intelligence", "data_scientist"):
        sub = lv[lv["ROLE"] == r]
        t = pd.crosstab(sub["FISCAL_YEAR"], sub["PW_WAGE_LEVEL"], normalize="index") * 100
        out["levels"][LABEL[r]] = [
            {"fy": fy.replace("FY", ""), **{L: round(t.loc[fy, L], 1) for L in "I II III IV".split()}}
            for fy in ("FY2023", "FY2024", "FY2025")]

    # 热力图：角色 × 职级 的实际薪资变化
    out["heatmap"] = []
    print("\n同职级内实际薪资变化")
    for r in ORDER:
        sub = lv[lv["ROLE"] == r]
        p = sub.pivot_table(index="PW_WAGE_LEVEL", columns="FISCAL_YEAR",
                            values="W_REAL", aggfunc="median")
        row = {"role": LABEL[r]}
        cells = []
        for L in "I II III IV".split():
            try:
                row[L] = round((p.loc[L, "FY2025"] / p.loc[L, "FY2023"] - 1) * 100, 1)
                row[L + "_n"] = int((sub["PW_WAGE_LEVEL"] == L).sum())
            except Exception:
                row[L], row[L + "_n"] = None, 0
            cells.append(f"{L}:{row[L]:>+6}%(n={row[L+'_n']})" if row[L] is not None else f"{L}: --")
        out["heatmap"].append(row)
        print(f"  {LABEL[r]:<24} " + "  ".join(cells))

    # 雇主（合并法人实体）
    da = new[new["ROLE"] == "data_analyst"].copy()
    da["EMP"] = da["EMPLOYER_NAME"].map(canon_employer)
    KIND = {"KFORCE": "派遣", "CAPITAL ONE": "银行", "EXLSERVICECOM": "外包",
            "CAPGEMINI AMERICA": "咨询", "WELLS FARGO BANK": "银行",
            "WAL-MART ASSOCIATES": "零售", "DELOITTE & TOUCHE": "咨询",
            "SOLSTICE SOLUTIONS": "外包", "CITIBANK": "银行", "INTUIT": "科技",
            "ZS ASSOCIATES": "咨询", "COGNIZANT TECHNOLOGY SOLUTIONS": "外包",
            "JPMORGAN CHASE BANK": "银行", "AMAZONCOM": "科技",
            "TATA CONSULTANCY": "外包", "INFOSYS LIMITED": "外包",
            "ACCENTURE": "咨询", "HCL AMERICA": "外包"}
    out["employers"] = [{"name": e.title(), "n": int(n), "kind": KIND.get(e, "其他")}
                        for e, n in da["EMP"].value_counts().head(14).items()]

    # 地理
    out["geo"] = {}
    for r in ("data_analyst", "data_scientist", "data_engineer", "business_intelligence"):
        s = new[new["ROLE"] == r]["WORKSITE_CITY"].str.title().value_counts()
        out["geo"][LABEL[r]] = [{"city": c, "n": int(n), "pct": round(n / s.sum() * 100, 1)}
                                for c, n in s.head(12).items()]

    # 薪资分布
    out["dist"] = []
    for r in ("data_scientist", "data_engineer", "data_architect",
              "business_intelligence", "data_analyst"):
        w = wage[wage["ROLE"] == r]["WAGE_RATE_OF_PAY_FROM"]
        if len(w) < 100:
            continue
        out["dist"].append({"role": LABEL[r], "n": int(len(w)),
                            **{k: int(w.quantile(q)) for k, q in
                               (("p10", .10), ("p25", .25), ("p50", .50),
                                ("p75", .75), ("p90", .90))}})

    # 职位名集中度
    t = df["JOB_TITLE"].fillna("").str.strip().str.lower()
    vc_t = t.value_counts()
    pts = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000,
           10000, 25000, 50000, 100000, len(vc_t)]
    out["titles"] = {
        "unique": int(len(vc_t)), "total": int(len(t)),
        "once": int((vc_t == 1).sum()),
        "once_share": round((vc_t == 1).sum() / len(t) * 100, 1),
        "curve": [{"k": int(k), "pct": round(vc_t.head(k).sum() / len(t) * 100, 1)} for k in pts]}
    print(f"\n不重复职位名 {len(vc_t):,} 种；只出现一次的 {(vc_t==1).sum():,} 种")

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n已写出 {OUT_JSON}")


if __name__ == "__main__":
    main()

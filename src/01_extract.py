"""
H-1B LCA 披露数据 ETL
来源: 美国劳工部 OFLC, FY2023-FY2025 季度文件
做法: 逐季下载 -> 流式读取 -> 只留需要的列 -> 只留已认证 -> 追加写出 -> 删除原始 xlsx
"""
import os, sys, csv, gzip, time, urllib.request
import openpyxl

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://www.dol.gov/sites/dolgov/files/ETA/oflc/pdfs"
OUT = "lca_certified.csv.gz"
RAW = "lca"
YEARS = [2023, 2024, 2025]
QUARTERS = [1, 2, 3, 4]

KEEP = [
    "CASE_NUMBER", "CASE_STATUS", "RECEIVED_DATE", "DECISION_DATE", "VISA_CLASS",
    "JOB_TITLE", "SOC_CODE", "SOC_TITLE", "FULL_TIME_POSITION", "BEGIN_DATE",
    "TOTAL_WORKER_POSITIONS", "NEW_EMPLOYMENT", "CONTINUED_EMPLOYMENT", "CHANGE_EMPLOYER",
    "EMPLOYER_NAME", "EMPLOYER_STATE", "NAICS_CODE",
    "WORKSITE_CITY", "WORKSITE_STATE", "WORKSITE_POSTAL_CODE",
    "WAGE_RATE_OF_PAY_FROM", "WAGE_RATE_OF_PAY_TO", "WAGE_UNIT_OF_PAY",
    "PREVAILING_WAGE", "PW_UNIT_OF_PAY", "PW_WAGE_LEVEL",
    "H_1B_DEPENDENT", "TOTAL_WORKSITE_LOCATIONS",
]
# 保留已认证与"认证后撤回"——后者也代表雇主确实提出过需求，是否计入留给分析阶段决定
STATUS_KEEP = {"Certified", "Certified - Withdrawn"}

os.makedirs(RAW, exist_ok=True)


def fetch(year, q):
    name = f"LCA_Disclosure_Data_FY{year}_Q{q}.xlsx"
    path = os.path.join(RAW, f"FY{year}_Q{q}.xlsx")
    if os.path.exists(path) and os.path.getsize(path) > 1_000_000:
        return path
    url = f"{BASE}/{name}"
    t = time.time()
    try:
        urllib.request.urlretrieve(url, path)
    except Exception as e:
        print(f"  [下载失败] FY{year} Q{q}: {e}", flush=True)
        return None
    mb = os.path.getsize(path) / 1048576
    print(f"  下载完成 FY{year} Q{q}  {mb:.1f} MB  {time.time()-t:.0f}s", flush=True)
    return path


def extract(path, writer, year, q):
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb[wb.sheetnames[0]]
    it = ws.iter_rows(values_only=True)
    hdr = list(next(it))
    missing = [c for c in KEEP if c not in hdr]
    if missing:
        print(f"  [字段缺失] FY{year} Q{q}: {missing}", flush=True)
    idx = [hdr.index(c) if c in hdr else None for c in KEEP]
    si = hdr.index("CASE_STATUS")
    kept = seen = blank = 0
    for r in it:
        if r[si] is None:
            blank += 1
            continue
        seen += 1
        if r[si] not in STATUS_KEEP:
            continue
        row = [(r[i] if i is not None else None) for i in idx]
        row = [(v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else v) for v in row]
        writer.writerow(row + [f"FY{year}", f"Q{q}"])
        kept += 1
    wb.close()
    print(f"  FY{year} Q{q}: 实际 {seen} 行, 空白 {blank} 行, 保留已认证 {kept} 行", flush=True)
    return seen, kept, blank


def main():
    first = not os.path.exists(OUT)
    mode = "wt" if first else "at"
    total_kept = total_seen = total_blank = 0
    with gzip.open(OUT, mode, encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if first:
            w.writerow(KEEP + ["FISCAL_YEAR", "FISCAL_QUARTER"])
        for y in YEARS:
            for q in QUARTERS:
                p = fetch(y, q)
                if not p:
                    continue
                try:
                    s, k, b = extract(p, w, y, q)
                    total_seen += s; total_kept += k; total_blank += b
                except Exception as e:
                    print(f"  [解析失败] FY{y} Q{q}: {e}", flush=True)
                finally:
                    try:
                        os.remove(p)   # 处理完即删，控制磁盘占用
                    except OSError:
                        pass
    print(f"\n完成。真实行数 {total_seen}, 空白填充 {total_blank}, 已认证保留 {total_kept}", flush=True)
    print(f"输出: {OUT}  ({os.path.getsize(OUT)/1048576:.1f} MB)", flush=True)


if __name__ == "__main__":
    main()

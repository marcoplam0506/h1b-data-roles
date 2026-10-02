"""
从 LCA 的自由文本 JOB_TITLE 里重建「数据岗」。

为什么需要这一步：美国标准职业分类(SOC)里没有 Data Analyst 这个编号，
所以无法用 SOC_CODE 筛选，只能从雇主自己填的职位名里认。

设计原则：
1. 先归一化（去掉 Excel 公式残留、内部编码、职级词），再匹配。
2. 采用「白名单 + 排除守卫」：必须命中某个数据岗模式，且不命中排除模式，才算。
   不采用「含 analyst 就算」——数据显示这会把大量软件/测试岗算进来。
3. 职级单独抽取，不参与归类。
4. 所有规则、命中量、以及被排除的样本全部输出，供复核。
"""
import re

# ---------------------------------------------------------------- 归一化

_QUOTED = re.compile(r'^=?"(.*)"$')          # ="data engineer"  ← 雇主填表时的 Excel 公式残留
_JOBCODE = re.compile(r"\b[a-z]{1,3}\d{2,}\b")  # jc60 / jc50 等某雇主的内部职位编码
_LEVEL_TAIL = re.compile(
    r"[\s,\-–—]*\b("
    r"i{1,3}v?|iv|v|vi{0,3}"                 # 罗马数字 I..VIII
    r"|[1-5]"                                # 阿拉伯数字级别
    r"|level\s*[1-5ivx]+"
    r")\b\s*$", re.I)
_SENIORITY = re.compile(
    r"\b(senior|sr\.?|junior|jr\.?|lead|principal|staff|chief|head|"
    r"associate|assistant|entry[\s\-]?level|intern|manager|mgr\.?|director|vp)\b", re.I)
_PUNCT = re.compile(r"[^a-z0-9\s/&+.\-]")
_WS = re.compile(r"\s+")


def normalize(raw):
    """返回 (核心职位名, 职级词列表, 级别标记)。"""
    if not isinstance(raw, str):
        return "", [], ""
    s = raw.strip()
    m = _QUOTED.match(s)
    if m:
        s = m.group(1)                        # 剥掉 ="..." 外壳
    s = s.lower().strip()
    s = _JOBCODE.sub(" ", s)                  # 去内部编码
    s = _PUNCT.sub(" ", s)
    s = _WS.sub(" ", s).strip()

    level = ""
    lm = _LEVEL_TAIL.search(s)
    if lm:
        level = lm.group(1).strip()
        s = s[:lm.start()].strip()

    seniority = [w.lower().rstrip(".") for w in _SENIORITY.findall(s)]
    core = _SENIORITY.sub(" ", s)
    core = _WS.sub(" ", core).strip()
    core = core.strip(" .,-/&+")          # 去掉职级词剥离后遗留的孤立标点，如 "sr." 的句点
    core = _WS.sub(" ", core).strip()
    return core, seniority, level


# ---------------------------------------------------------------- 排除守卫
# 命中这些 = 不是数据岗，即使标题里有 analyst / data 之类的词。
EXCLUDE = [
    (r"\bprogrammer\s+analyst\b",              "软件开发"),
    (r"\b(computer\s+)?systems?\s+analyst\b",  "系统分析"),
    (r"\bbusiness\s+systems?\s+analyst\b",     "系统分析"),
    (r"\b(qa|quality\s+assurance)\b",          "测试"),
    (r"\btest(ing)?\s+analyst\b",              "测试"),
    (r"\banalyst\s*[\-–]\s*testing\b",         "测试"),
    (r"\bsoftware\s+(developer|engineer)\b",   "软件开发"),
    (r"\bfinancial\s+analyst\b",               "金融（按 BA 同一逻辑排除）"),
    (r"\bmarket\s+research\s+analyst\b",       "市场研究（按 BA 同一逻辑排除）"),
    (r"\bmanagement\s+analyst\b",              "管理咨询"),
    (r"\bnetwork\s+analyst\b",                 "网络运维"),
    (r"\bsecurity\s+analyst\b",                "信息安全"),
    (r"\bhelp\s*desk\b|\bsupport\s+analyst\b", "IT 支持"),
]
EXCLUDE = [(re.compile(p), why) for p, why in EXCLUDE]

# ---------------------------------------------------------------- 数据岗白名单
# 顺序有意义：先匹配更具体的模式。
BUCKETS = [
    ("data_engineer", [
        r"\bdata\s+engineer(ing)?\b",
        r"\banalytics\s+engineer\b",
        r"\bbig\s+data\s+engineer\b",
        r"\betl\s+(developer|engineer)\b",
        r"\bdata\s+(pipeline|platform)\s+engineer\b",
    ]),
    ("data_scientist", [
        r"\bdata\s+scien(ce|tist)\b",
        r"\bmachine\s+learning\s+(engineer|scientist)\b",
        r"\bml\s+(engineer|scientist)\b",
        r"\bapplied\s+scientist\b",
        r"\bresearch\s+scientist\s*[,\-]?\s*(data|ml|machine)\b",
    ]),
    ("business_intelligence", [
        r"\bbusiness\s+intelligence\b",
        r"\bbi\s+(analyst|developer|engineer|consultant|architect)\b",
    ]),
    ("data_architect", [
        r"\bdata\s+architect\b",
        r"\bdata\s+model(l)?er\b",
    ]),
    ("data_analyst", [
        r"\bdata\s+analyst\b",
        r"\bdata\s+analytics\b",
        r"\banalytics\s+analyst\b",
        r"\bbusiness\s+data\s+analyst\b",
        r"\bquantitative\s+analyst\b",
        r"\breporting\s+analyst\b",
        r"\banalytics\s+(specialist|consultant)\b",
    ]),
]
BUCKETS = [(name, [re.compile(p) for p in pats]) for name, pats in BUCKETS]


def classify(raw):
    """返回 (bucket 或 None, 排除原因 或 None, 核心名, 职级, 级别)。"""
    core, seniority, level = normalize(raw)
    if not core:
        return None, "空标题", core, seniority, level

    # 白名单优先于排除守卫：
    # "business data analyst" 应归为数据岗，不该被 business analyst 规则误杀。
    hit = None
    for name, pats in BUCKETS:
        if any(p.search(core) for p in pats):
            hit = name
            break

    for pat, why in EXCLUDE:
        if pat.search(core):
            # 命中排除；只有当白名单命中的是更具体的数据岗模式时才保留
            if hit and not re.search(r"\bsystems?\s+analyst\b|\bprogrammer\b|\bqa\b", core):
                break
            return None, why, core, seniority, level

    if hit:
        return hit, None, core, seniority, level

    # 兜底：纯 "analyst" 无修饰词，无法判断，单独标记供人工复核
    if re.fullmatch(r"analyst", core):
        return None, "裸 analyst，信息不足", core, seniority, level
    return None, None, core, seniority, level

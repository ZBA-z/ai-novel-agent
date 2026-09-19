# -*- coding: utf-8 -*-
"""
交付集自洽性校验器（给维护者用，不属于运行时依赖）

检查项：
  C1 文件引用      — 形如 `NN_xxx.md` / 内核文件 NN 的引用是否有对应文件
  C2 章节引用      — 形如 `xxx.md` §X 的引用，被引文件内是否真有该序号的标题
  C3 表格列数      — 每张 Markdown 表格的列数是否与表头一致
  C4 围栏配平      — 代码围栏 ``` 是否成对
  C5 占位符越界    — 规范类文件（非模板）里是否混入了 {{变量}}
  C6 关键数字      — 同一口径在不同文件里的取值是否一致（防"改了内容忘改计数"）
        并且**上报覆盖数**：0 处匹配 = 检查未生效；仅 1 处 = 无法交叉验证。
        这两者都会报 WARN，**不允许用 PASS 掩盖"没检查"**。

用法：
  python tools/check-bundle.py            # 检查并输出摘要
  python tools/check-bundle.py --verbose  # 附带 INFO 与每项断言的覆盖分布

退出码：0 = 无 FAIL；1 = 有 FAIL

设计边界：这是**防回归网，不是正确性证明**。
         它只检查可机械判定的东西，「内容写得对不对」不在它的能力范围内。
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONTENT_DIRS = ["10_内核", "20_人格", "30_台账"]

# 交付集外的资产：引用它们不算死链，但列出来供人工确认对方确实存在
EXTERNAL_HINTS = [
    "fanqie-blockbuster-forge", "multi-model-pipeline", "chapter-ops",
    "character-dna", "compliance-guide", "de-ai-guide", "continuity-system",
    "emotion-curve", "chapter-outline", "edge-cases", "model-adaptation",
    "humanizer", "libai", "write", "风格库", "books", "新书创作",
]

# 本交付集**本身就是模板集**：这些文件里的 {{变量}} 是设计内容，不是"没填完"
PLACEHOLDER_OK = {
    "01_项目卡模板.md", "04_交接物契约.md", "05_项目目录模板.md",
    "07_角色卡与状态快照模板.md",
    "10_选品人格_Scout.md", "20_作家人格_Author.md", "30_读者人格_Reader.md",
}

# 关键数字断言：同一口径在不同文件里出现的值必须一致
KEY_NUMBERS = [
    ("单章字数区间", re.compile(r"2200\s*[–\-~]\s*3000")),
    ("台账字段数", re.compile(r"字段（\*\*(\d+)\s*个\*\*")),
    ("状态必填字段数", re.compile(r"(\d+)\s*个必填字段")),
    ("闸门三态数", re.compile(r"闸门三态（(\d+)\s*个取值")),
    ("项目目录数", re.compile(r"\*\*(\d+)\s*个目录\*\*")),
    ("H 契约条数", re.compile(r"（共\s*(\d+)\s*条）")),
]


def collect_files():
    out = []
    for d in CONTENT_DIRS:
        p = os.path.join(ROOT, d)
        if not os.path.isdir(p):
            continue
        for n in sorted(os.listdir(p)):
            if n.endswith(".md"):
                out.append(os.path.join(p, n))
    return out


def load(path):
    return io.open(path, encoding="utf-8").read()


def strip_fences(text):
    """剥掉代码围栏内的内容，避免把示例当断言。"""
    out, infence = [], False
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            infence = not infence
            continue
        if not infence:
            out.append(line)
    return "\n".join(out)


NORM = {"0": "〇", "零": "〇"}


def norm_sec(s):
    return NORM.get(s, s)


def section_index(text):
    return {m.group(1) for m in re.finditer(r"§\s*([〇零一二三四五六七八九十百\d]+)", text)}


# ---------- C1 / C2：引用检查 ----------

def check_refs(files):
    res, info = [], []
    all_names = {os.path.basename(f) for f in files}
    secmap = {os.path.basename(f): section_index(strip_fences(load(f))) for f in files}
    dead_file, dead_sec, external = [], [], []

    for f in files:
        base = os.path.basename(f)
        raw_nf = strip_fences(load(f))

        for m in re.finditer(r"`([A-Za-z0-9_\-]+\.md)`", raw_nf):
            name = m.group(1)
            if name in all_names:
                continue
            if any(h in name for h in EXTERNAL_HINTS):
                external.append((base, name))
            else:
                dead_file.append((base, name))

        for m in re.finditer(r"内核文件?\s*(\d+)", raw_nf):
            num = m.group(1)
            if not [n for n in all_names if n.startswith(num.zfill(2) + "_")]:
                dead_file.append((base, "内核文件 %s（无匹配）" % num))

        for m in re.finditer(r"`([A-Za-z0-9_\-]+\.md)`\s*§\s*([〇零一二三四五六七八九十百\d]+)", raw_nf):
            name, sec = m.group(1), norm_sec(m.group(2))
            if name in secmap and sec not in secmap[name]:
                dead_sec.append((base, "%s §%s" % (name, sec)))

    res.append(("C1 文件引用", dead_file, "%d 处死链" % len(dead_file)))
    res.append(("C2 章节引用", dead_sec, "%d 处指向不存在的小节" % len(dead_sec)))
    info.append(("C1b 外部引用（信息级·不算错）", external,
                 "%d 处指向交付集外资产，需人工确认对方确实存在" % len(external)))
    return res, info, len(dead_file) + len(dead_sec)


# ---------- C3 / C4：格式检查 ----------

def check_format(files):
    bad_tbl, bad_fence = [], []
    for f in files:
        base = os.path.basename(f)
        lines = load(f).split("\n")
        n_fence = sum(1 for l in lines if l.strip().startswith("```"))
        if n_fence % 2 != 0:
            bad_fence.append((base, "``` 出现 %d 次（奇数）" % n_fence))

        infence, i = False, 0
        while i < len(lines):
            l = lines[i]
            if l.strip().startswith("```"):
                infence = not infence
                i += 1
                continue
            if not infence and l.strip().startswith("|") and i + 1 < len(lines) \
                    and re.match(r"^\s*\|[\s:\-\|]+\|\s*$", lines[i + 1]):
                hdr = l.count("|") - 1
                j = i + 2
                while j < len(lines) and lines[j].strip().startswith("|"):
                    c = lines[j].count("|") - 1
                    if c != hdr:
                        bad_tbl.append((base, "第 %d 行：%d 列 vs 表头 %d 列" % (j + 1, c, hdr)))
                    j += 1
                i = j
                continue
            i += 1

    return [("C3 表格列数", bad_tbl, "%d 行列数不匹配" % len(bad_tbl)),
            ("C4 围栏配平", bad_fence, "%d 个文件围栏未配平" % len(bad_fence))], \
        len(bad_tbl) + len(bad_fence)


# ---------- C5：占位符 ----------

def check_placeholder(files):
    bad = []
    for f in files:
        base = os.path.basename(f)
        if base in PLACEHOLDER_OK:
            continue
        hits = re.findall(r"\{\{[^}]*\}\}", strip_fences(load(f)))
        if hits:
            bad.append((base, "非模板文件出现 %d 处占位符：%s" % (len(hits), hits[0][:30])))
    return [("C5 占位符越界", bad, "%d 个文件越界" % len(bad))], len(bad)


# ---------- C6：关键数字一致性（带覆盖数上报） ----------

def check_numbers(files):
    bad, warn, report = [], [], []
    for label, pat in KEY_NUMBERS:
        seen = {}
        for f in files:
            base = os.path.basename(f)
            txt = strip_fences(load(f))
            for m in pat.finditer(txt):
                vals = [g for g in m.groups() if g]
                key = vals[-1] if vals else m.group(0)
                ln = txt[:m.start()].count("\n") + 1
                seen.setdefault(key, []).append("%s:%d" % (base, ln))
        report.append((label, seen))

        if len(seen) == 0:
            warn.append((label, "**0 处匹配** → 该断言未在任何文件中出现，本条检查未生效"))
        elif len(seen) > 1:
            bad.append((label, "出现多个不同值：%s" % {k: v[:3] for k, v in seen.items()}))
        else:
            k = list(seen)[0]
            if len(seen[k]) < 2:
                warn.append((label, "单点断言（仅 %s，值=%s）→ 无法交叉验证一致性"
                             % (seen[k][0], k)))

    return [("C6 关键数字一致性", bad, "%d 项存在多值" % len(bad))], len(bad), report, warn


def main():
    verbose = "--verbose" in sys.argv
    files = collect_files()
    if not files:
        print("未找到任何交付文件，路径可能不对：%s" % ROOT)
        return 1

    print("=" * 68)
    print("交付集自洽性校验 · %s" % ROOT)
    print("受检文件 %d 个" % len(files))
    print("=" * 68)

    r1, i1, n1 = check_refs(files)
    r2, n2 = check_format(files)
    r3, n3 = check_placeholder(files)
    r4, n4, numreport, warns = check_numbers(files)

    if verbose:
        for name, items, summary in i1:
            print("\n[INFO] %s — %s" % (name, summary))
            for it in items[:25]:
                print("        - %s : %s" % it)

    total, warn_total = 0, 0
    for res in (r1, r2, r3, r4):
        for name, items, summary in res:
            status = "PASS" if not items else "FAIL"
            if status == "FAIL":
                total += len(items)
            print("\n[%s] %s — %s" % (status, name, summary))
            for it in items[:25]:
                print("        - %s : %s" % it)
            if len(items) > 25:
                print("        …（另有 %d 条）" % (len(items) - 25))

    if warns:
        warn_total = len(warns)
        print("\n[WARN] C6 覆盖不足 — %d 项（**这不是通过，是没查或没查全**）" % warn_total)
        for label, msg in warns:
            print("        - %s : %s" % (label, msg))

    if verbose:
        print("\n--- C6 关键数字覆盖分布 ---")
        for label, seen in numreport:
            print("  %s: %s" % (label, {k: v[:4] for k, v in seen.items()}))

    print("\n" + "=" * 68)
    print("结论：FAIL %d 项 ｜ WARN %d 项（覆盖不足）" % (total, warn_total))
    print("边界：本校验器只做机械可判定的检查，不判断内容对不对。")
    print("=" * 68)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())

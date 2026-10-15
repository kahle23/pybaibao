"""
recorder — 独立脚本式 E2E 的结果记录与用例执行骨架。

把"逐用例 record/blocked + JSONL 留痕 + SkipCase 前置跳过 + 末尾汇总 +
exit code"的重复模式收敛成一个 :class:`CaseRecorder`。适用于**不走 pytest**、
单文件独立执行的 E2E 脚本（.env 驱动、顺序执行、自管造数回收的那一类）。

来源：12-SDI e2e 十三份模板顶部完全同构的 ``record``/``blocked``/``_jsonl``/
``SkipCase``/``require`` 五件套 + main() 里逐 TC 的 try/except 编排。

约定（沿脚本口径）：**用例函数内部自行 record(PASS/FAIL)**；:meth:`run_case`
只兜异常——:class:`SkipCase` 记 BLOCKED（前置不满足），其余异常记 FAIL。
"""

import json
import time
from collections.abc import Callable
from typing import Any


class SkipCase(Exception):
    """用例前置不满足（锚数据缺失等）——记 BLOCKED 而非 FAIL。"""


class CaseRecorder:
    """
    用例结果记录器。

    >>> rec = CaseRecorder(run_tag="pre-fv-10131529")
    >>> rec.require(anchor is not None, "TC-001", "锚单")   # 不满足抛 SkipCase
    >>> rec.record("TC-001", True, "列值一致")
    >>> rec.run_case("TC-002", tc_002, page)                 # 兜 SkipCase/异常
    >>> raise SystemExit(rec.exit_code())

    Attributes:
        run_tag: 本轮标识（写进 JSONL，供报告对账）。
        jsonl_path: 结果留痕文件（相对 cwd）；置 None 关闭落盘。
        echo: 是否打印每条结果行。
        evidence_max: 单条 evidence 截断长度。
    """

    def __init__(
        self, run_tag: str = "", jsonl_path: str | None = "results.jsonl",
        echo: bool = True, evidence_max: int = 500,
    ):
        self.run_tag = run_tag
        self.jsonl_path = jsonl_path
        self.echo = echo
        self.evidence_max = evidence_max
        self.results: list[tuple[str, bool, str]] = []

    # ------------------------------------------------------------------
    # 记录
    # ------------------------------------------------------------------

    def record(self, tc: str, ok: bool, ev: str = "") -> None:
        """
        记一条 PASS/FAIL。
        """
        self.results.append((tc, bool(ok), str(ev)))
        if self.echo:
            print(("PASS " if ok else "FAIL ") + tc + (f" | {ev}" if ev else ""), flush=True)
        self._jsonl(tc, "PASS" if ok else "FAIL", str(ev))

    def blocked(self, tc: str, reason: Any) -> None:
        """
        记一条 BLOCKED（前置不满足/被阻塞）。
        """
        self.results.append((tc, False, "BLOCKED " + str(reason)))
        if self.echo:
            print("BLOCKED " + tc + " | " + str(reason), flush=True)
        self._jsonl(tc, "BLOCKED", str(reason))

    def skipped(self, tc: str, reason: Any) -> None:
        """
        记一条 SKIPPED（备查占位，不计 FAIL）。
        """
        self.results.append((tc, True, "SKIPPED " + str(reason)))
        if self.echo:
            print("SKIPPED " + tc + " | " + str(reason), flush=True)
        self._jsonl(tc, "SKIPPED", str(reason))

    def require(self, cond: Any, tc: str, what: str) -> None:
        """
        前置断言：不满足抛 :class:`SkipCase`（配合 :meth:`run_case` 记 BLOCKED）。
        """
        if not cond:
            raise SkipCase(f"{tc} 前置不满足，缺 {what}")

    def _jsonl(self, tc: str, status: str, evidence: str) -> None:
        if not self.jsonl_path:
            return
        try:
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "run": self.run_tag, "tc": tc, "status": status,
                    "evidence": evidence[: self.evidence_max],
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------

    def run_case(self, name: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> bool:
        """
        执行一个用例函数并兜异常。

        用例函数内部自行 :meth:`record`（PASS/FAIL 均可）；本方法只把
        :class:`SkipCase` 记 BLOCKED、把其余异常记 FAIL。返回是否未出异常。
        """
        try:
            fn(*args, **kwargs)
            return True
        except SkipCase as sk:
            self.blocked(name, str(sk))
        except Exception as e:  # 兜底记 FAIL，不中断整轮
            self.record(name, False, repr(e)[:220])
        return False

    # ------------------------------------------------------------------
    # 汇总
    # ------------------------------------------------------------------

    @property
    def failed(self) -> list[tuple[str, bool, str]]:
        """全部未通过项（FAIL/BLOCKED；SKIPPED 以 True 记账，不在其中）。"""
        return [r for r in self.results if not r[1]]

    @property
    def passed(self) -> list[tuple[str, bool, str]]:
        return [r for r in self.results if r[1]]

    def summary_line(self) -> str:
        """末尾汇总行（沿脚本口径：PASS / FAIL&BLOCKED / SKIPPED 分列）。"""
        skipped_n = sum(1 for r in self.results if str(r[2]).startswith("SKIPPED"))
        return (f"共 {len(self.results)} 条：{len(self.passed) - skipped_n} PASS / "
                f"{len(self.failed) - skipped_n} FAIL/BLOCKED / {skipped_n} SKIPPED")

    def exit_code(self) -> int:
        """进程退出码（有 FAIL/BLOCKED 即 1）。"""
        return 1 if self.failed else 0

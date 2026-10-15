"""
netwatch — context 级流量观察引擎。

把"挂在 BrowserContext 上监听请求/响应，按黑白名单判定写操作"的重复模式收敛成
配置注入式引擎：引擎本身零业务知识，端点规则全部由 :class:`NetWatchCfg` 提供。

来源：12-SDI e2e 十三份模板各自内嵌的 ``NetWatch``/``PdWatch``（各 100~250 行，
方法集已漂移成 4 个分支）——本模块取全集合并。判定语义沿脚本实证口径：

  - **硬性黑名单**：写方法（POST/PUT/DELETE）命中即记 ``violations``（红线 FAIL 依据）；
    ``hard_contains`` 命中但 path 以读语义后缀结尾时放行（POST /xxx/search 类）。
  - **末段特判**（``seg_kinds``）：URL 末段等于指定值即记违规，不限方法
    （GET /xxx/export 下载类也算）。
  - **受控写**：写方法命中受控规则 → 按 kind 计数 + 捕获响应体（断言写结果用）。
  - **读捕获**：path（去 query）含任一 ``read_frags`` → 捕获响应体（断言列表数据用）。
  - **其他写**：写方法既不受控也不在读白名单 → 登记 ``other_writes``；
    ``other_write_kind`` 非空时同时记为硬性违规（纯读域兜底）。

配套轮询助手 :func:`wait_write` / :func:`wait_read` / :func:`poll_ok_body`
（复用 :func:`baibao.autotest.polling.poll_until`）。

依赖：playwright（运行时由调用方传入 BrowserContext）。
"""

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from .polling import poll_until

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page


@dataclass(frozen=True)
class KindFrag:
    """
    端点规则：命中 ``frag`` 判为 ``kind``（endswith 或 contains 由所在规则组决定）。
    """

    kind: str
    frag: str


@dataclass(frozen=True)
class KindMethodFrag:
    """
    方法敏感规则：``method`` 且 URL 含 ``frag`` 判为 ``kind``。
    """

    kind: str
    method: str
    frag: str


def _kfs(pairs: tuple[tuple[str, str], ...]) -> tuple[KindFrag, ...]:
    """
    ``((kind, frag), ...)`` 快捷转 :class:`KindFrag` 元组（配置书写省样板）。
    """
    return tuple(KindFrag(k, f) for k, f in pairs)


def _kmfs(triples: tuple[tuple[str, str, str], ...]) -> tuple[KindMethodFrag, ...]:
    """
    ``((kind, method, frag), ...)`` 快捷转 :class:`KindMethodFrag` 元组。
    """
    return tuple(KindMethodFrag(k, m, f) for k, m, f in triples)


@dataclass
class NetWatchCfg:
    """
    流量判定配置（全部可选，空配置 = 只记录不判定）。

    Attributes:
        include_prefixes: URL 必须包含其一才进入记录/判定；空元组 = 全部记录。
        hard_endswith: 硬性黑名单（path endswith frag）；仅写方法参与。
        hard_contains: 硬性黑名单（contains frag）；仅写方法参与。
        hard_contains_read_suffixes: ``hard_contains`` 命中但 path 以这些后缀结尾时放行
            （POST 读语义端点，如 ``/search``）。
        hard_method_frag: 硬性黑名单（方法敏感）；仅写方法参与。
        controlled_endswith / controlled_contains / controlled_method_frag: 受控写规则（仅写方法）。
        read_frags: 读捕获白名单——path（去 query）含任一片段即捕获响应体。
        seg_kinds: ``(末段, kind)``——URL 末段等于指定值即记违规，**不限方法**（导出下载类）。
        track_other_writes: 是否登记"其他写"（写方法但不在受控/读白名单）。
        other_write_kind: 非空时"其他写"**同时记为该 kind 的硬性违规**（纯读域兜底，
            如 ``"unexpected-write"``）；空 = 只登记 other_writes 不判 FAIL。
        post_max / write_post_max / read_post_max: 请求体截断长度（请求登记/写捕获/读捕获）。
    """

    include_prefixes: tuple[str, ...] = ()
    hard_endswith: tuple[KindFrag, ...] = ()
    hard_contains: tuple[KindFrag, ...] = ()
    hard_contains_read_suffixes: tuple[str, ...] = ()
    hard_method_frag: tuple[KindMethodFrag, ...] = ()
    controlled_endswith: tuple[KindFrag, ...] = ()
    controlled_contains: tuple[KindFrag, ...] = ()
    controlled_method_frag: tuple[KindMethodFrag, ...] = ()
    read_frags: tuple[str, ...] = ()
    seg_kinds: tuple[tuple[str, str], ...] = ()
    track_other_writes: bool = True
    other_write_kind: str = ""
    post_max: int = 4000
    write_post_max: int = 800
    read_post_max: int = 400
    ok_code: int = 200

    @classmethod
    def build(
        cls,
        *,
        include_prefixes: tuple[str, ...] = (),
        hard_endswith: tuple[tuple[str, str], ...] = (),
        hard_contains: tuple[tuple[str, str], ...] = (),
        hard_contains_read_suffixes: tuple[str, ...] = (),
        hard_method_frag: tuple[tuple[str, str, str], ...] = (),
        controlled_endswith: tuple[tuple[str, str], ...] = (),
        controlled_contains: tuple[tuple[str, str], ...] = (),
        controlled_method_frag: tuple[tuple[str, str, str], ...] = (),
        read_frags: tuple[str, ...] = (),
        seg_kinds: tuple[tuple[str, str], ...] = (),
        **kwargs: Any,
    ) -> "NetWatchCfg":
        """
        ``((kind, frag), ...)`` 裸元组快捷构造（省去逐条 KindFrag 包装）。
        """
        return cls(
            include_prefixes=include_prefixes,
            hard_endswith=_kfs(hard_endswith),
            hard_contains=_kfs(hard_contains),
            hard_contains_read_suffixes=hard_contains_read_suffixes,
            hard_method_frag=_kmfs(hard_method_frag),
            controlled_endswith=_kfs(controlled_endswith),
            controlled_contains=_kfs(controlled_contains),
            controlled_method_frag=_kmfs(controlled_method_frag),
            read_frags=read_frags,
            seg_kinds=seg_kinds,
            **kwargs,
        )


_WRITE_METHODS = ("POST", "PUT", "DELETE")


class NetWatch:
    """
    BrowserContext 级流量观察器（sync Playwright）。

    挂到 context 上后持续记录，配合 :meth:`mark` 做增量断言：

    >>> watch = NetWatch(ctx, cfg)
    >>> m = watch.mark()          # 操作前打点
    >>> ...                       # 页面操作
    >>> watch.write_since(m, "save")     # 受控写命中
    >>> watch.last_ok_body(m, "/search") # 最近一次 code=200 的读响应体

    多 context（多角色）合并对账用 :meth:`merged`。
    事件回调内的异常一律吞掉（观察器不能弄死被测流程）。
    """

    def __init__(self, ctx: "BrowserContext", cfg: NetWatchCfg | None = None):
        self.cfg = cfg or NetWatchCfg()
        self.reqs: list[dict[str, Any]] = []
        self.bodies: list[dict[str, Any]] = []
        self.writes: list[dict[str, Any]] = []
        self.violations: list[dict[str, Any]] = []
        self.controlled: list[dict[str, Any]] = []
        self.other_writes: list[dict[str, Any]] = []
        ctx.on("request", self._on_req)
        ctx.on("response", self._on_resp)

    # ------------------------------------------------------------------
    # 分类规则（cfg 驱动）
    # ------------------------------------------------------------------

    def _seg_kind(self, path: str) -> str | None:
        """
        URL 末段特判（seg_kinds 规则；导出/导入类不限方法）。
        """
        seg = [s for s in path.split("/") if s]
        if seg:
            for tail, kind in self.cfg.seg_kinds:
                if seg[-1] == tail:
                    return kind
        return None

    def _hard_kind(self, method: str, path: str) -> str | None:
        """
        硬性黑名单判定（仅写方法；contains 组受读语义后缀白名单约束）。
        """
        if method not in _WRITE_METHODS:
            return None
        for r in self.cfg.hard_endswith:
            if path.endswith(r.frag):
                return r.kind
        for r in self.cfg.hard_contains:
            if r.frag in path:
                if path.endswith(self.cfg.hard_contains_read_suffixes):
                    return None
                return r.kind
        for rm in self.cfg.hard_method_frag:
            if method == rm.method and rm.frag in path:
                return rm.kind
        return None

    def _controlled_kind(self, method: str, path: str) -> str | None:
        """
        受控写判定（仅写方法；endswith → contains → 方法前缀三组规则）。
        """
        if method not in _WRITE_METHODS:
            return None
        for r in self.cfg.controlled_endswith:
            if path.endswith(r.frag):
                return r.kind
        for r in self.cfg.controlled_contains:
            if r.frag in path:
                return r.kind
        for rm in self.cfg.controlled_method_frag:
            if method == rm.method and rm.frag in path:
                return rm.kind
        return None

    # ------------------------------------------------------------------
    # 事件处理
    # ------------------------------------------------------------------

    def _on_req(self, req: Any) -> None:
        """
        请求事件：登记 + 硬性/受控/其他写分类（异常吞掉）。
        """
        try:
            url = req.url or ""
            if self.cfg.include_prefixes and not any(p in url for p in self.cfg.include_prefixes):
                return
            method = (req.method or "").upper()
            path = url.split("?")[0]
            entry: dict[str, Any] = {"method": method, "url": url, "post": None}
            if method in _WRITE_METHODS:
                entry["post"] = (req.post_data or "")[: self.cfg.post_max]
            self.reqs.append(entry)
            sk = self._seg_kind(path)
            hk = sk or self._hard_kind(method, path)
            if hk:
                self.violations.append(
                    {"kind": hk, "method": method, "url": url, "post": entry["post"]})
                return
            if method in _WRITE_METHODS:
                ck = self._controlled_kind(method, path)
                if ck:
                    self.controlled.append(
                        {"kind": ck, "method": method, "url": url, "post": entry["post"]})
                elif not any(f in path for f in self.cfg.read_frags):
                    other = {"method": method, "url": url, "post": entry["post"]}
                    if self.cfg.track_other_writes:
                        self.other_writes.append(other)
                    if self.cfg.other_write_kind:
                        self.violations.append({"kind": self.cfg.other_write_kind,
                                                "method": method, "url": url,
                                                "post": entry["post"]})
        except Exception:
            pass

    def _on_resp(self, resp: Any) -> None:
        """
        响应事件：受控写捕获响应体 + 读白名单响应捕获（异常吞掉）。
        """
        try:
            url = resp.url or ""
            method = (resp.request.method or "").upper()
            path = url.split("?")[0]
            ck = self._controlled_kind(method, path)
            if ck:
                e: dict[str, Any] = {
                    "kind": ck, "status": resp.status, "url": url,
                    "body": None, "req_post": None}
                try:
                    e["req_post"] = (resp.request.post_data or "")[: self.cfg.write_post_max]
                except Exception:
                    pass
                try:
                    e["body"] = resp.json()
                except Exception:
                    pass
                self.writes.append(e)
                self.bodies.append({"status": resp.status, "url": url,
                                    "body": e["body"], "req_post": e["req_post"]})
                return
            if not any(f in path for f in self.cfg.read_frags):
                return
            e = {"status": resp.status, "url": url, "body": None, "req_post": None}
            try:
                e["req_post"] = (resp.request.post_data or "")[: self.cfg.read_post_max]
            except Exception:
                pass
            try:
                e["body"] = resp.json()
            except Exception:
                try:
                    e["body"] = {"_text": (resp.text() or "")[:400]}
                except Exception:
                    pass
            self.bodies.append(e)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 增量查询
    # ------------------------------------------------------------------

    def mark(self) -> dict[str, int]:
        """
        当前水位打点（供 ``*_since`` 增量查询）。
        """
        return {"b": len(self.bodies), "q": len(self.reqs), "w": len(self.writes)}

    def bodies_since(self, mark: dict[str, int] | None, frag: str) -> list[dict[str, Any]]:
        """
        mark 之后 URL 含 ``frag`` 的捕获响应（含受控写捕获）。
        """
        b0 = mark["b"] if isinstance(mark, dict) else 0
        return [e for e in self.bodies[b0:] if frag in (e.get("url") or "")]

    def write_since(self, mark: dict[str, int] | None, kind: str) -> list[dict[str, Any]]:
        """
        mark 之后 kind 命中的受控写事件。
        """
        w0 = mark["w"] if isinstance(mark, dict) else 0
        return [e for e in self.writes[w0:] if e.get("kind") == kind]

    def write_post_since(self, mark: dict[str, int] | None, kind: str) -> dict[str, Any]:
        """
        mark 之后该 kind 最近一次受控写的请求体（JSON 解析，失败回退 {}）。
        """
        for e in reversed(self.write_since(mark, kind)):
            try:
                parsed: dict[str, Any] = json.loads(e.get("req_post") or "{}")
                return parsed
            except Exception:
                continue
        return {}

    def last_req_since(self, mark: dict[str, int] | None, frag: str) -> dict[str, Any]:
        """
        mark 之后最近一次带请求体的含 ``frag`` 请求（JSON 解析，失败回退 {}）。
        """
        q0 = mark["q"] if isinstance(mark, dict) else 0
        for e in reversed(self.reqs[q0:]):
            if frag in (e.get("url") or "") and e.get("post"):
                try:
                    parsed: dict[str, Any] = json.loads(e["post"])
                    return parsed
                except Exception:
                    continue
        return {}

    def posts_since(self, mark: dict[str, int] | None, frag: str) -> list[dict[str, Any]]:
        """
        mark 之后 URL 含 ``frag`` 的全部 POST 请求体（逐个 JSON 解析，跳过失败项）。
        """
        q0 = mark["q"] if isinstance(mark, dict) else 0
        out: list[dict[str, Any]] = []
        for e in self.reqs[q0:]:
            if frag not in (e.get("url") or "") or e.get("method") != "POST" or not e.get("post"):
                continue
            try:
                out.append(json.loads(e["post"]))
            except Exception:
                continue
        return out

    def _ok_body(self, e: dict[str, Any] | None) -> dict[str, Any] | None:
        """
        事件响应体是否为 ``code == ok_code`` 的业务成功体（不是则返回 None）。
        """
        b = e.get("body") if e else None
        if not isinstance(b, dict):  # isinstance 会把 Any 收窄成 dict[Unknown, ...]，cast 回真实形状
            return None
        bd = cast("dict[str, Any]", b)
        return bd if bd.get("code") == self.cfg.ok_code else None

    def last_ok_body(
        self, mark: dict[str, int] | None, frag: str, include_any: bool = False,
    ) -> dict[str, Any] | None:
        """
        mark 之后最近一次 code=ok 的含 ``frag`` 响应体；``include_any`` 时兜底全历史。
        """
        for e in reversed(self.bodies_since(mark, frag)):
            b = self._ok_body(e)
            if b is not None:
                return b
        if include_any:
            b0 = mark["b"] if isinstance(mark, dict) else 0
            for e in reversed(self.bodies[b0:]):
                if frag in (e.get("url") or ""):
                    b = self._ok_body(e)
                    if b is not None:
                        return b
        return None

    def last_ok_body_any(self, frag: str) -> dict[str, Any] | None:
        """
        全历史找最近一次 code=ok 的含 ``frag`` 响应体（首载类请求在 mark 之前发出时用）。
        """
        for e in reversed(self.bodies):
            if frag in (e.get("url") or ""):
                b = self._ok_body(e)
                if b is not None:
                    return b
        return None

    def evt_count_since(self, mark: dict[str, int] | None, frag: str) -> int:
        """
        mark 之后 URL 含 ``frag`` 的捕获响应条数。
        """
        return len(self.bodies_since(mark, frag))

    def api_count_since(
        self, mark: dict[str, int] | None, frag: str, method: str | None = None,
    ) -> int:
        """
        mark 之后 URL 含 ``frag`` 的请求条数（可限定方法）。
        """
        q0 = mark["q"] if isinstance(mark, dict) else 0
        cnt = 0
        for e in self.reqs[q0:]:
            if frag not in (e.get("url") or ""):
                continue
            if method and (e.get("method") or "").upper() != method.upper():
                continue
            cnt += 1
        return cnt

    def count_suffix(self, suffix: str, method: str | None = None) -> int:
        """
        全历史 path 以 ``suffix`` 结尾的请求条数（可限定方法）。
        """
        cnt = 0
        for e in self.reqs:
            path = (e.get("url") or "").split("?")[0]
            if not path.endswith(suffix):
                continue
            if method and (e.get("method") or "").upper() != method.upper():
                continue
            cnt += 1
        return cnt

    def kind_counts(self) -> dict[str, int]:
        """
        受控写按 kind 计数。
        """
        counts: dict[str, int] = {}
        for e in self.controlled:
            counts[e["kind"]] = counts.get(e["kind"], 0) + 1
        return counts

    def hard_counts(self) -> dict[str, int]:
        """
        硬性违规按 kind 计数。
        """
        counts: dict[str, int] = {}
        for e in self.violations:
            counts[e["kind"]] = counts.get(e["kind"], 0) + 1
        return counts

    # ------------------------------------------------------------------
    # 合并
    # ------------------------------------------------------------------

    def merge_from(self, *others: "NetWatch") -> None:
        """
        把其他 watch 的记录并入自身（多角色/多 context 终态对账）。
        """
        for w in others:
            self.reqs.extend(w.reqs)
            self.bodies.extend(w.bodies)
            self.writes.extend(w.writes)
            self.violations.extend(w.violations)
            self.controlled.extend(w.controlled)
            self.other_writes.extend(w.other_writes)

    @classmethod
    def merged(cls, *watches: "NetWatch", cfg: "NetWatchCfg | None" = None) -> "NetWatch":
        """
        聚合多个 watch 的对账视图（不挂事件、只读查询用）。
        """
        nw = cls.__new__(cls)
        nw.cfg = cfg or (watches[0].cfg if watches else NetWatchCfg())
        nw.reqs, nw.bodies, nw.writes = [], [], []
        nw.violations, nw.controlled, nw.other_writes = [], [], []
        nw.merge_from(*watches)
        return nw


def wait_write(
    page: "Page", watch: NetWatch, mark: dict[str, int] | None,
    kind: str, timeout_ms: int = 12000,
) -> bool:
    """
    轮询直到 mark 后出现该 kind 的受控写事件（借 page.wait_for_timeout 走协议消息）。
    """
    return bool(poll_until(
        lambda: watch.write_since(mark, kind),
        timeout_ms=timeout_ms, interval_ms=400, sleep_ms=page.wait_for_timeout,
    ))


def wait_read(
    page: "Page", watch: NetWatch, mark: dict[str, int] | None,
    frag: str, timeout_ms: int = 10000,
) -> bool:
    """
    轮询直到 mark 后捕获到 URL 含 ``frag`` 的响应。
    """
    return bool(poll_until(
        lambda: watch.bodies_since(mark, frag),
        timeout_ms=timeout_ms, interval_ms=400, sleep_ms=page.wait_for_timeout,
    ))


def poll_ok_body(
    page: "Page", watch: NetWatch, mark: dict[str, int] | None,
    frag: str, timeout_ms: int = 12000,
) -> dict[str, Any] | None:
    """
    轮询直到拿到 mark 后最近一次 code=ok 的含 ``frag`` 响应体（超时返回 None）。
    """
    return poll_until(
        lambda: watch.last_ok_body(mark, frag),
        timeout_ms=timeout_ms, interval_ms=400, sleep_ms=page.wait_for_timeout,
    )

"""
token_session — token 型后端接口的 requests 会话（自动处理登录失效）。

面向"验证码登录 → token 请求头鉴权 → body code=401 表登录失效"的后台系统，
为 E2E 造数/接口直连提供一条与浏览器并行的鉴权通道：

  - **双 token 来源**：优先复用 ``.auth/`` 登录态缓存（storage_state 里的
    localStorage token，与浏览器侧同一份缓存，一轮测试只登录一次）；
    读不到或已失效时走 HTTP 配方现场登录。
  - **登录失效自动处理**：任一响应被判定未授权（默认 HTTP 401 或 body
    ``code == 401``）→ 自动重登一次并**原样重放**该请求，调用方无感。
    重放上限一次，防凭据错误死循环。
  - **防御式 JSON 解析**：非 JSON 响应包成 ``{"_rawText": ..., "_status": ...}``
    （与 :class:`baibao.autotest.api.base.ApiBase` 口径一致）。

与 :class:`baibao.autotest.api.base.ApiBase` 的分工：ApiBase 走 Playwright
``APIRequestContext`` 复用浏览器 cookie；本模块走纯 ``requests``，适合脱离
浏览器上下文的造数/回收。

来源：12-SDI e2e 九份模板各自内嵌的 ``api_sess``/``api_post``（captcha 登录 +
401 重登重放，2026-10-12 pre token 波动实证配方）。

依赖：requests（**按需懒加载**——未装 requests 的环境仍可 import 本包其他模块，
首次发请求时才报可读错误）。与 playwright 无关。
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import requests


def _ensure_requests() -> None:
    """
    惰性探测 requests（未安装时给可读指引；不在模块顶层导入，
    保证无 requests 环境不受牵连——实导入由调用处函数内完成）。
    """
    if find_spec("requests") is None:
        raise ImportError(
            "token_session 需要 requests：pip install 'baibao[autotest]' 或 pip install requests",
        )


@dataclass
class TokenSessionCfg:
    """
    token 会话配置（登录配方各环节全部可注入）。

    Attributes:
        base_url: API 基础地址（末尾斜杠会被去除）。
        login_path: 登录端点路径（如 ``/system/login``）；空串表示无法 HTTP 登录
            （只能从 ``auth_state`` 取 token，失效即抛错）。
        login_payload: ``(account, password, captcha_id) -> 登录请求体``。
        captcha_path: 验证码图端点（``None`` 表示登录无需验证码，不预取 captchaId）。
        captcha_id_from: 从验证码端点响应抽 captchaId（默认 ``data.captchaId``）。
        captcha_value: 验证码值——固定字符串或零参可调用（测试环境常为万能码）。
        token_header: token 放的请求头名。
        token_from: 从登录响应抽 token（默认 ``data.token``）。
        unauthorized_when: ``(body, status) -> bool`` 登录失效判定
            （默认 HTTP 401 或 body ``code == 401``）。
        ok_code: 业务成功码（``unwrap`` 用）。
        timeout_s: 单请求超时秒数。
        conn_retries: 登录链（验证码/登录）连接瞬断重试次数（并行批次环境偶发
            connection refused；仅登录链重试，业务请求不重试）。
        conn_retry_sleep_s: 连接重试间隔秒。
        extra_headers: 随每个请求发送的附加头。
        auth_state: ``.auth/<role>.json`` storage_state 缓存路径（可选；
            提供时优先从其中读 token）。
        token_state_key: token 在 storage_state localStorage 里的 key
            （如 ``maToken``；不提供则不做缓存读取）。
        write_back_auth_state: 401 重登拿到新 token 后是否回写 ``auth_state``
            （把 storage_state 里的旧 token 换新，浏览器侧缓存同步续期）。
    """

    base_url: str = ""
    login_path: str = ""
    login_payload: Callable[[str, str, str | None], dict[str, Any]] = field(
        default_factory=lambda: _default_login_payload,
    )
    captcha_path: str | None = None
    captcha_id_from: Callable[[dict[str, Any]], str | None] = field(
        default_factory=lambda: _captcha_id_from_data,
    )
    captcha_value: str | Callable[[], str] = "1"
    token_header: str = "Authorization"
    token_from: Callable[[dict[str, Any]], str | None] = field(
        default_factory=lambda: _token_from_data,
    )
    unauthorized_when: Callable[[dict[str, Any] | None, int], bool] = field(
        default_factory=lambda: _unauthorized_default,
    )
    ok_code: int = 200
    timeout_s: int = 40
    conn_retries: int = 0
    conn_retry_sleep_s: float = 8.0
    extra_headers: dict[str, str] = field(default_factory=dict[str, str])
    auth_state: Path | None = None
    token_state_key: str = ""
    write_back_auth_state: bool = False


def _default_login_payload(account: str, password: str, captcha_id: str | None) -> dict[str, Any]:
    """
    IMP 形态默认登录体：account/password +（有验证码时）captchaId/captchaVal。
    """
    body: dict[str, Any] = {"account": account, "password": password}
    if captcha_id is not None:
        body["captchaId"] = captcha_id
        body["captchaVal"] = "1"
    return body


def _captcha_id_from_data(resp: dict[str, Any]) -> str | None:
    """
    从验证码端点响应抽 captchaId（默认 ``data.captchaId``）。

    isinstance 守卫会让 pyright 把收窄结果标成 ``dict[Unknown, ...]`` 级联报错，
    经 cast(Any) 隔离后取值、再按真实形状收口（mypy/pyright 双绿口径）。
    """
    data: Any = cast(Any, resp).get("data") if isinstance(resp, dict) else None
    return cast("dict[str, Any]", data).get("captchaId") if isinstance(data, dict) else None


def _token_from_data(resp: dict[str, Any]) -> str | None:
    """
    从登录响应抽 token（默认 ``data.token``；收窄隔离口径同上）。
    """
    data: Any = cast(Any, resp).get("data") if isinstance(resp, dict) else None
    return cast("dict[str, Any]", data).get("token") if isinstance(data, dict) else None


def _unauthorized_default(body: dict[str, Any] | None, status: int) -> bool:
    """
    登录失效判定：HTTP 401 或 body ``code == 401``。
    """
    if status == 401:
        return True
    return isinstance(body, dict) and body.get("code") == 401


class TokenSession:
    """
    token 型 API 会话（懒登录 + 失效自动重登重放）。

    >>> cfg = TokenSessionCfg(base_url=BASE, login_path="/system/login",
    ...                       captcha_path="/system/captcha/image",
    ...                       auth_state=Path(".auth/A.json"), token_state_key="maToken")
    >>> api = TokenSession(cfg, account, password)
    >>> api.post("/biz/factory/add", {"fullNameZh": "E2E-SEED-X"})   # 401 自愈
    >>> api.unwrap(api.post("/wms/warehouse/init-virtual-preview", {}))  # code!=ok 抛错
    """

    def __init__(self, cfg: TokenSessionCfg, account: str, password: str):
        self.cfg = cfg
        self.account = account
        self.password = password
        self.base_url = cfg.base_url.rstrip("/")
        self._sess: requests.Session | None = None
        self._token: str | None = None
        # 缓存 token 已被服务端判失效后置位——后续 _ensure_ready 跳过缓存直走 HTTP 登录，
        # 否则 401 重放会反复读到同一份过期缓存
        self._auth_state_failed = False

    # ------------------------------------------------------------------
    # token 获取
    # ------------------------------------------------------------------

    def _token_from_auth_state(self) -> str | None:
        """
        从 storage_state 缓存的 localStorage 里读 token（没有/读不到返回 None）。
        """
        if not (self.cfg.auth_state and self.cfg.token_state_key):
            return None
        try:
            state = json.loads(self.cfg.auth_state.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        for origin in state.get("origins", []):
            for item in origin.get("localStorage", []):
                if item.get("name") == self.cfg.token_state_key:
                    tok = (item.get("value") or "").strip()
                    # 2026-10-14 S12 试点首验修正：IMP FE 以 JSON.stringify 落 localStorage
                    # （maToken 实存值带首尾双引号）——原样读出会把引号带进 Authorization 头，
                    # 后端解析失败统一包装成 code=500「操作失败！」（误似业务异常）。剥引号。
                    if len(tok) >= 2 and tok[0] == '"' and tok[-1] == '"':
                        tok = tok[1:-1]
                    return tok or None
        return None

    def _write_back_token(self, token: str) -> None:
        """
        把新 token 回写 storage_state 缓存（浏览器侧缓存同步续期；失败静默）。
        """
        if not (self.cfg.write_back_auth_state and self.cfg.auth_state
                and self.cfg.token_state_key):
            return
        try:
            state = json.loads(self.cfg.auth_state.read_text(encoding="utf-8"))
            hit = False
            for origin in state.get("origins", []):
                for item in origin.get("localStorage", []):
                    if item.get("name") == self.cfg.token_state_key:
                        # 保持原缓存格式（IMP FE 存 JSON.stringify 带引号形态；读侧已兼容裸值）
                        item["value"] = (f'"{token}"' if str(item.get("value", "")).strip().startswith('"')
                                         else token)
                        hit = True
            if not hit:
                if not state.get("origins"):
                    state["origins"] = []
                state["origins"].append({
                    "origin": self.base_url.split("//")[-1].split("/")[0],
                    "localStorage": [{"name": self.cfg.token_state_key, "value": token}],
                })
            self.cfg.auth_state.write_text(
                json.dumps(state, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _login(self) -> str:
        """
        走 HTTP 配方登录，返回 token（失败抛 RuntimeError）。
        """
        if not self.cfg.login_path:
            raise RuntimeError(
                "token 失效且未配置 login_path——无法自动重登"
                f"（auth_state={self.cfg.auth_state}）")
        _ensure_requests()
        import requests  # 函数内导入（懒加载语义），requests 自带 py.typed 走真类型
        s = self._sess or requests.Session()

        def _retry(fn: Callable[[], Any]) -> Any:
            """
            登录链连接瞬断重试（conn_retries 次，间隔 conn_retry_sleep_s）。
            """
            last: Exception | None = None
            for _ in range(self.cfg.conn_retries + 1):
                try:
                    return fn()
                except requests.exceptions.ConnectionError as e:
                    last = e
                    time.sleep(self.cfg.conn_retry_sleep_s)
            raise RuntimeError(f"登录链连接失败（重试 {self.cfg.conn_retries} 次仍失败）: {last!r}")

        captcha_id = None
        if self.cfg.captcha_path:
            # URL 在 lambda 外拼好：mypy 对闭包内的属性收窄不可靠（captcha_path 可空）
            cap_url = self.base_url + self.cfg.captcha_path
            cap = _retry(lambda: s.get(
                cap_url,
                timeout=self.cfg.timeout_s).json())
            captcha_id = self.cfg.captcha_id_from(cap)
            if not captcha_id:
                raise RuntimeError(f"取 captchaId 失败: {str(cap)[:200]}")
        body = dict(self.cfg.login_payload(self.account, self.password, captcha_id))
        cv = self.cfg.captcha_value
        if captcha_id is not None and cv is not None and "captchaVal" not in body:
            body["captchaVal"] = cv() if callable(cv) else cv
        r = _retry(lambda: s.post(self.base_url + self.cfg.login_path, json=body,
                                  timeout=self.cfg.timeout_s).json())
        # isinstance 会把 Any 收窄成 Unknown 联合并污染 r 的后续使用，经别名隔离
        r_body: Any = r
        tok = self.cfg.token_from(cast("dict[str, Any]", r_body)) if isinstance(r_body, dict) else None
        if not tok:
            raise RuntimeError(f"API 登录失败: {str(r)[:200]}")
        s.headers[self.cfg.token_header] = tok
        s.headers.update(self.cfg.extra_headers)
        self._sess = s
        self._token = tok
        self._write_back_token(tok)
        return tok

    def _ensure_ready(self) -> "requests.Session":
        """
        确保拿到带 token 的会话（缓存优先且未被判失效，HTTP 登录兜底）。
        """
        if self._sess is not None and self._token:
            return self._sess
        tok = None if self._auth_state_failed else self._token_from_auth_state()
        if tok:
            _ensure_requests()
            import requests
            s = requests.Session()
            s.headers[self.cfg.token_header] = tok
            s.headers.update(self.cfg.extra_headers)
            self._sess, self._token = s, tok
            return s
        self._login()
        assert self._sess is not None  # _login 成功必置会话
        return self._sess

    def reset(self) -> None:
        """
        丢弃当前会话/token（下次请求触发重登；缓存 token 失效也会被跳过）。
        """
        self._sess, self._token = None, None
        self._auth_state_failed = True

    @property
    def token(self) -> str | None:
        """
        当前 token（不触发登录；需要就绪会话用 ``api._ensure_ready()``）。
        """
        return self._token

    # ------------------------------------------------------------------
    # 请求（401 自动重登重放一次）
    # ------------------------------------------------------------------

    def request(
        self, method: str, path: str, body: dict[str, Any] | None = None,
        *, _retried: bool = False, **kwargs: Any,
    ) -> dict[str, Any]:
        """
        发请求并解析 JSON；登录失效时重登一次原样重放。
        """
        s = self._ensure_ready()
        r = s.request(method, self.base_url + path,
                      json=body if body is not None else {},
                      timeout=self.cfg.timeout_s, **kwargs)
        out = self._parse_json(r)
        if self.cfg.unauthorized_when(out if isinstance(out, dict) else None, r.status_code):
            if _retried:
                return out
            self.reset()
            return self.request(method, path, body, _retried=True, **kwargs)
        return out

    def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """
        GET 请求（401 自愈同 :meth:`request`）。
        """
        return self.request("GET", path, None, **kwargs)

    def post(self, path: str, body: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        """
        POST 请求（401 自愈同 :meth:`request`）。
        """
        return self.request("POST", path, body, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> dict[str, Any]:
        """
        DELETE 请求（401 自愈同 :meth:`request`）。
        """
        return self.request("DELETE", path, None, **kwargs)

    @staticmethod
    def _parse_json(r: "requests.Response") -> dict[str, Any]:
        """
        防御式 JSON 解析（非 JSON 包成 ``_rawText``/``_status``）。
        """
        try:
            out: Any = r.json()
            if isinstance(out, dict):
                return cast("dict[str, Any]", out)
            return {"_wrapped": out, "_status": r.status_code}
        except ValueError:
            return {"_rawText": r.text[:200], "_status": r.status_code}

    def unwrap(self, resp: dict[str, Any], what: str = "") -> Any:
        """
        断言 body ``code == ok_code`` 并返回 ``data``（否则抛 AssertionError）。
        """
        assert isinstance(resp, dict) and resp.get("code") == self.cfg.ok_code, (
            f"{what or '接口'} 返回异常: {str(resp)[:200]}")
        return resp.get("data")

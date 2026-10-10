"""多平台 LLM 客户端管理。"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from app.core.config import get_user_settings_file

from langchain_openai import ChatOpenAI as _BaseChatOpenAI
from langchain_core.outputs import ChatGenerationChunk

from app.core.logging import get_logger
from app.services.model_settings import (
    enrich_providers,
    load_model_parameters,
    normalize_legacy_parameters,
    provider_key,
)

logger = get_logger(__name__)


# =============================================================================
# DeepSeek / OpenAI 兼容 reasoning_content 修复（monkey-patch LangChain）
# =============================================================================
# LangChain 的 _format_message_content 会过滤掉 reasoning_content block，
# _convert_from_v1_to_chat_completions 会过滤掉 reasoning block，
# _convert_message_to_dict 不会把 additional_kwargs.reasoning_content 发给 API。
# 这导致 DeepSeek 思考模式在多轮对话中报错：
#   "The `reasoning_content` in the thinking mode must be passed back to the API."
#
# 修复策略：
#  1. patch _format_message_content：保留 reasoning_content block
#  2. patch _convert_from_v1_to_chat_completions：保留 reasoning block
#  3. patch _convert_message_to_dict：把 additional_kwargs.reasoning_content 注入 API payload
# =============================================================================


def _apply_reasoning_content_patches():
    """一次性应用所有 reasoning_content 相关 patch。"""
    try:
        from langchain_openai.chat_models import base as lc_base
    except Exception:
        return

    original_format = lc_base._format_message_content

    def _patched_format_message_content(content, api="chat/completions", role=None):
        """保留 reasoning_content block，不剥离。"""
        result = original_format(content, api=api, role=role)
        if content and isinstance(content, list) and isinstance(result, list):
            for block in content:
                if isinstance(block, dict):
                    btype = block.get("type", "")
                    if btype in ("reasoning_content", "thinking") and block not in result:
                        result.append(block)
        return result

    lc_base._format_message_content = _patched_format_message_content

    # Patch _convert_from_v1_to_chat_completions：保留 reasoning block
    try:
        from langchain_openai.chat_models import _compat as lc_compat

        if hasattr(lc_compat, "_convert_from_v1_to_chat_completions"):
            _orig_convert = lc_compat._convert_from_v1_to_chat_completions

            def _patched_convert(message):
                if isinstance(message.content, list):
                    new_content = []
                    kept = []
                    for block in message.content:
                        if isinstance(block, dict):
                            btype = block.get("type", "")
                            if btype == "text":
                                new_content.append({"type": "text", "text": block["text"]})
                            elif btype == "tool_call":
                                pass  # 保持不变，tool_call block 正常保留
                            elif btype in ("reasoning", "reasoning_content", "thinking"):
                                # 统一转换为 reasoning_content block 类型
                                kept.append({"type": "reasoning_content", "content": block.get("content", "")})
                            else:
                                new_content.append(block)
                        else:
                            new_content.append(block)
                    # 推理内容放在最前面
                    result = message.model_copy(update={"content": kept + new_content})
                    return result
                return message

            lc_compat._convert_from_v1_to_chat_completions = _patched_convert
    except Exception as e:
        logger.error(f"[LLM] ⚠️ patch _convert_from_v1_to_chat_completions 失败: {e}")

    # Patch _convert_message_to_dict：把 additional_kwargs.reasoning_content 注入 payload
    # 同时处理 reasoning block -> top-level reasoning_content 字段的转换
    _orig_convert_dict = lc_base._convert_message_to_dict

    def _patched_convert_message_to_dict(message, api="chat/completions"):
        result = _orig_convert_dict(message, api=api)
        if isinstance(message, lc_base.AIMessage):
            # 优先从 additional_kwargs 取
            rc = message.additional_kwargs.get("reasoning_content")
            # fallback：从 content blocks 中找
            if not rc and isinstance(message.content, list):
                for block in message.content:
                    if isinstance(block, dict) and block.get("type") == "reasoning_content":
                        rc = block.get("content", "")
                        break
            if rc:
                result["reasoning_content"] = rc
                # 如果 content 是 list，确保其中有 reasoning block
                if isinstance(result.get("content"), list):
                    has_reasoning = any(
                        isinstance(b, dict) and b.get("type") == "reasoning_content" for b in result["content"]
                    )
                    if not has_reasoning:
                        result["content"] = [{"type": "reasoning_content", "content": rc}] + result["content"]
        return result

    lc_base._convert_message_to_dict = _patched_convert_message_to_dict

    # Patch _create_chat_result：确保从 API 响应中提取 reasoning_content 到 additional_kwargs
    _orig_create_chat_result = lc_base.ChatOpenAI._create_chat_result  # type: ignore

    def _patched_create_chat_result(self, response, generation_info=None):
        result = _orig_create_chat_result(self, response, generation_info)
        # 从 API 原始响应中提取 reasoning_content（DeepSeek 等模型放在 delta 中）
        response_dict = response.model_dump() if hasattr(response, "model_dump") else response
        choices = response_dict.get("choices") or []
        for choice in choices:
            delta = choice.get("delta", {})
            rc = delta.get("reasoning_content") or choice.get("message", {}).get("reasoning_content")
            if rc:
                msg = result.generations[0].message
                if hasattr(msg, "additional_kwargs"):
                    msg.additional_kwargs["reasoning_content"] = rc
                # 同时放到 content 中（LangChain 处理时会用到）
                if hasattr(msg, "content") and isinstance(msg.content, list):
                    has_reasoning = any(
                        isinstance(b, dict) and b.get("type") == "reasoning_content" for b in msg.content
                    )
                    if not has_reasoning:
                        msg.content = [{"type": "reasoning_content", "content": rc}] + msg.content
                break
        return result

    lc_base.ChatOpenAI._create_chat_result = _patched_create_chat_result  # type: ignore

    # Patch parse_tool_call：DeepSeek thinking 模式有时输出格式不标准的 JSON，
    # LangChain 默认直接标记为 invalid，这里加入智能修复策略
    try:
        from langchain_core.output_parsers.openai_tools import parse_tool_call as _orig_parse_tool_call
        import re

        def _parse_args_smart_fix(args_str):
            """智能修复并解析工具参数 JSON。

            策略：
            1. 直接解析
            2. 去掉尾随逗号（包括字符串末尾的逗号）
            3. 修复中文/弯引号
            4. 从混排文本中提取 JSON
            """
            if not args_str:
                return {}
            if isinstance(args_str, (dict, list)):
                return args_str
            s = str(args_str).strip()
            if not s:
                return {}

            # 直接解析
            try:
                return json.loads(s)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

            # 修复1：去掉尾随逗号（包括字符串末尾的 ,})
            # 先处理末尾的 ,} 或 ,]  再处理字符串末尾的 ,}
            fixed = s
            for _ in range(5):  # 最多5次，防止过度修复
                prev = fixed
                fixed = re.sub(r",(\s*)([}\]])", r"\2", fixed)
                fixed = re.sub(r",\s*$", "", fixed)  # 字符串末尾的尾随逗号
                if fixed == prev:
                    break
            try:
                return json.loads(fixed)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

            # 修复2：修复中文/弯引号
            for old, new in [
                ("\u201c", '"'),
                ("\u201d", '"'),
                ("\u300c", '"'),
                ("\u300d", '"'),
                ("\u2018", "'"),
                ("\u2019", "'"),
            ]:
                fixed = fixed.replace(old, new)
            try:
                return json.loads(fixed)
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

            # 修复3：从混排文本中提取 JSON（从后往前找）
            # 用括号匹配来找到完整的 JSON 对象
            def find_json_objects(text):
                results = []
                i = len(text) - 1
                while i >= 0:
                    if text[i] == "}":
                        depth = 0
                        start = i
                        for j in range(i, -1, -1):
                            if text[j] == "}":
                                depth += 1
                            elif text[j] == "{":
                                depth -= 1
                                if depth == 0:
                                    results.append(text[j : start + 1])
                                    i = j - 1
                                    break
                    i -= 1
                return results

            for candidate in find_json_objects(s):
                try:
                    result = json.loads(candidate)
                    if isinstance(result, dict):
                        return result
                except (json.JSONDecodeError, ValueError, TypeError):
                    continue

            return None

        def _patched_parse_tool_call(raw_tool_call, *, partial=False, strict=False, return_id=True):
            if "function" not in raw_tool_call:
                return None
            arguments = raw_tool_call["function"]["arguments"]

            if partial:
                try:
                    from langchain_core.utils.json import parse_partial_json

                    return _orig_parse_tool_call(raw_tool_call, partial=True, strict=strict, return_id=return_id)
                except Exception:
                    return None
            elif not arguments:
                return {
                    "name": raw_tool_call["function"].get("name") or "",
                    "args": {},
                    "id": raw_tool_call.get("id"),
                }

            # 先尝试智能修复
            parsed = _parse_args_smart_fix(arguments)
            if parsed is not None:
                from langchain_core.messages.tool import tool_call as _tc
                from langchain_core.messages.tool import ToolCall

                result = {
                    "name": raw_tool_call["function"].get("name") or "",
                    "args": parsed,
                }
                if return_id:
                    result["id"] = raw_tool_call.get("id")
                return _tc(**result)

            # 修复失败，回退原始行为（会报 invalid）
            return _orig_parse_tool_call(raw_tool_call, partial=partial, strict=strict, return_id=return_id)

        import langchain_core.output_parsers.openai_tools as _oa_tools

        _oa_tools.parse_tool_call = _patched_parse_tool_call
        logger.info("[LLM] ✅ parse_tool_call JSON 智能修复 patch 已应用")
    except Exception as e:
        logger.error(f"[LLM] ⚠️ patch parse_tool_call 失败: {e}")

    # Patch parse_partial_json：LangChain 的 init_tool_calls() 直接调用 parse_partial_json，
    # 而不是 parse_tool_call。如果不 patch 这里，流式路径仍会产生 invalid_tool_calls。
    # 这个 patch 优先于 _parse_args_smart_fix 的修复（_parse_args_smart_fix 在非流式路径生效）。
    try:
        from langchain_core.utils.json import parse_partial_json as _orig_parse_partial_json

        _orig_parse_partial_json_ref = _orig_parse_partial_json

        def _patched_parse_partial_json(s: str, *, strict: bool = False) -> Any:
            # 先尝试原始解析
            try:
                return _orig_parse_partial_json_ref(s, strict=strict)
            except Exception:
                pass

            # 修复尾随逗号（DeepSeek thinking 模式的常见问题）
            fixed = s
            for _ in range(10):
                prev = fixed
                fixed = re.sub(r",(\s*)([}\]])", r"\2", fixed)
                if fixed == prev:
                    break
            if fixed != s:
                try:
                    import json

                    return json.loads(fixed, strict=strict)
                except Exception:
                    pass

            # 修复中文/弯引号
            for old, new in [
                ("\u201c", '"'),
                ("\u201d", '"'),
                ("\u300c", '"'),
                ("\u300d", '"'),
                ("\u2018", "'"),
                ("\u2019", "'"),
            ]:
                fixed = fixed.replace(old, new)
            try:
                import json

                return json.loads(fixed, strict=strict)
            except Exception:
                pass

            return _orig_parse_partial_json_ref(s, strict=strict)

        import langchain_core.utils.json as _json_mod

        _json_mod.parse_partial_json = _patched_parse_partial_json

        # 关键：langchain_core.messages.ai 使用了 `from langchain_core.utils.json import parse_partial_json`
        # 这创建了一个本地引用，必须同时 patch 这个本地引用才能让 init_tool_calls() 使用修复后的版本
        import langchain_core.messages.ai as _ai_mod

        _ai_mod.parse_partial_json = _patched_parse_partial_json

        logger.info("[LLM] ✅ parse_partial_json trailing-comma patch 已应用（utils + ai）")
    except Exception as e:
        logger.error(f"[LLM] ⚠️ patch parse_partial_json 失败: {e}")

    logger.info("[LLM] ✅ DeepSeek reasoning_content patch 已应用")


_apply_reasoning_content_patches()


class ChatOpenAI(_BaseChatOpenAI):
    """支持 reasoning_content 的 ChatOpenAI 子类。

    LangChain 底层不映射 reasoning_content 到 additional_kwargs，
    这个子类在流式处理时从原始 chunk 中提取 reasoning_content，
    注入到 AIMessageChunk.additional_kwargs["reasoning_content"] 中，
    使其可以被 agent 流式处理代码正确获取。
    """

    def _convert_chunk_to_generation_chunk(self, chunk, default_chunk_class, base_generation_info=None):
        generation_chunk = super()._convert_chunk_to_generation_chunk(chunk, default_chunk_class, base_generation_info)
        if generation_chunk is None:
            return None

        # LangChain normalizes OpenAI's prompt_tokens_details.cached_tokens,
        # but some compatible providers (notably DeepSeek) expose cache hits
        # only as top-level custom fields. Preserve the raw usage for the
        # accounting layer instead of losing those provider extensions.
        raw_usage = chunk.get("usage")
        if isinstance(raw_usage, dict):
            generation_chunk.message.response_metadata["raw_token_usage"] = dict(raw_usage)

        # 从原始 chunk 中提取 reasoning_content
        choices = chunk.get("choices", []) or chunk.get("chunk", {}).get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            reasoning_content = delta.get("reasoning_content")
            if reasoning_content:
                msg = generation_chunk.message
                if hasattr(msg, "additional_kwargs"):
                    msg.additional_kwargs["reasoning_content"] = reasoning_content

        return generation_chunk


def init_chat_model_with_reasoning(model_name: str, provider: str = ""):
    """
    创建支持 reasoning_content 的 ChatOpenAI 实例。

    等价于 langchain.chat_models.init_chat_model，但使用自定义的
    ChatOpenAI 子类，能在流式处理中正确提取 reasoning_content。
    仅用于 OpenAI 兼容接口。Anthropic 模型走 init_chat_model。
    """
    kwargs, effort = _resolve_llm_params(model_name, provider)
    model_provider = kwargs.pop("model_provider", None)

    # Anthropic 模型走标准 init_chat_model（内部会路由到 ChatAnthropic）
    if model_provider == "anthropic":
        llm = _init_chat_model_fallback(kwargs)
    else:
        # OpenAI 兼容接口：thinking 需要从顶层移到 extra_body
        if "thinking" in kwargs:
            thinking_cfg = kwargs.pop("thinking")
            extra_body = kwargs.get("extra_body") or {}
            extra_body["thinking"] = thinking_cfg
            kwargs["extra_body"] = extra_body
        llm = ChatOpenAI(**kwargs)
    # Local metadata is never sent to the provider. It controls visible reasoning
    # using exactly the configuration that created this client.
    llm._wence_reasoning_effort = effort
    return llm


def _init_chat_model_fallback(kwargs: dict):
    """Anthropic 模型走 init_chat_model，不做额外处理"""
    from langchain.chat_models import init_chat_model as _init_chat_model

    return _init_chat_model(model_provider="anthropic", **kwargs)


# ============== 配置文件路径 ==============

SETTINGS_FILE = get_user_settings_file()


# ============== 数据结构 ==============


@dataclass
class LLMProvider:
    """LLM 提供商配置"""

    name: str
    api_key: str
    base_url: str
    api_type: str  # openai / anthropic
    models: list[dict]  # 该 provider 下的模型列表


# ============== 配置读取 ==============


def load_user_settings() -> dict:
    """加载用户设置"""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["providers"] = enrich_providers(
                data.get("providers", []), load_model_parameters(), data.get("temperature", 0.5)
            )
            return data
        return {"providers": []}
    except Exception as e:
        logger.error(f"加载用户设置失败: {e}")
        return {"providers": []}


def normalize_base_url(base_url: str) -> str:
    """
    标准化 base_url
    - 移除末尾的 /
    - 如果没有版本后缀（如 /v1），自动添加 /v1
    """
    url = (base_url or "").rstrip("/")
    if not url:
        return ""

    # 检查是否已有版本后缀（如 /v1, /v2 等）
    if not re.search(r"/v\d+$", url):
        url = url + "/v1"

    return url


def infer_api_type(model_id: str, base_url: str, configured_type: str = "") -> str:
    """推断 provider 的 API 类型。"""
    if configured_type in {"openai", "anthropic"}:
        return configured_type

    lowered_url = (base_url or "").lower()
    lowered_model = (model_id or "").lower()

    # 官方 Anthropic 域名优先走 ChatAnthropic
    if "anthropic.com" in lowered_url:
        return "anthropic"

    # 其余场景默认走 OpenAI 兼容接口（可承载 Claude 代理/中转）
    if lowered_model.startswith("claude") and "anthropic" in lowered_url:
        return "anthropic"
    return "openai"


def get_providers_from_settings() -> dict[str, LLMProvider]:
    """从用户设置中获取所有已启用的提供商配置"""
    settings = load_user_settings()
    providers = {}

    for provider_data in settings.get("providers", []):
        if not provider_data.get("enabled", True):
            continue

        name = provider_key(provider_data.get("name", ""))
        if not name:
            continue

        base_url_raw = provider_data.get("baseUrl", "")
        configured_api_type = str(provider_data.get("apiType", "")).strip().lower()

        # 先用首个可用模型辅助推断，未提供则留空
        first_model_id = ""
        for m in provider_data.get("models", []):
            if isinstance(m, dict) and m.get("enabled", True):
                first_model_id = str(m.get("id", ""))
                break

        api_type = infer_api_type(first_model_id, base_url_raw, configured_api_type)
        normalized_base_url = base_url_raw.rstrip("/") if api_type == "anthropic" else normalize_base_url(base_url_raw)

        providers[name] = LLMProvider(
            name=provider_data.get("name", ""),
            api_key=provider_data.get("apiKey", ""),
            base_url=normalized_base_url,
            api_type=api_type,
            models=provider_data.get("models", []),
        )

    return providers


def find_provider_for_model(model_id: str, provider_name: str = "") -> tuple[LLMProvider | None, str]:
    """
    根据模型 ID 找到对应的提供商

    Returns:
        (provider, actual_model_id) - 提供商配置和实际模型ID
    """
    providers = get_providers_from_settings()

    # 遍历所有 provider，查找包含该模型的 provider
    for name, provider in providers.items():
        if provider_name and name != provider_key(provider_name):
            continue
        for model in provider.models:
            if model.get("id") == model_id and model.get("enabled", False):
                return provider, model_id

    # 如果没找到精确匹配，返回 None
    return None, model_id


def get_first_available_model() -> tuple[LLMProvider | None, str]:
    """获取第一个可用的模型"""
    providers = get_providers_from_settings()

    for provider_name, provider in providers.items():
        for model in provider.models:
            if model.get("enabled", False):
                return provider, model.get("id", "")

    return None, ""


def get_custom_prompt() -> str:
    """从 user_settings.json 读取用户自定义 Prompt"""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("customPrompt", "") or ""
    except Exception as e:
        logger.error(f"读取 customPrompt 失败: {e}")
    return ""


def get_proxy_config() -> dict:
    """从用户设置中获取代理配置

    Returns:
        {"enabled": bool, "host": str, "port": int}
    """
    settings = load_user_settings()
    proxy = settings.get("proxy", {})
    return {
        "enabled": proxy.get("enabled", False),
        "host": proxy.get("host", ""),
        "port": proxy.get("port", 0),
    }


def get_proxy_url() -> str | None:
    """根据 host + port 构建 http 代理 URL，未启用则返回 None"""
    cfg = get_proxy_config()
    if cfg["enabled"] and cfg["host"] and cfg["port"]:
        return f"http://{cfg['host']}:{cfg['port']}"
    return None


def get_http_proxy_url() -> str | None:
    """获取 http 代理 URL，未启用则返回 None"""
    return get_proxy_url()


def get_https_proxy_url() -> str | None:
    """获取 https 代理 URL，未启用则返回 None"""
    return get_proxy_url()


def get_httpx_proxy_url() -> str | None:
    """获取 httpx 使用的单一代理 URL，未启用则返回 None"""
    return get_proxy_url()


def get_reasoning_extra_body(model_name: str, effort: str = "medium") -> dict | None:
    """
    返回 OpenAI 兼容模型的 reasoning/thinking extra_body 参数。

    为未单独适配的兼容接口保留现有的多种启用参数格式。
    具体支持的字段及强度取值由提供商决定。
    """
    lowered = model_name.lower()

    # Preserve the existing compatibility fields for these providers.
    base = {
        "thinking": {"type": "enabled", "parameters": {"effort": effort}},
        "enable_thinking": True,
        "reasoning": {"type": "enabled"},
    }

    # Qwen 特定参数
    if "qwen" in lowered:
        base["thinking"] = {"type": "enabled"}

    return base


def get_disable_thinking_extra_body(model_name: str) -> dict | None:
    """
    返回禁用 thinking 的 extra_body 参数。

    为未单独适配的兼容接口保留现有的多种禁用参数格式。
    具体是否支持关闭推理由提供商决定。
    """
    # Preserve the existing compatibility fields for these providers.
    return {
        "thinking": {"type": "disabled"},
        "enable_thinking": False,
        "reasoning": {"type": "off"},
    }


def _apply_anthropic_parameters(kwargs: dict, model_name: str, effort: str, thinking_enabled: bool) -> None:
    """Map effort to Anthropic's output_config or legacy thinking-token budget."""
    lowered = model_name.lower().replace(".", "-")
    match = re.search(r"(opus|sonnet|haiku)-(\d+)(?:-(\d)(?!\d))?", lowered)
    family, major, minor = (match[1], int(match[2]), int(match[3] or 0)) if match else ("", 0, 0)
    version = (major, minor)
    adaptive = (family in {"opus", "sonnet"} and version >= (4, 6)) or major >= 5
    supports_effort = adaptive or (family == "opus" and version >= (4, 5))
    if supports_effort:
        mapped_effort = {"none": "low", "minimal": "low"}.get(effort, effort)
        if mapped_effort == "xhigh" and version < (4, 7):
            mapped_effort = "max" if adaptive else "high"
        kwargs["output_config"] = {"effort": mapped_effort}

    if adaptive:
        kwargs["thinking"] = {"type": "adaptive" if thinking_enabled else "disabled"}
    elif major >= 4 or "3-7-sonnet" in lowered:
        if thinking_enabled:
            if kwargs["max_tokens"] <= 1024:
                raise ValueError(
                    "Anthropic 深度思考要求 Max Tokens 大于 1024，请调整模型设置或将 Reasoning Effort 设为 none"
                )
            budget = {"minimal": 1024, "low": 2048, "medium": 4096, "high": 8192, "xhigh": 16384}[effort]
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": min(budget, kwargs["max_tokens"] - 1)}
        else:
            kwargs["thinking"] = {"type": "disabled"}

    # Anthropic's thinking modes constrain sampling; newer models do not accept
    # sampling controls at all. See platform.claude.com/docs/en/build-with-claude/thinking.
    if (thinking_enabled and "thinking" in kwargs) or version >= (4, 7) or major >= 5:
        kwargs.pop("temperature", None)
        kwargs.pop("top_p", None)
    elif kwargs["top_p"] == 1:
        kwargs.pop("top_p")
    else:
        # Anthropic disallows setting both temperature and top_p on newer models.
        kwargs.pop("temperature")


def _resolve_llm_params(model_name: str, provider: str = "") -> tuple[dict, str]:
    """
    根据模型名解析出 init_chat_model 所需的参数及保存的推理程度。
    不处理环境变量清理/恢复（由调用方负责）。
    """
    actual_model_name = resolve_model(model_name, provider)
    provider_info, _ = find_provider_for_model(actual_model_name, provider)

    if not provider_info:
        raise ValueError(f"未找到模型 {actual_model_name} 对应的提供商配置，请在设置中添加")

    if not provider_info.api_key:
        raise ValueError(f"提供商 {provider_info.name} 未配置 API Key")

    effective_api_type = infer_api_type(actual_model_name, provider_info.base_url, provider_info.api_type)
    proxy_url = get_https_proxy_url() or get_http_proxy_url()
    selected_model = next(model for model in provider_info.models if model.get("id") == actual_model_name)
    parameters = normalize_legacy_parameters(selected_model.get("parameters"))
    effort = parameters["reasoningEffort"]
    thinking_enabled = effort != "none"

    kwargs: dict = {
        "model": actual_model_name,
        "api_key": provider_info.api_key,
        "temperature": parameters["temperature"],
        "top_p": parameters["topP"],
        "max_tokens": parameters["maxTokens"],
        "streaming": True,
    }

    if effective_api_type == "anthropic":
        kwargs["model_provider"] = "anthropic"
        if provider_info.base_url:
            kwargs["base_url"] = provider_info.base_url
        if proxy_url:
            kwargs["anthropic_proxy"] = proxy_url
        _apply_anthropic_parameters(kwargs, actual_model_name, effort, thinking_enabled)
    else:
        kwargs["model_provider"] = "openai"
        kwargs["base_url"] = provider_info.base_url
        # OpenAI-compatible streaming APIs return usage only when explicitly
        # requested through stream_options.include_usage.
        kwargs["stream_usage"] = True
        if proxy_url:
            import httpx

            kwargs["http_client"] = httpx.Client(proxy=proxy_url)
            kwargs["http_async_client"] = httpx.AsyncClient(proxy=proxy_url)
        lowered = actual_model_name.lower()
        if "deepseek" in lowered or "deepseek.com" in provider_info.base_url.lower():
            # DeepSeek accepts medium as a compatibility alias; the switch and
            # effort belong to separate top-level request fields.
            kwargs["extra_body"] = {"thinking": {"type": "enabled" if thinking_enabled else "disabled"}}
            kwargs["reasoning_effort"] = effort if thinking_enabled else "none"
        elif re.match(r"^(?:o\d(?:-|$)|gpt-[56])", lowered):
            supports_none = re.match(r"^gpt-5\.[1-9]", lowered) is not None and "pro" not in lowered
            if effort == "none" and not supports_none:
                raise ValueError(
                    f"模型 {actual_model_name} 不支持 Reasoning Effort=none，请选择其支持的推理程度或更换模型"
                )
            kwargs["reasoning_effort"] = effort
            # GPT-5.1/5.2 accept sampling only with effort=none; older reasoning
            # models do not support these fields at all.
            if not supports_none or kwargs.get("reasoning_effort") != "none":
                kwargs.pop("temperature", None)
                kwargs.pop("top_p", None)
        elif re.match(r"^gpt-[34]", lowered) or "api.openai.com" in provider_info.base_url.lower():
            pass  # Non-reasoning OpenAI models reject thinking/effort parameters.
        elif thinking_enabled:
            kwargs["reasoning_effort"] = effort
            kwargs["extra_body"] = get_reasoning_extra_body(actual_model_name, effort)
        else:
            disable_extra = get_disable_thinking_extra_body(actual_model_name)
            if disable_extra:
                kwargs["extra_body"] = disable_extra
                logger.info("[LLM] Reasoning Effort=none，已发送禁用 thinking 参数")

    return kwargs, effort


def get_llm_init_kwargs(model_name: str, provider: str = "") -> dict:
    """
    获取 init_chat_model 所需的完整参数字典。

    用法: init_chat_model(**get_llm_init_kwargs("gpt-4o"))
    """
    kwargs, _effort = _resolve_llm_params(model_name, provider)
    return kwargs


class LLMClientManager:
    """LLM 客户端管理器"""

    _clients: dict[str, AsyncOpenAI] = {}

    @classmethod
    def get_client(cls, model_id: str) -> AsyncOpenAI:
        """
        根据模型 ID 获取对应的 AsyncOpenAI 客户端

        Args:
            model_id: 模型 ID，如 "gpt-4o", "glm-4.5"

        Returns:
            配置好的 AsyncOpenAI 客户端
        """
        # 解析模型，处理 auto
        actual_model_id = cls.resolve_model(model_id)

        # 查找对应的 provider
        provider, _ = find_provider_for_model(actual_model_id)

        if not provider:
            raise ValueError(f"未找到模型 {actual_model_id} 对应的提供商配置，请在设置中添加")

        if not provider.api_key:
            raise ValueError(f"提供商 {provider.name} 未配置 API Key")

        # 获取代理配置
        proxy_url = get_proxy_url()

        # 使用 provider name + base_url + proxy 作为缓存 key
        cache_key = f"{provider.name}:{provider.base_url}:{proxy_url or ''}"

        # 使用缓存
        if cache_key in cls._clients:
            return cls._clients[cache_key]

        # 创建新客户端
        import httpx as _httpx

        http_client = _httpx.AsyncClient(proxy=proxy_url) if proxy_url else None
        client = AsyncOpenAI(
            api_key=provider.api_key,
            base_url=provider.base_url,
            http_client=http_client,
        )

        cls._clients[cache_key] = client
        return client

    @classmethod
    def get_provider_info(cls, model_id: str) -> LLMProvider | None:
        """获取模型对应的提供商信息"""
        actual_model_id = cls.resolve_model(model_id)
        provider, _ = find_provider_for_model(actual_model_id)
        return provider

    @classmethod
    def get_default_model(cls, provider: str = "") -> str:
        """获取默认模型（第一个启用的模型，可按提供商过滤）"""
        if provider:
            # 根据提供商获取模型
            provider_config = cls._get_provider_config(provider)
            if provider_config:
                models = provider_config.get("models", [])
                for model in models:
                    if model.get("enabled", False):
                        return model.get("id", "gpt-4o")

        # 如果没找到指定提供商的模型，尝试获取第一个启用的模型
        _, model_id = get_first_available_model()
        if model_id:
            return model_id
        # 兜底返回
        return "gpt-4o"

    @classmethod
    def _get_provider_config(cls, provider_name: str) -> dict | None:
        """根据提供商名称获取配置"""
        try:
            settings_data = load_user_settings()
            for p in settings_data.get("providers", []):
                if provider_key(p.get("name", "")) == provider_key(provider_name):
                    return p
        except Exception:
            pass
        return None

    @classmethod
    def resolve_model(cls, model_id: str | None, provider: str = "") -> str:
        """
        解析模型 ID，处理 auto 和空值

        Args:
            model_id: 用户指定的模型 ID，可能是 "auto" 或具体模型
            provider: 模型提供商名称

        Returns:
            实际使用的模型 ID
        """
        if not model_id or model_id == "auto":
            return cls.get_default_model(provider)
        return model_id

    @classmethod
    def clear_cache(cls):
        """清除客户端缓存（配置变更后调用）"""
        cls._clients.clear()


# ============== 便捷函数 ==============


def get_llm_client(model_id: str) -> AsyncOpenAI:
    """获取 LLM 客户端的便捷函数"""
    return LLMClientManager.get_client(model_id)


def resolve_model(model_id: str | None, provider: str = "") -> str:
    """解析模型 ID 的便捷函数"""
    return LLMClientManager.resolve_model(model_id, provider)


def create_sync_llm_client(
    model_name: str,
    provider: str = "",
    temperature: float | None = None,
) -> Any | None:
    """
    创建同步的 ChatOpenAI 客户端（用于长期记忆提取等不需要流式的场景）。

    Args:
        model_name: 模型名称
        provider: 可选的提供商
        temperature: 可选的温度参数，不提供则使用模型默认值

    Returns:
        ChatOpenAI 实例，失败返回 None
    """
    try:
        kwargs = get_llm_init_kwargs(model_name, provider=provider)
        model_provider = kwargs.pop("model_provider", None)
        kwargs["streaming"] = False

        # Preserve provider sampling restrictions when memory extraction overrides temperature.
        if temperature is not None and "temperature" in kwargs:
            kwargs["temperature"] = temperature

        if model_provider == "anthropic":
            return _init_chat_model_fallback(kwargs)

        # OpenAI 兼容接口
        return ChatOpenAI(**kwargs)
    except Exception as e:
        logger.error(f"[LLM] 创建同步客户端失败: {e}")
        return None

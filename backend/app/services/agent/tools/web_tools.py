"""单智能体网络工具。"""

from langchain_core.tools import tool
from langgraph.config import get_stream_writer


@tool
def web_fetch(url: str) -> str:
    """拓取网页内容 - 根据 URL 获取网页正文，自动清洗 HTML 标签、脚本、样式等。"""
    from curl_cffi import requests as curl_requests
    from bs4 import BeautifulSoup

    from app.services.llm_client import get_httpx_proxy_url

    writer = get_stream_writer()
    writer({"type": "status", "content": f"🌐 正在拓取网页: {url}"})
    print(f"[web_fetch] 开始拓取: {url}")

    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": origin + "/",
            "Cache-Control": "max-age=0",
        }
        proxy_url = get_httpx_proxy_url()
        proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None

        session = curl_requests.Session(impersonate="chrome131")
        if proxies:
            session.proxies = proxies
        session.verify = False

        resp = session.get(url, headers=headers, timeout=20, allow_redirects=True)
        if resp.status_code == 403:
            print(f"[web_fetch] 收到 403，尝试预热 Cookie: {origin}")
            session.get(origin, headers=headers, timeout=10, allow_redirects=True)
            resp = session.get(url, headers=headers, timeout=20, allow_redirects=True)

        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            text = resp.text[:8000]
            print(f"[web_fetch] ✅ 非 HTML 内容，直接返回 {len(text)} 字符")
            return text

        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe", "svg"]):
            tag.decompose()

        main_content = (
            soup.find("article")
            or soup.find("main")
            or soup.find(attrs={"role": "main"})
            or soup.find(
                "div",
                class_=lambda c: c
                and any(
                    k in (c if isinstance(c, str) else " ".join(c))
                    for k in ["content", "article", "post", "entry", "main"]
                ),
            )
        )
        target = main_content if main_content else soup.body if soup.body else soup

        lines = []
        for elem in target.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "blockquote", "pre", "code"]
        ):
            text = elem.get_text(strip=True)
            if not text:
                continue
            tag_name = elem.name
            if tag_name.startswith("h"):
                level = tag_name[1]
                lines.append(f"{'#' * int(level)} {text}")
            elif tag_name == "li":
                lines.append(f"- {text}")
            elif tag_name in ("pre", "code"):
                lines.append(f"```\n{text}\n```")
            elif tag_name == "blockquote":
                lines.append(f"> {text}")
            else:
                lines.append(text)

        result = "\n\n".join(lines)
        if len(result) < 100:
            result = target.get_text(separator="\n", strip=True)
        if len(result) > 8000:
            result = result[:8000] + "\n\n[内容已截断，原文过长]"

        title = soup.title.get_text(strip=True) if soup.title else ""
        if title:
            result = f"标题: {title}\n\n{result}"

        print(f"[web_fetch] ✅ 已拓取 {len(result)} 字符")
        writer({"type": "status", "content": "✅ 网页拓取完成"})
        return result

    except curl_requests.errors.RequestsError as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        print(f"[web_fetch] ❌ 拓取失败: HTTP {status or e}")
        writer({"type": "status", "content": "❌ 该网页无法访问，跳过"})
        return "该网页无法访问（已跳过）。请直接使用已有的搜索摘要继续完成任务，不要因此放弃生成文档。"
    except Exception as e:
        print(f"[web_fetch] ❌ 拓取失败: {e}")
        writer({"type": "status", "content": "❌ 该网页无法访问，跳过"})
        return "该网页无法访问（已跳过）。请直接使用已有的搜索摘要继续完成任务，不要因此放弃生成文档。"

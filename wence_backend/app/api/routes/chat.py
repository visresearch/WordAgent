"""
聊天处理路由
"""

import json
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.chat import ChatRequest, ChatResponse, ModelsResponse, ModelInfo
from app.core.config import settings
from app.core.agent import process_writing_request_stream  # 暂时不用真实 AI

router = APIRouter()

# 可用模型列表（可以从配置文件或数据库加载）
AVAILABLE_MODELS = [
    ModelInfo(id="gpt-5", name="GPT-5", provider="OpenAI", description="强大的GPT模型"),
    ModelInfo(id="auto", name="Auto", provider="WenceAI", description="自动选择最佳模型"),
]

# 模拟 AI 输出的 JSON 数据
MOCK_AI_RESPONSE = {
  "text": "1.1  实习目的\r（1）通过本次实习，将课堂所学的计算机相关理论知识与企业实际工程项目相结合，深入了解相关技术在真实场景中的应用方式与实现过程，加深对专业基础知识和核心技术的理解，提升理论联系实际的能力。\r（2）在实习过程中，系统了解企业的软件开发流程、项目管理模式及技术规范，参与实际系统或模块的设计、开发与调试工作，逐步提升工程实践能力、技术应用能力以及独立分析问题和解决问题的能力。\r（3）通过融入真实的企业工作环境，增强职业责任意识和团队协作意识，学习良好的职业行为规范与工作方法，明确个人职业发展方向，为今后的专业学习、毕业设计及就业发展奠定坚实基础。\r1.2  个人目标\r（1）在已有的计算机专业基础上，进一步深化对机器人系统与智能导航相关技术的理解，重点提升在 ROS2 框架下的系统开发能力，熟悉 SLAM、定位、路径规划与导航等核心模块在实际项目中的应用，为今后从事相关技术方向打下扎实基础。\r（2）通过持续参与实际工程项目，不断提升工程实践能力与系统调试能力，逐步培养独立分析问题、定位问题并解决问题的能力，增强对复杂系统整体架构和工程细节的把控能力，向具备实际项目经验的工程型人才目标迈进。\r（3）在实践过程中不断完善自身职业素养，强化责任意识和团队协作意识，明确未来在智能机器人、自动化系统及相关技术领",
  "paragraphs": [
    {
      "text": "1.1  实习目的",
      "alignment": "left",
      "lineSpacing": 12,
      "indentLeft": 0,
      "indentRight": 0,
      "indentFirstLine": 0,
      "spaceBefore": 8.324999809265137,
      "spaceAfter": 8.324999809265137,
      "runs": [
        {"text": "1.1  ", "fontName": "Times New Roman", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": "实习目的", "fontName": "黑体", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False}
      ],
      "tabStops": [],
      "styleName": "标题 2"
    },
    {
      "text": "（1）通过本次实习，将课堂所学的计算机相关理论知识与企业实际工程项目相结合，深入了解相关技术在真实场景中的应用方式与实现过程，加深对专业基础知识和核心技术的理解，提升理论联系实际的能力。",
      "alignment": "justify",
      "lineSpacing": 18,
      "indentLeft": 0,
      "indentRight": 0,
      "indentFirstLine": 24,
      "spaceBefore": 0,
      "spaceAfter": 0,
      "runs": [
        {"text": "（", "fontName": "宋体", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": "1", "fontName": "Times New Roman", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": "）通过本次实习，将课堂所学的计算机相关理论知识与企业实际工程项目相结合，深入了解相关技术在真实场景中的应用方式与实现过程，加深对专业基础知识和核心技术的理解，提升理论联系实际的能力。", "fontName": "宋体", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False}
      ],
      "tabStops": [],
      "styleName": "正文缩进段落"
    },
    {
      "text": "（2）在实习过程中，系统了解企业的软件开发流程、项目管理模式及技术规范，参与实际系统或模块的设计、开发与调试工作，逐步提升工程实践能力、技术应用能力以及独立分析问题和解决问题的能力。",
      "alignment": "justify",
      "lineSpacing": 18,
      "indentLeft": 0,
      "indentRight": 0,
      "indentFirstLine": 24,
      "spaceBefore": 0,
      "spaceAfter": 0,
      "runs": [
        {"text": "（", "fontName": "宋体", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": "2", "fontName": "Times New Roman", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": "）在实习过程中，系统了解企业的软件开发流程、项目管理模式及技术规范，参与实际系统或模块的设计、开发与调试工作，逐步提升工程实践能力、技术应用能力以及独立分析问题和解决问题的能力。", "fontName": "宋体", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False}
      ],
      "tabStops": [],
      "styleName": "正文缩进段落"
    },
    {
      "text": "（3）通过融入真实的企业工作环境，增强职业责任意识和团队协作意识，学习良好的职业行为规范与工作方法，明确个人职业发展方向，为今后的专业学习、毕业设计及就业发展奠定坚实基础。",
      "alignment": "justify",
      "lineSpacing": 18,
      "indentLeft": 0,
      "indentRight": 0,
      "indentFirstLine": 24,
      "spaceBefore": 0,
      "spaceAfter": 0,
      "runs": [
        {"text": "（", "fontName": "宋体", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": "3", "fontName": "Times New Roman", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": "）通过融入真实的企业工作环境，增强职业责任意识和团队协作意识，学习良好的职业行为规范与工作方法，明确个人职业发展方向，为今后的专业学习、毕业设计及就业发展奠定坚实基础。", "fontName": "宋体", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False}
      ],
      "tabStops": [],
      "styleName": "正文缩进段落"
    },
    {
      "text": "1.2  个人目标",
      "alignment": "left",
      "lineSpacing": 12,
      "indentLeft": 0,
      "indentRight": 0,
      "indentFirstLine": 0,
      "spaceBefore": 8.324999809265137,
      "spaceAfter": 8.324999809265137,
      "runs": [
        {"text": "1.2  ", "fontName": "Times New Roman", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": "个人目标", "fontName": "黑体", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False}
      ],
      "tabStops": [],
      "styleName": "标题 2"
    },
    {
      "text": "（1）在已有的计算机专业基础上，进一步深化对机器人系统与智能导航相关技术的理解，重点提升在 ROS2 框架下的系统开发能力，熟悉 SLAM、定位、路径规划与导航等核心模块在实际项目中的应用，为今后从事相关技术方向打下扎实基础。",
      "alignment": "justify",
      "lineSpacing": 18,
      "indentLeft": 0,
      "indentRight": 0,
      "indentFirstLine": 24,
      "spaceBefore": 0,
      "spaceAfter": 0,
      "runs": [
        {"text": "（", "fontName": "宋体", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": "1", "fontName": "Times New Roman", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": "）在已有的计算机专业基础上，进一步深化对机器人系统与智能导航相关技术的理解，重点提升在", "fontName": "宋体", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": " ROS2 ", "fontName": "Times New Roman", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": "框架下的系统开发能力，熟悉", "fontName": "宋体", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": " SLAM", "fontName": "Times New Roman", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": "、定位、路径规划与导航等核心模块在实际项目中的应用，为今后从事相关技术方向打下扎实基础。", "fontName": "宋体", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False}
      ],
      "tabStops": [],
      "styleName": "正文缩进段落"
    },
    {
      "text": "（2）通过持续参与实际工程项目，不断提升工程实践能力与系统调试能力，逐步培养独立分析问题、定位问题并解决问题的能力，增强对复杂系统整体架构和工程细节的把控能力，向具备实际项目经验的工程型人才目标迈进。",
      "alignment": "justify",
      "lineSpacing": 18,
      "indentLeft": 0,
      "indentRight": 0,
      "indentFirstLine": 24,
      "spaceBefore": 0,
      "spaceAfter": 0,
      "runs": [
        {"text": "（", "fontName": "宋体", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": "2", "fontName": "Times New Roman", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": "）通过持续参与实际工程项目，不断提升工程实践能力与系统调试能力，逐步培养独立分析问题、定位问题并解决问题的能力，增强对复杂系统整体架构和工程细节的把控能力，向具备实际项目经验的工程型人才目标迈进。", "fontName": "宋体", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False}
      ],
      "tabStops": [],
      "styleName": "正文缩进段落"
    },
    {
      "text": "（3）在实践过程中不断完善自身职业素养，强化责任意识和团队协作意识，明确未来在智能机器人、自动化系统及相关技术领域的发展方向，为后续的专业学习、毕业设计以及职业发展做好充分准备。",
      "alignment": "justify",
      "lineSpacing": 18,
      "indentLeft": 0,
      "indentRight": 0,
      "indentFirstLine": 24,
      "spaceBefore": 0,
      "spaceAfter": 0,
      "runs": [
        {"text": "（", "fontName": "宋体", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": "3", "fontName": "Times New Roman", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False},
        {"text": "）在实践过程中不断完善自身职业素养，强化责任意识和团队协作意识，明确未来在智能机器人、自动化系统及相关技术领域的发展方向，为后续的专业学习、毕业设计以及职业发展做好充分准备。", "fontName": "宋体", "fontSize": 12, "bold": False, "italic": False, "underline": "none", "color": "#000000", "highlight": "none", "strikethrough": False, "superscript": False, "subscript": False}
      ],
      "tabStops": [],
      "styleName": "正文缩进段落"
    }
  ],
  "tables": [],
  "fields": [],
  "images": []
}


@router.get("/models", response_model=ModelsResponse)
async def get_models():
    """
    获取可用模型列表
    """
    return ModelsResponse(
        success=True,
        models=AVAILABLE_MODELS
    )

async def generate_stream(request: ChatRequest):
    """生成流式响应 - 使用 Agent + Tool Calling"""
    async for chunk in process_writing_request_stream(
        message=request.message,
        document_json=request.documentJson,
        history=request.history
    ):
        yield chunk


# ============== 模拟 AI 输出（调试用，注释掉即可）==============
# async def generate_stream_mock(request: ChatRequest):
#     """生成流式响应 - 模拟 AI 输出"""
#     mock_text_parts = ["好的，", "我来帮您处理这段文档。", "\n\n", "以下是处理后的结果："]
#     for part in mock_text_parts:
#         yield f"data: {json.dumps({'type': 'text', 'content': part}, ensure_ascii=False)}\n\n"
#         await asyncio.sleep(0.3)
#     yield f"data: {json.dumps({'type': 'json', 'content': MOCK_AI_RESPONSE}, ensure_ascii=False)}\n\n"
#     yield "data: [DONE]\n\n"


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天接口
    使用 SSE 返回流式响应
    """
    print("=" * 50)
    print("收到流式聊天请求:")
    print(f"用户消息: {request.message}")
    print(f"模式: {request.mode}")
    print(f"模型: {request.model}")
    print(f"文档 JSON: {json.dumps(request.documentJson, ensure_ascii=False, indent=2)}")
    print("=" * 50)

    return StreamingResponse(
        generate_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

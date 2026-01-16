from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.config import get_stream_writer

# 使用 OpenAI 兼容 API（硬编码配置）
model = ChatOpenAI(
    model="qwen2.5:7b",
    temperature=0,
    api_key="sk-l4ET3MWX8vsqAVqv0tXt5o1bbc7sh5L1fDV7oV66oDPrxLlQ",
    base_url="http://localhost:11434/v1",
    streaming=True,  # 启用流式输出
)


# 定义工具
@tool
def multiply(a: int, b: int) -> int:
    """Multiply a and b.

    Args:
        a: First int
        b: Second int
    """
    return a * b


@tool
def add(a: int, b: int) -> int:
    """Adds a and b.

    Args:
        a: First int
        b: Second int
    """
    return a + b


@tool
def divide(a: int, b: int) -> float:
    """Divide a by b.

    Args:
        a: First int
        b: Second int
    """
    return a / b


# 绑定工具到模型
tools = [add, multiply, divide]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)


# 定义节点函数
def call_model(state: MessagesState):
    """调用 LLM - 支持流式输出"""
    writer = get_stream_writer()
    writer("🤖 正在思考...")
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def call_tools(state: MessagesState):
    """执行工具调用"""
    from langchain_core.messages import ToolMessage
    
    writer = get_stream_writer()
    
    last_message = state["messages"][-1]
    results = []
    for tool_call in last_message.tool_calls:
        tool_fn = tools_by_name[tool_call["name"]]
        writer(f"🔧 调用工具: {tool_call['name']}")
        result = tool_fn.invoke(tool_call["args"])
        writer(f"✅ 结果: {result}")
        results.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))
    return {"messages": results}


def should_call_tools(state: MessagesState) -> str:
    """判断是否需要调用工具"""
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "call_tools"
    return END


# 构建 LangGraph 图
graph = StateGraph(MessagesState)

# 添加节点
graph.add_node("call_model", call_model)
graph.add_node("call_tools", call_tools)

# 添加边
graph.add_edge(START, "call_model")
graph.add_conditional_edges("call_model", should_call_tools, {"call_tools": "call_tools", END: END})
graph.add_edge("call_tools", "call_model")  # 工具执行后回到模型

# 编译图
app = graph.compile()


# 测试
if __name__ == "__main__":
    from langchain_core.messages import HumanMessage

    print("=" * 50)
    print("LangGraph 流式输出示例")
    print("=" * 50)

    # 测试问题
    questions = [
        "3 乘以 4 等于多少？",
        "100 除以 5 再加 20 等于多少？",
        "你好，今天天气怎么样？写一段100字的回答。",  # 不需要工具的问题
    ]

    for q in questions:
        print(f"\n问题: {q}")
        print(f"回答: ", end="", flush=True)
        
        # 使用 stream 方法进行流式处理
        response = app.stream(
            {"messages": [HumanMessage(content=q)]},
            stream_mode=['messages', 'custom']
        )
        
        for input_type, chunk in response:
            if input_type == "messages":
                # AI 的输出内容（流式 token）
                if chunk and len(chunk) > 0:
                    content = chunk[0].content
                    if content:
                        print(content, end="", flush=True)
            elif input_type == "custom":
                # 工具执行的输出内容
                print(f"\n{chunk}", end="", flush=True)
        
        print("\n" + "-" * 30)

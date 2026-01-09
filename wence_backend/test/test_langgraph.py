from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langgraph.graph import StateGraph, MessagesState, START, END

# 使用 OpenAI 兼容 API（硬编码配置）
model = ChatOpenAI(
    model="gpt-4",
    temperature=0,
    api_key="sk-l4ET3MWX8vsqAVqv0tXt5o1bbc7sh5L1fDV7oV66oDPrxLlQ",
    base_url="https://api.chatanywhere.tech"
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
    """调用 LLM"""
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def call_tools(state: MessagesState):
    """执行工具调用"""
    from langchain_core.messages import ToolMessage
    last_message = state["messages"][-1]
    results = []
    for tool_call in last_message.tool_calls:
        tool_fn = tools_by_name[tool_call["name"]]
        result = tool_fn.invoke(tool_call["args"])
        results.append(ToolMessage(
            content=str(result),
            tool_call_id=tool_call["id"]
        ))
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
graph.add_conditional_edges("call_model", should_call_tools, {
    "call_tools": "call_tools",
    END: END
})
graph.add_edge("call_tools", "call_model")  # 工具执行后回到模型

# 编译图
app = graph.compile()


# 测试
if __name__ == "__main__":
    from langchain_core.messages import HumanMessage
    
    print("=" * 50)
    print("LangGraph 工具调用示例")
    print("=" * 50)
    
    # 测试问题
    questions = [
        "3 乘以 4 等于多少？",
        "100 除以 5 再加 20 等于多少？",
        "你好，今天天气怎么样？"  # 不需要工具的问题
    ]
    
    for q in questions:
        print(f"\n问题: {q}")
        result = app.invoke({"messages": [HumanMessage(content=q)]})
        final_answer = result["messages"][-1].content
        print(f"回答: {final_answer}")
        print("-" * 30)
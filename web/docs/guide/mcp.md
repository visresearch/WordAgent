# MCP 服务器配置

MCP（Model Context Protocol）是一种开放协议，允许你向 AI 接入**外部工具和数据源**，极大扩展智能体的能力边界。

## 什么是 MCP

通过 MCP，你可以让 AI 调用自定义工具，例如：

- 查询数据库或本地文件
- 调用第三方 API（天气、股票、搜索引擎等）
- 执行系统命令或脚本
- 接入企业内部系统

文策 AI 的智能体会自动发现并调用已配置的 MCP 工具，无需修改代码。

## 利用魔塔社区配置远程 MCP 服务器

魔塔社区在[MCP广场](https://www.modelscope.cn/mcp)中有大量现成的 MCP 服务器可以直接使用。

这里推荐安装 **Tavily智搜** 和 **可视化图表-MCP-Server** 两款功能强大的 MCP 服务器。

### Tavily智搜

**Tavily智搜**是为智能体专用的联网工具，具有网页搜索访问、网页抓取功能，可以极大提升智能体的资料搜集和信息更新能力。

![](/modelscope.png)

![](/modelscope_tavily.png)

点开按照配置说明在右侧**服务配置**中点击配置按钮，填写MCP服务器所需要的TAVILY_API_KEY，传输类型选择`Streamable Http`，鉴权类型选择`无鉴权`，有效期选择`长期有效`，点击重置服务即可获得MCP配置json字符串。如：

```json
{
  "mcpServers": {
    "tavily-mcp": {
      "type": "streamable_http",
      "url": "https://mcp.api-inference.modelscope.net/xxxxxxxxxxxxxx/mcp"
    }
  }
}
```
将其复制到文策AI的设置面板中 **MCP** 标签页的 JSON 配置框中，点击保存即可。

![](/mcp.png)

### 可视化图表-MCP-Server

**可视化图表-MCP-Server**是一个专门用于生成可视化图表的 MCP 服务器，支持多种图表类型（折线图、柱状图、饼图等），并且可以直接返回图片URL，非常适合需要数据分析和可视化的智能体应用场景。

![](/mcp-server-chart.png)

下面是使用**可视化图表-MCP-Server**的一个场景示例：

![](/mcp_example.png)

::: tip 提示
更多现成的 MCP 服务器可以在 [魔塔社区MCP广场](https://www.modelscope.cn/mcp) 中找到。
:::

## 验证是否生效

配置完成后，你可以点击 **测试连接** 按钮验证 MCP 服务器是否配置成功。如果看到有返回HTTP 状态码200的成功响应，说明配置已生效。


# 中国主流 AI 平台接入规范

本项目不追求全球所有模型。业务工具只实现一套；平台适配只处理工具 schema、调用 ID、消息回填、模型状态字段和错误格式差异。

**当前工程状态：** Rongwei 的 REST 接口、规范化工具目录和通用工具调用分发器已写入开发分支。下表中的官方协议已按官方文档核对；各平台的 Rongwei 实机调用和端到端验收仍待完成。

## 首批范围与优先级

| 平台 | 优先级 | 接入路径 | 官方协议状态 | Rongwei 实机验收 |
|---|---:|---|---|---|
| DeepSeek | 1 | DeepSeek API Tool Calls | 已确认 | 未完成 |
| 通义千问 | 2 | 阿里云百炼 / DashScope Function Calling | 已确认 | 未完成 |
| 豆包 | 3 | 火山方舟 / Ark Function Calling | 已确认 | 未完成 |
| 智谱 GLM | 4 | BigModel Function Tool Calls；按模型/接口选择 | 已确认 | 未完成 |
| 百度千帆 / ERNIE | 5 | Qianfan v2 Chat Completions tool_calls | 已确认 | 未完成 |
| Kimi / Moonshot | 后续候选 | 原生 API 或 Model Studio 代接 | 需单独核实 | 不纳入第一轮 |

这里的“官方协议已确认”只说明官方接口存在相应工具调用方式，并不代表 Rongwei 已经和该平台实机连接成功。每个平台仍需按具体模型 ID、API 版本、账号区域和参数要求验证。

## 官方协议核对

### 1. DeepSeek

官方 Tool Calls 文档给出 tools/function、模型返回 tool_calls、应用执行工具并回填结果的流程。DeepSeek V3.2 开始支持思考模式工具调用。思考模式下，后续请求必须完整回传 assistant 消息中的 `reasoning_content`，即使上一轮没有实际调用工具也一样；不遵守可能收到 400 错误。Chat Completions 不支持在对话中间插入任意外部工具调用消息。

官方资料：
- https://api-docs.deepseek.com/zh-cn/guides/tool_calls/
- https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/

**Rongwei 适配要求：** 原样保留模型返回的 assistant tool-call message；不要丢弃 `reasoning_content`、tool call id 或 function arguments。

### 2. 通义千问 / 阿里云百炼

Model Studio 的 Function Calling 文档说明了工具定义、模型生成调用指令、应用执行函数、回填结果并再次调用模型的标准流程。文档列出的可支持模型不只 Qwen，还包括部分 DeepSeek、GLM、Kimi 等模型；实际能力依具体模型系列和账号服务而定。

官方资料：
- https://docs.modelstudio.console.alibabacloud.com/zh/model-studio/qwen-function-calling
- https://docs.modelstudio.console.alibabacloud.com/en/model-studio/qwen-function-calling

**Rongwei 适配要求：** 优先实现 DashScope Function Calling；按账号区域和百炼工作空间配置 Base URL，不在代码中硬编码单一区域端点。

**特殊兼容提示：** 在阿里云 Model Studio 通过其 Function Calling 接口调用 GLM 系列时，官方说明通常需要在请求中增加 `extra_body={"tool_stream": true}`；具体模型例外应以对应模型文档为准。这是“GLM 通过百炼”的参数，不应误套到所有智谱原生 API 请求。

### 3. 豆包 / 火山方舟

火山方舟官方 Function Calling 文档说明模型返回工具名和参数，应用负责执行，再把工具结果回传给模型，以继续生成答案。

官方资料：
- https://docs.volcengine.com/docs/ark/function-calling

**Rongwei 适配要求：** 使用 Ark 当前模型支持的工具定义格式；保留 tool call id；回填结果前验证调用名称和 JSON 参数；设置最大调用轮数和超时，避免无限循环。

### 4. 智谱 GLM

**首批接入优先走阿里云百炼托管的 GLM Function Calling**，因为百炼官方 Function Calling 支持模型列表明确包括 GLM-5.3、GLM-5.2、GLM-5.1 和 GLM-5；其中 GLM 调用 Function Calling 时通常需要在请求里传入 `extra_body={"tool_stream": true}`，GLM-5.3 默认已开启该参数。实际仍以具体模型版本的文档为准。

官方资料：
- https://docs.modelstudio.console.alibabacloud.com/zh/model-studio/qwen-function-calling
- https://docs.bailian.console.aliyun.com/zh/model-studio/glm-zhipu

**Rongwei 适配要求：** 使用百炼兼容接口和 DashScope API Key。项目中的 GLM 适配器配置为 `DASHSCOPE_API_KEY`、`GLM_MODEL` 和可覆盖的 `GLM_BASE_URL`，默认北京兼容模式 endpoint，并传入 `tool_stream=true`。

智谱原生 BigModel 的助手对话 API 页面目前标注为 deprecated，虽然文档返回结构中包含 tool_calls，但不应把这个旧助手 API 当作第一接入方案。原生 BigModel Chat Completions 若要列入后续支持，需另行确认当前非弃用 API、可用模型列表及完整工具调用往返，再增加单独适配器。

### 5. 百度千帆 / ERNIE

百度千帆官方 `POST /v2/chat/completions` 文档定义了 `tool_calls`、函数名和 JSON 参数字符串，并要求把模型返回的 assistant tool-call message 与匹配的 `role=tool` 消息放回下一轮 messages。工具返回消息需要使用真实的 `tool_call_id`。官方文档最近更新时间为 2026-11-11。

官方资料：
- https://cloud.baidu.com/doc/qianfan-api/s/wmwbl48n4
- https://cloud.baidu.com/doc/qianfan-api/s/Amwbl4wln

**Rongwei 适配要求：** 第一轮先支持 v2 Chat Completions 的函数调用；千帆 Agent 应用的 `/v2/app/conversation/runs` 和 SSE 事件协议作为单独适配路径，不与 Chat Completions 混为一谈。

### 6. Kimi / Moonshot（后续候选）

Kimi 的 API 概览说明了 API 格式兼容情况，但不能据此推断所有模型、参数和自定义 function call 行为都与其他 OpenAI-compatible API 完全相同。阿里云 Model Studio 的 Function Calling 文档列出部分 Kimi 模型，但这属于百炼托管路径，不代表 Moonshot 原生 API 已通过 Rongwei 测试。

官方资料：
- https://www.kimi.ai/zh-hans/help/kimi-api/api-overview
- https://docs.modelstudio.console.alibabacloud.com/zh/model-studio/qwen-function-calling

## 当前统一工具调用流程

1. 宿主 AI 接收用户提供的客户文字、截图、广告或车型资料。
2. 宿主 AI 将已观察事实和证据整理成 Rongwei 工具参数。
3. 模型返回 function/tool call，包含调用 ID、工具名称和 arguments。
4. 宿主将工具调用交给 Rongwei 的 `/v1/tool-calls/dispatch`（或在本地调用 SDK）。
5. Rongwei 验证参数和证据引用，执行业务规则，按原始调用 ID 返回 `role=tool` 消息。
6. 宿主将**原始 assistant tool-call message 不变地保留**，追加工具结果，再按平台协议请求模型继续回答。
7. 模型输出自然语言销售分析和客户语言回复草稿；用户自行审核发送。

## 每个平台的实机验收清单

1. 按当前账号、区域和模型版本成功鉴权。
2. 正确获取/配置该平台支持的工具定义。
3. 模型能触发 Rongwei 业务工具，并返回符合约定的参数。
4. Rongwei 能解析并校验工具调用、执行真实业务逻辑。
5. 结果按正确的 call ID 和消息角色回传给模型。
6. 多轮调用中保留 reasoning、tool metadata、图片/多模态字段等该平台所需上下文。
7. 测试并发工具调用、非法 JSON、未知工具、工具超限、限流、超时、欠费和接口错误。
8. 不打印 API Key，不把客户原始聊天和个人信息写入日志。
9. 同一套汽车出口验收样例在各平台得到一致的业务规则和结构化结果。
10. 在 CI 或可复现集成报告中留下模型 ID、接口版本、测试日期和通过/失败结果。

## 不采用的做法

- 不因接口兼容 OpenAI 就宣称该模型全部兼容。
- 不把 MCP 支持等同于 Function Calling 支持。
- 不把协议文档确认当作实机接入成功。
- 不将用户 API Key 硬编码进仓库。
- 不为每个平台复制不同版本的汽车销售逻辑和评分标准。

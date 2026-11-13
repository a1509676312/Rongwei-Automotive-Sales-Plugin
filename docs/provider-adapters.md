# 中国主流 AI 平台接入计划

本项目不追求全球所有模型接入。统一业务工具只实现一次，适配器负责处理不同平台的工具调用协议、消息回传和多模态参数差异。

## 首批范围

| 平台 | 优先级 | 计划接入方式 | 当前状态 |
|---|---:|---|---|
| DeepSeek | 1 | Tool Calls / OpenAI-compatible API | 待实现 |
| 通义千问（百炼） | 2 | DashScope Function Calling | 待实现 |
| 豆包（火山方舟） | 3 | Ark Function Calling | 待实现 |
| 智谱 GLM | 4 | BigModel Tool Calls | 待实现 |
| 百度千帆 / ERNIE | 5 | Qianfan tool_calls | 待实现 |
| Kimi / Moonshot | 6 | 待官方工具调用契约核实 | 候选，不纳入首批验收 |

## 官方资料核对记录

- DeepSeek 官方 Tool Calls 文档展示 tools/function 的调用与结果回填；DeepSeek V3.2 起思考模式支持工具调用。思考模式需要在后续请求保留 reasoning_content。来源：https://api-docs.deepseek.com/zh-cn/guides/tool_calls/ 和 https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/
- 阿里云 Model Studio 官方文档描述 Qwen Function Calling 的模型调用、函数执行和结果回传流程。来源：https://docs.modelstudio.console.alibabacloud.com/en/model-studio/qwen-function-calling
- 火山方舟官方文档展示 Doubao Function Calling 的工具定义、tool_calls 解析和 tool 结果回传流程。来源：https://docs.volcengine.com/docs/ark/function-calling
- 智谱官方助手对话 API 文档包含 tool_calls 的函数名和 JSON 参数字段；智谱智能体开发文档说明 Agent 节点具备 function call 能力。来源：https://docs.bigmodel.cn/api-reference/助手-api/助手对话 和 https://docs.bigmodel.cn/cn/guide/platform/intelligent-agent
- 百度千帆官方 API 文档定义 tool_calls 数组及函数调用参数。来源：https://cloud.baidu.com/doc/qianfan-api/s/Amwbl4wln
- Kimi 官方 API 概览确认 API 格式兼容 OpenAI，但当前核对的官方页面未确认自定义 function tool 的完整往返协议。因此先列为候选，不宣称已经支持。来源：https://www.kimi.ai/zh-hans/help/kimi-api/api-overview

## 每个适配器的验收条件

1. 能获取该平台当前可用模型列表或明确配置模型标识。
2. 能把 canonical tools 转成平台要求的工具格式。
3. 能解析一次或多次工具调用，并校验函数名和参数。
4. 能把工具结果按平台协议回传给模型。
5. 能正确终止循环，设置最大工具调用次数和单次超时，防止无限调用。
6. 保留 provider 的必要思考状态字段、调用 ID、多模态字段和错误信息。
7. 对不支持的 JSON Schema 字段做可预测降级，而不是静默丢弃关键约束。
8. 模型拒绝、参数非法、限流、超时、额度不足、服务不可用时给出可理解错误。
9. 不打印 API Key，不把客户原始对话写入应用日志。
10. 使用统一的汽车销售验收样例完成端到端测试。

## 不采用的做法

- 不因 API 地址兼容 OpenAI 就直接宣布完整兼容。
- 不把 MCP 支持等同于 Function Calling 支持；两者按实际平台能力分别验收。
- 不在项目中硬编码用户 API Key。
- 不为不同平台复制五份业务规则或不同评分标准。

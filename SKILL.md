---
name: code-visualizer
description: "写代码 + 代码可视化助手。当用户要生成/编写/重构代码，或想把代码结构、依赖关系、类关系、函数调用链、执行流程画成图时触发。支持 Python(.py) 与 JS/TS(.js/.jsx/.ts/.tsx)。覆盖：项目依赖图、类图、调用图、目录树、流程图/时序图，并渲染为可交互可视化。This skill should be used when the user says things like '帮我画一下这个项目的结构''把这个类的继承关系可视化''看下函数调用链''生成代码并配图''解释这段代码流程'."
agent_created: true
metadata:
  version: "1.0.0"
  author: "WorkBuddy"
  tags: "code,visualization,mermaid,dependency-graph,class-diagram,call-graph,python,javascript,typescript"
---

# 写代码 + 代码可视化助手

面向 Python 与 JS/TS 的编码与可视化技能。核心价值：写代码的同时，把代码结构"画出来"，让依赖、继承、调用关系一眼可见。

## 何时使用
- 用户要写/生成/重构代码（含脚手架、函数、模块拆分）。
- 用户要"看结构""可视化""画个图"：依赖关系、类图、调用链、目录树、执行流程。
- 用户要解释一段代码的逻辑走向。

## 工作流程

```
理解需求 → (如需画图) 跑 code_graph.py 解析 → 渲染 Mermaid → 解释/落代码
```

### 1. 生成 / 编写代码
- 先确认语言、目标文件、与现有代码风格保持一致（读同目录已有文件再动手）。
- 小步产出：单文件函数优先，避免一次性大改写。
- 该写测试就写最小可运行验证。

### 2. 可视化（核心能力）
用 bundled 脚本 `scripts/code_graph.py` 解析源码，输出 Mermaid 文本，再渲染。

| 想要的效果 | 命令 |
|-----------|------|
| 整个项目 import/依赖图 | `python scripts/code_graph.py deps <目录>` |
| 单个文件类图(继承/方法) | `python scripts/code_graph.py classes <文件>` |
| 单个文件函数调用链 | `python scripts/code_graph.py calls <文件>` |
| 目录/文件结构树 | `python scripts/code_graph.py tree <目录>` |

加 `--html <path.html>` 额外生成**可直接用浏览器打开**的自包含图（mermaid CDN 渲染）。
加 `--limit N` 限制节点数（默认 60，图过大时自动截断并提示）。

脚本零依赖，用托管 Python 运行：
`C:\Users\1\.workbuddy\binaries\python\versions\3.13.12\python.exe scripts/code_graph.py deps <目录> --html out.html`

### 3. 渲染 Mermaid
两种渲染路径（任选）：
- **对话内实时预览**：用 `show_widget`，`widget_code` 为含 mermaid CDN 的 HTML 片段：
  ```html
  <div class="mermaid">%%MERMAID_TEXT%%</div>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script>mermaid.initialize({startOnLoad:true});</script>
  ```
- **交付物文件**：`--html` 生成的 .html，用 present_files 交给用户，浏览器打开可缩放/导出。

### 4. 图太复杂时的处理
- 超过 ~40 节点先 `--limit` 截断，或按子模块分别出图。
- 依赖图里跨文件循环依赖用虚线 `-.->` 标"疑似耦合"，在解释里点出。
- 手写流程图/时序图讲解业务逻辑时，套用 `references/mermaid-cheatsheet.md` 语法，不必跑脚本。

## 输出规范
- 先给图（或图 + 简要结论），再给代码 diff/文件。
- 解释结构时，明确标注"高耦合点""循环依赖""孤儿模块"等风险。
- 中文沟通，结论前置；图只是辅助，不替代码本身。

## 参考
- Mermaid 语法与渲染细节见 `references/mermaid-cheatsheet.md`。
- 脚本实现（解析规则、裁剪、语言支持）见 `scripts/code_graph.py`，需要改解析规则直接编辑。

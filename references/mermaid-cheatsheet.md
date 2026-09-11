# Mermaid 语法速查（代码可视化常用）

本 skill 用 Mermaid 文本描述图，再由 Visualizer 或浏览器渲染。常用四类：

## 1. flowchart（流程图 / 依赖图 / 调用图）
```
flowchart LR          %% LR=横向  TD=纵向
  A["节点A"] --> B["节点B"]
  B --> C
  A -.-> D["虚线"]     %% 虚线表示弱/可选依赖
  B ==> E["粗线"]
```
- 方向：`LR`(左→右) `TD`(上→下) `RL` `BT`
- 形状：`[矩形]` `(圆角)` `{菱形/判断}` `[[平行四边形]]` `"文本"` 防特殊字符
- 连线：`-->` 实线箭头 `-- text -->` 带标签 `-.->` 虚线 `==>` 粗线

## 2. classDiagram（类图）
```
classDiagram
  class Animal {
    +String name
    +eat()
  }
  class Dog
  Animal <|-- Dog        %% 继承
  Dog --> Bone           %% 关联
  Dog *-- Tail           %% 组合
  Dog o-- Leg            %% 聚合
```
- 可见性：`+` public `-` private `#` protected
- 关系：`<--` 继承 `-->` 关联 `*--` 组合 `o--` 聚合 `--` 依赖

## 3. sequenceDiagram（时序图：适合讲解执行流程）
```
sequenceDiagram
  participant U as 用户
  participant S as 服务
  U->>S: 请求
  S-->>U: 响应
  Note over U,S: 注释
```

## 4. graph（结构树，也可当目录树）
```
graph TD
  root --> a
  root --> b
  a --> a1
```

## 渲染方式
- 浏览器：把 Mermaid 文本包进 `<div class="mermaid">`，引 mermaid CDN，存档为 .html 打开。
- 对话内：用 `show_widget` 输出含 mermaid CDN 的 HTML 片段，实时预览。
- 节点 id 必须纯字母数字/下划线；含路径或中文的标签用 `["..."]` 包住。

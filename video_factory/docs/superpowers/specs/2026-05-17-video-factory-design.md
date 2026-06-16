# Video Factory — AI 自媒体视频生成管线

## Overview

通用 AI 驱动的自媒体视频生成工作流。输入主题词，输出成品视频文件。面向热点解说和知识科普两类内容。

- **驱动方式:** Python CLI + Claude Code 对话
- **自动化:** 全自动，从主题到成片一步到位
- **参数:** 时长、画幅比、风格均可配置

## Architecture

配置驱动的 Pipeline + Recipe 系统。每个 Recipe 描述一类视频的完整生成流程，Runner 读取 Recipe 后按序执行各 Step。Step 之间通过 PipelineContext 传递数据。

```
main.py
  ├── 解析 CLI 参数 (--recipe, --topic, --duration, --aspect)
  ├── 加载 config/recipes/{name}.yaml
  └── 调用 Runner.run(recipe, topic, overrides)

Runner.run:
  PipelineContext 创建
    → Step.fetch   → Step.storyboard → Step.media_gen
    → Step.validate → Step.compose   → Step.render
```

## Project Structure

```
video_factory/
├── main.py                    # CLI 入口
├── pipeline/
│   ├── runner.py              # Pipeline runner
│   ├── context.py             # PipelineContext dataclass
│   └── base.py                # Step 基类
├── steps/
│   ├── fetch_news.py          # brave-search 抓取 + 筛选
│   ├── storyboard.py          # 分镜 + 旁白脚本
│   ├── media_gen.py           # edge-tts 语音 + 图片
│   ├── duration_check.py      # 时长校验
│   ├── compose_video.py       # hyperframes 视频代码
│   └── render_output.py       # 合成输出
├── config/
│   └── recipes/
│       ├── hot_news.yaml
│       └── knowledge.yaml
├── output/
│   └── {task_id}/
│       ├── workdir/           # 中间产物 (脚本、mp3、png、html)
│       └── final.mp4
└── requirements.txt
```

## Recipe Format

YAML 文件定义工作流，支持 `{{var}}` 模板变量引用 CLI 传入的参数。

```yaml
name: 热点新闻快剪
defaults:
  duration: 60
  aspect: "9:16"
steps:
  - id: fetch
    module: steps.fetch_news
    config:
      source: brave_search
      max_items: 5
      select_top: 3
  - id: script
    module: steps.storyboard
    config:
      image_style: editorial_illustration
      narration_lang: zh-CN
  - id: media
    module: steps.media_gen
    config:
      tts_voice: zh-CN-XiaoxiaoNeural
  - id: validate
    module: steps.duration_check
    config:
      max_duration_sec: "{{duration}}"
      strategy: trim
  - id: compose
    module: steps.compose_video
    config:
      aspect: "{{aspect}}"
  - id: render
    module: steps.render_output
    config:
      format: mp4
```

## PipelineContext

Step 间唯一的数据交换载体：

```python
@dataclass
class PipelineContext:
    task_id: str           # UUID，同时也是 output 子目录名
    topic: str             # 用户输入的主题
    params: dict           # CLI 覆盖参数 {duration, aspect, ...}
    artifacts: dict        # {"news_items": [...], "segments": [...], ...}
    logs: list[str]
```

artifacts 在各步逐步填充：
- `fetch_news` → `artifacts["news_items"]`
- `storyboard` → `artifacts["segments"]` (narration, image_prompt, duration_est)
- `media_gen` → `segments` 补上 `audio_path`, `image_path`
- `compose_video` → `artifacts["html_path"]`
- `render_output` → `artifacts["final_video_path"]`

## Steps

### fetch_news
- 调用 brave-search API 搜索 topic
- 返回前 N 条，按相关度排序
- 输出: `artifacts["news_items"]`

### storyboard
- 将 news_items + topic 发给 LLM，生成旁白脚本
- 同时为每段生成 image_gen 图片生成 prompt
- 估算每段旁白对应的大致时长（按字数估算）
- 输出: `artifacts["segments"]`

### media_gen
- 逐段调用 edge-tts 生成 mp3 音频
- 逐段调用内置 image_gen 生成配图，下载到 workdir
- 输出: 补全 `segments[].audio_path`, `segments[].image_path`

### duration_check
- 累加所有音频文件的实际时长（读取 mp3 metadata）
- 与 max_duration_sec 对比
- strategy=trim: 超时则截断最后一段旁白重新生成
- strategy=warn: 仅打印警告继续
- strategy=error: 直接终止

### compose_video
- 将 segments 写入 hyperframes 视频工程（HTML 文件）
- 包含：时间轴、字幕、图片动画、音频轨道
- 输出: `artifacts["html_path"]`

### render_output
- 调 hyperframes CLI 渲染 HTML → mp4
- 输出到 `output/{task_id}/final.mp4`

## Step Base Class

```python
class Step(ABC):
    @abstractmethod
    def run(self, ctx: PipelineContext) -> None:
        ...
```

Runner 通过 importlib 加载 module，实例化 `Step`，调用 `run(ctx)`。`run()` 内部负责从 `ctx` 读入、写回 `ctx.artifacts`。

## CLI Interface

```bash
python main.py --recipe hot_news --topic "黑客新闻"
python main.py --recipe hot_news --topic "AI动态" --duration 45 --aspect 16:9
echo '{"recipe":"hot_news","topic":"黑客新闻","duration":60}' | python main.py --json
```

- `--recipe`: recipe 文件名（不含 .yaml）
- `--topic`: 视频主题
- `--duration`: 覆盖默认时长（秒）
- `--aspect`: 覆盖默认画幅
- `--json`: 从 stdin 读 JSON 参数（用于 Claude Code 对话模式驱动）

## Error Handling

- 每步失败自动重试 2 次（指数退避 1s / 4s）
- API 调用超时 120s
- 失败后 workdir 保留不删，方便排错
- 启动时前置检查：`edge-tts --version`, `brave-search` API key 等

## Out of Scope (v1)

- 断点续跑
- 多语言旁白（仅中文）
- 复杂转场/特效（hyperframes 默认模板）
- Web UI
- 字幕样式自定义

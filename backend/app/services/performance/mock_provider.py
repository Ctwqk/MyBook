"""Deterministic long-text mock provider for performance baselines."""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.llm.base import LLMProvider, LLMResponse


class PerformanceMockLLMProvider(LLMProvider):
    """Mock provider that exercises the full generation path with 2500+ CJK chars."""

    def __init__(
        self,
        model: str = "performance-mock-longform",
        temperature: float = 0.0,
        max_tokens: int = 8192,
        chapter_body_chars: int = 3300,
    ):
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.call_count = 0
        self.chapter_body_chars = chapter_body_chars

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        self.call_count += 1
        content = self._generate_content(prompt, system_prompt or "")
        return LLMResponse(
            content=content,
            model=self.model,
            usage={
                "prompt_tokens": max(1, len(prompt) // 4),
                "completion_tokens": max(1, len(content) // 4),
                "total": max(1, (len(prompt) + len(content)) // 4),
            },
            raw_response={"mock": True, "performance": True, "call_number": self.call_count},
        )

    async def generate_structured(
        self,
        prompt: str,
        system_prompt: Optional[str],
        response_schema: dict[str, Any],
        **kwargs,
    ) -> dict[str, Any]:
        self.call_count += 1
        return {"result": "performance mock structured response"}

    async def chat(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        prompt = "\n".join(message.get("content", "") for message in messages)
        return await self.generate(prompt, None, **kwargs)

    def _generate_content(self, prompt: str, system_prompt: str) -> str:
        if "结构化信息" in prompt and "JSON" in prompt:
            return json.dumps(
                {
                    "chapter_summary": "本章完成一次关键推进，并留下新的选择压力。",
                    "event_candidates": [
                        {"type": "discovery", "description": "主角发现异常"},
                        {"type": "risk", "description": "同伴提出风险"},
                        {"type": "clue", "description": "敌方线索浮现"},
                    ],
                    "state_change_candidates": [
                        {"character": "林澈", "change": "决心增强"}
                    ],
                    "thread_beat_candidates": [
                        {"thread": "旧案线索", "beat": "推进"}
                    ],
                    "lore_candidates": [
                        {"topic": "城市地下网络", "detail": "存在隐秘节点"}
                    ],
                    "timeline_hints": [
                        {"time": "同日夜晚", "event": "旧车站追踪"}
                    ],
                },
                ensure_ascii=False,
            )
        if "章节大纲" in prompt and ("起始章节号" in prompt or "请为第" in prompt):
            return self._outline_response(prompt)
        if "请续写" in prompt or "继续" in prompt:
            chapter_no = self._extract_chapter_no(prompt)
            return self._chapter_body(chapter_no, continuation=True, target_chars=900)
        if "生成第" in prompt and "正文" in prompt:
            chapter_no = self._extract_chapter_no(prompt)
            return self._chapter_body(chapter_no, continuation=False, target_chars=self.chapter_body_chars)
        if "审查" in prompt or "review" in prompt.lower():
            return json.dumps(
                {
                    "score": 8,
                    "issues": [],
                    "summary": "结构完整，节奏稳定。",
                },
                ensure_ascii=False,
            )
        return self._chapter_body(self._extract_chapter_no(prompt), target_chars=600)

    def _outline_response(self, prompt: str) -> str:
        start = self._extract_number(prompt, r"起始章节号[：:]\s*(\d+)", default=1)
        end = self._extract_number(prompt, r"结束章节号[：:]\s*(\d+)", default=start + 59)
        chapters = []
        for chapter_no in range(start, end + 1):
            chapters.append(
                {
                    "title": f"暗潮第{chapter_no}夜",
                    "outline": (
                        f"起：第{chapter_no}章从主角收到异常信号开始。"
                        f"承：团队追查信号来源并发现旧案关联。"
                        f"转：线索指向更深层的城市网络，主角必须做出选择。"
                        f"合：本章以新的危机和下一章行动目标收束。"
                    ),
                    "hook": f"第{chapter_no}章结尾出现一条无法追踪的回信。",
                    "key_events": ["异常信号", "旧案关联", "行动目标"],
                }
            )
        return json.dumps(chapters, ensure_ascii=False)

    def _chapter_body(
        self,
        chapter_no: int,
        *,
        continuation: bool = False,
        target_chars: int,
    ) -> str:
        title = "" if continuation else f"# 第{chapter_no}章：暗潮第{chapter_no}夜\n\n"
        paragraphs = []
        seed_sentences = [
            f"第{chapter_no}章的夜色压在城市上空，霓虹像潮水一样沿着玻璃幕墙缓慢流动。",
            "林澈站在旧车站的候车厅里，听见广播反复播报一趟不存在的列车。",
            "他没有急着行动，而是把掌心贴在冰冷的栏杆上，感受金属深处传来的细微震颤。",
            "那种震颤像某种暗号，短促、克制，却又精准地指向三年前失踪案留下的空白。",
            "身后的同伴低声提醒他，监控摄像头已经偏转，说明有人比他们更早抵达现场。",
            "林澈抬头看见二楼尽头的灯依次熄灭，黑暗像被人折叠过一样迅速逼近。",
            "他想起导师留下的警告，真正危险的不是敌人现身，而是所有证据同时变得合理。",
            "于是他选择反向追踪，把伪装成噪声的信号拆开，一点点拼出隐藏的坐标。",
            "坐标指向城市下方废弃的能源井，也指向他一直不愿承认的家族旧名。",
            "当第一声警报响起时，林澈没有后退，他知道这一章的答案必须由自己亲手打开。",
        ]
        index = 0
        while len("".join(paragraphs)) < target_chars:
            block = []
            for _ in range(5):
                sentence = seed_sentences[index % len(seed_sentences)]
                block.append(sentence)
                index += 1
            paragraphs.append("".join(block))
        body = "\n\n".join(paragraphs)
        body = body[: target_chars + 120]
        if not body.endswith(("。", "！", "？")):
            body += "。"
        return title + body

    def _extract_chapter_no(self, prompt: str) -> int:
        patterns = [
            r"第\s*(\d+)\s*章",
            r"章节号[：:]\s*(\d+)",
            r"chapter_no[\"']?\s*[:=]\s*(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 1

    def _extract_number(self, prompt: str, pattern: str, *, default: int) -> int:
        match = re.search(pattern, prompt)
        if not match:
            return default
        return int(match.group(1))

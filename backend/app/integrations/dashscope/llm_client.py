"""
DashScope LLM 客户端封装
使用 Qwen3 进行翻译
"""

import asyncio
from typing import Optional

from loguru import logger
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


class LLMClient:
    """DashScope LLM 客户端（OpenAI 兼容）"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ):
        """
        初始化 LLM 客户端

        Args:
            api_key: DashScope API Key
            base_url: API 地址
            model: 模型名称
            max_tokens: 最大 token 数
        """
        self.api_key = api_key or settings.dashscope_api_key
        self.base_url = base_url or settings.llm_base_url
        self.model = model or settings.llm_model
        self.max_tokens = max_tokens or settings.llm_max_tokens

        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY is required")

        # 创建 OpenAI 客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        logger.info(f"LLM Client initialized: model={self.model}, base_url={self.base_url}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
    ) -> str:
        """
        翻译文本

        Args:
            text: 待翻译文本
            source_lang: 源语言代码（zh, en, ja, ko等）
            target_lang: 目标语言代码
            context: 上下文信息（可选）

        Returns:
            翻译结果

        Raises:
            RuntimeError: 翻译失败
        """
        logger.info(
            f"Translating: {len(text)} chars, {source_lang} -> {target_lang}"
        )

        # 构建提示词
        system_prompt = self._build_system_prompt(source_lang, target_lang)
        user_prompt = self._build_user_prompt(text, context)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=0.3,  # 较低温度，保证翻译稳定性
            )

            translation = response.choices[0].message.content.strip()

            logger.info(
                f"Translation completed: {len(translation)} chars, "
                f"tokens={response.usage.total_tokens}"
            )

            return translation

        except Exception as e:
            logger.error(f"Translation failed: {e}")
            raise RuntimeError(f"Translation failed: {e}") from e

    def translate_batch(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
    ) -> list[str]:
        """
        批量翻译（同步版本）

        Args:
            texts: 待翻译文本列表
            source_lang: 源语言代码
            target_lang: 目标语言代码
            context: 上下文信息（可选）

        Returns:
            翻译结果列表
        """
        logger.info(f"Batch translating {len(texts)} texts")

        results = []
        for i, text in enumerate(texts):
            try:
                translation = self.translate(text, source_lang, target_lang, context)
                results.append(translation)
                logger.debug(f"Translated {i+1}/{len(texts)}")
            except Exception as e:
                logger.error(f"Failed to translate text {i+1}: {e}")
                # 失败时使用原文
                results.append(text)

        return results

    async def translate_async(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
    ) -> str:
        """
        异步翻译

        Args:
            text: 待翻译文本
            source_lang: 源语言代码
            target_lang: 目标语言代码
            context: 上下文信息（可选）

        Returns:
            翻译结果
        """
        # 在线程池中运行同步方法
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.translate, text, source_lang, target_lang, context
        )

    async def translate_batch_async(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
        context: Optional[str] = None,
        concurrency: int = 5,
    ) -> list[str]:
        """
        批量异步翻译（并发）

        Args:
            texts: 待翻译文本列表
            source_lang: 源语言代码
            target_lang: 目标语言代码
            context: 上下文信息（可选）
            concurrency: 并发数

        Returns:
            翻译结果列表
        """
        logger.info(f"Async batch translating {len(texts)} texts, concurrency={concurrency}")

        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(concurrency)

        async def translate_with_semaphore(text: str) -> str:
            async with semaphore:
                return await self.translate_async(text, source_lang, target_lang, context)

        # 并发执行
        tasks = [translate_with_semaphore(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to translate text {i+1}: {result}")
                final_results.append(texts[i])  # 失败时使用原文
            else:
                final_results.append(result)

        return final_results

    def _build_system_prompt(self, source_lang: str, target_lang: str) -> str:
        """构建系统提示词"""
        lang_names = {
            "zh": "中文",
            "en": "英文",
            "ja": "日文",
            "ko": "韩文",
            "es": "西班牙语",
            "fr": "法语",
            "de": "德语",
            "ru": "俄语",
        }

        source_name = lang_names.get(source_lang, source_lang)
        target_name = lang_names.get(target_lang, target_lang)

        return f"""你是一个专业的视频字幕翻译专家。

任务：将{source_name}文本翻译成{target_name}

要求：
1. 保持原意准确，符合目标语言的表达习惯
2. 保留原文的语气和情感
3. 对于专有名词，保持原样或使用通用翻译
4. 只输出翻译结果，不要添加任何解释或说明
5. 保持原文的格式和标点符号风格
6. 【重要】翻译应简洁精炼，尽量使译文的朗读时长与原文相当（这对视频配音非常重要），避免译文过长导致语速过快"""

    def _build_user_prompt(self, text: str, context: Optional[str] = None) -> str:
        """构建用户提示词"""
        if context:
            return f"""上下文：{context}

待翻译文本：
{text}"""
        return text


# 全局单例
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取 LLM 客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client

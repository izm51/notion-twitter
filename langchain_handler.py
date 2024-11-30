import os
import operator
from logging import getLogger, StreamHandler, DEBUG
from typing import Annotated
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from typing import Any
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.addHandler(handler)
logger.setLevel(DEBUG)


class State(BaseModel):
    content: str = Field(..., description="要約対象の全文")
    chunks: Annotated[list[str], operator.add] = Field(
        default=[], description="抽出されたブロック"
    )
    posts: Annotated[list[str], operator.add] = Field(default=[], description="投稿文")
    current_judge: bool = Field(default=False, description="品質チェックの結果")
    judgement_reason: str = Field(default="", description="品質チェックの判定理由")
    trial_count: int = Field(default=0, description="試行回数")


class Judgement(BaseModel):
    judge: bool = Field(default=False, description="判定結果")
    reason: str = Field(default="", description="判定理由")


class LangChainConfig:
    MODEL_NAME = "gpt-4o-mini"
    TEMPERATURE = 0.5
    BLOCK_MIN_CHARS = 300
    BLOCK_MAX_CHARS = 600
    POST_MIN_CHARS = 110
    POST_MAX_CHARS = 140
    MAX_TRIALS = 3


class LangChainHandler:
    def __init__(self):
        logger.info("Initializing LangChainHandler")
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
        os.environ["LANGCHAIN_PROJECT"] = "pr-charming-fiesta-52"
        self.model = ChatOpenAI(
            model=LangChainConfig.MODEL_NAME, temperature=LangChainConfig.TEMPERATURE
        )

    def block_selection_node(self, state: State) -> dict[str, Any]:
        logger.info("Starting block selection")
        prompt = ChatPromptTemplate.from_template(
            """次の文章を{min_chars}文字から{max_chars}文字程度ずつのブロックに分割し、その中からランダムに1ブロックを抜き出してください。

文章:
{content}
"""
        )
        chain = prompt | self.model | StrOutputParser()
        chunk = chain.invoke(
            {
                "content": state.content,
                "min_chars": LangChainConfig.BLOCK_MIN_CHARS,
                "max_chars": LangChainConfig.BLOCK_MAX_CHARS,
            }
        )
        logger.debug(f"Selected block: {chunk[:100]}...")
        return {"chunks": [chunk]}

    def post_generate_node(self, state: State) -> dict[str, Any]:
        logger.info(f"Generating post (trial #{state.trial_count + 1})")
        prompt = ChatPromptTemplate.from_template(
            """指示：
以下に提供する文章を、SNSに投稿するための読み応えがあり、全角{min_chars}文字以上{max_chars}文字以内の文章に仕上げてください。
提供された文章から{min_chars}文字以上のコンテンツを生成できない場合のみ、独自にコンテンツを生成してください。

文体・トーン：
・文体: 威厳がありつつもカジュアルで口語的。話し言葉を多用し、読者に直接語りかける形式。
・トーン: 率直でストレート。時に厳しい表現を用いながらも親しみやすさを保つ。
・言葉遣い: 実体験を元にして組み立てた理論を語っている口調。丁寧かつフランクで軽快。男性的な言葉遣いを優先。
・内容の特徴: 一般論すぎない理論。権威ある言葉や研究データを含み、説得力を持たせる。
・禁止事項: 文末にビックリマークなどカジュアルすぎる表現を避ける。ハッシュタグの使用は禁止。

例:
・自己分析を通じて、自分の内的欲求を理解することはキャリア選択において不可欠。外部の期待に流されず、自分が本当に求めるものに耳を傾けることが大切ですよ。自分の特性を活かせる環境を選ぶことで、仕事においても自己実現を図れるはずです。内なる声に従って、輝く場所を見つけよう。
・読書はただのインプットじゃない。効率的に学ぶためには、まずアウトプットを考えてみよう。自分の課題に合った情報を抽出する「ゲームの攻略本」のような読み方が鍵。これで得た知識は実際の行動に直結する。目的を持った読書が、あなたの成長を加速させる。

チェックポイント：
・出力は絶対に{min_chars}文字以上{max_chars}文字以内であること。
・読み応えがあり、内容が充実していること。

文章:
{content}
"""
        )
        chain = prompt | self.model | StrOutputParser()
        post = chain.invoke(
            {
                "content": state.chunks[-1],
                "min_chars": LangChainConfig.POST_MIN_CHARS,
                "max_chars": LangChainConfig.POST_MAX_CHARS,
            }
        )
        logger.debug(f"Generated post: {post}")
        return {"posts": [post]}

    def _count_chars(self, text: str) -> int:
        """全角と半角を区別して文字数をカウント"""
        return sum(2 if ord(char) > 127 or ord(char) == 0x2212 else 1 for char in text)

    def rule_check_node(self, state: State) -> dict[str, Any]:
        logger.info("Checking post rules")
        post = state.posts[-1]
        char_count = self._count_chars(post)
        is_valid = (
            LangChainConfig.POST_MIN_CHARS * 2
            <= char_count
            <= LangChainConfig.POST_MAX_CHARS * 2
        )
        reason = f"文字数: 半角{char_count}文字" + (
            "OK"
            if is_valid
            else f"文字数制限(全角で{LangChainConfig.POST_MIN_CHARS}-{LangChainConfig.POST_MAX_CHARS}文字)を満たしていません。"
        )

        logger.info(f"Rule check result: {is_valid}, Reason: {reason}")
        return {"current_judge": is_valid, "judgement_reason": reason}

    def adjust_post_length_node(self, state: State) -> dict[str, Any]:
        logger.info("Arranging post length")
        prompt = ChatPromptTemplate.from_template(
            """次の文章を全角{min_chars}文字以上{max_chars}文字以内に調整してください。

文章:
{content}
"""
        )
        chain = prompt | self.model | StrOutputParser()
        post = chain.invoke(
            {
                "content": state.posts[-1],
                "min_chars": LangChainConfig.POST_MIN_CHARS,
                "max_chars": LangChainConfig.POST_MAX_CHARS,
            }
        )
        logger.debug(f"Arranged post: {post}")
        return {"posts": [post], "trial_count": state.trial_count + 1}

    def run_workflow(self, content: str) -> str:
        logger.info("Starting workflow")
        self.state = State(content=content)
        workflow = StateGraph(State)

        workflow.add_node("block_selection", self.block_selection_node)
        workflow.add_node("post_generate", self.post_generate_node)
        workflow.add_node("rule_check", self.rule_check_node)
        workflow.add_node("adjust_post", self.adjust_post_length_node)

        workflow.set_entry_point("block_selection")
        workflow.add_edge("block_selection", "post_generate")
        workflow.add_edge("post_generate", "rule_check")
        workflow.add_edge("adjust_post", "rule_check")

        workflow.add_conditional_edges(
            "rule_check",
            lambda state: (
                state.current_judge or state.trial_count >= LangChainConfig.MAX_TRIALS
            ),
            {True: END, False: "adjust_post"},
        )

        compiled = workflow.compile()

        try:
            result = compiled.invoke(self.state)
            logger.info("Workflow completed successfully")
            if not result["current_judge"]:
                logger.error(f"Post validation failed: {result.judgement_reason}")
                raise Exception(
                    f"current_judge: {result['current_judge']}, judgement_reason: {result['judgement_reason']}"
                )
            else:
                logger.info("Post generated and validated successfully")
                return result["posts"][-1]
        except Exception as e:
            logger.error(f"Workflow failed with error: {str(e)}")
            raise

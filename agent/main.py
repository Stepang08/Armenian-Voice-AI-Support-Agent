"""
agent/main.py — Armenian bank voice agent entrypoint.

Pipeline:
  Microphone → VAD (Silero) → STT (Whisper, language=hy)
             → LLM (GPT-4o-mini + RAG context)
             → TTS (OpenAI alloy) → Speaker

Run:
  PYTHONPATH=. python3 agent/main.py start
"""

import os
import asyncio
from dotenv import load_dotenv
from loguru import logger

from livekit.agents import Agent, AgentSession, AutoSubscribe, JobContext, WorkerOptions, cli
from livekit.plugins import openai as lk_openai
from livekit.plugins import silero

from agent.prompts import WELCOME_MESSAGE, SYSTEM_PROMPT
from rag.knowledge_base import KnowledgeBase
from rag.retriever import Retriever

load_dotenv()


async def entrypoint(ctx: JobContext):
    logger.info(f"Agent connecting to room: {ctx.room.name}")

    # Load knowledge base — done here in the worker process
    kb = KnowledgeBase(persist_path=os.getenv("CHROMA_DB_PATH", "./data/chroma_db"))
    retriever = Retriever(kb)

    # Pre-fetch broad context for the initial greeting
    chunks, _ = retriever.retrieve("loan deposit branch credit savings interest rate")
    initial_context = Retriever.format_context(chunks)

    class BankAgent(Agent):
        async def on_user_turn_completed(self, turn_ctx, new_message):
            # Extract user text
            user_text = ""
            if hasattr(new_message, "text_content"):
                user_text = new_message.text_content or ""
            elif hasattr(new_message, "content"):
                user_text = str(new_message.content or "")
            if not user_text.strip():
                return

            logger.info(f"User said: {user_text!r}")

            # Retrieve relevant context
            chunks, is_on_topic = retriever.retrieve(user_text)
            logger.info(f"Retrieved {len(chunks)} chunks, on_topic={is_on_topic}")

            if not is_on_topic:
                await self.update_instructions(
                    SYSTEM_PROMPT.format(
                        context="User asked an off-topic question. Politely refuse in Armenian. "
                                "Say you can only help with Armenian bank deposits, loans, and branches."
                    )
                )
                return

            context = Retriever.format_context(chunks)
            await self.update_instructions(SYSTEM_PROMPT.format(context=context))

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    session = AgentSession(
        vad=silero.VAD.load(),
        stt=lk_openai.STT(model="whisper-1", language="hy"),
        llm=lk_openai.LLM(model=os.getenv("LLM_MODEL", "gpt-4o-mini")),
        tts=lk_openai.TTS(voice="alloy"),
    )

    agent = BankAgent(instructions=SYSTEM_PROMPT.format(context=initial_context))
    await session.start(agent=agent, room=ctx.room)
    await session.generate_reply(instructions=WELCOME_MESSAGE)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        initialize_process_timeout=60.0,
    ))

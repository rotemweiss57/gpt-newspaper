from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json5 as json
from openai import OpenAI
import os

sample_json_standard = """
{
  "title": title of the article,
  "date": today's date,
  "paragraphs": [
    "paragraph 1",
    "paragraph 2",
    "paragraph 3",
    "paragraph 4",
    "paragraph 5",
    ],
    "summary": "2 sentences summary of the article"
}
"""

sample_json_advanced = """
{
  "title": "Full title of the article",
  "date": "DD/MM/YYYY",
  "paragraphs": [
    "First paragraph with full sentences explaining introduction and context. This should be 4-7 complete sentences providing background.",
    "Second paragraph with full sentences about background information and historical context. Again, 4-7 complete sentences.",
    "Third paragraph discussing main point 1 with detailed explanations and examples. Must be 4-7 complete sentences.",
    "Fourth paragraph exploring main point 2 with specific examples and data. Should contain 4-7 complete sentences.",
    "Fifth paragraph analyzing main point 3 with in-depth analysis. Include 4-7 complete sentences.",
    "Sixth paragraph presenting additional perspective or viewpoint 1. Write 4-7 complete sentences.",
    "Seventh paragraph discussing additional perspective or viewpoint 2. Should have 4-7 complete sentences.",
    "Eighth paragraph examining implications and consequences. Include 4-7 complete sentences.",
    "Ninth paragraph with expert opinions, quotes, or case studies. Write 4-7 complete sentences.",
    "Tenth paragraph about future outlook and predictions. Must contain 4-7 complete sentences.",
    "Eleventh paragraph with additional insights or analysis (INCLUDE THIS). Write 4-7 complete sentences.",
    "Twelfth paragraph as comprehensive conclusion synthesizing all points (INCLUDE THIS). Must be 4-7 complete sentences."
    ],
    "summary": "Comprehensive 3-4 sentence summary covering all major points discussed in the article."
}
"""

sample_revise_json = """
{
    "paragraphs": [
        "paragraph 1",
        "paragraph 2",
        "paragraph 3",
        "paragraph 4",
        "paragraph 5",
    ],
    "message": "message to the critique"
}
"""


class WriterAgent:
    def __init__(self, language: str = "english", length: str = "standard"):
        self.language = language
        self.length = length
        self.language_instructions = {
            "english": "Write the article in English.",
            "polish": "Napisz artykuł w języku polskim. All content including title, paragraphs, and summary must be in Polish."
        }
        self.length_instructions = {
            "standard": "Write a concise, well-structured article with 5-6 paragraphs. Focus on the most important information.",
            "advanced": "Write a comprehensive, in-depth article with 8-12 paragraphs. Thoroughly explore all aspects of the topic, provide detailed analysis, context, and multiple perspectives. Exhaustively cover the subject matter with rich detail and nuanced discussion."
        }

    def writer(self, query: str, sources: list):
        language_instruction = self.language_instructions.get(self.language, self.language_instructions["english"])
        length_instruction = self.length_instructions.get(self.length, self.length_instructions["standard"])
        sample_json = sample_json_advanced if self.length == "advanced" else sample_json_standard
        
        # Use GPT-4o with extended context for advanced mode, GPT-4 for standard
        if self.length == "advanced":
            # Advanced mode: GPT-4o with high max_tokens and detailed instructions
            messages = [
                SystemMessage(content=f"You are an expert newspaper writer specializing in comprehensive, in-depth journalism. "
                           f"Your articles are known for thorough analysis, rich detail, and exhaustive coverage of topics.\n"
                           f"{language_instruction}\n"
                           f"{length_instruction}\n"
                           f"CRITICAL INSTRUCTION: Your articles MUST contain EXACTLY 10-12 paragraphs. This is NON-NEGOTIABLE.\n"
                           f"Each paragraph must be substantial with 4-7 sentences. Standard 5-6 paragraph articles are NOT acceptable.\n"
                           f"You will write extended, comprehensive articles that thoroughly explore every aspect of the topic."),
                HumanMessage(content=f"Today's date is {datetime.now().strftime('%d/%m/%Y')}\n"
                           f"Query or Topic: {query}\n"
                           f"Sources:\n{sources}\n\n"
                           f"Your task is to write a critically acclaimed, comprehensive, IN-DEPTH article about the provided query or topic.\n\n"
                           f"*** MANDATORY REQUIREMENTS - STRICT COMPLIANCE REQUIRED ***\n\n"
                           f"YOU MUST WRITE EXACTLY 12 PARAGRAPHS. NOT 6, NOT 8, BUT 12 FULL PARAGRAPHS.\n\n"
                           f"PARAGRAPH STRUCTURE (MANDATORY - WRITE ALL 12):\n"
                           f"Paragraph 1: Introduction and context setting (5-7 sentences)\n"
                           f"Paragraph 2: Historical background and origins (5-7 sentences)\n"
                           f"Paragraph 3: Current state and recent developments (5-7 sentences)\n"
                           f"Paragraph 4: Key aspect #1 with detailed analysis (5-7 sentences)\n"
                           f"Paragraph 5: Key aspect #2 with specific examples (5-7 sentences)\n"
                           f"Paragraph 6: Key aspect #3 with case studies (5-7 sentences)\n"
                           f"Paragraph 7: Multiple perspectives and viewpoints (5-7 sentences)\n"
                           f"Paragraph 8: Challenges and limitations (5-7 sentences)\n"
                           f"Paragraph 9: Implications and consequences (5-7 sentences)\n"
                           f"Paragraph 10: Expert opinions and research (5-7 sentences)\n"
                           f"Paragraph 11: Future outlook and predictions (5-7 sentences)\n"
                           f"Paragraph 12: Comprehensive conclusion and synthesis (5-7 sentences)\n\n"
                           f"{language_instruction}\n\n"
                           f"*** CRITICAL: The JSON 'paragraphs' array MUST contain ALL 12 paragraphs. Do not skip any! ***\n\n"
                           f"Please return nothing but a JSON in the following format:\n"
                           f"{sample_json}\n")
            ]
            
            # Use gpt-4-turbo for better instruction following on longer content
            response = ChatOpenAI(
                model='gpt-4-turbo',
                max_retries=1,
                max_tokens=4096,  # gpt-4-turbo max completion tokens
                temperature=0.8,
                model_kwargs={
                    "response_format": {"type": "json_object"}
                }
            ).invoke(messages).content
        else:
            # Standard mode with GPT-4
            messages = [
                SystemMessage(content=f"You are a newspaper writer. Your sole purpose is to write a well-written article about a "
                           f"topic using a list of articles.\n{language_instruction}\n{length_instruction}\n "),
                HumanMessage(content=f"Today's date is {datetime.now().strftime('%d/%m/%Y')}\n."
                           f"Query or Topic: {query}"
                           f"{sources}\n"
                           f"Your task is to write a critically acclaimed article for me about the provided query or "
                           f"topic based on the sources.\n "
                           f"{language_instruction}\n"
                           f"Please return nothing but a JSON in the following format:\n"
                           f"{sample_json}\n ")
            ]
            optional_params = {
                "response_format": {"type": "json_object"}
            }
            response = ChatOpenAI(model='gpt-4-0125-preview', max_retries=1, model_kwargs=optional_params).invoke(messages).content
        
        return json.loads(response)

    def revise(self, article: dict):
        language_instruction = self.language_instructions.get(self.language, self.language_instructions["english"])
        length_instruction = self.length_instructions.get(self.length, self.length_instructions["standard"])
        
        messages = [
            SystemMessage(content=f"You are a newspaper editor. Your sole purpose is to edit a well-written article about a "
                       f"topic based on given critique.\n{language_instruction}\n{length_instruction}\n "),
            HumanMessage(content=f"{str(article)}\n"
                        f"Your task is to edit the article based on the critique given.\n "
                        f"{language_instruction}\n"
                        f"Please return json format of the 'paragraphs' and a new 'message' field"
                        f"to the critique that explain your changes or why you didn't change anything.\n"
                        f"please return nothing but a JSON in the following format:\n"
                        f"{sample_revise_json}\n ")
        ]

        optional_params = {
            "response_format": {"type": "json_object"}
        }

        response = ChatOpenAI(model='gpt-4-0125-preview', max_retries=1, model_kwargs=optional_params).invoke(messages).content
        response = json.loads(response)
        print(f"For article: {article['title']}")
        print(f"Writer Revision Message: {response['message']}\n")
        return response

    def run(self, article: dict):
        critique = article.get("critique")
        if critique is not None:
            article.update(self.revise(article))
        else:
            article.update(self.writer(article["query"], article["sources"]))
        return article

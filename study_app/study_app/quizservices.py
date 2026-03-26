import json
import re
from uuid import uuid4
from datetime import datetime

from .gemini import get_gemini_client
from .database import get_db
from .models import (
    GenerateQuizRequest,
    QuizQuestionResponse,
    QuizResponse,
    SubmitAnswerRequest,
    AnswerFeedback,
    QuestionType,
    DifficultyLevel,
)


def _quiz_prompt(
    text: str,
    num_questions: int,
    question_types: list[QuestionType],
    difficulty: DifficultyLevel,
) -> str:
    types_str = ", ".join(q.value for q in question_types)
    return f"""You are an expert academic quiz generator.

Generate exactly {num_questions} quiz questions from the text below.
Mix these question types: {types_str}.
Difficulty level: {difficulty.value}.

Return a JSON array and NOTHING else (no markdown fences, no preamble):
[
  {{
    "question_type": "mcq",
    "question_text": "What is the primary function of mitochondria?",
    "options": ["A. Store genetic information", "B. Produce ATP through cellular respiration", "C. Synthesise proteins", "D. Transport materials"],
    "correct_answer": "B",
    "explanation": "Mitochondria are the site of cellular respiration.",
    "difficulty": "medium"
  }}
]

Rules:
- MCQ must have exactly 4 options labelled A, B, C, D. correct_answer is the letter only.
- True/False questions must have ["True", "False"] as options. correct_answer is "True" or "False".
- Every question must be directly answerable from the text.
- Explanation must be 1-2 sentences.

TEXT:
{text[:100000]}"""


def _semantic_grade_prompt(question: str, correct: str, user_answer: str) -> str:
    return f"""You are a strict but fair academic grader.

Question: {question}
Correct answer: {correct}
Student's answer: {user_answer}

Reply with ONLY a JSON object:
{{"is_correct": true, "reason": "one sentence explanation"}}"""


def _parse_json(raw: str) -> list | dict:
    cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
    return json.loads(cleaned)


def _normalise_mcq_answer(answer: str) -> str:
    match = re.search(r"[A-Da-d]", answer)
    return match.group(0).upper() if match else answer.strip().upper()


class QuizService:

    def __init__(self):
        self.client = get_gemini_client()

    def generate_quiz(self, req: GenerateQuizRequest) -> QuizResponse:
        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute(
                    "SELECT content FROM study_sessions WHERE id = %s",
                    (str(req.session_id),),
                )
                row = cur.fetchone()
        finally:
            db.close()

        if not row:
            raise ValueError(f"Session {req.session_id} not found")

        text = row[0]
        prompt = _quiz_prompt(
            text, req.num_questions, req.question_types, req.difficulty
        )
        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw_qs = _parse_json(response.text)

        questions = []
        db = get_db()
        try:
            with db.cursor() as cur:
                for q in raw_qs:
                    options = q.get("options")
                    cur.execute(
                        """INSERT INTO quiz_questions
                           (session_id, question_type, question_text, options, correct_answer, explanation, difficulty)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)
                           RETURNING id, created_at
                        """,
                        (
                            str(req.session_id),
                            q["question_type"],
                            q["question_text"],
                            json.dumps(options) if options else None,
                            q["correct_answer"],
                            q.get("explanation", ""),
                            q.get("difficulty", req.difficulty.value),
                        ),
                    )
                    row = cur.fetchone()
                    questions.append(
                        QuizQuestionResponse(
                            id=row[0],
                            session_id=req.session_id,
                            question_type=q["question_type"],
                            question_text=q["question_text"],
                            options=options,
                            difficulty=q.get("difficulty", req.difficulty.value),
                            created_at=row[1],
                        )
                    )
        finally:
            db.close()

        return QuizResponse(
            session_id=req.session_id,
            questions=questions,
            total=len(questions),
        )

    def submit_answer(
        self, req: SubmitAnswerRequest, consecutive_correct: int = 0
    ) -> AnswerFeedback:
        db = get_db()
        try:
            with db.cursor() as cur:
                cur.execute(
                    "SELECT question_type, question_text, correct_answer, explanation FROM quiz_questions WHERE id = %s",
                    (str(req.question_id),),
                )
                row = cur.fetchone()
        finally:
            db.close()

        if not row:
            raise ValueError(f"Question {req.question_id} not found")

        q_type, question_text, correct, explanation = row
        q_type = QuestionType(q_type)

        if q_type == QuestionType.mcq:
            is_correct = _normalise_mcq_answer(
                req.user_answer
            ) == _normalise_mcq_answer(correct)
        else:
            is_correct = self._semantic_grade(question_text, correct, req.user_answer)

        return AnswerFeedback(
            is_correct=is_correct,
            correct_answer=correct,
            explanation=explanation or "",
        )

    def _semantic_grade(self, question: str, correct: str, user_answer: str) -> bool:
        try:
            prompt = _semantic_grade_prompt(question, correct, user_answer)
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            result = _parse_json(response.text)
            return bool(result.get("is_correct", False))
        except Exception:
            return user_answer.strip().lower() == correct.strip().lower()

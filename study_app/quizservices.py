import json
import re
from uuid import UUID

from google import genai
from study_app.gemini import get_gemini_client
from study_app.database import get_supabase
from study_app.models import (
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
    "explanation": "Mitochondria are the site of cellular respiration, producing ATP from glucose and oxygen.",
    "difficulty": "medium"
  }},

  {{
    "question_type": "true or false",
    "question_text": "The Great Wall of China is visible from space.",
    "options": "True",
    "correct_answer": "True",
    "explanation": "The Great Wall of China is indeed visible from space.",
    "difficulty": "easy"
  }}
]

Rules:
- MCQ must have exactly 4 options labelled A, B, C, D. correct_answer is the letter only.
- True or False questions must have "True" or "False" as the only option.
- Every question must be directly answerable from the text — no outside knowledge required.
- Explanation must be 1–2 sentences, exam-focused.
- Vary difficulty: roughly 40% easy, 40% medium, 20% hard.

TEXT:
{text[:100000]}"""


def _semantic_grade_prompt(question: str, correct: str, user_answer: str) -> str:
    return f"""You are a strict but fair academic grader.

Question: {question}
Correct answer: {correct}
Student's answer: {user_answer}

Is the student's answer CORRECT? It is correct if it captures the same key concept,
even if worded differently. Minor spelling mistakes are acceptable.

Reply with ONLY a JSON object:
{{"is_correct": true/false, "reason": "one sentence explanation"}}"""


def _parse_json(raw: str) -> list | dict:
    cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
    return json.loads(cleaned)


def _normalise_mcq_answer(answer: str) -> str:
    """Accept 'B', 'b', 'B.', 'b)', 'option B' → always return 'B'."""
    match = re.search(r"[A-Da-d]", answer)
    return match.group(0).upper() if match else answer.strip().upper()


class QuizService:

    def __init__(self):
        self.model: genai.GenerativeModel = get_gemini_client()
        self.db = get_supabase()

    def generate_quiz(self, req: GenerateQuizRequest) -> QuizResponse:
        """
        Generate quiz questions for a content session and persist them.
        Returns questions WITHOUT correct answers (those are server-side only).
        """
        # 1. Fetch the session text (use simplified if available)
        session = (
            self.db.table("content_sessions")
            .select("normalised_text, simplified_text")
            .eq("id", str(req.session_id))
            .single()
            .execute()
        ).data
        text = session.get("simplified_text") or session["normalised_text"]

        # 2. Call Gemini
        prompt = _quiz_prompt(text, req.num_questions,
                              req.question_types, req.difficulty)
        response = self.model.generate_content(prompt)
        raw_qs = _parse_json(response.text)

        # 3. Persist questions (with answers, server-side only)
        rows = []
        for q in raw_qs:
            row = {
                "user_id":    str(req.user_id),
                "question_type":   q["question_type"],
                "question_text":   q["question_text"],
                "options":         q.get("options"),
                "correct_answer":  q["correct_answer"],
                "explanation":     q.get("explanation", ""),
                "difficulty":      q.get("difficulty", req.difficulty.value),
            }
            rows.append(row)

        inserted = self.db.table("quiz_questions").insert(rows).execute()

        # 4. Build client-safe response (no correct_answer)
        questions = [
            QuizQuestionResponse(
                id=r["id"],
                session_id=r["session_id"],
                question_type=r["question_type"],
                question_text=r["question_text"],
                options=r.get("options"),
                difficulty=r.get("difficulty"),
                created_at=r["created_at"],
            )
            for r in inserted.data
        ]

        return QuizResponse(
            session_id=req.session_id,
            questions=questions,
            total=len(questions),
        )

    def submit_answer(
        self,
        req: SubmitAnswerRequest,
        consecutive_correct: int = 0,
    ) -> AnswerFeedback:
        """
        Grade the user's answer, persist the attempt, and award XP.
        """
        # 1. Fetch question WITH correct answer
        q = (
            self.db.table("quiz_questions")
            .select("*")
            .eq("id", str(req.question_id))
            .single()
            .execute()
        ).data

        q_type = QuestionType(q["question_type"])
        correct = q["correct_answer"]
        explain = q.get("explanation", "")

        # 2. Adaptive Grading Logic
        if q_type == QuestionType.mcq:
            # Still use normalized string matching for Multiple Choice
            is_correct = _normalise_mcq_answer(
                req.user_answer) == _normalise_mcq_answer(correct)
        else:
            # USE AI FOR SEMANTIC GRADING (True/False or Short Answer)
            # This ensures "Mitochondria produce energy" is marked correct
            is_correct = self._semantic_grade(
                q["question_text"], correct, req.user_answer)

        # 3. Persist attempt
        self.db.table("quiz_attempts").insert({
            "question_id": str(req.question_id),
            "user_id":     str(req.user_id),
            "user_answer": req.user_answer,
            "is_correct":  is_correct,
        }).execute()

        return AnswerFeedback(
            question_id=req.question_id,
            is_correct=is_correct,
            correct_answer=correct,
            explanation=explain,
        )

    def _semantic_grade(self, question: str, correct: str, user_answer: str) -> bool:
        """Use Gemini to check if a flashcard answer is semantically correct."""
        try:
            prompt = _semantic_grade_prompt(question, correct, user_answer)
            response = self.model.generate_content(prompt)
            result = _parse_json(response.text)
            return bool(result.get("is_correct", False))
        except Exception:
            # Fallback to fuzzy string match if Gemini fails
            return user_answer.strip().lower() == correct.strip().lower()

    def get_unanswered(self, session_id: str, user_id: str) -> QuizResponse:
        """Returns only questions the user hasn't answered yet."""

        answered = (
            self.db.table("quiz_attempts")
            .select("question_id")
            .eq("user_id", str(user_id))
            .execute()
        ).data
        answered_ids = {r["question_id"] for r in answered}

        # Fetch session questions
        all_qs = (
            self.db.table("quiz_questions")
            .select("*")
            .eq("user_id", str(user_id))
            .eq("user_id", str(user_id))
            .execute()
        ).data

        unanswered = [q for q in all_qs if q["id"] not in answered_ids]

        questions = [
            QuizQuestionResponse(
                id=q["id"],
                session_id=q["session_id"],
                question_type=q["question_type"],
                question_text=q["question_text"],
                options=q.get("options"),
                difficulty=q.get("difficulty"),
                created_at=q["created_at"],
            )
            for q in unanswered
        ]
        return QuizResponse(
            session_id=UUID(session_id),
            questions=questions,
            total=len(questions),
        )

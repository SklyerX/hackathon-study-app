import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

export type Question = {
    id: string;
    session_id: string;
    question_type: "mcq" | "true_false" | "flashcard";
    question_text: string;
    options: string[] | string | null;
    difficulty: "easy" | "medium" | "hard";
    created_at: string;
};

export type AnswerFeedback = {
    question_id: string;
    is_correct: boolean;
    correct_answer: string;
    explanation: string;
};

type Props = {
    questions: Question[];
    sessionId: string; // comes back from ingestion response
    onComplete?: (score: number, total: number) => void;
};

async function submitAnswer(
    questionId: string,
    sessionId: string,
    userAnswer: string,
    streak: number
): Promise<AnswerFeedback> {
    const res = await fetch(
        `http://localhost:9999/api/quiz/answer?consecutive_correct=${streak}`,
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question_id: questionId,
                session_id: sessionId,
                user_answer: userAnswer,
            }),
        }
    );
    if (!res.ok) throw new Error("Failed to submit answer");
    return res.json();
}

const difficultyVariant: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    easy: "default",
    medium: "secondary",
    hard: "destructive",
};

export default function Quiz({ questions, sessionId, onComplete }: Props) {
    const [index, setIndex] = useState(0);
    const [selected, setSelected] = useState<string | null>(null);
    const [flashcardInput, setFlashcardInput] = useState("");
    const [feedback, setFeedback] = useState<AnswerFeedback | null>(null);
    const [loading, setLoading] = useState(false);
    const [score, setScore] = useState(0);
    const [streak, setStreak] = useState(0);
    const [done, setDone] = useState(false);

    const current = questions[index];
    const isLast = index === questions.length - 1;
    const progress = Math.round((index / questions.length) * 100);

    const handleSubmit = async () => {
        if (!current) return;
        const answer = current.question_type === "flashcard" ? flashcardInput : selected;
        if (!answer) return;

        setLoading(true);
        try {
            const fb = await submitAnswer(current.id, sessionId, answer, streak);
            setFeedback(fb);
            if (fb.is_correct) {
                setScore((s) => s + 1);
                setStreak((s) => s + 1);
            } else {
                setStreak(0);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleNext = () => {
        if (isLast) {
            setDone(true);
            onComplete?.(score + (feedback?.is_correct ? 1 : 0), questions.length);
            return;
        }
        setFeedback(null);
        setSelected(null);
        setFlashcardInput("");
        setIndex((i) => i + 1);
    };

    if (!questions.length) {
        return (
            <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
                No questions available.
            </div>
        );
    }

    if (done) {
        const pct = Math.round((score / questions.length) * 100);
        return (
            <div className="flex flex-col items-center justify-center gap-3 py-12">
                <p className="text-6xl font-bold">{pct}%</p>
                <p className="text-muted-foreground text-lg">
                    {score} / {questions.length} correct
                </p>
                <p className="text-sm text-muted-foreground">
                    {pct >= 80 ? "Great work!" : pct >= 50 ? "Keep practicing!" : "Review the material and try again."}
                </p>
            </div>
        );
    }

    const renderOptions = () => {
        if (current.question_type === "mcq") {
            const opts = Array.isArray(current.options) ? current.options : [];
            return (
                <div className="flex flex-col gap-2 mt-4">
                    {opts.map((opt) => {
                        const letter = opt.split(".")[0]?.trim() ?? opt;
                        const isSelected = selected === letter;
                        const isCorrect = feedback?.correct_answer === letter;
                        const isWrong = feedback && isSelected && !feedback.is_correct;

                        return (
                            <button
                                key={opt}
                                disabled={!!feedback}
                                onClick={() => setSelected(letter)}
                                className={cn(
                                    "text-left px-4 py-3 rounded-lg border text-sm transition-colors disabled:cursor-not-allowed",
                                    isCorrect
                                        ? "border-green-500 bg-green-50 dark:bg-green-950 text-green-800 dark:text-green-200"
                                        : isWrong
                                            ? "border-red-400 bg-red-50 dark:bg-red-950 text-red-800 dark:text-red-200"
                                            : isSelected
                                                ? "border-primary bg-primary/5"
                                                : "border-border hover:bg-muted"
                                )}
                            >
                                {opt}
                            </button>
                        );
                    })}
                </div>
            );
        }

        if (current.question_type === "true_false") {
            return (
                <div className="flex gap-3 mt-4">
                    {["True", "False"].map((opt) => {
                        const isSelected = selected === opt;
                        const isCorrect = feedback?.correct_answer === opt;
                        const isWrong = feedback && isSelected && !feedback.is_correct;

                        return (
                            <button
                                key={opt}
                                disabled={!!feedback}
                                onClick={() => setSelected(opt)}
                                className={cn(
                                    "flex-1 px-4 py-3 rounded-lg border text-sm font-medium transition-colors disabled:cursor-not-allowed",
                                    isCorrect
                                        ? "border-green-500 bg-green-50 dark:bg-green-950 text-green-800 dark:text-green-200"
                                        : isWrong
                                            ? "border-red-400 bg-red-50 dark:bg-red-950 text-red-800 dark:text-red-200"
                                            : isSelected
                                                ? "border-primary bg-primary/5"
                                                : "border-border hover:bg-muted"
                                )}
                            >
                                {opt}
                            </button>
                        );
                    })}
                </div>
            );
        }

        if (current.question_type === "flashcard") {
            return (
                <Textarea
                    disabled={!!feedback}
                    value={flashcardInput}
                    onChange={(e) => setFlashcardInput(e.target.value)}
                    placeholder="Type your answer..."
                    rows={3}
                    className="mt-4 resize-none"
                />
            );
        }

        return null;
    };

    const canSubmit =
        !feedback &&
        !loading &&
        (current.question_type === "flashcard"
            ? flashcardInput.trim().length > 0
            : !!selected);

    return (
        <div className="flex flex-col gap-4 w-full max-w-2xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>Question {index + 1} of {questions.length}</span>
                <div className="flex items-center gap-2">
                    {streak > 1 && (
                        <span className="text-orange-500 font-medium text-sm">
                            🔥 {streak} streak
                        </span>
                    )}
                    <Badge variant={difficultyVariant[current.difficulty] ?? "outline"}>
                        {current.difficulty}
                    </Badge>
                    <Badge variant="outline">{current.question_type}</Badge>
                </div>
            </div>

            {/* Progress */}
            <Progress value={progress} className="h-1.5" />

            {/* Question card */}
            <Card>
                <CardContent className="pt-6">
                    <p className="text-base font-medium leading-relaxed">
                        {current.question_text}
                    </p>
                    {renderOptions()}
                </CardContent>
            </Card>

            {/* Feedback */}
            {feedback && (
                <Alert variant={feedback.is_correct ? "default" : "destructive"}>
                    <AlertTitle>
                        {feedback.is_correct ? "Correct!" : `Incorrect — ${feedback.correct_answer}`}
                    </AlertTitle>
                    {feedback.explanation && (
                        <AlertDescription>{feedback.explanation}</AlertDescription>
                    )}
                </Alert>
            )}

            {/* Actions */}
            <div className="flex justify-end">
                {!feedback ? (
                    <Button disabled={!canSubmit} onClick={handleSubmit}>
                        {loading ? "Checking..." : "Submit"}
                    </Button>
                ) : (
                    <Button onClick={handleNext}>
                        {isLast ? "Finish" : "Next"}
                    </Button>
                )}
            </div>
        </div>
    );
}
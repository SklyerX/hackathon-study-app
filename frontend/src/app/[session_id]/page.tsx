"use client";

import { AudioPlayer, AudioPlayerControlBar, AudioPlayerDurationDisplay, AudioPlayerElement, AudioPlayerMuteButton, AudioPlayerPlayButton, AudioPlayerSeekBackwardButton, AudioPlayerSeekForwardButton, AudioPlayerTimeDisplay, AudioPlayerTimeRange, AudioPlayerVolumeRange } from "@/components/ai-elements/audio-player";
import Quiz from "@/components/quiz-me";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { AudioLines, BrainCircuit, Loader2, Pen } from "lucide-react";
import { redirect, useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import ReactMarkdown from "react-markdown";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Field, FieldContent, FieldDescription, FieldLabel, FieldTitle } from "@/components/ui/field";
import { Input } from "@/components/ui/input";


export default function Page() {
    const [value, setValue] = useState("summary")
    const { session_id } = useParams();
    const [sessionSummary, setSessionSummary] = useState<string>("");
    const [speechData, setSpeechData] = useState<any | null>(null);
    const [questions, setQuestions] = useState<any[]>([]);
    const [speechText, setSpeechText] = useState<string>("");
    const [difficulty, setDifficulty] = useState<string>("medium");
    const [numQuestions, setNumQuestions] = useState<number>(25);

    const [loadingStates, setLoadingStates] = useState({
        summary: false,
        speech: false,
        quiz: false,
    })

    if (!session_id) return redirect("/")


    const updateLoadingState = (key: keyof typeof loadingStates, value: boolean) => setLoadingStates((prev) => ({ ...prev, [key]: value }))

    useEffect(() => {
        if (!session_id) return;

        const fetchSummaryData = async () => {
            updateLoadingState("summary", true)
            const res = await fetch(`http://localhost:9999/api/study/explain`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"  // 👈 this
                },
                body: JSON.stringify({
                    session_id
                })
            });
            if (!res.ok) return toast.error("Failed to fetch summary");

            const data = await res.json();

            setSessionSummary(data.explanation)
            updateLoadingState("summary", false)
        }

        if (value === "summary" && !sessionSummary) fetchSummaryData();
    }, [session_id, value]);

    const handleSpeechify = async () => {
        updateLoadingState("speech", true)

        const res = await fetch("http://localhost:9999/api/audio/read-premium", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                content: speechText
            })
        });

        if (!res.ok) return toast.error("Failed to speechify your text");

        const data = await res.json();

        const response = await fetch(
            `http://localhost:9999${data.url}`
        );

        const arrayBuffer = await response.arrayBuffer();
        const base64 = Buffer.from(arrayBuffer).toString("base64");

        const newData: any = {
            base64,
            format: "wav",
            mediaType: "audio/wav",
            uint8Array: new Uint8Array(arrayBuffer),
        };

        setSpeechData(newData);
        updateLoadingState("speech", false)
    }

    const fetchQuiz = async () => {
        updateLoadingState("quiz", true)
        const res = await fetch(`http://localhost:9999/api/quiz/generate`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"  // 👈 this
            },
            body: JSON.stringify({
                session_id,
                "num_questions": numQuestions,
                "difficulty": difficulty,
                "question_types": ["mcq", "true_false"]
            })
        });
        if (!res.ok) return toast.error("Failed to fetch summary");

        const data = await res.json();

        setQuestions(data.questions)
        updateLoadingState("quiz", false)
    }

    return (
        <div>
            <Tabs value={value} onValueChange={(value) => setValue(value)} defaultValue="summary">
                <TabsList variant="line">
                    <TabsTrigger value="summary">
                        <BrainCircuit className="size-4" />
                        Summary
                    </TabsTrigger>
                    <TabsTrigger value="speech">
                        <AudioLines className="size-4" />
                        Speech
                    </TabsTrigger>
                    <TabsTrigger value="quiz">
                        <Pen className="size-4" />
                        Quiz</TabsTrigger>
                </TabsList>
            </Tabs>

            <div className="mt-5">
                {value === "quiz" && !loadingStates.quiz ?
                    questions.length > 0 ? (
                        <Quiz questions={questions} sessionId={session_id as string} />
                    ) : (
                        <>
                            <RadioGroup defaultValue="easy" onValueChange={(value) => setDifficulty(value)}>
                                <FieldLabel htmlFor="easy-difficulty">
                                    <Field orientation="horizontal">
                                        <FieldContent>
                                            <FieldTitle>Easy</FieldTitle>
                                            <FieldDescription>
                                                Easy peasy lemon squeezy
                                            </FieldDescription>
                                        </FieldContent>
                                        <RadioGroupItem value="easy" id="easy-difficulty" />
                                    </Field>
                                </FieldLabel>
                                <FieldLabel htmlFor="medium-difficulty">
                                    <Field orientation="horizontal">
                                        <FieldContent>
                                            <FieldTitle>Medium</FieldTitle>
                                            <FieldDescription>A little harder but not the hardest.</FieldDescription>
                                        </FieldContent>
                                        <RadioGroupItem value="medium" id="medium-difficulty" />
                                    </Field>
                                </FieldLabel>
                                <FieldLabel htmlFor="hard-difficulty">
                                    <Field orientation="horizontal">
                                        <FieldContent>
                                            <FieldTitle>Hard</FieldTitle>
                                            <FieldDescription>
                                                You think you know it all huh? give it a try
                                            </FieldDescription>
                                        </FieldContent>
                                        <RadioGroupItem value="hard" id="hard-plan" />
                                    </Field>
                                </FieldLabel>
                            </RadioGroup>

                            <Input value={numQuestions} type="number" onChange={({ target }) => setNumQuestions(Number(target.value))} className="my-2" />

                            <Button className="mt-2 w-full" onClick={fetchQuiz}>Generate quiz</Button>
                        </>
                    )
                    : null}
                {value === "quiz" &&
                    loadingStates.quiz ? (
                    <div className="flex flex-row items-center gap-4">
                        <Loader2 className="size-4 animate-spin" />
                        Generating quiz... stand by!
                    </div>
                ) : null}
                {value === "summary" ?
                    !loadingStates.summary ? (
                        <><h3 className="text-lg font-semibold">Summarization below</h3>
                            <p className="mt-px text-muted-foreground mb-4">Your AI analysis is shown below</p>
                            <ReactMarkdown>{sessionSummary}</ReactMarkdown></>
                    ) : (
                        <div className="flex items-center gap-2">
                            <Loader2 className="size-4 animate-spin" />
                            Generating AI summary
                        </div>
                    )
                    : null}
                {value === "speech" ? speechData ? (
                    <>
                        <AudioPlayer>
                            <AudioPlayerElement data={speechData} />
                            <AudioPlayerControlBar>
                                <AudioPlayerPlayButton />
                                <AudioPlayerSeekBackwardButton seekOffset={10} />
                                <AudioPlayerSeekForwardButton seekOffset={10} />
                                <AudioPlayerTimeDisplay />
                                <AudioPlayerTimeRange />
                                <AudioPlayerDurationDisplay />
                                <AudioPlayerMuteButton />
                                <AudioPlayerVolumeRange />
                            </AudioPlayerControlBar>
                        </AudioPlayer>
                        <div className="mt-5 border-t py-4">
                            {speechText}
                        </div>
                    </>
                ) : (
                    <>
                        <h3 className="text-lg font-semibold">Speechify mode</h3>
                        <p className="mt-px text-muted-foreground">Please paste the text you want read out to you below!</p>
                        <Textarea value={speechText} onChange={({ target }) => setSpeechText(target.value)} className="mt-5 h-52" placeholder="Today in lecture we're going to discuss..." />
                        <Button className="w-full mt-2" size="lg" onClick={handleSpeechify} disabled={loadingStates.speech}>
                            {loadingStates.speech ? (
                                <>
                                    <Loader2 className="size-4 animate-spin" />
                                    Speechifying...
                                </>
                            ) : "Speechify!"}
                        </Button>
                    </>
                ) : null}
            </div>
        </div>
    );
}

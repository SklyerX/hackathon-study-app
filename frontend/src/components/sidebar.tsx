'use client'

import { AudioLines, BrainCircuit, ScrollText, WandSparkles } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from "clsx";

const options = [
    {
        name: "Summary",
        icon: BrainCircuit,
        href: "/"
    },
    {
        name: "Quiz",
        icon: ScrollText,
        href: "/quiz"
    },
    {
        name: "Speech",
        icon: AudioLines,
        href: "/speech"
    },
    {
        name: "Simplify",
        icon: WandSparkles,
        href: "/simplify"
    }
]

export default function Navbar() {
    const pathname = usePathname()
    return (
        <div className='flex items-center justify-center py-5 gap-10'>
            {options.map((opt) => (
                <Link href={opt.href} className={clsx('text-muted-foreground! flex! items-center gap-2 hover:text-foreground', {
                    "bg-[#272727] text-white! px-3 py-1.5 rounded-md": pathname === opt.href
                })} key={opt.href}>
                    <opt.icon className='size-5' />
                    <span>{opt.name}</span>
                </Link>
            ))}
        </div>
    )
}

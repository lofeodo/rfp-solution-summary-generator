import { Link } from "react-router-dom";

export default function Masthead({ compact = false }: { compact?: boolean }) {
  if (compact)
    return (
      <div className="flex items-baseline justify-between gap-4 border-b-2 border-ink pb-2">
        <Link to="/" className="font-display text-lg font-extrabold tracking-tight hover:text-accent">
          RFP<span className="text-accent">/</span>Summary
        </Link>
        <Link to="/" className="kicker hover:text-ink">
          ← All runs
        </Link>
      </div>
    );
  return (
    <header className="grid grid-cols-12 md:gap-x-6 border-b-2 border-ink pb-6">
      <p className="kicker col-span-12 mb-4 md:col-span-3 md:mb-0 md:pt-3">
        Agentic pipeline
        <br />
        Parse · Extract · Propose · Assess
      </p>
      <h1 className="display col-span-12 text-[clamp(3rem,8vw,7.5rem)] md:col-span-9">
        RFP<span className="text-accent">/</span>Solution
        <br />
        <span className="ml-[0.6em] font-serif font-normal italic tracking-[-0.02em]">summary</span>
      </h1>
    </header>
  );
}

import Link from "next/link";

/** Server component nav — avoids unnecessary client hydration. */
export function Nav() {
  return (
    <header className="border-b border-zinc-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/" className="text-sm font-semibold tracking-tight text-zinc-900">
          AssessGen
        </Link>
        <nav className="flex gap-4 text-sm text-zinc-600">
          <Link href="/generate" className="hover:text-zinc-900">
            Generate
          </Link>
          <Link href="/listening-audio" className="hover:text-zinc-900">
            Listening audio
          </Link>
          <a
            href="http://127.0.0.1:8080/api/docs"
            target="_blank"
            rel="noreferrer"
            className="hover:text-zinc-900"
          >
            API docs
          </a>
        </nav>
      </div>
    </header>
  );
}

import { Nav } from "@/components/nav";
import "./globals.css";

export const metadata = {
  title: "AssessGen",
  description: "Lightweight IELTS practice content generator",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // suppressHydrationWarning: browser extensions often inject attrs on <html>/<body>
    <html lang="en" suppressHydrationWarning>
      <body
        className="min-h-screen bg-zinc-50 text-zinc-900 antialiased"
        suppressHydrationWarning
      >
        <Nav />
        <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}

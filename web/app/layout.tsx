import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Crew 618-J · Philmont 2026",
  description: "Itinerary 12-1 · South Country Loop · 53.3 miles · June 18–29, 2026",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-stone-50 text-stone-900 min-h-screen">
        <header className="bg-forest-800 text-white shadow-md">
          <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-3 hover:opacity-90 transition-opacity">
              <span className="text-2xl">⛺</span>
              <div>
                <div className="font-bold text-lg leading-tight">Crew 618-J</div>
                <div className="text-xs text-green-200 leading-tight">Philmont 2026 · South Country Loop</div>
              </div>
            </Link>
            <nav className="flex gap-4 text-sm">
              <Link href="/" className="hover:text-green-200 transition-colors">Overview</Link>
              <Link href="/itinerary/" className="hover:text-green-200 transition-colors">Itinerary</Link>
            </nav>
          </div>
        </header>
        <main className="max-w-6xl mx-auto px-4 py-6">
          {children}
        </main>
        <footer className="border-t border-stone-200 mt-12 py-6 text-center text-xs text-stone-400">
          Crew 618-J · Itinerary 12-1 Challenging · Philmont Scout Ranch · June 2026
        </footer>
      </body>
    </html>
  );
}

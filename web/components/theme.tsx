"use client";
import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

/** Inline script run before paint so the saved theme never flashes. */
export const THEME_SCRIPT = `try{var h=document.documentElement;if(localStorage.getItem("theme")==="dark"){h.classList.add("dark");h.classList.remove("light");h.style.colorScheme="dark"}}catch(e){}`;

export function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => setDark(document.documentElement.classList.contains("dark")), []);
  const flip = () => {
    const d = !dark; setDark(d);
    const h = document.documentElement; h.classList.toggle("dark", d); h.classList.toggle("light", !d); h.style.colorScheme = d ? "dark" : "light";
    try { localStorage.setItem("theme", d ? "dark" : "light"); } catch { /* private mode */ }
  };
  return (
    <button onClick={flip} aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      className="tap grid h-9 w-9 place-items-center rounded-xl text-slate-600 ring-1 ring-slate-200 hover:bg-slate-100">
      {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}

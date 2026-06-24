import { useEffect, useState } from "react";
import { authConfig, login } from "../api";

/** SPA sign-in gate. Validates against the backend, stores a session token. */
export default function Login({ onAuthed, onBack }: { onAuthed: () => void; onBack: () => void }) {
  const [workspace, setWorkspace] = useState("Foresight");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    authConfig().then((c) => { setWorkspace(c.workspace); setEmail(c.demo_email); }).catch(() => {});
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      const r = await login(email, password);
      if (r.ok && r.token) {
        localStorage.setItem("foresight-auth", r.token);
        localStorage.setItem("foresight-workspace", r.workspace || workspace);
        localStorage.setItem("foresight-email", r.email || email);
        onAuthed();
      } else {
        setErr(r.detail || "Invalid email or password");
      }
    } catch {
      setErr("Could not reach the server.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-[100dvh] grid place-items-center bg-gray-950 text-gray-100 px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2.5 mb-6 justify-center">
          <span className="grid place-items-center w-9 h-9 rounded-lg bg-[#FFB600] text-black text-xl leading-none">◎</span>
          <span className="font-grotesk font-extrabold text-xl">Foresight</span>
        </div>
        <div className="rounded-2xl ring-1 ring-white/10 bg-gray-900 p-6">
          <h1 className="font-grotesk text-lg font-bold">Sign in</h1>
          <p className="text-xs text-gray-400 mt-1">to the <b className="text-gray-200">{workspace}</b> workspace</p>
          <form onSubmit={submit} className="flex flex-col gap-3 mt-5">
            <label className="text-xs text-gray-400">Email
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoFocus
                className="w-full mt-1 bg-gray-950 border border-white/10 rounded-md px-3 py-2 text-sm outline-none focus:border-[#FFB600]/60" />
            </label>
            <label className="text-xs text-gray-400">Password
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                className="w-full mt-1 bg-gray-950 border border-white/10 rounded-md px-3 py-2 text-sm outline-none focus:border-[#FFB600]/60" />
            </label>
            {err && <p className="text-xs text-red-400">{err}</p>}
            <button type="submit" disabled={busy}
              className="mt-1 w-full py-2.5 rounded-md bg-[#FFB600] text-black text-sm font-bold disabled:opacity-50 hover:opacity-90 transition">
              {busy ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="text-[11px] text-gray-500 mt-4">
            Demo access: <span className="font-mono text-gray-400">{email || "demo@foresight.ai"}</span> /
            <span className="font-mono text-gray-400"> foresight</span>
          </p>
        </div>
        <button onClick={onBack} className="text-xs text-gray-500 hover:text-gray-300 mt-4 mx-auto block">← Back to home</button>
      </div>
    </div>
  );
}

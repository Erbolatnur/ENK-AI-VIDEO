"use client";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

type Job = { id: string; prompt: string; aspect: string; duration: number; status: "queued" | "processing" | "done" | "failed"; progress: number; error?: string };
type Model = { id: string; title: string; available: boolean };
const ASPECTS = ["9:16", "16:9", "1:1"];
const STATUS = { queued: "В очереди", processing: "Создаётся", done: "Готово", failed: "Ошибка" };
const frameClass = (a: string) => (a === "9:16" ? "tall" : a === "16:9" ? "wide" : "sq");

export default function Home() {
  const [token, setToken] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [models, setModels] = useState<Model[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [prompt, setPrompt] = useState("");
  const [aspect, setAspect] = useState("9:16");
  const [duration, setDuration] = useState(5);
  const [model, setModel] = useState("demo");
  const [subtitles, setSubtitles] = useState(true);
  const [image, setImage] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [video, setVideo] = useState<{ id: string; url: string; aspect: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const api = useCallback(async (path: string, init: RequestInit = {}) => {
    const res = await fetch(path, { ...init, headers: { Authorization: `Bearer ${token}` } });
    if (res.status === 401) { localStorage.removeItem("enk_token"); setToken(null); throw new Error("Неверный токен. Войдите снова."); }
    if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(typeof d.detail === "string" ? d.detail : `Ошибка запроса (${res.status})`); }
    return res;
  }, [token]);

  useEffect(() => { setToken(localStorage.getItem("enk_token")); }, []);
  useEffect(() => {
    if (!token) return;
    let stop = false;
    const tick = async () => { try { const r = await api("/api/jobs"); const d = await r.json(); if (!stop) setJobs(d); } catch { /* повторим через 3 с */ } };
    api("/api/models").then((r) => r.json()).then(setModels).catch(() => {});
    tick();
    const t = setInterval(tick, 3000);
    return () => { stop = true; clearInterval(t); };
  }, [token, api]);

  async function create(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      const f = new FormData();
      f.append("prompt", prompt); f.append("aspect", aspect); f.append("duration", String(duration));
      f.append("model", model); f.append("subtitles", String(subtitles));
      if (image) f.append("image", image);
      await api("/api/jobs", { method: "POST", body: f });
      setPrompt(""); setImage(null); if (fileRef.current) fileRef.current.value = "";
    } catch (err) { setError((err as Error).message); } finally { setBusy(false); }
  }

  async function open(j: Job) {
    setError("");
    try {
      const blob = await (await api(`/api/jobs/${j.id}/download`)).blob();
      setVideo((v) => { if (v) URL.revokeObjectURL(v.url); return { id: j.id, url: URL.createObjectURL(blob), aspect: j.aspect }; });
    } catch (err) { setError((err as Error).message); }
  }

  if (!token) {
    return (
      <main className="login">
        <h1 className="logo" style={{ marginBottom: 20 }}>ENK <b>AI VIDEO</b></h1>
        <form className="panel" onSubmit={(e) => { e.preventDefault(); const t = draft.trim(); if (t) { localStorage.setItem("enk_token", t); setToken(t); } }}>
          <label htmlFor="tk" style={{ marginTop: 0 }}>Токен доступа</label>
          <input id="tk" type="password" value={draft} onChange={(e) => setDraft(e.target.value)} autoFocus />
          <button className="go" type="submit">Войти</button>
          {error && <p className="err" role="alert">{error}</p>}
        </form>
      </main>
    );
  }

  const cur = model === "demo";
  const shown = video ? video.aspect : aspect;
  return (
    <>
      <header className="top">
        <span className="logo">ENK <b>AI VIDEO</b></span>
        <button className="ghost" onClick={() => { localStorage.removeItem("enk_token"); setToken(null); setJobs([]); setVideo(null); }}>Выйти</button>
      </header>
      <div className="wrap">
        <form className="panel" onSubmit={create}>
          <h2>Новое видео</h2>
          <label htmlFor="pr" style={{ marginTop: 0 }}>Описание сцены</label>
          <textarea id="pr" required maxLength={1000} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="Например: неоновый город ночью, камера медленно летит вдоль улицы" />
          <label>Формат</label>
          <div className="seg">{ASPECTS.map((a) => <button type="button" key={a} aria-pressed={aspect === a} onClick={() => setAspect(a)}>{a}</button>)}</div>
          <label htmlFor="du">Длительность: {duration} с</label>
          <input id="du" type="range" min={2} max={15} value={duration} onChange={(e) => setDuration(+e.target.value)} />
          <label htmlFor="mo">Модель</label>
          <select id="mo" value={model} onChange={(e) => setModel(e.target.value)}>
            {models.length === 0 && <option value="demo">DEMO</option>}
            {models.map((m) => <option key={m.id} value={m.id} disabled={!m.available}>{m.title}{m.available ? "" : " (нужен ключ)"}</option>)}
          </select>
          <label htmlFor="im">Фото для анимации (необязательно)</label>
          <input id="im" ref={fileRef} type="file" accept="image/png,image/jpeg" onChange={(e) => setImage(e.target.files?.[0] ?? null)} />
          <label className="check"><input type="checkbox" checked={subtitles} onChange={(e) => setSubtitles(e.target.checked)} />Добавить субтитры</label>
          {cur && <p className="note">В режиме DEMO видео собирается без нейросети: анимированный фон или плавное приближение фото.</p>}
          <button className="go" type="submit" disabled={busy || !prompt.trim()}>{busy ? "Отправляем" : "Создать видео"}</button>
          {error && <p className="err" role="alert">{error}</p>}
        </form>
        <section>
          <div className="stage">
            <div className={`frame ${frameClass(shown)}`} key={shown + (video?.id ?? "")} style={{ ["--ar" as string]: shown.replace(":", " / ") }}>
              {video ? <video src={video.url} controls playsInline autoPlay loop /> : <span>Здесь появится готовое видео</span>}
            </div>
          </div>
          {video && <div className="bar"><a className="btn-link" href={video.url} download={`enk-${video.id.slice(0, 8)}.mp4`}>Скачать MP4</a></div>}
          <div className="panel" style={{ marginTop: 20 }}>
            <h2>Мои проекты</h2>
            {jobs.length === 0 ? <p className="note" style={{ margin: 0 }}>Пока пусто. Опишите сцену слева и нажмите «Создать видео».</p> : (
              <ul className="jobs">{jobs.map((j) => (
                <li className="job" key={j.id}>
                  <p>{j.prompt}</p>
                  <div className="row"><span>{j.aspect}, {j.duration} с</span><span>{STATUS[j.status]}</span></div>
                  {(j.status === "queued" || j.status === "processing") && <div className="prog"><i style={{ width: `${j.progress}%` }} /></div>}
                  {j.status === "failed" && <span className="err" style={{ margin: 0 }}>{j.error}</span>}
                  {j.status === "done" && <button className="ghost" onClick={() => open(j)}>Смотреть</button>}
                </li>))}
              </ul>)}
          </div>
        </section>
      </div>
    </>
  );
}

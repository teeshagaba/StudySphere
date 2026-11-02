# StudyOS

AI-powered study & placement operating system — DSA tracking with cross-sheet sync, contest aggregation, AI mentor, coding playground, notes, spaced revision, company readiness, knowledge graph, AI learning tracker, focus mode, career tracker, analytics and gamification.

**Stack:** Next.js 15 + TypeScript · FastAPI · PostgreSQL · Redis · Azure OpenAI · Judge0

## Quick start

```bash
cp backend/.env.example backend/.env   # set JWT_SECRET, Azure OpenAI, Judge0
docker compose up --build
```

Open http://localhost:3000. API docs: http://localhost:8000/docs.

### Local dev (without Docker for the apps)

```bash
docker compose up -d postgres redis
cd backend && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
uvicorn app.main:app --reload
cd ../frontend && npm install && npm run dev
```

### Judge0

Either self-host ([judge0/judge0](https://github.com/judge0/judge0)) and set `JUDGE0_URL`, or use RapidAPI with `JUDGE0_URL=https://judge0-ce.p.rapidapi.com` and `JUDGE0_API_KEY`.

## How the key features work

| Feature | Implementation |
|---|---|
| Cross-sheet completion | Every sheet references a canonical `Question` (by LeetCode slug / URL alias / title). Progress is stored once per user per question, so solving it updates Blind 75, NeetCode 150, company sheets, etc. at once. Import any sheet via `POST /api/dsa/sheets/import`. |
| Contests | LeetCode, Codeforces, CodeChef via official/public APIs; AtCoder, HackerRank, HackerEarth, TopCoder, Kaggle, GFG, CodinGame, etc. via [clist.by](https://clist.by) (set `CLIST_*`). Cached in Redis for 30 min. |
| AI Mentor | 5 modes (hint, teacher, interviewer, debugger, planner). Hints escalate 1→3. Full solution only unlocks after ≥2 attempts or ≥30 min on the problem. |
| Revision | Solving schedules reviews at 1 → 3 → 7 → 15 → 30 → 60 days; forgetting resets to day 1. |
| Mastery | Per topic: Σ difficulty weight × confidence × revision stage, normalised to 100. Knowledge graph adds prerequisites and recommends unlocked weak topics. |
| Company readiness | 60% frequency-weighted coverage of the company's questions + 40% mastery of the topics they ask. |
| Playground | Judge0 execution for C++, Java, Python, JavaScript, Go; AI review with complexity analysis; AI-simulated dry-run stepper. |
| Gamification | XP for solves/revisions/focus/learning, levels, streaks, badges. |

Schema is auto-created on startup for development; add Alembic migrations before production.

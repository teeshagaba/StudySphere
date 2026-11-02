"""AI-Era Interview Prep — practice series C (more exercises for every section)."""

TTL_CACHE = '''import time
import threading


class TTLCache:
    """Thread-safe in-memory cache where each entry expires after ttl seconds."""

    def __init__(self, ttl: float, max_items: int = 1000):
        self.ttl = ttl
        self.max_items = max_items
        self._data = {}
        self._lock = threading.Lock()

    def get(self, key):
        item = self._data.get(key)  #!BUG Read happens outside the lock while set()/cleanup mutate the dict
        if item is None:
            return None
        value, expires = item
        if expires < time.time():
            return value  #!BUG Expired entries are returned instead of being treated as a miss (and evicted)
        return value

    def set(self, key, value):
        with self._lock:
            if len(self._data) > self.max_items:  #!BUG Off-by-one: allows max_items + 1 entries before evicting
                self._data.clear()  #!BUG Clearing everything on overflow causes a sudden 100% miss rate (use LRU eviction)
            self._data[key] = (value, time.time() + self.ttl)
'''

PAGINATE_JS = '''// Returns one page of orders for the infinite-scroll list.
async function listOrders(db, userId, page = 1, pageSize = 20) {
  const offset = page * pageSize;  //!BUG Page 1 skips the first 20 rows — offset should be (page - 1) * pageSize
  const rows = await db.query(
    `SELECT * FROM orders WHERE user_id = ${userId} ORDER BY created_at DESC LIMIT ${pageSize} OFFSET ${offset}`  //!BUG SQL injection via string interpolation; also pageSize is unbounded
  );
  return {
    items: rows,
    hasMore: rows.length > 0,  //!BUG Always true when a page is non-empty — should be rows.length === pageSize (or fetch pageSize + 1)
  };
}
'''

RETRY = '''import random
import time

import requests


def fetch_with_retry(url: str, retries: int = 5) -> dict:
    for attempt in range(retries):
        try:
            resp = requests.get(url)  #!BUG No timeout: a hung connection blocks this worker forever
            resp.raise_for_status()
            return resp.json()
        except Exception:  #!BUG Retries everything, including 4xx client errors that will never succeed
            time.sleep(2 ** attempt)  #!BUG No jitter: many clients retry in lock-step (thundering herd)
    return {}  #!BUG Silently returns {} after exhausting retries — callers can't tell failure from an empty result
'''

AI_KTH = '''import heapq


def kth_largest(nums: list[int], k: int) -> int:
    """Return the k-th largest element. O(n log k) time, O(k) space."""
    heap = []
    for x in nums:
        heapq.heappush(heap, x)
        if len(heap) > k:
            heapq.heappop(heap)
    return heap[0]
'''

AI_ANAGRAMS = '''from collections import defaultdict


def group_anagrams(words: list[str]) -> list[list[str]]:
    groups = defaultdict(list)
    for w in words:
        groups["".join(sorted(w))].append(w)
    return list(groups.values())
'''

AI_DEBOUNCE = '''// Debounce: run fn only after `wait` ms have passed without another call.
function debounce(fn, wait) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), wait);
  };
}
'''

TZ_BUG = '''from datetime import datetime, date


def orders_for_day(db, day: date):
    """All orders placed on `day` (business runs in IST, UTC+5:30)."""
    start = datetime(day.year, day.month, day.day)  #!BUG Naive datetime is interpreted as UTC by the DB — IST day boundaries are off by 5:30
    end = datetime(day.year, day.month, day.day, 23, 59, 59)  #!BUG Misses orders in the last second (use < next day's midnight)
    return db.execute(
        "SELECT * FROM orders WHERE created_at BETWEEN %s AND %s", (start, end)
    ).fetchall()
'''

REACT_LEAK = '''import { useEffect, useState } from "react";

export function LivePrice({ symbol }) {
  const [price, setPrice] = useState(null);

  useEffect(() => {
    const id = setInterval(async () => {
      const res = await fetch(`/api/price/${symbol}`);
      setPrice((await res.json()).price);
    }, 1000);
  }, [symbol]);  //!BUG No cleanup: every symbol change / remount leaks another interval (clearInterval in the returned function)

  return <span>{price ?? "…"}</span>;
}
'''

DEADLOCK_SQL = '''-- Transfer service: two requests run concurrently
-- Request A: transfer(1 -> 2)            Request B: transfer(2 -> 1)
BEGIN;
UPDATE accounts SET balance = balance - 100 WHERE id = :from_id;  --!BUG Locks rows in request order: A locks 1 then 2, B locks 2 then 1 → deadlock
UPDATE accounts SET balance = balance + 100 WHERE id = :to_id;
COMMIT;
'''

EXPRESS_REPO = [
    ("server.js", "javascript", '''const express = require("express");
const todos = require("./routes/todos");
const { requireUser } = require("./middleware/auth");

const app = express();
app.use(express.json());
app.use("/api/todos", requireUser, todos);
app.use((err, req, res, next) => {
  console.error(err);
  res.status(500).json({ error: "internal" });
});
app.listen(process.env.PORT || 3000);
'''),
    ("middleware/auth.js", "javascript", '''const jwt = require("jsonwebtoken");

exports.requireUser = (req, res, next) => {
  const token = (req.headers.authorization || "").replace("Bearer ", "");
  try {
    req.user = jwt.verify(token, process.env.JWT_SECRET);
    next();
  } catch {
    res.status(401).json({ error: "unauthorized" });
  }
};
'''),
    ("routes/todos.js", "javascript", '''const router = require("express").Router();
const db = require("../db");

router.get("/", async (req, res, next) => {
  try {
    res.json(await db.todos.findMany({ where: { userId: req.user.id }, take: 50 }));
  } catch (e) { next(e); }
});

router.patch("/:id", async (req, res, next) => {
  try {
    const todo = await db.todos.update({ where: { id: Number(req.params.id) }, data: req.body });
    res.json(todo);
  } catch (e) { next(e); }
});

module.exports = router;
'''),
]

CLI_REPO = [
    ("cli.py", "python", '''import argparse

from backup.runner import run_backup


def main():
    p = argparse.ArgumentParser(prog="backup")
    p.add_argument("source")
    p.add_argument("--dest", default="s3://company-backups")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    run_backup(args.source, args.dest, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
'''),
    ("backup/runner.py", "python", '''from pathlib import Path

from .storage import upload
from .state import load_manifest, save_manifest


def run_backup(source: str, dest: str, dry_run: bool = False) -> None:
    manifest = load_manifest(dest)
    for path in Path(source).rglob("*"):
        if path.is_file() and manifest.get(str(path)) != path.stat().st_mtime:
            if not dry_run:
                upload(path, dest)
                manifest[str(path)] = path.stat().st_mtime
    if not dry_run:
        save_manifest(dest, manifest)
'''),
    ("backup/state.py", "python", '''import json

from .storage import read_text, write_text


def load_manifest(dest: str) -> dict:
    try:
        return json.loads(read_text(f"{dest}/manifest.json"))
    except FileNotFoundError:
        return {}


def save_manifest(dest: str, manifest: dict) -> None:
    write_text(f"{dest}/manifest.json", json.dumps(manifest))
'''),
]

HIT_COUNTER = '''class HitCounter:
    """Counts hits in the last 5 minutes. hit(ts) and get_hits(ts) are called with increasing timestamps (seconds)."""

    def __init__(self):
        self.hits = []

    def hit(self, timestamp: int) -> None:
        self.hits.append(timestamp)

    def get_hits(self, timestamp: int) -> int:
        count = 0
        for t in self.hits:  #!BUG O(total hits) per call and the list grows forever (memory leak)
            if timestamp - t <= 300:  #!BUG Window is 301 seconds wide — should be < 300
                count += 1
        return count
'''

MERGE_FEEDS = '''def merge_feeds(feeds: list[list[dict]], limit: int) -> list[dict]:
    """Each feed is sorted by 'ts' descending. Return the newest `limit` posts overall."""
    merged = []
    for feed in feeds:
        merged.extend(feed)  #!BUG Copies every post from every feed — O(N) memory even when limit is tiny
    merged.sort(key=lambda p: p["ts"])  #!BUG Sorted ascending: returns the OLDEST posts, not the newest
    return merged[:limit]
'''

SCHEDULER = '''import time


class Scheduler:
    def __init__(self):
        self.jobs = []  # (run_at, fn)

    def schedule(self, delay_s: float, fn) -> None:
        self.jobs.append((time.time() + delay_s, fn))

    def run_pending(self) -> None:
        now = time.time()
        for job in self.jobs:  #!BUG Removing from the list while iterating it skips the next job
            run_at, fn = job
            if run_at <= now:
                fn()  #!BUG One failing job raises and stops every remaining job
                self.jobs.remove(job)  #!BUG O(n) removal per job; a min-heap keyed by run_at is O(log n)
'''

PR_NODE_AUTH = '''--- a/src/routes/auth.js
+++ b/src/routes/auth.js
+router.post("/login", async (req, res) => {
+  const user = await User.findOne({ email: req.body.email });
+  if (!user || user.password !== req.body.password) {  //!BUG Plaintext password comparison — store and compare bcrypt/argon2 hashes
+    return res.status(401).json({ error: "User not found or wrong password" });
+  }
+  const token = jwt.sign({ id: user.id, role: user.role }, "secret123");  //!BUG Hard-coded JWT secret committed to the repo
+  res.cookie("token", token);  //!BUG Cookie missing httpOnly / secure / sameSite flags
+  res.json({ token, user });  //!BUG Returns the full user document including the password field
+});
'''

PR_UPLOAD = '''--- a/app/routers/files.py
+++ b/app/routers/files.py
+@router.post("/upload")
+async def upload(file: UploadFile):
+    data = await file.read()  #!BUG Reads the entire upload into memory with no size limit (easy DoS)
+    path = f"/srv/uploads/{file.filename}"  #!BUG Path traversal: filename like ../../etc/cron.d/x escapes the folder
+    with open(path, "wb") as f:
+        f.write(data)
+    return {"url": f"/static/{file.filename}"}  #!BUG No content-type check: users can upload .html/.svg served from your origin (stored XSS)
'''

PR_MIGRATION = '''--- /dev/null
+++ b/migrations/0042_orders_status.sql
+ALTER TABLE orders ADD COLUMN status TEXT NOT NULL;  --!BUG Fails on a non-empty table (no DEFAULT) and rewrites a 40M-row table under lock
+UPDATE orders SET status = 'paid' WHERE paid_at IS NOT NULL;  --!BUG One giant UPDATE locks/bloats the table — backfill in batches
+CREATE INDEX idx_orders_status ON orders(status);  --!BUG Blocks writes for the whole build — use CREATE INDEX CONCURRENTLY
+ALTER TABLE orders DROP COLUMN paid_at;  --!BUG Old app version still reads paid_at → errors during rolling deploy (expand/contract)
'''

AI_EMAIL = '''import re

# Validates any RFC-compliant email address.
EMAIL = re.compile(r"[a-z]+@[a-z]+\\.com")  #!BUG Unanchored, lowercase-only, rejects digits/dots/+tags, and only allows .com


def is_valid_email(s: str) -> bool:
    return bool(EMAIL.search(s))  #!BUG search() matches a substring: "junk x@y.com junk" passes — use fullmatch
'''

AI_GATHER = '''import asyncio

import httpx


async def fetch_all(urls: list[str]) -> list[str]:
    """Fetch all URLs concurrently with bounded concurrency (max 10 at a time)."""
    results = []
    async with httpx.AsyncClient() as client:
        for url in urls:
            r = await client.get(url)  #!BUG Awaited one at a time — fully sequential, not concurrent (and no concurrency bound exists)
            results.append(r.text)
    return results
'''

AI_JS_SORT = '''// Returns the three highest scores, highest first.
function topThree(scores) {
  return scores.sort().reverse().slice(0, 3);  //!BUG Default sort is lexicographic ([100, 9, 25] → "100" < "25" < "9") and sort() mutates the caller's array
}
'''

EXERCISES_C = [
    # ------------------------------------------------------------------ 1. Code Comprehension
    {
        "id": "comp-ttl-cache", "section": "comprehension", "title": "TTL cache used by the pricing service",
        "difficulty": "Medium", "minutes": 15, "summary": "A small cache with concurrency and expiry bugs.",
        "context": "This cache sits in front of a slow pricing API. Users sometimes see stale prices and p99 spikes every few minutes.",
        "files": [("ttl_cache.py", "python", TTL_CACHE)],
        "tasks": [
            {"id": "explain", "kind": "text", "prompt": "Explain what get() and set() are supposed to do.",
             "rubric": [("Stores value with an expiry timestamp", r"expir|timestamp|ttl"),
                        ("get returns None on miss / expired", r"miss|none|expired"),
                        ("Lock for thread safety", r"lock|thread")],
             "explanation": "set stores (value, now+ttl) under a lock; get should return the value only if it hasn't expired, otherwise treat it as a miss."},
            {"id": "bugs", "kind": "lines", "prompt": "Flag the bugs (4).",
             "explanation": "Unlocked read, expired entries returned, off-by-one capacity, clear-all eviction."},
            {"id": "symptom", "kind": "choice", "prompt": "Which bug explains the periodic p99 spikes?",
             "options": ["The unlocked read", "Clearing the whole cache when it's full", "Using time.time()", "The default max_items"],
             "answer": 1, "explanation": "Clearing everything makes every following request a miss at once → a burst of slow upstream calls."},
            {"id": "improve", "kind": "text", "prompt": "How would you redesign eviction?",
             "rubric": [("LRU (OrderedDict / move_to_end)", r"lru|ordereddict|move_to_end|least recently"),
                        ("Evict expired entries lazily or periodically", r"lazy|periodic|sweep|on read"),
                        ("Or use a library (cachetools)", r"cachetools|library|redis")],
             "explanation": "Use an OrderedDict LRU (evict one oldest item), drop expired entries on read, or use cachetools.TTLCache."},
        ],
    },
    {
        "id": "comp-pagination", "section": "comprehension", "title": "Infinite-scroll pagination helper",
        "difficulty": "Easy", "minutes": 10, "summary": "Three bugs in twelve lines of Node.js.",
        "context": "Users report the first 20 orders never show up and the 'Load more' button never disappears.",
        "files": [("orders.js", "javascript", PAGINATE_JS)],
        "tasks": [
            {"id": "bugs", "kind": "lines", "prompt": "Flag the faulty lines (3).",
             "explanation": "Offset off by one page, SQL injection + unbounded page size, wrong hasMore check."},
            {"id": "cursor", "kind": "text", "prompt": "Why is cursor (keyset) pagination better than OFFSET for this feed?",
             "rubric": [("OFFSET scans and discards rows — slow for deep pages", r"scan|skip|discard|slow|deep"),
                        ("New inserts shift pages → duplicates/missed items", r"duplicate|shift|miss|insert"),
                        ("WHERE created_at < :cursor with an index", r"created_at ?<|cursor|keyset|where")],
             "explanation": "Keyset pagination (WHERE created_at < :last ORDER BY created_at DESC LIMIT n) uses the index, is O(page) and stable when new rows arrive."},
        ],
    },
    {
        "id": "comp-retry", "section": "comprehension", "title": "HTTP retry helper",
        "difficulty": "Medium", "minutes": 12, "summary": "Retries that make outages worse.",
        "context": "During a partner outage our workers piled up and never recovered. This helper is used everywhere.",
        "files": [("http_utils.py", "python", RETRY)],
        "tasks": [
            {"id": "bugs", "kind": "lines", "prompt": "Flag the problems (4).",
             "explanation": "No timeout, retrying non-retryable errors, no jitter, swallowing the final failure."},
            {"id": "fix", "kind": "text", "prompt": "Describe a production-grade retry policy.",
             "rubric": [("Timeouts on every call", r"timeout"),
                        ("Retry only transient errors (5xx, 429, connection)", r"5xx|429|transient|connection|idempot"),
                        ("Exponential backoff with jitter + cap", r"jitter|random"),
                        ("Raise after final attempt / circuit breaker", r"raise|circuit|breaker|propagat")],
             "explanation": "Set connect/read timeouts, retry only idempotent requests on 5xx/429/connection errors, exponential backoff with full jitter and a cap, then raise; add a circuit breaker."},
        ],
    },
    # ------------------------------------------------------------------ 2. AI-Assisted Coding
    {
        "id": "ai-kth-largest", "section": "ai_assist", "title": "Kth Largest Element — check the AI's heap",
        "difficulty": "Easy", "minutes": 10, "summary": "The AI used a min-heap of size k. Can you defend it?",
        "context": "AI: \"Keep a min-heap of the k largest elements seen so far; its root is the answer.\"",
        "files": [("ai_answer.py", "python", AI_KTH)],
        "tasks": [
            {"id": "correct", "kind": "text", "prompt": "Why is the heap root the k-th largest?",
             "rubric": [("Heap holds the k largest seen so far", r"k largest|largest k|top k"),
                        ("Popping removes the smallest of them", r"pop|smallest|min"),
                        ("Root = smallest of the top k = k-th largest", r"root|heap\[0\]|smallest of")],
             "explanation": "Invariant: the heap contains the k largest elements so far; the min-heap root is the smallest of those, i.e. the k-th largest."},
            {"id": "edges", "kind": "text", "prompt": "Which inputs break it or need a decision?",
             "rubric": [("k > len(nums) or k <= 0", r"k ?>|k ?<=|k is larger|invalid k|out of range"),
                        ("Empty list", r"empty"),
                        ("Duplicates count separately", r"duplicate")],
             "explanation": "k larger than n (or ≤ 0) and empty input raise IndexError; duplicates are counted individually (that's what LeetCode expects)."},
            {"id": "alt", "kind": "choice", "prompt": "Which alternative has O(n) average time?",
             "options": ["Sort and index", "Quickselect", "Max-heap of all n then pop k times", "Binary search tree"],
             "answer": 1, "explanation": "Quickselect partitions like quicksort but recurses into one side: O(n) average, O(n²) worst case."},
        ],
    },
    {
        "id": "ai-anagrams", "section": "ai_assist", "title": "Group Anagrams — complexity check",
        "difficulty": "Easy", "minutes": 8, "summary": "Correct code — but is the complexity claim right?",
        "context": "AI: \"This runs in O(n) time.\"",
        "files": [("ai_answer.py", "python", AI_ANAGRAMS)],
        "tasks": [
            {"id": "complexity", "kind": "choice", "prompt": "Actual time complexity for n words of max length k?",
             "options": ["O(n)", "O(n · k log k)", "O(n² · k)", "O(k log k)"], "answer": 1,
             "explanation": "Each word is sorted: O(k log k), done n times."},
            {"id": "faster", "kind": "text", "prompt": "How can you get O(n · k)?",
             "rubric": [("Count letters (26-length tuple) as the key", r"count|26|frequency|tuple"),
                        ("Avoid sorting", r"no sort|without sort|instead of sort|avoid sort")],
             "explanation": "Use a 26-length character count tuple as the key instead of the sorted string (assuming lowercase a–z)."},
        ],
    },
    {
        "id": "ai-debounce", "section": "ai_assist", "title": "Debounce — explain the closure",
        "difficulty": "Medium", "minutes": 10, "summary": "Frontend interview classic, written by AI.",
        "context": "AI: \"Classic debounce using a closure.\" It is correct — your job is to prove you understand it.",
        "files": [("debounce.js", "javascript", AI_DEBOUNCE)],
        "tasks": [
            {"id": "how", "kind": "text", "prompt": "Explain how it works and why `timer` survives between calls.",
             "rubric": [("Closure keeps timer between calls", r"closure|enclos|scope"),
                        ("Each call clears the previous timer", r"clear"),
                        ("fn runs after wait ms of silence", r"after|silence|quiet|last call")],
             "explanation": "The returned function closes over `timer`; each call cancels the pending timeout and starts a new one, so fn only runs after `wait` ms with no calls."},
            {"id": "this", "kind": "choice", "prompt": "Why use a regular function and fn.apply(this, args)?",
             "options": ["Performance", "To keep the caller's `this` (e.g. when used as an object method / event handler)", "It's required by setTimeout", "No reason"],
             "answer": 1, "explanation": "An arrow inside a normal function captures the caller's `this`; apply forwards it and the arguments."},
            {"id": "extend", "kind": "text", "prompt": "What features would a production debounce add?",
             "rubric": [("cancel() / flush()", r"cancel|flush"),
                        ("leading / trailing options", r"leading|trailing|immediate"),
                        ("maxWait", r"maxwait|max wait")],
             "explanation": "cancel/flush methods, leading/trailing edge options and maxWait (like lodash.debounce)."},
        ],
    },
    # ------------------------------------------------------------------ 3. Debugging Simulator
    {
        "id": "dbg-timezone", "section": "debugging", "title": "Daily sales report is off",
        "difficulty": "Medium", "minutes": 12, "summary": "Finance says yesterday's totals don't match the payment provider.",
        "context": "Incident: The daily report for 1 March is missing orders placed between 00:00 and 05:30 IST and includes some from 2 March.\n"
                   "Database column created_at is TIMESTAMPTZ stored in UTC.",
        "files": [("reports.py", "python", TZ_BUG)],
        "tasks": [
            {"id": "lines", "kind": "lines", "prompt": "Flag the buggy lines (2).",
             "explanation": "Naive datetimes treated as UTC; inclusive 23:59:59 end misses the last second."},
            {"id": "root", "kind": "choice", "prompt": "Root cause of the 5:30 shift?",
             "options": ["DB clock drift", "Naive local-day boundaries compared against UTC timestamps", "Floating point", "Caching"],
             "answer": 1, "explanation": "The IST day must be converted to UTC boundaries (or use AT TIME ZONE)."},
            {"id": "fix", "kind": "text", "prompt": "Write or describe the fix.",
             "rubric": [("Timezone-aware datetimes (ZoneInfo('Asia/Kolkata'))", r"zoneinfo|tz|aware|asia/kolkata|pytz"),
                        ("Half-open range: >= start AND < next day", r">=|half.?open|< ?next|next day"),
                        ("Store/compare in UTC", r"utc")],
             "explanation": "start = datetime(d, tzinfo=ZoneInfo('Asia/Kolkata')); end = start + 1 day; WHERE created_at >= start AND created_at < end."},
        ],
    },
    {
        "id": "dbg-react-interval", "section": "debugging", "title": "Price widget slows the browser down",
        "difficulty": "Easy", "minutes": 8, "summary": "Network tab shows dozens of requests per second after switching stocks.",
        "context": "After switching between symbols a few times the page makes 10+ requests per second and prices flicker between symbols.",
        "files": [("LivePrice.jsx", "javascript", REACT_LEAK)],
        "tasks": [
            {"id": "lines", "kind": "lines", "prompt": "Flag the buggy line.", "explanation": "The effect never clears its interval."},
            {"id": "flicker", "kind": "choice", "prompt": "Why do prices flicker between symbols?",
             "options": ["Server bug", "Old intervals for previous symbols keep calling setPrice", "CSS animation", "React batching"],
             "answer": 1, "explanation": "Each leaked interval still updates the same state with its own symbol's price."},
            {"id": "fix", "kind": "text", "prompt": "Show the fix.",
             "rubric": [("return () => clearInterval(id)", r"clearinterval|cleanup|return \(\)"),
                        ("Ignore stale responses (AbortController / flag)", r"abort|stale|ignore|cancel")],
             "explanation": "Return () => clearInterval(id) from the effect and abort/ignore in-flight fetches for the old symbol."},
        ],
    },
    {
        "id": "dbg-deadlock", "section": "debugging", "title": "Transfers fail with 'deadlock detected'",
        "difficulty": "Hard", "minutes": 12, "summary": "Two concurrent transfers in opposite directions.",
        "context": "Postgres log: ERROR: deadlock detected — Process 4121 waits for ShareLock on transaction 991; blocked by process 4122.",
        "files": [("transfer.sql", "sql", DEADLOCK_SQL)],
        "tasks": [
            {"id": "lines", "kind": "lines", "prompt": "Flag the line that causes the deadlock.",
             "explanation": "Rows are locked in request order, so opposite transfers lock in opposite orders."},
            {"id": "order", "kind": "order", "prompt": "Order the events that lead to the deadlock.",
             "items": ["A locks account 1", "B locks account 2", "A waits for account 2", "B waits for account 1",
                       "Postgres detects the cycle and aborts one transaction"],
             "explanation": "Classic circular wait."},
            {"id": "fix", "kind": "text", "prompt": "How do you fix it?",
             "rubric": [("Lock rows in a consistent order (lower id first)", r"order|lower id|sort|consistent"),
                        ("SELECT ... FOR UPDATE both rows first", r"for update"),
                        ("Retry on deadlock / serialization failure", r"retry")],
             "explanation": "Always lock accounts in ascending id order (SELECT ... WHERE id IN (a,b) ORDER BY id FOR UPDATE), then update; retry on deadlock errors."},
        ],
    },
    # ------------------------------------------------------------------ 4. Production Code Reading
    {
        "id": "repo-express", "section": "repos", "title": "Express: Todo API",
        "difficulty": "Medium", "minutes": 15, "summary": "Navigate routes, middleware and error handling.",
        "context": "New-joiner task: understand this service and answer the team lead's questions.",
        "files": EXPRESS_REPO,
        "tasks": [
            {"id": "flow", "kind": "order", "prompt": "Order what happens for PATCH /api/todos/7.",
             "items": ["express.json() parses the body", "requireUser verifies the JWT", "todos router matches PATCH /:id",
                       "db.todos.update runs", "Response JSON is sent (or error middleware returns 500)"],
             "explanation": "Middleware runs in registration order, then the router, then errors flow to the error handler."},
            {"id": "security", "kind": "choice", "prompt": "What is the most serious bug in routes/todos.js?",
             "options": ["take: 50", "PATCH updates any user's todo and accepts any field from req.body (IDOR + mass assignment)",
                         "Using async handlers", "Number(req.params.id)"],
             "answer": 1, "explanation": "The update filters only by id — no userId check — and passes req.body straight through (could change userId)."},
            {"id": "fix", "kind": "text", "prompt": "How would you fix PATCH?",
             "rubric": [("Filter by id AND userId", r"userid|owner|req\.user"),
                        ("Allow-list fields (title, done)", r"allow|whitelist|pick|only|schema|zod|validate"),
                        ("404 when not found / not owned", r"404|not found")],
             "explanation": "updateMany({ where: { id, userId: req.user.id }, data: pick(body, ['title','done']) }) with validation; return 404 if nothing matched."},
        ],
    },
    {
        "id": "repo-backup-cli", "section": "repos", "title": "Python: backup CLI",
        "difficulty": "Easy", "minutes": 12, "summary": "Trace a small CLI across three modules.",
        "context": "The backup CLI sometimes re-uploads everything. Read the code to understand why.",
        "files": CLI_REPO,
        "tasks": [
            {"id": "entry", "kind": "choice", "prompt": "Where does a run start and what decides whether a file is uploaded?",
             "options": ["state.py compares file sizes", "cli.py → run_backup, which compares each file's mtime with the manifest",
                         "storage.upload checks a hash", "Every file is always uploaded"],
             "answer": 1, "explanation": "main() parses args and calls run_backup, which skips files whose mtime matches the manifest."},
            {"id": "reupload", "kind": "text", "prompt": "Why might it re-upload everything sometimes?",
             "rubric": [("Manifest is only saved at the end — a crash loses progress", r"crash|end|interrupt|fail.*save|only saved"),
                        ("Missing manifest → empty dict", r"missing|filenotfound|empty"),
                        ("mtime changes (copy/checkout) without content change", r"mtime|touch|checkout|copy|hash")],
             "explanation": "If a run crashes, the manifest is never written; a missing manifest means {}; and mtime changes without content change trigger uploads — use content hashes and save progress periodically."},
        ],
    },
    # ------------------------------------------------------------------ 5. Interview Simulation
    {
        "id": "int-hit-counter", "section": "interview", "title": "Design round: hit counter",
        "difficulty": "Medium", "minutes": 25, "timed": True,
        "summary": "Classic follow-up question on existing code.",
        "context": "Interviewer: \"Here's a hit counter a junior wrote. It works but production is unhappy. Improve it.\"",
        "files": [("hit_counter.py", "python", HIT_COUNTER)],
        "tasks": [
            {"id": "bugs", "kind": "lines", "prompt": "Flag the issues (2).",
             "explanation": "Unbounded list scanned every call, and a 301-second window."},
            {"id": "optimize", "kind": "text", "prompt": "Make get_hits O(1) and memory bounded.",
             "rubric": [("Deque, pop old entries from the left", r"deque|popleft|pop old"),
                        ("Or 300 circular buckets of (timestamp, count)", r"bucket|circular|ring|% ?300|mod"),
                        ("Bounded memory", r"bounded|constant|o\(1\)|fixed")],
             "explanation": "Use 300 buckets indexed by ts % 300 storing (ts, count) — O(1) time and memory — or a deque that drops entries older than 300 s."},
            {"id": "scale", "kind": "text", "prompt": "Now hits come from 50 servers. What changes?",
             "rubric": [("Shared store (Redis INCR per second bucket with TTL)", r"redis|incr|shared|central"),
                        ("Aggregate per-server counts", r"aggregat|sum|merge"),
                        ("Accept approximate / eventual counts", r"approx|eventual")],
             "explanation": "Each server increments a per-second Redis key (with TTL); reads sum the last 300 keys — or aggregate local counts periodically and accept slight lag."},
        ],
    },
    {
        "id": "int-merge-feeds", "section": "interview", "title": "Coding round: merge K feeds",
        "difficulty": "Medium", "minutes": 25, "timed": True,
        "summary": "Fix and optimise a K-way merge.",
        "context": "Interviewer: \"Each follower feed is already sorted newest first. We only need the top `limit`. What's wrong here?\"",
        "files": [("feeds.py", "python", MERGE_FEEDS)],
        "tasks": [
            {"id": "bugs", "kind": "lines", "prompt": "Flag the problems (2).",
             "explanation": "Copies everything, and sorts in the wrong direction."},
            {"id": "optimize", "kind": "text", "prompt": "Give the optimal approach and its complexity.",
             "rubric": [("Heap of the head of each feed (heapq / merge)", r"heap|heapq|priority"),
                        ("Pop limit times, push next from same feed", r"pop|next|push"),
                        ("O(limit · log k)", r"log ?k|limit ?\*|l log k")],
             "explanation": "Push each feed's first post into a max-heap keyed by ts; pop `limit` times, pushing the next post from the same feed: O(k + limit·log k)."},
        ],
    },
    {
        "id": "int-scheduler", "section": "interview", "title": "Debug round: job scheduler",
        "difficulty": "Hard", "minutes": 25, "timed": True,
        "summary": "Jobs are randomly skipped and one failure stops everything.",
        "context": "Interviewer: \"Some jobs never run and one bad job takes down the rest. Find out why and redesign it.\"",
        "files": [("scheduler.py", "python", SCHEDULER)],
        "tasks": [
            {"id": "bugs", "kind": "lines", "prompt": "Flag the bugs (3).",
             "explanation": "Mutating the list during iteration, no error isolation, O(n) removals."},
            {"id": "design", "kind": "text", "prompt": "Redesign it.",
             "rubric": [("Min-heap ordered by run_at", r"heap|priority"),
                        ("try/except per job + logging", r"try|except|isolat|log"),
                        ("Thread safety / worker pool", r"lock|thread|pool|worker"),
                        ("Persistence / retries for durability", r"persist|durab|retry|database|queue")],
             "explanation": "Use a heap keyed by run_at, pop while due, run each job in try/except (or a worker pool), protect with a lock, and persist jobs if they must survive restarts."},
        ],
    },
    # ------------------------------------------------------------------ 6. Prompt Engineering
    {
        "id": "prompt-refactor", "section": "prompts", "title": "Write a safe refactoring prompt",
        "difficulty": "Medium", "minutes": 10, "summary": "Refactor legacy code without changing behaviour.",
        "context": "Weak prompt: \"clean up this code\".\nYou have a 400-line Python function `process_order()` with no tests that handles payments and emails.",
        "tasks": [
            {"id": "risk", "kind": "choice", "prompt": "What is the biggest risk of the weak prompt?",
             "options": ["It's too short to read", "The AI may silently change behaviour in untested payment logic",
                         "AI can't read Python", "It will be too slow"],
             "answer": 1, "explanation": "Without constraints the model optimises for 'clean', not 'equivalent'."},
            {"id": "prompt", "kind": "prompt", "prompt": "Write a strong refactoring prompt.",
             "rubric": [("Preserve behaviour exactly / no functional change", r"behaviou?r|no functional|same output|equivalent|preserve"),
                        ("Ask for characterization tests first", r"test"),
                        ("Small incremental steps", r"step|increment|small"),
                        ("Explain each change / list risks", r"explain|risk|why"),
                        ("Constraints: language version, style, keep public API", r"version|api|signature|style|pep")],
             "explanation": "Ask for characterization tests first, then small behaviour-preserving steps that keep the public signature, explaining each change and flagging risky spots."},
        ],
    },
    {
        "id": "prompt-review", "section": "prompts", "title": "Write a code-review prompt",
        "difficulty": "Easy", "minutes": 8, "summary": "Get a focused, prioritised review instead of nitpicks.",
        "context": "Weak prompt: \"review my PR\". The PR adds a password-reset endpoint to a FastAPI app.",
        "tasks": [
            {"id": "prompt", "kind": "prompt", "prompt": "Write a strong review prompt.",
             "rubric": [("Context: framework and what the PR does", r"fastapi|password.?reset|endpoint|pr"),
                        ("Focus areas: security, correctness, edge cases", r"security|correct|edge"),
                        ("Prioritise by severity", r"severity|priorit|critical|blocking"),
                        ("Reference lines / suggest concrete fixes", r"line|suggest|fix|diff"),
                        ("Skip pure style nitpicks", r"nit|style|ignore formatting")],
             "explanation": "Give context, ask for security/correctness/edge-case issues (token expiry, enumeration, rate limiting) ranked by severity with line references and concrete fixes; skip formatting nits."},
        ],
    },
    {
        "id": "prompt-sql", "section": "prompts", "title": "Write a text-to-SQL prompt",
        "difficulty": "Medium", "minutes": 10, "summary": "Get SQL that runs on your actual schema.",
        "context": "Weak prompt: \"sql for top customers\". Your DB is PostgreSQL with tables customers(id, name, country) and orders(id, customer_id, total, created_at).",
        "tasks": [
            {"id": "prompt", "kind": "prompt", "prompt": "Write a strong text-to-SQL prompt.",
             "rubric": [("Dialect", r"postgres|dialect"),
                        ("Schema with table/column names", r"customers|orders|schema|column"),
                        ("Precise definition of 'top' (metric, period, limit)", r"revenue|sum|total|last|period|limit|top \d+"),
                        ("Ties / NULL handling", r"tie|null"),
                        ("Output only SQL / explain briefly", r"only sql|explain|comment|format")],
             "explanation": "Name the dialect, paste the schema, define 'top' precisely (e.g. top 10 by SUM(total) in the last 90 days), say how to handle ties/NULLs and ask for SQL plus a one-line explanation."},
        ],
    },
    # ------------------------------------------------------------------ 7. System Thinking
    {
        "id": "sys-notifications", "section": "system", "title": "Notification fan-out",
        "difficulty": "Medium", "minutes": 20, "summary": "Push, email and SMS for 10M users.",
        "context": """Current design:

  [Order svc] --HTTP--> [Notification svc] --sync--> [Email provider] + [SMS provider] + [Push (FCM/APNs)]

During a sale, order latency jumps from 200ms to 6s and some customers get the same SMS three times.""",
        "tasks": [
            {"id": "root", "kind": "choice", "prompt": "Why does order latency jump?",
             "options": ["Database indexes", "Orders wait synchronously for slow third-party providers", "CDN", "Too many pods"],
             "answer": 1, "explanation": "The order request blocks on the notification chain and its external providers."},
            {"id": "dupes", "kind": "choice", "prompt": "Most likely reason for duplicate SMS?",
             "options": ["Users clicked twice", "Retries after timeouts without idempotency keys", "SMS provider bug", "DNS"],
             "answer": 1, "explanation": "The request timed out, was retried, but the first attempt had already succeeded."},
            {"id": "design", "kind": "text", "prompt": "Redesign it.",
             "rubric": [("Publish an event / queue and return immediately", r"queue|event|kafka|async|publish"),
                        ("Per-channel workers with rate limits", r"worker|channel|rate"),
                        ("Idempotency key per notification", r"idempot|dedup"),
                        ("User preferences / retries with DLQ", r"preference|dlq|dead|retry")],
             "explanation": "Order svc publishes OrderPlaced; per-channel workers consume it, respect provider rate limits and user preferences, dedupe with an idempotency key, retry with backoff and a DLQ."},
        ],
    },
    {
        "id": "sys-autocomplete", "section": "system", "title": "Search autocomplete",
        "difficulty": "Medium", "minutes": 20, "summary": "Suggestions within 50 ms for every keystroke.",
        "context": "Product wants top-10 suggestions as users type. Today each keystroke runs SELECT ... WHERE query LIKE 'pre%' ORDER BY count DESC on a 200M-row table (p95 900ms).",
        "tasks": [
            {"id": "flow", "kind": "order", "prompt": "Order a good request path.",
             "items": ["Client debounces keystrokes", "Request hits the CDN/edge cache for popular prefixes",
                       "Autocomplete service looks up the prefix in an in-memory trie / top-k map", "Top-10 suggestions are returned",
                       "Search logs feed an offline job that rebuilds the top-k data"],
             "explanation": "Cut requests at the client, cache at the edge, serve from precomputed memory, rebuild offline."},
            {"id": "ds", "kind": "choice", "prompt": "Best serving data structure?",
             "options": ["SQL LIKE with an index", "Trie with precomputed top-k per node (or prefix → top-k map)", "Linked list", "Bloom filter"],
             "answer": 1, "explanation": "Precomputing top-k per prefix makes lookups O(prefix length)."},
            {"id": "tradeoffs", "kind": "text", "prompt": "Discuss freshness and scale trade-offs.",
             "rubric": [("Offline rebuild (hourly/daily) vs real-time trends", r"offline|batch|rebuild|hour|daily|real.?time|trend"),
                        ("Shard by prefix / replicate for reads", r"shard|replica|partition"),
                        ("Filter offensive / personalise", r"filter|offensive|personal")],
             "explanation": "Rebuild top-k offline and blend in a small real-time trending layer; shard by prefix and replicate; filter bad terms and optionally personalise."},
        ],
    },
    {
        "id": "sys-ride-matching", "section": "system", "title": "Ride matching hot spots",
        "difficulty": "Hard", "minutes": 25, "summary": "Driver location updates overwhelm one database shard.",
        "context": "4M drivers send GPS every 4 s (1M writes/s). Locations are stored in Postgres sharded by city. The Mumbai shard is at 100% CPU every evening.",
        "tasks": [
            {"id": "root", "kind": "choice", "prompt": "What is the core problem?",
             "options": ["Too few indexes", "Hot shard: city-level sharding puts all Mumbai traffic on one node, and ephemeral GPS points don't belong in a durable OLTP store",
                         "GPS precision", "Client bugs"], "answer": 1,
             "explanation": "Skewed shard key plus the wrong storage for high-churn ephemeral data."},
            {"id": "design", "kind": "text", "prompt": "Propose a better design.",
             "rubric": [("In-memory geo index (Redis GEO / H3 / geohash cells)", r"redis|geo|h3|geohash|s2|in.?memory"),
                        ("Shard by fine-grained cell, not city", r"cell|finer|grid|shard"),
                        ("TTL for stale locations; persist history asynchronously", r"ttl|expire|async|stream|kafka"),
                        ("Search nearby cells for matching", r"nearby|neighbo|ring|radius")],
             "explanation": "Keep live locations in an in-memory geo index partitioned by H3/geohash cell with TTLs, query neighbouring cells to match, and stream history to cheap storage asynchronously."},
        ],
    },
    # ------------------------------------------------------------------ 8. Code Review Training
    {
        "id": "rev-node-login", "section": "review", "title": "PR #301: login endpoint",
        "difficulty": "Easy", "minutes": 10, "summary": "Four security issues in nine lines.",
        "context": "Author: \"Login done! Returns the token and user so the frontend has everything.\"",
        "files": [("PR-301.diff", "diff", PR_NODE_AUTH)],
        "tasks": [
            {"id": "lines", "kind": "lines", "prompt": "Comment on every problematic line (4).",
             "explanation": "Plaintext passwords, hard-coded secret, insecure cookie, leaking the password field."},
            {"id": "decision", "kind": "choice", "prompt": "Your review decision?",
             "options": ["Approve", "Approve with nits", "Request changes"], "answer": 2,
             "explanation": "Credential handling issues are blocking."},
            {"id": "extra", "kind": "text", "prompt": "What else should a login endpoint have?",
             "rubric": [("Rate limiting / lockout", r"rate|lockout|brute|throttl"),
                        ("Generic error message (no user enumeration)", r"generic|enumerat|same message"),
                        ("Short-lived token + refresh / expiry", r"expir|refresh|short"),
                        ("Audit logging / MFA", r"log|audit|mfa|2fa")],
             "explanation": "Rate limiting, a generic error message, expiring tokens with refresh, and audit logging (MFA optional)."},
        ],
    },
    {
        "id": "rev-upload", "section": "review", "title": "PR #145: file upload",
        "difficulty": "Medium", "minutes": 10, "summary": "A simple upload endpoint with three exploits.",
        "context": "Author: \"Users can now upload profile pictures.\"",
        "files": [("PR-145.diff", "diff", PR_UPLOAD)],
        "tasks": [
            {"id": "lines", "kind": "lines", "prompt": "Comment on the problematic lines (3).",
             "explanation": "Unbounded read, path traversal, no content-type restriction."},
            {"id": "better", "kind": "text", "prompt": "Describe a safe implementation.",
             "rubric": [("Size limit / stream in chunks", r"size|limit|chunk|stream"),
                        ("Generate own filename (uuid), never trust user filename", r"uuid|random|generat|own name|sanitiz"),
                        ("Allow-list types and verify content (magic bytes / re-encode)", r"allow|whitelist|magic|mime|re.?encode|pillow"),
                        ("Store in object storage / separate domain", r"s3|blob|object storage|separate domain|cdn")],
             "explanation": "Enforce a size limit while streaming, store under a generated UUID name, allow-list image types and re-encode with Pillow, and serve from object storage on a separate domain."},
        ],
    },
    {
        "id": "rev-migration", "section": "review", "title": "PR #512: orders status migration",
        "difficulty": "Hard", "minutes": 12, "summary": "A migration that would take production down.",
        "context": "Author: \"Replaces paid_at with a status column. Ran fine on my laptop.\" orders has 40M rows; deploys are rolling.",
        "files": [("PR-512.diff", "diff", PR_MIGRATION)],
        "tasks": [
            {"id": "lines", "kind": "lines", "prompt": "Comment on the dangerous lines (4).",
             "explanation": "NOT NULL without default, giant UPDATE, blocking index build, dropping a column still in use."},
            {"id": "plan", "kind": "order", "prompt": "Order a zero-downtime rollout.",
             "items": ["Add nullable status column", "Deploy code that writes both paid_at and status",
                       "Backfill status in batches", "Create the index CONCURRENTLY and add the NOT NULL constraint",
                       "Deploy code that reads only status", "Drop paid_at in a later release"],
             "explanation": "Expand → migrate → contract, so every running app version stays compatible."},
        ],
    },
    # ------------------------------------------------------------------ 9. AI Verification
    {
        "id": "ver-email-regex", "section": "verify", "title": "AI email validator",
        "difficulty": "Easy", "minutes": 6, "summary": "\"RFC-compliant\" in one regex? Check it.",
        "context": "AI: \"This validates any RFC-compliant email address.\"",
        "files": [("ai_answer.py", "python", AI_EMAIL)],
        "tasks": [
            {"id": "verdict", "kind": "choice", "prompt": "Verdict?", "options": ["Correct", "Contains bugs"], "answer": 1,
             "explanation": "It rejects most valid emails and accepts strings with junk around an email."},
            {"id": "lines", "kind": "lines", "prompt": "Flag the faulty lines (2).",
             "explanation": "Overly narrow, unanchored pattern; search() instead of fullmatch()."},
            {"id": "approach", "kind": "text", "prompt": "What would you do instead?",
             "rubric": [("Use a well-tested library (email-validator / pydantic EmailStr)", r"library|email.?validator|emailstr|pydantic"),
                        ("Loose syntax check + fullmatch", r"fullmatch|anchor|\^|loose|simple"),
                        ("Confirm by sending a verification email", r"verif|confirm|send")],
             "explanation": "Use a maintained validator (pydantic EmailStr / email-validator) for syntax and confirm ownership with a verification email."},
        ],
    },
    {
        "id": "ver-async-gather", "section": "verify", "title": "AI 'concurrent' fetcher",
        "difficulty": "Medium", "minutes": 8, "summary": "The docstring promises concurrency. Does the code deliver?",
        "context": "AI: \"Fetches all URLs concurrently with at most 10 in flight.\"",
        "files": [("ai_answer.py", "python", AI_GATHER)],
        "tasks": [
            {"id": "verdict", "kind": "choice", "prompt": "Verdict?", "options": ["Correct", "Doesn't match its claims"], "answer": 1,
             "explanation": "It awaits each request in turn — sequential, with no concurrency limit at all."},
            {"id": "lines", "kind": "lines", "prompt": "Flag the faulty line.", "explanation": "await inside the loop serialises requests."},
            {"id": "fix", "kind": "text", "prompt": "Write the correct version.",
             "rubric": [("asyncio.gather / TaskGroup", r"gather|taskgroup|create_task"),
                        ("asyncio.Semaphore(10)", r"semaphore"),
                        ("Timeouts / error handling", r"timeout|return_exceptions|except")],
             "explanation": "sem = asyncio.Semaphore(10); async def one(u): async with sem: return (await client.get(u, timeout=10)).text; return await asyncio.gather(*(one(u) for u in urls))."},
        ],
    },
    {
        "id": "ver-js-sort", "section": "verify", "title": "AI top-three scores",
        "difficulty": "Easy", "minutes": 5, "summary": "A JavaScript classic that AI gets wrong all the time.",
        "context": "AI: \"Sort, reverse and slice — simple and correct.\"",
        "files": [("ai_answer.js", "javascript", AI_JS_SORT)],
        "tasks": [
            {"id": "output", "kind": "choice", "prompt": "What does topThree([100, 9, 25, 3]) return?",
             "options": ["[100, 25, 9]", "[9, 3, 25]", "[3, 25, 100]", "[100, 9, 25]"], "answer": 1,
             "explanation": "Default sort compares strings: ['100','25','3','9'] → reversed ['9','3','25','100'] → [9, 3, 25]."},
            {"id": "lines", "kind": "lines", "prompt": "Flag the faulty line.", "explanation": "Lexicographic, mutating sort."},
            {"id": "fix", "kind": "text", "prompt": "Write the fix.",
             "rubric": [("Numeric comparator (b - a)", r"b ?- ?a|comparator|\(a, ?b\)"),
                        ("Copy first ([...scores] / toSorted / slice())", r"\[\.\.\.|tosorted|slice\(\)|copy")],
             "explanation": "return [...scores].sort((a, b) => b - a).slice(0, 3); (or scores.toSorted((a, b) => b - a))."},
        ],
    },
]

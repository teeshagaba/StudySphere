"""AI-Era interview content, part B: interview simulation, prompt engineering, system thinking, code review,
AI verification. See ai_era_a for the `!BUG` marker convention."""

LOG_ANALYZER = '''import re
from collections import Counter, defaultdict

LINE = r'(?P<ip>\\S+) \\[(?P<ts>[^\\]]+)\\] "(?P<method>\\w+) (?P<path>\\S+)" (?P<status>\\d{3}) (?P<ms>\\d+)'


class LogAnalyzer:
    def __init__(self):
        self.latencies = defaultdict(list)
        self.hits = Counter()
        self.errors = 0
        self.lines = 0

    def ingest(self, raw_lines):
        for raw in raw_lines:
            m = re.match(LINE, raw)  #!BUG Recompiles/looks up the pattern for every line; precompile with re.compile once
            if not m:
                continue
            self.lines += 1
            path = m["path"].split("?")[0]
            self.hits[path] += 1
            self.latencies[path].append(int(m["ms"]))
            if m["status"].startswith("5"):
                self.errors += 1

    def top_endpoints(self, n=5):
        return sorted(self.hits.items(), key=lambda kv: kv[1], reverse=True)[:n]  #!BUG Full sort each call; Counter.most_common(n) uses a heap: O(m log n)

    def p95(self, path):
        values = sorted(self.latencies[path])  #!BUG Sorts the whole list on every call; cache or keep a sorted structure / t-digest
        if not values:
            return None
        index = int(len(values) * 0.95)  #!BUG Nearest-rank off-by-one: should be ceil(0.95 * n) - 1 (for n=20 this returns the max, not p95)
        return values[index]

    def error_rate(self):
        return self.errors / self.lines  #!BUG ZeroDivisionError when nothing was ingested

    def report(self):
        lines = [f"lines={self.lines} error_rate={self.error_rate():.2%}"]
        for path, count in self.top_endpoints():
            lines.append(f"{path:<30} {count:>6} p95={self.p95(path)}ms")
        return "\\n".join(lines)
'''

SHORTENER = '''import hashlib
import time

BASE62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


class Shortener:
    def __init__(self, store):
        self.store = store  # dict-like: code -> {"url": str, "created": float, "clicks": int}
        self.counter = 0

    def _code(self, url: str) -> str:
        digest = hashlib.md5(url.encode()).hexdigest()
        return digest[:6]  #!BUG Truncated hash collides (24 bits); collisions silently overwrite another user's link

    def shorten(self, url: str) -> str:
        if not url.startswith("http"):  #!BUG Weak validation: accepts "httpjavascript:..." style values; parse the URL and allow only http/https schemes
            raise ValueError("invalid url")
        code = self._code(url)
        self.store[code] = {"url": url, "created": time.time(), "clicks": 0}
        self.counter += 1  #!BUG Unsynchronised shared counter — not thread-safe under concurrent requests
        return code

    def resolve(self, code: str) -> str | None:
        entry = self.store.get(code)
        if entry is None:
            return None
        entry["clicks"] += 1
        return entry["url"]

    def stats(self):
        return {"links": len(self.store), "created": self.counter}
'''

PR_SQL = '''--- a/app/routers/users.py
+++ b/app/routers/users.py
@@ -40,6 +40,24 @@ router = APIRouter(prefix="/users")
+@router.get("/search")
+def search_users(q: str, db: Session = Depends(get_db)):  #!BUG No authentication/authorization — anyone can enumerate users
+    rows = db.execute(text(f"SELECT * FROM users WHERE name LIKE '%{q}%'")).all()  #!BUG SQL injection via f-string; use bound parameters
+    result = []
+    for r in rows:
+        result.append(dict(r._mapping))  #!BUG Returns every column including password_hash and email (data leak); use a response schema
+    return result  #!BUG Unbounded result set — no limit/pagination
'''

PR_REACT = '''--- a/src/components/Profile.tsx
+++ b/src/components/Profile.tsx
@@ -1,20 +1,28 @@
+export default function Profile({ userId }: { userId: string }) {
+  const [user, setUser] = useState<User | null>(null);
+  const [posts, setPosts] = useState<Post[]>([]);
+
+  useEffect(() => {
+    fetch(`/api/users/${userId}`).then((r) => r.json()).then(setUser);
+  }, []);  //!BUG Missing userId dependency — stale profile when the prop changes; also no abort on unmount (race)
+
+  fetch(`/api/users/${userId}/posts`).then((r) => r.json()).then(setPosts);  //!BUG Fetch during render → infinite render/request loop
+
+  return (
+    <div>
+      <h1 dangerouslySetInnerHTML={{ __html: user?.bio ?? "" }} />  //!BUG XSS: rendering user-controlled HTML
+      {posts.map((p, i) => <PostCard key={i} post={p} />)}  //!BUG Index as key
+    </div>
+  );
+}
'''

PR_JAVA = '''--- a/src/main/java/com/acme/report/ReportService.java
+++ b/src/main/java/com/acme/report/ReportService.java
@@ -12,6 +12,26 @@ public class ReportService {
+    public List<CustomerSummary> monthlyReport() {
+        List<CustomerSummary> out = new ArrayList<>();
+        for (Customer c : customerRepo.findAll()) {  //!BUG Loads every customer into memory; page or stream
+            List<Order> orders = orderRepo.findByCustomerId(c.getId());  //!BUG N+1 query per customer; aggregate with one GROUP BY query
+            double total = 0;  //!BUG double for currency; use BigDecimal
+            for (Order o : orders) {
+                if (o.getCreatedAt().isAfter(Instant.now().minus(30, ChronoUnit.DAYS))) total += o.getAmount();
+            }
+            if (total > 1000) out.add(new CustomerSummary(c.getName(), total));  //!BUG Magic number — extract a named, configurable threshold
+        }
+        try {
+            mailer.send("finance@acme.com", render(out));
+        } catch (Exception e) {  //!BUG Swallows all exceptions silently — log/rethrow and alert
+        }
+        return out;
+    }
'''

AI_BSEARCH = '''import bisect


def search(nums: list[int], target: int) -> int:
    """Returns the index of target in sorted nums, or -1. O(log n)."""
    if hasattr(bisect, "bisect_search"):
        return bisect.bisect_search(nums, target)  #!BUG Hallucinated API: bisect.bisect_search does not exist
    lo, hi = 0, len(nums) - 1
    while lo < hi:  #!BUG Loop condition skips the last candidate (lo == hi) — target at the final position is missed
        mid = (lo + hi) / 2  #!BUG True division gives a float index → TypeError in Python 3; use //
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
'''

AI_PARENS = '''def is_valid(s: str) -> bool:
    pairs = {")": "(", "]": "[", "}": "{"}
    stack = []
    for ch in s:
        if ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
        else:
            stack.append(ch)
    return not stack
'''

AI_DEDUP = '''def dedupe(items: list) -> list:
    """Removes duplicates while preserving the original order. O(n)."""
    return list(set(items))  #!BUG set() does not preserve insertion order and fails for unhashable items (lists/dicts)
'''

AI_SQL = '''-- Second highest salary. Handles ties and returns NULL when there is no second salary.
SELECT salary AS second_highest
FROM employees
ORDER BY salary DESC  --!BUG Duplicates: with salaries 100,100,90 OFFSET 1 returns 100, not 90 (needs DISTINCT)
LIMIT 1 OFFSET 1;  --!BUG Returns an empty result, not NULL, when there is no second row (wrap in a scalar subquery / MAX)
'''

EXERCISES_B = [
    # ------------------------------------------------------------------ 5. Interview Simulation
    {
        "id": "int-log-analyzer", "section": "interview", "title": "Google-style round: log analyzer",
        "difficulty": "Medium", "minutes": 45, "timed": True,
        "summary": "Existing code instead of a blank editor: explain, debug, optimize, refactor, extend.",
        "context": "Interviewer: \"This class powers our latency dashboard. Walk me through it, then let's improve it.\" "
                   "You have 45 minutes. Think aloud in your answers.",
        "files": [("log_analyzer.py", "python", LOG_ANALYZER)],
        "tasks": [
            {"id": "explain", "kind": "text", "prompt": "Explain what this code does.",
             "rubric": [("Parses access-log lines with a regex", r"regex|pars"),
                        ("Counts hits per path (ignoring query string)", r"count|hits|query"),
                        ("Tracks latencies and computes p95", r"latenc|p95|percentile"),
                        ("Tracks 5xx error rate", r"5xx|error")],
             "explanation": "Parses each log line, normalises the path, counts hits, stores latencies per path, counts 5xx, and reports top endpoints with p95."},
            {"id": "bugs", "kind": "lines", "prompt": "Find the bugs and inefficiencies (5).",
             "explanation": "Pattern not precompiled, full sort for top-N, sort per p95 call, nearest-rank off-by-one, divide by zero."},
            {"id": "optimize", "kind": "text", "prompt": "Optimize p95 for a dashboard that calls it every second on millions of lines.",
             "rubric": [("Avoid re-sorting: cache / incremental structure", r"cache|increment|sorted ?list|bisect|maintain"),
                        ("Streaming estimators: t-digest / HDR histogram / buckets", r"t.?digest|hdr|histogram|bucket|sketch"),
                        ("Trade-off: approximate vs exact, memory", r"approx|memory|exact")],
             "explanation": "Use a fixed-bucket latency histogram or t-digest per path (O(1) update, tiny memory, approximate), or cache sorted values invalidated on ingest."},
            {"id": "refactor", "kind": "text", "prompt": "How would you refactor the design?",
             "rubric": [("Separate parsing from aggregation", r"separat|parser|single responsib"),
                        ("Precompiled pattern / dataclass for entries", r"compile|dataclass|typed"),
                        ("Make it testable / injectable clock or sources", r"test|inject|interface")],
             "explanation": "Split LogParser (pure, testable) from MetricsAggregator, use a compiled regex + typed LogEntry, and keep report formatting separate."},
            {"id": "feature", "kind": "text", "prompt": "Add a per-status-code breakdown per endpoint. Describe or write the change.",
             "rubric": [("Counter keyed by (path, status) or nested", r"\(path, ?status\)|status.*counter|counter.*status|defaultdict\(counter"),
                        ("Update in ingest", r"ingest"),
                        ("Expose in report / API", r"report|return|expose")],
             "explanation": "self.status = defaultdict(Counter); in ingest: self.status[path][m['status']] += 1; add it to report()."},
        ],
    },
    {
        "id": "int-shortener", "section": "interview", "title": "Code comprehension round: URL shortener",
        "difficulty": "Medium", "minutes": 30, "timed": True,
        "summary": "Review a teammate's shortener before it goes live.",
        "context": "Interviewer: \"A teammate wrote this shortener. Would you approve it? What would you change?\"",
        "files": [("shortener.py", "python", SHORTENER)],
        "tasks": [
            {"id": "bugs", "kind": "lines", "prompt": "Flag the problems (3).",
             "explanation": "Hash truncation collisions overwrite links, weak scheme validation, unsynchronised counter."},
            {"id": "optimize", "kind": "text", "prompt": "Redesign code generation to be collision-free and scalable.",
             "rubric": [("Base62-encode a unique id (DB sequence / Snowflake)", r"base62|sequence|snowflake|unique id|auto.?increment"),
                        ("Or detect collisions and retry with a salt", r"collision|retry|check exist"),
                        ("Distributed id ranges per server", r"range|distributed|shard")],
             "explanation": "Base62-encode a unique numeric id (DB sequence or per-node id ranges / Snowflake) — collision-free by construction."},
            {"id": "feature", "kind": "text", "prompt": "Add link expiry. What changes?",
             "rubric": [("Store expires_at", r"expir|ttl"),
                        ("Check on resolve, return 404/410", r"resolve|410|404|gone"),
                        ("Cleanup job or TTL index", r"cleanup|ttl index|cron|background|sweep")],
             "explanation": "Store expires_at, reject expired links in resolve() (410 Gone), purge with a TTL index or background job."},
        ],
    },
    # ------------------------------------------------------------------ 6. Prompt Engineering
    {
        "id": "prompt-debug", "section": "prompts", "title": "Write a debugging prompt",
        "difficulty": "Easy", "minutes": 10, "summary": "Turn 'fix my code' into a prompt that gets a real diagnosis.",
        "context": "Weak prompt: \"my react app is broken pls fix\"\n\nError in the browser console:\n"
                   "TypeError: Cannot read properties of undefined (reading 'map') at TaskList (TaskList.tsx:6)\n\n"
                   "The component receives `tasks` from a fetch in its parent.",
        "tasks": [
            {"id": "compare", "kind": "choice", "prompt": "Which prompt is strongest?",
             "options": ["Fix this error: TypeError map undefined",
                         "You are a senior React engineer. In my React 18 + TypeScript app, TaskList crashes with "
                         "\"TypeError: Cannot read properties of undefined (reading 'map')\" on first render. Code below. "
                         "Explain the root cause, give a minimal fix, and one way to prevent it.",
                         "Rewrite my whole app in Vue so it works",
                         "Why is JavaScript so bad?"],
             "answer": 1, "explanation": "It gives role, stack, exact error, when it happens, the code, and the expected output format."},
            {"id": "prompt", "kind": "prompt", "prompt": "Write your own strong debugging prompt for this bug.",
             "rubric": [("Tech stack / context", r"react|typescript|version|component"),
                        ("Exact error message", r"typeerror|cannot read|undefined"),
                        ("Includes code or says where", r"code|snippet|below|tasklist"),
                        ("When it happens / repro", r"first render|when|steps|reproduce|initial"),
                        ("Asks for root cause, not just a patch", r"root cause|why|explain"),
                        ("Requested output format / constraints", r"format|minimal|diff|steps|bullet|don't rewrite|constraint")],
             "explanation": "Strong: stack + exact error + code + repro + what you tried + ask for root cause, minimal fix, and prevention."},
        ],
    },
    {
        "id": "prompt-optimize", "section": "prompts", "title": "Write an optimization prompt",
        "difficulty": "Medium", "minutes": 10, "summary": "Get actionable query tuning instead of generic advice.",
        "context": "Weak prompt: \"make my sql faster\"\n\nQuery (PostgreSQL 16, orders has 40M rows, p95 2.8s):\n"
                   "SELECT * FROM orders WHERE status = 'shipped' AND created_at > now() - interval '7 days' ORDER BY created_at DESC LIMIT 50;",
        "tasks": [
            {"id": "prompt", "kind": "prompt", "prompt": "Write a strong optimization prompt.",
             "rubric": [("Database + version", r"postgres|mysql|version|16"),
                        ("Data size / current latency", r"40m|rows|latency|2\.8|p95|ms|seconds"),
                        ("Includes the query and EXPLAIN plan", r"explain|plan|query"),
                        ("Existing indexes / schema", r"index|schema"),
                        ("Goal / target", r"target|goal|under|<"),
                        ("Asks for trade-offs (write cost, storage)", r"trade.?off|write|storage|cost")],
             "explanation": "Include DB/version, table size, current p95, the query, EXPLAIN (ANALYZE) output, existing indexes, a "
                            "target latency, and ask for index options with trade-offs (e.g. composite (status, created_at DESC))."},
        ],
    },
    {
        "id": "prompt-arch", "section": "prompts", "title": "Write an architecture-understanding prompt",
        "difficulty": "Medium", "minutes": 10, "summary": "Onboard to an unfamiliar repo with AI, safely.",
        "context": "You joined a team with a 120k-line Spring Boot monorepo. Weak prompt: \"explain this repo\".",
        "tasks": [
            {"id": "prompt", "kind": "prompt", "prompt": "Write a prompt that helps you build an accurate mental model of the codebase.",
             "rubric": [("Provide structure (tree / key files / build files)", r"tree|structure|pom|gradle|files|module"),
                        ("Ask for a specific flow trace", r"flow|trace|request|end.?to.?end"),
                        ("Ask for components and responsibilities", r"component|responsib|layer|module"),
                        ("Ask for a diagram / structured output", r"diagram|mermaid|table|bullet|format"),
                        ("Ask to cite files / say when unsure (avoid hallucination)", r"cite|file path|reference|unsure|don't guess|assum")],
             "explanation": "Share the tree + build files + entry points, ask for modules and responsibilities, one end-to-end request trace with file "
                            "citations, a mermaid diagram, and to flag assumptions rather than guess."},
        ],
    },
    {
        "id": "prompt-tests", "section": "prompts", "title": "Write a test-generation prompt",
        "difficulty": "Easy", "minutes": 8, "summary": "Ask for tests that actually catch bugs.",
        "context": "Weak prompt: \"write tests\". Function: merge(intervals) from the AI-assisted section.",
        "tasks": [
            {"id": "prompt", "kind": "prompt", "prompt": "Write a strong test-generation prompt.",
             "rubric": [("Framework (pytest / jest ...)", r"pytest|jest|junit|unittest|framework"),
                        ("Function signature / code", r"merge|signature|code"),
                        ("Edge cases listed", r"edge|empty|touch|nest|unsorted"),
                        ("Behaviour/contract (e.g. must not mutate input)", r"mutat|contract|expect|behavio"),
                        ("Format: table-driven / parametrized", r"parametri|table|each case")],
             "explanation": "Name the framework, paste the function, list edge cases and contract (e.g. no input mutation), ask for parametrized tests with explanations."},
        ],
    },
    # ------------------------------------------------------------------ 7. System Thinking
    {
        "id": "sys-photo-upload", "section": "system", "title": "Photo upload pipeline",
        "difficulty": "Medium", "minutes": 20, "summary": "Trace frontend → API → storage → queue → worker → DB.",
        "context": """Architecture:

  [Browser] --1--> [API: POST /uploads] --2--> [S3 presigned URL]
      |                                              ^
      +-------------------3 (PUT file)---------------+
  [S3 event] --4--> [SQS queue] --5--> [Thumbnail workers x2] --6--> [Postgres: photos] --7--> [CDN]

Metrics (Monday 10:00): queue depth 48,000 and rising, worker CPU 98%, API p95 120ms, DB CPU 15%.""",
        "tasks": [
            {"id": "flow", "kind": "order", "prompt": "Order the data flow for one upload.",
             "items": ["Browser asks the API for a presigned URL", "Browser PUTs the file directly to S3",
                       "S3 emits an object-created event to the queue", "A worker generates thumbnails",
                       "Worker writes photo metadata to Postgres", "Users fetch images through the CDN"],
             "explanation": "Direct-to-S3 upload keeps large files off the API; processing is asynchronous via the queue."},
            {"id": "bottleneck", "kind": "choice", "prompt": "Where is the bottleneck?",
             "options": ["API servers", "Thumbnail workers", "Postgres", "CDN"], "answer": 1,
             "explanation": "Queue depth grows and worker CPU is saturated while API and DB are idle."},
            {"id": "fix", "kind": "text", "prompt": "How do you fix it and keep it fixed?",
             "rubric": [("Autoscale workers on queue depth / age", r"autoscal|scale.*worker|queue depth|queue age"),
                        ("Make processing idempotent (at-least-once delivery)", r"idempot|at.?least.?once|duplicate"),
                        ("DLQ for poison messages", r"dlq|dead.?letter|poison"),
                        ("Alert on queue age", r"alert|monitor|slo")],
             "explanation": "Autoscale workers on queue depth/age, make processing idempotent, use a DLQ, alert on oldest-message age."},
        ],
    },
    {
        "id": "sys-feed", "section": "system", "title": "Feed latency spike after deploy",
        "difficulty": "Hard", "minutes": 20, "summary": "Cache stampede across frontend, API, Redis and Postgres.",
        "context": """Architecture:

  [React app] -> [API Gateway] -> [Feed service] -> [Redis cache (TTL 60s)] -> miss -> [Postgres (feed query 400ms)]

After each deploy (which flushes Redis), Postgres CPU hits 100%, feed p99 goes from 80ms to 12s for ~3 minutes.
Every hot key expires at exactly the same time on the hour as well.""",
        "tasks": [
            {"id": "root", "kind": "choice", "prompt": "What is happening?",
             "options": ["Gateway rate limiting", "Cache stampede / thundering herd: many concurrent misses hit Postgres at once",
                         "React re-renders", "Redis is too slow"], "answer": 1,
             "explanation": "Empty cache + synchronized TTLs → thousands of identical 400ms queries in parallel."},
            {"id": "fix", "kind": "text", "prompt": "Propose mitigations.",
             "rubric": [("Request coalescing / single-flight / lock per key", r"coalesc|single.?flight|lock|mutex"),
                        ("TTL jitter", r"jitter|random"),
                        ("Stale-while-revalidate / early refresh", r"stale|revalidat|early|refresh ahead"),
                        ("Warm cache before switching traffic / don't flush on deploy", r"warm|pre.?populat|don't flush|versioned key")],
             "explanation": "Single-flight per key, TTL jitter, serve stale while revalidating, warm the cache (don't flush on deploy)."},
        ],
    },
    {
        "id": "sys-checkout-api", "section": "system", "title": "Checkout API interactions",
        "difficulty": "Hard", "minutes": 20, "summary": "Synchronous service chain, failures and consistency.",
        "context": """Checkout today (all synchronous HTTP):

  [Web] -> [Order svc] -> [Inventory svc] -> [Payment svc] -> [Partner gateway]
                              \\-> [Notification svc]

Each hop: p99 300ms, availability 99.9%. Partner gateway p99 2s.""",
        "tasks": [
            {"id": "avail", "kind": "choice", "prompt": "Roughly what is the end-to-end availability of 4 internal 99.9% services in series?",
             "options": ["99.9%", "99.6%", "96%", "99.99%"], "answer": 1,
             "explanation": "0.999⁴ ≈ 0.996 — chains multiply failure probability."},
            {"id": "design", "kind": "text", "prompt": "How would you redesign it to be more resilient and consistent?",
             "rubric": [("Async notifications via events/queue", r"async|queue|event|kafka|outbox"),
                        ("Saga / compensating actions for inventory+payment", r"saga|compensat|orchestrat|choreograph"),
                        ("Idempotency keys between services", r"idempot"),
                        ("Timeouts / retries / circuit breakers", r"timeout|retr|circuit")],
             "explanation": "Make notifications async (outbox + queue), run reserve→charge→confirm as a saga with compensations, idempotency keys on every hop, timeouts + breakers."},
        ],
    },
    # ------------------------------------------------------------------ 8. Code Review Training
    {
        "id": "rev-search", "section": "review", "title": "PR #482: user search endpoint",
        "difficulty": "Easy", "minutes": 10, "summary": "A small backend PR with big security problems.",
        "context": "Author: \"Added quick user search for the admin panel. Tested locally, works!\"",
        "files": [("PR-482.diff", "diff", PR_SQL)],
        "tasks": [
            {"id": "lines", "kind": "lines", "prompt": "Leave a comment on every problematic line (4).",
             "explanation": "Missing auth, SQL injection, leaking sensitive columns, unbounded results."},
            {"id": "decision", "kind": "choice", "prompt": "Your review decision?",
             "options": ["Approve", "Approve with nits", "Request changes"], "answer": 2,
             "explanation": "Security issues block merge."},
            {"id": "better", "kind": "text", "prompt": "Suggest the better implementation.",
             "rubric": [("Bound parameters / ORM query", r"bind|parameter|:q|ilike|orm|select\("),
                        ("Admin-only dependency", r"admin|auth|role|permission"),
                        ("Response schema without secrets", r"schema|response_model|pydantic|exclude|password"),
                        ("Limit / pagination", r"limit|paginat")],
             "explanation": "Depends(require_admin); select(User).where(User.name.ilike(f'%{q}%')).limit(20) with bound params; response_model=list[UserPublic]."},
        ],
    },
    {
        "id": "rev-react", "section": "review", "title": "PR #219: Profile component",
        "difficulty": "Medium", "minutes": 12, "summary": "Frontend PR with effects, rendering and security issues.",
        "context": "Author: \"New profile page with bio and posts.\"",
        "files": [("PR-219.diff", "diff", PR_REACT)],
        "tasks": [
            {"id": "lines", "kind": "lines", "prompt": "Comment on the problematic lines (4).",
             "explanation": "Missing effect dependency, fetch in render (infinite loop), XSS via dangerouslySetInnerHTML, index keys."},
            {"id": "better", "kind": "text", "prompt": "How should data fetching be implemented instead?",
             "rubric": [("useEffect with [userId] deps", r"\[userid\]|depend"),
                        ("AbortController / cleanup", r"abort|cleanup|cancel"),
                        ("Or a data library (React Query / SWR)", r"react query|tanstack|swr|loader"),
                        ("Loading and error states", r"loading|error")],
             "explanation": "One effect keyed on [userId] with AbortController cleanup (or React Query/SWR), handle loading/error, render bio as text."},
        ],
    },
    {
        "id": "rev-java", "section": "review", "title": "PR #77: monthly finance report",
        "difficulty": "Medium", "minutes": 12, "summary": "Readability, performance and reliability review.",
        "context": "Author: \"Cron job for finance's monthly top-customer report.\"",
        "files": [("PR-77.diff", "diff", PR_JAVA)],
        "tasks": [
            {"id": "lines", "kind": "lines", "prompt": "Comment on the problematic lines (5).",
             "explanation": "findAll() into memory, N+1, double money, magic number, swallowed exception."},
            {"id": "maint", "kind": "text", "prompt": "Rate readability & maintainability and propose a cleaner structure.",
             "rubric": [("Single aggregate query (GROUP BY / HAVING)", r"group by|having|aggregate"),
                        ("BigDecimal", r"bigdecimal"),
                        ("Named/configurable threshold & clock injection", r"constant|config|threshold|clock"),
                        ("Separate reporting from mailing; handle errors", r"separat|single responsib|log|rethrow|alert")],
             "explanation": "One SQL aggregate with HAVING sum > :threshold, BigDecimal, inject Clock + threshold config, split query/render/send and log or rethrow failures."},
        ],
    },
    # ------------------------------------------------------------------ 9. AI Verification Challenges
    {
        "id": "ver-bsearch", "section": "verify", "title": "AI binary search",
        "difficulty": "Easy", "minutes": 8, "summary": "The AI claims O(log n) and full correctness.",
        "context": "AI: \"Here's an efficient, production-ready binary search. It uses Python's built-in bisect_search when available.\"",
        "files": [("ai_answer.py", "python", AI_BSEARCH)],
        "tasks": [
            {"id": "verdict", "kind": "choice", "prompt": "Verdict?", "options": ["Correct — ship it", "Contains bugs / hallucinations"],
             "answer": 1, "explanation": "Hallucinated API, float index, and a loop that misses the last candidate."},
            {"id": "lines", "kind": "lines", "prompt": "Flag the faulty lines (3).",
             "explanation": "bisect.bisect_search doesn't exist; / instead of //; while lo < hi with hi = mid - 1 skips lo == hi."},
            {"id": "why", "kind": "text", "prompt": "How would you have caught these quickly?",
             "rubric": [("Check docs / REPL for the API", r"doc|repl|exist|hallucin"),
                        ("Run tests incl. edge cases (target at ends, single element)", r"test|edge|last|end|single"),
                        ("Type checker / linter", r"type|mypy|lint|pyright")],
             "explanation": "Verify APIs against docs/REPL, run tests for first/last/missing/single-element cases, and use a type checker."},
        ],
    },
    {
        "id": "ver-parens", "section": "verify", "title": "AI valid parentheses",
        "difficulty": "Easy", "minutes": 6, "summary": "Not every AI answer is wrong. Can you tell?",
        "context": "AI: \"Stack-based solution, O(n) time, O(n) space.\"",
        "files": [("ai_answer.py", "python", AI_PARENS)],
        "tasks": [
            {"id": "verdict", "kind": "choice", "prompt": "Verdict?", "options": ["Correct", "Contains bugs"], "answer": 0,
             "explanation": "It is correct for inputs containing only bracket characters."},
            {"id": "why", "kind": "text", "prompt": "Justify your verdict and mention any assumptions.",
             "rubric": [("Closing bracket must match the top of the stack", r"top|pop|match"),
                        ("Empty stack at the end", r"empty|not stack|leftover"),
                        ("Assumes only bracket characters (others get pushed)", r"assum|other char|letters|only bracket")],
             "explanation": "Each closer must match the most recent opener; leftovers mean invalid. Assumption: any non-closing char is treated as an opener."},
        ],
    },
    {
        "id": "ver-dedupe", "section": "verify", "title": "AI order-preserving dedupe",
        "difficulty": "Easy", "minutes": 5, "summary": "The docstring makes a promise the code can't keep.",
        "context": "AI: \"One-liner that removes duplicates and preserves order in O(n).\"",
        "files": [("ai_answer.py", "python", AI_DEDUP)],
        "tasks": [
            {"id": "verdict", "kind": "choice", "prompt": "Verdict?", "options": ["Correct", "Contains bugs"], "answer": 1,
             "explanation": "set() is unordered and requires hashable items."},
            {"id": "lines", "kind": "lines", "prompt": "Flag the faulty line.", "explanation": "list(set(items)) loses order."},
            {"id": "fix", "kind": "text", "prompt": "Give a correct implementation.",
             "rubric": [("dict.fromkeys or seen-set loop", r"fromkeys|seen"),
                        ("Preserves first occurrence order", r"order|first")],
             "explanation": "list(dict.fromkeys(items)) — dicts preserve insertion order (hashable items); for unhashable, a seen list/serialised keys."},
        ],
    },
    {
        "id": "ver-sql", "section": "verify", "title": "AI 'second highest salary' SQL",
        "difficulty": "Medium", "minutes": 8, "summary": "Confident comments, wrong results.",
        "context": "AI: \"This query handles ties and returns NULL when there's no second salary.\"",
        "files": [("ai_answer.sql", "sql", AI_SQL)],
        "tasks": [
            {"id": "verdict", "kind": "choice", "prompt": "Verdict?", "options": ["Correct", "Contains bugs"], "answer": 1,
             "explanation": "Both claims in the comment are false."},
            {"id": "lines", "kind": "lines", "prompt": "Flag the faulty lines (2).",
             "explanation": "No DISTINCT (ties) and empty result instead of NULL."},
            {"id": "fix", "kind": "text", "prompt": "Write a correct query.",
             "rubric": [("DISTINCT or MAX(salary) < MAX", r"distinct|max\(salary\).*<|dense_rank"),
                        ("Returns NULL via scalar subquery / aggregate", r"select \(|subquery|max\(|null")],
             "explanation": "SELECT MAX(salary) FROM employees WHERE salary < (SELECT MAX(salary) FROM employees); — or a scalar subquery with DISTINCT ... OFFSET 1."},
        ],
    },
]

"""Rule-based mentor used when no LLM is configured, so hints and plans always work."""

import re

from ..data.lessons import LESSONS
from ..models import Question

# pattern/topic -> (nudge, pattern explanation, step outline)
HINTS: dict[str, tuple[str, str, str]] = {
    "Hashing": (
        "What if you could answer 'have I seen this value before?' in O(1)?",
        "Use a hash map / set to remember values (or counts) you've already visited while scanning once.",
        "1) Scan the input once. 2) For each element compute what you need (complement, key, count). "
        "3) Look it up in the map before inserting the current element. 4) Return/update the answer.",
    ),
    "Two Pointers": (
        "Does sorting the input, or the input already being sorted, let you discard candidates quickly?",
        "Two pointers: start at both ends (or slow/fast from the start) and move the pointer that can improve the answer.",
        "1) Sort if allowed. 2) left=0, right=n-1. 3) Compare the current pair with the target. "
        "4) Move left forward if you need a bigger value, right backward if smaller. 5) Skip duplicates if required.",
    ),
    "Sliding Window": (
        "You're looking for a contiguous subarray/substring — can you reuse work when the range shifts by one?",
        "Sliding window: grow the right edge, and shrink the left edge whenever the window becomes invalid.",
        "1) Keep counts/state for the window. 2) Expand right, update state. 3) While invalid, shrink left and update. "
        "4) Record the best window after each expansion.",
    ),
    "Fast & Slow Pointers": (
        "What happens if one pointer moves twice as fast as another?",
        "Floyd's fast & slow pointers detect cycles and find middles in O(1) space.",
        "1) slow=fast=head. 2) Move slow by 1, fast by 2. 3) If they meet there's a cycle. "
        "4) To find the cycle start, reset one to head and move both by 1 until they meet.",
    ),
    "Binary Search": (
        "Is there a monotonic property — once something is true it stays true?",
        "Binary search on the index or on the answer space; check the mid condition and discard half each step.",
        "1) Define lo/hi over the index or answer range. 2) mid=(lo+hi)//2. 3) Write a check(mid) that is monotonic. "
        "4) Move lo or hi based on check. 5) Be careful with off-by-one and the loop condition.",
    ),
    "Merge Intervals": (
        "What if the intervals were sorted by start time?",
        "Sort by start, then merge each interval into the previous one if they overlap.",
        "1) Sort by start. 2) Keep a result list. 3) If current.start <= last.end, extend last.end. 4) Otherwise append.",
    ),
    "Cyclic Sort": (
        "Values lie in 1..n — could each value tell you exactly which index it belongs to?",
        "Cyclic sort: place each number at index value-1 by swapping, then scan for mismatches.",
        "1) For i in range(n): while nums[i] is in range and not at its spot, swap it there. 2) Scan for the first index i with nums[i] != i+1.",
    ),
    "In-place Reversal": (
        "Can you flip the next pointers as you walk the list, using only a few variables?",
        "In-place reversal with prev / curr / next pointers.",
        "1) prev=None, curr=head. 2) Save nxt=curr.next. 3) curr.next=prev. 4) prev=curr, curr=nxt. 5) For sub-lists, reconnect the boundaries.",
    ),
    "BFS": (
        "Do you need the shortest number of steps, or a level-by-level order?",
        "BFS with a queue explores in layers; the first time you reach a node is the shortest path in an unweighted graph.",
        "1) Push the start(s) into a queue and mark visited. 2) Pop, process neighbours, push unvisited ones. "
        "3) Track levels by processing the queue size per iteration.",
    ),
    "DFS": (
        "Can the answer for a node be built from the answers of its children/neighbours?",
        "DFS / recursion: solve the sub-problem for each child and combine on the way back up.",
        "1) Define what the recursive function returns. 2) Handle the base case (null / visited). "
        "3) Recurse on children. 4) Combine results and update a global answer if needed.",
    ),
    "Topological Sort": (
        "Are there dependencies — something must happen before something else?",
        "Topological sort (Kahn's BFS on in-degrees) orders a DAG and detects cycles.",
        "1) Build adjacency + in-degree. 2) Queue all nodes with in-degree 0. 3) Pop, append to order, decrement neighbours. "
        "4) If the order has fewer than n nodes there's a cycle.",
    ),
    "Top-K Elements": (
        "Do you need the whole sorted order, or just the best K?",
        "Keep a heap of size K (min-heap for K largest) so each insertion is O(log K).",
        "1) Push elements into a min-heap. 2) If size > K, pop the smallest. 3) The heap now holds the K largest.",
    ),
    "K-way Merge": (
        "You have several sorted lists — which element could possibly be next overall?",
        "K-way merge: a min-heap holding the current head of each list.",
        "1) Push the head of each list. 2) Pop the smallest, append to output. 3) Push that list's next element.",
    ),
    "Two Heaps": (
        "Can you keep the smaller half and the larger half of the numbers separately?",
        "Two heaps: a max-heap for the lower half and a min-heap for the upper half; balance their sizes.",
        "1) Insert into the max-heap, move its top to the min-heap. 2) Rebalance so sizes differ by at most 1. 3) Median comes from the tops.",
    ),
    "Backtracking": (
        "Can you build the answer one choice at a time and undo a choice when it leads nowhere?",
        "Backtracking: choose → explore → un-choose, pruning invalid partial states early.",
        "1) Write dfs(index, path). 2) If path is complete, record it. 3) For each choice: add it, recurse, remove it. "
        "4) Skip duplicates (sort first) and prune impossible branches.",
    ),
    "1D DP": (
        "Can the answer at position i be built from answers at i-1, i-2, ...?",
        "1D DP: dp[i] depends on a few previous states; often reducible to O(1) space.",
        "1) Define dp[i] in words. 2) Write the recurrence. 3) Set base cases. 4) Iterate in order. 5) Optimise space.",
    ),
    "2D / Grid DP": (
        "On a grid, from which neighbouring cells can you arrive at (i, j)?",
        "Grid DP: dp[i][j] built from top/left (or other allowed moves).",
        "1) dp[i][j] = best way to reach (i, j). 2) Fill the first row/column. 3) Combine from allowed previous cells. 4) Answer at the target cell.",
    ),
    "Knapsack": (
        "For each item, you either take it or skip it — what state do you need to remember?",
        "Knapsack DP over (item, capacity/target). Unbounded variants allow reusing an item.",
        "1) dp[c] = best/ways for capacity c. 2) For each item loop capacity (backwards for 0/1, forwards for unbounded). 3) dp[c] = combine(dp[c], dp[c-w] + v).",
    ),
    "LIS": (
        "For each element, what is the longest increasing chain that can end there?",
        "LIS: O(n²) DP or O(n log n) patience sorting with binary search.",
        "1) tails = []. 2) For each x, binary-search the first tail >= x and replace it (or append). 3) len(tails) is the answer.",
    ),
    "DP on Strings": (
        "Compare the two strings character by character from the end — what are your options when they match vs. don't?",
        "String DP: dp[i][j] over prefixes of both strings (LCS / edit distance family).",
        "1) dp[i][j] = answer for s[:i], t[:j]. 2) If s[i-1]==t[j-1] use dp[i-1][j-1]. 3) Else take the best of insert/delete/replace or skip options.",
    ),
    "Partition DP / MCM": (
        "Try every place where the 'last' split or operation could happen.",
        "Interval / MCM DP: dp[i][j] = best over k in (i, j) of dp[i][k] + dp[k][j] + cost.",
        "1) dp over intervals by increasing length. 2) For each (i, j) try every split k. 3) Take min/max.",
    ),
    "Greedy": (
        "Is there a locally best choice that never hurts the final answer?",
        "Greedy: sort or scan and make the best local decision; prove it with an exchange argument.",
        "1) Decide the sort key / scan order. 2) Make the locally optimal choice. 3) Keep a running answer.",
    ),
    "Monotonic Stack": (
        "For each element, do you need the next/previous greater or smaller element?",
        "Monotonic stack keeps indices in increasing/decreasing order; popping reveals the answer for the popped element.",
        "1) Iterate over indices. 2) While the stack top violates the order, pop and resolve it with the current index. 3) Push the current index.",
    ),
    "Prefix Sum": (
        "Can you express any subarray sum as a difference of two prefix sums?",
        "Prefix sums + hash map of seen prefix values count subarrays with a target sum in O(n).",
        "1) running=0, seen={0:1}. 2) For each x: running+=x, ans+=seen[running-k], seen[running]+=1.",
    ),
    "Union Find": (
        "Are you repeatedly merging groups and asking whether two things are in the same group?",
        "Disjoint Set Union with path compression and union by rank.",
        "1) parent[i]=i. 2) find with path compression. 3) union roots by rank. 4) Count components or detect cycles on union.",
    ),
    "Shortest Path": (
        "Edges have weights — does plain BFS still give the shortest path?",
        "Dijkstra with a min-heap for non-negative weights (Bellman-Ford / BFS-by-stops for constraints).",
        "1) dist=[inf]; dist[src]=0. 2) Heap of (dist, node). 3) Pop, skip stale entries, relax edges, push improved distances.",
    ),
    "Minimum Spanning Tree": (
        "You want to connect everything at the minimum total cost.",
        "MST via Kruskal (sort edges + DSU) or Prim (heap).",
        "1) Sort edges by weight. 2) Add an edge if it joins two different components (DSU). 3) Stop at n-1 edges.",
    ),
    "Kadane": (
        "Should the best subarray ending here extend the previous one, or start fresh?",
        "Kadane's algorithm: cur = max(x, cur + x); best = max(best, cur).",
        "1) cur=best=nums[0]. 2) For each next x update cur and best. 3) For products, track both max and min.",
    ),
    "Divide & Conquer": (
        "Can you split the problem in half, solve each half and combine?",
        "Divide & conquer (merge-sort style) with a linear combine step.",
        "1) Split at mid. 2) Recurse on both halves. 3) Combine results while counting/merging.",
    ),
    "Simulation": (
        "Carefully model exactly what the statement describes — what state changes each step?",
        "Simulation: maintain boundaries/state and apply the rules step by step.",
        "1) Define state (boundaries, direction). 2) Loop applying the rule. 3) Update state and stop at the end condition.",
    ),
}

TOPIC_FALLBACK = {
    "Arrays": "Hashing", "Strings": "Hashing", "Linked List": "In-place Reversal", "Stack & Queue": "Monotonic Stack",
    "Binary Tree": "DFS", "Binary Search Tree": "DFS", "Heap": "Top-K Elements", "Graph": "BFS",
    "Dynamic Programming": "1D DP", "Trie": "DFS", "Matrix": "BFS", "Bit Manipulation": "Simulation",
    "Math": "Simulation", "Design": "Hashing", "Sorting": "Greedy", "Recursion": "Backtracking",
}

FOOTER = "\n\n— Offline mentor. Add an AI key in backend/.env for full conversational help."


def _key(q: Question | None) -> str | None:
    if q is None:
        return None
    patterns = [t.name for t in q.tags if t.kind == "pattern" and t.name in HINTS]
    if patterns:
        return patterns[0]
    topics = [t.name for t in q.tags if t.kind == "topic" and t.name in TOPIC_FALLBACK]
    return TOPIC_FALLBACK[topics[0]] if topics else None


def _lesson(message: str) -> str | None:
    text = message.lower()
    matches = [(len(topic), track, topic) for track, topics in LESSONS.items() for topic in topics if topic.lower() in text]
    if not matches:
        query = re.sub(r"^\s*(please\s+)?(teach me|explain|what is|what are|tell me about)\s+", "", text).strip(" ?.!")
        if len(query) >= 4:
            matches = [(len(topic), track, topic) for track, topics in LESSONS.items() for topic in topics
                       if query in topic.lower()]
    if not matches:
        return None
    # Prefer the lesson whose track is also named, then the longest topic name.
    _, track, topic = max(matches, key=lambda m: (m[1].lower() in text, m[0]))
    points, practice = LESSONS[track][topic]
    bullets = "\n".join(f"• {p}" for p in points)
    return (f"{topic} ({track})\n\nKey ideas:\n{bullets}\n\nTry this: {practice}\n\n"
            "Explain it back to me in your own words — that's the fastest way to check you've got it.")


def reply(mode: str, q: Question | None, hint_level: int, last_message: str, planner_context: str = "") -> str:
    key = _key(q)
    if mode == "hint":
        if key is None:
            return ("Pick a problem from the list (or use the Hint button in DSA Sheets) and I'll give you a "
                    "nudge → pattern → step outline." + FOOTER)
        nudge, pattern, steps = HINTS[key]
        text = {1: f"Hint 1 — nudge: {nudge}", 2: f"Hint 2 — pattern ({key}): {pattern}", 3: f"Hint 3 — steps: {steps}"}
        return text[hint_level] + FOOTER
    if mode == "teacher":
        if lesson := _lesson(last_message):
            return lesson + FOOTER
        if key is None:
            key = next((k for k in HINTS if k.lower() in last_message.lower()), None)
        if key is None:
            topics = ", ".join(HINTS)
            return (f"I can explain any topic from the Learn page (e.g. 'Teach me Window Functions', 'Teach me Deadlocks') "
                    f"or these DSA patterns: {topics}." + FOOTER)
        nudge, pattern, steps = HINTS[key]
        return f"Concept: {key}\n\n{pattern}\n\nHow to apply it:\n{steps}\n\nCheck yourself: {nudge}" + FOOTER
    if mode == "interviewer":
        title = q.title if q else "the problem"
        return (f"Let's do {title}.\n1) Restate the problem and ask about input size and edge cases.\n"
                "2) Give a brute force and its complexity.\n3) Optimise — which pattern applies and why?\n"
                "4) Walk me through an example before coding.\n5) After coding: test empty, single element, duplicates, "
                "negatives, and the largest input." + FOOTER)
    if mode == "debugger":
        return ("Debug checklist:\n• Off-by-one in loop bounds / binary search (lo <= hi vs lo < hi)\n"
                "• Not resetting state between test cases\n• Integer overflow / division by zero\n"
                "• Mutating a collection while iterating it\n• Missing base case in recursion\n"
                "• Forgetting to mark visited before pushing to the queue\n"
                "Trace your code by hand on the smallest failing input." + FOOTER)
    return (f"{planner_context}\n\n| Day | Focus | Tasks | Time |\n|---|---|---|---|\n"
            "| 1 | Weakest topic | 3 easy + 1 medium | 2h |\n| 2 | Weakest topic | 2 medium + revise due | 2h |\n"
            "| 3 | 2nd weakest topic | 3 medium | 2h |\n| 4 | Revision | all due revisions + 1 hard | 2h |\n"
            "| 5 | Target company sheet | 3 high-frequency problems | 2.5h |\n| 6 | Contest | 1 virtual/live contest + upsolve | 2.5h |\n"
            "| 7 | Mock interview | 2 timed problems + review notes | 2h |" + FOOTER)

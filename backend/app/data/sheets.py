"""Canonical problem bank and curated sheet definitions.

Every sheet references the same canonical LeetCode problem, so solving a problem once marks it
solved in every sheet that contains it. Sheet membership follows each sheet's published list
as closely as a LeetCode-canonical catalog allows; import the official list via
POST /api/dsa/sheets/import for exact ordering.
"""

from dataclasses import dataclass, field

# code -> (sheet slug, name, description)
SHEETS: dict[str, tuple[str, str, str]] = {
    "A2Z": ("striver-a2z", "take U forward · A2Z DSA Sheet", "Striver's (TUF) step-by-step A to Z DSA course sheet."),
    "SDE": ("striver-sde", "take U forward · SDE Sheet", "Striver's (TUF) SDE interview sheet."),
    "S79": ("striver-79", "take U forward · 79 Last-Moment", "Striver's (TUF) last-moment revision sheet."),
    "TDP": ("striver-dp", "take U forward · DP Series", "Striver's (TUF) dynamic programming playlist problems."),
    "TGR": ("striver-graph", "take U forward · Graph Series", "Striver's (TUF) graph playlist problems."),
    "LB": ("love-babbar-450", "Love Babbar 450", "Love Babbar's DSA cracker sheet (LeetCode equivalents)."),
    "B75": ("blind-75", "Blind 75", "The classic 75 must-do interview problems."),
    "NC": ("neetcode-150", "NeetCode 150", "Blind 75 extended with pattern-focused problems."),
    "NC2": ("neetcode-250", "NeetCode 250", "NeetCode 150 plus extra practice problems."),
    "G75": ("grind-75", "Grind 75", "Time-boxed interview plan by the author of Blind 75."),
    "G169": ("grind-169", "Grind 169", "The extended Grind list."),
    "TI": ("top-interview-150", "LeetCode Top Interview 150", "LeetCode's official interview study plan."),
    "L75": ("leetcode-75", "LeetCode 75", "LeetCode's official 75-question study plan."),
    "T100": ("top-100-liked", "LeetCode Top 100 Liked", "The 100 most-liked LeetCode problems."),
    "AP": ("apna-college", "Apna College DSA Sheet", "Apna College's placement DSA sheet."),
    "FZ": ("fraz-sheet", "Fraz DSA Sheet", "Mohammad Fraz's interview preparation sheet."),
    "AG": ("arsh-goyal", "Arsh Goyal DSA Sheet", "Arsh Goyal's 'Must-do' product company sheet."),
    "AV": ("aditya-verma-dp", "Aditya Verma DP", "Problems from Aditya Verma's DP playlist (knapsack, LCS, MCM)."),
    "SP": ("sean-prashad", "Sean Prashad Patterns", "LeetCode problems grouped by the 14 core patterns."),
    "GFG": ("gfg-must-do", "GFG Must-Do", "GeeksforGeeks must-do interview questions (LeetCode equivalents)."),
    "TIH": ("tech-interview-handbook", "Tech Interview Handbook", "Yangshun's week-by-week plan."),
}
FAANG_SHEET = ("faang-premium", "FAANG Top Frequency", "Premium-style list: questions FAANG asks most often.")
FAANG = {"Amazon", "Google", "Meta", "Apple", "Microsoft", "Netflix"}

# Sheets that are strict supersets of others.
IMPLIES = {"B75": ["NC"], "NC": ["NC2"], "G75": ["G169"], "SDE": ["A2Z"], "S79": ["A2Z"], "TDP": ["A2Z"], "TGR": ["A2Z"]}

COMPANIES = {
    "AMZ": "Amazon", "GOO": "Google", "MS": "Microsoft", "META": "Meta", "APL": "Apple", "ADB": "Adobe",
    "UBER": "Uber", "NV": "Nvidia", "GS": "Goldman Sachs", "FK": "Flipkart", "WM": "Walmart",
    "BBG": "Bloomberg", "LI": "LinkedIn", "ATL": "Atlassian", "SF": "Salesforce", "ORC": "Oracle",
}

# code -> (name, kind). Order of topics defines section order inside sheets.
TAGS: dict[str, tuple[str, str]] = {
    "ARR": ("Arrays", "topic"), "STR": ("Strings", "topic"), "HASH": ("Hashing", "topic"),
    "MATH": ("Math", "topic"), "BITS": ("Bit Manipulation", "topic"), "SORT": ("Sorting", "topic"),
    "LL": ("Linked List", "topic"), "STK": ("Stack & Queue", "topic"), "Q": ("Stack & Queue", "topic"),
    "TREE": ("Binary Tree", "topic"), "BST": ("Binary Search Tree", "topic"), "HEAP": ("Heap", "topic"),
    "MAT": ("Matrix", "topic"), "TRIE": ("Trie", "topic"), "GRAPH": ("Graph", "topic"),
    "DP": ("Dynamic Programming", "topic"), "DES": ("Design", "topic"), "REC": ("Recursion", "topic"),
    "TP": ("Two Pointers", "pattern"), "SW": ("Sliding Window", "pattern"), "FS": ("Fast & Slow Pointers", "pattern"),
    "BS": ("Binary Search", "pattern"), "MI": ("Merge Intervals", "pattern"), "CS": ("Cyclic Sort", "pattern"),
    "LLR": ("In-place Reversal", "pattern"), "BFS": ("BFS", "pattern"), "DFS": ("DFS", "pattern"),
    "TOPO": ("Topological Sort", "pattern"), "TOPK": ("Top-K Elements", "pattern"), "KWM": ("K-way Merge", "pattern"),
    "2H": ("Two Heaps", "pattern"), "BT": ("Backtracking", "pattern"), "DP1": ("1D DP", "pattern"),
    "DP2": ("2D / Grid DP", "pattern"), "KNAP": ("Knapsack", "pattern"), "LIS": ("LIS", "pattern"),
    "LCS": ("DP on Strings", "pattern"), "MCM": ("Partition DP / MCM", "pattern"), "GRD": ("Greedy", "pattern"),
    "MONO": ("Monotonic Stack", "pattern"), "PS": ("Prefix Sum", "pattern"), "UF": ("Union Find", "pattern"),
    "SP": ("Shortest Path", "pattern"), "MST": ("Minimum Spanning Tree", "pattern"), "KAD": ("Kadane", "pattern"),
    "DC": ("Divide & Conquer", "pattern"), "SIM": ("Simulation", "pattern"),
}
SECTION_ORDER = list(dict.fromkeys(name for name, kind in TAGS.values() if kind == "topic"))

# slug[=Title] | difficulty | tags | companies (CODE+freq 1-5) | sheets
BANK = """
two-sum | E | ARR HASH | AMZ5 GOO4 MS4 ADB3 APL3 GS2 | B75 G75 SDE TI T100 LB AP FZ AG SP GFG TIH
contains-duplicate | E | ARR HASH SORT | AMZ3 ADB2 APL2 | B75 SP AP TIH
valid-anagram | E | STR HASH SORT | AMZ3 MS2 BBG2 | B75 G75 TI AP SP TIH
group-anagrams | M | STR HASH SORT | AMZ4 MS3 GOO2 BBG3 | B75 TI T100 LB AP SP TIH
top-k-frequent-elements | M | ARR HASH HEAP TOPK | AMZ4 GOO3 META3 | B75 SP AP FZ TIH
product-of-array-except-self | M | ARR PS | AMZ4 META4 MS3 APL3 | B75 G75 TI T100 L75 AP SP TIH
encode-and-decode-strings | M | STR DES | GOO3 META2 | B75
longest-consecutive-sequence | M | ARR HASH | GOO4 AMZ3 | B75 SDE TI T100 SP AP
valid-sudoku | M | ARR HASH MAT | AMZ3 APL2 UBER3 | NC TI
majority-element | E | ARR HASH | AMZ3 GOO2 | G75 SDE TI AP FZ
majority-element-ii | M | ARR | AMZ2 | SDE AP
sort-colors | M | ARR TP SORT | MS3 AMZ3 | SDE T100 G169 LB AP FZ AG GFG SP
next-permutation | M | ARR TP | GOO3 AMZ3 MS2 FK2 | SDE T100 LB AP FZ AG
maximum-subarray | M | ARR DP KAD | AMZ4 MS4 LI3 | B75 G75 SDE T100 TI LB AP FZ AG GFG SP TIH
best-time-to-buy-and-sell-stock | E | ARR SW | AMZ5 MS4 META3 BBG3 GS3 | B75 G75 SDE T100 TI LB AP FZ AG SP TIH
best-time-to-buy-and-sell-stock-ii | M | ARR GRD | AMZ3 | TI TDP AP
rotate-image | M | ARR MAT | AMZ3 MS3 APL3 | NC SDE T100 TI LB AP AG
spiral-matrix | M | ARR MAT SIM | MS4 AMZ3 GOO2 | B75 G169 TI T100 A2Z LB AP FZ AG GFG
set-matrix-zeroes | M | ARR MAT | MS3 AMZ3 META2 | B75 SDE TI T100 AP FZ
pascals-triangle=Pascal's Triangle | E | ARR DP | AMZ2 APL2 | SDE AP
merge-sorted-array | E | ARR TP SORT | META4 MS3 AMZ3 | TI SDE AP LB GFG
find-the-duplicate-number | M | ARR TP FS BS | AMZ4 MS3 | NC SDE T100 G169 LB AP FZ SP
first-missing-positive | H | ARR HASH CS | AMZ3 GOO2 MS2 | T100 G169 NC2 AP FZ SP
missing-number | E | ARR BITS MATH CS | AMZ3 MS2 | B75 A2Z SP AP FZ
find-all-numbers-disappeared-in-an-array | E | ARR CS | GOO2 | SP
move-zeroes | E | ARR TP | META4 MS2 | T100 L75 A2Z AP SP
remove-duplicates-from-sorted-array | E | ARR TP | MS2 META2 | TI SDE AP
rotate-array | M | ARR TP | MS3 AMZ2 | TI A2Z AP
subarray-sum-equals-k | M | ARR HASH PS | META5 GOO3 AMZ3 | T100 G169 A2Z NC2 AP FZ AG SP
4sum | M | ARR TP SORT | AMZ2 | SDE AP
reverse-pairs | H | ARR DC SORT | GOO2 | SDE
max-consecutive-ones | E | ARR | GOO1 | A2Z
max-consecutive-ones-iii | M | ARR SW | META3 | L75 A2Z SP
rearrange-array-elements-by-sign | M | ARR TP | AMZ1 | A2Z
largest-number | M | STR SORT GRD | AMZ3 | NC2
insert-delete-getrandom-o1=Insert Delete GetRandom O(1) | M | DES HASH | AMZ3 META3 | TI NC2
h-index=H-Index | M | ARR SORT | GOO2 | TI
gas-station | M | ARR GRD | AMZ3 | NC TI G169
candy | H | ARR GRD | AMZ3 | TI A2Z
trapping-rain-water | H | ARR TP STK MONO | AMZ5 GOO4 MS3 GS4 FK3 | NC SDE S79 G75 TI T100 LB AP FZ AG GFG SP
jump-game | M | ARR GRD DP | AMZ3 MS2 | B75 TI T100 A2Z AP SP
jump-game-ii | M | ARR GRD | AMZ3 | NC TI T100 A2Z AP
container-with-most-water | M | ARR TP GRD | AMZ3 GOO2 | B75 TI T100 L75 AP FZ SP TIH
3sum | M | ARR TP SORT | AMZ4 MS3 ADB3 META3 | B75 G75 SDE TI T100 LB AP FZ AG SP TIH
two-sum-ii-input-array-is-sorted | M | ARR TP BS | AMZ2 | NC TI AP
3sum-closest | M | ARR TP SORT | META2 | SP AP
valid-palindrome | E | STR TP | MS3 META3 | B75 G75 TI SP AP TIH
is-subsequence | E | STR TP | GOO1 | TI L75
merge-intervals | M | ARR SORT MI | GOO4 MS3 AMZ3 META3 WM2 | B75 G75 SDE S79 TI T100 LB AP FZ AG SP TIH
insert-interval | M | ARR MI | GOO3 | B75 G75 TI SP
non-overlapping-intervals | M | ARR GRD MI | AMZ2 | B75 L75 A2Z SP
meeting-rooms | E | ARR SORT MI | AMZ1 | B75 SP
meeting-rooms-ii | M | ARR HEAP MI | AMZ4 GOO4 META3 | B75 G169 SP
summary-ranges | E | ARR | GOO1 | TI
minimum-number-of-arrows-to-burst-balloons | M | ARR GRD MI | MS1 | TI L75
longest-substring-without-repeating-characters | M | STR HASH SW | AMZ5 MS4 GOO3 ADB3 | B75 G75 SDE S79 TI T100 LB AP FZ AG SP TIH
longest-repeating-character-replacement | M | STR SW | GOO2 | B75 A2Z SP
minimum-window-substring | H | STR HASH SW | GOO4 META3 AMZ2 | B75 G75 TI T100 A2Z LB AP FZ SP
permutation-in-string | M | STR SW | MS2 | NC AP SP
sliding-window-maximum | H | ARR HEAP SW MONO | AMZ4 GOO3 | NC SDE T100 AP AG
find-all-anagrams-in-a-string | M | STR SW | AMZ2 | T100 AP SP
longest-palindromic-substring | M | STR DP | AMZ4 MS3 | B75 G169 S79 T100 LB AP FZ AG SP
palindromic-substrings | M | STR DP | META3 | B75 SP
string-to-integer-atoi=String to Integer (atoi) | M | STR | MS3 AMZ2 | G75 SDE AP
reverse-words-in-a-string | M | STR TP | MS3 | TI SDE L75 AP
longest-common-prefix | E | STR | GOO2 AMZ2 | TI SDE AP
roman-to-integer | E | STR MATH HASH | AMZ2 | TI SDE AP
integer-to-roman | M | STR MATH | AMZ2 | TI SDE
find-the-index-of-the-first-occurrence-in-a-string | E | STR | MS1 | TI SDE
repeated-string-match | M | STR | GOO1 | SDE
count-and-say | M | STR | AMZ1 | SDE LB
valid-parentheses | E | STR STK | AMZ4 MS4 GOO2 META3 | B75 G75 SDE TI T100 LB AP FZ AG SP GFG TIH
generate-parentheses | M | STR BT | AMZ3 MS3 | NC T100 A2Z AP FZ
decode-string | M | STR STK REC | GOO3 AMZ3 | G169 T100 L75 AP
isomorphic-strings | E | STR HASH | GOO2 | TI A2Z
word-pattern | E | STR HASH | UBER1 | TI
ransom-note | E | STR HASH | MS1 | G75 TI
longest-palindrome | E | STR HASH GRD | GOO1 | G75
zigzag-conversion | M | STR | AMZ1 | TI
text-justification | H | STR SIM | GOO2 | TI
reverse-string | E | STR TP | MS1 | AP
sort-characters-by-frequency | M | STR HASH HEAP SORT | AMZ1 | A2Z SP
maximum-nesting-depth-of-the-parentheses | E | STR | - | A2Z
rotate-string | E | STR | - | A2Z
string-compression | M | STR TP | MS1 | L75
reverse-vowels-of-a-string | E | STR TP | GOO1 | L75
merge-strings-alternately | E | STR TP | - | L75
greatest-common-divisor-of-strings | E | STR MATH | - | L75
kids-with-the-greatest-number-of-candies | E | ARR | - | L75
can-place-flowers | E | ARR GRD | LI1 | L75
reverse-linked-list | E | LL LLR | MS4 AMZ3 NV3 APL2 | B75 G75 SDE S79 T100 L75 LB AP FZ AG SP GFG TIH
reverse-linked-list-ii | M | LL LLR | AMZ2 | TI SP
merge-two-sorted-lists | E | LL TP | AMZ3 MS3 APL2 | B75 G75 SDE TI T100 LB AP FZ AG SP TIH
linked-list-cycle | E | LL FS | MS3 AMZ2 | B75 G75 SDE TI T100 LB AP FZ SP TIH
linked-list-cycle-ii | M | LL FS | MS2 | SDE T100 AP FZ SP
middle-of-the-linked-list | E | LL FS | AMZ2 | G75 SDE AP SP
remove-nth-node-from-end-of-list | M | LL TP | META3 AMZ2 | B75 G169 SDE TI T100 AP FZ SP TIH
reorder-list | M | LL FS LLR | AMZ2 META2 | B75 SP
palindrome-linked-list | E | LL FS LLR | META3 AMZ2 | G169 SDE T100 LB AP FZ SP
intersection-of-two-linked-lists | E | LL TP | AMZ3 MS2 | SDE T100 LB AP FZ
add-two-numbers | M | LL MATH | AMZ4 MS3 BBG3 | NC SDE TI T100 LB AP AG
copy-list-with-random-pointer | M | LL HASH | AMZ4 META3 BBG2 | NC SDE TI T100 LB AP AG
reverse-nodes-in-k-group | H | LL LLR | MS3 AMZ3 | NC SDE TI T100 LB AP FZ AG SP
rotate-list | M | LL TP | MS1 | SDE TI AP
flatten-a-multilevel-doubly-linked-list | M | LL DFS | BBG2 | AP
merge-k-sorted-lists | H | LL HEAP KWM | AMZ4 GOO3 META3 | B75 G169 T100 A2Z LB AP FZ AG SP
sort-list | M | LL SORT DC | MS2 | G169 T100 TI A2Z AP
odd-even-linked-list | M | LL | MS1 | L75 A2Z
delete-node-in-a-linked-list | M | LL | APL1 | SDE
delete-the-middle-node-of-a-linked-list | M | LL FS | - | L75 A2Z
remove-duplicates-from-sorted-list | E | LL | - | LB AP
partition-list | M | LL TP | - | TI
maximum-twin-sum-of-a-linked-list | M | LL TP | - | L75
lru-cache=LRU Cache | M | DES HASH LL | AMZ5 MS5 GOO3 NV3 ADB3 FK3 WM2 | NC G75 SDE S79 TI T100 LB AP FZ AG GFG
lfu-cache=LFU Cache | H | DES HASH LL | AMZ3 GOO2 | SDE NC2
min-stack | M | STK DES | AMZ4 BBG3 MS2 | NC G75 SDE TI T100 AP FZ
implement-queue-using-stacks | E | STK Q DES | AMZ2 MS2 | G75 SDE AP
implement-stack-using-queues | E | STK Q DES | - | SDE AP
evaluate-reverse-polish-notation | M | STK MATH | AMZ2 LI2 | NC G75 TI
daily-temperatures | M | STK MONO | AMZ3 GOO2 | NC T100 L75 SP
car-fleet | M | STK SORT MONO | GOO2 | NC
largest-rectangle-in-histogram | H | STK MONO | AMZ3 GOO3 MS2 | NC G169 SDE S79 T100 LB AP FZ AG GFG
maximal-rectangle | H | STK DP MONO MAT | GOO2 AMZ2 | A2Z LB TDP AP
next-greater-element-i | E | STK MONO | AMZ2 | SDE AP
next-greater-element-ii | M | STK MONO | AMZ2 | A2Z AP
asteroid-collision | M | STK | AMZ3 | A2Z L75
sum-of-subarray-minimums | M | STK MONO | AMZ2 | A2Z
remove-k-digits | M | STK GRD MONO | AMZ2 | A2Z
online-stock-span | M | STK MONO DES | AMZ2 | SDE L75
basic-calculator | H | STK MATH | GOO3 AMZ2 | G169 TI
basic-calculator-ii | M | STK MATH | META3 | G169
simplify-path | M | STK STR | META2 | TI
removing-stars-from-a-string | M | STK STR | - | L75
number-of-recent-calls | E | Q DES | - | L75
dota2-senate | M | Q GRD | - | L75
find-the-celebrity | M | ARR TP | META2 | SDE
binary-search | E | ARR BS | MS2 | NC G75 A2Z AP
search-insert-position | E | ARR BS | - | TI A2Z
search-a-2d-matrix | M | ARR BS MAT | AMZ3 MS2 | NC SDE TI T100 LB AP
search-a-2d-matrix-ii | M | BS MAT DC | AMZ3 | A2Z AP AG
find-first-and-last-position-of-element-in-sorted-array | M | ARR BS | META3 GOO2 | TI T100 A2Z LB AP FZ
search-in-rotated-sorted-array | M | ARR BS | MS4 AMZ3 NV2 META3 | B75 G75 SDE S79 TI T100 LB AP FZ AG SP GFG TIH
search-in-rotated-sorted-array-ii | M | ARR BS | - | A2Z
find-minimum-in-rotated-sorted-array | M | ARR BS | MS3 AMZ2 | B75 G169 TI T100 A2Z AP SP TIH
find-peak-element | M | ARR BS | GOO3 META3 | TI L75 A2Z AP
single-element-in-a-sorted-array | M | ARR BS BITS | GOO1 | SDE AP
koko-eating-bananas | M | ARR BS | AMZ2 | NC A2Z L75
capacity-to-ship-packages-within-d-days | M | ARR BS | AMZ2 | A2Z
split-array-largest-sum | H | ARR BS DP | GOO2 | A2Z NC2
minimum-number-of-days-to-make-m-bouquets | M | ARR BS | - | A2Z
find-the-smallest-divisor-given-a-threshold | M | ARR BS | - | A2Z
kth-missing-positive-number | E | ARR BS | META2 | A2Z
magnetic-force-between-two-balls | M | ARR BS SORT | - | A2Z
median-of-two-sorted-arrays | H | ARR BS DC | GOO4 AMZ3 MS3 ADB2 GS3 | NC SDE TI T100 LB AP FZ AG
time-based-key-value-store | M | DES HASH BS | GOO3 | NC G169
sqrtx=Sqrt(x) | E | MATH BS | AMZ2 | TI A2Z
powx-n=Pow(x, n) | M | MATH REC | META3 GOO2 | NC SDE TI AP
successful-pairs-of-spells-and-potions | M | ARR BS SORT | - | L75
guess-number-higher-or-lower | E | BS | - | L75
binary-tree-inorder-traversal | E | TREE DFS STK | MS2 | SDE T100 AP
binary-tree-preorder-traversal | E | TREE DFS STK | - | SDE AP
binary-tree-postorder-traversal | E | TREE DFS STK | - | SDE AP
binary-tree-level-order-traversal | M | TREE BFS | AMZ4 MS3 META3 | B75 G75 SDE TI T100 LB AP FZ AG SP GFG TIH
binary-tree-zigzag-level-order-traversal | M | TREE BFS | AMZ3 MS2 BBG2 | SDE TI LB AP
binary-tree-right-side-view | M | TREE BFS DFS | META4 AMZ2 | NC G75 SDE TI T100 L75 AP SP
maximum-depth-of-binary-tree | E | TREE DFS BFS | AMZ2 MS2 | B75 G75 SDE TI T100 L75 LB AP FZ SP TIH
diameter-of-binary-tree | E | TREE DFS | META4 AMZ2 | NC G75 SDE T100 LB AP FZ SP
balanced-binary-tree | E | TREE DFS | AMZ2 | NC G75 SDE LB AP
same-tree | E | TREE DFS | AMZ1 | B75 SDE TI AP SP TIH
symmetric-tree | E | TREE DFS BFS | MS2 | SDE TI T100 AP
invert-binary-tree | E | TREE DFS | GOO2 | B75 G75 TI T100 A2Z AP SP TIH
subtree-of-another-tree | E | TREE DFS | AMZ2 | B75 AP SP TIH
binary-tree-maximum-path-sum | H | TREE DFS DP | META4 AMZ3 GOO2 | B75 G169 SDE S79 TI T100 AP FZ AG SP TIH
lowest-common-ancestor-of-a-binary-tree | M | TREE DFS | MS4 AMZ4 META4 | G75 SDE S79 TI T100 L75 LB AP FZ AG SP GFG
lowest-common-ancestor-of-a-binary-search-tree | M | BST TREE DFS | AMZ3 MS2 | B75 G75 SDE LB AP SP TIH
construct-binary-tree-from-preorder-and-inorder-traversal | M | TREE DC HASH | AMZ3 MS2 | B75 G75 SDE TI T100 LB AP FZ SP TIH
construct-binary-tree-from-inorder-and-postorder-traversal | M | TREE DC HASH | AMZ2 | SDE TI AP
serialize-and-deserialize-binary-tree | H | TREE DES BFS | AMZ4 META4 GOO3 LI3 | B75 G75 SDE LB AP FZ AG SP TIH
flatten-binary-tree-to-linked-list | M | TREE DFS LL | MS3 META2 | SDE TI T100 AP
populating-next-right-pointers-in-each-node | M | TREE BFS | MS2 AMZ2 | SDE AP
populating-next-right-pointers-in-each-node-ii | M | TREE BFS | BBG1 | TI
vertical-order-traversal-of-a-binary-tree | H | TREE BFS HASH SORT | AMZ3 META3 | SDE LB AP FZ
all-nodes-distance-k-in-binary-tree | M | TREE BFS DFS | AMZ3 META3 | G169 A2Z AP FZ
maximum-width-of-binary-tree | M | TREE BFS | AMZ2 | SDE AP
count-complete-tree-nodes | E | TREE BS DFS | GOO1 | TI A2Z
path-sum | E | TREE DFS | AMZ1 | TI AP
path-sum-ii | M | TREE DFS BT | AMZ2 | AP SP
path-sum-iii | M | TREE DFS PS | AMZ2 | T100 L75 AP
sum-root-to-leaf-numbers | M | TREE DFS | - | TI
binary-tree-paths | E | TREE DFS BT | GOO1 | A2Z AP
count-good-nodes-in-binary-tree | M | TREE DFS | MS2 | NC L75
leaf-similar-trees | E | TREE DFS | - | L75
longest-zigzag-path-in-a-binary-tree | M | TREE DFS DP | - | L75
maximum-level-sum-of-a-binary-tree | M | TREE BFS | - | L75
average-of-levels-in-binary-tree | E | TREE BFS | - | TI
boundary-of-binary-tree | M | TREE DFS | AMZ2 | A2Z
binary-tree-cameras | H | TREE DFS DP GRD | GOO2 | NC2 FZ
house-robber-iii | M | TREE DP DFS | GOO2 | NC2
kth-smallest-element-in-a-bst | M | BST DFS | AMZ3 GOO2 | B75 G75 SDE TI T100 LB AP FZ SP TIH
validate-binary-search-tree | M | BST DFS | AMZ4 MS3 BBG3 META3 | B75 G75 SDE TI T100 LB AP FZ AG SP TIH
search-in-a-binary-search-tree | E | BST | - | SDE L75 AP
insert-into-a-binary-search-tree | M | BST | - | A2Z AP
delete-node-in-a-bst | M | BST | - | L75 A2Z LB AP
convert-sorted-array-to-binary-search-tree | E | BST DC | AMZ2 | TI T100 AP
construct-binary-search-tree-from-preorder-traversal | M | BST STK | AMZ1 | SDE AP
binary-search-tree-iterator | M | BST STK DES | META3 | TI A2Z
two-sum-iv-input-is-a-bst | E | BST HASH TP | AMZ1 | A2Z AP
recover-binary-search-tree | M | BST DFS | AMZ1 | A2Z AP
minimum-absolute-difference-in-bst | E | BST DFS | - | TI
inorder-successor-in-bst | M | BST | META2 | SDE
maximum-sum-bst-in-binary-tree | H | BST DFS DP | AMZ1 | A2Z
kth-largest-element-in-an-array | M | ARR HEAP SORT TOPK | AMZ4 META4 NV2 | NC G169 SDE TI T100 L75 LB AP FZ AG SP
kth-largest-element-in-a-stream | E | HEAP DES | AMZ2 | NC A2Z
last-stone-weight | E | HEAP | AMZ1 | NC
k-closest-points-to-origin | M | HEAP TOPK MATH | META4 AMZ3 | NC G75 SP
task-scheduler | M | HEAP GRD HASH | META3 AMZ2 | NC G75 A2Z SP
design-twitter | M | DES HEAP HASH | AMZ2 | NC
find-median-from-data-stream | H | HEAP DES 2H | AMZ4 GOO3 MS3 | B75 G75 SDE TI T100 LB AP FZ AG SP TIH
ipo=IPO | H | HEAP GRD 2H | AMZ1 | TI SP
find-k-pairs-with-smallest-sums | M | HEAP KWM | - | TI SP
hand-of-straights | M | HASH GRD SORT | GOO2 | NC A2Z
reorganize-string | M | STR HEAP GRD | AMZ3 GOO2 | SP
smallest-number-in-infinite-set | M | HEAP DES | - | L75
total-cost-to-hire-k-workers | M | HEAP TP | - | L75
maximum-subsequence-score | M | HEAP GRD SORT | - | L75
kth-smallest-element-in-a-sorted-matrix | M | HEAP BS MAT KWM | GOO2 | G169 SP AP
top-k-frequent-words | M | HEAP HASH TOPK | AMZ3 | SP
subsets | M | ARR BT BITS | META3 AMZ2 | NC G75 SDE T100 LB AP FZ SP
subsets-ii | M | ARR BT | AMZ1 | NC SDE AP SP
combination-sum | M | ARR BT | AMZ3 | B75 G75 SDE TI T100 LB AP FZ SP TIH
combination-sum-ii | M | ARR BT | AMZ2 | NC SDE AP SP
combination-sum-iii | M | ARR BT | - | L75 A2Z
combinations | M | BT | - | TI SP
permutations | M | ARR BT | AMZ3 MS2 | NC G75 SDE TI T100 LB AP FZ SP
permutations-ii | M | ARR BT | - | AP
word-search | M | ARR BT MAT | MS3 AMZ3 | B75 G75 SDE TI T100 LB AP FZ SP TIH
word-search-ii | H | TRIE BT MAT | AMZ3 MS2 | B75 G169 TI A2Z AP SP TIH
palindrome-partitioning | M | STR BT DP | AMZ2 | NC SDE AP SP
letter-combinations-of-a-phone-number | M | STR BT | AMZ3 | NC G75 TI T100 L75 A2Z AP SP
n-queens=N-Queens | H | BT | AMZ2 | NC SDE T100 LB AP FZ AG
n-queens-ii=N-Queens II | H | BT | - | TI
sudoku-solver | H | BT MAT | AMZ2 MS2 | SDE LB AP AG
permutation-sequence | H | MATH REC | - | SDE
word-break-ii | H | STR DP BT TRIE | AMZ2 | A2Z AP
expression-add-operators | H | MATH BT | META2 GOO1 | A2Z
number-of-islands | M | GRAPH BFS DFS MAT UF | AMZ5 MS4 GOO3 NV2 WM2 | B75 G75 S79 TI T100 TGR LB AP FZ AG SP GFG TIH
max-area-of-island | M | GRAPH DFS MAT | AMZ2 | NC
clone-graph | M | GRAPH BFS DFS HASH | META3 AMZ2 | B75 G75 SDE TI AP SP TIH
walls-and-gates | M | GRAPH BFS MAT | META2 | NC
rotting-oranges | M | GRAPH BFS MAT | AMZ4 MS2 FK2 | NC G75 SDE S79 TGR LB L75 AP FZ AG
pacific-atlantic-water-flow | M | GRAPH DFS BFS MAT | GOO2 | B75 SP TIH
surrounded-regions | M | GRAPH DFS BFS MAT UF | GOO1 | NC TI TGR
course-schedule | M | GRAPH TOPO BFS DFS | AMZ3 GOO3 MS2 | B75 G75 SDE TI T100 TGR LB AP FZ SP TIH
course-schedule-ii | M | GRAPH TOPO | AMZ3 META2 | NC G169 TI TGR AP
graph-valid-tree | M | GRAPH UF DFS | GOO2 LI2 | B75 SP
number-of-connected-components-in-an-undirected-graph | M | GRAPH UF DFS | GOO2 | B75 SP
redundant-connection | M | GRAPH UF | GOO1 | NC
word-ladder | H | GRAPH BFS STR | AMZ4 GOO2 | NC G169 SDE TI TGR LB AP FZ
word-ladder-ii | H | GRAPH BFS BT | AMZ2 | TGR
alien-dictionary | H | GRAPH TOPO STR | AMZ3 META3 GOO2 | B75 TGR SP
flood-fill | E | GRAPH DFS BFS MAT | AMZ1 | G75 TGR SP
01-matrix | M | GRAPH BFS MAT | GOO2 | G75 TGR
is-graph-bipartite | M | GRAPH BFS DFS UF | META2 | SDE TGR AP
find-eventual-safe-states | M | GRAPH TOPO DFS | - | TGR
number-of-enclaves | M | GRAPH DFS BFS MAT | - | TGR
number-of-provinces | M | GRAPH DFS UF | AMZ2 | L75 TGR AP
network-delay-time | M | GRAPH SP HEAP | AMZ2 | NC TGR
cheapest-flights-within-k-stops | M | GRAPH SP BFS DP | AMZ3 | NC TGR
path-with-minimum-effort | M | GRAPH SP HEAP MAT | GOO2 | TGR
shortest-path-in-binary-matrix | M | GRAPH BFS MAT | AMZ2 META2 | TGR
number-of-ways-to-arrive-at-destination | M | GRAPH SP DP | - | TGR
find-the-city-with-the-smallest-number-of-neighbors-at-a-threshold-distance | M | GRAPH SP | - | TGR
min-cost-to-connect-all-points | M | GRAPH MST UF | AMZ2 | NC TGR
number-of-operations-to-make-network-connected | M | GRAPH UF DFS | AMZ1 | TGR
accounts-merge | M | GRAPH UF DFS HASH | META3 GOO2 | G75 TGR
most-stones-removed-with-same-row-or-column | M | GRAPH UF | GOO2 | TGR
making-a-large-island | H | GRAPH UF DFS MAT | GOO2 | TGR
swim-in-rising-water | H | GRAPH HEAP BS UF | GOO1 | NC
critical-connections-in-a-network | H | GRAPH DFS | AMZ3 | TGR
reconstruct-itinerary | H | GRAPH DFS | GOO2 | NC
evaluate-division | M | GRAPH DFS UF | GOO2 | TI
snakes-and-ladders | M | GRAPH BFS MAT | AMZ2 | TI
minimum-genetic-mutation | M | GRAPH BFS STR | - | TI
keys-and-rooms | M | GRAPH DFS | - | L75
reorder-routes-to-make-all-paths-lead-to-the-city-zero | M | GRAPH DFS BFS | - | L75
nearest-exit-from-entrance-in-maze | M | GRAPH BFS MAT | - | L75
minimum-height-trees | M | GRAPH TOPO BFS | GOO1 | G169
bus-routes | H | GRAPH BFS | GOO2 | FZ
longest-increasing-path-in-a-matrix | H | GRAPH DFS DP TOPO MAT | GOO3 | G169 AP
implement-trie-prefix-tree=Implement Trie (Prefix Tree) | M | TRIE DES | AMZ3 MS2 GOO2 | B75 G75 SDE TI T100 L75 LB AP FZ SP TIH
design-add-and-search-words-data-structure | M | TRIE DES DFS | META3 | B75 TI SP TIH
maximum-xor-of-two-numbers-in-an-array | M | TRIE BITS | GOO1 | SDE
maximum-xor-with-an-element-from-array | H | TRIE BITS | - | SDE
search-suggestions-system | M | TRIE STR BS | AMZ3 | L75
longest-word-in-dictionary | M | TRIE STR | - | A2Z
climbing-stairs | E | DP DP1 | AMZ3 ADB2 | B75 G75 TI T100 TDP LB AP FZ SP GFG TIH
min-cost-climbing-stairs | E | DP DP1 | AMZ1 | NC L75
n-th-tribonacci-number=N-th Tribonacci Number | E | DP DP1 | - | L75
house-robber | M | DP DP1 | AMZ3 GOO2 | B75 G169 TI T100 L75 TDP AP SP TIH
house-robber-ii | M | DP DP1 | MS2 | B75 TDP AP SP
decode-ways | M | STR DP DP1 | META4 GOO3 | B75 G169 AP FZ SP TIH
coin-change | M | DP KNAP | AMZ4 GOO3 MS2 GS2 | B75 G75 TI T100 TDP LB AP FZ AV SP GFG TIH
coin-change-ii | M | DP KNAP | AMZ2 | NC TDP AP AV
maximum-product-subarray | M | ARR DP KAD | AMZ3 LI3 | B75 G169 S79 T100 AP FZ SP TIH
word-break | M | STR DP TRIE | AMZ4 GOO3 META3 | B75 G75 SDE TI T100 LB AP FZ SP TIH
longest-increasing-subsequence | M | DP BS LIS | MS3 GOO3 AMZ2 | B75 G169 SDE TI T100 TDP LB AP FZ AG AV SP GFG TIH
partition-equal-subset-sum | M | DP KNAP | AMZ3 META2 | NC G75 T100 TDP LB AP FZ AV SP
unique-paths | M | DP DP2 MAT | AMZ3 GOO2 | B75 G75 SDE T100 TDP LB AP FZ SP TIH
unique-paths-ii | M | DP DP2 MAT | AMZ1 | TI TDP AP
minimum-path-sum | M | DP DP2 MAT | AMZ2 GS2 | TI T100 TDP AP
triangle | M | DP DP2 | AMZ1 | TI TDP
minimum-falling-path-sum | M | DP DP2 MAT | GS2 | TDP
cherry-pickup-ii | H | DP DP2 MAT | GOO1 | TDP
longest-common-subsequence | M | STR DP LCS | AMZ3 GOO2 | B75 G169 SDE T100 L75 TDP LB AP FZ AG AV SP GFG TIH
longest-palindromic-subsequence | M | STR DP LCS | AMZ2 | TDP LB AP AV
minimum-insertion-steps-to-make-a-string-palindrome | H | STR DP LCS | GOO1 | TDP AV
delete-operation-for-two-strings | M | STR DP LCS | GOO1 | TDP AV
shortest-common-supersequence | H | STR DP LCS | AMZ1 | TDP AV
distinct-subsequences | H | STR DP LCS | GOO1 | NC TDP
edit-distance | M | STR DP LCS | GOO3 AMZ3 MS2 | NC SDE T100 TI TDP L75 LB AP FZ AG AV GFG
wildcard-matching | H | STR DP GRD | GOO2 MS2 | TDP LB AP
regular-expression-matching | H | STR DP REC | GOO3 META3 | NC T100 AP
interleaving-string | M | STR DP DP2 | AMZ1 | NC TI AP
best-time-to-buy-and-sell-stock-iii | H | ARR DP | AMZ2 | TI TDP AP
best-time-to-buy-and-sell-stock-iv | H | ARR DP | AMZ1 | TI TDP
best-time-to-buy-and-sell-stock-with-cooldown | M | ARR DP | AMZ2 | NC TDP AP
best-time-to-buy-and-sell-stock-with-transaction-fee | M | ARR DP GRD | AMZ1 | L75 TDP
target-sum | M | ARR DP KNAP BT | META3 | NC TDP AP AV
number-of-longest-increasing-subsequence | M | DP LIS | - | TDP
largest-divisible-subset | M | DP LIS SORT | - | TDP
longest-string-chain | M | DP LIS STR | GOO2 | TDP
burst-balloons | H | DP MCM | GOO2 | NC TDP AV AP
minimum-cost-to-cut-a-stick | H | DP MCM SORT | - | TDP AV
palindrome-partitioning-ii | H | STR DP MCM | AMZ1 | TDP AV LB
partition-array-for-maximum-sum | M | DP DP1 | - | TDP
count-square-submatrices-with-all-ones | M | DP MAT | GOO1 | TDP
maximal-square | M | DP MAT DP2 | AMZ3 GOO2 | G169 TI LB AP
perfect-squares | M | DP MATH BFS | GOO2 | T100 AP
longest-valid-parentheses | H | STR STK DP | AMZ2 | T100 AP FZ
dungeon-game | H | DP DP2 MAT | AMZ1 | LB AP
super-egg-drop | H | DP BS MATH MCM | GOO2 | AV LB
unique-binary-search-trees | M | DP TREE MATH | AMZ1 | AP
ones-and-zeroes | M | DP KNAP | GOO1 | AV
last-stone-weight-ii | M | DP KNAP | GOO1 | AV
domino-and-tromino-tiling | M | DP DP1 | GOO1 | L75
scramble-string | H | STR DP MCM | GOO1 | AV
russian-doll-envelopes | H | DP BS LIS SORT | GOO2 | AP
assign-cookies | E | ARR GRD SORT | AMZ1 | A2Z
lemonade-change | E | ARR GRD | - | A2Z
valid-parenthesis-string | M | STR GRD DP | AMZ2 | NC A2Z
partition-labels | M | STR GRD HASH | AMZ3 | NC A2Z SP
merge-triplets-to-form-target-triplet | M | ARR GRD | GOO1 | NC
increasing-triplet-subsequence | M | ARR GRD | META2 | L75
single-number | E | ARR BITS | AMZ2 | NC TI T100 A2Z AP SP
single-number-ii | M | ARR BITS | GOO1 | TI A2Z
number-of-1-bits | E | BITS | APL1 | B75 TI SP TIH
counting-bits | E | BITS DP | AMZ1 | B75 L75 SP TIH
reverse-bits | E | BITS | APL1 | B75 TI SP
sum-of-two-integers | M | BITS MATH | META2 | B75 SP
power-of-two | E | BITS MATH | GOO1 | A2Z AP
minimum-flips-to-make-a-or-b-equal-to-c | M | BITS | - | L75
divide-two-integers | M | BITS MATH | META2 | A2Z
bitwise-and-of-numbers-range | M | BITS | - | TI
minimum-bit-flips-to-convert-number | E | BITS | - | A2Z
reverse-integer | M | MATH | AMZ2 BBG2 | NC
palindrome-number | E | MATH | AMZ1 | TI AP
plus-one | E | ARR MATH | GOO2 | NC TI
multiply-strings | M | STR MATH | META2 | NC AP
happy-number | E | MATH HASH FS | - | NC TI SP
factorial-trailing-zeroes | M | MATH | - | TI
count-primes | M | MATH | AMZ1 | A2Z AP
max-points-on-a-line | H | MATH HASH | GOO1 | TI
detect-squares | M | DES HASH | GOO1 | NC
add-binary | E | STR MATH BITS | META2 | G75 TI AP
game-of-life | M | ARR MAT SIM | GOO1 | TI
maximum-average-subarray-i=Maximum Average Subarray I | E | ARR SW | - | L75
maximum-number-of-vowels-in-a-substring-of-given-length | M | STR SW | - | L75
longest-subarray-of-1s-after-deleting-one-element=Longest Subarray of 1's After Deleting One Element | M | ARR SW | - | L75
fruit-into-baskets | M | ARR SW HASH | GOO1 | A2Z SP
number-of-substrings-containing-all-three-characters | M | STR SW | - | A2Z
binary-subarrays-with-sum | M | ARR SW PS | - | A2Z
count-number-of-nice-subarrays | M | ARR SW | - | A2Z
subarrays-with-k-different-integers=Subarrays with K Different Integers | H | ARR SW | AMZ1 | A2Z
minimum-size-subarray-sum | M | ARR SW BS | GOO2 | TI AP SP
substring-with-concatenation-of-all-words | H | STR SW HASH | - | TI
find-pivot-index | E | ARR PS | - | L75
find-the-highest-altitude | E | ARR PS | - | L75
contiguous-array | M | ARR HASH PS | META2 | G169 AP
continuous-subarray-sum | M | ARR HASH PS | META2 | SP
subarray-sums-divisible-by-k=Subarray Sums Divisible by K | M | ARR PS | - | AP
find-the-difference-of-two-arrays | E | ARR HASH | - | L75
unique-number-of-occurrences | E | HASH | - | L75
determine-if-two-strings-are-close | M | STR HASH | - | L75
equal-row-and-column-pairs | M | MAT HASH | - | L75
max-number-of-k-sum-pairs=Max Number of K-Sum Pairs | M | ARR TP HASH | - | L75
"""

_UPPER = {"i", "ii", "iii", "iv", "bst", "lru", "lfu", "xor", "ipo"}
_LOWER = {"a", "an", "the", "of", "in", "to", "and", "or", "for", "by", "with", "from", "on", "at", "into", "is"}
_DIFF = {"E": "Easy", "M": "Medium", "H": "Hard"}


@dataclass
class Problem:
    slug: str
    title: str
    difficulty: str
    topics: list[str]
    patterns: list[str]
    companies: dict[str, int]
    sheets: set[str] = field(default_factory=set)

    @property
    def section(self) -> str:
        return self.topics[0] if self.topics else "Misc"


def _title(slug: str) -> str:
    words = slug.split("-")
    out = []
    for i, w in enumerate(words):
        if w in _UPPER:
            out.append(w.upper())
        elif i and w in _LOWER:
            out.append(w)
        else:
            out.append(w.title())
    return " ".join(out)


def _expand(codes: set[str]) -> set[str]:
    out, stack = set(), list(codes)
    while stack:
        c = stack.pop()
        if c not in out:
            out.add(c)
            stack.extend(IMPLIES.get(c, []))
    return out


def problems() -> list[Problem]:
    out = []
    for line in BANK.strip().splitlines():
        head, diff, tags, comps, sheets = (part.strip() for part in line.split("|"))
        slug, _, title = head.partition("=")
        topics, patterns = [], []
        for code in tags.split():
            name, kind = TAGS[code]
            target = topics if kind == "topic" else patterns
            if name not in target:
                target.append(name)
        companies = {} if comps == "-" else {COMPANIES[c[:-1]]: int(c[-1]) for c in comps.split()}
        for code in sheets.split():
            if code not in SHEETS:
                raise ValueError(f"Unknown sheet code {code!r} for {slug}")
        out.append(
            Problem(slug, title or _title(slug), _DIFF[diff], topics, patterns, companies, _expand(set(sheets.split())))
        )
    return out

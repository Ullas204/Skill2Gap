"""Phase 12 – Question banks and parametric generators for the Assessment Platform.

Deterministic, offline-safe content following the existing rule-based engine
philosophy (see interview.question_generator / interview.coding_engine).
"""

from __future__ import annotations

import random
from collections.abc import Callable

from app.services.interview.question_generator import QuestionGenerator


def _mcq(text: str, options: list[str], correct: int, *, skill: str, topic: str,
         difficulty: str, explanation: str, seconds: int = 60) -> dict:
    return {
        "question_type": "mcq",
        "skill": skill,
        "topic": topic,
        "difficulty": difficulty,
        "question_text": text,
        "content": {"options": options},
        "correct_answer": {"option_index": correct},
        "explanation": explanation,
        "estimated_time_seconds": seconds,
    }


# ═══════════════════════════════════════════════════════════════════
# Technical MCQ bank (per-skill)
# ═══════════════════════════════════════════════════════════════════

TECHNICAL_MCQ: dict[str, list[dict]] = {
    "react": [
        _mcq("Which React hook is used to manage local component state?", ["useEffect", "useState", "useMemo", "useRef"], 1,
             skill="React", topic="Hooks", difficulty="easy",
             explanation="useState allows functional components to maintain local state."),
        _mcq("What is the purpose of the dependency array in useEffect?", ["To memoize values", "To control when the effect re-runs", "To pass props", "To define component keys"], 1,
             skill="React", topic="Hooks", difficulty="medium",
             explanation="The dependency array tells React to re-run the effect only when listed values change."),
        _mcq("Why are keys important when rendering lists in React?", ["Styling", "Identifying items across renders for reconciliation", "Sorting", "Accessibility"], 1,
             skill="React", topic="Rendering", difficulty="medium",
             explanation="Keys help React identify which items changed, were added, or removed during reconciliation."),
        _mcq("Which pattern lifts shared state to a common ancestor?", ["Context lifting", "State hoisting (lifting state up)", "Portal pattern", "Reducer pattern"], 1,
             skill="React", topic="State", difficulty="medium",
             explanation="Lifting state up moves shared state to the closest common ancestor of components that need it."),
        _mcq("What does React.memo do?", ["Memoizes expensive calculations", "Skips re-rendering if props are unchanged", "Caches HTTP requests", "Persists state to storage"], 1,
             skill="React", topic="Performance", difficulty="hard",
             explanation="React.memo performs a shallow props comparison and skips re-render when props are equal."),
    ],
    "python": [
        _mcq("Which data type is immutable in Python?", ["list", "dict", "tuple", "set"], 2,
             skill="Python", topic="Types", difficulty="easy",
             explanation="Tuples are immutable; lists, dicts and sets can be modified after creation."),
        _mcq("What does a decorator do in Python?", ["Deletes a function after use", "Wraps a function to extend behavior without modifying it", "Compiles a function", "Renames a module"], 1,
             skill="Python", topic="Functions", difficulty="medium",
             explanation="Decorators wrap functions, extending behavior while keeping the original interface."),
        _mcq("What is the output of len({1, 2, 2, 3})?", ["4", "3", "2", "TypeError"], 1,
             skill="Python", topic="Sets", difficulty="easy",
             explanation="Sets remove duplicates, so {1,2,2,3} has 3 elements."),
        _mcq("How does the GIL affect multithreaded CPU-bound Python code?", ["It parallelizes threads perfectly", "Only one thread executes Python bytecode at a time", "It disables threading", "It garbage-collects faster"], 1,
             skill="Python", topic="Concurrency", difficulty="hard",
             explanation="The Global Interpreter Lock serializes bytecode execution, limiting CPU-bound parallelism; multiprocessing bypasses it."),
        _mcq("Which construct creates a lazy sequence in Python?", ["List comprehension", "Generator expression", "Tuple literal", "Set literal"], 1,
             skill="Python", topic="Iterators", difficulty="medium",
             explanation="Generator expressions produce values lazily one at a time instead of materializing a list."),
    ],
    "javascript": [
        _mcq("What is the result of typeof null in JavaScript?", ['"null"', '"object"', '"undefined"', '"boolean"'], 1,
             skill="JavaScript", topic="Types", difficulty="medium",
             explanation='typeof null returns "object" due to a legacy quirk in the language.'),
        _mcq("Which keyword declares a block-scoped variable that cannot be reassigned?", ["var", "let", "const", "static"], 2,
             skill="JavaScript", topic="Variables", difficulty="easy",
             explanation="const declares block-scoped bindings that cannot be reassigned."),
        _mcq("What do Promises primarily solve?", ["Memory leaks", "Callback-based asynchronous flow", "DOM performance", "CSS specificity"], 1,
             skill="JavaScript", topic="Async", difficulty="medium",
             explanation="Promises flatten callback-based async flows and compose with async/await."),
        _mcq("In the event loop, which runs first: a resolved .then callback or setTimeout(fn, 0)?", ["setTimeout always first", "Resolved promise callbacks run before timers", "Both run simultaneously", "Order is undefined"], 1,
             skill="JavaScript", topic="Event Loop", difficulty="hard",
             explanation="Microtasks (promise callbacks) drain before the next macrotask (timers)."),
        _mcq("What does Array.prototype.reduce return?", ["A new array", "A single accumulated value", "undefined", "An iterator"], 1,
             skill="JavaScript", topic="Arrays", difficulty="medium",
             explanation="reduce folds the array into a single accumulated value using the provided reducer."),
    ],
    "sql": [
        _mcq("Which clause filters groups produced by GROUP BY?", ["WHERE", "HAVING", "ORDER BY", "LIMIT"], 1,
             skill="SQL", topic="Aggregation", difficulty="medium",
             explanation="HAVING filters aggregated groups; WHERE filters individual rows before grouping."),
        _mcq("An INNER JOIN returns:", ["All rows from both tables", "Only rows with matching keys in both tables", "All left-table rows", "Cartesian product"], 1,
             skill="SQL", topic="Joins", difficulty="easy",
             explanation="INNER JOIN keeps only rows where the join predicate matches in both tables."),
        _mcq("Which statement about indexes is TRUE?", ["Indexes always speed up writes", "Indexes speed reads but add write overhead", "Indexes are only for primary keys", "Indexes store full table copies"], 1,
             skill="SQL", topic="Indexing", difficulty="medium",
             explanation="Indexes accelerate lookups but every INSERT/UPDATE must also maintain them."),
        _mcq("What does ACID's 'D' guarantee?", ["Data is denormalized", "Committed transactions survive crashes", "Duplicate rows are impossible", "Deadlocks never occur"], 1,
             skill="SQL", topic="Transactions", difficulty="hard",
             explanation="Durability ensures once a transaction commits, its changes persist even across failures."),
        _mcq("Which window function assigns ranks without gaps after ties?", ["ROW_NUMBER()", "RANK()", "DENSE_RANK()", "NTILE()"], 2,
             skill="SQL", topic="Window Functions", difficulty="hard",
             explanation="DENSE_RANK gives tied rows equal rank and the next distinct value gets the immediately following rank (no gaps)."),
    ],
    "docker": [
        _mcq("What is the difference between an image and a container?", ["None", "An image is a read-only template; a container is a running instance", "Containers are stored in registries", "Images run processes"], 1,
             skill="Docker", topic="Fundamentals", difficulty="easy",
             explanation="Images are immutable templates layered to create runnable containers."),
        _mcq("Why use multi-stage Docker builds?", ["To run multiple apps", "To keep the final image small by excluding build tooling", "To increase cache size", "To enable GPU support"], 1,
             skill="Docker", topic="Builds", difficulty="medium",
             explanation="Multi-stage builds compile in one stage and copy only artifacts into a slim runtime stage."),
        _mcq("Which instruction executes at container start and accepts arguments appended via docker run?", ["RUN", "ENTRYPOINT", "FROM", "ENV"], 1,
             skill="Docker", topic="Dockerfile", difficulty="hard",
             explanation="ENTRYPOINT defines the executable; CMD supplies defaults that docker run args override."),
    ],
    "aws": [
        _mcq("Under the AWS shared responsibility model, who patches the guest OS on EC2?", ["AWS", "The customer", "Both equally", "Nobody"], 1,
             skill="AWS", topic="Security", difficulty="medium",
             explanation="AWS secures the underlying infrastructure; customers patch and secure the guest OS and applications."),
        _mcq("Which S3 storage class fits rarely-accessed archive data with retrieval delays?", ["S3 Standard", "S3 Glacier", "S3 Standard-IA", "EBS"], 1,
             skill="AWS", topic="Storage", difficulty="easy",
             explanation="Glacier is designed for archival with retrieval times from minutes to hours."),
        _mcq("What is the key difference between SQS and SNS?", ["SQS is push, SNS is pull", "SQS is message queueing (pull); SNS is pub/sub notification (push)", "They are identical", "SNS stores messages for weeks"], 1,
             skill="AWS", topic="Messaging", difficulty="medium",
             explanation="SQS queues messages for consumers to poll; SNS fans out notifications to subscribers."),
    ],
    "java": [
        _mcq("Which principle hides internal object details and exposes only necessary operations?", ["Inheritance", "Encapsulation", "Polymorphism", "Abstraction via interfaces only"], 1,
             skill="Java", topic="OOP", difficulty="easy",
             explanation="Encapsulation bundles state with methods and restricts direct field access."),
        _mcq("HashMap vs Hashtable: which statement is correct?", ["HashMap is synchronized", "HashMap is unsynchronized and allows null keys", "Hashtable allows null values", "They are identical"], 1,
             skill="Java", topic="Collections", difficulty="medium",
             explanation="HashMap is not synchronized and permits one null key; Hashtable synchronizes every method."),
        _mcq("What does the volatile keyword guarantee?", ["Atomic increments", "Visibility of writes across threads", "Lock acquisition", "Thread priority"], 1,
             skill="Java", topic="Concurrency", difficulty="hard",
             explanation="volatile establishes happens-before visibility; it does not make compound operations atomic."),
    ],
    "fastapi": [
        _mcq("How does FastAPI validate request bodies?", ["Runtime reflection only", "Pydantic models declared as endpoint parameters", "JSON Schema files", "Manual parsing"], 1,
             skill="FastAPI", topic="Validation", difficulty="easy",
             explanation="FastAPI uses Pydantic model type hints to parse and validate request payloads automatically."),
        _mcq("Defining an endpoint with async def means:", ["Requests run in a threadpool", "The endpoint runs on the event loop and should await I/O", "Responses are cached", "Blocking calls become safe"], 1,
             skill="FastAPI", topic="Async", difficulty="medium",
             explanation="async def endpoints run on the event loop; blocking calls there stall all requests."),
        _mcq("What is FastAPI's dependency injection used for?", ["Only authentication", "Sharing logic like DB sessions/auth across routes declaratively", "HTML templating", "Static files"], 1,
             skill="FastAPI", topic="DI", difficulty="medium",
             explanation="Depends() wires reusable components (sessions, auth, pagination) into endpoints."),
    ],
}

TECH_THEORY_MCQ: list[dict] = [
    _mcq("Which OS scheduling algorithm can cause starvation of long jobs?", ["Round Robin", "Shortest Job First", "FIFO", "Multilevel with aging"], 1,
         skill="Operating Systems", topic="Scheduling", difficulty="medium",
         explanation="SJF prioritizes short jobs, potentially starving longer ones; aging mitigates it."),
    _mcq("What does a deadlock require (Coffman conditions include)?", ["Preemption of all resources", "Circular wait", "Single process", "Guaranteed interrupts"], 1,
         skill="Operating Systems", topic="Concurrency", difficulty="hard",
         explanation="Deadlock requires mutual exclusion, hold-and-wait, no preemption and circular wait."),
    _mcq("Which TCP feature ensures reliable, ordered delivery?", ["Best-effort routing", "Sequence numbers and acknowledgments", "Broadcast addressing", "Checksum-only validation"], 1,
         skill="Networks", topic="TCP/IP", difficulty="medium",
         explanation="TCP uses sequence numbers, ACKs and retransmission for ordered reliable delivery."),
    _mcq("Which normalization form removes transitive dependencies?", ["1NF", "2NF", "3NF", "BCNF"], 2,
         skill="DBMS", topic="Normalization", difficulty="hard",
         explanation="3NF eliminates transitive dependencies of non-key attributes on the primary key."),
    _mcq("Which OOP concept lets different classes respond to the same method call differently?", ["Overloading only", "Polymorphism", "Encapsulation", "Composition"], 1,
         skill="OOP", topic="Principles", difficulty="easy",
         explanation="Polymorphism allows a shared interface with type-specific implementations."),
]

# ═══════════════════════════════════════════════════════════════════
# Parametric aptitude generators
# ═══════════════════════════════════════════════════════════════════


def _opts(correct_val: str, distractors: list[str]) -> tuple[list[str], int]:
    seen = {correct_val}
    uniq: list[str] = []
    for d in distractors:
        if d not in seen:
            seen.add(d)
            uniq.append(d)
    for filler in ("Cannot be determined", "None of these", "All of these"):
        if len(uniq) >= 3:
            break
        if filler not in seen:
            seen.add(filler)
            uniq.append(filler)
    options = [correct_val] + uniq[:3]
    order = list(range(len(options)))
    random.shuffle(order)
    shuffled = [options[i] for i in order]
    return shuffled, shuffled.index(correct_val)


def gen_percentage(rng: random.Random) -> dict:
    pct = rng.choice([10, 15, 20, 25, 40, 60])
    n = rng.randrange(200, 900, 50)
    ans = pct * n // 100
    text, correct = f"What is {pct}% of {n}?", str(ans)
    opts, ci = _opts(correct, [str(ans + rng.choice([-30, -20, 10, 20])), str(ans * 2), str(ans // 2)])
    return _mcq(text, opts, ci, skill="Quantitative", topic="Percentages", difficulty="easy",
                explanation=f"{pct}% of {n} = {pct}/100 × {n} = {ans}.", seconds=45)


def gen_profit_loss(rng: random.Random) -> dict:
    cp = rng.randrange(400, 1200, 50)
    profit = rng.choice([10, 15, 20, 25])
    sp = cp + cp * profit // 100
    text = f"An item bought for Rs.{cp} is sold for Rs.{sp}. What is the profit percentage?"
    correct = f"{profit}%"
    opts, ci = _opts(correct, [f"{profit - 5}%", f"{profit + 5}%", f"{profit + 10}%"])
    return _mcq(text, opts, ci, skill="Quantitative", topic="Profit & Loss", difficulty="easy",
                explanation=f"Profit = {sp}-{cp} = {sp-cp}; profit% = {(sp-cp)/cp*100:.0f}% = {profit}%.", seconds=60)


def gen_ratio(rng: random.Random) -> dict:
    a = rng.randrange(2, 6)
    b = rng.choice([x for x in range(2, 7) if x != a])
    unit = rng.randrange(100, 500, 50)
    total = (a + b) * unit
    share = a * unit
    text = f"Rs.{total} is divided between two people in the ratio {a}:{b}. How much does the FIRST person receive?"
    correct = f"Rs.{share}"
    opts, ci = _opts(correct, [
        f"Rs.{total}",
        f"Rs.{unit}",
        f"Rs.{(max(a, b) + 1) * unit}",
    ])
    return _mcq(text, opts, ci, skill="Quantitative", topic="Ratio", difficulty="easy",
                explanation=f"Total parts = {a}+{b} = {a+b}; each part = {total}/{a+b} = {unit}; first share = {a}×{unit} = {share}.", seconds=60)


def gen_average(rng: random.Random) -> dict:
    nums = [rng.randrange(10, 99) for _ in range(5)]
    avg = sum(nums) / 5
    text = f"The average of {', '.join(map(str, nums))} is closest to:"
    correct = f"{avg:.0f}"
    opts, ci = _opts(correct, [f"{avg + rng.randint(3, 9):.0f}", f"{avg - rng.randint(3, 9):.0f}", f"{sum(nums)}"])
    return _mcq(text, opts, ci, skill="Quantitative", topic="Average", difficulty="easy",
                explanation=f"Sum = {sum(nums)}; average = {sum(nums)}/5 = {avg}.", seconds=45)


def gen_time_work(rng: random.Random) -> dict:
    a = rng.choice([6, 8, 10, 12])
    b = rng.choice([12, 24, 24, 15])
    import math
    lcm = math.lcm(a, b)
    rate = lcm // a + lcm // b
    days = Fraction_str(lcm, rate)
    text = f"A completes a job in {a} days and B in {b} days. Working together, how many days will they take?"
    correct = days
    opts, ci = _opts(correct, [f"{a + b} days", f"{lcm} days", f"{rate} days"])
    return _mcq(text, opts, ci, skill="Quantitative", topic="Time & Work", difficulty="medium",
                explanation=f"LCM={lcm} units of work. Rates: {lcm//a}+{lcm//b}={rate}/day ⇒ {lcm}/{rate} days.", seconds=90)


def Fraction_str(num: int, den: int) -> str:
    import math
    g = math.gcd(num, den)
    n, d = num // g, den // g
    whole = n // d
    rem = n % d
    if rem == 0:
        return f"{whole} days"
    return f"{whole} {rem}/{d} days"


def gen_tsd(rng: random.Random) -> dict:
    speed = rng.choice([40, 50, 60, 72])
    time_h = rng.choice([2, 3, 5])
    dist = speed * time_h
    text = f"A train travels {dist} km in {time_h} hours. What is its average speed in km/h?"
    correct = str(speed)
    opts, ci = _opts(correct, [str(speed + 10), str(dist - time_h), str(speed - 8)])
    return _mcq(text, opts, ci, skill="Quantitative", topic="Time, Speed & Distance", difficulty="easy",
                explanation=f"Speed = distance/time = {dist}/{time_h} = {speed} km/h.", seconds=45)


def gen_probability(rng: random.Random) -> dict:
    kind = rng.choice(["die", "coins"])
    if kind == "die":
        target = rng.choice([4, 5, 6])
        correct = "1/6"
        text = f"What is the probability of rolling a {target} on a fair six-sided die?"
        expl = "One favorable face out of six equally likely faces."
    else:
        correct = "1/4"
        text = "Two fair coins are tossed. What is the probability of getting exactly two heads?"
        expl = "HH is one outcome among four equally likely outcomes."
    opts, ci = _opts(correct, ["1/2", "1/3", "2/3"] if kind == "die" else ["1/2", "3/4", "1/8"])
    return _mcq(text, opts, ci, skill="Quantitative", topic="Probability", difficulty="easy",
                explanation=expl, seconds=45)


def gen_perm_comb(rng: random.Random) -> dict:
    n, r = 5, 2
    import math
    val = math.perm(n, r)
    text = f"In how many ways can a president and a treasurer be chosen from a group of {n} people (distinct roles)?"
    correct = str(val)
    opts, ci = _opts(correct, [str(math.comb(n, r)), str(n * n), str(val * 2)])
    return _mcq(text, opts, ci, skill="Quantitative", topic="Permutation & Combination", difficulty="medium",
                explanation=f"P({n},{r}) = {n}×{n-1} = {val} (order matters for distinct roles).", seconds=60)


def gen_number_system(rng: random.Random) -> dict:
    d = rng.choice([7, 8, 9, 11])
    q = rng.randrange(30, 120)
    n = q * d + rng.randrange(1, d)
    correct_r = n % d
    text = f"What is the remainder when {n} is divided by {d}?"
    correct = str(correct_r)
    wrong = [(correct_r + 1) % d, (correct_r + 2) % d, (correct_r + 3) % d]
    opts, ci = _opts(correct, [str(w) for w in wrong])
    return _mcq(text, opts, ci, skill="Quantitative", topic="Number Systems", difficulty="easy",
                explanation=f"{n} = {d}×{n//d} + {correct_r}, so the remainder is {correct_r}.", seconds=45)


def gen_simple_interest(rng: random.Random) -> dict:
    p = rng.randrange(1000, 8000, 500)
    rate = rng.choice([5, 6, 8, 10])
    yrs = rng.choice([2, 3, 4])
    si = p * rate * yrs // 100
    text = f"Find the simple interest on Rs.{p} at {rate}% per annum for {yrs} years."
    correct = f"Rs.{si}"
    opts, ci = _opts(correct, [f"Rs.{si + p // 10}", f"Rs.{si * 2}", f"Rs.{si - 50}"])
    return _mcq(text, opts, ci, skill="Quantitative", topic="Simple Interest", difficulty="easy",
                explanation=f"SI = P×R×T/100 = {p}×{rate}×{yrs}/100 = Rs.{si}.", seconds=60)


def gen_compound_interest(rng: random.Random) -> dict:
    p = rng.choice([10000, 20000])
    rate = 10
    amt = int(p * (1.1) ** 2)
    ci = amt - p
    text = f"Find the compound interest on Rs.{p} at 10% per annum for 2 years, compounded annually."
    correct = f"Rs.{ci}"
    opts, ci = _opts(correct, [f"Rs.{amt - p // 100}", f"Rs.{p // 10}", f"Rs.{ci + 500}"])
    return _mcq(text, opts, ci, skill="Quantitative", topic="Compound Interest", difficulty="medium",
                explanation=f"Amount = {p}×1.1² = Rs.{amt}; CI = {amt}-{p} = Rs.{ci}.", seconds=90)


def gen_data_interpretation(rng: random.Random) -> dict:
    sales = {"Mon": rng.randrange(40, 90, 10), "Tue": rng.randrange(40, 90, 10), "Wed": rng.randrange(40, 90, 10)}
    total = sum(sales.values())
    best = max(sales, key=lambda k: sales[k])
    lines = "\n".join(f"  {k}: {v} units" for k, v in sales.items())
    text = f"A shop records these daily sales:\n{lines}\nWhat are the TOTAL units sold over the three days?"
    correct = str(total)
    opts, ci = _opts(correct, [str(total + 20), str(total - 10), str(max(sales.values()))])
    return _mcq(text, opts, ci, skill="Quantitative", topic="Data Interpretation", difficulty="easy",
                explanation=f"Total = {'+'.join(str(v) for v in sales.values())} = {total} (peak day: {best}).", seconds=75)


QUANT_GENERATORS: dict[str, Callable[[random.Random], dict]] = {
    "percentages": gen_percentage,
    "profit_loss": gen_profit_loss,
    "ratio": gen_ratio,
    "average": gen_average,
    "time_work": gen_time_work,
    "tsd": gen_tsd,
    "probability": gen_probability,
    "permutation_combination": gen_perm_comb,
    "number_system": gen_number_system,
    "simple_interest": gen_simple_interest,
    "compound_interest": gen_compound_interest,
    "data_interpretation": gen_data_interpretation,
}


# ─── Logical reasoning ──────────────────────────────────────────────


def gen_number_series(rng: random.Random) -> dict:
    kind = rng.choice(["arith", "geo", "fib"])
    if kind == "arith":
        start, step = rng.randrange(2, 12), rng.randrange(3, 9)
        seq = [start + step * i for i in range(5)]
        nxt = seq[-1] + step
        expl = f"Arithmetic progression adding {step} each step."
    elif kind == "geo":
        start, ratio = rng.randrange(2, 5), 2
        seq = [start * ratio**i for i in range(5)]
        nxt = seq[-1] * ratio
        expl = f"Geometric progression multiplying by {ratio}."
    else:
        a, b = rng.randrange(1, 4), rng.randrange(2, 6)
        seq = [a, b]
        for _ in range(3):
            seq.append(seq[-1] + seq[-2])
        nxt = seq[-1] + seq[-2]
        expl = "Each term is the sum of the previous two (Fibonacci-style)."
    text = f"Find the next number in the series: {', '.join(map(str, seq))}, ?"
    correct = str(nxt)
    opts, ci = _opts(correct, [str(nxt + rng.randint(1, 4)), str(nxt - rng.randint(1, 4)), str(seq[-1])])
    return _mcq(text, opts, ci, skill="Logical Reasoning", topic="Number Series", difficulty="medium",
                explanation=expl, seconds=75)


def gen_coding_decoding(rng: random.Random) -> dict:
    words = [("CAT", "DBU"), ("DOG", "EPH"), ("SUN", "TVO"), ("BIRD", "CJSE"), ("LAMP", "MBNQ")]
    shift = 1
    src, coded = rng.choice(words)
    text = f'In a certain code, "{src}" is written as "{coded}". How is "MIND" written in that code?'
    mind = "".join(chr(ord(c) + shift) for c in "MIND")
    correct = mind
    wrong = {"".join(chr(ord(c) + 2) for c in "MIND"), "MIND"[::-1], "".join(chr(ord(c) - 1) for c in "MIND")}
    opts, ci = _opts(correct, list(wrong)[:3])
    return _mcq(text, opts, ci, skill="Logical Reasoning", topic="Coding-Decoding", difficulty="easy",
                explanation=f"Each letter shifts forward by {shift}: M→{mind[0]}, I→{mind[1]}, N→{mind[2]}, D→{mind[3]}.", seconds=60)


LOGICAL_CURATED: list[dict] = [
    _mcq("Pointing to a photo, Ravi said, 'She is the daughter of my grandfather's only son.' How is the girl related to Ravi?",
         ["Cousin", "Sister", "Aunt", "Niece"], 1,
         skill="Logical Reasoning", topic="Blood Relations", difficulty="medium",
         explanation="Grandfather's only son is Ravi's father; his daughter is Ravi's sister."),
    _mcq("A man walks 3 km north, turns right and walks 4 km. How far is he from the starting point?",
         ["7 km", "5 km", "1 km", "12 km"], 1,
         skill="Logical Reasoning", topic="Directions", difficulty="easy",
         explanation="√(3²+4²)=5 km (Pythagoras)."),
    _mcq("Statements: All pens are books. Some books are red. Conclusions: I. Some pens are red. II. All books are pens.",
         ["Only I follows", "Only II follows", "Both follow", "Neither follows"], 3,
         skill="Logical Reasoning", topic="Syllogisms", difficulty="medium",
         explanation="Neither conclusion necessarily follows from the premises."),
    _mcq("Statement: 'The new policy will reduce costs.' Assumption: The policy is implemented correctly.",
         ["Not assumed", "Implicitly assumed", "Contradicted", "Irrelevant assumption"], 1,
         skill="Logical Reasoning", topic="Statement & Assumptions", difficulty="medium",
         explanation="Cost reduction presumes proper implementation, making it an implicit assumption."),
    _mcq("Five friends sit in a row. P is left of Q but right of R. S sits at the far right. T sits between P and Q. Who sits in the middle?",
         ["P", "Q", "T", "R"], 2,
         skill="Logical Reasoning", topic="Seating Arrangement", difficulty="medium",
         explanation="Arrangement R-P-T-Q-S places T exactly in the middle (third position)."),
    _mcq("If in a code language 'FLOWER' is coded by reversing its letters, how is 'GARDEN' coded?",
         ["NEDRAG", "GARDEN", "DRAGEN", "NEDGRA"], 0,
         skill="Logical Reasoning", topic="Coding-Decoding", difficulty="easy",
         explanation="'GARDEN' reversed letter-by-letter becomes 'NEDRAG'."),
    _mcq("Complete the analogy: Book : Author :: Painting : ?",
         ["Canvas", "Artist", "Gallery", "Brush"], 1,
         skill="Logical Reasoning", topic="Analogy", difficulty="easy",
         explanation="An author creates a book just as an artist creates a painting."),
]

VERBAL_CURATED: list[dict] = [
    _mcq("Choose the synonym for 'UBIQUITOUS':",
         ["Rare", "Omnipresent", "Unique", "Obsolete"], 1,
         skill="Verbal", topic="Vocabulary", difficulty="medium",
         explanation="Ubiquitous means existing everywhere at once."),
    _mcq("Choose the antonym for 'SCARCITY':",
         ["Shortage", "Abundance", "Deficit", "Want"], 1,
         skill="Verbal", topic="Vocabulary", difficulty="easy",
         explanation="Scarcity (short supply) is opposite to abundance."),
    _mcq("Select the grammatically correct sentence:",
         ["He don't like coffee.", "He doesn't likes coffee.", "He doesn't like coffee.", "He not like coffee."], 2,
         skill="Verbal", topic="Grammar", difficulty="easy",
         explanation="Third person singular takes 'doesn't' + base verb ('like')."),
    _mcq("Identify the misused word: 'The principal effect of the medicine was drowsiness, effecting her ability to drive.'",
         ["principal", "effecting", "ability", "drowsiness"], 1,
         skill="Verbal", topic="Sentence Correction", difficulty="medium",
         explanation="'Effecting' is wrong here; the sentence needs 'affecting' (to influence)."),
    _mcq("Arrange: (P) the meeting (Q) despite (R) heavy traffic (S) she attended",
         ["S-Q-R-P", "S-P-Q-R", "Q-S-P-R", "R-Q-S-P"], 1,
         skill="Verbal", topic="Para Jumbles", difficulty="medium",
         explanation="'Despite heavy traffic she attended the meeting' is the coherent ordering."),
]


# ═══════════════════════════════════════════════════════════════════
# Coding problems — Python problems ship executable reference
# solutions + runnable test cases; other languages are graded with
# structural heuristics when no sandbox runtime is available.
# ═══════════════════════════════════════════════════════════════════

CODING_PROBLEMS: dict[str, list[dict]] = {
    "easy": [
        {
            "title": "Two Sum",
            "language": "python",
            "topics": ["arrays", "hash maps"],
            "description": (
                "Given an integer array `nums` and an integer `target`, return the indices of the two "
                "numbers that add up to `target`. Exactly one solution exists.\n\n"
                "Function signature: `def two_sum(nums, target)`"
            ),
            "starter_code": "def two_sum(nums, target):\n    # Write your solution here\n    pass\n",
            "reference_solution": (
                "def two_sum(nums, target):\n"
                "    seen = {}\n"
                "    for i, n in enumerate(nums):\n"
                "        if target - n in seen:\n"
                "            return [seen[target - n], i]\n"
                "        seen[n] = i\n"
                "    return []\n"
            ),
            "test_cases": [
                {"args": [[2, 7, 11, 15], 9], "expected": [0, 1]},
                {"args": [[3, 2, 4], 6], "expected": [1, 2]},
                {"args": [[3, 3], 6], "expected": [0, 1]},
                {"args": [[1, 5, 9], 100], "expected": []},
            ],
        },
        {
            "title": "Reverse String",
            "language": "python",
            "topics": ["strings", "two pointers"],
            "description": "Return the input string reversed.\n\nFunction signature: `def reverse_string(s)`",
            "starter_code": "def reverse_string(s):\n    pass\n",
            "reference_solution": "def reverse_string(s):\n    return s[::-1]\n",
            "test_cases": [
                {"args": ["hello"], "expected": "olleh"},
                {"args": ["abcd"], "expected": "dcba"},
                {"args": [""], "expected": ""},
            ],
        },
        {
            "title": "Palindrome Check",
            "language": "python",
            "topics": ["strings"],
            "description": (
                "Return True if the input string reads the same forwards and backwards "
                "(case-sensitive), else False.\n\nFunction signature: `def is_palindrome(s)`"
            ),
            "starter_code": "def is_palindrome(s):\n    pass\n",
            "reference_solution": "def is_palindrome(s):\n    return s == s[::-1]\n",
            "test_cases": [
                {"args": ["racecar"], "expected": True},
                {"args": ["hello"], "expected": False},
                {"args": ["a"], "expected": True},
            ],
        },
        {
            "title": "Missing Number",
            "language": "python",
            "topics": ["arrays", "math"],
            "description": (
                "Given a list containing n distinct numbers taken from 0..n, return the missing one.\n\n"
                "Function signature: `def missing_number(nums)`"
            ),
            "starter_code": "def missing_number(nums):\n    pass\n",
            "reference_solution": (
                "def missing_number(nums):\n"
                "    n = len(nums)\n"
                "    return n * (n + 1) // 2 - sum(nums)\n"
            ),
            "test_cases": [
                {"args": [[3, 0, 1]], "expected": 2},
                {"args": [[0, 1]], "expected": 2},
                {"args": [[1]], "expected": 0},
            ],
        },
    ],
    "medium": [
        {
            "title": "Valid Parentheses",
            "language": "python",
            "topics": ["stacks", "strings"],
            "description": (
                "Given a string of brackets '()[]{}', return True if it is valid — every opening bracket "
                "is closed by the same type in the correct order.\n\n"
                "Function signature: `def is_valid_parentheses(s)`"
            ),
            "starter_code": "def is_valid_parentheses(s):\n    pass\n",
            "reference_solution": (
                "def is_valid_parentheses(s):\n"
                "    pairs = {')': '(', ']': '[', '}': '{'}\n"
                "    stack = []\n"
                "    for ch in s:\n"
                "        if ch in '([{':\n"
                "            stack.append(ch)\n"
                "        elif not stack or stack.pop() != pairs[ch]:\n"
                "            return False\n"
                "    return not stack\n"
            ),
            "test_cases": [
                {"args": ["()[]{}"], "expected": True},
                {"args": ["([)]"], "expected": False},
                {"args": ["{[]}"], "expected": True},
                {"args": ["("], "expected": False},
            ],
        },
        {
            "title": "Binary Search",
            "language": "python",
            "topics": ["searching", "arrays"],
            "description": (
                "Implement binary search on a sorted list. Return the index of `target` or -1 if absent.\n\n"
                "Function signature: `def binary_search(nums, target)`"
            ),
            "starter_code": "def binary_search(nums, target):\n    pass\n",
            "reference_solution": (
                "def binary_search(nums, target):\n"
                "    lo, hi = 0, len(nums) - 1\n"
                "    while lo <= hi:\n"
                "        mid = (lo + hi) // 2\n"
                "        if nums[mid] == target:\n"
                "            return mid\n"
                "        if nums[mid] < target:\n"
                "            lo = mid + 1\n"
                "        else:\n"
                "            hi = mid - 1\n"
                "    return -1\n"
            ),
            "test_cases": [
                {"args": [[1, 3, 5, 7, 9], 5], "expected": 2},
                {"args": [[1, 3, 5, 7, 9], 4], "expected": -1},
                {"args": [[], 1], "expected": -1},
            ],
        },
        {
            "title": "Maximum Subarray Sum (Kadane)",
            "language": "python",
            "topics": ["dynamic programming", "arrays"],
            "description": (
                "Find the largest sum of any contiguous subarray.\n\n"
                "Function signature: `def max_subarray_sum(nums)`"
            ),
            "starter_code": "def max_subarray_sum(nums):\n    pass\n",
            "reference_solution": (
                "def max_subarray_sum(nums):\n"
                "    best = cur = nums[0]\n"
                "    for n in nums[1:]:\n"
                "        cur = max(n, cur + n)\n"
                "        best = max(best, cur)\n"
                "    return best\n"
            ),
            "test_cases": [
                {"args": [[-2, 1, -3, 4, -1, 2, 1, -5, 4]], "expected": 6},
                {"args": [[5, 4, -1, 7, 8]], "expected": 23},
                {"args": [[-3, -1, -2]], "expected": -1},
            ],
        },
        {
            "title": "Merge Intervals",
            "language": "python",
            "topics": ["sorting", "arrays"],
            "description": (
                "Given a list of intervals [start, end], merge all overlapping intervals and return them "
                "sorted by start.\n\nFunction signature: `def merge_intervals(intervals)`"
            ),
            "starter_code": "def merge_intervals(intervals):\n    pass\n",
            "reference_solution": (
                "def merge_intervals(intervals):\n"
                "    out = []\n"
                "    for iv in sorted(intervals):\n"
                "        if out and iv[0] <= out[-1][1]:\n"
                "            out[-1][1] = max(out[-1][1], iv[1])\n"
                "        else:\n"
                "            out.append(list(iv))\n"
                "    return out\n"
            ),
            "test_cases": [
                {"args": [[[1, 3], [2, 6], [8, 10], [15, 18]]], "expected": [[1, 6], [8, 10], [15, 18]]},
                {"args": [[[1, 4], [4, 5]]], "expected": [[1, 5]]},
                {"args": [[]], "expected": []},
            ],
        },
    ],
    "hard": [
        {
            "title": "Coin Change",
            "language": "python",
            "topics": ["dynamic programming"],
            "description": (
                "Given coin denominations and an amount, return the FEWEST coins needed to make that "
                "amount, or -1 if impossible.\n\nFunction signature: `def coin_change(coins, amount)`"
            ),
            "starter_code": "def coin_change(coins, amount):\n    pass\n",
            "reference_solution": (
                "def coin_change(coins, amount):\n"
                "    dp = [0] + [float('inf')] * amount\n"
                "    for c in coins:\n"
                "        for x in range(c, amount + 1):\n"
                "            dp[x] = min(dp[x], dp[x - c] + 1)\n"
                "    return dp[amount] if dp[amount] != float('inf') else -1\n"
            ),
            "test_cases": [
                {"args": [[1, 2, 5], 11], "expected": 3},
                {"args": [[2], 3], "expected": -1},
                {"args": [[1], 0], "expected": 0},
            ],
        },
        {
            "title": "Longest Substring Without Repeating Characters",
            "language": "python",
            "topics": ["sliding window", "hash maps"],
            "description": (
                "Return the length of the longest substring without repeating characters.\n\n"
                "Function signature: `def length_of_longest_substring(s)`"
            ),
            "starter_code": "def length_of_longest_substring(s):\n    pass\n",
            "reference_solution": (
                "def length_of_longest_substring(s):\n"
                "    last, start, best = {}, 0, 0\n"
                "    for i, ch in enumerate(s):\n"
                "        if ch in last and last[ch] >= start:\n"
                "            start = last[ch] + 1\n"
                "        last[ch] = i\n"
                "        best = max(best, i - start + 1)\n"
                "    return best\n"
            ),
            "test_cases": [
                {"args": ["abcabcbb"], "expected": 3},
                {"args": ["bbbbb"], "expected": 1},
                {"args": ["pwwkew"], "expected": 3},
                {"args": [""], "expected": 0},
            ],
        },
        {
            "title": "Longest Increasing Subsequence",
            "language": "python",
            "topics": ["dynamic programming", "binary search"],
            "description": (
                "Return the LENGTH of the longest strictly increasing subsequence.\n\n"
                "Function signature: `def length_of_lis(nums)`"
            ),
            "starter_code": "def length_of_lis(nums):\n    pass\n",
            "reference_solution": (
                "import bisect\n"
                "def length_of_lis(nums):\n"
                "    tails = []\n"
                "    for n in nums:\n"
                "        i = bisect.bisect_left(tails, n)\n"
                "        if i == len(tails):\n"
                "            tails.append(n)\n"
                "        else:\n"
                "            tails[i] = n\n"
                "    return len(tails)\n"
            ),
            "test_cases": [
                {"args": [[10, 9, 2, 5, 3, 7, 101, 18]], "expected": 4},
                {"args": [[0, 1, 0, 3, 2, 3]], "expected": 4},
                {"args": [[7, 7, 7]], "expected": 1},
            ],
        },
    ],
}

CODING_CONCEPTUAL: dict[str, list[dict]] = {
    "javascript": [
        {
            "title": "Implement debounce",
            "language": "javascript",
            "topics": ["async", "timers"],
            "description": (
                "Write a `debounce(fn, delay)` function in JavaScript that delays invoking `fn` until "
                "`delay` ms have elapsed since the last call."
            ),
            "starter_code": "function debounce(fn, delay) {\n  // your code\n}\n",
            "keywords": ["settimeout", "cleartimeout", "return"],
        },
    ],
    "java": [
        {
            "title": "Thread-safe Singleton",
            "language": "java",
            "topics": ["oop", "multithreading"],
            "description": "Write a thread-safe singleton class in Java and explain how double-checked locking works.",
            "starter_code": "// your Java singleton here\n",
            "keywords": ["private", "static", "synchronized", "getinstance"],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════
# Debugging questions — intentionally broken code + grading keywords
# ═══════════════════════════════════════════════════════════════════

DEBUG_QUESTIONS: list[dict] = [
    {
        "skill": "Python",
        "topic": "Loops & Accumulation",
        "difficulty": "easy",
        "buggy_code": (
            "def average(numbers):\n"
            "    total = 0\n"
            "    for n in numbers:\n"
            "        total = n   # something feels wrong\n"
            "    return total / len(numbers)\n"
        ),
        "question_text": (
            "The function below should return the average of a list but always returns wrong values. "
            "Identify the bug, explain why it happens, and provide corrected code."
        ),
        "correct_answer": {"keywords": ["total = n", "+=", "sum(", "accumulate"]},
        "explanation": "`total = n` overwrites the accumulator each iteration instead of adding; use `total += n`.",
    },
    {
        "skill": "Python",
        "topic": "Default Arguments",
        "difficulty": "medium",
        "buggy_code": (
            "def add_item(item, items=[]):\n"
            "    items.append(item)\n"
            "    return items\n"
            "\n"
            "print(add_item(1))  # [1]\n"
            "print(add_item(2))  # expected [2], got ???\n"
        ),
        "question_text": "Why does the second call print [1, 2]? Identify the issue and fix it.",
        "correct_answer": {"keywords": ["mutable default", "shared", "none", "evaluated once"]},
        "explanation": "Mutable default arguments are evaluated once at definition time and shared across calls; default to None and create a new list inside.",
    },
    {
        "skill": "React",
        "topic": "Hooks Dependencies",
        "difficulty": "medium",
        "buggy_code": (
            "const [count, setCount] = useState(0);\n"
            "\n"
            "useEffect(() => {\n"
            "    const id = setInterval(() => setCount(count + 1), 1000);\n"
            "    return () => clearInterval(id);\n"
            "}, []);   // empty dependency array\n"
        ),
        "question_text": (
            "This React component's timer always increments count from 0 to 1 and stops. "
            "Identify the bug and provide a fix."
        ),
        "correct_answer": {"keywords": ["closure", "stale", "[count]", "prev"]},
        "explanation": "The interval callback closes over stale `count`; fix with a functional update `setCount(c => c + 1)` or add `[count]` to dependencies.",
    },
]


# ═══════════════════════════════════════════════════════════════════
# Code output prediction — snippets verified against real runtimes
# ═══════════════════════════════════════════════════════════════════

OUTPUT_PREDICTION: list[dict] = [
    {
        "language": "python",
        "snippet": "nums = [i * i for i in range(4)]\nprint(nums)",
        "output": "[0, 1, 4, 9]",
        "topic": "List Comprehensions",
        "difficulty": "easy",
        "explanation": "range(4) yields 0-3; squaring gives [0, 1, 4, 9].",
    },
    {
        "language": "python",
        "snippet": "s = 'interview'\nprint(s[2:5])",
        "output": "ter",
        "topic": "String Slicing",
        "difficulty": "easy",
        "explanation": "Slice [2:5] takes indices 2,3,4 -> 'ter'.",
    },
    {
        "language": "python",
        "snippet": "x = [10, 20, 30]\nx.append(x.pop())\nprint(x)",
        "output": "[10, 20, 30]",
        "topic": "Lists",
        "difficulty": "medium",
        "explanation": "pop() removes 30 then append() re-adds it, leaving the list unchanged.",
    },
    {
        "language": "javascript",
        "snippet": "console.log(typeof null);",
        "output": "object",
        "topic": "Types",
        "difficulty": "medium",
        'explanation': 'A historical quirk: typeof null reports "object".',
    },
    {
        "language": "javascript",
        "snippet": "console.log([1, 2, 3].map(x => x * 2).join('-'));",
        "output": "2-4-6",
        "topic": "Array Methods",
        "difficulty": "medium",
        "explanation": "map doubles elements then join joins with '-'.",
    },
]


# ═══════════════════════════════════════════════════════════════════
# SQL assessment — sample database + questions with reference queries.
# Candidate queries are executed on an isolated in-memory SQLite DB
# seeded with this schema/data and compared against reference output.
# ═══════════════════════════════════════════════════════════════════

SQL_SCHEMA_STATEMENTS: list[str] = [
    "CREATE TABLE departments (id INTEGER PRIMARY KEY, name TEXT NOT NULL)",
    """INSERT INTO departments VALUES
        (1, 'Engineering'), (2, 'Sales'), (3, 'Marketing'), (4, 'Finance')""",
    "CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT NOT NULL, department_id INTEGER, salary INTEGER, hired_year INTEGER)",
    """INSERT INTO employees VALUES
        (1, 'Asha',  1, 90000, 2019),
        (2, 'Bilal', 1, 75000, 2021),
        (3, 'Chen',  2, 60000, 2020),
        (4, 'Divya', 2, 65000, 2022),
        (5, 'Emil',  3, 55000, 2023),
        (6, 'Farah', 1, 95000, 2018),
        (7, 'Gopal', 4, 70000, 2021)""",
]

SQL_QUESTIONS: list[dict] = [
    {
        "title": "Filter rows (WHERE)",
        "topic": "SELECT / WHERE",
        "difficulty": "easy",
        "question_text": "Write a query returning the names of all employees in department id 1, sorted alphabetically.",
        "reference_query": "SELECT name FROM employees WHERE department_id = 1 ORDER BY name",
    },
    {
        "title": "Join departments",
        "topic": "JOIN",
        "difficulty": "easy",
        "question_text": "Write a query returning each employee's name together with their department name (columns: name, department).",
        "reference_query": (
            "SELECT e.name AS name, d.name AS department "
            "FROM employees e JOIN departments d ON e.department_id = d.id ORDER BY e.name"
        ),
    },
    {
        "title": "High-paying departments",
        "topic": "GROUP BY / HAVING",
        "difficulty": "medium",
        "question_text": "Write a query returning the names of departments whose average employee salary exceeds 70000.",
        "reference_query": (
            "SELECT d.name FROM departments d JOIN employees e ON e.department_id = d.id "
            "GROUP BY d.name HAVING AVG(e.salary) > 70000 ORDER BY d.name"
        ),
    },
    {
        "title": "Above company average",
        "topic": "Subqueries",
        "difficulty": "medium",
        "question_text": "Write a query returning the names of employees who earn more than the company-wide average salary, sorted by salary descending.",
        "reference_query": (
            "SELECT name FROM employees WHERE salary > "
            "(SELECT AVG(salary) FROM employees) ORDER BY salary DESC"
        ),
    },
    {
        "title": "Second highest salary",
        "topic": "LIMIT / OFFSET",
        "difficulty": "medium",
        "question_text": "Write a query returning the single second-highest distinct salary value.",
        "reference_query": "SELECT DISTINCT salary FROM employees ORDER BY salary DESC LIMIT 1 OFFSET 1",
    },
    {
        "title": "Salary rank per department",
        "topic": "Window Functions",
        "difficulty": "hard",
        "question_text": (
            "Using a window function, write a query that returns employee names with their salary rank within their "
            "department (rank 1 = highest salary). Columns: name, dept_rank. Order by name."
        ),
        "reference_query": (
            "WITH ranked AS (SELECT name, DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) AS dept_rank "
            "FROM employees) SELECT name, dept_rank FROM ranked WHERE dept_rank <= 2 ORDER BY name"
        ),
    },
]

SQL_MCQ_BANK: list[dict] = TECHNICAL_MCQ["sql"]


# ═══════════════════════════════════════════════════════════════════
# System design / scenario / case study — rubric-keyword grading
# ═══════════════════════════════════════════════════════════════════

SYSTEM_DESIGN_PROMPTS: dict[str, list[dict]] = {
    "medium": [
        {
            "prompt": "Design a URL shortening service like bit.ly. Cover API design, data model, ID generation, redirects, caching, and analytics.",
            "rubric": ["api", "database", "hash", "cache", "redirect", "scale", "read/write"],
        },
        {
            "prompt": "Design a real-time chat application supporting group chats, delivery receipts and offline messages.",
            "rubric": ["websocket", "message queue", "storage", "presence", "delivery", "offline"],
        },
        {
            "prompt": "Design a notification system that can push email/SMS/push notifications at a rate of 10M/day.",
            "rubric": ["queue", "worker", "template", "retry", "deduplication", "rate limit"],
        },
    ],
    "hard": [
        {
            "prompt": "Design a food delivery system like Swiggy/Zomato covering ordering, live tracking, dispatch and payments.",
            "rubric": ["geo", "matching", "queue", "payment", "consistency", "tracking"],
        },
        {
            "prompt": "Design an e-commerce platform backend supporting catalog search, cart, checkout and inventory reservation.",
            "rubric": ["search index", "cart", "inventory", "transaction", "cache", "idempotent"],
        },
        {
            "prompt": "Design a video streaming platform like YouTube: upload pipeline, transcoding, CDN delivery and recommendations hook.",
            "rubric": ["upload", "transcode", "cdn", "storage", "adaptive bitrate", "metadata"],
        },
    ],
}

SCENARIO_BANK: list[dict] = [
    {
        "skill": "Backend",
        "topic": "Production Incident",
        "difficulty": "medium",
        "question_text": (
            "Your REST API starts timing out in production after a routine deploy; CPU is normal but connection "
            "counts spike. Walk through your diagnosis and mitigation step by step."
        ),
        "rubric": ["logs", "metrics", "rollback", "connection pool", "database", "monitoring", "root cause"],
    },
    {
        "skill": "Data",
        "topic": "Slow Query",
        "difficulty": "medium",
        "question_text": "A dashboard query that took 200ms now takes 40s after data growth. How do you diagnose and fix it?",
        "rubric": ["explain", "index", "query plan", "partition", "denormalize", "cache"],
    },
    {
        "skill": "Architecture",
        "topic": "Migration",
        "difficulty": "hard",
        "question_text": "Describe how you would migrate a monolith's user table (50M rows) to a new schema with zero downtime.",
        "rubric": ["dual write", "backfill", "migration", "flag", "cutover", "rollback"],
    },
]

CASE_STUDY_BANK: list[dict] = [
    {
        "skill": "Product Engineering",
        "topic": "Scaling Decision",
        "difficulty": "medium",
        "question_text": (
            "Case: A startup's monolith handles 100k requests/day fine but growth projections show 50x in 12 months. "
            "The team is 4 engineers. Recommend an architecture evolution plan with trade-offs at each stage."
        ),
        "rubric": ["bottleneck", "phased", "trade-off", "team size", "database", "cache", "monitoring"],
    },
    {
        "skill": "Engineering Management",
        "topic": "Quality vs Speed",
        "difficulty": "hard",
        "question_text": (
            "Case: Marketing promises a feature in 2 weeks. Engineering estimates 6 weeks including tests. "
            "As tech lead, what do you do? Outline negotiation, risk assessment and shipping strategy."
        ),
        "rubric": ["scope", "risk", "feature flag", "testing", "stakeholder", "incremental"],
    },
]

SITUATIONAL_JUDGMENT_BANK: list[dict] = [
    {
        "skill": "Judgment",
        "topic": "Deadline Pressure",
        "difficulty": "medium",
        "question_text": (
            "You discover a teammate hard-coded credentials into the repo two days before a release demo. "
            "What do you do, in order?"
        ),
        "rubric": ["rotate", "revoke", "secret manager", "notify", "git history", "priority"],
    },
    {
        "skill": "Judgment",
        "topic": "Ambiguous Requirements",
        "difficulty": "medium",
        "question_text": (
            "A stakeholder gives you conflicting requirements verbally and by email. The deadline is near. "
            "How do you proceed?"
        ),
        "rubric": ["clarify", "written", "prioritize", "assumption", "confirm", "escalate"],
    },
]


def build_resume_questions(projects: list[str], skills: list[str], experiences: list[str]) -> list[dict]:
    """Resume/project-based question templates personalized to candidate context."""
    out: list[dict] = []
    for proj in projects[:3]:
        out.append({
            "skill": skills[0] if skills else "General",
            "topic": "Project Deep-Dive",
            "difficulty": "medium",
            "question_text": (
                f"Walk us through the architecture of your project '{proj}'. What were the key technical "
                "challenges, what trade-offs did you make, and how would you scale it 10x?"
            ),
            "correct_answer": {"rubric": ["architecture", "challenge", "trade-off", "scale"]},
        })
    if skills:
        sk = ", ".join(skills[:3])
        out.append({
            "skill": skills[0],
            "topic": "Technology Depth",
            "difficulty": "hard",
            "question_text": (
                f"Your resume lists {sk}. Pick the one you know best and explain its internals or advanced "
                "concepts you have used in production."
            ),
            "correct_answer": {"rubric": ["internals", "advanced", "production", "example"]},
        })
    for exp in experiences[:2]:
        out.append({
            "skill": "Experience",
            "topic": "Role Impact",
            "difficulty": "medium",
            "question_text": f"At '{exp}', what was the most impactful technical decision you owned and why?",
            "correct_answer": {"rubric": ["decision", "impact", "metric", "ownership"]},
        })
    return out


def behavioral_pool(difficulty: str) -> list[dict]:
    """Reuse the existing interview module's behavioral pool (no duplication)."""
    items = QuestionGenerator._BEHAVIORAL_QUESTIONS.get(difficulty, QuestionGenerator._BEHAVIORAL_QUESTIONS["medium"])
    return [
        {
            "skill": "Behavioral",
            "topic": "Behavioral",
            "difficulty": difficulty,
            "question_text": q,
            "correct_answer": {"rubric": ["situation", "action", "result", "reflection"]},
        }
        for q in items
    ]


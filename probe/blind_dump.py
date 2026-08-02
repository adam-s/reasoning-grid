"""Print a slice of the blind worklist for classification. Disposable."""
import json, sys

w = json.load(open("derived/blind-worklist.json"))
a, b = int(sys.argv[1]), int(sys.argv[2])
for it in w[a:b]:
    print(f"### {it['n']} {it['id']}")
    print(f"  [-2] {it['prev2'][:140]}")
    print(f"  [-1] {it['prev1'][:140]}")
    print(f"  >>>> {it['target'][:400]}")
    print(f"  [+1] {it['next1'][:140]}")
    print(f"  [+2] {it['next2'][:140]}")
    print()

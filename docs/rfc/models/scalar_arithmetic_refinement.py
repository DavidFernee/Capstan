# Scalar arithmetic refinement: executable finite reference model
# External verification only; neither implementation nor normative evaluator.
from itertools import product
MIN, MAX = -(2**63), 2**63-1
OPS = ("+", "-", "*", "/", "%")
def source(op, a, b):
    if op in ("/", "%"):
        if b == 0: return ("trap", "division_by_zero")
        q = (abs(a)//abs(b)) * (-1 if (a<0) != (b<0) else 1)
        n = q if op == "/" else a-q*b
    else:
        n = {"+": lambda: a+b, "-": lambda: a-b, "*": lambda: a*b}[op]()
    return ("value", n) if MIN <= n <= MAX else ("trap", "integer_overflow")

def target(op, a, b, mutant=False):
    # Independently expressed checked arithmetic, not actual CCAM evaluator.
    if op in ("/", "%"):
        if b == 0: return ("trap", "division_by_zero")
        if a == MIN and b == -1:
            if op == "/" or mutant: return ("trap", "integer_overflow")
            return ("value", 0)
        q, r = divmod(a,b)
        if r != 0 and (a<0) != (b<0): q += 1
        return ("value", q if op == "/" else a-q*b)
    if op == "+": n = a+b
    elif op == "-": n = a-b
    else: n = a*b
    if not MIN <= n <= MAX: return ("trap", "integer_overflow")
    return ("value", n)

def run():
    domain = sorted(set(range(-16,17)) | {MIN,MIN+1,MAX-1,MAX,-2**32,2**32})
    cases = 0
    witnesses = []
    for op,a,b in product(OPS,domain,domain):
        expected = source(op,a,b)
        assert expected == target(op,a,b), (op,a,b,expected,target(op,a,b))
        if expected != target(op,a,b,True): witnesses.append((op,a,b))
        cases += 1
    assert witnesses == [("%",MIN,-1)], witnesses
    print(f"scalar operand domain: {len(domain)}; cases: {cases}; mismatches: 0")
    print(f"mutant witnesses: {witnesses}")
if __name__ == "__main__": run()

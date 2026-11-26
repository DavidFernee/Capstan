from collections import deque
# State: epoch, live, queued epoch (-1 absent), remaining, reserved, spent, effects
# One object, one unit per request, bounded epoch and capacity.
def edges(s, fixed):
 e,l,q,b,r,w,f=s
 if l and q==-1 and b: yield 'enqueue',(e,l,e,b-1,r+1,w,f)
 if l: yield 'revoke',(e,False,q,b,r,w,f)
 if not l and e<2: yield 'reissue',(e+1,True,q,b,r,w,f)
 if q!=-1:
  yield 'cancel',(e,l,-1,b+r,0,w,f)
  if not fixed or (l and q==e): yield 'commit',(e,l,-1,b,0,w+r,f+1)
def scan(fixed):
 start=(0,True,-1,3,0,0,0); seen={start}; queue=deque([(start,[]) ]); violations=[]; n=0
 while queue:
  s,p=queue.popleft()
  assert s[3]+s[4]+s[5]==3 and min(s[3:6])>=0
  for a,t in edges(s,fixed):
   n+=1
   if a=='commit' and not(s[1] and s[2]==s[0]): violations.append(p+[a])
   if t not in seen: seen.add(t);queue.append((t,p+[a]))
 return len(seen),n,violations
for fixed in (False,True):
 states,trans,bad=scan(fixed);print(f'commit revalidation={fixed}: {states} states, {trans} edges, {len(bad)} violating edges');print('shortest witness:',min(bad,key=len) if bad else 'none')
 assert bool(bad)!=fixed
# Crash/retry model: effect durable, acknowledgement may be lost. Atomic dedup + effect.
for fixed in (False,True):
 seen={(False,False,0)}; q=deque(seen); n=0; bad=[]
 while q:
  d,a,c=q.popleft()
  ts=[]
  if not a and c<2: ts.append((True,False,c+(not d or not fixed)))
  if d: ts.append((d,True,c))
  ts.append((d,False,c)) # lost acknowledgement/restart
  for t in ts:
   n+=1
   if t[2]>1: bad.append(t)
   if t not in seen: seen.add(t);q.append(t)
 print(f'atomic durable dedup={fixed}: {len(seen)} states, {n} edges, {len(bad)} violating edges');assert bool(bad)!=fixed
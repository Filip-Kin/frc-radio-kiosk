"""v2d placer: v2c's macro annealer (place_d.py) for the soft phase, then a
greedy legalizer that finds every legal spot at once by FFT correlation of the
body's mask against the occupied raster, biggest bodies first, each at the legal
spot nearest its annealed position (wirelength breaks ties), then v2c's hard
refinement (moves that never add overlap).
Usage: place2d.py seed iters out.json   (env BH, BOARD, PARTS, L1, RW)"""
import os, sys
seed, ITER, OUT = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
sys.argv = [sys.argv[0], str(seed), str(ITER), OUT]
src = open('place_d.py').read().split("INIT=os.environ.get('INITM')")[0]
exec(src)
import numpy as np

phase(ITER, 8.0, 0.05, 0.3, float(os.environ.get('L1', '300')), 12, False)
print('soft WL %.0f overlapping %d' % (sum(NC.values()), total_ovl()), flush=True)

FY, FX = 1 << int(np.ceil(np.log2(NY + 64))), 1 << int(np.ceil(np.log2(NX + 64)))
def legal_map(field, mk):
    h, w = mk.shape
    A = np.zeros((FY, FX)); A[:NY, :NX] = field
    B = np.zeros((FY, FX)); B[:h, :w] = mk
    C = np.real(np.fft.ifft2(np.fft.fft2(A) * np.conj(np.fft.fft2(B))))
    ok = C[:NY, :NX] < 0.5
    ok[:, NX - w + 1:] = False; ok[NY - h + 1:, :] = False
    return ok

failed = []
def legalize_fast(order_keys):
    failed.clear()
    occ[:] = 0
    for k in order_keys:
        tx, ty, ta = bst[k]
        if k in CAP and CAP[k] in state and CAP[k] not in bodies.get(k, {}).get('mem', []):
            tx, ty = state[CAP[k]][0], state[CAP[k]][1]   # a decoupling cap aims at its IC's final spot
        base = (keep > 0).astype(float) + (occ > 0)
        if bodies[k]['tht']: base = base + backcrt
        if bodies[k]['pwr']: base = base + ethkeep
        base = (base > 0).astype(float)
        cands = []
        for a in (ta, (ta + 90) % 360, (ta + 180) % 360, (ta + 270) % 360):
            i0, j0, mk = bodies[k]['masks'][a]
            ok = legal_map(base, mk)
            js, is_ = np.nonzero(ok)
            if not len(js): continue
            xs = (is_ - i0) * G; ys = (js - j0) * G
            d = np.hypot(xs - tx, ys - ty) + (0 if a == ta else 1.5)
            for t in np.argsort(d)[:25]:
                cands.append((float(d[t]), float(xs[t]), float(ys[t]), a))
        if not cands:
            failed.append(k); add_b(k, 1); continue
        cands.sort(); best = None
        for d, x, y, a in cands[:40]:
            bst[k] = [round(x, 3), round(y, 3), a]; place_members(k)
            sc = sum(netcost(n) for n in bnets[k]) + RW * reg_full(k) + 4 * d
            if best is None or sc < best[0]: best = (sc, x, y, a)
        bst[k] = [round(best[1], 3), round(best[2], 3), best[3]]; place_members(k)
        for n in bnets[k]: NC[n] = netcost(n)
        add_b(k, 1)

size = {k: int(bodies[k]['masks'][0][2].sum()) for k in keys}
# macros, then each IC followed straight away by its decoupling caps, then the rest
big = sorted(keys, key=lambda k: (-(k in MAC), -size[k]))
order = []
for k in big:
    if k in order or (k in CAP and CAP[k] in bodies): continue
    order.append(k)
    order += [c for c in capof.get(k, []) if c in bodies and c not in order]
order += [k for k in big if k not in order]
soft = {k: list(v) for k, v in bst.items()}
for attempt in range(8):
    for k in keys: bst[k] = list(soft[k]); place_members(k)
    legalize_fast(order)
    print('attempt', attempt, 'no spot for', failed, flush=True)
    if not failed: break
    order = [k for k in order if k in failed] + [k for k in order if k not in failed]
print('legal WL %.0f overlapping %d' % (sum(NC.values()), total_ovl()), flush=True)
# swaps of two single parts with the same land pattern: same mask, so overlap cannot change
libs = {}
for k in keys:
    if k not in MAC: libs.setdefault((parts[idx[k]]['lib'], bodies[k]['pwr'], bodies[k]['tht']), []).append(k)
swapable = [l for l in libs.values() if len(l) > 1]
def swap_phase(n, T0, T1):
    acc = 0
    for it in range(n):
        T = T0 * (T1 / T0) ** (it / n)
        grp = random.choice(swapable); k1, k2 = random.sample(grp, 2)
        a1, a2 = bst[k1], bst[k2]
        before = sum(NC[x] for x in bnets[k1] | bnets[k2]) + RW * (reg_full(k1) + reg_full(k2))
        add_b(k1, -1); add_b(k2, -1)
        bst[k1], bst[k2] = list(a2), list(a1); place_members(k1); place_members(k2)
        ch = {x: netcost(x) for x in bnets[k1] | bnets[k2]}
        after = sum(ch.values()) + RW * (reg_full(k1) + reg_full(k2))
        d = after - before
        if d < 0 or random.random() < math.exp(-d / T): NC.update(ch); acc += 1
        else: bst[k1], bst[k2] = list(a1), list(a2); place_members(k1); place_members(k2)
        add_b(k1, 1); add_b(k2, 1)
    return acc
for cyc in range(3):
    print('swaps accepted', swap_phase(60000, 2.0, 0.01), 'WL %.0f' % sum(NC.values()), flush=True)
    phase(int(os.environ.get('REFINE', '400000')) // 3, 0.8, 0.01, 300, 300, 2.5, True)
bad = [k for k in keys if (add_b(k, -1), ovl_b(k), add_b(k, 1))[1]]
print('refined WL %.0f overlapping %d %s' % (sum(NC.values()), len(bad), bad[:10]), flush=True)
json.dump(dict(state=state, pins=pin_of, wl=sum(NC.values()), bad=bad), open(OUT, 'w'))

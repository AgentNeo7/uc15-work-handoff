"""Standalone deterministic synthetic prototype. No runtime integration or domain authority."""
import argparse
import copy
import datetime
import hashlib
import json
import math
from pathlib import Path
import sys


def obj(x, keys):
    if not isinstance(x, dict) or set(x) != set(keys.split()):
        raise ValueError("object fields must be: " + keys)
    return x


def text(x):
    if not isinstance(x, str) or not x or len(x) > 2048:
        raise ValueError("expected nonempty bounded string")
    return x


def arr(x):
    if not isinstance(x, list) or len(x) > 500:
        raise ValueError("expected list of at most 500 elements")
    return x


def names(x):
    values = [text(v) for v in arr(x)]
    if len(values) != len(set(values)):
        raise ValueError("duplicate identifiers")
    return values


def num(x, minimum=0):
    if type(x) not in (int, float) or not math.isfinite(x) or x < minimum or x > 1e12:
        raise ValueError("invalid bounded number")
    return x


def integer(x, minimum=0):
    if type(x) is not int:
        raise ValueError("expected integer")
    return num(x, minimum)


def boolean(x):
    if type(x) is not bool:
        raise ValueError("expected boolean")
    return x


def unique(rows):
    ids = [text(x["id"]) for x in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate record ID")


def scalar(x):
    if x is not None and type(x) not in (str, int, float, bool):
        raise ValueError("expected scalar value")
    if type(x) in (int,float) and not math.isfinite(x):
        raise ValueError("nonfinite number")
    return x


def result(**kw):
    return {"evidence_class": "simulated", "analysis_completed": True, **kw}


def analyze(payload):
    obj(payload, "spec_version evidence_class data")
    if type(payload["spec_version"]) is not int or payload["spec_version"] != 1 or payload["evidence_class"] != "simulated":
        raise ValueError("only spec_version 1 synthetic evidence_class simulated supported")
    return run(copy.deepcopy(payload["data"]))


def matches(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and matches(actual[k], v) for k,v in expected.items())
    return actual == expected


def read_json(path):
    if path.stat().st_size > 1000000:
        raise ValueError("input exceeds 1000000 bytes")
    return json.loads(path.read_text())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--expect", type=Path, help="optional recursive subset oracle; mismatch exits 1")
    a=p.parse_args()
    try:
        if a.input.resolve() == a.output.resolve() or (a.expect and a.expect.resolve() == a.output.resolve()):
            raise ValueError("output must not overwrite input or oracle")
        output=analyze(read_json(a.input))
        expected=read_json(a.expect) if a.expect else None
        a.output.write_text(json.dumps(output,indent=2,sort_keys=True,allow_nan=False)+"\n")
        return 0 if expected is None or matches(output,expected) else 1
    except (ValueError, KeyError, TypeError, OSError, RecursionError, OverflowError) as e:
        print("invalid input: "+str(e),file=sys.stderr)
        return 2

def run(d):
    obj(d,'owner roles obligations completed_steps resume_steps evidence current_versions decision packet_version allowed_reviewers now')
    roles=names(d['roles']);completed=names(d['completed_steps']);resume=names(d['resume_steps']);reviewers=names(d['allowed_reviewers']);num(d['now']);text(d['packet_version'])
    if d['owner'] is not None and d['owner'] not in roles:raise ValueError('owner role unknown')
    if not set(reviewers)<=set(roles):raise ValueError('reviewer role unknown')
    obs=arr(d['obligations']);unique(obs);ev=arr(d['evidence']);unique(ev)
    if not isinstance(d['current_versions'],dict):raise ValueError('versions must be mapping')
    for k,v in d['current_versions'].items():text(k);text(v)
    decision=obj(d['decision'],'actor accepted packet_version');text(decision['actor']);boolean(decision['accepted']);text(decision['packet_version'])
    issues=[]
    if d['owner'] is None:issues.append('owner_missing')
    for o in obs:
        obj(o,'id owner deadline status');num(o['deadline'])
        if o['status'] not in ['open','completed']:raise ValueError('invalid obligation state')
        if o['owner'] not in roles:issues.append('unowned_obligation:'+o['id'])
        if o['status']=='open' and o['deadline']<d['now']:issues.append('overdue_obligation:'+o['id'])
    for e in ev:
        obj(e,'id version');text(e['version'])
        if e['id'] not in d['current_versions']:issues.append('missing_evidence_version:'+e['id'])
        elif d['current_versions'][e['id']]!=e['version']:issues.append('stale_evidence:'+e['id'])
    issues.extend('completed_step_repeated:'+s for s in resume if s in completed)
    if not decision['accepted']:issues.append('decision_not_accepted')
    if decision['actor'] not in reviewers:issues.append('reviewer_not_permitted')
    if decision['packet_version']!=d['packet_version']:issues.append('obsolete_decision')
    return result(status='blocked' if issues else 'ready_for_declared_return',owner=d['owner'] if issues else decision['actor'],resume_steps=[] if issues else resume,issues=sorted(issues),obligations=obs,executed=False,authority='Declared role strings only; no authentication or permission lookup.')

if __name__ == "__main__":
    sys.exit(main())

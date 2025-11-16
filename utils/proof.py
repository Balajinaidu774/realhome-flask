import hashlib
import json
import os
import datetime

LEDGER_PATH = os.path.join(os.path.dirname(__file__), '..', 'ledger.txt')


def compute_sha256(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def make_merkle_root(hashes):
    # Simple Merkle root computation: pairwise hash until single root
    if not hashes:
        return ''
    current = hashes[:]
    while len(current) > 1:
        next_level = []
        for i in range(0, len(current), 2):
            a = current[i]
            b = current[i+1] if i+1 < len(current) else a
            next_level.append(compute_sha256(a + b))
        current = next_level
    return current[0]


def anchor_to_ledger(root_hash: str) -> dict:
    # Append an anchor line to a simple local ledger file and return an anchor id
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    timestamp = datetime.datetime.utcnow().isoformat()
    anchor_id = compute_sha256(root_hash + timestamp)[:16]
    line = json.dumps({'anchor_id': anchor_id, 'root': root_hash, 'ts': timestamp})
    with open(LEDGER_PATH, 'a', encoding='utf-8') as f:
        f.write(line + '\n')
    return {'anchor_id': anchor_id, 'root': root_hash, 'ts': timestamp}

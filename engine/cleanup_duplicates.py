"""Detect and optionally merge/delete duplicate concept files.

Usage:
  python cleanup_duplicates.py       # dry-run, shows duplicates
  python cleanup_duplicates.py --apply   # apply deletions and remapping

Behavior:
- Groups concept JSON files by content fingerprint (ignoring 'id' and 'version').
- For each group with multiple files, chooses a canonical file (prefer non-UUID id).
- In --apply mode:
  - Deletes duplicate files (non-canonical)
  - Updates `installed_content` table to point to canonical id
  - Updates lesson files that reference deleted concept ids
"""
import os
import json
import hashlib
import argparse
import sqlite3

PROJECT = os.path.dirname(os.path.dirname(__file__))
CONCEPTS_DIR = os.path.join(PROJECT, 'content', 'concepts')
LESSONS_DIR = os.path.join(PROJECT, 'content', 'lessons')
DB_PATH = os.path.join(PROJECT, 'database', 'progress.db')

def fingerprint(obj):
    # remove id and version then canonicalize
    o = {k:v for k,v in obj.items() if k not in ('id','version')}
    s = json.dumps(o, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(s.encode('utf-8')).hexdigest()

def is_uuid(s):
    import re
    return bool(re.match(r'^[0-9a-fA-F\-]{36}$', s))

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_duplicates():
    files = [f for f in os.listdir(CONCEPTS_DIR) if f.endswith('.json')]
    groups = {}
    meta = {}
    for fn in files:
        path = os.path.join(CONCEPTS_DIR, fn)
        try:
            data = load_json(path)
        except Exception:
            continue
        fp = fingerprint(data)
        groups.setdefault(fp, []).append(fn)
        meta[fn] = data
    # filter groups with >1
    dup = {fp: (groups[fp], [meta[f] for f in groups[fp]]) for fp in groups if len(groups[fp])>1}
    return dup

def show_preview(dup):
    if not dup:
        print('No duplicates found.')
        return
    print('Duplicate groups:')
    for fp, (files, datas) in dup.items():
        print('\nGroup fingerprint:', fp)
        for fn, d in zip(files, datas):
            cid = d.get('id')
            ver = d.get('version')
            print(f' - {fn}    id={cid}   version={ver}')

def apply_cleanup(dup):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for fp, (files, datas) in dup.items():
        # choose canonical: prefer non-uuid id
        choices = list(zip(files,datas))
        canonical_fn, canonical_data = None, None
        for fn,d in choices:
            if not is_uuid(d.get('id','')):
                canonical_fn, canonical_data = fn,d
                break
        if not canonical_fn:
            canonical_fn, canonical_data = choices[0]

        canonical_id = canonical_data.get('id')
        # remove others
        for fn,d in choices:
            if fn == canonical_fn:
                continue
            old_id = d.get('id')
            old_path = os.path.join(CONCEPTS_DIR, fn)
            print(f'Deleting duplicate file: {old_path} (id={old_id})')
            try:
                os.remove(old_path)
            except Exception as e:
                print('  failed to delete:', e)
            # update installed_content table: replace old_id with canonical_id
            try:
                cur.execute('UPDATE installed_content SET content_id = ? WHERE content_id = ?', (canonical_id, old_id))
            except Exception:
                pass
            # update lessons referencing old_id
            for lf in os.listdir(LESSONS_DIR):
                if not lf.endswith('.json'):
                    continue
                lp = os.path.join(LESSONS_DIR, lf)
                try:
                    ld = load_json(lp)
                except Exception:
                    continue
                changed = False
                concepts = ld.get('concepts', [])
                new_concepts = [canonical_id if c==old_id else c for c in concepts]
                if new_concepts != concepts:
                    ld['concepts'] = new_concepts
                    with open(lp, 'w', encoding='utf-8') as f:
                        json.dump(ld, f, indent=2, ensure_ascii=False)
                    print(f'  updated lesson {lf} replacing {old_id} -> {canonical_id}')
    conn.commit()
    conn.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    dup = find_duplicates()
    show_preview(dup)
    if args.apply:
        if not dup:
            print('Nothing to apply')
            return
        confirm = input('\nApply deletions and remapping? type YES to continue: ')
        if confirm.strip() == 'YES':
            apply_cleanup(dup)
            print('Applied cleanup.')
        else:
            print('Aborted.')

if __name__ == '__main__':
    main()

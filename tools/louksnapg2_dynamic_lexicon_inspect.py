#!/usr/bin/env python3
"""Safely inventory pinned Perseus Greek/Latin XML archives without extraction."""
from __future__ import annotations
import argparse, hashlib, json, tarfile
from collections import Counter
from pathlib import Path, PurePosixPath
from defusedxml import ElementTree as DET

SOURCE_REPOSITORY = "PerseusDL/dynamic-lexicon"
SOURCE_COMMIT = "945b03db7ff358217a18540a7d7efef9d7339b66"
ARCHIVE_LIMIT_BYTES = 5_000_000
MEMBER_LIMIT = 20_000
TOTAL_XML_LIMIT_BYTES = 1_000_000_000
SAMPLE_LIMIT = 80
CANDIDATE_TAGS = {"entry","lexeme","lemma","word","sense","trans","gloss","form","orth","pos","headword","dictscrap","lexicalentry"}

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()

def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1].casefold()

def inspect_archive(path: Path, language: str) -> dict:
    if path.is_symlink() or not path.is_file(): raise RuntimeError("DYNAMIC_LEXICON_ARCHIVE_MISSING_OR_UNSAFE:"+language)
    if path.stat().st_size > ARCHIVE_LIMIT_BYTES: raise RuntimeError("DYNAMIC_LEXICON_ARCHIVE_SIZE_LIMIT:"+language)
    tags, attrs, candidates, roots, root_children = Counter(), Counter(), Counter(), Counter(), Counter()
    samples, xml_members, member_count, total_xml_bytes = [], 0, 0, 0
    with tarfile.open(path, mode="r:gz") as archive:
        for member in archive:
            member_count += 1
            if member_count > MEMBER_LIMIT: raise RuntimeError("DYNAMIC_LEXICON_MEMBER_LIMIT:"+language)
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts:
                raise RuntimeError("DYNAMIC_LEXICON_UNSAFE_MEMBER:"+member.name[:200])
            if member.isdir():
                continue
            if not member.isfile():
                raise RuntimeError("DYNAMIC_LEXICON_UNSAFE_MEMBER_TYPE:"+member.name[:200])
            if not name.name.casefold().endswith(".xml") or member.size < 1: continue
            total_xml_bytes += int(member.size)
            if total_xml_bytes > TOTAL_XML_LIMIT_BYTES: raise RuntimeError("DYNAMIC_LEXICON_XML_TOTAL_LIMIT:"+language)
            handle = archive.extractfile(member)
            if handle is None: raise RuntimeError("DYNAMIC_LEXICON_MEMBER_READ_FAILED:"+member.name[:200])
            xml_members += 1
            depth, local_samples = 0, 0
            for event, element in DET.iterparse(handle, events=("start","end")):
                tag = local_name(str(element.tag))
                if event == "start":
                    if depth == 0: roots[tag] += 1
                    elif depth == 1: root_children[tag] += 1
                    tags[tag] += 1
                    for key in element.attrib: attrs[str(key).rsplit("}",1)[-1].casefold()] += 1
                    if tag in CANDIDATE_TAGS: candidates[tag] += 1
                    if local_samples < SAMPLE_LIMIT and (tag in CANDIDATE_TAGS or depth <= 1):
                        samples.append({"member":member.name[:240],"tag":tag,"depth":depth,
                          "attributes":{str(k).rsplit("}",1)[-1]:str(v)[:180] for k,v in list(element.attrib.items())[:12]}})
                        local_samples += 1
                    depth += 1
                else:
                    depth -= 1
                    element.clear()
            handle.close()
    if not xml_members: raise RuntimeError("DYNAMIC_LEXICON_NO_XML_MEMBERS:"+language)
    return {"language":language,"archive_bytes":path.stat().st_size,"archive_sha256":sha256_file(path),
      "tar_members":member_count,"xml_members":xml_members,"xml_uncompressed_bytes":total_xml_bytes,
      "root_tags":dict(roots.most_common(40)),"root_child_tags":dict(root_children.most_common(80)),
      "element_tags":dict(tags.most_common(120)),"attribute_names":dict(attrs.most_common(80)),
      "candidate_lexical_tags":dict(candidates.most_common(40)),"samples":samples}

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--greek",type=Path,required=True); p.add_argument("--latin",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    greek=inspect_archive(a.greek,"grc"); latin=inspect_archive(a.latin,"lat")
    report={"schema":"LOUKSNAPG2_DYNAMIC_LEXICON_XML_INVENTORY/1.0","status":"PASS_XML_INVENTORY_ONLY",
      "source":{"repository":SOURCE_REPOSITORY,"commit":SOURCE_COMMIT,
      "data_license":"Creative Commons Attribution-ShareAlike (version unspecified in upstream README)",
      "attribution":"Perseus Digital Library Dynamic Lexicon"},
      "greek":greek,"latin":latin,
      "cross_language_alignment":{"status":"NOT_BUILT","reason":"XML schemas must be compared before selecting sense and alignment fields; shared English glosses alone do not prove Greek-Latin equivalence."},
      "runtime_transducer_promotion":"NOT_AUTHORIZED","certification":"NOT_GRANTED"}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":report["status"],
      "greek":{"xml_members":greek["xml_members"],"xml_uncompressed_bytes":greek["xml_uncompressed_bytes"],"sha256":greek["archive_sha256"],"top_tags":list(greek["candidate_lexical_tags"].items())[:12]},
      "latin":{"xml_members":latin["xml_members"],"xml_uncompressed_bytes":latin["xml_uncompressed_bytes"],"sha256":latin["archive_sha256"],"top_tags":list(latin["candidate_lexical_tags"].items())[:12]},
      "alignment":"NOT_BUILT","output":str(a.output)},ensure_ascii=False,sort_keys=True))
    return 0
if __name__=="__main__": raise SystemExit(main())

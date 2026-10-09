"""V3-29 independently fetched source text gate, separate from model assertions.

Only finite textbook sections from immutable V3-28 seeds are accepted.
No citation laundering: a valid URL is not semantic claim approval; require
fresh source HTML and exact recognizable published section text on each run.
"""
from __future__ import annotations
from hashlib import sha256
from html.parser import HTMLParser
import json
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ANCHORS = {
    "LINEAR_SLOPE": (
        "3.2 Slope of a Line", "rise", "run", "slope",
    ),
    "CONSTANT_ACCELERATION_VELOCITY": (
        "2.5 Motion Equations for Constant Acceleration", "velocity",
        "acceleration", "Solving for",
    ),
}
MAX_BYTES = 1_500_000
class _SectionText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]
        self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript") and self.skip:self.skip-=1
    def handle_data(self,content):
        if not self.skip:self.parts.append(content)
def clean_source_text(raw:bytes)->str:
    parser=_SectionText()
    parser.feed(raw.decode("utf-8","replace"))
    return " ".join(" ".join(parser.parts).split())
def source_certificate(seed:dict,*,html:bytes,observed_url:str)->dict:
    expected=seed["source_url"]
    if (not isinstance(expected,str) or
        not expected.startswith("https://openstax.org/books/") or
        observed_url!=expected or urlparse(observed_url).hostname!="openstax.org"):
        raise ValueError("V3_29_SOURCE_ORIGIN_OR_REDIRECT_MISMATCH")
    if not html or len(html)>MAX_BYTES:
        raise ValueError("V3_29_SOURCE_BODY_MISSING_OR_OVERSIZE")
    text=clean_source_text(html)
    anchors=ANCHORS.get(seed["model_kind"])
    if not anchors or any(anchor.casefold() not in text.casefold() for anchor in anchors):
        raise ValueError("V3_29_SOURCE_EXCERPT_ANCHORS_NOT_FOUND")
    if len(text)<1200:
        raise ValueError("V3_29_TOO_SHORT_TO_SUPPORT_SOURCE_SECTION")
    # Additional targeted extraction, not just any page mentioning physics.
    if seed["model_kind"]=="LINEAR_SLOPE":
        if not re.search(r"slope.{0,100}rise.{0,100}run|rise.{0,140}run.{0,140}slope",text,re.I):
            raise ValueError("V3_29_SLOPE_RELATION_NOT_LOCATED")
    elif not re.search(r"velocity.{0,110}acceleration|acceleration.{0,110}velocity",text,re.I):
        raise ValueError("V3_29_VELOCITY_ACCELERATION_CONTEXT_NOT_LOCATED")
    return {"status":"SOURCE_HTML_ANCHOR_VERIFIED_NOT_INDEPENDENT_SEMANTIC_REVIEW",
            "url":expected,"retrieved_bytes_sha256":sha256(html).hexdigest(),
            "normalized_text_sha256":sha256(text.encode()).hexdigest(),
            "publisher":"OpenStax","source_section_anchor_count":len(anchors),
            "external_semantic_fact_review":"UNMEASURED",
            "content_persisted":"ONLY_HASHES_AND_ANCHOR_COUNTS"}

def fetch_textbook(seed:dict,*,opener=None)->dict:
    request=Request(seed["source_url"],headers={
        "User-Agent":"LearnFlowSourceVerifier/1.0 (academic testing)",
        "Accept":"text/html"})
    transport=opener or urlopen
    with transport(request,timeout=22) as r:
        # No following a redirect to a mirror / adversarial domain.
        url=r.geturl()
        header_length=r.headers.get("Content-Length")
        if header_length and int(header_length)>MAX_BYTES:
            raise ValueError("V3_29_SOURCE_CONTENT_TOO_LARGE")
        data=r.read(MAX_BYTES+1)
    return source_certificate(seed,html=data,observed_url=url)

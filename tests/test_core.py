import json
from datetime import datetime,timezone
from rdsa.extractor import extract
from rdsa.scorer import score
from rdsa.classifier import classify
def fixture(): return json.load(open('data/synthetic_posts.json',encoding='utf-8'))['posts']
def test_worked_example():
    lead=score(extract(fixture()[0]['post'],datetime(2026,7,13,3,0,tzinfo=timezone.utc)),datetime(2026,7,13,3,0,tzinfo=timezone.utc)); assert lead.lead_score==100
def test_all_labels():
    for item in fixture():
        lead=score(extract(item['post'],datetime(2026,7,13,7,0,tzinfo=timezone.utc)),datetime(2026,7,13,7,0,tzinfo=timezone.utc)); assert classify(lead).lead_class==item['expected']['lead_class'],item['post']['id']

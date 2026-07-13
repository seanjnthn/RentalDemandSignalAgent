import json
from datetime import datetime, timezone, timedelta
from rdsa.db import connect, upsert_lead, purge_old_leads
from rdsa.extractor import extract
from rdsa.scorer import score
from rdsa.classifier import classify

def lead(post_id, text="cari apartemen BSD 2 kamar 6 jt/bulan", username="u"):
    return classify(score(extract({"id":post_id,"text":text,"timestamp":"2026-07-13T00:00:00Z","username":username,"permalink":"https://threads.net/p"})))

def test_dedup_near_duplicate_and_manual_status(tmp_path):
    c=connect(str(tmp_path/"db.sqlite")); a=lead("a"); assert upsert_lead(c,a)==1; assert upsert_lead(c,a)==0
    c.execute("update leads set status='reviewed' where post_id='a'"); c.commit(); assert upsert_lead(c,lead("a"))==0
    assert c.execute("select status from leads where post_id='a'").fetchone()[0] == 'reviewed'
    assert upsert_lead(c,lead("b", "cari apartemen BSD 2 kamar 6 jt/bulan banget"))==0
    assert c.execute("select status from leads where post_id='a'").fetchone()[0] == 'reviewed'

def test_retention_purges_old_terminal_leads(tmp_path):
    c=connect(str(tmp_path/"db.sqlite")); a=lead("old"); upsert_lead(c,a)
    old=(datetime.now(timezone.utc)-timedelta(days=100)).isoformat(); c.execute("update leads set status='rejected',last_seen=?",(old,)); c.commit()
    b=lead("new", username="different-user"); upsert_lead(c,b); c.execute("update leads set status='rejected' where post_id='new'"); c.commit()
    assert purge_old_leads(c,90)==1 and c.execute("select count(*) from leads").fetchone()[0]==1

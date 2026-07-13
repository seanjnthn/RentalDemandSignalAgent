from types import SimpleNamespace
from rdsa.cli import process_raw
from rdsa.db import connect

def test_pilot_process_persists_and_prints_preview_without_send(capsys, tmp_path):
    posts=[{"id":"pilot-1","text":"cari apartemen BSD 2 kamar 6 jt/bulan secepatnya","username":"u","timestamp":"2026-07-13T00:00:00Z","permalink":"https://threads.net/p/1"}]
    c=connect(str(tmp_path/"db.sqlite")); args=SimpleNamespace(dry_run=True,pilot=True)
    result=process_raw(posts,"apify",args,c); output=capsys.readouterr().out
    assert result["new"]==1 and c.execute("select count(*) from leads").fetchone()[0]==1
    assert "🏠 RENTAL LEAD" in output and "Recommended action" in output and "sendMessage" not in output

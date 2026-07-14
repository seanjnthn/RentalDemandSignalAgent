from rdsa.threads_client import ThreadsClient
from rdsa.notifier import TelegramNotifier
from rdsa import config
class Response:
    def __init__(self,payload): self.payload=payload
    def raise_for_status(self): pass
    def json(self): return self.payload
class Session:
    def __init__(self): self.calls=[]
    def get(self,url,**kwargs): self.calls.append(("GET",url,kwargs)); return Response({"data":[{"id":"1"}]})
    def post(self,url,**kwargs): self.calls.append(("POST",url,kwargs)); return Response({"ok":True})
def test_threads_search_is_get_only():
    s=Session(); posts=ThreadsClient('token',session=s).search('cari sewa',limit=999)
    assert posts==[{"id":"1"}] and s.calls[0][0]=='GET' and s.calls[0][2]['params']['limit']==100
def test_telegram_targets_configured_group(monkeypatch):
    # Under the private-pilot safety model, the notifier only delivers to the
    # configured TELEGRAM_ALLOWED_CHAT_ID. Bind both the allowed chat and the
    # notifier to the same id and confirm the POST targets it.
    monkeypatch.setattr(config, "TELEGRAM_ALLOWED_CHAT_ID", "-1001")
    s=Session(); assert TelegramNotifier('bot','-1001',s).send('card')['ok']; assert s.calls[0][0]=='POST'; assert s.calls[0][2]['json']['chat_id']=='-1001'

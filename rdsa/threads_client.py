import requests
FIELDS="id,text,media_type,permalink,timestamp,username,has_replies,is_quote_post,is_reply"
class ThreadsClient:
    def __init__(self,token,base_url="https://graph.threads.net/v1.0",session=None): self.token=token; self.base_url=base_url.rstrip("/"); self.session=session or requests
    def search(self,q,location=None,since=None,until=None,limit=25,search_type="RECENT",media_type="TEXT"):
        p={"q":q,"search_type":search_type,"search_mode":"KEYWORD","media_type":media_type,"limit":min(limit,100),"fields":FIELDS,"access_token":self.token}; p.update({k:v for k,v in (("since",since),("until",until)) if v is not None})
        r=self.session.get(self.base_url+"/keyword_search",params=p,timeout=30); r.raise_for_status(); payload=r.json(); posts=payload.get("data",[])
        while payload.get("paging",{}).get("next"):
            r=self.session.get(payload["paging"]["next"],timeout=30); r.raise_for_status(); payload=r.json(); posts.extend(payload.get("data",[]))
        return posts

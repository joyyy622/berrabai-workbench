"""Owner-only durable workspace and bounded RSS collection."""
import ipaddress
import json
import socket
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET


def init_business(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS business_workspace(id INTEGER PRIMARY KEY CHECK(id=1),version INTEGER NOT NULL DEFAULT 0,payload TEXT NOT NULL)")
    conn.execute("INSERT OR IGNORE INTO business_workspace(id,payload) VALUES(1,?)", (json.dumps({"orders":[],"events":[],"intel":[],"reports":[],"tasks":[],"feeds":[]}),))


def read_workspace(conn):
    r = conn.execute("SELECT version,payload FROM business_workspace WHERE id=1").fetchone()
    return {"version":r["version"], "state":json.loads(r["payload"])}


def save_workspace(conn, version, state):
    if not isinstance(state,dict): raise ValueError("工作台数据格式无效")
    allowed = ("orders","events","intel","reports","tasks","feeds")
    if set(state) != set(allowed): raise ValueError("工作台字段不完整，请刷新")
    for k in allowed:
        if not isinstance(state[k],list): raise ValueError("数据必须为列表")
    if len(state["orders"])>30000: raise ValueError("最多保存30000条订单明细")
    from datetime import date
    seen=set()
    for row in state["orders"]:
        if not isinstance(row,dict): raise ValueError("订单明细格式无效")
        for key in ("id","orderId","date","product","color","status"):
            if not isinstance(row.get(key),str) or not row[key] or len(row[key])>500:
                raise ValueError("订单字段无效："+key)
        date.fromisoformat(row["date"])
        if row["id"] in seen: raise ValueError("订单明细编号重复")
        seen.add(row["id"])
        for key in ("qty","refundQty","paid","refund"):
            if type(row.get(key)) is not int or row[key]<0 or row[key]>1e11:
                raise ValueError("订单金额与数量必须为非负整数")
        if row["qty"]<1 or row["refundQty"]>row["qty"] or row["refund"]>row["paid"]:
            raise ValueError("退款金额或退货件数超出原订单")
    raw=json.dumps(state,ensure_ascii=False)
    if len(raw.encode())>8_000_000: raise ValueError("数据量超过本地版本上限")
    cursor=conn.execute("UPDATE business_workspace SET version=version+1,payload=? WHERE id=1 AND version=?", (raw,version))
    if cursor.rowcount!=1: raise ValueError("其他页面已更新数据，请刷新后重试，当前改动尚未保存")
    return version+1


def normalize_feed_url(url):
    # Code-formatted links are often copied with surrounding Markdown backticks.
    return str(url).strip().strip('`').strip()


def check_url(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None,443):
        raise ValueError("资讯源需为不含账号信息的HTTPS地址")
    for result in socket.getaddrinfo(parsed.hostname,443):
        if not ipaddress.ip_address(result[4][0]).is_global:
            raise ValueError("资讯源不能指向本地或内网")
    return url


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        check_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def fetch_feed(url):
    url=normalize_feed_url(url)
    check_url(url)
    request=urllib.request.Request(url,headers={"User-Agent":"BerrabaiResearch/1.0","Accept":"application/rss+xml,application/atom+xml,text/xml"})
    try:
        with urllib.request.build_opener(SafeRedirect()).open(request,timeout=15) as res:
            raw=res.read(2_000_001)
    except urllib.error.HTTPError as error:
        if error.code==404:
            raise ValueError('来源地址不存在（404），请编辑来源，检查地址末尾是否多出符号，以及是否为正确的RSS地址') from error
        raise ValueError(f'来源网站返回{error.code}，暂时无法获取；请稍后重试或更换来源') from error
    if len(raw)>2_000_000: raise ValueError("资讯源过大")
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper(): raise ValueError("不支持此XML格式")
    root=ET.fromstring(raw)
    ns='{http://www.w3.org/2005/Atom}'
    items=root.findall('.//item') or root.findall(ns+'entry')
    output=[]
    for item in items[:25]:
        title=item.findtext('title') or item.findtext(ns+'title') or ''
        link=item.findtext('link')
        if not link:
            element=item.find(ns+'link')
            link=element.get('href','') if element is not None else ''
        if urllib.parse.urlsplit(link or '').scheme not in ('https','http'): continue
        output.append({"title":title[:300],"url":link[:2000],"published":(item.findtext('pubDate') or item.findtext(ns+'published') or item.findtext(ns+'updated') or '')[:100]})
    if not output: raise ValueError("没有读取到RSS或Atom条目，请检查来源地址")
    return output

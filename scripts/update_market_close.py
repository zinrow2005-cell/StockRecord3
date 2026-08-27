#!/usr/bin/env python3
from __future__ import annotations
import json, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'market-close.json'
SOURCES=[('twse','listed','證交所','https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL'),('tpex','otc','櫃買中心','https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes')]
def roc_date(value):
    s=''.join(ch for ch in str(value or '').strip() if ch.isdigit())
    if len(s)==7:return f'{int(s[:3])+1911:04d}-{s[3:5]}-{s[5:7]}'
    if len(s)==8:return f'{int(s[:4]):04d}-{s[4:6]}-{s[6:8]}'
    return ''
def num(value):
    try:return float(str(value or '').replace(',','').strip())
    except Exception:return 0.0
def fetch_json(url):
    last=None
    for attempt in range(3):
        try:
            req=Request(url,headers={'User-Agent':'Mozilla/5.0 GitHubActions StockRecord/1.6.4','Accept':'application/json'})
            with urlopen(req,timeout=30) as r:return json.loads(r.read().decode('utf-8-sig'))
        except Exception as e:
            last=e;time.sleep(2*(attempt+1))
    raise last
def load_old():
    try:
        d=json.loads(OUT.read_text(encoding='utf-8'));return d if isinstance(d,dict) else {}
    except Exception:return {}
def main():
    old=load_old();old_quotes=old.get('quotes') if isinstance(old.get('quotes'),dict) else {};by_market={'listed':{},'otc':{}}
    for sym,q in old_quotes.items():
        if isinstance(q,dict) and q.get('market') in by_market:by_market[q['market']][sym]=q
    status={};trading_dates={};success=0
    for key,market,label,url in SOURCES:
        try:
            rows=fetch_json(url)
            if not isinstance(rows,list) or not rows:raise RuntimeError('empty response')
            fresh={}
            for row in rows:
                if not isinstance(row,dict):continue
                sym=str(row.get('Code') or row.get('SecuritiesCompanyCode') or '').strip().upper();price=num(row.get('ClosingPrice') if 'ClosingPrice' in row else row.get('Close'));date=roc_date(row.get('Date'));name=str(row.get('Name') or row.get('CompanyName') or '').strip()
                if sym and price>0 and date:fresh[sym]={'symbol':sym,'stockName':name,'price':price,'priceDate':date,'market':market,'source':label}
            if not fresh:raise RuntimeError('no recognizable quote rows')
            by_market[market]=fresh;dates=sorted({q['priceDate'] for q in fresh.values()});trading_dates[key]=dates[-1] if dates else '';status[key]={'ok':True,'count':len(fresh),'message':'official sync complete','tradingDate':trading_dates[key]};success+=1
        except Exception as e:
            kept=len(by_market[market]);status[key]={'ok':False,'count':kept,'message':f'{type(e).__name__}: {e}; kept previous {kept} quotes'}
    quotes={**by_market['listed'],**by_market['otc']}
    if not quotes:raise SystemExit('No quote data available from official sources and no previous data to preserve.')
    tz=timezone(timedelta(hours=8));payload={'version':1,'generatedAt':datetime.now(tz).isoformat(timespec='seconds'),'tradingDates':trading_dates,'quotes':dict(sorted(quotes.items())),'sourceStatus':status}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8');print(f'wrote {len(quotes)} quotes; source success={success}/2; dates={trading_dates}')
if __name__=='__main__':main()

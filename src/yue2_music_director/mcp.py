"""Explicit loopback-only MCP client for YuE2 Studio.

Does not open outbound internet connections or discover/scan ports.
No automatic retry on POST. Uses modern server/discover, with a legacy fallback.
"""
from __future__ import annotations
import json
import os
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

MODERN = '2026-07-28'
LEGACY = '2025-11-25'


class MCPError(RuntimeError):
    pass


def endpoint(url: str) -> str:
    if not isinstance(url, str):
        raise ValueError('MCP URL must be a string')
    p = urlsplit(url.strip())
    if p.scheme not in ('http','https') or p.hostname not in ('localhost','127.0.0.1','::1'):
        raise ValueError('MCP URL must point to an explicit loopback host')
    if p.username or p.password or p.query or p.fragment or not p.path or p.path == '/':
        raise ValueError('MCP URL must include a path, no credentials/query/fragment')
    try:
        port = p.port
    except ValueError:
        raise ValueError('Invalid port') from None
    if port is not None and not 1<=port<=65535:
        raise ValueError('Invalid port')
    return url.strip()


def configured_endpoint(value: str | None = None) -> str:
    url = value or os.environ.get('YUE2_MCP_URL')
    if not url:
        raise ValueError('Provide --url or the YUE2_MCP_URL environment variable')
    return endpoint(url)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise MCPError('MCP redirects are blocked')


def _parse_response(data: bytes, content_type: str):
    raw = data.decode('utf-8-sig')
    if 'text/event-stream' in content_type:
        for frame in raw.replace('\r\n','\n').split('\n\n'):
            parts=[line[5:].strip() for line in frame.split('\n') if line.startswith('data:')]
            if not parts:
                continue
            try:
                candidate=json.loads('\n'.join(parts))
            except ValueError:
                continue
            if isinstance(candidate,dict) and ('result' in candidate or 'error' in candidate):
                return candidate
        raise MCPError('No JSON-RPC result in event stream')
    try:
        payload=json.loads(raw)
    except ValueError as exc:
        raise MCPError('Invalid JSON-RPC payload') from exc
    if not isinstance(payload,dict):
        raise MCPError('JSON-RPC reply must be an object')
    return payload


class Client:
    def __init__(self,url: str,timeout: int=90):
        self.url=endpoint(url)
        self.timeout=timeout
        self.version=MODERN
        self.era='modern'
        self.session=None
        self.sequence=0
        self.opener=build_opener(ProxyHandler({}), _NoRedirect())

    def _post(self,payload,method,name=None,include_version=True):
        headers={'Content-Type':'application/json',
                 'Accept':'application/json, text/event-stream',
                 'Mcp-Method':method,
                 'User-Agent':'yue2-music-director/0.6'}
        if include_version: headers['MCP-Protocol-Version']=self.version
        if self.session: headers['Mcp-Session-Id']=self.session
        if name: headers['Mcp-Name']=name
        req=Request(self.url,json.dumps(payload).encode('utf-8'),headers,method='POST')
        try:
            with self.opener.open(req,timeout=self.timeout) as resp:
                self.session=resp.headers.get('Mcp-Session-Id',self.session)
                raw=resp.read(2_000_001)
                if len(raw)>2_000_000:
                    raise MCPError('MCP reply larger than 2 MB')
                if not raw.strip():
                    return None
                return _parse_response(raw,resp.headers.get('Content-Type',''))
        except (HTTPError,URLError) as exc:
            raise MCPError(f'MCP transport error: {type(exc).__name__}') from exc

    def rpc(self,method,params=None,name=None,include_version=True):
        self.sequence+=1
        request={'jsonrpc':'2.0','id':self.sequence,'method':method,'params':params or {}}
        result=self._post(request,method,name,include_version)
        if not isinstance(result,dict):
            raise MCPError('Missing MCP result')
        if result.get('error'):
            raise MCPError('MCP RPC returned an error')
        if 'result' not in result:
            raise MCPError('MCP response has no result')
        return result['result']

    def connect(self):
        try:
            info={'io.modelcontextprotocol/protocolVersion':MODERN,
                  'io.modelcontextprotocol/clientCapabilities':{},
                  'io.modelcontextprotocol/clientInfo':{'name':'yue2-music-director','version':'0.6'}}
            result=self.rpc('server/discover',{'_meta':info})
            if MODERN not in result.get('supportedVersions',[]):
                raise MCPError('Modern protocol unavailable')
            self.era='modern'
            return self
        except MCPError:
            self.version=LEGACY
            self.session=None
            result=self.rpc('initialize',{'protocolVersion':LEGACY,
                                          'capabilities':{},
                                          'clientInfo':{'name':'yue2-music-director','version':'0.6'}},
                            include_version=False)
            self.version=result.get('protocolVersion',LEGACY)
            self.era='legacy'
            self._post({'jsonrpc':'2.0','method':'notifications/initialized'},
                       'notifications/initialized')
            return self

    def tools(self):
        out=[]
        cursor=None
        for _ in range(12):
            params={}
            if cursor: params['cursor']=cursor
            if self.era=='modern': params['_meta']=self._meta()
            response=self.rpc('tools/list',params)
            out.extend(response.get('tools',[]))
            cursor=response.get('nextCursor')
            if not cursor: return out
        raise MCPError('Too many tools/list pages')

    def _meta(self):
        return {'io.modelcontextprotocol/protocolVersion':self.version,
                'io.modelcontextprotocol/clientCapabilities':{},
                'io.modelcontextprotocol/clientInfo':{'name':'yue2-music-director','version':'0.6'}}

    def call(self,name: str,arguments: dict):
        params={'name':name,'arguments':arguments}
        if self.era=='modern': params['_meta']=self._meta()
        result=self.rpc('tools/call',params,name)
        if not isinstance(result,dict) or result.get('isError'):
            raise MCPError(f'MCP tool {name} failed (inspect Studio; never retry submission blindly)')
        return result


def unpack(result):
    """Decode a read-only MCP tool result, preserving native structuredContent."""
    if isinstance(result,dict) and isinstance(result.get('structuredContent'),dict):
        return result['structuredContent']
    if isinstance(result,dict):
        for part in result.get('content',[]):
            if isinstance(part,dict) and part.get('type')=='text':
                try: return json.loads(part.get('text',''))
                except (TypeError,ValueError): pass
    return result

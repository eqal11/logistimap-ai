"""Bound optimization JSON bodies before Pydantic parses them."""
from starlette.responses import JSONResponse
class OptimizationBodyLimit:
    def __init__(self,app,max_bytes=1_500_000):self.app=app;self.max_bytes=max_bytes
    async def __call__(self,scope,receive,send):
        if scope["type"]!="http" or not scope.get("path","").startswith(("/api/optimization","/api/sites","/api/geoai")) or scope.get("method")!="POST":
            return await self.app(scope,receive,send)
        chunks=[];size=0;more=True
        while more:
            message=await receive()
            if message["type"]=="http.disconnect":return
            chunk=message.get("body",b"");size+=len(chunk)
            if size>self.max_bytes:
                return await JSONResponse({"error":{"code":"body_limit","message":"Optimization request exceeds 1.5 MB."}},status_code=413)(scope,receive,send)
            chunks.append(chunk);more=message.get("more_body",False)
        delivered=False
        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered=True;return {"type":"http.request","body":b"".join(chunks),"more_body":False}
            return await receive()
        return await self.app(scope,bounded_receive,send)

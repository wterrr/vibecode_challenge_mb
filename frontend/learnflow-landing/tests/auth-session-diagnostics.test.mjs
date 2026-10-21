import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const moduleSource = readFileSync(new URL('../src/api/learnflow.js', import.meta.url), 'utf8')
  .replaceAll('import.meta.env.VITE_API_BASE_URL', 'globalThis.__testApiBase');

let serial = 0;
async function createClient({base='', fetchImpl} = {}) {
  globalThis.__testApiBase = base;
  globalThis.window = {location: {origin:'https://learnflow.vibe.tinhgon.xyz'}};
  globalThis.fetch = fetchImpl;
  const url = `data:text/javascript;base64,${Buffer.from(moduleSource).toString('base64')}#${serial++}`;
  return await import(url);
}

function result(status, body, type='application/json') {
  return new Response(typeof body === 'string' ? body : JSON.stringify(body), {
    status, headers:{'content-type':type},
  });
}

test('fresh/expired session is a distinct 401, never a generic backend failure', async () => {
  const client=await createClient({fetchImpl:async()=>result(401,{detail:'Authentication required'})});
  await assert.rejects(client.getAuthSession(),err => {
    assert.equal(err.status,401);
    assert.match(err.message,/chưa đăng nhập|hết hạn/);
    return true;
  });
});

test('valid session fetch uses same-origin cookie and stores CSRF', async () => {
  let url, options;
  const client=await createClient({
    base:'https://learnflow.vibe.tinhgon.xyz/',
    fetchImpl:async (u,o) => {
      url=u;options=o;
      return result(200,{auth_required:true,authenticated:true,username:'admin',csrf_token:'a'.repeat(64)});
    },
  });
  const session=await client.getAuthSession();
  assert.equal(session.authenticated,true);
  assert.equal(url,'/api/auth/session');
  assert.equal(options.credentials,'same-origin');
  assert.equal(options.cache,'no-store');
});

test('cross-origin Vite API base never sends private session requests to another host', async () => {
  let request;
  const client=await createClient({
    base:'https://external-api.invalid',
    fetchImpl:async(url,options)=>{
      request={url,options};
      return result(401,{detail:'Authentication required'});
    },
  });
  await assert.rejects(client.getAuthSession(),{status:401});
  assert.equal(request.url,'/api/auth/session');
  assert.equal(request.options.credentials,'same-origin');
});

for (const [status, expected] of [
  [403, 'HTTP 403'],[404, 'HTTP 404'],[502,'HTTP 502'],
]) {
  test(`backend ${status} produces actionable status, not generic login failure`, async()=>{
    const client=await createClient({fetchImpl:async()=>result(status,{detail:'error'})});
    await assert.rejects(client.getAuthSession(),err=>{
      assert.equal(err.status,status);
      assert.match(err.message,new RegExp(expected));
      return true;
    });
  });
}

test('proxy returning HTML 200 is not accepted as an authenticated session', async()=>{
  const client=await createClient({
    fetchImpl:async()=>result(200,'<!doctype html><html><body>bad reverse proxy</body></html>','text/html'),
  });
  await assert.rejects(client.getAuthSession(),err=>{
    assert.match(err.message,/không phải JSON/);return true;
  });
});

test('invalid JSON and malformed auth payload fail closed',async()=>{
  const client=await createClient({fetchImpl:async()=>result(200,'{not-json','application/json')});
  await assert.rejects(client.getAuthSession(),/JSON hợp lệ/);
  globalThis.fetch=async()=>result(200,{auth_required:true,authenticated:true,csrf_token:''});
  await assert.rejects(client.getAuthSession(),/không đúng định dạng/);
});

test('network failure is reported separately from expired credentials',async()=>{
  const client=await createClient({fetchImpl:async()=>{throw new TypeError('blocked by proxy')}});
  await assert.rejects(client.getAuthSession(),err=>{
    assert.equal(err.status,0);
    assert.match(err.message,/Không kết nối được API đăng nhập/);
    return true;
  });
});

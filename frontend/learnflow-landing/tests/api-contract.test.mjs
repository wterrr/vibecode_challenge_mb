import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,writeFile,mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';

// Compile-free contract test: replace only Vite compile-time env in API JS.
const dir=await mkdtemp(join(tmpdir(),'learnflow-api-'));
const source=(await readFile(new URL('../src/api/learnflow.js',import.meta.url),'utf8'))
  .replaceAll('import.meta.env.VITE_API_BASE_URL', "''");
await writeFile(join(dir,'api.mjs'),source);
const api=await import(pathToFileURL(join(dir,'api.mjs')));

const oldFetch=globalThis.fetch;
test.after(async()=>{globalThis.fetch=oldFetch;await rm(dir,{recursive:true,force:true});});
const response=(status,body)=>({status,ok:status>=200&&status<300,json:async()=>body});

test('POST /api/jobs uses true FastAPI LearningRequest contract',async()=>{
  let observed;
  globalThis.fetch=async(url,init)=>{observed={url,init};return response(202,{job_id:'job-01',status_url:'/api/jobs/job-01'});};
  const result=await api.createLesson('Binary Search là gì?',{audience:'Beginner',language:'vi',duration:90});
  assert.equal(observed.url,'/api/jobs');
  assert.equal(observed.init.method,'POST');
  assert.deepEqual(JSON.parse(observed.init.body),{
    topic:'Binary Search là gì?',audience:'Beginner',language:'vi',target_duration_seconds:90,visual_style:'clean'
  });
  assert.equal(result.job_id,'job-01');
});

test('job status, library, delete, and health match real endpoint paths',async()=>{
  const paths=[];
  globalThis.fetch=async(url,opts)=>{paths.push([url,opts.method]);return response(opts.method==='DELETE'?204:200,{status:'ok'});};
  await api.checkBackend();await api.getLesson('job-01');await api.listLessons();await api.deleteLesson('job-01');
  assert.deepEqual(paths,[['/healthz','GET'],['/api/jobs/job-01','GET'],['/api/jobs?limit=30','GET'],['/api/jobs/job-01','DELETE']]);
});

test('no external or unapproved video URLs allowed',()=>{
  assert.equal(api.asMediaUrl('/api/jobs/abc/video'),'/api/jobs/abc/video');
  assert.equal(api.asMediaUrl('/api/v3/ai/array-preview/abc/video'),'/api/v3/ai/array-preview/abc/video');
  assert.equal(api.asMediaUrl('https://evil.example/video.mp4'),null);
  assert.equal(api.asMediaUrl('//evil.example'),null);
  assert.equal(api.asMediaUrl('javascript:alert(1)'),null);
});

test('backend 422 ABSTAIN is presented as a failure; not silently converted to sample',async()=>{
  globalThis.fetch=async()=>response(422,{detail:'UNSUPPORTED_ARRAY_TOPIC'});
  await assert.rejects(()=>api.createLesson('unsupported',{audience:'Beginner',language:'en',duration:60}),
    e=>e instanceof api.ApiError && e.status===422 && e.message==='UNSUPPORTED_ARRAY_TOPIC');
});

test('paid GPT preview sends explicit consent, only one caller-side POST, no library fallback',async()=>{
  let count=0,body;
  globalThis.fetch=async(url,opts)=>{assert.equal(url,'/api/v3/ai/array-preview');count++;body=JSON.parse(opts.body);return response(200,{status:'REAL_GPT_NATIVE_TECHNICAL_PREVIEW_NOT_PRODUCTION'});};
  await api.createPaidDevPreview('How can a 3 by 4 grid turn into a 4 by 3 grid?');
  assert.deepEqual(body,{query:'How can a 3 by 4 grid turn into a 4 by 3 grid?',language:'en',paid_consent:true});
  assert.equal(count,1);
});

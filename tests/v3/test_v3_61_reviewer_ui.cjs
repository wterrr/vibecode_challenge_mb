"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const u=require("../../learnflow_v3/review_ui/v361_reviewer.js");
const ids=["attention_reversed_query","fraction_equivalence","process_heldout_unknown"].flatMap(case_id=>["A","B","C"].map(n=>({case_id,clip_id:case_id+"_"+n+".mp4"})));
function rows(){return ids.map(x=>({...x,rater_id:"TEST_ONLY_001",clarity:"3",causal_witness:"3",semantic_continuity:"3",legibility:"3",pacing:"3",confidence:"3",watched_full_video:"YES",replay_count:"0",timestamp_failure_notes:""}))}
test("exact 9-row V3-60 schema export",()=>{const c=u.serializeCSV(rows(),ids,"TEST_ONLY_001");assert.equal(c.split("\n").length,11);assert.equal(c.split("\n")[0],u.FIELDS.join(","));assert.ok(!c.includes("treatment"))});
test("notes safely escaped; prevent spreadsheet injection",()=>{assert.equal(u.escapeCSV('6.5s: "confusing", note'),'"6.5s: ""confusing"", note"');const r=rows();r[0].timestamp_failure_notes="=HYPERLINK()";assert.throws(()=>u.serializeCSV(r,ids,"TEST_ONLY_001"),/formula/)});
test("negative corrupt missing forged and partial ratings",()=>{assert.throws(()=>u.serializeCSV(rows().slice(1),ids,"TEST_ONLY_001"),/nine/);
for(const [key,value,pattern] of [["clarity","","Score"],["clarity","6","Score"],["confidence","","confidence"],["watched_full_video","NO","Watch"],["clip_id","forged_A.mp4","Frozen"],["replay_count","-1","Replay"],["rater_id","OTHER","Inconsistent"]]){const r=rows();r[0][key]=value;assert.throws(()=>u.serializeCSV(r,ids,"TEST_ONLY_001"),new RegExp(pattern,"i"))}
const r=rows();r[0].clarity="2";assert.throws(()=>u.serializeCSV(r,ids,"TEST_ONLY_001"),/timestamp/);r[0].timestamp_failure_notes="8.2s: unreadable";assert.ok(u.serializeCSV(r,ids,"TEST_ONLY_001"))});
test("pseudonyms bounded to no-PII characters",()=>{assert.ok(u.validRater("reviewer_001"));for(const id of ["x","Person Name","name@example.com","=SUM()"])assert.ok(!u.validRater(id))});

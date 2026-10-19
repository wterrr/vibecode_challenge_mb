import {useCallback,useEffect,useRef,useState} from 'react';
import {ArrowUp,ArrowUpRight,CheckCircle2,ChevronDown,ExternalLink,LoaderCircle,PlayCircle,RotateCcw,Sparkles,Video,AlertCircle} from 'lucide-react';
import {asMediaUrl,checkBackend,createLesson,createPaidDevPreview,getLesson} from '../api/learnflow';

const SAMPLES = ['Đạo hàm là gì?', 'Binary Search hoạt động thế nào?', 'Vì sao các hành tinh có quỹ đạo?'];
const STAGES = {
  planning:'Lập kế hoạch bài học',validating_plan:'Kiểm tra kế hoạch',audio:'Tạo lời thuyết minh',
  rendering:'Dựng hình minh họa',assembling:'Ghép video',validating_output:'Kiểm tra video cuối',
};
const DEV_PREVIEW_ENABLED = import.meta.env.DEV && import.meta.env.VITE_ENABLE_LOCAL_GPT_PREVIEW === 'true';
const STORAGE_KEY='learnflow_last_job_id';
const PAID_ATTEMPT_KEY='learnflow_gpt_paid_attempted';
const hasPaidAttempt = () => {try{return sessionStorage.getItem(PAID_ATTEMPT_KEY)==='1';}catch{return false;}};
const readLast = () => {try{return window.localStorage.getItem(STORAGE_KEY)||'';}catch{return '';}};
const storeLast = id => {try{if(id)window.localStorage.setItem(STORAGE_KEY,id);else window.localStorage.removeItem(STORAGE_KEY);}catch{}};

function errorText(job) {
  const item=job?.error;
  if (!item) return 'Backend báo job thất bại. Xem log máy chủ để biết nguyên nhân.';
  if (typeof item === 'string') return item;
  return item.message || item.user_message || item.code || 'Không thể hoàn tất bài học này.';
}

export default function PromptComposer(){
  const [value,setValue]=useState('');
  const [audience,setAudience]=useState('Beginner');
  const [language,setLanguage]=useState('vi');
  const [duration,setDuration]=useState(90);
  const [advanced,setAdvanced]=useState(false);
  const [online,setOnline]=useState(null);
  const [activeId,setActiveId]=useState(readLast);
  const [job,setJob]=useState(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [pollError,setPollError]=useState('');
  const [mode,setMode]=useState('jobs');
  const [consent,setConsent]=useState(false);
  const [paidAttempted,setPaidAttempted]=useState(hasPaidAttempt);
  const [paidPreview,setPaidPreview]=useState(null);
  const textRef=useRef(null);
  const submitting=useRef(false);
  const requestController=useRef(null);

  useEffect(()=>{
    const ctrl=new AbortController();
    checkBackend(ctrl.signal).then(r=>setOnline(r?.status==='ok')).catch(()=>setOnline(false));
    return ()=>ctrl.abort();
  },[]);

  const refresh=useCallback((id)=>{
    if(!id)return;
    setPollError('');
    getLesson(id).then(setJob).catch(e=>setPollError(e.message));
  },[]);

  useEffect(()=>{
    const open=(event)=>{
      const id=event.detail?.id;
      if(typeof id!=='string' || !id)return;
      setPaidPreview(null);setJob(null);setError('');setActiveId(id);storeLast(id);
      document.getElementById('try')?.scrollIntoView({behavior:'smooth',block:'center'});
    };
    window.addEventListener('learnflow:open-job',open);
    return ()=>window.removeEventListener('learnflow:open-job',open);
  },[]);

  useEffect(()=>{
    if(!activeId)return;
    let mounted=true;let polling=false;
    const ctrl=new AbortController();
    const fetchCurrent=async()=>{
      if(polling)return;
      polling=true;
      try{
        const data=await getLesson(activeId,ctrl.signal);
        if(mounted){setJob(data);setPollError('');}
      }catch(e){if(mounted)setPollError(e.message);}
      finally{polling=false;}
    };
    fetchCurrent();
    const timer=setInterval(()=>{if(!['succeeded','failed'].includes(job?.status))fetchCurrent();},2500);
    return ()=>{mounted=false;ctrl.abort();clearInterval(timer);};
  },[activeId,job?.status]);

  useEffect(()=>()=>requestController.current?.abort(),[]);

  const submit=async()=>{
    const query=value.trim();
    if(query.length<3 || busy || submitting.current)return;
    if(mode==='gpt'){
      if(!DEV_PREVIEW_ENABLED){setError('Preview GPT chỉ mở trong chế độ local development.');return;}
      if(query.length<35||query.length>300||language!=='en'){
        setError('Preview GPT yêu cầu câu hỏi tiếng Anh dài 35–300 ký tự về mảng 3×4 ↔ 4×3.');return;
      }
      if(!consent){setError('Bạn cần chủ động đánh dấu đồng ý gọi API GPT trả phí.');return;}
      if(paidAttempted){setError('Phiên trình duyệt này đã thực hiện một lượt GPT. Không tự retry; vui lòng kiểm tra backend.');return;}
    }
    submitting.current=true;setBusy(true);setError('');setPollError('');
    try{
      if(mode==='gpt'){
        // Paid POST: NEVER retry from this UI, even after network timeout.
        setPaidPreview(null);setJob(null);setActiveId('');storeLast('');
        // Lock this browser tab/session before the network request starts.
        setPaidAttempted(true);
        try{sessionStorage.setItem(PAID_ATTEMPT_KEY,'1');}catch{}
        const data=await createPaidDevPreview(query);
        if(data?.status!=='REAL_GPT_NATIVE_TECHNICAL_PREVIEW_NOT_PRODUCTION'||!asMediaUrl(data.video_url)){
          throw new Error('Backend không trả về video đã được xác minh.');
        }
        setPaidPreview(data);
      }else{
        const ctrl=new AbortController();requestController.current=ctrl;
        const data=await createLesson(query,{audience,language,duration},ctrl.signal);
        if(!data?.job_id||!data?.status_url)throw new Error('Backend không trả về mã job hợp lệ.');
        setPaidPreview(null);setJob(null);setActiveId(data.job_id);storeLast(data.job_id);
        window.dispatchEvent(new Event('learnflow:jobs-changed'));
      }
      setOnline(true);
    }catch(e){setError(e.message||'Yêu cầu thất bại.');}
    finally{requestController.current=null;submitting.current=false;setBusy(false);}
  };

  const reset=()=>{
    if(busy)return;
    setValue('');setJob(null);setActiveId('');setPaidPreview(null);setError('');setPollError('');
    storeLast('');textRef.current?.focus();
  };
  const videoSrc=asMediaUrl(paidPreview?.video_url || (job?.status==='succeeded'&&job.video_url));
  const isRunning=job && ['queued','running'].includes(job.status);
  const isDone=job?.status==='succeeded';

  return <div className="hero-composer" id="try">
    <div className="composer-card">
      <label className="sr-only" htmlFor="learning-prompt">Chủ đề hoặc câu hỏi bạn muốn tìm hiểu</label>
      <textarea ref={textRef} id="learning-prompt" value={value} rows={3} onChange={e=>setValue(e.target.value)}
        onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();submit();}}}
        maxLength={500} placeholder="Nhập chủ đề hoặc câu hỏi bạn muốn tìm hiểu..." aria-label="Nhập chủ đề học tập"/>
      <div className="composer-toolbar">
        <span className="composer-assist">Enter để tạo video · Shift + Enter để xuống dòng</span>
        <button className="composer-submit" type="button" onClick={submit} disabled={busy||value.trim().length<3||(mode==='gpt'&&paidAttempted)} aria-label="Tạo bài học thật bằng LearnFlow" title="Tạo video">{busy?<LoaderCircle className="spin" size={20}/>:<ArrowUp size={20}/>}</button>
      </div>
    </div>
    <div className="lf-options-row">
      <div className="lf-service" aria-label="Kết nối backend" role="status"><i className={online===true?'ready':online===false?'offline':''}/>{online===true?'Đã kết nối máy chủ':online===false?'Chưa kết nối backend':'Đang kiểm tra máy chủ'}</div>
      <button type="button" className="lf-option-toggle" aria-expanded={advanced} onClick={()=>setAdvanced(v=>!v)}>Tùy chọn bài học <ChevronDown size={14} className={advanced?'flipped':''}/></button>
    </div>
    {advanced && <div className="lf-options-panel">
      <label>Đối tượng<select value={audience} onChange={e=>setAudience(e.target.value)}><option value="Beginner">Người mới bắt đầu</option><option value="Student">Học sinh / Sinh viên</option><option value="Developer">Lập trình viên</option><option value="Professional">Đi làm / Chuyên gia</option></select></label>
      <label>Ngôn ngữ<select value={language} onChange={e=>setLanguage(e.target.value)}><option value="vi">Tiếng Việt</option><option value="en">English</option></select></label>
      <label>Thời lượng dự kiến<select value={duration} onChange={e=>setDuration(Number(e.target.value))}><option value={60}>60 giây</option><option value={90}>90 giây</option><option value={120}>120 giây</option></select></label>
      {DEV_PREVIEW_ENABLED && <div className="lf-exp-preview">
        <label className="lf-mode-option"><input type="radio" checked={mode==='jobs'} onChange={()=>setMode('jobs')}/> Hệ thống tạo bài học (/api/jobs)</label>
        <label className="lf-mode-option"><input type="radio" checked={mode==='gpt'} onChange={()=>{setMode('gpt');setLanguage('en');}}/> GPT-6 trả phí — thử nghiệm local 3×4 ↔ 4×3</label>
        {mode==='gpt' && paidAttempted && <span className="lf-paid-lock">Đã sử dụng lượt GPT cho phiên này. Không thể gửi thêm từ giao diện.</span>}
        {mode==='gpt' && <label className="lf-mode-option"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/> Tôi đồng ý cho phép một request GPT trả phí. Không tự retry; chi phí token chỉ là ước tính, không phải giới hạn hóa đơn.</label>}
      </div>}
    </div>}
    {!activeId&&!paidPreview && <div className="composer-suggestions">{SAMPLES.map(q=><button key={q} type="button" onClick={()=>{setValue(q);textRef.current?.focus();}}>{q} <ArrowUpRight size={12}/></button>)}</div>}
    {error&&<div className="lf-alert" role="alert"><AlertCircle size={17}/><span>{error}</span></div>}
    {(activeId||paidPreview)&&<div className="lf-result" aria-live="polite">
      <div className="lf-result-header"><span><Sparkles size={16}/> VIDEO BÀI HỌC</span><button type="button" onClick={reset} disabled={busy}><RotateCcw size={14}/> Tạo bài khác</button></div>
      {paidPreview? <>
        <h3>GPT đã tạo video preview</h3><p className="lf-result-note">Model: {paidPreview.model} · {paidPreview.frame_count} frames. Đây là preview kỹ thuật giới hạn, chưa nghiệm thu sư phạm và không phải bản production.</p>
      </> : job? <>
        <h3>{job.display_title||job.topic}</h3>
        <div className="lf-statusline">{isRunning?<LoaderCircle className="spin" size={17}/>:isDone?<CheckCircle2 size={17}/>:<AlertCircle size={17}/>}
          <strong>{job.status==='queued'?'Đang chờ xử lý':job.status==='running'?(STAGES[job.stage]||'Đang tạo video'):isDone?'Video đã sẵn sàng':'Không thể hoàn thành'}</strong>
          <span>{job.progress_percent||0}%</span>
        </div>
        <div className="lf-progress-track" role="progressbar" aria-valuenow={job.progress_percent||0} aria-valuemin={0} aria-valuemax={100}><i style={{width:`${job.progress_percent||0}%`}}/></div>
        {job.status==='failed'&&<p className="lf-failure" role="alert">{errorText(job)}</p>}
        {isDone&&!videoSrc&&<p className="lf-failure">Job đã thành công nhưng backend chưa cung cấp MP4. Hãy kiểm tra artifact store.</p>}
      </> : <div className="lf-statusline"><LoaderCircle className="spin" size={17}/> Đang lấy trạng thái job...</div>}
      {pollError&&<div className="lf-alert" role="status"><AlertCircle size={15}/>{pollError} <button type="button" onClick={()=>refresh(activeId)}>Thử kiểm tra lại</button></div>}
      {videoSrc&&<div className="lf-video-wrap"><video key={videoSrc} src={videoSrc} controls playsInline preload="metadata" aria-label="Video bài học LearnFlow vừa được tạo"/><div className="lf-video-actions"><a href={videoSrc} download>Tải / mở video <ExternalLink size={15}/></a><span>{paidPreview?'Chỉ xem qua developer preview': 'Video do backend tạo, không phải phim Gemini ở bên dưới'}</span></div></div>}
      {job&&<small className="lf-technical-note">Mã job: {job.id} · Lưu và tiếp tục kiểm tra trạng thái khi tải lại trang.</small>}
    </div>}
    {busy&&<p className="lf-busy-note" role="status"><LoaderCircle className="spin" size={14}/> {mode==='gpt'?'Đang chạy request GPT duy nhất; không tải lại trang hoặc gửi lần hai.':'Đang gửi yêu cầu tới backend...'}</p>}
    <p className="composer-footnote">Tạo video qua API LearnFlow · Kết quả chỉ xuất hiện khi backend xử lý và kiểm tra thành công. Video Gemini bên dưới là phim giới thiệu sản phẩm.</p>
  </div>;
}

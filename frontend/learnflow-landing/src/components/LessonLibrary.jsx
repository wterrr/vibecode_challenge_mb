import {useEffect,useState} from 'react';
import {BookOpen,CheckCircle2,Clock3,ExternalLink,LoaderCircle,RefreshCw,Trash2} from 'lucide-react';
import {deleteLesson,listLessons} from '../api/learnflow';

const LABEL={queued:'Đang chờ',running:'Đang xử lý',succeeded:'Hoàn tất',failed:'Thất bại'};
export default function LessonLibrary(){
  const [jobs,setJobs]=useState([]);
  const [loaded,setLoaded]=useState(false);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [filter,setFilter]=useState('all');
  const load=async()=>{
    setBusy(true);setError('');
    try{const data=await listLessons();setJobs(Array.isArray(data)?data:[]);setLoaded(true);}
    catch(e){setError(e.message);}
    finally{setBusy(false);}
  };
  useEffect(()=>{
    load();
    const change=()=>load();
    window.addEventListener('learnflow:jobs-changed',change);
    return ()=>window.removeEventListener('learnflow:jobs-changed',change);
  },[]);
  const visible=jobs.filter(j=>filter==='all'||j.status===filter);
  const open=id=>window.dispatchEvent(new CustomEvent('learnflow:open-job',{detail:{id}}));
  const remove=async job=>{
    if(['queued','running'].includes(job.status))return;
    if(!window.confirm(`Xóa bài học “${job.display_title||job.topic}”? Tệp video đi kèm cũng sẽ bị xóa.`))return;
    try{await deleteLesson(job.id);await load();}catch(e){setError(e.message);}
  };
  return <section className="lf-library section-pad" id="library"><div className="container">
    <div className="lf-library-title"><div><span className="lf-library-eyebrow">YOUR CREATIONS ✳</span><h2>Thư viện <em>bài học.</em></h2><p>Theo dõi các video đã yêu cầu và mở lại những bài học trước đó.</p></div><button type="button" onClick={load} disabled={busy} className="lf-library-refresh"><RefreshCw size={16} className={busy?'spin':''}/> Làm mới</button></div>
    <div className="lf-library-filters" aria-label="Bộ lọc bài học">{[['all','Tất cả'],['succeeded','Hoàn tất'],['running','Đang tạo'],['failed','Thất bại']].map(([id,label])=><button type="button" key={id} aria-pressed={filter===id} className={filter===id?'active':''} onClick={()=>setFilter(id)}>{label}</button>)}</div>
    {error&&<div className="lf-alert" role="alert">{error}</div>}
    {visible.length? <div className="lf-library-grid">{visible.map(job=><article className="lf-lesson-card" key={job.id}>
      <div className="lf-lesson-card-top"><span className={`lf-lesson-status status-${job.status}`}>{job.status==='succeeded'?<CheckCircle2 size={13}/>:<Clock3 size={13}/>} {LABEL[job.status]||job.status}</span><span>{job.language==='en'?'EN':'VI'} · {job.target_duration_seconds}s</span></div>
      <h3>{job.display_title||job.topic}</h3><p>{new Date(job.created_at).toLocaleString('vi-VN',{dateStyle:'short',timeStyle:'short'})}</p>
      <div className="lf-card-actions"><button type="button" onClick={()=>open(job.id)}><ExternalLink size={15}/> Xem bài học</button>
      {!['queued','running'].includes(job.status)&&<button type="button" className="lf-delete" aria-label="Xóa bài học" onClick={()=>remove(job)}><Trash2 size={16}/></button>}</div>
    </article>)}</div>:<div className="lf-library-empty">{busy?<LoaderCircle className="spin" size={23}/>:<BookOpen size={27}/>}<p>{!loaded?'Đang tải thư viện…':filter==='all'?'Chưa có bài học nào. Hãy thử nhập một câu hỏi ở phía trên.':'Không có bài học ở trạng thái này.'}</p></div>}
    <p className="lf-library-note">Trạng thái lấy trực tiếp từ /api/jobs; không hiển thị dữ liệu mẫu. Video được bảo vệ bằng phiên đăng nhập quản trị và API riêng tư khi chạy production.</p>
  </div></section>;
}

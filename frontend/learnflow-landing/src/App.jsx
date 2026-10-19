import {useEffect,useRef,useState} from 'react';
import {ArrowDown,ArrowLeft,ArrowRight,ArrowUp,ArrowUpRight,BookOpen,ChevronLeft,ChevronRight,Layers3,Menu,Moon,MousePointer2,Pause,Play,RotateCcw,SlidersHorizontal,Sparkles,Sun,Video,Volume2,VolumeX,WandSparkles,X} from 'lucide-react';
import MascotActor from './components/MascotActor';
import OpeningIntro from './components/OpeningIntro';
import PromptComposer from './components/PromptComposer';
import LessonLibrary from './components/LessonLibrary';
import AnimatedContent from './components/reactbits/AnimatedContent';
import './styles.css';

const EXAMPLES = [
  {id:'math',category:'TOÁN HỌC',name:'Đạo hàm',title:'Nhìn thấy sự thay đổi, thay vì chỉ ghi nhớ công thức.',description:'Một đường cong, một tiếp tuyến và khoảnh khắc bạn nhận ra đạo hàm thực sự có nghĩa gì.',color:'lilac',duration:'01:20',index:'01'},
  {id:'algorithm',category:'KHOA HỌC MÁY TÍNH',name:'Binary Search',title:'Một thuật toán trở nên dễ hiểu khi từng bước hiện ra.',description:'Theo dõi cách khoảng tìm kiếm thu hẹp để tìm ra đáp án — từ trực giác đến logic.',color:'peach',duration:'01:45',index:'02'},
  {id:'science',category:'KHOA HỌC',name:'Chuyển động quỹ đạo',title:'Khi những khái niệm trừu tượng bắt đầu chuyển động.',description:'Dùng hình ảnh chuyển động để nhìn các mối quan hệ mà một đoạn văn khó mô tả hết.',color:'mint',duration:'02:10',index:'03'}
];
const ALGO_STEPS = [
 {low:0,high:8,mid:4,note:'Bắt đầu với toàn bộ danh sách đã sắp xếp.',found:false},
 {low:5,high:8,mid:6,note:'23 lớn hơn 16. Bỏ nửa bên trái.',found:false},
 {low:5,high:5,mid:5,note:'23 nhỏ hơn 38. Chỉ còn một phần tử.',found:false},
 {low:5,high:5,mid:5,note:'Đã tìm thấy số 23 ở vị trí thứ 6!',found:true},
];
const VALUES=[2,5,8,12,16,23,38,56,72];
function Brand(){return <a className="brand" href="#top" aria-label="LearnFlow — về đầu trang"><span className="brand-symbol" aria-hidden="true"><i/><i/><i/><i/></span><span>learnflow<span className="brand-dot">.</span></span></a>}
function Eyebrow({children}){return <div className="eyebrow"><span className="asterisk">✳</span>{children}</div>}
function Header(){
 const [open,setOpen]=useState(false);
 const [theme,setTheme]=useState('light');
 useEffect(()=>{document.documentElement.dataset.theme=theme;},[theme]);
 const close=()=>setOpen(false);
 return <header className="site-header"><div className="nav-inner"><Brand/><nav className={`nav-links ${open?'nav-open':''}`} aria-label="Điều hướng chính"><a href="#explore" onClick={close}>Khám phá</a><a href="#experience" onClick={close}>Trải nghiệm</a><a href="#library" onClick={close}>Thư viện</a><a href="#how" onClick={close}>Cách hoạt động</a><a href="#purpose" onClick={close}>Về LearnFlow</a></nav><div className="nav-right"><button className="theme-button" onClick={()=>setTheme(v=>v==='light'?'dark':'light')} aria-label={theme==='light'?'Chuyển giao diện tối':'Chuyển giao diện sáng'}>{theme==='light'?<Moon size={18}/>:<Sun size={18}/>}</button><a className="btn btn-dark nav-primary" href="#try">Bắt đầu khám phá <ArrowUpRight size={16}/></a><button className="mobile-menu" aria-label={open?'Đóng menu':'Mở menu'} aria-expanded={open} onClick={()=>setOpen(v=>!v)}>{open?<X size={22}/>:<Menu size={22}/>}</button></div></div></header>
}
function DerivativeArt({x=1.5,large=false}){
 const W=590,H=360,L=64,B=295,sX=160,sY=40;
 const px=v=>L+v*sX;
 const py=v=>B-v*v*sY;
 const path=Array.from({length:91},(_,i)=>{let a=i*3.03/90;return `${i?'L':'M'} ${px(a).toFixed(2)} ${py(a).toFixed(2)}`}).join(' ');
 return <svg className={`graph-svg ${large?'large':''}`} viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Đồ thị hàm số y bằng x bình phương và tiếp tuyến tại x bằng ${x.toFixed(1)}`}>
  <defs><pattern id={large?'grid-large':'grid-small'} width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0 H0 V40" fill="none" stroke="currentColor" strokeOpacity=".055"/></pattern><linearGradient id={large?'line-large':'line-small'} x1="0" y1="1" x2="1" y2="0"><stop stopColor="#9985fc"/><stop offset="1" stopColor="#6c50de"/></linearGradient></defs>
  <rect width={W} height={H} fill={`url(#${large?'grid-large':'grid-small'})`} rx="14"/>
  <line x1={L} x2="555" y1={B} y2={B} stroke="currentColor" strokeOpacity=".3" strokeWidth="1.5"/>
  <line x1={L} x2={L} y1="24" y2={B+15} stroke="currentColor" strokeOpacity=".3" strokeWidth="1.5"/>
  {[1,2,3].map(v=><text key={v} x={px(v)} y={B+23} fill="currentColor" opacity=".45" textAnchor="middle" fontSize="12">{v}</text>)}
  <text x="74" y="40" fill="#7964e7" fontSize="18" fontWeight="750" fontFamily="inherit">y = x²</text>
  <text x="540" y="319" fill="currentColor" opacity=".5" fontSize="12">x</text>
  <path d={path} fill="none" stroke={`url(#${large?'line-large':'line-small'})`} strokeWidth={large?5:4} strokeLinecap="round"/>
  <line x1={px(x-.83)} y1={py(x)+(.83*2*x*sY)} x2={px(x+.83)} y2={py(x)-(.83*2*x*sY)} stroke="#f49b71" strokeWidth="3" strokeLinecap="round"/>
  <line x1={px(x)} y1={py(x)} x2={px(x)} y2={B} stroke="#937ae8" strokeWidth="1.6" strokeDasharray="5 7" opacity=".5"/>
  <circle cx={px(x)} cy={py(x)} r="11" fill="#a893ff" opacity=".19"/><circle cx={px(x)} cy={py(x)} r="6" fill="#7457e6" stroke="#fff" strokeWidth="2.4"/>
  <g transform={`translate(${Math.min(px(x)+12,447)},${Math.max(py(x)-51,25)})`}><rect width="115" height="34" rx="11" fill="#ffffff" stroke="#e8e0ff"/><text x="14" y="22" fill="#503bc1" fontSize="13" fontWeight="750">f′(x) = {(2*x).toFixed(1)}</text></g>
 </svg>;
}
function AlgorithmArt({step=0}){
 const s=ALGO_STEPS[step];
 return <div className="algo-visual" aria-label="Minh họa các bước tìm kiếm nhị phân"><div className="algo-topline"><span>sorted_array</span><span>target = <b>23</b></span></div><div className="algo-bars">{VALUES.map((v,i)=>{const inactive=i<s.low||i>s.high,mid=i===s.mid;return <div key={v} className={`algo-bar ${inactive?'removed':''} ${mid?'selected':''} ${s.found&&mid?'found':''}`}><div className="bar-shape" style={{height:`${36+v*1.45}px`}}/><b>{v}</b><span>{String(i).padStart(2,'0')}</span></div>})}</div><div className="algo-annotation"><span className="algo-line"/><span>{s.note}</span></div></div>;
}
function OrbitArt(){return <div className="orbit-visual" role="img" aria-label="Minh họa chuyển động quỹ đạo với các hành tinh"><div className="orbit-streak orbit-streak-a"/><div className="orbit-streak orbit-streak-b"/><div className="space-star s-a"/><div className="space-star s-b"/><div className="space-star s-c"/><div className="space-star s-d"/><div className="orbit-ring orbit-ring-one"><div className="orbit-planet orbit-planet-a"/></div><div className="orbit-ring orbit-ring-two"><div className="orbit-planet orbit-planet-b"/></div><div className="orbit-ring orbit-ring-three"><div className="orbit-planet orbit-planet-c"/></div><div className="orbit-sun"><span/></div><span className="orbit-caption">GRAVITY / MOTION</span></div>}
function Visual({kind,x=1.5,step=0,large=false}){return kind==='math'?<DerivativeArt x={x} large={large}/>:kind==='algorithm'?<AlgorithmArt step={step}/>:<OrbitArt/>}
function formatVideoTime(value){
 const seconds=Number.isFinite(value)?Math.floor(value):0;
 return `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;
}
function HeroVideo(){
 const videoRef=useRef(null);
 const [playing,setPlaying]=useState(false);
 const [progress,setProgress]=useState(0);
 const [duration,setDuration]=useState(10);
 const [muted,setMuted]=useState(true);
 const [reducedMotion,setReducedMotion]=useState(()=>typeof window!=='undefined'&&window.matchMedia('(prefers-reduced-motion: reduce)').matches);
 const [videoError,setVideoError]=useState(false);
 useEffect(()=>{
   const media=window.matchMedia('(prefers-reduced-motion: reduce)');
   const onPreferenceChange=()=>{setReducedMotion(media.matches);if(media.matches)videoRef.current?.pause();};
   media.addEventListener?.('change',onPreferenceChange);
   return ()=>media.removeEventListener?.('change',onPreferenceChange);
 },[]);
 const togglePlayback=async()=>{
   const video=videoRef.current;
   if(!video||videoError)return;
   if(!video.paused){video.pause();return;}
   try{await video.play();}catch{setPlaying(false);}
 };
 const currentTime=progress*duration;
 return <div className="hero-player hero-video-player">
   <div className="hero-video-canvas">
     {videoError ? <div className="hero-video-fallback" role="status"><img src={`${import.meta.env.BASE_URL}media/learnflow-product-film-poster.webp`} alt="Minh họa hình học màu tím cho ý tưởng học trực quan"/><span>Không thể phát video trên trình duyệt này.</span></div> :
       <video ref={videoRef} className="hero-motion-video" src={`${import.meta.env.BASE_URL}media/learnflow-product-film.mp4`} poster={`${import.meta.env.BASE_URL}media/learnflow-product-film-poster.webp`} autoPlay={!reducedMotion} playsInline muted={muted} loop preload="metadata" aria-label="Video giới thiệu LearnFlow: từ câu hỏi đến nghiên cứu, sơ đồ và thiết kế video giáo dục" onPlay={()=>setPlaying(true)} onPause={()=>setPlaying(false)} onError={()=>setVideoError(true)} onLoadedMetadata={e=>setDuration(e.currentTarget.duration||10)} onTimeUpdate={e=>{const v=e.currentTarget;setProgress(v.duration?v.currentTime/v.duration:0);}} />}
   </div>
   <div className="player-controls">
     <button className="player-play" onClick={togglePlayback} disabled={videoError} aria-label={playing?'Tạm dừng video':'Phát video'}>{playing?<Pause size={15} fill="currentColor"/>:<Play size={15} fill="currentColor"/>}</button>
     <div className="player-progress" role="progressbar" aria-label="Tiến độ video" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress*100)}><i style={{width:`${progress*100}%`}}/></div>
     <span className="player-timestamp">{formatVideoTime(currentTime)} / {formatVideoTime(duration)}</span>
     <button type="button" className="player-sound" onClick={()=>setMuted(v=>!v)} disabled={videoError} aria-label={muted?'Bật âm thanh video':'Tắt âm thanh video'} aria-pressed={!muted}>{muted?<VolumeX size={15}/>:<Volume2 size={15}/>}</button>
     <span className="player-hd">HD</span>
   </div>
 </div>;
}
function Hero(){
 return <section className="hero hero-workspace section-pad" id="top">
   <div className="hero-blob hero-blob-left"/><div className="hero-blob hero-blob-right"/>
   <div className="hero-container">
     <div className="hero-focus">
       <div className="hero-heading"><h1>Hôm nay bạn muốn tìm hiểu điều gì?</h1></div>
       <PromptComposer/>
     </div>
     <div className="hero-stage" aria-label="Video minh họa LearnFlow">
       <div className="hero-stage-glow"/>
       <HeroVideo/>
       <div className="pixel-friend friend-one"><div className="friend-circle friend-purple"><MascotActor name="insight" label="Nhân vật LearnFlow với bóng đèn ý tưởng"/></div></div>
       <div className="pixel-friend friend-two"><div className="friend-circle friend-peach"><MascotActor name="learner" label="Nhân vật LearnFlow tóc cam với cuốn sách"/></div></div>
     </div>
   </div>
 </section>;
}

function Marquee(){return <div className="word-ribbon" aria-hidden="true"><div>IMAGINE <span>✳</span> EXPLORE <span>✳</span> UNDERSTAND <span>✳</span> CONNECT <span>✳</span> IMAGINE <span>✳</span> EXPLORE <span>✳</span> UNDERSTAND <span>✳</span></div></div>}
function Showcase(){
 const [tab,setTab]=useState('math'); const [step,setStep]=useState(0);const [x,setX]=useState(1.5);
 const item=EXAMPLES.find(e=>e.id===tab);
 const changeTab=v=>{setTab(v);setStep(0);};
 return <section id="explore" className="showcase-section section-pad"><div className="container"><AnimatedContent><div className="section-intro center"><Eyebrow>KHÁM PHÁ QUA HÌNH ẢNH</Eyebrow><h2>Để ý tưởng <em>tự cất lời.</em></h2><p>Không phải một bức tường toàn chữ. Mỗi chủ đề là một thế giới nhỏ được kể bằng hình ảnh, nhịp điệu và sự tò mò.</p></div></AnimatedContent>
 <div className="showcase-tabs" role="tablist" aria-label="Chọn ví dụ minh họa">{EXAMPLES.map(e=><button key={e.id} id={`tab-${e.id}`} role="tab" aria-selected={tab===e.id} aria-controls="example-panel" className={`showcase-tab ${tab===e.id?'active':''}`} onClick={()=>changeTab(e.id)}><span>{e.index}</span>{e.name}<ArrowUpRight size={15}/></button>)}</div>
 <div className={`showcase-board board-${item.color}`} id="example-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}><div className="showcase-copy"><span className="showcase-category"><i/> {item.category} <span>/</span> {item.duration}</span><span className="showcase-index">0{EXAMPLES.findIndex(e=>e.id===tab)+1} <small>/ 03</small></span><h3>{item.title}</h3><p>{item.description}</p><div className="showcase-copy-bottom"><span><Sparkles size={15}/> Storytelling, not slides.</span><span>MINH HỌA TƯƠNG TÁC <ArrowUpRight size={14}/></span></div></div><div className="showcase-visual"><div className="visual-window"><div className="visual-window-top"><span><i/><i/><i/></span><span>visual / {item.id}</span><span>✳</span></div><div className={`visual-window-content content-${item.id}`}><Visual kind={item.id} step={step} x={x}/></div><div className="visual-window-bottom">{tab==='algorithm'?<><button onClick={()=>setStep(v=>Math.max(0,v-1))} disabled={step===0} aria-label="Quay lại bước trước"><ChevronLeft size={16}/></button><span>STEP {step+1} / 04</span><button onClick={()=>setStep(v=>Math.min(3,v+1))} disabled={step===3} aria-label="Bước kế tiếp"><ChevronRight size={16}/></button></>:tab==='math'?<><span>Vị trí x</span><input aria-label="Thay đổi vị trí x trong ví dụ đạo hàm" type="range" min="0.4" max="2.6" step="0.1" value={x} onChange={e=>setX(Number(e.target.value))}/><b>{x.toFixed(1)}</b></>:<><span><span className="orbit-activity"/> ORBITAL MOTION</span><span>∞ LOOP</span></>}</div></div><span className="showcase-corner-mark">✳</span></div></div>
 <div className="showcase-disclaimer"><Sparkles size={15}/> Đây là minh họa tương tác thiết kế cho landing page, <strong>không phải video được render bởi LearnFlow.</strong> Thay bằng video thật sau khi kiểm định chất lượng.</div></div></section>;
}
function InteractiveLesson(){const [x,setX]=useState(1.3);return <section id="experience" className="experience-section section-pad"><div className="container experience-grid"><AnimatedContent><div className="experience-copy"><Eyebrow>HỌC BẰNG CÁCH KHÁM PHÁ</Eyebrow><h2>Đừng chỉ xem.<br/><em>Hãy tự khám phá.</em></h2><p>Thử kéo một điểm trên đường cong. Một thay đổi nhỏ trong hình ảnh có thể giúp bạn hiểu cả một khái niệm tưởng như rất khó.</p><div className="experience-points"><div><span><MousePointer2 size={18}/></span><div><b>Chạm vào kiến thức</b><p>Thay đổi một giá trị, nhìn kết quả chuyển động tức thì.</p></div></div><div><span><Sparkles size={18}/></span><div><b>Hiểu vì sao, không chỉ nhớ</b><p>Ý nghĩa được xây dựng từ trực giác trước khi đi đến công thức.</p></div></div></div><div className="experience-signature"><span>✳</span> INSPIRED BY CURIOSITY, BUILT FOR CLARITY.</div></div></AnimatedContent><AnimatedContent direction="horizontal" distance={55}><div className="interactive-card"><div className="interactive-heading"><div><span className="interactive-label"><span/> MINI LESSON / 001</span><h3>Độ dốc thay đổi như thế nào?</h3></div><span className="interactive-icon"><SlidersHorizontal size={20}/></span></div><div className="interactive-graph"><DerivativeArt x={x} large/></div><div className="interactive-panel"><div className="panel-range-label"><span>Kéo để thay đổi vị trí trên đồ thị</span><b>x = {x.toFixed(1)}</b></div><input type="range" min="0.4" max="2.6" step="0.1" value={x} onChange={e=>setX(Number(e.target.value))} aria-label="Vị trí x trên đồ thị"/><div className="formula-readout"><div><small>HÀM SỐ</small><strong>f(x) = x²</strong></div><span><ArrowRight size={21}/></span><div><small>ĐỘ DỐC TẠI x</small><strong>f′(x) = {(2*x).toFixed(1)}</strong></div></div></div><div className="interactive-footer"><span><span className="handdrawn-star">✷</span> Try it yourself</span><button onClick={()=>setX(1.3)}><RotateCcw size={14}/> Đặt lại</button></div></div></AnimatedContent></div></section>}
function Process(){const [active,setActive]=useState(0);const steps=[{tag:'YOUR CURIOSITY',name:'Bắt đầu với một ý tưởng',body:'Một câu hỏi, một khái niệm hoặc một điều bạn muốn giải thích.',icon:BookOpen},{tag:'VISUAL STORYBOARD',name:'Biến kiến thức thành câu chuyện',body:'Sắp xếp nội dung thành từng cảnh, hình ảnh và nhịp giải thích có chủ đích.',icon:Layers3},{tag:'EDUCATIONAL VIDEO',name:'Đưa lời giải thích vào chuyển động',body:'Một video trực quan giúp người xem theo dõi ý tưởng từ đầu đến cuối.',icon:Video}];return <section id="how" className="process-section section-pad"><div className="container"><AnimatedContent><div className="process-head"><div><Eyebrow>ĐƠN GIẢN ĐỂ BẮT ĐẦU</Eyebrow><h2>Từ một câu hỏi.<br/><em>Đến một câu chuyện.</em></h2></div><p>Một quy trình có thể phức tạp ở bên trong, nhưng trải nghiệm người học cần rõ ràng và gần gũi ở bên ngoài.</p></div></AnimatedContent><div className="process-layout"><div className="process-list">{steps.map((s,i)=><button className={`process-step ${active===i?'selected':''}`} key={s.tag} onClick={()=>setActive(i)} aria-pressed={active===i}><span className="process-number">0{i+1}</span><div><span className="process-tag">{s.tag}</span><h3>{s.name}</h3><p>{s.body}</p></div><span className="process-circle"><ArrowUpRight size={17}/></span></button>)}</div><div className="process-stage"><div className="process-stage-head"><span><span/> LEARNFLOW / WORKFLOW</span><span>0{active+1} / 03</span></div>{active===0?<div className="stage-prompt"><div className="prompt-rings"><span>✳</span></div><div className="prompt-box"><span>YOUR IDEA</span><b>“Đạo hàm thật sự có ý nghĩa gì?”</b><div><Sparkles size={14}/> Từ một câu hỏi nhỏ...</div></div><div className="stage-actor"><MascotActor name="insight" label="Nhân vật LearnFlow với ý tưởng mới"/></div></div>:active===1?<div className="stage-storyboard"><div className="storyboard-card s1"><span>01 / EXPLAIN</span><div className="story-line line-one"/><div className="story-line line-two"/><b>Vấn đề</b></div><div className="storyboard-card s2"><span>02 / VISUALIZE</span><DerivativeArt x={1.15}/><b>Trực giác</b></div><div className="storyboard-card s3"><span>03 / CONNECT</span><div className="story-formula">f′(x) = 2x</div><b>Khám phá</b></div><span className="storyboard-arrow">✦</span></div>:<div className="stage-video"><div className="video-top"><span>VISUAL LESSON</span><span>01:20</span></div><DerivativeArt x={1.85}/><div className="video-bottom"><Play size={17} fill="currentColor"/><div><i/></div><span>01:20</span></div><div className="stage-actor stage-actor-end"><MascotActor name="creator" label="Nhân vật LearnFlow tóc xanh đang tạo video"/></div></div>}<div className="process-stage-foot"><span>CONCEPTUAL PRODUCT JOURNEY</span><div><button onClick={()=>setActive(v=>(v+2)%3)} aria-label="Bước trước"><ArrowLeft size={17}/></button><button onClick={()=>setActive(v=>(v+1)%3)} aria-label="Bước tiếp theo"><ArrowRight size={17}/></button></div></div></div></div><p className="process-note">* Minh họa cách giải thích. Các video thật được tạo và lưu tại phần Thư viện.</p></div></section>}
function Purpose(){return <section id="purpose" className="purpose-section section-pad"><div className="container purpose-layout"><div className="purpose-visual"><div className="purpose-shape ps-one"/><div className="purpose-shape ps-two"/><div className="purpose-orbit"/><span className="purpose-asterisk">✳</span><div className="purpose-core"><span className="purpose-icon"><Sparkles size={25}/></span><span className="purpose-core-text">“À, mình hiểu rồi!”</span><div className="purpose-actor"><MascotActor name="research" label="Nhân vật LearnFlow tóc tím đeo kính nghiên cứu"/></div></div><div className="purpose-chip chip-top">✦ A LITTLE MOMENT OF CLARITY</div><div className="purpose-chip chip-bottom">MADE FOR CURIOUS MINDS ↗</div></div><AnimatedContent><div className="purpose-copy"><Eyebrow>ĐIỀU CHÚNG TÔI TIN</Eyebrow><h2>Một hình ảnh đẹp là tốt.<br/><em>Một hình ảnh giúp bạn hiểu còn tốt hơn.</em></h2><p>LearnFlow hướng đến những video không chỉ bắt mắt, mà còn giải thích có trình tự, chọn đúng hình ảnh và làm rõ những mối liên hệ khó thấy.</p><div className="purpose-values"><div><span>01</span><b>Clarity over complexity.</b><p>Ít nhiễu hơn, ý tưởng rõ hơn.</p></div><div><span>02</span><b>Meaningful motion.</b><p>Chuyển động phục vụ lời giải thích.</p></div><div><span>03</span><b>Made for understanding.</b><p>Đẹp là khởi đầu, hiểu mới là đích đến.</p></div></div></div></AnimatedContent></div></section>}
function Audience(){return <section className="audience-section section-pad"><div className="container"><div className="audience-heading"><Eyebrow>VÔ VÀN ĐIỀU ĐỂ KHÁM PHÁ</Eyebrow><h2>Những câu chuyện tri thức<br/><em>chờ được kể.</em></h2></div><div className="audience-grid"><div className="audience-tile tile-math"><span className="tile-label">01 / MATHEMATICS</span><div className="tile-art art-math"><span>∫</span><span>ƒ(x)</span><span>π</span></div><h3>Toán học</h3><p>Biến công thức thành trực giác.</p><ArrowUpRight size={20}/></div><div className="audience-tile tile-tech"><span className="tile-label">02 / COMPUTER SCIENCE</span><div className="tile-art art-tech"><i/><i/><i/><i/><i/><i/><i/></div><h3>Công nghệ</h3><p>Nhìn thấy logic từng bước.</p><ArrowUpRight size={20}/></div><div className="audience-tile tile-science"><span className="tile-label">03 / SCIENCE</span><div className="tile-art art-science"><span className="mini-orbit"><i/></span><span className="mini-core"/></div><h3>Khoa học</h3><p>Khám phá quy luật vận động.</p><ArrowUpRight size={20}/></div></div></div></section>}
function LastCTA(){return <section className="closing-section"><div className="closing-sunburst">✳</div><div className="container closing-content"><div className="closing-friends" aria-label="Bốn nhân vật LearnFlow">
  <div className="closing-friend"><MascotActor name="research" label="Nhân vật nghiên cứu tóc tím đeo kính"/></div>
  <div className="closing-friend"><MascotActor name="insight" label="Nhân vật tìm ý tưởng với bóng đèn"/></div>
  <div className="closing-friend"><MascotActor name="creator" label="Nhân vật tạo video với laptop"/></div>
  <div className="closing-friend"><MascotActor name="learner" label="Nhân vật đọc sách tóc cam"/></div>
 </div><Eyebrow>STAY CURIOUS, KEEP EXPLORING</Eyebrow><h2>Một ý tưởng nhỏ.<br/><em>Muôn điều có thể.</em></h2><p>Hãy bắt đầu bằng những câu hỏi hay. Chúng tôi tin rằng kiến thức luôn xứng đáng được giải thích theo cách dễ hiểu hơn.</p><a className="btn btn-dark btn-large" href="#try">Thử đặt câu hỏi <ArrowUpRight size={19}/></a><span className="closing-mark">✦ MADE WITH CURIOSITY</span></div></section>}
function Footer(){return <footer className="footer"><div className="container footer-top"><div><Brand/><p>Complex ideas, made visual.<br/>Học bằng sự tò mò. Hiểu bằng hình ảnh.</p></div><nav aria-label="Liên kết cuối trang"><a href="#explore">Khám phá</a><a href="#experience">Trải nghiệm</a><a href="#how">Cách hoạt động</a><a href="#purpose">Về LearnFlow</a></nav></div><div className="container footer-bottom"><span>© 2026 LearnFlow. All rights reserved.</span><span>Frontend kết nối API LearnFlow · Video phụ thuộc backend</span><span>Made for curious minds ✳</span></div></footer>}
const INTRO_SESSION_KEY='learnflow-opening-seen-v2';
function shouldShowOpening(){
  if(typeof window==='undefined')return false;
  if(window.matchMedia('(prefers-reduced-motion: reduce)').matches)return false;
  try{return sessionStorage.getItem(INTRO_SESSION_KEY)!=='1';}
  catch{return true;}
}
export default function App(){
  const [showOpening,setShowOpening]=useState(shouldShowOpening);
  const finishOpening=()=>{
    try{sessionStorage.setItem(INTRO_SESSION_KEY,'1');}catch{/* storage may be disabled */}
    setShowOpening(false);
  };
  useEffect(()=>{
    if(!showOpening)return;
    const originalOverflow=document.body.style.overflow;
    document.body.style.overflow='hidden';
    const media=window.matchMedia('(prefers-reduced-motion: reduce)');
    const onReducedMotion=()=>{if(media.matches)finishOpening();};
    media.addEventListener?.('change',onReducedMotion);
    return ()=>{
      document.body.style.overflow=originalOverflow;
      media.removeEventListener?.('change',onReducedMotion);
    };
  },[showOpening]);
  return <>
    <div className="app-shell" aria-hidden={showOpening||undefined}>
      <Header/><main><Hero/><LessonLibrary/><Marquee/><Showcase/><InteractiveLesson/><Process/><Purpose/><Audience/><LastCTA/></main><Footer/>
    </div>
    {showOpening&&<OpeningIntro onComplete={finishOpening}/>}
  </>;
}

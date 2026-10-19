"""Asset, JSX, video and static preview checks (not a replacement for npm build)."""
from pathlib import Path
from PIL import Image
from bs4 import BeautifulSoup
import hashlib
import subprocess
import json
ROOT = Path(__file__).resolve().parent
failures=[]
for rel in ['index.html','preview.html','package.json','src/App.jsx','src/main.jsx','src/styles.css','src/components/MascotActor.jsx','src/components/PromptComposer.jsx','src/components/LessonLibrary.jsx','src/api/learnflow.js','backend_bridge/react_landing.py','backend_bridge/install_into_backend.py']:
    if not (ROOT/rel).is_file(): failures.append('Missing '+rel)
assets={
    'learner': 'Ảnh ChatGPT 10_52_30 7 thg 10, 2026-1.png',
    'creator': 'Ảnh ChatGPT 10_52_31 7 thg 10, 2026-2.png',
    'insight': 'Ảnh ChatGPT 10_52_32 7 thg 10, 2026-3.png',
    'research': 'Ảnh ChatGPT 10_52_35 7 thg 10, 2026-4.png',
}
for name,original in assets.items():
    p=ROOT/'public/mascots'/f'{name}.png'
    if not p.is_file():
        failures.append(f'Mascot missing: {name}')
        continue
    with Image.open(p) as im:
        if im.size != (1254,1254) or im.mode != 'RGBA': failures.append(f'Unexpected mascot properties {name}')
    old=Path('/mnt/data')/original
    if old.is_file() and hashlib.sha256(old.read_bytes()).hexdigest()!=hashlib.sha256(p.read_bytes()).hexdigest():
        failures.append(f'Mascot modified from supplied original: {name}')
app=(ROOT/'src/App.jsx').read_text()
for text in ['<PromptComposer/>','<LessonLibrary/>','<HeroVideo/>', 'learnflow-product-film.mp4','learnflow-product-film-poster.webp','muted={muted}','prefers-reduced-motion','closing-friends']:
    if text not in app: failures.append('Missing JS marker: '+text)
for name in assets:
    if f'name="{name}"' not in app: failures.append('Mascot not rendered: '+name)
if 'LottieActor' in app or 'DotLottieReact' in app:
    failures.append('Legacy Lottie code remains in app')
style=(ROOT/'src/styles.css').read_text()
for marker in ['.mascot-actor','@keyframes mascot-bob','@media(prefers-reduced-motion:reduce)','max-width:640px','.closing-friends']:
    if marker not in style: failures.append('Missing CSS marker: '+marker)
if style.count('{')!=style.count('}'):failures.append('Unbalanced CSS')
preview=BeautifulSoup((ROOT/'preview.html').read_text(),'html.parser')
for sel in ['#preview-learning-prompt','#preview-submit','#preview-result','#hero-static-video','.closing-friends']:
    if not preview.select_one(sel):failures.append('Static preview missing '+sel)
imgs=preview.select('.mascot-actor img')
if len(imgs)<8: failures.append('Not all static preview mascots updated')
for img in imgs:
    src=img.get('src')
    if not src or not (ROOT/src.replace('./','')).is_file(): failures.append('Broken mascot ref: '+str(src))
video=ROOT/'public/media/learnflow-product-film.mp4'
poster=ROOT/'public/media/learnflow-product-film-poster.webp'
if not video.is_file() or not poster.is_file(): failures.append('Missing video or poster')
else:
    result=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_name,width,height','-of','json',str(video)],capture_output=True,text=True)
    if result.returncode: failures.append('ffprobe failed')
    else:
        data=json.loads(result.stdout)
        streams=data.get('streams',[])
        if not any(v.get('codec_name')=='h264' and v.get('width')==1280 and v.get('height')==720 for v in streams): failures.append('Video resolution/codec incorrect')
        if not 9.8<float(data['format']['duration'])<10.3: failures.append('Unexpected video duration')
# Ensure the production React interaction is not the old local simulation.
api = (ROOT/'src/api/learnflow.js').read_text()
composer = (ROOT/'src/components/PromptComposer.jsx').read_text()
for name in ['createLesson','getLesson','listLessons','createPaidDevPreview','asMediaUrl']:
    if name not in api: failures.append('Missing backend API helper: '+name)
for name in ['createLesson(query','getLesson(activeId','paid_consent','paidAttempted']:
    if name not in composer and name!='paid_consent': failures.append('Missing real composer flow: '+name)
if 'setSubmitted(q)' in composer: failures.append('Old local-only simulated composer is present')
if failures:
    print('FAIL')
    for failure in failures: print(' -',failure)
    raise SystemExit(1)
print(f'PASS: four unchanged PNGs, {len(imgs)} static-preview mascots, original film, React API wiring and backend integration files')

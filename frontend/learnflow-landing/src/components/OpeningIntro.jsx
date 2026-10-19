import {useEffect, useRef, useState} from 'react';
import {ArrowRight} from 'lucide-react';

/**
 * AI film: duplicated paper-motion cycle removed at the source (original
 * frames 74–81). Its new final shot reveals the LearnFlow mark, so the
 * website enters with ONE fade, not a second simulated paper burst.
 */
export default function OpeningIntro({onComplete}) {
  const videoRef = useRef(null);
  const skipRef = useRef(null);
  const phaseRef = useRef('video');
  const [phase, setPhase] = useState('video');

  const beginReveal = () => {
    if (phaseRef.current !== 'video') return;
    phaseRef.current = 'reveal';
    setPhase('reveal');
  };

  useEffect(() => {
    skipRef.current?.focus({preventScroll: true});
    const onKeyDown = event => { if (event.key === 'Escape') onComplete(); };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onComplete]);

  useEffect(() => {
    // Always keep the landing page accessible if loading/playback fails.
    const fallback = setTimeout(() => {
      if (phaseRef.current === 'video') onComplete();
    }, 5500);
    const video = videoRef.current;
    if (video) {
      const attempt = video.play();
      if (attempt?.catch) attempt.catch(error => {
        if (phaseRef.current === 'video' && error?.name !== 'AbortError') onComplete();
      });
    }
    return () => clearTimeout(fallback);
  }, [onComplete]);

  useEffect(() => {
    if (phase !== 'reveal') return;
    const finish = setTimeout(onComplete, 450);
    return () => clearTimeout(finish);
  }, [phase, onComplete]);

  return <div className={`opening-overlay opening-${phase}`} role="dialog" aria-modal="true" aria-label="LearnFlow — Oops! An Idea!">
    <span className="sr-only">Nhân vật LearnFlow ôm chồng sách, vấp ngã và giấy bay lên, mở màn trang học tập.</span>
    <video
      ref={videoRef}
      className="opening-film"
      src={`${import.meta.env.BASE_URL}media/learnflow-opening-v2-no-loop.mp4`}
      poster={`${import.meta.env.BASE_URL}media/learnflow-opening-v2-poster.jpg`}
      preload="auto"
      playsInline
      autoPlay
      muted
      aria-hidden="true"
      onEnded={beginReveal}
      onError={onComplete}
    />
    {phase === 'video' && <button ref={skipRef} type="button" className="opening-skip" onClick={onComplete} aria-label="Bỏ qua đoạn mở đầu">
      Bỏ qua <ArrowRight size={15}/>
    </button>}
  </div>;
}

/** The four official LearnFlow mascots, preserved exactly from the user-provided PNGs. */
const MASCOTS = {
  learner: 'mascots/learner.png',
  creator: 'mascots/creator.png',
  insight: 'mascots/insight.png',
  research: 'mascots/research.png',
};

export default function MascotActor({name = 'learner', className = '', label = ''}) {
  return (
    <span className={`mascot-actor ${className}`} role="img" aria-label={label || `LearnFlow mascot: ${name}`}>
      <img src={`${import.meta.env.BASE_URL}${MASCOTS[name] || MASCOTS.learner}`} alt="" loading="lazy" decoding="async" draggable="false" />
    </span>
  );
}

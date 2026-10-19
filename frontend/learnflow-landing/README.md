# LearnFlow — FE tích hợp backend tạo video thật (V3-96 compatible)

**Start here: [README-INTEGRATION.md](README-INTEGRATION.md).** The uploaded React landing is now integrated with the existing FastAPI job API, including create, real progress, final MP4 player, library, and optional explicit-consent developer GPT preview. Assets and four pixel mascots are preserved from the supplied ZIP. The standalone `preview.html` is a legacy static preview only — it **does not** call backend APIs; run the React app instead.

The frontend runs with `npm install && npm run dev` (backend on port 8000), and can be built into the existing FastAPI server with `npm run build` then `python backend_bridge/install_into_backend.py --backend <repo-checkout>`. The existing backend repo is required separately. No production launch or real provider call was performed here.

---

## Historical asset/readme notes

# LearnFlow Landing — Official Pixel Mascots + Gemini Product Film

Updated from the current React/Vite LearnFlow landing. The Napkin × Brilliant-inspired sections, colors and **topic input** remain. This update replaces the old generated placeholder Lottie mascots with the four exact PNGs supplied by the user and swaps the Hero clip to the new Gemini motion film.

## Run

```bash
npm install
npm run dev
```

To validate a release, run `npm run build`. Node.js 20+ is recommended. A standalone static HTML mock can be viewed from `preview.html` (ideally serve the project directory using `python -m http.server 8000` then open `http://localhost:8000/preview.html`). The static preview has working local topic input and video controls; other fully interactive React sections require Vite.

## Updated assets

| File | Exact character supplied by user |
| --- | --- |
| `public/mascots/research.png` | Purple hair, glasses, teal shirt, laptop |
| `public/mascots/insight.png` | Dark-blue hair, lightbulb, pink shirt, teal laptop |
| `public/mascots/creator.png` | Dark-blue hair, lavender outfit, laptop |
| `public/mascots/learner.png` | Orange hair, reading yellow-and-white book |

The PNG bytes are preserved from the uploads. `src/components/MascotActor.jsx` renders them; CSS adds only a slight motion effect that respects `prefers-reduced-motion`. The last CTA shows all four. Old placeholder Lottie animations and the unused dotLottie dependency have been removed.

- `public/media/learnflow-product-film.mp4` — **new uploaded** Gemini product motion film, H.264/AAC, 1280×720, 10 seconds. Web-optimized encode of the uploaded clip (original story and timing preserved).
- `public/media/learnflow-product-film-poster.webp` — video fallback frame.
- The Hero player plays silently on load, loops, has play/pause, accurate progress, and a user-controlled audio toggle. `prefers-reduced-motion` disables autoplay.

## Functionality retained

- Hero input (`#learning-prompt`) with Enter to submit, Shift+Enter for newline, suggestions, reset, and **local template-based** four-step storyboard preview. The site does **not** submit the prompt to a server.
- Showcase tabs, Binary Search stepper, derivative slider, staged storyboard, dark/light theme, responsive/mobile navigation, scrolling CTA.
- Disclosure that the Gemini product film is an **illustrative concept**, not a real video output from LearnFlow's AI backend.

## Verification

`python validate_project.py` (requires Python `Pillow` and `beautifulsoup4`) checks all four original PNGs, file references, video encoding, React/CSS structure and static preview. JSX syntax was additionally checked using the TypeScript parser and video was decoded with FFmpeg.

The production Vite build **could not be completed in this environment**, because `npm install` failed to resolve `registry.npmjs.org` (EAI_AGAIN). The browser screenshot test was also blocked by the environment's Chromium navigation policy. Please run `npm install && npm run build` in a networked environment before deployment.

React Bits licensed code is in `src/components/reactbits/`; retain `LICENSE.reactbits.md`.


## Opening “Oops! An Idea!” — loop repaired (Oct 2026)

- Authoritative uploaded Gemini source: `Voxel_mascot_falling_with_books_20261008150800-ezremove.mp4` (4.0s, 96 frames @ 24 FPS).
- Corrected asset: `public/media/learnflow-opening-v2-no-loop.mp4` (3.6667s, 88 frames @ 24 FPS).
- Removed **the eight-frame repeated paper motion at original frames 74–81**: these reenacted almost the same movement seen in 66–73. Original frame 73 now transitions straight to original frame 82; the fade-in LearnFlow-logo ending is preserved.
- The updated end frame already contains a paper-to-logo reveal, so `OpeningIntro.jsx` no longer spawns another artificial set of flying papers in the React handoff. It lets the clip end naturally and fades to the actual Hero in 450ms.
- Video URL and poster names are versioned so browsers cannot reuse the stale, previously patched file from cache.
- Plays once per browser tab/session using `sessionStorage['learnflow-opening-seen-v2']`; supports Skip, Escape, reduced-motion bypass and automatic fallback on playback failure. Use a fresh tab/session to replay after first viewing.
- `preview.html` is updated to match the React opening logic and uses the same corrected MP4.
- Real topic input, four original mascots, large product-film showcase, and other landing sections remain unchanged.

Run `npm install && npm run dev` to launch React. Run `npm run build` once dependencies are installed.

## Hero layout refresh
- Hero follows question → wide Manus-inspired input → original large video showcase. The old slogan and product-film labels remain removed.
- MP4 remains the supplied Gemini motion concept; it is not a verified output from the LearnFlow video pipeline.
- The composer is still an on-device outline illustration (no backend request).

## Hero position correction
- Product video is restored to the original large showcase directly BELOW the topic prompt, with its original responsive sizing.
- Only the prompt area uses Manus-inspired width, spacing, textarea and circular submit button.

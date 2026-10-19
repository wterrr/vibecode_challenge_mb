# V3-96 — Real new user prompt through actual Chromium /create UI → GPT-6 Luna → native MP4: TECHNICAL PASS

**Verified:** 2026-10-19. **One original genuine paid user intent** carried from user command “chạy chứng minh một prompt mới chạy GPT thật qua chính giao diện V3-95 đi”; continued only when user said “tiếp tục”. **Production remains BLOCKED; no merge of `main`.**

## Immutable experiment lineage and safe second trigger clarification

Parent: Draft PR #132 V3-95 HEAD `cd2f131e2310006078c06052be296256b5488a32`, [original V3-95 offline success #39201973801](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/39201973801). First-child V3-96 prereg **`c762194c9c3a30e63997abc67fbd572c4da42d02`** before implementation or paid request. Draft PR #133.

After one original `V396_AUTHORIZED_ONE_PAID_BROWSER_TRIGGER` commit at `084c6490d898fc1b89d99114db17af753f1c920a`, [Actions #39211384525](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/39211384525) **failed in its offline source test**; its actual `one_real_gpt_browser_click_paid_once` job concluded `skipped` **without even launching a paid provider step**. Source test had not been updated when the standalone live workflow was disabled in favor of the new registered single-workflow arrangement.

The source test was corrected on the development branch without weakening model admission. [New independent Playwright offline run #39212767128](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/39212767128) **SUCCESS**; the GitHub Actions unique-trigger guard then specifically checks **each historical authorizing run's jobs API** and permits continued authorization only when exactly the known previous run's paid job is independently confirmed **completed / skipped**. That guard amendment and offline [#39212950909](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/39212950909) **SUCCESS** occurred before the next trigger. This is a new GitHub trigger but **not a second paid model API call**, because the first paid job was never entered. Zero tolerance for retry and fallback remains.

Final single effective trigger SHA **`12f3e0d1983a472e00b4f1ba5824a3e2267ae210`**, message `V396_AUTHORIZED_ONE_PAID_BROWSER_TRIGGER`; actual [run #39213083034](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/39213083034), `run_attempt=1`, **SUCCESS**.

## Actual user-visible UI evidence (not mock or script-only)

Chromium Playwright headless on Ubuntu runner opens real local FastAPI `http://127.0.0.1:8765/create` (same existing actual `create_app` routes, JS and CSS).

- The browser finds real `#v395-ai-preview-form`, *types* exact previously preregistered **new user question**:
  `How can a 3 by 4 grid of squares turn into a 4 by 3 array and keep the same total?`
- It *checks* the explicit `#v395-paid-consent` checkbox and *clicks* `#v395-submit` without replaying V3-93's accepted JSON or using injected sender mocks.
- An intercepted **real network HTTP POST** to `/api/v3/ai/array-preview` is checked for exact user text, `language=en`, `paid_consent=true`; actual HTTP response **200**.
- Backend requires exact `openai/gpt-6-luna`, `finish_reason=stop`, strict fresh JSON, host-grounded semantic identity of exactly 12 squares, V3-94 every-frame collision/geometry gate and rendered native H264/AAC. **One real provider POST; zero retries and fallback.**
- Real JS shows a video element in the page and sets the URL to `/api/v3/ai/array-preview/<random-id>/video`. Chromium verifies that HTML video loaded metadata; the browser then makes a real HTTP GET for that exact source, and the **bytes SHA256 must equal the actual host-generated native MP4 file**, ruling out a static sample being substituted.
- Separately, [offline Chromium real browser #39210831469](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/39210831469), [#39212950909](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/39212950909), and the preflight part of #39213083034 verify off-topic questions **ABSTAIN without any model API key, POST or preview video**.

## First-party genuine live receipt and independently downloaded artifact

[GitHub Actions original artifact #12168835610](https://github.com/wterrr/vibecode_challenge_mb/actions/runs/39213083034/artifacts/12168835610), downloaded and byte-inspected in addition to original live job logs. ZIP SHA256 **`9db73c5c66c2b9bc705e61b53f1409c48b6bed4a93cc4b1e3bf68e61fa931394`**, 1,030,276 bytes. Original contains a 582,347B MP4, screenshot of actual human form before click, screenshot of result including HTML video, independent stills at 11.7s/22s, sanitized JSON receipt.

| Evidence property | Observed |
| --- | --- |
| `result` | **`GENUINE_GPT_NEW_PROMPT_BROWSER_UI_TO_NATIVE_MP4_TECHNICAL_PASS`** |
| `mode` | `REAL_PAID_BROWSER` |
| `mock_model_used` | **false** |
| `provider_posts` | **1** |
| `actual_model` | **`openai/gpt-6-luna`** |
| `finish_reason` | **`stop`** |
| `storyboard_origin` | `GENUINE_NEW_GPT_POST` |
| `storyboard_sha256` | `28f420d146480f39070697833c537bd35414d2776ea1f758eaab782f6931b1a3` |
| `accepted_source_sha256` | `a5f9761e295a4ad5d1498c24f03dad3319da6d6c50d1d9f76e9442773fae5a8a` |
| `host_ledger_sha256` | `8ea108abef60738268892c74b9013da33e9d09064fb2e9de19f234ca4f6fee76` |
| `provider_reported_cost_usd` | **`0.00025443` USD** |
| `ui_http_status` | **200** |
| `browser_ui_paid_consent` | **true** |
| `browser_http_post_verified` | **true** |
| `browser_html5_video_metadata` | **LOADED** |
| `private_video_http_get_sha_verified` | **true** |
| `decoded_native_mp4` | **true** |
| `frame_count` | **411** |
| `video_sha256` | `25f3aa95f34be85b7ed04667a97b738c1663620ccf82e2f31b8cea5e512fde71` |
| `human_quality` | **UNRATED** |
| `independent_human_review` | **NOT_RUN** |
| `production` | **BLOCKED** |

**Independent media decode in the model's local container:** `ffprobe` says H.264 video 1280×720 at 15fps, **411 frames**, AAC audio, **27.400s**; file 582,347 bytes; SHA256 equals receipt exactly. `ffmpeg -v error -i ... -f null -` completed cleanly (full decoded streams).

**Direct original-frame spot review:** 11.7s mid-transition shows continuous recognizable persistent square IDs with no overlap with title, note or narration; 22.0s shows correct 4-row×3-column arrangement and a legible spoken-claim caption, without the two historical V3-93 collision defects. This is a **two-frame visual spot check**, while per-frame geometry validation is host-automated. It is **not** independent human pedagogical scoring.

## Important product/science limitations

**This is a genuine new prompt submitted through an actual UI and a fresh genuine model-generated storyboard, not an old static one.** The new question still belongs to the same narrow square-array mathematical family already supported; it is **NOT** evidence of flexible arbitrary topic-to-video generalization. Legacy `/api/jobs` is unchanged, and GPT preview is **OFF by default**, local developer only, synchronous and protected by per-process one-attempt gate. This is **not a durable, multi-user production backend nor an account-wide cost/credit cap**.

Even though the source geometry and media are technically verified, human educational clarity, learning gain and 3Blue1Brown visual/pedagogical parity are **NOT independently established**. **No production publication, no merge main, no second paid model request.**

### Final verdict

**REAL CHROMIUM UI INPUT/CONSENT PASS · AUTHENTIC GPT-6 Luna NEW STORYBOARD PASS · HOST SOURCE FACTS PASS · ACTUAL HTML VIDEO GET / FILE SHA PASS · H.264/AAC COMPLETE DECODE PASS · PRE-REGISTERED COLLISION FRAMES VISUALLY CLEAN · EXACTLY 1 REAL GPT MODEL POST · $0.00025443 PROVIDER-REPORTED · PEDAGOGICAL QUALITY UNRATED · PRODUCTION BLOCKED.**

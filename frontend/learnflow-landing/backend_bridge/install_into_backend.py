#!/usr/bin/env python3
"""Install this Vite landing into the EXISTING LearnFlow FastAPI checkout.

Usage: python backend_bridge/install_into_backend.py --backend /path/to/vibecode_challenge_mb
Requires `npm install && npm run build` in this project's root beforehand.
No changes to production prompts, V2 Core, pipelines, paid API guards, or main branch.
"""
import argparse
import shutil
from pathlib import Path

ANCHOR = "    app.include_router(web_router)"
NEW_ROUTES = """    # Opt-in React landing; API + legacy pages are unaffected.
    import os
    if os.getenv("LEARNFLOW_REACT_LANDING", "0") == "1":
        from app.web.react_landing import router as react_landing_router
        app.include_router(react_landing_router)
    app.include_router(web_router)"""


def install(backend: Path, frontend: Path, dry_run: bool = False) -> None:
    backend = backend.resolve()
    main_file = backend / 'app' / 'main.py'
    web_dir = backend / 'app' / 'web'
    static_dir = backend / 'app' / 'static'
    dist = frontend / 'dist'
    if not (main_file.is_file() and web_dir.is_dir() and static_dir.is_dir()):
        raise SystemExit('Expected LearnFlow backend checkout with app/main.py, app/web and app/static')
    if not (dist / 'index.html').is_file() or not (dist / 'assets').is_dir():
        raise SystemExit('Missing compiled Vite assets. Run npm install && npm run build in frontend first.')
    output_dir = static_dir / 'landing'
    if output_dir.exists() and output_dir.is_symlink():
        raise SystemExit('Unsafe symlink at app/static/landing; aborting')
    main_text = main_file.read_text(encoding='utf-8')
    if 'LEARNFLOW_REACT_LANDING' not in main_text:
        if main_text.count(ANCHOR) != 1:
            raise SystemExit('Backend app/main.py differs from verified V3-96 integration anchor; aborting safely.')
        updated = main_text.replace(ANCHOR, NEW_ROUTES)
    else:
        if 'react_landing_router' not in main_text:
            raise SystemExit('Found unexpected landing integration; aborting safely.')
        updated = main_text
    if dry_run:
        print('Preflight OK; no files changed.')
        return
    # Keep a backup of the original app. Do not touch the existing static dirs.
    if updated != main_text:
        backup = main_file.with_suffix('.py.before-react-landing')
        if not backup.exists():
            backup.write_text(main_text,encoding='utf-8')
        main_file.write_text(updated,encoding='utf-8')
    shutil.copy2(frontend / 'backend_bridge' / 'react_landing.py', web_dir / 'react_landing.py')
    # Dist uses hashed Vite assets; replace previous bundled frontend only.
    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.copytree(dist, output_dir)
    print('LearnFlow React landing installed at app/static/landing.')
    print('Run: LEARNFLOW_REACT_LANDING=1 uvicorn app.main:app --host 127.0.0.1 --port 8000')
    print('Open: http://127.0.0.1:8000/')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend',type=Path,required=True)
    parser.add_argument('--dry-run',action='store_true')
    args = parser.parse_args()
    install(args.backend,Path(__file__).resolve().parent.parent,args.dry_run)

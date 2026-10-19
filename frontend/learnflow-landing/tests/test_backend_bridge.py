"""Test the opt-in FastAPI landing bridge without needing the full private backend checkout."""
from pathlib import Path
import importlib.util
import tempfile
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
import sys

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(HERE / 'backend_bridge'))
from install_into_backend import install


def test_install_and_fastapi_static_roundtrip():
    with tempfile.TemporaryDirectory() as root:
        root=Path(root)
        be=root/'backend'
        (be/'app'/'web').mkdir(parents=True)
        (be/'app'/'static').mkdir()
        (be/'app'/'main.py').write_text('def create_app():\n    app = something()\n    app.include_router(web_router)\n    return app\n')
        src=root/'fe'
        (src/'dist'/'assets').mkdir(parents=True)
        (src/'dist'/'index.html').write_text('<html><body>LearnFlow React UI</body></html>')
        (src/'dist'/'assets'/'app.js').write_text('console.log("ready")')
        (src/'backend_bridge').mkdir()
        (src/'backend_bridge'/'react_landing.py').write_bytes((HERE/'backend_bridge'/'react_landing.py').read_bytes())
        install(be,src,dry_run=True)
        assert 'LEARNFLOW_REACT_LANDING' not in (be/'app'/'main.py').read_text()
        install(be,src)
        assert (be/'app'/'main.py.before-react-landing').exists()
        main=(be/'app'/'main.py').read_text()
        assert main.index('app.include_router(react_landing_router)') < main.index('app.include_router(web_router)')
        install(be,src)
        assert main==(be/'app'/'main.py').read_text()  # idempotent
        mod_path=be/'app'/'web'/'react_landing.py'
        spec=importlib.util.spec_from_file_location('lf_react_landing_bridge_test',mod_path)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        app=FastAPI()
        app.mount('/static',StaticFiles(directory=be/'app'/'static'),name='static')
        app.include_router(module.router)
        @app.get('/healthz')
        def health():return {'status':'ok'}
        client=TestClient(app)
        assert 'LearnFlow React UI' in client.get('/').text
        assert 'ready' in client.get('/static/landing/assets/app.js').text
        assert client.get('/healthz').json()=={'status':'ok'}

if __name__=='__main__':
    test_install_and_fastapi_static_roundtrip()
    print('FastAPI bridge + static assets: PASS')

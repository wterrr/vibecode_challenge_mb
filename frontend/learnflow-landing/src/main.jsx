import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.jsx';
import './styles.css';
import {getAuthSession, logoutAdmin} from './api/learnflow';


const root = createRoot(document.getElementById('root'));
async function bootstrap() {
  try {
    const session=await getAuthSession();
    root.render(<React.StrictMode><>
      {session?.auth_required && <div style={{position:'fixed',right:12,top:12,zIndex:1000,
        background:'#fff',border:'1px solid #e8e4f8',padding:'7px 11px',borderRadius:12,
        boxShadow:'0 3px 14px #0001',fontSize:12}}>
        <span style={{marginRight:12}}>{session.username}</span>
        <button style={{border:0,background:'transparent',cursor:'pointer',color:'#6650d5'}}
          onClick={logoutAdmin}>Đăng xuất</button>
      </div>}
      <App />
    </></React.StrictMode>);
  } catch (error) {
    root.render(<main role="alert" style={{fontFamily:'system-ui',padding:'6rem 2rem',textAlign:'center'}}>
      Không thể xác minh phiên đăng nhập. <a href="/login">Đăng nhập</a>
    </main>);
  }
}
bootstrap();

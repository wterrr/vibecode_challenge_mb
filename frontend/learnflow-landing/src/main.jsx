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
    // This is the normal unauthenticated path. Never render an alarming
    // generic "session verification failed" page over a pending redirect.
    if (error?.status === 401) {
      window.location.replace('/login');
      return;
    }
    const safeStatus = Number.isInteger(error?.status) && error.status >= 400
      ? `HTTP ${error.status}` : 'Lỗi kết nối/API';
    const detail = error?.message || 'Không thể kết nối tới backend LearnFlow.';
    root.render(<main role="alert" style={{fontFamily:'system-ui',padding:'6rem 2rem',textAlign:'center',maxWidth:650,margin:'0 auto'}}>
      <h1>Không thể kiểm tra trạng thái đăng nhập</h1>
      <p>{detail}</p>
      <p style={{fontSize:13,color:'#686478'}}>Chi tiết: {safeStatus}. Backend: /api/auth/session</p>
      <button type="button" style={{padding:'10px 16px',borderRadius:8,cursor:'pointer'}}
        onClick={() => window.location.reload()}>Thử lại</button>
      <p><a href="/login">Đi đến trang đăng nhập</a></p>
    </main>);
  }
}
bootstrap();

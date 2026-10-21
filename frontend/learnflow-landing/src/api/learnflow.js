/** Canonical LearnFlow FastAPI contract (V3-96 compatible).
 * All requests are same-origin; Vite proxies /api and /healthz in development.
 * Never put provider keys in browser code. Never retry paid requests automatically.
 */
// Authentication and private media are same-origin by design. A mistakenly
// injected cross-origin VITE_API_BASE_URL must not drop the session cookie.
// Empty API base is the canonical production deployment arrangement.
function resolveApiRoot(configured) {
  const base = String(configured || '').trim();
  if (!base) return '';
  try {
    const origin = window.location.origin;
    const parsed = new URL(base, origin);
    if (parsed.origin !== origin || parsed.search || parsed.hash) return '';
    return parsed.pathname === '/' ? '' : (parsed.pathname.endsWith('/') ? parsed.pathname.slice(0, -1) : parsed.pathname);
  } catch {
    return '';
  }
}
const ROOT = resolveApiRoot(import.meta.env.VITE_API_BASE_URL);

let authCsrf = '';
export async function getAuthSession() {
  let response;
  try {
    response = await fetch(`${ROOT}/api/auth/session`, {
      method:'GET', credentials:'same-origin', cache:'no-store',
      headers:{'Accept':'application/json'},
    });
  } catch {
    throw new ApiError(
      'Không kết nối được API đăng nhập. Kiểm tra /healthz, reverse proxy và cấu hình website.',
      0
    );
  }
  if (response.status === 401) {
    // A 401 is expected for a new/expired session. The React bootstrap owns
    // the navigation, avoiding a render race with window.location.replace().
    throw new ApiError('Bạn chưa đăng nhập hoặc phiên đã hết hạn.', 401);
  }
  if (!response.ok) {
    const status = response.status;
    const explanation =
      status === 404 ? 'Không tìm thấy /api/auth/session. Kiểm tra backend FastAPI và định tuyến /api.' :
      status === 403 ? 'Backend từ chối yêu cầu kiểm tra phiên (HTTP 403).' :
      status >= 500 ? 'Backend hoặc reverse proxy gặp lỗi khi kiểm tra phiên.' :
      'Không thể xác minh phiên đăng nhập.';
    throw new ApiError(`${explanation} (HTTP ${status})`, status);
  }
  const contentType = response.headers?.get?.('content-type') || '';
  if (!contentType.toLowerCase().includes('application/json')) {
    throw new ApiError(
      'API kiểm tra phiên trả về HTML/thành phần không phải JSON. Kiểm tra reverse proxy /api.',
      0
    );
  }
  const data = await response.json().catch(() => {
    throw new ApiError('Dữ liệu phiên đăng nhập từ backend không phải JSON hợp lệ.', 0);
  });
  if (!data || typeof data !== 'object' ||
      typeof data.auth_required !== 'boolean' ||
      (data.auth_required && (!data.authenticated || !data.csrf_token))) {
    throw new ApiError('Backend trả về thông tin phiên không đúng định dạng.', 0);
  }
  authCsrf = data?.csrf_token || '';
  return data;
}
export async function logoutAdmin() {
  const result=await json('/api/auth/logout',{method:'POST'});
  authCsrf='';
  window.location.replace('/login');
  return result;
}

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function asMediaUrl(path) {
  if (!path || typeof path !== 'string') return null;
  // Server-owned relative media URLs only; reject external or protocol-relative URLs.
  if (!/^\/api\/(jobs\/|v3\/ai\/array-preview\/)/.test(path) || path.startsWith('//')) return null;
  return `${ROOT}${path}`;
}

function detailMessage(body, status) {
  const detail = body?.detail;
  if (typeof detail === 'string' && detail.length <= 500) return detail;
  if (Array.isArray(detail)) return detail.map(d => d?.msg).filter(Boolean).join('; ').slice(0, 500);
  if (status === 404) return 'Không tìm thấy tài nguyên hoặc tính năng backend chưa được bật.';
  if (status === 409) return 'Yêu cầu đang xung đột với trạng thái hiện tại.';
  if (status === 422) return 'Câu hỏi hoặc thông số chưa được backend hỗ trợ.';
  if (status >= 500) return 'Máy chủ chưa xử lý được yêu cầu. Vui lòng kiểm tra log backend.';
  return `Máy chủ trả về HTTP ${status}.`;
}

async function json(path, {method = 'GET', body, signal, timeout = 15000} = {}) {
  const controller = new AbortController();
  const cancel = () => controller.abort();
  if (signal?.aborted) controller.abort();
  signal?.addEventListener('abort', cancel, {once:true});
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(`${ROOT}${path}`, {
      method,
      credentials: 'same-origin',
      cache: 'no-store',
      headers: {
        'Accept':'application/json',
        ...(body === undefined ? {} : {'Content-Type':'application/json'}),
        ...(method !== 'GET' && authCsrf ? {'X-CSRF-Token':authCsrf} : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    const data = response.status === 204 ? null : await response.json().catch(() => null);
    if (response.status===401) {
      window.location.replace('/login');
      throw new ApiError('Phiên đăng nhập đã hết hạn.',401);
    }
    if (!response.ok) throw new ApiError(detailMessage(data, response.status), response.status);
    return data;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error.name === 'AbortError') throw new ApiError('Kết nối bị hủy hoặc đã hết thời gian chờ. Hãy kiểm tra trạng thái trước khi thử lại.');
    throw new ApiError('Không kết nối được backend LearnFlow. Kiểm tra FastAPI và cấu hình proxy.');
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', cancel);
  }
}

export const checkBackend = (signal) => json('/healthz', {signal,timeout:5000});
export const createLesson = (topic, options, signal) => json('/api/jobs', {
  method:'POST',
  body:{topic, audience:options.audience, language:options.language, target_duration_seconds:options.duration, visual_style:'clean'},
  signal, timeout:25000,
});
export const getLesson = (id, signal) => json(`/api/jobs/${encodeURIComponent(id)}`, {signal});
export const listLessons = (signal) => json('/api/jobs?limit=30', {signal});
export const deleteLesson = (id) => json(`/api/jobs/${encodeURIComponent(id)}`, {method:'DELETE'});
export const updateLesson = (id, display_title) => json(`/api/jobs/${encodeURIComponent(id)}`, {method:'PATCH',body:{display_title}});
export const createPaidDevPreview = (query) => json('/api/v3/ai/array-preview', {
  method:'POST', body:{query,language:'en',paid_consent:true}, timeout:240000,
});

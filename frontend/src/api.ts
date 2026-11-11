export async function api(path:string, init:RequestInit={}) {
 const response=await fetch('/api/v1'+path,{...init,credentials:'include',headers:init.body instanceof FormData?{}:{'Content-Type':'application/json',...init.headers}});
 if(!response.ok){let message='Request failed';try{const body=await response.json();message=typeof body.detail==='string'?body.detail:JSON.stringify(body.detail)}catch{message=`Request failed (${response.status})`}throw new Error(message)}
 return response.json();
}
export const post=(path:string,body:unknown={})=>api(path,{method:'POST',body:JSON.stringify(body)});

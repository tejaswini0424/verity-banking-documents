// Uses the user's existing Vercel login in memory; never writes or logs tokens.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';

const root=path.resolve(import.meta.dirname,'..');
const statePath=path.join(root,'.vercel','deployment-state.json');
const auth=JSON.parse(await fs.readFile(path.join(os.homedir(),'AppData','Roaming','com.vercel.cli','Data','auth.json'),'utf8'));
const team='team_Jkx8L3LGGrb8fAzL5NtQJmcT';
const integration='icfg_1jA6Sik7tHJ2oh9NMZ3nOP2q';
let state={teamId:team,name:'verity-banking-documents'};
try{state={...state,...JSON.parse(await fs.readFile(statePath,'utf8'))}}catch{}
async function save(){await fs.mkdir(path.dirname(statePath),{recursive:true});await fs.writeFile(statePath,JSON.stringify(state,null,2));}
async function api(url,method='GET',body){
 const response=await fetch('https://api.vercel.com'+url+(url.includes('?')?'&':'?')+'teamId='+team,{method,headers:{Authorization:'Bearer '+auth.token,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(90000)});
 const data=await response.json();
 if(!response.ok)throw new Error(`${method} ${url}: ${response.status} ${data.error?.message||'Request failed'}`);
 return data;
}
const mode=process.argv[2];
if(mode==='setup'){
 if(!state.projectId){
  const p=await api('/v11/projects','POST',{name:state.name,framework:null,buildCommand:'npm run build --prefix frontend',installCommand:'npm ci --prefix frontend',outputDirectory:'frontend/dist',environmentVariables:[{key:'COOKIE_SECURE',value:'true',target:['production','preview'],type:'plain'},{key:'ARTIFACT_STORAGE',value:'database',target:['production','preview'],type:'plain'}]});
  state.projectId=p.id;await save();console.log(JSON.stringify({projectId:p.id,name:p.name}));
 }
 if(!state.storeId){
  // Omit billingPlanId: this endpoint only auto-selects a FREE plan.
  const resource=await api('/v1/storage/stores/integration/direct','POST',{name:'verity-banking-documents-db',integrationConfigurationId:integration,integrationProductIdOrSlug:'neon',metadata:{region:'sin1',auth:false},source:'marketplace'});
  state.storeId=resource.store.id;state.resourceId=resource.store.externalResourceId||resource.store.externalId;await save();
  console.log(JSON.stringify({storeId:state.storeId,resourceId:state.resourceId,plan:resource.store.billingPlan?.name||resource.store.billingPlan?.id,status:resource.store.status}));
 }
 if(!state.connected){
  if(!state.resourceId)throw new Error('Store created but resource ID requires inspection before connection.');
  await api(`/v1/integrations/installations/${integration}/resources/${state.resourceId}/connections`,'POST',{projectId:state.projectId,envVarEnvironments:['production','preview'],makeEnvVarsSensitive:true});
  state.connected=true;await save();console.log('Connected private database to this project.');
 }
}else if(mode==='deploy'){
 if(!state.projectId||!state.connected)throw new Error('Run setup and verify database connection first.');
 const files=[];
 async function collect(dir){for(const entry of await fs.readdir(path.join(root,dir),{withFileTypes:true})){
  if(['node_modules','dist','__pycache__'].includes(entry.name)||entry.name.endsWith('.tsbuildinfo')||entry.name.endsWith('.test.ts')||entry.name.startsWith('.env'))continue;
  const relative=path.posix.join(dir,entry.name);
  if(entry.isDirectory())await collect(relative);else files.push({file:relative,data:(await fs.readFile(path.join(root,relative))).toString('base64'),encoding:'base64'});
 }}
 for(const dir of ['api','backend','frontend'])await collect(dir);
 for(const name of ['requirements.txt','.python-version','vercel.json'])files.push({file:name,data:await fs.readFile(path.join(root,name),'utf8'),encoding:'utf-8'});
 const deployment=await api('/v13/deployments','POST',{name:state.name,project:state.projectId,target:'production',files,projectSettings:{framework:null,buildCommand:'npm run build --prefix frontend',installCommand:'npm ci --prefix frontend',outputDirectory:'frontend/dist'}});
 state.deploymentId=deployment.id;state.url='https://'+deployment.url;await save();
 console.log(JSON.stringify({id:deployment.id,url:state.url,status:deployment.readyState}));
}else if(mode==='status'){
 const d=await api('/v13/deployments/'+state.deploymentId);
 console.log(JSON.stringify({id:d.id,status:d.readyState,url:'https://'+d.url,aliases:d.alias,error:d.errorMessage||d.error?.message}));
 if(d.readyState==='READY'){state.aliases=d.alias;state.ready=true;await save();}
}else if(mode==='env-keys'){
 const e=await api('/v10/projects/'+state.projectId+'/env');
 console.log(JSON.stringify(e.envs.map(v=>({key:v.key,target:v.target,type:v.type}))));
}else if(mode==='logs'){
 const events=await api('/v3/deployments/'+state.deploymentId+'/events?direction=backward&limit=40');
 console.log(events.map(e=>e.text||e.payload?.text||'').join('\n'));
}else throw new Error('Use setup, deploy, status, env-keys, or logs.');

import { apiFetch } from './endpoint.ts'
import { getSkyToken } from './sky'
import type { VisionChatResult } from '../types/visionChat'
export async function visionRequest<T>(path:string,method='GET',body?:FormData,signal?:AbortSignal):Promise<T>{
  const token=getSkyToken();if(!token)throw new Error('请先登录平台')
  const response=await apiFetch('/agent-api/vision-chat'+path,{method,body,signal,headers:{Authorization:`Bearer ${token}`}})
  const value=await response.json().catch(()=>null)
  if(!response.ok||!value)throw new Error(typeof value?.detail==='string'?value.detail:'看图请求未完成，请检查Agent服务')
  return value as T
}
export async function askVision(question:string,requestId:string,conversationId:string,file:File|undefined,signal:AbortSignal):Promise<VisionChatResult>{
  const form=new FormData();form.append('question',question);form.append('request_id',requestId);form.append('conversation_id',conversationId);form.append('external_allowed','true');if(file)form.append('image',file)
  const value=await visionRequest<VisionChatResult>('', 'POST',form,signal)
  if(value.source!=='deepseek_vision'||typeof value.summary!=='string'||!Array.isArray(value.observations)||!Array.isArray(value.limitations)||!/^[a-f0-9]{64}$/.test(value.image_sha256))throw new Error('视觉结果格式异常，本次不作为成功展示')
  return value
}

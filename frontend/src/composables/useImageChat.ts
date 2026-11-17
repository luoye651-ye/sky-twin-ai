import { computed, onScopeDispose, shallowRef, watch } from 'vue'
import { askVision, visionRequest } from '../api/visionChat'
export function useImageChat(identity:()=>string){
  const enabled=shallowRef(false),file=shallowRef<File>(),preview=shallowRef(''),consent=shallowRef(false),hasContext=shallowRef(false),error=shallowRef('')
  const health=shallowRef({ready:false,message:'开启看图后检查现有DeepSeek配置'})
  const ready=computed(()=>health.value.ready&&consent.value&&!!(file.value||hasContext.value))
  let conversationId=crypto.randomUUID(),alive=true,generation=0,healthController:AbortController|undefined
  function choose(value:File|undefined){
    error.value='';if(value&&(value.size>2*1024*1024||!['image/png','image/jpeg'].includes(value.type))){error.value='请选择2MiB以内PNG/JPEG';return}
    if(preview.value)URL.revokeObjectURL(preview.value)
    file.value=value;preview.value=value?URL.createObjectURL(value):'';hasContext.value=false;consent.value=false
  }
  async function check(){
    const ticket=++generation;healthController?.abort();const control=new AbortController();healthController=control;const timer=setTimeout(()=>control.abort(),10000)
    try{const result=await visionRequest<{ready:boolean;message:string}>('/health','GET',undefined,control.signal);if(alive&&ticket===generation)health.value=result}
    catch(e){if(alive&&ticket===generation)health.value={ready:false,message:e instanceof Error?e.message:'看图服务不可用'}}finally{clearTimeout(timer)}
  }
  async function ask(question:string,requestId:string,signal:AbortSignal){
    if(!ready.value)throw new Error('请先上传图片并确认可发送至DeepSeek')
    const result=await askVision(question,requestId,conversationId,file.value,signal)
    if(!signal.aborted&&alive){file.value=undefined;hasContext.value=true}
    return result
  }
  function clear(){const old=conversationId;conversationId=crypto.randomUUID();choose(undefined);if(identity())void visionRequest(`/${old}`,'DELETE').catch(()=>{})}
  watch(enabled,value=>{if(value&&identity())void check()})
  watch(identity,()=>{generation++;healthController?.abort();clear();enabled.value=false;health.value={ready:false,message:'开启看图后检查现有DeepSeek配置'}})
  onScopeDispose(()=>{alive=false;generation++;healthController?.abort();if(preview.value)URL.revokeObjectURL(preview.value)})
  return{enabled,file,preview,consent,hasContext,error,health,ready,choose,ask,check,clear}
}

export interface VisionObservation { label:string; description:string; location:string; certainty:'清晰'|'疑似'|'无法确定' }
export interface VisionChatResult { summary:string; observations:VisionObservation[]; limitations:string[]; source:'deepseek_vision'; model:string; image_sha256:string; image_width:number; image_height:number; run_id:string }

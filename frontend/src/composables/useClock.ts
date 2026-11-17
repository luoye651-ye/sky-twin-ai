import { computed,onMounted,onUnmounted, ref} from 'vue'

export function useClock(){
    //ref 表示这个数据发生变化后，页面也会自动更新
    const now = ref(new Date())
    //保存定时器编号，方便组件销毁时清除
    let timerId:number | undefined
    //把7转成为07
    function pad(value:number){
        return String(value).padStart(2,'0')
    }
    //computed 表示根据now自动计算显示内容
    const formattedTime = computed(() => {
        const date = now.value
        const year = date.getFullYear()
        const month = pad(date.getMonth()+1)
        const day = pad(date.getDate())
        const hour = pad(date.getHours())
        const minute = pad(date.getMinutes())
        const second = pad(date.getSeconds())
        
        return `${year}-${month}-${day} ${hour}:${minute}:${second}`
    })

    //time 标签的datetime属性需要标准时间格式
    const isoTime = computed(() => now.value.toISOString())

    //组件显示时启动定时器
    onMounted(() =>{
        timerId = window.setInterval(() => {
            now.value = new Date()
        },1000)
    })

    //离开页面时清楚定时器，防止内存泄漏？
    onUnmounted(() => {
        if (timerId !== undefined){
            window.clearInterval(timerId)
        }
    })

    return{
        formattedTime,
        isoTime
    }
}

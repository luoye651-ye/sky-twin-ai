import request from '@/utils/request'
export const skyRequest = (path, method = 'get', data) => request({ url: `/sky${path}`, method, data })

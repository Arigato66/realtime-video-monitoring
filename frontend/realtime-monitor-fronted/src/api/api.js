import axios from 'axios'

// 使用环境变量
let baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1.0'

export const requestLogin = params => {
    return axios({
        method: 'POST',
        url: `${baseURL}/login`,
        data: params
    })
        .then(res => res.data)
}

export const requestSignin = params => {
    return axios({
        method: 'POST',
        url: `${baseURL}/signin`,
        data: params
    })
        .then(res => res.data)
}

export const requestMailcode = params => {
    return axios({
        method: 'POST',
        url: `${baseURL}/mailcode`,
        data: params
    })
        .then(res => res.data)
}